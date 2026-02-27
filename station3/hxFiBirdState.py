"""
hxFiBirdState.py

Bird feeder scale runtime using frozen HX711 driver.

- Reads raw weight values from HX711
- FSM detects bird triggers and writes peak weights or -1 to birdpipe
- Maintains software offset and EMA baseline correction
- Performs safe baseline recalibration on startup and during run
- Persists calibration values from configBird3
"""

from datetime import datetime
import time
import numpy as np
import os
import errno
import lgpio

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
BASELINE_MAX = 0.7 * weightThreshold
WATCHDOG_LIMIT = 300.0
WATCHDOG_SAMPLES = 5
SLEEP_TIME = 1.0
BASELINE_ALPHA = 0.03
NONE_CALIB_LIMIT = 15
samples_for_calib = 50

# ---------------- FIFO ----------------
fifo = birdpath['fifo']
if not fifoExists(fifo):
    os.mkfifo(fifo)
    ms.log("hxFiBird created missing FIFO")

# ---------------- Helper functions ----------------
def get_mean(raw_vals):
    median = np.median(raw_vals)
    spread = np.max(raw_vals) - np.min(raw_vals)
    ms.log(f"spread from {np.min(raw_vals)} to {np.max(raw_vals)}")
    return median, spread

def calibOffset(tries, raw_vals, hxoffset, sleeptime):
    success = False
    for _ in range(tries):
        median, spread = get_mean(raw_vals)
        if spread < weightThreshold and abs(median) < 2 * weightThreshold:
            hxoffset -= median * hxScale
            success = True
        time.sleep(sleeptime)
    ms.log("hxOffset Cal OK" if success else "hxOffset Cal SKIPPED")
    ms.log(f"hxOffset reset to: {hxoffset}")
    return hxoffset

def sendFifo(weight):
    try:
        fd = os.open(fifo, os.O_WRONLY | os.O_NONBLOCK)
        with os.fdopen(fd, 'w') as fifoFp:
            fifoFp.write(str(weight) + "\n")
    except OSError as e:
        if e.errno != errno.ENXIO:
            raise

# ---------------- Watchdog ----------------
class BaselineWatchdog:
    def __init__(self):
        self.buffer = []

    def check(self, weight):
        self.buffer.append(weight)
        if len(self.buffer) > WATCHDOG_SAMPLES:
            self.buffer.pop(0)
        if len(self.buffer) == WATCHDOG_SAMPLES:
            median = np.median(self.buffer)
            if abs(median) > WATCHDOG_LIMIT:
                ms.log(f"WATCHDOG sensor fault: {median} g")
                self.buffer.clear()
                return True
        return False

# ---------------- FSM ----------------
STATE_IDLE = 0
STATE_SURGE_CANDIDATE = 1
STATE_SURGE_CONFIRMED = 2

class WeightFSM:
    def __init__(self, threshold, weight_max):
        self.state = STATE_IDLE
        self.threshold = threshold
        self.weightMax = weight_max
        self.baseline_buf = []
        self.surge_buf = []
        self.baseline_window = 5
        self.surge_window = 3
        self.weightBaseline = 0.7 * threshold
        self.baseline_stable_at_entry = False

    def _baseline_stable(self):
        return len(self.baseline_buf) >= self.baseline_window and all(v < self.weightBaseline for v in self.baseline_buf)

    def _update_baseline_buf(self, w):
        if w < self.threshold:
            self.baseline_buf.append(abs(w))
            if len(self.baseline_buf) > self.baseline_window:
                self.baseline_buf.pop(0)

    def _reset_surge(self):
        self.surge_buf = []

    def update(self, w, timestr):
        if self.state == STATE_IDLE:
            if self.threshold < w < self.weightMax:
                self.state = STATE_SURGE_CANDIDATE
                self._reset_surge()
                self.surge_buf.append(w)
                ms.log(f"{timestr} first move above threshold")
                return None
            self._update_baseline_buf(w)
            self.baseline_stable_at_entry = self._baseline_stable()
            return "IDLE" if self.baseline_stable_at_entry else None

        if self.state == STATE_SURGE_CANDIDATE:
            if self.threshold < w < self.weightMax:
                self.surge_buf.append(w)
                if len(self.surge_buf) >= self.surge_window and self.baseline_stable_at_entry:
                    self.state = STATE_SURGE_CONFIRMED
                    peak = max(self.surge_buf)
                    ms.log(f"{timestr} surge → FIFO {peak}g")
                    sendFifo(peak)
                    self._reset_surge()
                    return "SURGE_OK"
            else:
                self.state = STATE_IDLE
            return None

        if self.state == STATE_SURGE_CONFIRMED:
            if w < self.threshold or w >= self.weightMax:
                sendFifo(-1)
                self.state = STATE_IDLE
                self.baseline_buf.clear()
            return None

# ---------------- Main ----------------
ms.init()
ms.log(f"Start hxFiBirdState {datetime.now()}")
writePID(1)

# ---- Correct driver initialization ----
hx = HX711.create(lgpio, dout_pin=hxDataPin, sck_pin=hxClckPin)
hx.set_offset(-hxOffset)   # preserve legacy formula
hx.set_scale(hxScale)

fsm = WeightFSM(weightThreshold, weightlimit)
watchdog = BaselineWatchdog()
baseline_est = 0.0
none_counter = 0
raw_sample_buffer = []

try:
    time.sleep(STARTUP_SETTLE_TIME)

    while True:
        raw_value = hx.read_raw()
        weight = roundFlt((raw_value + hxOffset) / hxScale)

        now = datetime.now()
        timestr = f"{now.hour}:{now.minute}:{now.second}"

        event = fsm.update(weight, timestr)
        ms.log(f"{timestr} {weight}g event={event}", False)

        # EMA baseline correction
        if event == "IDLE" and abs(weight) < BASELINE_MAX:
            baseline_est = (1.0 - BASELINE_ALPHA) * baseline_est + BASELINE_ALPHA * weight
            if abs(baseline_est) > 0.6:
                corr = np.clip(baseline_est, -1.5, 1.5)
                hxOffset -= corr * hxScale
                ms.log(f"{timestr} hxOffset EMA adjust → {hxOffset}")
                baseline_est = 0.0

        # Watchdog
        if watchdog.check(weight):
            ms.log("HX711 watchdog triggered; waiting for recovery")
            baseline_est = 0.0
            continue

        # ----- Recalibration identical to C version -----
        if event is None and abs(weight) < 2 * weightThreshold:
            none_counter += 1
            raw_sample_buffer.append(raw_value)
            if none_counter >= NONE_CALIB_LIMIT:
                hxOffset = calibOffset(1, raw_sample_buffer[-samples_for_calib:], hxOffset, SLEEP_TIME)
                none_counter = 0
                raw_sample_buffer.clear()
        else:
            none_counter = 0
            raw_sample_buffer.clear()

        if event == "SURGE_OK":
            baseline_est = 0.0

        time.sleep(SLEEP_TIME)

except (KeyboardInterrupt, SystemExit):
    ms.log("hxFiBirdState shutting down")

finally:
    update_config_json({"hxOffset": hxOffset, "hxScale": hxScale})
    hx.close()
    clearPID(1)
    ms.log(f"End hxFiBirdState {datetime.now()}")