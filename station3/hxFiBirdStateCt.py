"""
hxFiBirdStateCt.py

HX711 -> Sample -> Baseline -> FSM -> Recorders

Core physical quantities:
    raw
    offset
    weight

No signal, energy, stability models.

- old hxOffset and thereby BOOT_LOAD_DETECT not suitable. By environment hxOffset can vary more than a bird weight.
- SignalLogger output processed offline by hx_signalanalyzer.py
- later: cmd line arg "test" to activate SignalLogger and TraceRecorder only for debugging
"""
from dataclasses import dataclass
from collections import deque
from datetime import datetime
import time
import os
import sys
import errno
import ctypes
import numpy as np

from sharedBird import fifoExists, writePID, clearPID
from configBird3 import (
    birdpath, hxDataPin, hxClckPin, hxScale,
    weightThreshold, weightlimit,
    update_config_json
)
import msgBird as ms
testmode = False
WEIGHTTHRESHOLD_off = 0.7 * weightThreshold

@dataclass
class Sample:

    t: float = 0.0

    raw_sample: int = 0
    raw: int = 0
    raw_delta: int = 0

    offset: float = 0.0
    weight: float = 0.0

    state: int = 0
    peak: float = 0.0

    startup_spread: int = 0
    startup_attempts: int = 0
    startup_maxspread: int = 0
    startup_delay: float = 0.0

    note: str = ""

# ============================================================
# HX711 DRIVER
# ============================================================

class HX711_CT:
    def __init__(self):
        global testmode
        if testmode:
            libpath = f"{birdpath['appdir']}/c/libhx711_debug.so"
        else: libpath = f"{birdpath['appdir']}/c/libhx711.so"
        self.lib = ctypes.CDLL(libpath)

        self.lib.hx711_init.argtypes = [ctypes.c_int, ctypes.c_int]
        self.lib.hx711_read.restype = ctypes.c_int64
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
# SIMPLE MEDIAN FILTER
# ============================================================

class MedianFilter:
    def __init__(self, size=7):
        self.buf = deque(maxlen=size)

    def update(self, sample: Sample):
        self.buf.append(sample.raw_sample)
        sample.raw = int(np.median(self.buf))

# ============================================================
# BASELINE (offset management and raw → weight conversion)
# ============================================================

STARTUP_SETTLE_TIME = 2.0
STABLE_SAMPLES = 60
STABLE_SPREAD_LIMIT = 10000
STARTUP_MAX_TIME = 30.0
OFFSET_ALPHA = 0.0025
class Baseline:
    def __init__(self, hx: HX711_CT):
        self.hx = hx
        self.offset = 0.0
        self.stable_buf = deque(maxlen=STABLE_SAMPLES)
    def update_stable_buffer(self, raw):
        self.stable_buf.append(raw)
    def stable_raw(self):
        if len(self.stable_buf) < STABLE_SAMPLES:
            return None
        values = np.array(self.stable_buf)
        p10, p90 = np.percentile(values, [10, 90])
        spread = p90 - p10
        if spread > STABLE_SPREAD_LIMIT:
            return None
        return float(np.median(values))
    def stable_spread(self):
        if len(self.stable_buf) == 0:
            return 0
        values = np.array(self.stable_buf)
        p10, p90 = np.percentile(values, [10, 90])
        return p90 - p10
    def startup(self, sample):
        time.sleep(STARTUP_SETTLE_TIME)
        ms.log("Startup zeroing...")
        t0 = time.monotonic()
        attempts = 0
        self.stable_buf.clear()
        while time.monotonic() - t0 < STARTUP_MAX_TIME:
            raw = self.hx.read()
            self.update_stable_buffer(raw)
            attempts += 1
            raw_value = self.stable_raw()
            if raw_value is not None:
                self.offset = raw_value
                sample.offset = self.offset
                sample.weight = 0.0
                sample.startup_spread = self.stable_spread()
                sample.startup_attempts = attempts
                sample.startup_maxspread = STABLE_SPREAD_LIMIT
                sample.startup_delay = time.monotonic() - t0
                sample.note = f"STARTUP_ZERO spread={sample.startup_spread:.0f}"
                ms.log(sample.note)
                return True
            time.sleep(0.02)
        raise RuntimeError("HX711 startup did not stabilize")
    def process(self, sample):
        sample.offset = self.offset
        sample.weight = (sample.raw - self.offset) / hxScale
    def follow_idle(self, sample):
        self.offset += (sample.raw - self.offset) * OFFSET_ALPHA
    def adopt_raw_value(self, raw_value, sample):
        self.offset = raw_value
        self.stable_buf.clear()
        sample.offset = self.offset
        sample.weight = 0.0
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
CAMERA_DELAY = 2.0
ARRIVAL_CONFIRM_SAMPLES = 10
STATE_TIMEOUT = 300.0

class WeightFSM:
    def __init__(self):
        self.state = STATE_IDLE
        self.state_t0 = time.monotonic()
        self.threshold_on = weightThreshold
        self.threshold_off = WEIGHTTHRESHOLD_off
        self.above_count = 0
        self.below_count = 0
        self.peak = 0.0
        self.departure_t0 = 0.0
        self.present_t0 = 0.0
        self.camera_sent = False

    def reset(self, keep_peak=True):
        self.above_count = 0
        self.below_count = 0
        if not keep_peak:
            self.peak = 0.0

    def force_idle(self):
        self.state = STATE_IDLE
        self.state_t0 = time.monotonic()
        self.reset(keep_peak=False)
        self.camera_sent = False

    def _transition(self, new_state, sample, note, keep_peak=True, departure=False):
        self.state = new_state
        self.state_t0 = time.monotonic()
        self.reset(keep_peak=keep_peak)
        if new_state == STATE_PRESENT:
            self.present_t0 = self.state_t0
            self.camera_sent = False
        if departure:
            self.departure_t0 = self.state_t0
        sample.note = note
        return STATE_NAME[new_state]

    def camera_trigger(self):
        if self.state != STATE_PRESENT:
            return False
        if self.camera_sent:
            return False
        if time.monotonic() - self.present_t0 < CAMERA_DELAY:
            return False
        self.camera_sent = True
        return True

    def check_timeout(self, sample, baseline):
        # Only stable states can become the new IDLE.
        if self.state in (STATE_ARRIVAL, STATE_PRESENT, STATE_DEPARTURE):
            if time.monotonic() - self.state_t0 > STATE_TIMEOUT:
                raw_value = baseline.stable_raw()
                if raw_value is not None:
                    old_state = STATE_NAME[self.state]
                    baseline.adopt_raw_value(raw_value, sample)
                    self.force_idle()
                    sample.note = f"STATE_TIMEOUT {old_state} → IDLE"
                    return "STATE_TIMEOUT"
            return None

        # IDLE may reset its baseline if it has drifted away.
        if self.state == STATE_IDLE:
            if abs(sample.weight) > WEIGHTTHRESHOLD_off:
                raw_value = baseline.stable_raw()
                if raw_value is not None:
                    baseline.adopt_raw_value(raw_value, sample)
                    self.reset(keep_peak=False)
                    sample.note = "IDLE_BASELINE_RESET"
                    return "IDLE_BASELINE_RESET"
            return None

        # OVERSIZE: never auto-calibrate.
        return None

    def process_weight(self, weight, sample):
        sample.note = ""
        if self.state == STATE_IDLE:
            return self.state_idle(weight, sample)
        if self.state == STATE_ARRIVAL:
            return self.state_arrival(weight, sample)
        if self.state == STATE_PRESENT:
            return self.state_present(weight, sample)
        if self.state == STATE_DEPARTURE:
            return self.state_departure(weight, sample)
        if self.state == STATE_OVERSIZE:
            return self.state_oversize(weight, sample)
        return None

    def state_idle(self, weight, sample):
        if weight > self.threshold_on:
            self.above_count += 1
            if self.above_count >= 3:
                self.peak = weight
                if weight > weightlimit:
                    return self._transition(
                        STATE_OVERSIZE,
                        sample,
                        "IDLE→OVERSIZE"
                    )
                return self._transition(
                    STATE_ARRIVAL,
                    sample,
                    "IDLE→ARRIVAL"
                )
        else:
            self.above_count = 0
        return None

    def state_arrival(self, weight, sample):
        self.peak = max(self.peak, weight)
        if weight < self.threshold_off:
            return self._transition(
                STATE_IDLE,
                sample,
                "ARRIVAL_CANCELLED",
                keep_peak=False
            )
        if self.peak > weightlimit:
            return self._transition(
                STATE_OVERSIZE,
                sample,
                "ARRIVAL→OVERSIZE"
            )
        self.above_count += 1
        if (self.above_count >= ARRIVAL_CONFIRM_SAMPLES
            and self.peak > weightThreshold + 2.0):
            return self._transition(
                STATE_PRESENT,
                sample,
                "ARRIVAL→PRESENT"
            )
        return None

    def state_present(self, weight, sample):
        self.peak = max(self.peak, weight)
        if self.peak > weightlimit:
            return self._transition(
                STATE_OVERSIZE,
                sample,
                "PRESENT→OVERSIZE"
            )
        if weight < self.threshold_off:
            self.below_count += 1
            if self.below_count >= 2:
                return self._transition(
                    STATE_DEPARTURE,
                    sample,
                    "PRESENT→DEPARTURE",
                    departure=True
                )
        else:
            self.below_count = 0
        return None

    def state_oversize(self, weight, sample):
        self.peak = max(self.peak, weight)
        if weight < self.threshold_off:
            self.below_count += 1
            if self.below_count >= 2:
                return self._transition(
                    STATE_DEPARTURE,
                    sample,
                    "OVERSIZE→DEPARTURE",
                    departure=True
                )
        else:
            self.below_count = 0
        return None

    def state_departure(self, weight, sample):
        if time.monotonic() - self.departure_t0 > 2:
            return self._transition(
                STATE_IDLE,
                sample,
                "TIMEOUT→IDLE",
                keep_peak=False
            )
        if weight > self.threshold_on:
            self.peak = weight
            if weight > weightlimit:
                return self._transition(
                    STATE_OVERSIZE,
                    sample,
                    "DEPARTURE→OVERSIZE"
                )
            return self._transition(
                STATE_ARRIVAL,
                sample,
                "DEPARTURE→ARRIVAL"
            )
        return None
# ============================================================
# Recorders (may need external analysis tools): SignalLogger, TraceRecorder, NullRecorder
# ============================================================
def readable_time():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

class SignalLogger:
    def __init__(self, sample):
        self.file = os.path.join(
            birdpath["ramdisk"],
            f"signal_{datetime.now():%Y-%m-%d_%H-%M-%S}.csv"
        )
        with open(self.file, "w") as f:
            f.write("# weightThreshold={}\n".format(weightThreshold))
            f.write("# threshold_off={:.2f}\n".format(WEIGHTTHRESHOLD_off))
            f.write("# hxScale={}\n".format(hxScale))
            f.write("# startup_offset={:.1f}\n".format(sample.offset))
            f.write("# startup_note={}\n".format(sample.note))
            f.write("# startup_spread={}\n".format(sample.startup_spread))
            f.write("# startup_attempts={}\n".format(sample.startup_attempts))
            f.write("# startup_maxspread={}\n".format(sample.startup_maxspread))
            f.write("# startup_delay={:.2f}\n".format(sample.startup_delay))
            f.write("time,mono_t,raw,offset,weight,state,event,peak,note\n")
    def log(self, sample, event=""):
        with open(self.file, "a", buffering=1) as f:
            f.write(
                f"{readable_time()},"
                f"{sample.t:.3f},"
                f"{sample.raw_sample},"
                f"{sample.offset:.2f},"
                f"{sample.weight:.3f},"
                f"{STATE_NAME[sample.state]},"
                f"{event},"
                f"{sample.peak:.3f},"
                f"{sample.note}\n"
            )

class TraceRecorder:
    def __init__(self):
        self.event_id = 0
        self.raw_jump_count = 0
        self.raw_jump_events = 0
        self.file = os.path.join(
            birdpath["ramdisk"],
            "trace_events.csv"
        )
        if not os.path.exists(self.file):
            with open(self.file, "w") as f:
                f.write(
                    "event_id,time,reason,"
                    "weight,peak,state,note,"
                    "offset,startup_spread,"
                    "startup_attempts,"
                    "startup_maxspread,"
                    "startup_delay\n"
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
                f"{sample.note},"
                f"{sample.offset:.1f},"
                f"{sample.startup_spread},"
                f"{sample.startup_attempts},"
                f"{sample.startup_maxspread},"
                f"{sample.startup_delay:.2f}\n"
            )

    def dump_raw_jump(self, sample: Sample, previous_raw: int):
        self.event_id += 1
        self.raw_jump_events += 1
        with open(self.file, "a", buffering=1) as f:
            f.write(
                f"{self.event_id},"
                f"{readable_time()},"
                f"HX711_RAW_JUMP,"
                f"{sample.weight:.2f},"
                f"{sample.peak:.2f},"
                f"{STATE_NAME[sample.state]},"
                f"before={previous_raw} "
                f"after={sample.raw_sample} "
                f"filtered={sample.raw} "
                f"delta={sample.raw_delta},"
                f"{sample.offset:.1f},"
                f"{sample.startup_spread},"
                f"{sample.startup_attempts},"
                f"{sample.startup_maxspread},"
                f"{sample.startup_delay:.2f}\n"
            )

class NullRecorder:
    def __init__(self):
        self.raw_jump_count = 0 # is used here: 'trace.raw_jump_count += 1'
        self.raw_jump_events = 0
    # functions of TraceRecorder:
    def dump_event(self, *args, **kwargs):
        pass
    def dump_raw_jump(self,*args,**kwargs):
        pass
    # functions of SignalLogger:
    def log(self, *args, **kwargs):
        pass
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
# INITIALIZATION
# ============================================================

ms.init()

if len(sys.argv) > 1 and sys.argv[1] == "test":
    testmode = True
    ms.log(f"Testmode of {sys.argv[0]}")
else:
    ms.log(sys.argv[0])
ms.log(f"... starting at {time.ctime()}")
# ms.log(f"... starting at {datetime.now()}")

writePID(1)
hx = HX711_CT()
sample = Sample()
baseline = Baseline(hx)
baseline.startup(sample)
median = MedianFilter()
for value in baseline.stable_buf:
    median.buf.append(int(value))
fsm = WeightFSM()

if testmode:
    signal_logger = SignalLogger(sample)
    trace = TraceRecorder()
else:
    signal_logger = NullRecorder()
    trace = NullRecorder()

trace.dump_event(
    "BOOT",
    sample
)

# ============================================================
# MAIN LOOP
# ============================================================

last_raw_sample = None

try:
    while True:

        sample.t = time.monotonic()

        sample.raw_sample = hx.read()

        median.update(sample)

        baseline.process(sample)

        event = fsm.process_weight(
            sample.weight,
            sample
        )

        sample.state = fsm.state
        sample.peak = fsm.peak

        if fsm.state == STATE_IDLE:
            if abs(sample.weight) < WEIGHTTHRESHOLD_off:
                baseline.update_stable_buffer(sample.raw)
                baseline.follow_idle(sample)

        timeout_event = fsm.check_timeout(
            sample,
            baseline
        )

        if timeout_event:
            event = timeout_event


        signal_logger.log(sample,event)

        if event:
            trace.dump_event(event,sample)


        if fsm.camera_trigger():
            send_fifo(sample.peak)

        elif event == "DEPARTURE":
            send_fifo(-1)

        ms.log(
            f"{sample.weight:.2f} g "
            f"{STATE_NAME[sample.state]}",
            terminal=False
        )
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