"""
hxFiBirdState.py — Bird feeder weight monitoring with HX711

- Uses lean HX711 driver (gain=64)
- Performs startup stabilization and offset calibration
- Detects surges via finite-state machine
- Adds baseline watchdog for impossible shifts
- Sends weight via FIFO
- Logs events with timestamps
- EMA-based drift correction
- Compatible with lgpio Raspbian Trixie
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

# ------------------- Runtime constants -------------------
STARTUP_SETTLE_TIME = 1.2     # seconds for HX711 front-end to settle
WATCHDOG_LIMIT = 120          # grams considered impossible baseline
WATCHDOG_SAMPLES = 5          # consecutive samples for watchdog trigger

# ------------------- Helper functions -------------------
def get_mean(sensor, num_vals, hOffset, sleeptime):
    """Collect multiple samples, return median and spread for diagnostics."""
    readings = np.empty(shape=num_vals, dtype=float)
    for i in range(num_vals):
        raw = sensor.read_raw()
        readings[i] = roundFlt((raw + hOffset) / hxScale)
        time.sleep(sleeptime)
    median = np.median(readings)
    spread = np.max(readings) - np.min(readings)
    return median, spread


def calibOffset(sensor, hxoffset, sleeptime):
    """
    Perform offset auto-calibration using averaged raw readings.

    Philosophy: assume scale unloaded → average raw value represents baseline.
    """
    raw_mean = sensor.read_average(samples=30, delay=sleeptime)
    weight_mean = roundFlt((raw_mean + hxoffset) / hxScale)
    hxoffset -= weight_mean * hxScale
    ms.log(f"hxOffset calibrated → {hxoffset}")
    return hxoffset


def sendFifo(wght):
    """Nonblocking FIFO write; skip silently if no reader."""
    fifo = birdpath['fifo']
    try:
        fd = os.open(fifo, os.O_WRONLY | os.O_NONBLOCK)
        with os.fdopen(fd, 'w') as fifoFp:
            fifoFp.write(str(wght) + "\n")
    except OSError as e:
        if e.errno != errno.ENXIO:
            raise

# ------------------- Baseline watchdog -------------------
class BaselineWatchdog:
    """Detects impossible baseline shifts (HX711 boot glitch)."""
    def __init__(self):
        self.buffer = []

    def check(self, weight, raw, offset):
        self.buffer.append(weight)
        if len(self.buffer) > WATCHDOG_SAMPLES:
            self.buffer.pop(0)
        if len(self.buffer) == WATCHDOG_SAMPLES:
            median = np.median(self.buffer)
            if abs(median) > WATCHDOG_LIMIT:
                ms.log(f"WATCHDOG baseline shift: weight={median} raw={raw} offset={offset}")
                self.buffer.clear()
                return True
        return False

# ------------------- Weight finite-state machine -------------------
STATE_IDLE = 0
STATE_SURGE_CANDIDATE = 1
STATE_SURGE_CONFIRMED = 2

class WeightFSM:
    """FSM to detect stable baseline and weight surges."""
    def __init__(self, weightThreshold, weightMax):
        self.state = STATE_IDLE
        self.weightThreshold = weightThreshold
        self.weightMax = weightMax
        self.weightBaseline = 0.7 * weightThreshold
        self.baseline_window = 5
        self.surge_window = 3
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

    def update(self, w, timestr):
        """FSM update: returns 'IDLE', 'SURGE_OK', or None (transitional)."""
        if self.state == STATE_IDLE:
            if w > self.weightThreshold and w < self.weightMax:
                self.state = STATE_SURGE_CANDIDATE
                self._reset_surge()
                self.surge_buf.append(w)
                ms.log(f"{timestr} first move above threshold")
                return None
            self._update_baseline_buf(w)
            self.baseline_stable_at_entry = self._baseline_stable()
            return "IDLE" if self.baseline_stable_at_entry else None

        if self.state == STATE_SURGE_CANDIDATE:
            if w > self.weightThreshold and w < self.weightMax:
                self.surge_buf.append(w)
                if len(self.surge_buf) >= self.surge_window:
                    if self.baseline_stable_at_entry:
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
            if w < self.weightThreshold or w >= self.weightMax:
                sendFifo(-1)  # signal recording stop
                self.state = STATE_IDLE
                self.baseline_buf.clear()
            return None

# ------------------- Main lifecycle -------------------
ms.init()
ms.log(f"Start hxFiBirdState {datetime.now()}")

fifo = birdpath['fifo']
if not fifoExists(fifo):
    os.mkfifo(fifo)

writePID(1)

# --- Open GPIO chip & initialize HX711 driver ---
GPIO_FD = lgpio.gpiochip_open(0)
hx = HX711(gpio=lgpio, gpio_fd=GPIO_FD, dout_pin=hxDataPin, sck_pin=hxClckPin)

# Allow front-end to settle
time.sleep(STARTUP_SETTLE_TIME)

# Flush first conversions for correct gain phase
hx.stabilize()

# Initial offset calibration
hxOffset = calibOffset(hx, hxOffset, 0.05)

fsm = WeightFSM(weightThreshold, weightlimit)
watchdog = BaselineWatchdog()

baseline_est = 0.0
baseline_alpha = 0.03
sleepTime = 1.0

try:
    while True:
        raw = hx.read_raw()
        weight = roundFlt((raw + hxOffset) / hxScale)
        now = datetime.now()
        timeStr = f"{now.hour}:{now.minute}:{now.second}"

        # ----------------- Watchdog: detect impossible baseline -----------------
        if watchdog.check(weight, raw, hxOffset):
            ms.log("HX711 reinitializing after watchdog")
            hx.close()
            time.sleep(0.5)
            hx = HX711(gpio=lgpio, gpio_fd=GPIO_FD, dout_pin=hxDataPin, sck_pin=hxClckPin)
            time.sleep(STARTUP_SETTLE_TIME)
            hx.stabilize()
            hxOffset = calibOffset(hx, hxOffset, 0.05)
            baseline_est = 0.0
            continue

        # ----------------- FSM event processing -----------------
        event = fsm.update(weight, timeStr)
        ms.log(f"{timeStr} {weight}g event={event}", False)

        # ----------------- EMA baseline drift tracking -----------------
        if event == "IDLE" and abs(weight) < 0.7 * weightThreshold:
            baseline_est = (1.0 - baseline_alpha) * baseline_est + baseline_alpha * weight
            if abs(baseline_est) > 0.6:
                corr = np.clip(baseline_est, -1.5, 1.5)
                hxOffset -= corr * hxScale
                ms.log(f"{timeStr} hxOffset EMA adjust → {hxOffset}")
                baseline_est = 0.0

        if event == "SURGE_OK":
            baseline_est = 0.0

        time.sleep(sleepTime)

except (KeyboardInterrupt, SystemExit):
    ms.log("hxFiBirdState shutting down")

finally:
    update_config_json({"hxOffset": hxOffset, "hxScale": hxScale})
    hx.close()
    lgpio.gpiochip_close(GPIO_FD)
    clearPID(1)
    ms.log(f"End hxFiBirdState {datetime.now()}")