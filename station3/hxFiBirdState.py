"""
hxFiBirdState.py
----------------

Bird feeder scale runtime using HX711 + lgpio.

Goals
✔ Stable long-running operation
✔ Automatic baseline correction at boot
✔ Detect birds reliably (FSM)
✔ Recover from HX711 bad power-up states
✔ Persist offset calibration

Important design notes
- HX711 driver has NO tare → we maintain software offset
- Baseline must stay below threshold to detect birds
- Watchdog only triggers on impossible weights
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


# --------------------------------------------------
# Runtime tuning constants
# --------------------------------------------------

STARTUP_SETTLE_TIME = 1.2          # HX711 analog settle
BASELINE_MAX = 0.7 * weightThreshold
WATCHDOG_LIMIT = 300.0             # impossible weight → sensor fault
WATCHDOG_SAMPLES = 5


# --------------------------------------------------
# FIFO helper
# --------------------------------------------------

def sendFifo(wght):
    """Nonblocking FIFO write"""
    try:
        fd = os.open(fifo, os.O_WRONLY | os.O_NONBLOCK)
        with os.fdopen(fd, 'w') as fifoFp:
            fifoFp.write(str(wght) + "\n")
    except OSError as e:
        if e.errno != errno.ENXIO:
            raise


# --------------------------------------------------
# Baseline watchdog
# --------------------------------------------------

class BaselineWatchdog:
    """
    Detects HX711 stuck or mis-initialized states.
    Only triggers on unrealistic constant weight.
    """

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


# --------------------------------------------------
# Weight FSM (unchanged logic)
# --------------------------------------------------

STATE_IDLE = 0
STATE_SURGE_CANDIDATE = 1
STATE_SURGE_CONFIRMED = 2


class WeightFSM:
    def __init__(self, weightThreshold, weightMax):
        self.state = STATE_IDLE
        self.weightThreshold = weightThreshold
        self.weightMax = weightMax
        self.weightBaseline = 0.7 * weightThreshold

        self.baseline_buf = []
        self.surge_buf = []

        self.baseline_window = 5
        self.surge_window = 3
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

        if self.state == STATE_IDLE:

            if self.weightThreshold < w < self.weightMax:
                self.state = STATE_SURGE_CANDIDATE
                self._reset_surge()
                self.surge_buf.append(w)
                ms.log(f"{timestr} first move above threshold")
                return None

            self._update_baseline_buf(w)
            self.baseline_stable_at_entry = self._baseline_stable()
            return "IDLE" if self.baseline_stable_at_entry else None

        if self.state == STATE_SURGE_CANDIDATE:
            if self.weightThreshold < w < self.weightMax:
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
                sendFifo(-1)
                self.state = STATE_IDLE
                self.baseline_buf.clear()
            return None


# --------------------------------------------------
# Program start
# --------------------------------------------------

ms.init()
ms.log(f"Start hxFiBirdState {datetime.now()}")

fifo = birdpath['fifo']
if not fifoExists(fifo):
    os.mkfifo(fifo)

writePID(1)


# --------------------------------------------------
# HX711 initialization
# --------------------------------------------------

GPIO_FD = lgpio.gpiochip_open(0)
hx = HX711(gpio=lgpio, gpio_fd=GPIO_FD,
           dout_pin=hxDataPin, sck_pin=hxClckPin)

time.sleep(STARTUP_SETTLE_TIME)

# flush conversions (gain sync)
hx.stabilize()

# --- software baseline (replaces tare) ---
raw0 = hx.read_average(samples=10)
weight0 = (raw0 + hxOffset) / hxScale

if abs(weight0) > BASELINE_MAX:
    ms.log(f"Baseline drift at boot {weight0:.2f} g → correcting")
    hxOffset -= weight0 * hxScale


fsm = WeightFSM(weightThreshold, weightlimit)
watchdog = BaselineWatchdog()

baseline_est = 0.0
baseline_alpha = 0.03

sleepTime = 1.0


# --------------------------------------------------
# Main loop
# --------------------------------------------------

try:
    while True:

        raw = hx.read_raw()
        weight = roundFlt((raw + hxOffset) / hxScale)

        now = datetime.now()
        timeStr = f"{now.hour}:{now.minute}:{now.second}"

        # --- watchdog ---
        if watchdog.check(weight):
            ms.log("HX711 reinitializing after watchdog")

            hx.close()
            lgpio.gpiochip_close(GPIO_FD)
            time.sleep(0.5)

            GPIO_FD = lgpio.gpiochip_open(0)
            hx = HX711(gpio=lgpio, gpio_fd=GPIO_FD,
                       dout_pin=hxDataPin, sck_pin=hxClckPin)

            time.sleep(STARTUP_SETTLE_TIME)
            hx.stabilize()

            raw0 = hx.read_average(samples=10)
            weight0 = (raw0 + hxOffset) / hxScale
            if abs(weight0) > BASELINE_MAX:
                hxOffset -= weight0 * hxScale

            baseline_est = 0.0
            continue

        # --- FSM processing ---
        event = fsm.update(weight, timeStr)

        ms.log(f"{timeStr} {weight}g event={event}", False)

        # --- baseline drift EMA ---
        if event == "IDLE" and abs(weight) < BASELINE_MAX:

            baseline_est = (
                (1.0 - baseline_alpha) * baseline_est
                + baseline_alpha * weight
            )

            if abs(baseline_est) > 0.6:
                corr = np.clip(baseline_est, -1.5, 1.5)
                hxOffset -= corr * hxScale
                ms.log(f"{timeStr} hxOffset EMA adjust → {hxOffset}")
                baseline_est = 0.0

        if event == "SURGE_OK":
            baseline_est = 0.0

        time.sleep(sleepTime)


# --------------------------------------------------
# Shutdown
# --------------------------------------------------

except (KeyboardInterrupt, SystemExit):
    ms.log("hxFiBirdState shutting down")

finally:
    update_config_json({"hxOffset": hxOffset, "hxScale": hxScale})
    hx.close()
    lgpio.gpiochip_close(GPIO_FD)
    clearPID(1)
    ms.log(f"End hxFiBirdState {datetime.now()}")