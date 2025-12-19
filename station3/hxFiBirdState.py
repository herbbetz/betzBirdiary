"""
hxFiBird3.py

- Initializes HX711 with tare and scaling
- Performs resilient offset auto-calibration
- Uses a finite-state machine to:
    * detect stable baseline
    * detect constant weight surge (>3 values)
    * trigger FIFO once per surge
    * adapt baseline offset safely
- Sends weight via FIFO
- Logs events with timestamps
- Saves updated calibration back to config
- PID-managed lifecycle
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


# --------------------------------------------------
# Helper functions
# --------------------------------------------------

def get_mean(sensor, num_vals, hOffset, sleeptime):
    ms.log(f"hxFi samples {num_vals} readings...")
    readings = np.empty(shape=num_vals, dtype=float)

    for i in range(num_vals):
        raw = sensor.read_raw()
        readings[i] = roundFlt((raw + hOffset) / hxScale)
        time.sleep(sleeptime)

    median = np.median(readings)
    spread = np.max(readings) - np.min(readings)
    ms.log(f"spread from {np.min(readings)} to {np.max(readings)}")
    return median, spread


def calibOffset(tries, sensor, hxoffset, sleeptime):
    success = False
    for _ in range(tries):
        mean, spread = get_mean(sensor, 50, hxoffset, sleeptime)
        if spread < weightThreshold:
            if abs(mean) < 1.0:
                success = True
                break
            else:
                hxoffset -= mean * hxScale
        time.sleep(sleeptime)

    ms.log("hxOffset Cal OK" if success else "hxOffset Cal FAILED")
    ms.log(f"hxOffset reset to: {hxoffset}")
    return hxoffset


def sendFifo(wght):
    # nonblocking:
    try:
        fd = os.open(fifo, os.O_WRONLY | os.O_NONBLOCK)
        with os.fdopen(fd, 'w') as fifoFp:
            fifoFp.write(str(wght) + "\n")
    except OSError as e:
        if e.errno == errno.ENXIO: # ENXIO=6 usually, meaning no such device (FIFO reader)
            ms.log("hxFiBird: No FIFO reader, skip write")
        else:
            raise # Unexpected error (e.g. permission, missing file)


# --------------------------------------------------
# Weight finite-state machine (chatGPT)
# --------------------------------------------------

STATE_IDLE = 0
STATE_SURGE_CANDIDATE = 1
STATE_SURGE_CONFIRMED = 2


class WeightFSM:
    def __init__(self,
                 weightThreshold,
                 weightMax):

        self.state = STATE_IDLE

        self.weightThreshold = weightThreshold
        self.weightMax = weightMax
        self.weightBaseline = 0.7 * weightThreshold # tolerance for baseline

        self.baseline_window = 5 # number of values that baseline should have been stable
        self.surge_window = 3 # number of values considered for a valid surge

        self.baseline_buf = []
        self.surge_buf = []

        self.baseline_stable_at_entry = False

    def _baseline_stable(self):
        if len(self.baseline_buf) < self.baseline_window:
            return False
        return all(v < self.weightBaseline for v in self.baseline_buf)

    def _update_baseline_buf(self, w):
        if w < self.weightThreshold:
            self.baseline_buf.append(abs(w))
            if len(self.baseline_buf) > self.baseline_window:
                self.baseline_buf.pop(0)

    def _reset_surge(self):
        self.surge_buf = []

    def update(self, w, timeString):
        """
        Process one weight sample.

        Returns:
            "IDLE"     -> safe to use for offset adaption
            "SURGE_OK" -> surge confirmed, FIFO already sent
            None       -> ignore for calibration
        """

        # ---------------- IDLE ----------------
        if self.state == STATE_IDLE:

            # FIRST: detect surge
            if w > self.weightThreshold and w < self.weightMax:
                self.state = STATE_SURGE_CANDIDATE
                self._reset_surge()
                self.surge_buf.append(w)
                ms.log(f"{timeString} first movement above threshold")
                return None

            # ONLY baseline samples reach here
            self._update_baseline_buf(w)
            self.baseline_stable_at_entry = self._baseline_stable()

            return "IDLE" if self.baseline_stable_at_entry else None

        # -------- SURGE CANDIDATE --------
        if self.state == STATE_SURGE_CANDIDATE:
            if w > self.weightThreshold and w < self.weightMax:
                self.surge_buf.append(w)
                # ms.log(f"basebuf {self.baseline_buf}, {self.baseline_stable_at_entry}")
                if len(self.surge_buf) >= self.surge_window:
                    if self.baseline_stable_at_entry:
                        self.state = STATE_SURGE_CONFIRMED
                        peak = max(self.surge_buf)
                        ms.log(f"{len(self.surge_buf)} moves → FIFO push")
                        sendFifo(peak)
                        self._reset_surge()
                        return "SURGE_OK"
            else:
                self.state = STATE_IDLE
            return None

        # -------- SURGE CONFIRMED --------
        if self.state == STATE_SURGE_CONFIRMED:
            if w < self.weightThreshold or w >= self.weightMax:
                self.state = STATE_IDLE
                self.baseline_buf.clear() 
            return None


# --------------------------------------------------
# Main
# --------------------------------------------------

config_path = f"{birdpath['appdir']}/config.json"

samples = 50
sampleIdx = 0
sampleArr = np.empty(shape=samples, dtype=float)

sleepTime = 1.0
# EMA baseline tracking
baseline_est = 0.0
baseline_alpha = 0.002   # tuned for 1 Hz HX711 sampling

ms.init()
ms.log(f"Start hxFiBird3 {datetime.now()}")

if hxScale == 0:
    ms.log("hxScale must not be zero")
    exit(0)

fifo = birdpath['fifo']
if not fifoExists(fifo):
    os.mkfifo(fifo)
    ms.log("hxFiBird created FIFO")

writePID(1)

hx = HX711(data_pin=hxDataPin, clock_pin=hxClckPin)
hx.tare()
hxOffset = calibOffset(2, hx, hxOffset, sleepTime)

fsm = WeightFSM(
    weightThreshold=weightThreshold,
    weightMax = weightlimit
)

try:
    while True:
        reading = hx.read_raw()
        weight = roundFlt((reading + hxOffset) / hxScale)

        now = datetime.now()
        timeStr = f"{now.hour}:{now.minute}:{now.second}"
        ms.log(f"{timeStr} {weight} grams", False)

        event = fsm.update(weight, timeStr)

        # -------- baseline-driven offset adaption (EMA + samples safety median) --------
        if event == "IDLE":

            # ---- EMA drift tracking  = Exponential Moving Average, adapts every measurement ----
            baseline_est = (1.0 - baseline_alpha) * baseline_est + baseline_alpha * weight

            # Only apply small EMA correction if clearly drifting
            if abs(baseline_est) > 0.3:  # tighter threshold than median
                hxOffset -= baseline_est * hxScale
                ms.log(f"hxOffset EMA adjust: {hxOffset}")

            # ---- Median batch safety net ----
            if sampleIdx < samples:
                sampleArr[sampleIdx] = weight
                sampleIdx += 1
            else:
                spread = np.max(sampleArr) - np.min(sampleArr)
                if (spread < 0.2):
                    ms.log("no baseline spread -> disconnected?")

                apartZero = np.median(sampleArr)
                # safety clamp: only if EMA somehow failed
                if abs(apartZero) > 1.5:
                    hxOffset -= apartZero * hxScale
                    ms.log(f"hxOffset median adjust: {hxOffset}")

                sampleIdx = 0
        if event == "SURGE_OK":
            baseline_est = 0.0 # reset EMA
        time.sleep(sleepTime)

except (KeyboardInterrupt, SystemExit):
    ms.log("balance going down")

finally:
    update_config_json({"hxOffset": hxOffset, "hxScale": hxScale})
    hx.close()
    clearPID(1)
    ms.log(f"End hxFiBird3 {datetime.now()}")
