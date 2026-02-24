"""
hx711test.py — Diagnostic for HX711 + FSM + watchdog

- Demonstrates stabilization, EMA baseline, and surge detection
- Logs events to console
- Sends peaks to FIFO (nonblocking)
"""

import time
import numpy as np
from datetime import datetime
import os
import errno
import lgpio
from lgpioBird.HX711 import HX711
from sharedBird import roundFlt, fifoExists
from configBird3 import birdpath, hxDataPin, hxClckPin, hxOffset, hxScale, weightThreshold, weightlimit

# ---------------- Runtime constants ----------------
STARTUP_SETTLE_TIME = 1.2
WATCHDOG_LIMIT = 120
WATCHDOG_SAMPLES = 5
EMA_ALPHA = 0.03
SLEEP_TIME = 1.0

# ---------------- FIFO ----------------
FIFO_PATH = birdpath['fifo']
if not fifoExists(FIFO_PATH):
    os.mkfifo(FIFO_PATH)

def sendFifo(weight):
    """Nonblocking FIFO write; skip silently if no reader."""
    try:
        fd = os.open(FIFO_PATH, os.O_WRONLY | os.O_NONBLOCK)
        with os.fdopen(fd, 'w') as fifoFp:
            fifoFp.write(f"{weight}\n")
    except OSError as e:
        if e.errno != errno.ENXIO:
            raise

# ---------------- Watchdog ----------------
class BaselineWatchdog:
    def __init__(self):
        self.buffer = []

    def check(self, weight, raw, offset):
        self.buffer.append(weight)
        if len(self.buffer) > WATCHDOG_SAMPLES:
            self.buffer.pop(0)
        if len(self.buffer) == WATCHDOG_SAMPLES:
            median = np.median(self.buffer)
            if abs(median) > WATCHDOG_LIMIT:
                print(f"WATCHDOG: weight={median} raw={raw} offset={offset}")
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
        self.baseline_window = 5
        self.surge_window = 3
        self.baseline_buf = []
        self.surge_buf = []
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
                print(f"{timestr} first move above threshold")
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
                    print(f"{timestr} surge → FIFO {peak}g")
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
def main():
    GPIO_FD = lgpio.gpiochip_open(0)
    hx = HX711(gpio=lgpio, gpio_fd=GPIO_FD, dout_pin=hxDataPin, sck_pin=hxClckPin)

    time.sleep(STARTUP_SETTLE_TIME)
    hx.stabilize()
    offset = hx.read_average(30, delay=0.05)

    fsm = WeightFSM(weightThreshold, weightlimit)
    watchdog = BaselineWatchdog()
    baseline_est = 0.0

    print("Starting hx711test.py... Ctrl+C to stop")
    try:
        while True:
            raw = hx.read_raw()
            weight = roundFlt((raw - offset) / hxScale)
            now = datetime.now()
            timestr = f"{now.hour}:{now.minute}:{now.second}"

            # Watchdog
            if watchdog.check(weight, raw, offset):
                print("HX711 reinitializing after watchdog")
                hx.close()
                time.sleep(0.5)
                hx = HX711(gpio=lgpio, gpio_fd=GPIO_FD, dout_pin=hxDataPin, sck_pin=hxClckPin)
                time.sleep(STARTUP_SETTLE_TIME)
                hx.stabilize()
                offset = hx.read_average(30, delay=0.05)
                baseline_est = 0.0
                continue

            # FSM
            event = fsm.update(weight, timestr)
            print(f"{timestr} weight={weight}g event={event}")

            # EMA baseline
            if event == "IDLE" and abs(weight) < 0.7 * weightThreshold:
                baseline_est = (1.0 - EMA_ALPHA) * baseline_est + EMA_ALPHA * weight
                if abs(baseline_est) > 0.6:
                    corr = np.clip(baseline_est, -1.5, 1.5)
                    offset += corr * hxScale
                    print(f"{timestr} EMA adjust → offset={offset}")
                    baseline_est = 0.0

            if event == "SURGE_OK":
                baseline_est = 0.0

            time.sleep(SLEEP_TIME)

    except KeyboardInterrupt:
        print("Exiting hx711test.py...")

    finally:
        hx.close()
        lgpio.gpiochip_close(GPIO_FD)

if __name__ == "__main__":
    main()