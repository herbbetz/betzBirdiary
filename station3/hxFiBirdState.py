"""
hxFiBirdState.py
----------------

Runtime for HX711 bird feeder scale using Python HX711 driver.

- Reads HX711 directly
- FSM detects bird triggers and writes peak weights or -1 to birdpipe
- Maintains software offset and EMA baseline correction
- Performs occasional recalibration if FSM stuck in None
- Persists calibration values from config.json
"""

from datetime import datetime
import time
import numpy as np
import os
import errno

from lgpioBird.HX711 import HX711
from sharedBird import roundFlt, fifoExists, writePID, clearPID
from configBird3 import birdpath, hxDataPin, hxClckPin, hxOffset, hxScale, weightThreshold, weightlimit, update_config_json
import msgBird as ms

# ---------------- Constants ----------------
STARTUP_SETTLE_TIME = 1.2
BASELINE_MAX = 0.7 * weightThreshold
SLEEP_TIME = 1.0
BASELINE_ALPHA = 0.03

# ---------------- FIFO ----------------
fifo = birdpath['fifo']
if not fifoExists(fifo):
    os.mkfifo(fifo)
    ms.log("hxFiBird created FIFO")

def sendFifo(weight):
    try:
        fd = os.open(fifo, os.O_WRONLY | os.O_NONBLOCK)
        with os.fdopen(fd, 'w') as fifoFp:
            fifoFp.write(str(weight) + "\n")
    except OSError as e:
        if e.errno == errno.ENXIO:
            ms.log("hxFiBird: No FIFO reader, skip write")
        else:
            raise

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

# ---------------- Recalibration ----------------
def get_mean(raw_values, hxOffset, samples=50):
    readings = np.array([(v + hxOffset)/hxScale for v in raw_values[-samples:]])
    median = np.median(readings)
    spread = np.max(readings) - np.min(readings)
    return median, spread

def calibOffset(raw_values, hxOffset):
    median, spread = get_mean(raw_values, hxOffset)
    if spread < weightThreshold and abs(median) < 2*weightThreshold:
        hxOffset -= median * hxScale
        ms.log(f"hxOffset recalibrated: {hxOffset}")
    return hxOffset

# ---------------- Program start ----------------
ms.init()
ms.log(f"Start hxFiBirdState {datetime.now()}")
writePID(1)

hx = HX711(data_pin=hxDataPin, clock_pin=hxClckPin)
hx.tare()
hxOffset = calibOffset([hx.read_raw() for _ in range(50)], hxOffset)

fsm = WeightFSM(weightThreshold, weightlimit)
baseline_est = 0.0
none_count = 0
recent_raw = []

try:
    while True:
        raw_value = hx.read_raw()
        recent_raw.append(raw_value)
        if len(recent_raw) > 50:
            recent_raw.pop(0)
        weight = roundFlt((raw_value + hxOffset)/hxScale)
        now = datetime.now()
        timestr = f"{now.hour}:{now.minute}:{now.second}"

        event = fsm.update(weight, timestr)
        ms.log(f"{timestr} {weight}g event={event}", False)

        # EMA baseline drift
        if event == "IDLE" and abs(weight) < BASELINE_MAX:
            baseline_est = (1.0 - BASELINE_ALPHA)*baseline_est + BASELINE_ALPHA*weight
            if abs(baseline_est) > 0.6:
                corr = np.clip(baseline_est, -1.5, 1.5)
                hxOffset -= corr*hxScale
                ms.log(f"{timestr} hxOffset EMA adjust → {hxOffset}")
                baseline_est = 0.0

        # Recalibration if FSM stuck in None
        if event is None and abs(weight) < 2*weightThreshold:
            none_count += 1
            if none_count >= 15:
                hxOffset = calibOffset(recent_raw, hxOffset)
                none_count = 0
        else:
            none_count = 0

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