"""
hxFiBirdStateC.py
-----------------

Bird feeder scale runtime using HX711 C daemon (hx711d).

- Reads raw weight values from /home/pi/station3/ramdisk/hxfifo
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
import json

from sharedBird import roundFlt, fifoExists, writePID, clearPID
from configBird3 import birdpath, hxOffset, hxScale, weightThreshold, weightlimit, update_config_json
import msgBird as ms

# ---------------- Constants ----------------
STARTUP_SETTLE_TIME = 1.2
BASELINE_MAX = 0.7 * weightThreshold
WATCHDOG_LIMIT = 300.0
WATCHDOG_SAMPLES = 5
SLEEP_TIME = 1.0
BASELINE_ALPHA = 0.03

# ---------------- Paths ----------------
HXFIFO = "/home/pi/station3/ramdisk/hxfifo"
BIRDPIPE = birdpath['fifo']
PIDFILE = "/home/pi/station3/ramdisk/hx711d.pid"
CONFIG_FILE = "/home/pi/station3/configBird3/config.json"

# ---------------- Load calibration ----------------
with open(CONFIG_FILE, "r") as f:
    config = json.load(f)
hxOffset = config.get("hxOffset", 0)
hxScale = config.get("hxScale", 1)

# ---------------- Check FIFOs ----------------
if not fifoExists(HXFIFO):
    ms.log(f"ERROR: hx711d FIFO missing: {HXFIFO}")
    raise SystemExit(1)
if not fifoExists(BIRDPIPE):
    os.mkfifo(BIRDPIPE)
    ms.log(f"Created missing birdpipe FIFO: {BIRDPIPE}")

# ---------------- Optional: check daemon ----------------
if not os.path.exists(PIDFILE):
    ms.log(f"WARNING: hx711d.pid missing; daemon may not be running")

def sendFifo(weight):
    """Nonblocking write to birdpipe FIFO"""
    try:
        fd = os.open(BIRDPIPE, os.O_WRONLY | os.O_NONBLOCK)
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

# ---------------- Recalibration functions ----------------
def get_mean(raw_values, hxOffset, samples=50):
    """Return median and spread of raw readings"""
    readings = np.empty(samples, dtype=float)
    for i, val in enumerate(raw_values):
        readings[i] = roundFlt((val + hxOffset) / hxScale)
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
ms.log(f"Start hxFiBirdStateC {datetime.now()}")
writePID(1)

fsm = WeightFSM(weightThreshold, weightlimit)
watchdog = BaselineWatchdog()
baseline_est = 0.0
none_count = 0
recent_raw = []

try:
    with open(HXFIFO, "r") as fifo_in:
        time.sleep(STARTUP_SETTLE_TIME)

        while True:
            line = fifo_in.readline()
            if not line:
                time.sleep(0.1)
                continue
            try:
                raw_value = float(line.strip())
            except ValueError:
                continue

            recent_raw.append(raw_value)
            if len(recent_raw) > 50:  # keep last 50
                recent_raw.pop(0)

            weight = roundFlt((raw_value + hxOffset) / hxScale)
            now = datetime.now()
            timestr = f"{now.hour}:{now.minute}:{now.second}"

            # Watchdog
            if watchdog.check(weight):
                ms.log("HX711 watchdog triggered; waiting for daemon recovery")
                baseline_est = 0.0

            # FSM update
            event = fsm.update(weight, timestr)
            ms.log(f"{timestr} {weight}g event={event}", False)

            # EMA baseline drift
            if event == "IDLE" and abs(weight) < BASELINE_MAX:
                baseline_est = (1.0 - BASELINE_ALPHA) * baseline_est + BASELINE_ALPHA * weight
                if abs(baseline_est) > 0.6:
                    corr = np.clip(baseline_est, -1.5, 1.5)
                    hxOffset -= corr * hxScale
                    ms.log(f"{timestr} hxOffset EMA adjust → {hxOffset}")
                    baseline_est = 0.0

            # -------- Recalibration if FSM stuck in None ----------
            if event is None and abs(weight) < 2*weightThreshold:
                none_count += 1
                if none_count >= 15:
                    hxOffset = calibOffset(recent_raw[-50:], hxOffset)
                    none_count = 0
            else:
                none_count = 0

            if event == "SURGE_OK":
                baseline_est = 0.0

            time.sleep(SLEEP_TIME)

except (KeyboardInterrupt, SystemExit):
    ms.log("hxFiBirdStateC shutting down")

finally:
    update_config_json({"hxOffset": hxOffset, "hxScale": hxScale})
    clearPID(1)
    ms.log(f"End hxFiBirdStateC {datetime.now()}")