"""
hxFiBirdStateCt.py
dependent on c/libhx711.so

HX711 -> MedianFilter -> Baseline -> WeightFSM -> Recorders

raw      : median-filtered HX711 reading
offset   : current zero reference (baseline)
weight   : (raw - offset) / hxScale

- Baseline calibration is based on current stable raw values only. EMA adaptation.
- NoiseGuard measures baseline StdDev sigma (Welford) and on noise increases weightThreshold
- No hxOffset history or BOOT_LOAD_DETECT logic is used. By environment
  hxOffset can vary more than a bird weight.
- Startup establishes the initial baseline from a stable sample window.
- During IDLE, the baseline follows slow environmental drift.
- Self-calibration is allowed only from stable IDLE measurements.
- A state timeout can recover from a stuck ARRIVAL/PRESENT/DEPARTURE state
  by adopting a stable idle baseline and forcing a return to IDLE.
- OVERSIZE never triggers automatic baseline recalibration.

Finite-state machine
--------------------
IDLE -> ARRIVAL -> PRESENT -> DEPARTURE -> IDLE

ARRIVAL requires repeated confirmation samples.
PRESENT represents a confirmed bird visit.
Camera triggering occurs after CAMERA_DELAY seconds in PRESENT.
DEPARTURE confirms unloading before returning to IDLE.

The optional command line argument
    test
enables SignalLogger for debugging -> on ramdisk:
signal_hx.csv, hxFiBird.log (C driver on stderr)

Offline analysis of signal_hx.csv with hx_signalanalyzer.py.

direction aware strain gauge & load cell, so weight always positive on load. For this, hxPolarity must be defined correctly by calibrateHx.py .
"""

from dataclasses import dataclass, field
from collections import deque
from datetime import datetime
import ctypes
import errno
import os
import sys
import time
import numpy as np
import math
# for LiveLogger:
import urllib.parse
import urllib.error
import urllib.request

from sharedBird import writePID, clearPID, getTestmode
from configBird3 import (
    birdpath,
    hxDataPin,
    hxClckPin,
    hxPolScaleOff,
    weightThreshold,
    weightlimit
)
import msgBird as ms
# this values are configured by calibrateHx.py:
hxPolarity = hxPolScaleOff[0] # either +1 or -1 meaning strain gauge orientation is up or down, so weight should always go up on bird load
hxPolarity = 1 if hxPolarity == 1 else -1
hxScale = abs(hxPolScaleOff[1])
if hxScale == 0: hxScale = 600

@dataclass
class Sample:
    t: float = 0.0

    raw_sample: int = 0  # single ADC value before MedianFilter (could be spike)
    raw: int = 0  # ADCount after MedianFilter

    offset: float = 0.0
    weight: float = 0.0
    sigma: float = 0.0  # Standard deviation in grams
    dyn_threshold: float = 0.0

    state: int = 0

    startup_spread: int = 0
    startup_attempts: int = 0  # HX711 samples read until a stable baseline was successfully found
    startup_maxspread: int = 0
    startup_delay: float = 0.0

    events: list[str] = field(default_factory=list)

# ============================================================
# HX711 DRIVER
# ============================================================

ERR_BASE          = -10000000
ERR_WAIT_TIMEOUT  = ERR_BASE - 1  # -10000001
ERR_FRAME_PREEMPT = ERR_BASE - 2  # -10000002

class HX711_CT:
    def __init__(self, testmode: bool = False) -> None:
        self.open(testmode=testmode)

    def read(self) -> int:
        value = self.lib.hx711_read()

        if value <= ERR_BASE:
            if value == ERR_WAIT_TIMEOUT:
                raise RuntimeError("HX711 timeout: DOUT pin remained HIGH (Hardware disconnect or unready)")
            elif value == ERR_FRAME_PREEMPT:
                raise RuntimeError("HX711 preemption: OS scheduling delay invalidated frame timing")
            else:
                raise RuntimeError(f"HX711 driver error code: {value}")

        return value

    def open(self, testmode: bool = False) -> None:
        if testmode:
            libpath = f"{birdpath['appdir']}/c/libhx711_debug.so"
        else:
            libpath = f"{birdpath['appdir']}/c/libhx711.so"

        self.lib = ctypes.CDLL(libpath)

        self.lib.hx711_init.argtypes = [
            ctypes.c_int,
            ctypes.c_int
        ]
        self.lib.hx711_read.restype = ctypes.c_int64
        self.lib.hx711_close.restype = None

        ret = self.lib.hx711_init(hxDataPin, hxClckPin)
        if ret != 0:
            raise RuntimeError("HX711 init failed")

    def close(self) -> None:
        self.lib.hx711_close()

# ============================================================
# SIMPLE MEDIAN FILTER
# ============================================================

class MedianFilter:
    def __init__(self, size: int = 7) -> None:
        self.buf = deque(maxlen=size)

    def update(self, sample: Sample) -> None:
        self.buf.append(sample.raw_sample)
        sample.raw = int(np.median(self.buf))

# ============================================================
# BASELINE (offset management and raw -> weight conversion)
# ============================================================
# Unified config: every offset-adopting path (startup, follow_idle,
# reacquire) shares the same spread-based stability test and the same
# step cap philosophy. No path may move self.offset without passing
# through _stable_window() first.

SETTLE_TIME       = 2.0     # startup settle before sampling
MAX_WINDOW_TIME    = 60.0    # max time to wait for a stable window
WINDOW_SAMPLES      = 120     # samples per stability window (startup + reacquire)
SPREAD_LIMIT        = 3000    # p10-p90 ADC spread considered "quiet"
MAX_ATTEMPTS         = 3      # retries with relaxed spread limit
MAX_STEP_G          = 5.0     # hard cap per single offset correction (any path)
EMA_ALPHA           = 0.002   # IDLE per-tick drift-follow rate
IDLE_FOLLOW_WARMUP  = 3.0     # seconds after entering IDLE before EMA starts


class Baseline:
    def __init__(self, hx: HX711_CT) -> None:
        self.hx = hx
        self.offset = 0.0
        self._idle_t0: float = 0.0
        self._primed = False

    def mark_idle_start(self) -> None:
        self._idle_t0 = time.monotonic()

    # ---- shared stability primitive ----
    # Collects up to `samples` readings (bounded by max_time), returns
    # (median, spread) of the tightest window seen. Caller decides
    # whether spread is acceptable.
    def _collect_window(self, samples: int, max_time: float, spread_limit: float) -> tuple[float, float] | None:
        buf: list[int] = []
        best_spread = float("inf")
        best_median = 0.0
        t0 = time.monotonic()

        while time.monotonic() - t0 < max_time:
            try:
                raw = self.hx.read()
            except RuntimeError as e:
                ms.log(f"Baseline sample warning: {e}", terminal=False)
                time.sleep(0.1)
                continue

            buf.append(raw)
            if len(buf) > samples:
                buf.pop(0)

            if len(buf) >= samples:
                values = np.array(buf)
                p10, p90 = np.percentile(values, [10, 90])
                spread = p90 - p10
                if spread < best_spread:
                    best_spread = spread
                    best_median = float(np.median(values))
                if spread <= spread_limit:
                    return best_median, spread  # found a good-enough window, stop searching

        # ran out of time: return the best window seen, caller decides what to do
        return (best_median, best_spread) if buf else None

    # Applies a candidate offset with a hard per-call step cap.
    # Returns the applied (capped) delta in raw counts.
    def _apply_capped(self, candidate: float, max_step_g: float = MAX_STEP_G) -> float:
        delta = candidate - self.offset
        max_step = max_step_g * hxScale
        if abs(delta) > max_step:
            delta = max_step if delta > 0 else -max_step
        self.offset += delta
        return delta

    # ---- startup ----
    def startup(self, sample: Sample) -> bool:
        best = float("inf")
        spread_limit = SPREAD_LIMIT
        for attempt in range(1, MAX_ATTEMPTS + 1):
            spread_limit = SPREAD_LIMIT * (1 + 0.5 * (attempt - 1))
            if attempt > 1:
                ms.log(f"Startup retry {attempt}/{MAX_ATTEMPTS}")
                self.hx.close()
                self.hx.open(testmode=testmode)

            ms.log(f"Startup zeroing (attempt {attempt})...")
            time.sleep(SETTLE_TIME)
            for _ in range(5):
                try:
                    self.hx.read()
                except RuntimeError:
                    time.sleep(0.1)

            t0 = time.monotonic()
            result = self._collect_window(WINDOW_SAMPLES, MAX_WINDOW_TIME, spread_limit)
            delay = time.monotonic() - t0

            if result is not None:
                median, spread = result
                if spread <= spread_limit:
                    self.offset = median
                    sample.offset = self.offset
                    sample.weight = 0.0
                    sample.startup_spread = spread
                    sample.startup_attempts = attempt
                    sample.startup_maxspread = spread_limit
                    sample.startup_delay = delay
                    event = f"STARTUP_ZERO spread={spread:.0f} < {spread_limit}"
                    sample.events.append(event)
                    ms.log(event)
                    self._primed = True
                    return True
                best = min(best, spread)

        raise RuntimeError(
            f"HX711 startup did not stabilize "
            f"({MAX_ATTEMPTS} attempts, spread {best:.0f} > {spread_limit})"
        )

    # ---- per-tick conversion ----
    def process(self, sample: Sample) -> None:
        if not self._primed:
            sample.offset = self.offset
            sample.weight = 0.0
            return
        sample.offset = self.offset
        sample.weight = (sample.raw - self.offset) / hxScale * hxPolarity

    # ---- slow drift tracking during IDLE ----
    def follow_idle(self, sample: Sample, noiseguard: "NoiseGuard") -> None:
        if time.monotonic() - self._idle_t0 < IDLE_FOLLOW_WARMUP:
            return
        if not noiseguard.is_ready():
            return
        # sigma is the live proxy for "is the platform currently quiet" —
        # this is the ONLY gate. No weight-magnitude gate: a large offset
        # error must remain correctable regardless of how far it has drifted.
        if sample.sigma > (SPREAD_LIMIT / hxScale):
            return

        delta = sample.raw - self.offset
        step = delta * EMA_ALPHA
        max_step = MAX_STEP_G * hxScale * 0.01  # per-tick step stays much smaller than a full correction
        if abs(step) > max_step:
            step = max_step if step > 0 else -max_step
        self.offset += step

    # ---- emergency recovery ----
    # _collect_window only ever returns a window that already satisfies
    # spread_limit (or None on timeout), so no separate rejection check
    # is needed here.
    def reacquire(self, sample: Sample, burst: int = 25) -> bool:
        result = self._collect_window(burst, max_time=burst * 0.2, spread_limit=SPREAD_LIMIT)
        if result is None:
            sample.events.append("REACQ_TIMEOUT")
            return False

        candidate, spread = result
        delta = self._apply_capped(candidate)
        sample.offset = self.offset
        sample.weight = (sample.raw - self.offset) / hxScale * hxPolarity

        step_g = delta / hxScale * hxPolarity
        sample.events.append(f"REACQ {step_g:+.1f}g spread={spread:.0f}")
        return abs(candidate - self.offset) < 0.5 * hxScale # return remaining to further correct baseline

    # ---- single entry point for emergency recovery ----
    # `cautious=True`: platform state is unknown (ARRIVAL/PRESENT/DEPARTURE
    #   stuck) — a bird might still be on it, so take one capped attempt only.
    # `cautious=False`: platform is expected empty (IDLE) — safe to loop
    #   toward full convergence.
    # Returns an event string; caller never needs to know about bursts,
    # spread checks, or attempt counts.
    def recover(self, sample: Sample, cautious: bool, max_attempts: int = 5) -> str:
        if cautious:
            return "REACQ_OK" if self.reacquire(sample) else "REACQ_FAIL"

        for _ in range(max_attempts):
            if self.reacquire(sample):
                return "REACQ_OK"
        return "REACQ_INCOMPLETE"
    
# ============================================================
# NoiseGuard (Welford's StdDev, rolling window)
# ============================================================

class NoiseGuard:
    def __init__(self, window_samples: int = 210, min_ready_samples: int = 30) -> None:
        self.max_samples = window_samples
        self.min_ready_samples = min_ready_samples
        self.buf = np.zeros(self.max_samples, dtype=np.float64)
        self.count = 0
        self.head = 0
        self.mean = 0.0
        self.M2 = 0.0

    def reset(self) -> None:
        self.count = 0
        self.head = 0
        self.mean = 0.0
        self.M2 = 0.0

    def add_sample(self, raw: float) -> None:
        if self.count < self.max_samples:
            self.count += 1
            delta = raw - self.mean
            self.mean += delta / self.count
            delta2 = raw - self.mean
            self.M2 += delta * delta2
            self.buf[self.head] = raw
        else:
            old_val = self.buf[self.head]
            old_mean = self.mean
            self.mean += (raw - old_val) / self.max_samples
            self.M2 += (raw - old_val) * (raw - self.mean + old_val - old_mean)
            self.buf[self.head] = raw

        self.head = (self.head + 1) % self.max_samples

    def is_ready(self) -> bool:
        return self.count >= self.min_ready_samples

    def current_std(self) -> float:
        if self.count < 2:
            return 0.0
        variance = max(0.0, self.M2 / (self.count - 1))
        return float(np.sqrt(variance))

    def current_std_grams(self) -> float:
        if hxScale < 1:
            return 0.0
        return self.current_std() / hxScale

# ============================================================
# FSM
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
    STATE_OVERSIZE: "OVERSIZE",
}

# --- System Constants ---
CAMERA_DELAY = 2.0
ARRIVAL_CONFIRM_SAMPLES = 10
DEPARTURE_CONFIRM_SAMPLES = 20
RESET_COOLDOWN_S = 10.0
PRESENT_DRIFT_TIMEOUT = 60.0
STATE_TIMEOUT = 300.0

class WeightFSM:
    def __init__(self, weight_threshold: float) -> None:
        self.state = STATE_IDLE
        self.state_t0 = time.monotonic()
        self.above_count = 0
        self.below_count = 0
        self.departure_t0 = 0.0
        self.present_t0 = 0.0
        self.idle_cooldown_t0 = 0.0
        self._cooldown_duration = 3.0
        self.camera_sent = False
        self.weight_at_arrival = 0.0
        self.threshold_on = 0.0
        self.threshold_off = 0.0
        self.set_thresholds(weight_threshold)

    def set_thresholds(self, base_threshold: float) -> None:
        self.threshold_on = base_threshold
        self.threshold_off = 0.7 * base_threshold

    def reset(self) -> None:
        self.above_count = 0
        self.below_count = 0

    def force_idle(self, current_time: float) -> None:
        self.state = STATE_IDLE
        self.state_t0 = current_time
        self.idle_cooldown_t0 = current_time
        self._cooldown_duration = RESET_COOLDOWN_S
        self.reset()
        self.camera_sent = False

    def _transition(self, new_state: int, sample, event: str) -> str:
        old_state = self.state
        self.state = new_state
        self.state_t0 = time.monotonic()
        self.reset()

        if new_state == STATE_ARRIVAL:
            self.weight_at_arrival = sample.weight

        if new_state == STATE_PRESENT:
            self.present_t0 = self.state_t0
            self.camera_sent = False
            if self.weight_at_arrival <= 0:
                self.weight_at_arrival = sample.weight

        if new_state == STATE_DEPARTURE:
            self.departure_t0 = self.state_t0

        if old_state == STATE_DEPARTURE and new_state == STATE_IDLE:
            self.idle_cooldown_t0 = time.monotonic()
            self._cooldown_duration = 3.0

        sample.events.append(event)
        return event

    def camera_trigger(self) -> bool:
        if self.state != STATE_PRESENT:
            return False
        if self.camera_sent:
            return False
        if time.monotonic() - self.present_t0 < CAMERA_DELAY:
            return False
        self.camera_sent = True
        return True

    def check_timeout(self, sample, baseline) -> str | None:
        current_time = time.monotonic()

        timed_out = False
        cautious = False

        if self.state in (STATE_ARRIVAL, STATE_PRESENT, STATE_DEPARTURE):
            if current_time - self.state_t0 > STATE_TIMEOUT:
                timed_out = True
                cautious = True
            else:
                since = current_time - self.state_t0
                sample.events.append(f"_{since:.0f}s")
                return None

        elif self.state == STATE_IDLE:
            if sample.weight > self.threshold_off and current_time - self.state_t0 > STATE_TIMEOUT:
                timed_out = True
                cautious = False

        if not timed_out:
            return None

        old = STATE_NAME[self.state]
        result = baseline.recover(sample, cautious=cautious)
        sample.events.append(result)

        self.force_idle(current_time)
        event_str = f"BASELINE_RESET {old} -> IDLE" if cautious else "BASELINE_RESET"
        sample.events.append(event_str)
        return event_str

    def process_weight(self, sample) -> str | None:
        if self.state == STATE_IDLE:
            return self.state_idle(sample)
        if self.state == STATE_ARRIVAL:
            return self.state_arrival(sample)
        if self.state == STATE_PRESENT:
            return self.state_present(sample)
        if self.state == STATE_DEPARTURE:
            return self.state_departure(sample)
        if self.state == STATE_OVERSIZE:
            return self.state_oversize(sample)
        return None

    def state_idle(self, sample) -> str | None:
        if time.monotonic() - self.idle_cooldown_t0 < self._cooldown_duration:
            self.above_count = 0
            return None

        if sample.weight > self.threshold_on:
            self.above_count += 1
        else:
            self.above_count = 0
            return None

        if self.above_count >= 3:
            if sample.weight > weightlimit:
                return self._transition(STATE_OVERSIZE, sample, "IDLE->OVERSIZE")
            return self._transition(STATE_ARRIVAL, sample, "IDLE->ARRIVAL")
        return None

    def state_arrival(self, sample) -> str | None:
        if sample.weight < self.threshold_off:
            return self._transition(STATE_IDLE, sample, "ARRIVAL_CANCELLED")
        if sample.weight > weightlimit:
            return self._transition(STATE_OVERSIZE, sample, "ARRIVAL->OVERSIZE")

        self.above_count += 1
        if self.above_count >= ARRIVAL_CONFIRM_SAMPLES:
            return self._transition(STATE_PRESENT, sample, "ARRIVAL->PRESENT")
        return None

    def state_present(self, sample) -> str | None:
        if sample.weight > weightlimit:
            return self._transition(STATE_OVERSIZE, sample, "PRESENT->OVERSIZE")

        if time.monotonic() - self.present_t0 > PRESENT_DRIFT_TIMEOUT:
            entry_w = self.weight_at_arrival
            if entry_w > 0 and sample.weight > 0.5 * entry_w:
                return self._transition(
                    STATE_DEPARTURE, sample,
                    "PRESENT_DRIFT_EXIT->DEPARTURE"
                )

        if sample.weight < self.threshold_off:
            self.below_count += 1
            if self.below_count >= DEPARTURE_CONFIRM_SAMPLES:
                return self._transition(STATE_DEPARTURE, sample, "PRESENT->DEPARTURE")
        else:
            self.below_count = 0
        return None

    def state_oversize(self, sample) -> str | None:
        if sample.weight < self.threshold_off:
            self.below_count += 1
            if self.below_count >= DEPARTURE_CONFIRM_SAMPLES:
                return self._transition(STATE_DEPARTURE, sample, "OVERSIZE->DEPARTURE")
        else:
            self.below_count = 0
        return None

    def state_departure(self, sample) -> str | None:
        if time.monotonic() - self.departure_t0 > 2.0:
            return self._transition(STATE_IDLE, sample, "DEPARTURE->IDLE")
        return None

# ============================================================
# RECORDERS
# ============================================================

def readable_time() -> str:
    # return datetime.now().strftime("%y-%m-%d %H:%M:%S")
    return datetime.now().strftime("%H:%M:%S")

class SignalLogger:
    def __init__(self, sample: Sample) -> None:
        self.file = os.path.join(
            birdpath["ramdisk"],
            "signal_hx.csv"
        )
        self._last_second = -1
        self._write_header(sample)

    def _write_header(self, sample: Sample) -> None:
        with open(self.file, "w") as f:
            f.write(f"# weightThreshold={weightThreshold}\n")
            f.write(f"# threshold_off={0.7 * weightThreshold:.2f}\n")
            f.write(f"# weightlimit={weightlimit}\n")
            f.write(f"# hxScale={hxScale}\n")
            f.write(f"# CAMERA_DELAY={CAMERA_DELAY}\n")
            f.write(f"# startup_offset={sample.offset:.0f}\n")
            f.write(f"# startup_note={'|'.join(sample.events)}\n")
            f.write(f"# startup_attempts={sample.startup_attempts}\n")
            f.write(f"# startup_delay={sample.startup_delay:.2f}\n")
            f.write(
                "time,mono_t,raw,offset,weight,sigma,threshold,state,events\n"
            )

    def _format_row(self, sample: Sample, readtime: str) -> str:
        return (
            f"{readtime},"
            f"{sample.t:.3f},"
            f"{sample.raw},"
            f"{sample.offset:.0f},"
            f"{sample.weight:.2f},"
            f"{sample.sigma:.2f},"
            f"{sample.dyn_threshold:.2f},"
            f"{STATE_NAME[sample.state]},"
            f"{'|'.join(sample.events)}\n"
        )

    def log(self, sample: Sample, readtime: str) -> None:
        important = False
        for event in sample.events:
            if event in (
                "CAMERA_TRIGGER",
                "DEPARTURE_TRIGGER",
                "BASELINE_RESET",
                "NOISY",
                "HX711_GLITCH"
            ):
                important = True
                break

        second = int(sample.t)

        if not important:
            if second == self._last_second:
                return
            self._last_second = second

        with open(self.file, "a", buffering=1) as f:
            f.write(self._format_row(sample, readtime))

class LiveLogger:
    def __init__(self) -> None:
        self.url = "http://127.0.0.1:8080/hxsignal/update"
        self.timeout = 0.2

    def log(self, sample: Sample) -> None:
        query = urllib.parse.urlencode({
            "t": f"{sample.t:.3f}",
            "weight": f"{sample.weight:.2f}",
            "offset": f"{sample.offset:.0f}",
            "sigma": f"{sample.sigma:.2f}",
            "threshold": f"{sample.dyn_threshold:.2f}",
            "hxscale": f"{hxScale:.0f}"
        })

        request = urllib.request.Request(
            f"{self.url}?{query}",
            method="GET"
        )

        try:
            with urllib.request.urlopen(request, timeout=self.timeout):
                pass
        except (
            urllib.error.URLError,
            TimeoutError,
            OSError
        ):
            pass

class NullRecorder:
    def __init__(self) -> None:
        pass

    def log(self, *args, **kwargs) -> None:
        pass


# ============================================================
# MAIN PROGRAM
# ============================================================

fifo = birdpath["fifo"]

def send_fifo(value: int) -> None:
    try:
        fd = os.open(fifo, os.O_WRONLY | os.O_NONBLOCK)
    except OSError as e:
        if e.errno == errno.ENXIO:
            return
        raise

    try:
        with os.fdopen(fd, "w") as f:
            f.write(f"{value}\n")
    except OSError as e:
        if e.errno in (errno.EAGAIN, errno.EWOULDBLOCK):
            ms.log(f"send_fifo({value}): pipe full, trigger dropped", terminal=False)
        else:
            raise

# ============================================================
# INITIALIZATION
# ============================================================

ms.init()
testmode = False
if len(sys.argv) > 1 and sys.argv[1] == "test":
    testmode = True
if getTestmode() > 0:
    testmode = True
if testmode:
    ms.log(f"Testmode of {sys.argv[0]}")
else:
    ms.log(sys.argv[0])
ms.log(f"... starting at {time.ctime()}")

writePID(1)

hx = HX711_CT(testmode=testmode)
sample = Sample()

baseline = Baseline(hx)
baseline.startup(sample)

# Configuration
CRIT_NOISE = 6.0 # critical sigma
MEDIAN_SAMPLES = 7
NOISEGUARD_SAMPLES = 210
dyn_threshold = weightThreshold
max_dyn_threshold = 15
DYN_THRESHOLD_DEADBAND = 0.5 # only push a new dyn_threshold to FSM if it moved at least this much
fsm_threshold_applied = weightThreshold  # what the FSM currently has, tracked separately from dyn_threshold

# Initialize filters
median = MedianFilter(size=MEDIAN_SAMPLES)
noiseguard = NoiseGuard(window_samples=NOISEGUARD_SAMPLES)

# Pre-fill MedianFilter only.
# NoiseGuard deliberately starts empty.
for _ in range(MEDIAN_SAMPLES):
    sample.raw_sample = hx.read()
    median.update(sample)

fsm = WeightFSM(weightThreshold)
prev_fsm_state = fsm.state

if testmode:
    signal_logger = SignalLogger(sample)
    live_logger = LiveLogger()
else:
    signal_logger = NullRecorder()
    live_logger = NullRecorder()

# ============================================================
# MAIN LOOP
# ============================================================
try:
    while True:
        sample.events.clear()
        sample.t = time.monotonic()

        try:
            sample.raw_sample = hx.read()
            if sample.sigma > CRIT_NOISE:
                ms.setScalenoisy()
            else:
                ms.setScaleready()

        except RuntimeError as e:
            sample.events.append("HX711_GLITCH")
            ms.clearScaleready()
            ms.log(f"hx read: {e}", terminal=False)
            time.sleep(0.05)
            continue

        median.update(sample)
        baseline.process(sample)

        is_quiet = fsm.state == STATE_IDLE and sample.weight < 0.7 * weightThreshold # weightThreshold_off
        if is_quiet:
            noiseguard.add_sample(sample.raw)
        else:
            noiseguard.reset()

        sample.sigma = noiseguard.current_std_grams()

        # --- dyn_threshold: could just simulate at EMA pace and be logged, if not fed to FSM ---
        if fsm.state == STATE_IDLE and noiseguard.is_ready():
            target = min(3.0 * sample.sigma + weightThreshold, max_dyn_threshold)
        else:
            target = weightThreshold          # drift back to base when bird is on
        dyn_threshold += (target - dyn_threshold) * EMA_ALPHA
        dyn_threshold = max(dyn_threshold, weightThreshold)
        sample.dyn_threshold = dyn_threshold  # logged to CSV for offline analysis

        # --- FSM gets the fixed base, not the simulated value ---
        # fsm.set_thresholds(weightThreshold)
        # --- OR: ---
        # activation: push to FSM only on IDLE-entry, or on a dead-band change
        # while remaining IDLE -- never every tick, so threshold_on/off stay
        # stable across the ARRIVAL confirmation-count window and don't chatter
        if fsm.state == STATE_IDLE:
            if prev_fsm_state != STATE_IDLE or abs(dyn_threshold - fsm_threshold_applied) >= DYN_THRESHOLD_DEADBAND:
                fsm.set_thresholds(dyn_threshold)
                fsm_threshold_applied = dyn_threshold
        else:
            if fsm_threshold_applied != weightThreshold:
                fsm.set_thresholds(weightThreshold)
                fsm_threshold_applied = weightThreshold
        prev_fsm_state = fsm.state
        
        event = fsm.process_weight(sample)
        sample.state = fsm.state
        if fsm.state == STATE_IDLE:
            baseline.mark_idle_start()
            baseline.follow_idle(sample, noiseguard)

        # FSM TIMEOUT / BASELINE RECOVERY
        timeout_event = fsm.check_timeout(sample, baseline)
        if timeout_event:
            event = timeout_event
            sample.state = fsm.state

        # CAMERA / DEPARTURE TRIGGERS
        if fsm.camera_trigger():
            sample.events.append("CAMERA_TRIGGER")
            send_fifo(int(sample.weight))

        elif event and "->DEPARTURE" in event:
            sample.events.append("DEPARTURE_TRIGGER")
            send_fifo(-1)

        # RECORDERS
        read_time = readable_time()
        signal_logger.log(sample, read_time)
        live_logger.log(sample)

        ms.log(
            f"{read_time} "
            f"{sample.weight:.2f}g "
            f"{STATE_NAME[sample.state]}",
            terminal=False
        )

        time.sleep(0.15)

# ============================================================
# CLEAN EXIT
# ============================================================

except (KeyboardInterrupt, SystemExit):
    ms.log(f"shutdown {sys.argv[0]}")

finally:
    hx.close()
    ms.clearScaleready()
    clearPID(1)

    ms.log(f"{sys.argv[0]} stopped {time.ctime()}")