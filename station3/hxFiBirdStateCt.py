"""
hxFiBirdStateCt.py

HX711 -> Sample -> Baseline -> FSM -> Recorders

Only physical quantities:
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

WEIGHTTHRESHOLD_off = 0.7 * weightThreshold

@dataclass
class Sample:

    t: float = 0.0

    raw_sample: int = 0
    raw: int = 0

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

STARTUP_SETTLE_TIME = 5.0
STARTUP_SAMPLES = 60
STARTUP_SPREAD_LIMIT = 2000   # HX711 raw units, tune on hardware

OFFSET_STEP = 0.005
OFFSET_PERIOD = 200


class Baseline:

    def __init__(self, hx: HX711_CT):
        self.hx = hx
        self.offset = 0.0
        self.count = 0
        self.idle_bad_count = 0 # weight far from zero while state IDLE

    # --------------------------------------------------------
    # startup calibration
    # --------------------------------------------------------
    def startup(self, sample: Sample):

        ms.log("Startup zeroing...")

        time.sleep(STARTUP_SETTLE_TIME)

        t0 = time.monotonic()
        attempts = 0
        maxspread = 0

        while True:

            values = [
                self.hx.read()
                for _ in range(STARTUP_SAMPLES)
            ]

            spread = max(values) - min(values)
            attempts += 1
            maxspread = max(maxspread, spread)

            if spread <= STARTUP_SPREAD_LIMIT:
                break

            ms.log(
                f"Startup unstable spread={spread}"
            )
            time.sleep(0.5)

        self.offset = float(
            np.median(values)
        )

        sample.offset = self.offset
        sample.weight = 0.0

        sample.startup_spread = spread
        sample.startup_attempts = attempts
        sample.startup_maxspread = maxspread
        sample.startup_delay = time.monotonic() - t0
        sample.note = (
            f"STARTUP_ZERO "
            f"spread={spread} "
            f"attempts={attempts}"
        )
        ms.log(
            f"Startup accepted spread={spread}"
        )

        return True

    # --------------------------------------------------------
    # normal measurement conversion
    # --------------------------------------------------------
    def process(self, sample: Sample):

        sample.offset = self.offset
        sample.weight = (
            sample.raw - self.offset
        ) / hxScale
    # --------------------------------------------------------
    # connect Baseline and FSM IDLE in main():
    # --------------------------------------------------------
    def supervise(self, sample, idle=False):
        if not idle:
            self.idle_bad_count = 0
            return

        if abs(sample.weight) > WEIGHTTHRESHOLD_off: # large deviation of IDLE weight

            self.idle_bad_count += 1
            if self.idle_bad_count > 20:
                self.offset = sample.raw
                sample.offset = self.offset
                sample.weight = 0.0

                self.count = 0
                self.idle_bad_count = 0
                sample.note = "BASELINE_RESET"
        else:                                       # small deviation of IDLE weight
            self.idle_bad_count = 0
            self.adapt_offset(sample)
    # --------------------------------------------------------
    # slowly follow long-term zero drift
    # --------------------------------------------------------
    def adapt_offset(self, sample):

        self.count += 1

        if self.count < OFFSET_PERIOD:
            return

        self.count = 0

        self.offset += (
            sample.raw - self.offset
        ) * OFFSET_STEP

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
CAMERA_DELAY = 1.0 # 1 sec for the bird to sit before calling the camera by fifo

class WeightFSM:

    def __init__(self):

        self.state = STATE_IDLE

        self.threshold_on = weightThreshold
        self.threshold_off = WEIGHTTHRESHOLD_off

        # consecutive samples above/below threshold
        self.above_count = 0 # count consecutive measurements above arrival threshold
        self.below_count = 0 # count consecutive measurements below departure threshold

        self.peak = 0.0
        self.departure_t0 = 0.0

        self.present_t0 = 0.0
        self.camera_sent = False

    def reset(self, keep_peak=True):

        self.above_count = 0
        self.below_count = 0

        if not keep_peak:
            self.peak = 0.0


    def force_present(self, weight=0.0):

        self.state = STATE_PRESENT
        self.reset(keep_peak=False)
        self.peak = weight


    def _transition(
        self,
        new_state,
        sample,
        note,
        keep_peak=True,
        departure=False
    ):

        self.state = new_state
        self.reset(keep_peak=keep_peak)

        if new_state == STATE_PRESENT:
            self.present_t0 = time.monotonic()
            self.camera_sent = False

        if departure:
            self.departure_t0 = time.monotonic()

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

    # --------------------------------------------------------
    # main FSM entry
    # --------------------------------------------------------

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


    # --------------------------------------------------------
    # IDLE
    # --------------------------------------------------------

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


    # --------------------------------------------------------
    # ARRIVAL
    # --------------------------------------------------------

    def state_arrival(self, weight, sample):

        self.peak = max(
            self.peak,
            weight
        )

        # weight disappeared again:
        # cancel arrival, do not stay in ARRIVAL
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

        if self.above_count >= 5:

            return self._transition(
                STATE_PRESENT,
                sample,
                "ARRIVAL→PRESENT"
            )

        return None


    # --------------------------------------------------------
    # PRESENT
    # --------------------------------------------------------

    def state_present(self, weight, sample):

        self.peak = max(
            self.peak,
            weight
        )

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


    # --------------------------------------------------------
    # OVERSIZE
    # --------------------------------------------------------

    def state_oversize(self, weight, sample):

        self.peak = max(
            self.peak,
            weight
        )

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


    # --------------------------------------------------------
    # DEPARTURE
    # --------------------------------------------------------

    def state_departure(self, weight, sample):

        if time.monotonic() - self.departure_t0 > 2:

            return self._transition(
                STATE_IDLE,
                sample,
                "TIMEOUT→IDLE",
                keep_peak=False
            )

        # bird returns before departure completed

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
# Recorders (may need external analysis tools): SignalLogger, TraceRecorder
# ============================================================
def readable_time():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

class SignalLogger:

    def __init__(self):

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
            f.write(
                "time,mono_t,raw,offset,weight,state,event,peak,note\n"
            )

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
                f"{sample.startup_delay:.2f}\n"     )

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
ms.log(f"{sys.argv[0]} start {time.ctime()}")

writePID(1)

hx = HX711_CT()

sample = Sample()

baseline = Baseline(hx)

baseline.startup(sample)

median = MedianFilter()

fsm = WeightFSM()

signal_logger = SignalLogger()

trace = TraceRecorder()

trace.dump_event(
    "BOOT",
    sample
)

# ============================================================
# MAIN LOOP
# ============================================================
try:

    while True:

        sample.t = time.monotonic()

        # 1. raw measurement
        sample.raw_sample = hx.read()

        # 2. remove single raw peaks
        median.update(sample)

        # 3. raw -> weight
        baseline.process(sample)

        # 4. state decision
        event = fsm.process_weight(
            sample.weight,
            sample
        )

        sample.state = fsm.state
        sample.peak = fsm.peak
        # 5. baseline supervision, not zeroing baseline outside of STATE IDLE
        baseline.supervise(
            sample,
            idle=(fsm.state == STATE_IDLE)
        )
        if sample.note == "BASELINE_RESET":
            trace.dump_event("BASELINE_RESET", sample)
            ms.log("BASELINE_RESET")
            sample.note = ""

        # 6. record everything
        signal_logger.log(
            sample,
            event
        )
        if event:
            trace.dump_event(
                event,
                sample
            )

        # 7. communicate event
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