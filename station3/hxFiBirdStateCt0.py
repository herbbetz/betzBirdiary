"""
hxFiBirdStateCt.py

Purpose
-------
Read the HX711 load cell and generate reliable bird arrival/departure events.

Processing pipeline
-------------------
HX711_CT
    acquire raw ADC value

MedianFilter
    suppress single-sample spikes

Baseline
    convert filtered ADC value into weight

Watchdog
    detect hardware communication faults

WeightFSM
    determine object state

        IDLE
          ↓
      ARRIVAL
          ↓
      PRESENT
          ↓
     DEPARTURE
          ↓
        IDLE

        or

      OVERSIZE
          ↓
     DEPARTURE

TraceRecorder
    permanently log boot, reset and state transitions

SignalLogger
    temporarily save measurements before and after transitions
    for diagnostic analysis

Design rules
------------
• Sample is the only data object exchanged between modules.
• Modules modify only their own fields.
• Recorders never influence measurements or decisions.
• The main loop contains only the processing sequence.
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

    raw_sample: int = 0
    raw: int = 0

    offset: float = 0.0
    weight: float = 0.0
    drift: float = 0.0

    state: int = 0  # STATE_IDLE
    stable: int = 0
    peak: float = 0.0

    glitch: bool = False
    glitch_reason: str = ""

    note: str = ""

    def update_from_fsm(self, fsm):
        self.state = fsm.state
        self.peak = fsm.peak

        if fsm.state in (STATE_IDLE, STATE_ARRIVAL):
            self.stable = fsm.stable_up

        elif fsm.state in (STATE_PRESENT, STATE_OVERSIZE):
            self.stable = fsm.stable_down

        else:
            self.stable = 0

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
    def __init__(self, size=7):
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
# BASELINE (offset management and raw → weight conversion)
# ============================================================
STARTUP_SETTLE_TIME = 1.2


class Baseline:
    """
    Maintains the zero reference (offset).

    startup()
        determine initial offset while preserving an existing
        bird already sitting on the balance.

    process()
        convert filtered ADC values into weight.
    """

    def __init__(self, hx: HX711_CT):

        self.hx = hx

        self.offset = 0.0
        self.drift = 0.0

    # --------------------------------------------------------
    # startup calibration
    # --------------------------------------------------------

    def startup(
        self,
        sample: Sample,
        previous_offset=None,
        n=60
    ):

        ms.log("Startup zeroing...")

        time.sleep(STARTUP_SETTLE_TIME)

        values = [self.hx.read() for _ in range(n)]
        measured_offset = float(np.median(values))

        boot_load = False

        if previous_offset is not None:

            delta = (
                measured_offset - previous_offset
            ) / hxScale

            if abs(delta) > weightThreshold:

                boot_load = True

                ms.log(
                    f"Boot load detected: {delta:.1f} g"
                )

        if boot_load:
            self.offset = previous_offset
            sample.note = "BOOT_LOAD_DETECTED"

        else:
            self.offset = measured_offset
            sample.note = ""

        self.drift = 0.0

        sample.offset = self.offset
        sample.raw_sample = int(measured_offset)
        sample.raw = sample.raw_sample
        sample.weight = (
            sample.raw - self.offset
        ) / hxScale
        sample.drift = self.drift

        return boot_load

    # --------------------------------------------------------
    # normal operation
    # --------------------------------------------------------

    def process(self, sample: Sample):

        sample.offset = self.offset
        sample.weight = (
            sample.raw - self.offset
        ) / hxScale
        sample.drift = self.drift

# ============================================================
# STABILITY MODEL
#
# Converts the physical weight signal into a stable FSM input.
#
# Input:
#     sample.weight
#
# Output:
#     mean   -> cleaned weight for FSM
#     var    -> signal variation
#     energy -> short term movement indicator
#
# No decisions are made here.
# ============================================================

class StabilityModel:

    def __init__(
        self,
        stability_size=15,
        energy_size=5
    ):

        # history for stable weight calculation
        self.stability_window = deque(
            maxlen=stability_size
        )

        # history for movement calculation
        self.energy_window = deque(
            maxlen=energy_size
        )


    def process(self, sample: Sample):

        weight = sample.weight

        self.stability_window.append(weight)

        if len(self.stability_window) == self.stability_window.maxlen:

            mean = np.mean(
                self.stability_window
            )

            var = np.var(
                self.stability_window
            )

        else:

            mean = weight
            var = None


        self.energy_window.append(
            weight - mean
        )

        energy = np.mean(
            [
                abs(x)
                for x in self.energy_window
            ]
        )


        return (
            mean,
            var,
            energy
        )
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
        self.reset(keep_peak=False)
        self.peak = weight

    # =======================================================
    # public entry
    # =======================================================

    def process_weight(self, w, sample):

        sample.note = ""

        if self.state == STATE_IDLE:
            return self.state_idle(w, sample)

        if self.state == STATE_ARRIVAL:
            return self.state_arrival(w, sample)

        if self.state == STATE_PRESENT:
            return self.state_present(w, sample)

        if self.state == STATE_OVERSIZE:
            return self.state_oversize(w, sample)

        if self.state == STATE_DEPARTURE:
            return self.state_departure(w, sample)

        return None

    def _transition(self, new_state, sample: Sample, note,
                    keep_peak=True, departure=False):

        self.state = new_state
        self.reset(keep_peak=keep_peak)

        if departure:
            self.departure_t0 = time.monotonic()

        sample.note = note

        return STATE_NAME[new_state]    

    def state_idle(self, w, sample):

        if w > self.threshold_on:

            self.stable_up += 1

            if self.stable_up >= 3:

                self.peak = w

                if w > weightlimit:
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
            self.stable_up = 0

        return None

    def state_arrival(self, w, sample):

        self.peak = max(self.peak, w)

        if self.peak > weightlimit:
            return self._transition(
                STATE_OVERSIZE,
                sample,
                "ARRIVAL→OVERSIZE"
            )

        if w > self.threshold_on:

            self.stable_up += 1

            if self.stable_up >= 5:

                return self._transition(
                    STATE_PRESENT,
                    sample,
                    "ARRIVAL→PRESENT"
                )

        else:
            self.stable_up = 0

        return None
    
    def state_present(self, w, sample):

        self.peak = max(self.peak, w)

        if self.peak > weightlimit:
            return self._transition(
                STATE_OVERSIZE,
                sample,
                "PRESENT→OVERSIZE"
            )

        if w < self.threshold_off:

            self.stable_down += 1

            if self.stable_down >= 2:
                return self._transition(
                    STATE_DEPARTURE,
                    sample,
                    "PRESENT→DEPARTURE",
                    departure=True
                )

        else:
            self.stable_down = 0

        return None

    def state_oversize(self, w, sample):

        self.peak = max(self.peak, w)

        if w < self.threshold_off:

            self.stable_down += 1

            if self.stable_down >= 2:
                return self._transition(
                    STATE_DEPARTURE,
                    sample,
                    "OVERSIZE→DEPARTURE",
                    departure=True
                )

        else:
            self.stable_down = 0

        return None

    def state_departure(self, w, sample):

        if time.monotonic() - self.departure_t0 > 2:

            return self._transition(
                STATE_IDLE,
                sample,
                "TIMEOUT→IDLE",
                keep_peak=False
            )

        if w > self.threshold_on:

            self.peak = w

            if w > weightlimit:
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

    def __init__(self):

        self.file = os.path.join(
            birdpath["ramdisk"],
            f"signal_{datetime.now():%Y-%m-%d_%H-%M-%S}.csv"
        )

        with open(self.file, "w") as f:
            f.write(
                "time,mono_t,raw,offset,weight,state,event,peak,note\n"
            )


    def update(
        self,
        sample,
        *args,
        **kwargs
    ):
        """
        Compatibility wrapper.

        Old calls supplied:
            weight,
            var,
            mean,
            energy,
            state,
            event

        We ignore the invented diagnostics.
        """

        # extract only what we really need

        state = kwargs.get("state", "")

        event = kwargs.get("event", "")


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
# SYSTEM INITIALIZATION / RECOVERY
# ============================================================

def initialize_measurement_system(
        hx,
        sample,
        previous_offset,
        reason
):
    """
    Initialize Baseline and FSM after startup or HX711 reset.

    Returns:
        hx, baseline, fsm, watchdog, median, signal_logger

    reason:
        "BOOT" or "RESET"
    """

    baseline = Baseline(hx)

    boot_load = baseline.startup(
        sample,
        previous_offset=previous_offset
    )

    fsm = WeightFSM()

    if boot_load:

        fsm.force_present(sample.weight)

        if reason == "BOOT":
            sample.note = "BOOT_LOAD_DETECTED"
        else:
            sample.note = "RESET_LOAD_DETECTED"

    else:

        if reason == "BOOT":
            sample.note = "BOOT_ZERO"
        else:
            sample.note = "RESET_ZERO"


    sample.update_from_fsm(fsm)

    watchdog = Watchdog()
    median = MedianFilter(size=7)
    signal_logger = SignalLogger()
    stability = StabilityModel()

    return (
        baseline,
        fsm,
        watchdog,
        median,
        signal_logger,
        stability
    )

# ============================================================
# PROCESS ONE SAMPLE
# ============================================================

def process_sample(
    sample,
    median,
    baseline,
    watchdog,
    stability,
    fsm,
    signal_logger,
    trace
):

    median.update(sample)
    baseline.process(sample)

    watchdog.process(sample)

    if sample.glitch:
        return None, watchdog.glitch_count >= GLITCH_LIMIT

    mean, var, energy = stability.process(sample)

    event = fsm.process_weight(sample.weight, sample)

    sample.update_from_fsm(fsm)

    signal_logger.update(
        sample,
        sample.weight,
        var,
        mean,
        energy,
        STATE_NAME[sample.state],
        event
    )

    if event:
        trace.dump_event(event, sample)

    return event, False

# ============================================================
# INIT
# ============================================================

ms.init()
ms.log(f"{sys.argv[0]} start {time.ctime()}")

writePID(1)

hx = HX711_CT()

trace = TraceRecorder()

sample = Sample()

(
    baseline,
    fsm,
    watchdog,
    median,
    signal_logger,
    stability
) = initialize_measurement_system(
        hx,
        sample,
        hxOffset,
        "BOOT"
)

trace.dump_event("BOOT", sample)

# ============================================================
# LOOP STATE
# ============================================================
try:

    while True:

        sample.t = time.monotonic()

        try:
            sample.raw_sample = hx.read()

        except RuntimeError:
            ms.log("HX711 read error")
            time.sleep(0.15)
            continue

        event, recover = process_sample(
            sample,
            median,
            baseline,
            watchdog,
            stability,
            fsm,
            signal_logger,
            trace
        )

        if sample.glitch:

            ms.log(f"GLITCH: {sample.glitch_reason}")

            if recover:

                old_offset = baseline.offset
                hx.close()
                time.sleep(1)
                hx = HX711_CT()

                (
                    baseline,
                    fsm,
                    watchdog,
                    median,
                    signal_logger,
                    stability
                ) = initialize_measurement_system(
                    hx,
                    sample,
                    old_offset,
                    "RESET"
                )

                trace.dump_event("RESET", sample)

            time.sleep(0.15)
            continue

        if event == "ARRIVAL":
            send_fifo(sample.peak)

        elif event == "DEPARTURE":
            send_fifo(-1)

        ms.log(
            f"{sample.weight:.2f} g {STATE_NAME[sample.state]}",
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