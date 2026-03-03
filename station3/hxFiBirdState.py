"""
Bird feeder scale runtime using blocking HX711 driver.

- Reads raw weight values from HX711
- FSM detects bird triggers and writes peak weights or -1 to birdpipe
- Maintains software offset and EMA baseline correction
- Performs safe baseline recalibration on startup and during run (spread-based)
- Persists calibration values from configBird3

Simple deterministic FSM:
IDLE -> ARRIVAL -> PRESENT -> DEPARTURE -> IDLE

- No None state
- Immediate trigger when threshold crossed
- Baseline recalibration only in IDLE
"""

from datetime import datetime
import time
import numpy as np
import os
import errno

from lgpioBird.HX711 import HX711
from sharedBird import roundFlt, fifoExists, writePID, clearPID
from configBird3 import (
    birdpath, hxDataPin, hxClckPin,
    hxOffset, hxScale,
    weightThreshold, weightlimit,
    update_config_json
)
import msgBird as ms


# ---------------- Constants ----------------
STARTUP_SETTLE_TIME = 1.2
SLEEP_TIME = 1.0

BASELINE_ZONE = 0.6 * weightThreshold
STABLE_COUNT = 3
DRIFT_ALPHA = 0.02
MAX_SPREAD_FOR_CAL = weightThreshold


# ---------------- FIFO ----------------
fifo = birdpath["fifo"]
if not fifoExists(fifo):
    os.mkfifo(fifo)
    ms.log("hxFiBird created missing FIFO")


# ---------------- Helper ----------------
def get_median_spread(vals):
    return np.median(vals), np.max(vals) - np.min(vals)


def calibOffset(samples, hxoffset):
    median, spread = get_median_spread(samples)
    ms.log(f"Calibration spread {spread}")

    if spread < MAX_SPREAD_FOR_CAL:
        hxoffset += median * hxScale
        ms.log("hxOffset Cal OK")
    else:
        ms.log("hxOffset Cal SKIPPED")

    ms.log(f"hxOffset now {hxoffset}")
    return hxoffset


def sendFifo(weight):
    try:
        fd = os.open(fifo, os.O_WRONLY | os.O_NONBLOCK)
        with os.fdopen(fd, "w") as f:
            f.write(str(weight) + "\n")
    except OSError as e:
        if e.errno != errno.ENXIO:
            raise


# ---------------- FSM ----------------
STATE_IDLE = 0
STATE_ARRIVAL = 1
STATE_PRESENT = 2
STATE_DEPARTURE = 3


class WeightFSM:
    def __init__(self, threshold, weight_max):
        self.state = STATE_IDLE
        self.threshold = threshold
        self.weightMax = weight_max
        self.stable_counter = 0
        self.peak = 0.0

    def update(self, w, tstr):

        # ---------- IDLE ----------
        if self.state == STATE_IDLE:
            if w > self.threshold:
                self.state = STATE_ARRIVAL
                self.stable_counter = 0
                self.peak = w
                ms.log(f"{tstr} ARRIVAL")
                return "ARRIVAL"
            return "IDLE"

        # ---------- ARRIVAL ----------
        if self.state == STATE_ARRIVAL:
            if w > self.threshold:
                self.peak = max(self.peak, w)
                self.stable_counter += 1
                if self.stable_counter >= STABLE_COUNT:
                    self.state = STATE_PRESENT
                    sendFifo(self.peak)
                    ms.log(f"{tstr} PRESENT peak={self.peak}")
                    return "PRESENT"
            else:
                self.state = STATE_IDLE
            return "ARRIVAL"

        # ---------- PRESENT ----------
        if self.state == STATE_PRESENT:
            self.peak = max(self.peak, w)
            if w < self.threshold:
                self.state = STATE_DEPARTURE
                self.stable_counter = 0
                sendFifo(-1)
                ms.log(f"{tstr} DEPARTURE")
                return "DEPARTURE"
            return "PRESENT"

        # ---------- DEPARTURE ----------
        if self.state == STATE_DEPARTURE:
            if w < BASELINE_ZONE:
                self.stable_counter += 1
                if self.stable_counter >= STABLE_COUNT:
                    self.state = STATE_IDLE
                    ms.log(f"{tstr} back to IDLE")
                    return "IDLE"
            elif w > self.threshold:
                self.state = STATE_ARRIVAL
            return "DEPARTURE"


# ---------------- Main ----------------
ms.init()
ms.log(f"Start hxFiBirdState {datetime.now()}")
writePID(1)

hx = HX711(data_pin=hxDataPin, clock_pin=hxClckPin)

# ---- Startup baseline calibration ----
time.sleep(STARTUP_SETTLE_TIME)
raw_samples = [hx.read_raw() for _ in range(40)]
hxOffset = calibOffset(raw_samples, hxOffset)

fsm = WeightFSM(weightThreshold, weightlimit)

drift_est = 0.0
raw_idle_buffer = []


try:
    while True:
        raw = hx.read_raw()
        weight = roundFlt((raw - hxOffset) / hxScale)

        now = datetime.now()
        tstr = f"{now.hour}:{now.minute}:{now.second}"

        state = fsm.update(weight, tstr)

        # debugging:
        # ms.log(f"RAW={raw:.0f}  WEIGHT={weight:.2f} g  STATE={state}")
        ms.log(f"{tstr} {weight:.1f}grams {state}", terminal=False) # (..., False) prints only to 'linetxt', not to stdout

        # -------- Drift correction (IDLE only) --------
        if state == "IDLE" and abs(weight) < BASELINE_ZONE:
            drift_est = (1 - DRIFT_ALPHA) * drift_est + DRIFT_ALPHA * weight
            if abs(drift_est) > 0.5:
                hxOffset += drift_est * hxScale
                ms.log(f"{tstr} drift adjust → {hxOffset}")
                drift_est = 0.0

        # -------- Recalibration (true idle only) --------
            raw_idle_buffer.append(raw)
            if len(raw_idle_buffer) >= 30:
                hxOffset = calibOffset(raw_idle_buffer, hxOffset)
                raw_idle_buffer.clear()
        else:
            raw_idle_buffer.clear()
            drift_est = 0.0

        time.sleep(SLEEP_TIME)

except (KeyboardInterrupt, SystemExit):
    ms.log("hxFiBirdState shutting down")

finally:
    update_config_json({"hxOffset": hxOffset, "hxScale": hxScale})
    hx.close()
    clearPID(1)
    ms.log(f"End hxFiBirdState {datetime.now()}")