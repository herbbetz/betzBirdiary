"""
hxFiBirdStateCt2.py

Refactor principle:
- ONE object per cycle (Sample)
- all subsystems operate on it
- recorder only observes
"""

from dataclasses import dataclass
from collections import deque
from datetime import datetime
import time
import numpy as np
import ctypes
import os
import errno

from sharedBird import fifoExists, writePID, clearPID
from configBird3 import (
    birdpath, hxDataPin, hxClckPin, hxScale,
    weightThreshold, weightlimit,
    update_config_json
)
import msgBird as ms


# ============================================================
# SAMPLE (single source of truth per cycle)
# ============================================================

@dataclass
class Sample:
    t: float = 0.0

    # raw pipeline
    raw_sample: int = 0
    raw: int = 0

    # physical model
    offset: float = 0.0
    weight: float = 0.0
    drift: float = 0.0

    # FSM
    state: int = 0
    stable: int = 0
    peak: float = 0.0

    # watchdog
    glitch: bool = False
    glitch_reason: str = ""

    # annotations
    note: str = ""


# ============================================================
# HX711 DRIVER (unchanged contract)
# ============================================================

class HX711_CT:
    def __init__(self):
        libpath = f"{birdpath['appdir']}/c/libhx711.so"
        self.lib = ctypes.CDLL(libpath)

        self.lib.hx711_init.argtypes = [ctypes.c_int, ctypes.c_int]
        self.lib.hx711_read.restype = ctypes.c_long
        self.lib.hx711_close.restype = None

        ret = self.lib.hx711_init(hxDataPin, hxClckPin)
        if ret != 0:
            raise RuntimeError("HX711 init failed")

    def read(self):
        v = self.lib.hx711_read()
        if v == -9223372036854775808:
            raise RuntimeError("HX711 timeout")
        return v

    def close(self):
        self.lib.hx711_close()


# ============================================================
# SIMPLE MEDIAN FILTER (replaces moving_window everywhere)
# ============================================================

class MedianFilter:
    def __init__(self, size=3):
        self.buf = deque(maxlen=size)

    def update(self, sample: Sample):
        self.buf.append(sample.raw_sample)
        sample.raw = int(np.median(self.buf))

# ============================================================
# WATCHDOG (hardware integrity only)
# ============================================================

RAW_JUMP_LIMIT = 120000
RAW_ABS_LIMIT = 8_000_000
GLITCH_LIMIT = 5


class Watchdog:

    def __init__(self):
        self.last_raw = None
        self.glitch_count = 0

    def process(self, sample: Sample):

        sample.glitch = False
        sample.glitch_reason = ""

        raw = sample.raw_sample

        if abs(raw) > RAW_ABS_LIMIT:
            sample.glitch = True
            sample.glitch_reason = "ABS_LIMIT"

        if abs(sample.weight) > weightlimit:
            sample.glitch = True
            sample.glitch_reason = "WEIGHT_LIMIT"

        if self.last_raw is not None:
            if abs(raw - self.last_raw) > RAW_JUMP_LIMIT:
                sample.glitch = True
                sample.glitch_reason = "JUMP"

        self.last_raw = raw

        if sample.glitch:
            self.glitch_count += 1
        else:
            self.glitch_count = 0

        return self.glitch_count


# ============================================================
# BASELINE (offset + drift model)
# ============================================================

STARTUP_SETTLE_TIME = 1.2


class Baseline:

    def __init__(self, hx: HX711_CT):
        self.hx = hx
        self.offset = 0.0
        self.drift = 0.0

    # ---------------- startup calibration ----------------
    def startup(self, sample: Sample, n=60):

        ms.log("Startup zeroing...")

        time.sleep(STARTUP_SETTLE_TIME)

        vals = [self.hx.read() for _ in range(n)]
        self.offset = float(np.median(vals))
        self.drift = 0.0

        sample.offset = self.offset

        return self.offset

    # ---------------- convert raw → weight ----------------
    def process(self, sample: Sample):

        sample.offset = self.offset
        sample.weight = (sample.raw - self.offset) / hxScale

    # ---------------- drift correction ----------------
    def idle_update(self, sample: Sample):

        w = sample.weight

        # large disturbance → hard reset
        if abs(w) > 20:
            ms.log("Baseline hard reset")
            self.offset = sample.raw
            self.drift = 0.0
            return

        # EMA drift
        self.drift = 0.98 * self.drift + 0.02 * w

        if abs(self.drift) > 0.5:
            self.offset += self.drift * hxScale
            self.drift = 0.0

        sample.drift = self.drift
        sample.offset = self.offset

# ============================================================
# FSM (pure state machine, no I/O, no logging)
# ============================================================

STATE_IDLE = 0
STATE_ARRIVAL = 1
STATE_PRESENT = 2
STATE_DEPARTURE = 3
STATE_NAME = {
    0: "IDLE",
    1: "ARRIVAL",
    2: "PRESENT",
    3: "DEPARTURE"
}

class WeightFSM:

    def __init__(self):
        self.state = STATE_IDLE
        self.threshold_on = weightThreshold
        self.threshold_off = weightThreshold * 0.7  # hysteresis (IMPORTANT)

        self.stable_up = 0
        self.stable_down = 0
        self.peak = 0.0
        self.departure_t0 = 0.0

    def reset(self, keep_peak=True):
        self.stable_up = 0
        self.stable_down = 0

        if not keep_peak:
            self.peak = 0.0

    def process_weight(self, w: float, sample: Sample):

        sample.note = ""
        # ---------------- IDLE ----------------
        if self.state == STATE_IDLE:

            if w > self.threshold_on:
                self.stable_up += 1
                if self.stable_up >= 3:
                    self.state = STATE_ARRIVAL
                    self.reset()
                    self.peak = w
                    sample.note = "IDLE→ARRIVAL"
                    return "ARRIVAL"
            else:
                self.stable_up = 0

            return None

        # ---------------- ARRIVAL ----------------
        if self.state == STATE_ARRIVAL:

            self.peak = max(self.peak, w)

            if w > self.threshold_on:
                self.stable_up += 1
                if self.stable_up >= 5:
                    self.state = STATE_PRESENT
                    self.reset()                    
                    sample.note = "ARRIVAL→PRESENT"
                    return "PRESENT"
            else:
                self.stable_up = 0

            return None

        # ---------------- PRESENT ----------------
        if self.state == STATE_PRESENT:

            self.peak = max(self.peak, w)

            if w < self.threshold_off:
                self.stable_down += 1
                if self.stable_down >= 2:
                    self.state = STATE_DEPARTURE
                    self.reset()
                    self.departure_t0 = time.monotonic()
                    sample.note = "PRESENT→DEPARTURE"
                    return "DEPARTURE"
            else:
                self.stable_down = 0

            return None

        # ---------------- DEPARTURE ----------------
        if self.state == STATE_DEPARTURE:

            if time.monotonic() - self.departure_t0 > 2:
                self.state = STATE_IDLE
                self.reset(keep_peak=False)
                sample.note = "TIMEOUT→IDLE"
                return "IDLE"

            if w > self.threshold_on:
                self.state = STATE_ARRIVAL
                self.reset()
                self.peak = w
                sample.note = "DEPARTURE→ARRIVAL"
                return "ARRIVAL"

            return None

# ============================================================
# TRACE RECORDER (replaces CSV spam logging)
# ============================================================
def readable_time():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

import copy # real snapshot of Sample object, not reference

class TraceRecorder:

    def __init__(self, size_before=60):

        self.buffer = deque(maxlen=200)
        self.before = size_before
        self.event_id = 0

        self.file = os.path.join(
            birdpath["ramdisk"],
            "trace_events.csv"
        )

        # create header only for a new file
        if not os.path.exists(self.file):
            with open(self.file, "w") as f:
                f.write(
                    "event_id,event_time,reason,"
                    "t,raw,weight,offset,drift,"
                    "state,stable,peak,note\n"
                )


    def record(self, sample: Sample):

        # store a real snapshot, not a reference
        self.buffer.append(copy.deepcopy(sample))


    def dump_event(self, reason: str):

        self.event_id += 1

        event_time = readable_time()

        start = max(0, len(self.buffer) - self.before)

        snapshot = list(self.buffer)[start:]


        with open(self.file, "a", buffering=1) as f:

            for s in snapshot:

                f.write(
                    f"{self.event_id},"
                    f"{event_time},"
                    f"{reason},"
                    f"{s.t:.3f},"
                    f"{s.raw},"
                    f"{s.weight:.3f},"
                    f"{s.offset:.2f},"
                    f"{s.drift:.3f},"
                    f"{s.state},"
                    f"{s.stable},"
                    f"{s.peak:.2f},"
                    f"{s.note}\n"
                )

class SignalLogger:

    def __init__(self):

        self.file = os.path.join(
            birdpath["ramdisk"],
            f"signal_diag_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.csv"
        )

        with open(self.file, "w") as f:
            f.write(
                "time,mono_t,raw,filtered,weight,signal,var,mean,energy,state,event\n"
            )

    def update(
        self,
        sample,
        signal,
        var,
        mean,
        energy,
        state,
        event=""
    ):

        with open(self.file, "a", buffering=1) as f:
            f.write(
                f"{readable_time()},"
                f"{sample.t:.3f},"
                f"{sample.raw_sample},"
                f"{sample.raw},"
                f"{sample.weight:.3f},"
                f"{signal:.3f},"
                f"{var:.3f},"
                f"{mean:.3f},"
                f"{energy:.3f},"
                f"{state},"
                f"{event}\n"
            )
# ============================================================
# MAIN PROGRAM
# ============================================================

fifo = birdpath["fifo"]

if not fifoExists(fifo):
    os.mkfifo(fifo)
    ms.log("FIFO created")


def send_fifo(value):
    try:
        fd = os.open(fifo, os.O_WRONLY | os.O_NONBLOCK)
        with os.fdopen(fd, "w") as f:
            f.write(str(value) + "\n")
    except OSError as e:
        if e.errno != errno.ENXIO:
            raise


# ============================================================
# INIT
# ============================================================

ms.init()
ms.log(f"hxFiBirdStateCt2 start {time.ctime()}")

writePID(1)

hx = HX711_CT()

baseline = Baseline(hx)
fsm = WeightFSM()
watchdog = Watchdog()

trace = TraceRecorder()
signal_logger = SignalLogger()

median = MedianFilter(size=3)
sample = Sample()
baseline.startup(sample)

# ============================================================
# LOOP STATE
# ============================================================
stability_window = deque(maxlen=15)
energy_window = deque(maxlen=5)

try:
    while True:

        sample.t = time.monotonic()

        # ---------------- RAW ----------------
        try:
            sample.raw_sample = hx.read()
        except RuntimeError:
            ms.log("HX711 read error")
            time.sleep(0.15)
            continue

        # ---------------- FILTER ----------------
        median.update(sample)

        # ---------------- BASELINE ----------------
        baseline.process(sample)

        # ---------------- WATCHDOG ----------------
        glitches = watchdog.process(sample)

        if sample.glitch:
            ms.log(f"GLITCH: {sample.glitch_reason}")

            if glitches >= GLITCH_LIMIT:
                ms.log("HX711 reset")
                hx.close()
                time.sleep(1)

                hx = HX711_CT()
                baseline = Baseline(hx)
                baseline.startup(sample)

                watchdog = Watchdog()
                median = MedianFilter(size=3)

            time.sleep(0.15)
            continue

        # =========================================================
        # 1. PHYSICAL STABILITY MODEL (NEW CORE LAYER)
        # =========================================================
        weight = sample.weight

        stability_window.append(weight)

        if len(stability_window) == stability_window.maxlen:
            mean = np.mean(stability_window)
            var = np.var(stability_window)
        else:
            mean = weight
            var = 999.0

        # diagnostic only
        signal = weight

        # =========================================================
        # 2. Energy only for SignalLogger
        # =========================================================

        energy_window.append(mean)
        energy = np.mean([abs(x) for x in energy_window])
        # =========================================================
        # 3. FSM INPUT (ONLY CLEAN SIGNAL)
        # =========================================================

        event = fsm.process_weight(weight, sample)

        # synchronise Sample snapshot
        sample.state = fsm.state
        sample.peak = fsm.peak
        if fsm.state in (STATE_IDLE, STATE_ARRIVAL):
            sample.stable = fsm.stable_up
        elif fsm.state == STATE_PRESENT:
            sample.stable = fsm.stable_down
        else:
            sample.stable = 0

        signal_logger.update(
            sample,
            signal,
            var,
            mean,
            energy,
            STATE_NAME[fsm.state],
            event
        )

        trace.record(sample)
        if event is not None: 
            trace.dump_event(event)

        # ---------------- OUTPUT ----------------
        if event == "ARRIVAL":
            send_fifo(fsm.peak)

        elif event == "DEPARTURE":
            send_fifo(-1)

        ms.log(f"{weight:.2f} g {STATE_NAME[sample.state]}", terminal=False)

        # =========================================================
        # 4. DRIFT CONTROL (VERY STRICT NOW)
        # =========================================================
        '''
        if sample.state == STATE_IDLE and is_valid and is_quiet:

            # ultra-slow correction (wind-safe)
            baseline.drift = 0.997 * baseline.drift + 0.003 * mean

            # only correct if persistent bias exists
            if abs(baseline.drift) > 0.6:
                baseline.offset += baseline.drift * hxScale
                baseline.drift = 0.0
                sample.offset = baseline.offset
        '''
        time.sleep(0.15)
# ============================================================
# CLEAN EXIT
# ============================================================

except (KeyboardInterrupt, SystemExit):
    ms.log("shutdown hxFiBirdStateCt2")

finally:
    update_config_json({
        "hxOffset": baseline.offset,
        "hxScale": hxScale
    })

    hx.close()
    clearPID(1)

    ms.log(f"stopped {time.ctime()}")