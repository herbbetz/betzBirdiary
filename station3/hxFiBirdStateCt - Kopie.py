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
import sys
import errno

from sharedBird import fifoExists, writePID, clearPID
from configBird3 import (
    birdpath, hxDataPin, hxClckPin, hxScale, hxOffset,
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
    def startup(self, sample: Sample, n=60, previous_offset=None):

        ms.log("Startup zeroing...")

        time.sleep(STARTUP_SETTLE_TIME)

        vals = [self.hx.read() for _ in range(n)]
        measured_offset = float(np.median(vals))

        boot_load = False

        if previous_offset is not None:

            delta = (measured_offset - previous_offset) / hxScale

            if abs(delta) > weightThreshold:
                boot_load = True
                sample.note = "BOOT_LOAD_DETECTED"
                ms.log(f"Boot load detected: {delta:.1f}g")

        if boot_load and previous_offset is not None:
            self.offset = previous_offset
        else:
            self.offset = measured_offset

        self.drift = 0.0

        sample.offset = self.offset
        sample.raw_sample = int(measured_offset)
        sample.raw = sample.raw_sample
        sample.weight = (sample.raw - self.offset) / hxScale
        return boot_load

    # ---------------- convert raw → weight ----------------
    def process(self, sample):
        sample.offset = self.offset
        sample.weight = (sample.raw - self.offset) / hxScale
        sample.drift = self.drift

# ============================================================
# FSM (pure state machine, no I/O, no logging)
# ============================================================

STATE_IDLE = 0
STATE_ARRIVAL = 1
STATE_PRESENT = 2
STATE_DEPARTURE = 3
STATE_OVERSIZE = 4

STATE_NAME = {
    STATE_IDLE: "IDLE",
    STATE_ARRIVAL: "ARRIVAL",
    STATE_PRESENT: "PRESENT",
    STATE_DEPARTURE: "DEPARTURE",
    STATE_OVERSIZE: "OVERSIZE"
}


class WeightFSM:

    def __init__(self):

        self.state = STATE_IDLE

        self.threshold_on = weightThreshold
        self.threshold_off = weightThreshold * 0.7

        self.stable_up = 0
        self.stable_down = 0

        self.peak = 0.0
        self.departure_t0 = 0.0

    def reset(self, keep_peak=True):

        self.stable_up = 0
        self.stable_down = 0

        if not keep_peak:
            self.peak = 0.0

    def force_present(self, weight=0.0):
        self.state = STATE_PRESENT
        self.reset()
        self.peak = weight

    def process_weight(self, w: float, sample: Sample):

        sample.note = ""

        # -------------------------------------------------
        # IDLE
        # -------------------------------------------------
        if self.state == STATE_IDLE:

            if w > self.threshold_on:

                self.stable_up += 1

                if self.stable_up >= 3:

                    self.peak = w

                    if w > weightlimit:
                        self.state = STATE_OVERSIZE
                        self.reset()
                        sample.note = "IDLE→OVERSIZE"
                        return "OVERSIZE"

                    self.state = STATE_ARRIVAL
                    self.reset()
                    sample.note = "IDLE→ARRIVAL"
                    return "ARRIVAL"

            else:
                self.stable_up = 0

            return None

        # -------------------------------------------------
        # ARRIVAL
        # -------------------------------------------------
        if self.state == STATE_ARRIVAL:

            self.peak = max(self.peak, w)

            if self.peak > weightlimit:
                self.state = STATE_OVERSIZE
                self.reset()
                sample.note = "ARRIVAL→OVERSIZE"
                return "OVERSIZE"

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

        # -------------------------------------------------
        # PRESENT
        # -------------------------------------------------
        if self.state == STATE_PRESENT:

            self.peak = max(self.peak, w)

            if self.peak > weightlimit:
                self.state = STATE_OVERSIZE
                self.reset()
                sample.note = "PRESENT→OVERSIZE"
                return "OVERSIZE"

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

        # -------------------------------------------------
        # OVERSIZE
        # -------------------------------------------------
        if self.state == STATE_OVERSIZE:

            self.peak = max(self.peak, w)

            if w < self.threshold_off:

                self.stable_down += 1

                if self.stable_down >= 2:
                    self.state = STATE_DEPARTURE
                    self.reset()
                    self.departure_t0 = time.monotonic()
                    sample.note = "OVERSIZE→DEPARTURE"
                    return "DEPARTURE"

            else:
                self.stable_down = 0

            return None

        # -------------------------------------------------
        # DEPARTURE
        # -------------------------------------------------
        if self.state == STATE_DEPARTURE:

            if time.monotonic() - self.departure_t0 > 2:

                self.state = STATE_IDLE
                self.reset(keep_peak=False)
                sample.note = "TIMEOUT→IDLE"
                return "IDLE"

            if w > self.threshold_on:

                self.peak = w

                if w > weightlimit:
                    self.state = STATE_OVERSIZE
                    self.reset()
                    sample.note = "DEPARTURE→OVERSIZE"
                    return "OVERSIZE"

                self.state = STATE_ARRIVAL
                self.reset()
                sample.note = "DEPARTURE→ARRIVAL"
                return "ARRIVAL"

            return None
        
# ============================================================
# TRACE RECORDER (replaces CSV spam logging)
# ============================================================
def readable_time():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

class TraceRecorder:

    def __init__(self):

        self.event_id = 0

        self.file = os.path.join(
            birdpath["ramdisk"],
            "trace_events.csv"
        )

        if not os.path.exists(self.file):
            with open(self.file, "w") as f:
                f.write(
                    "event_id,time,reason,"
                    "weight,peak,state,note\n"
                )

    def dump_event(self, reason: str, sample: Sample):

        self.event_id += 1

        with open(self.file, "a", buffering=1) as f:

            f.write(
                f"{self.event_id},"
                f"{readable_time()},"
                f"{reason},"
                f"{sample.weight:.2f},"
                f"{sample.peak:.2f},"
                f"{STATE_NAME[sample.state]},"
                f"{sample.note}\n"
            )

class SignalLogger:

    def __init__(self, seconds=3, sample_time=0.15):

        self.samples_before = int(seconds / sample_time)
        self.samples_after = int(seconds / sample_time)

        self.buffer = deque(maxlen=self.samples_before)

        self.active = False
        self.after_counter = 0
        self.event_buffer = []

        self.file = os.path.join(
            birdpath["ramdisk"],
            f"signal_diag_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.csv"
        )

        with open(self.file, "w") as f:
            f.write(
                "time,mono_t,raw,filtered,weight,"
                "signal,var,mean,energy,state,event\n"
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

        row = (
            readable_time(),
            sample.t,
            sample.raw_sample,
            sample.raw,
            sample.weight,
            signal,
            var,
            mean,
            energy,
            state,
            event
        )

        # keep rolling history
        self.buffer.append(row)

        # first transition starts recording
        if event and not self.active:

            self.active = True
            self.after_counter = self.samples_after

            # copy pre-history
            self.event_buffer = list(self.buffer)

        # append post-history
        if self.active:

            self.event_buffer.append(row)
            self.after_counter -= 1

            if self.after_counter <= 0:
                self.write_event()
                self.active = False
                self.event_buffer = []

    def write_event(self):

        with open(self.file, "a", buffering=1) as f:

            for r in self.event_buffer:

                f.write(
                    f"{r[0]},"
                    f"{r[1]:.3f},"
                    f"{r[2]},"
                    f"{r[3]},"
                    f"{r[4]:.3f},"
                    f"{r[5]:.3f},"
                    f"{r[6]:.3f},"
                    f"{r[7]:.3f},"
                    f"{r[8]:.3f},"
                    f"{r[9]},"
                    f"{r[10]}\n"
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
ms.log(f"{sys.argv[0]} start {time.ctime()}")

writePID(1)

hx = HX711_CT()

baseline = Baseline(hx)
watchdog = Watchdog()

trace = TraceRecorder()

median = MedianFilter(size=3)
signal_logger = SignalLogger()

sample = Sample()

boot_load = baseline.startup(sample, previous_offset=hxOffset)
fsm = WeightFSM()
if boot_load:
    fsm.force_present(sample.weight)
    sample.note = "BOOT_LOAD_DETECTED"
else:
    sample.note = "BOOT_ZERO"

# baseline.process(sample)
sample.state = fsm.state
sample.peak = fsm.peak
trace.dump_event("BOOT", sample)

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
                old_offset = baseline.offset # store old offset before reset
                ms.log("HX711 reset")
                hx.close()
                time.sleep(1)

                hx = HX711_CT()
                baseline = Baseline(hx)
                fsm = WeightFSM()
                boot_load = baseline.startup(sample, previous_offset=old_offset)

                watchdog = Watchdog()
                if boot_load:
                    fsm.force_present(sample.weight)
                    sample.note = "RESET_LOAD_DETECTED"
                else:
                    sample.note = "RESET_ZERO"
                sample.state = fsm.state
                sample.peak = fsm.peak
                sample.raw_sample = 0
                sample.raw = 0
                sample.weight = 0
                sample.stable = 0
                trace.dump_event("RESET", sample)

                median = MedianFilter(size=3)
                signal_logger = SignalLogger()
                stability_window.clear()
                energy_window.clear()

            time.sleep(0.15)
            continue

        # =========================================================
        # 1. PHYSICAL STABILITY MODEL (NEW CORE LAYER)
        # =========================================================
        weight = sample.weight
        signal = sample.weight

        stability_window.append(weight)

        if len(stability_window) == stability_window.maxlen:
            mean = np.mean(stability_window)
            var = np.var(stability_window)
        else:
            mean = weight
            var = None

        # =========================================================
        # 2. Energy only for SignalLogger
        # =========================================================

        energy_window.append(weight - mean)
        energy = np.mean([abs(x) for x in energy_window])
        # =========================================================
        # 3. FSM INPUT (ONLY CLEAN SIGNAL)
        # =========================================================

        event = fsm.process_weight(mean, sample)

        # synchronise Sample snapshot
        sample.state = fsm.state
        sample.peak = fsm.peak
        if fsm.state in (STATE_IDLE, STATE_ARRIVAL):
            sample.stable = fsm.stable_up
        elif fsm.state in (STATE_PRESENT, STATE_OVERSIZE):
            sample.stable = fsm.stable_down
        else:
            sample.stable = 0

        signal_logger.update(
            sample,
            weight,
            var,
            mean,
            energy,
            STATE_NAME[fsm.state],
            event
        )

        if event is not None:
            trace.dump_event(event, sample)

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