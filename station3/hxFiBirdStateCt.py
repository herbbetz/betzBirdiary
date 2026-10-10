"""
hxFiBirdStateCt.py
dependent on c/libhx711.so

HX711 -> MedianFilter -> Baseline -> WeightFSM -> Recorders

raw    : median-filtered HX711 reading
offset : zero reference (baseline)
weight : (raw - offset) / hxScale * hxPolarity

The whole logic:
1. threshold = weightThreshold + NOISE_K * sigma (capped at MAX_THRESHOLD), updated in IDLE only.
2. Baseline moves only in IDLE: when the last IDLE_WINDOW raw values are quiet (p10-p90 spread <= weightThreshold)
   and their level is below threshold_on, offset = their median. The window is cleared whenever the FSM is not in IDLE.
3. sigma = robust noise from sample-to-sample differences (MAD).
4. ARRIVAL/PRESENT/DEPARTURE longer than STATE_TIMEOUT -> full startup re-zero, back to IDLE. OVERSIZE never re-zeroes.

IDLE -> ARRIVAL -> PRESENT -> DEPARTURE -> IDLE
Camera triggers CAMERA_DELAY seconds after entering PRESENT, a DEPARTURE trigger is sent on PRESENT->DEPARTURE.
Optional command line argument "test" enables SignalLogger (ramdisk: signal_hx.csv, hxFiBird.log).
Offline analysis of signal_hx.csv with hx_signalanalyzer.py.
Direction aware load cell: weight is positive on load, hxPolarity is set by calibrateHx.py.
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
import urllib.parse
import urllib.error
import urllib.request
from sharedBird import writePID, clearPID, getTestmode
from configBird3 import birdpath, hxDataPin, hxClckPin, hxPolScaleOff, weightThreshold, weightlimit
import msgBird as ms
hxPolarity = 1 if hxPolScaleOff[0] == 1 else -1
hxScale = abs(hxPolScaleOff[1])
if hxScale == 0: hxScale = 600

@dataclass
class Sample:
    t: float = 0.0
    raw_sample: int = 0  # single ADC value before MedianFilter
    raw: int = 0  # ADCount after MedianFilter
    offset: float = 0.0
    weight: float = 0.0
    sigma: float = 0.0  # noise in grams
    threshold: float = 0.0
    state: int = 0
    startup_spread: int = 0
    startup_attempts: int = 0
    startup_maxspread: int = 0
    startup_delay: float = 0.0
    events: list[str] = field(default_factory=list)

# ============================================================
# HX711 DRIVER
# ============================================================
ERR_BASE = -10000000
ERR_WAIT_TIMEOUT = ERR_BASE - 1
ERR_FRAME_PREEMPT = ERR_BASE - 2

class HX711_CT:
    def __init__(self, testmode: bool = False) -> None:
        self.open(testmode=testmode)

    def read(self) -> int:
        value = self.lib.hx711_read()
        if value <= ERR_BASE:
            if value == ERR_WAIT_TIMEOUT: raise RuntimeError("HX711 timeout: DOUT pin remained HIGH (Hardware disconnect or unready)")
            if value == ERR_FRAME_PREEMPT: raise RuntimeError("HX711 preemption: OS scheduling delay invalidated frame timing")
            raise RuntimeError(f"HX711 driver error code: {value}")
        return value

    def open(self, testmode: bool = False) -> None:
        libpath = f"{birdpath['appdir']}/c/libhx711{'_debug' if testmode else ''}.so"
        self.lib = ctypes.CDLL(libpath)
        self.lib.hx711_init.argtypes = [ctypes.c_int, ctypes.c_int]
        self.lib.hx711_read.restype = ctypes.c_int64
        self.lib.hx711_close.restype = None
        if self.lib.hx711_init(hxDataPin, hxClckPin) != 0: raise RuntimeError("HX711 init failed")

    def close(self) -> None:
        self.lib.hx711_close()

# ============================================================
# MEDIAN FILTER
# ============================================================
class MedianFilter:
    def __init__(self, size: int = 7) -> None:
        self.buf = deque(maxlen=size)

    def update(self, sample: Sample) -> None:
        self.buf.append(sample.raw_sample)
        sample.raw = int(np.median(self.buf))

# ============================================================
# BASELINE: the only place that moves the offset
# ============================================================
SETTLE_TIME = 2.0      # startup settle before sampling
MAX_WINDOW_TIME = 60.0 # max time to wait for a stable startup window
WINDOW_SAMPLES = 120   # samples per startup stability window
SPREAD_LIMIT = 3000    # startup: p10-p90 ADC spread considered "quiet"
MAX_ATTEMPTS = 3       # startup retries with relaxed spread limit
IDLE_WINDOW = 20   # IDLE: samples that must be quiet before the offset follows, ~3 s at 0.157 s/tick, equal to the post-departure cooldown

class Baseline:
    def __init__(self, hx: HX711_CT) -> None:
        self.hx = hx
        self.offset = 0.0
        self.win = deque(maxlen=IDLE_WINDOW)

    # returns (median, spread) of the first window below spread_limit, else of the tightest window seen
    def _collect_window(self, samples: int, max_time: float, spread_limit: float) -> tuple[float, float] | None:
        buf: list[int] = []
        best_spread = float("inf")
        best_median = 0.0
        t0 = time.monotonic()
        while time.monotonic() - t0 < max_time:
            try: raw = self.hx.read()
            except RuntimeError as e:
                ms.log(f"Baseline sample warning: {e}", terminal=False)
                time.sleep(0.1)
                continue
            buf.append(raw)
            if len(buf) > samples: buf.pop(0)
            if len(buf) >= samples:
                values = np.array(buf)
                p10, p90 = np.percentile(values, [10, 90])
                spread = p90 - p10
                if spread < best_spread:
                    best_spread = spread
                    best_median = float(np.median(values))
                if spread <= spread_limit: return best_median, spread
        return (best_median, best_spread) if buf else None

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
                try: self.hx.read()
                except RuntimeError: time.sleep(0.1)
            t0 = time.monotonic()
            result = self._collect_window(WINDOW_SAMPLES, MAX_WINDOW_TIME, spread_limit)
            delay = time.monotonic() - t0
            if result is not None:
                median, spread = result
                if spread <= spread_limit:
                    self.offset = median
                    self.win.clear()
                    sample.offset = self.offset
                    sample.weight = 0.0
                    sample.startup_spread = spread
                    sample.startup_attempts = attempt
                    sample.startup_maxspread = spread_limit
                    sample.startup_delay = delay
                    event = f"STARTUP_ZERO spread={spread:.0f} < {spread_limit}"
                    sample.events.append(event)
                    ms.log(event)
                    return True
                best = min(best, spread)
        raise RuntimeError(f"HX711 startup did not stabilize ({MAX_ATTEMPTS} attempts, spread {best:.0f} > {spread_limit})")

    def process(self, sample: Sample) -> None:
        sample.offset = self.offset
        sample.weight = (sample.raw - self.offset) / hxScale * hxPolarity

    # IDLE only: quiet window -> offset = its median. No EMA, no step cap, no warmup.
    def follow_idle(self, sample: Sample, limit_g: float) -> None:
        self.win.append(sample.raw)
        if len(self.win) < IDLE_WINDOW: return
        v = np.array(self.win)
        p10, p90 = np.percentile(v, [10, 90])
        med = float(np.median(v))
        # adopt only quiet windows whose level the FSM would not call a bird anyway
        if p90 - p10 <= weightThreshold * hxScale and (med - self.offset) / hxScale * hxPolarity <= limit_g: self.offset = med
# ============================================================
# NoiseGuard: robust noise (MAD of consecutive differences)
# median absolute deviation (MAD) less sensitive to bird steps than Welford sigma
# ============================================================
class NoiseGuard:
    def __init__(self, window_samples: int = 210, min_ready_samples: int = 30) -> None:
        self.diffs = deque(maxlen=window_samples)
        self.min_ready = min_ready_samples
        self.last: float | None = None

    def add_sample(self, raw: float) -> None:
        if self.last is not None: self.diffs.append(raw - self.last)
        self.last = raw

    def current_std_grams(self) -> float:
        if len(self.diffs) < self.min_ready: return 0.0
        d = np.array(self.diffs)
        mad = np.median(np.abs(d - np.median(d)))
        return float(1.4826 * mad / np.sqrt(2) / hxScale)

# ============================================================
# FSM
# ============================================================
STATE_IDLE = 0
STATE_ARRIVAL = 1
STATE_PRESENT = 2
STATE_DEPARTURE = 3
STATE_OVERSIZE = 4
STATE_NAME = {STATE_IDLE: "IDLE", STATE_ARRIVAL: "ARRIVAL", STATE_PRESENT: "PRESENT", STATE_DEPARTURE: "DEPARTURE", STATE_OVERSIZE: "OVERSIZE"}
ACTIVE_STATES = (STATE_ARRIVAL, STATE_PRESENT, STATE_DEPARTURE)
CAMERA_DELAY = 2.0
ARRIVAL_CONFIRM_SAMPLES = 10
DEPARTURE_CONFIRM_SAMPLES = 20
RESET_COOLDOWN_S = 10.0
STATE_TIMEOUT = 300.0
OFF_RATIO = 0.7

class WeightFSM:
    def __init__(self, threshold_on: float) -> None:
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
        self.set_threshold(threshold_on)
        self.handlers = {STATE_IDLE: self.state_idle, STATE_ARRIVAL: self.state_arrival, STATE_PRESENT: self.state_present,
                         STATE_DEPARTURE: self.state_departure, STATE_OVERSIZE: self.state_oversize}

    def set_threshold(self, on: float) -> None:
        self.threshold_on = on
        self.threshold_off = OFF_RATIO * on

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

    def timed_out(self) -> bool:
        return self.state in ACTIVE_STATES and time.monotonic() - self.state_t0 > STATE_TIMEOUT

    def _transition(self, new_state: int, sample, event: str) -> str:
        old_state = self.state
        self.state = new_state
        self.state_t0 = time.monotonic()
        self.reset()
        if new_state == STATE_ARRIVAL: self.weight_at_arrival = sample.weight
        if new_state == STATE_PRESENT:
            self.present_t0 = self.state_t0
            self.camera_sent = False
            if self.weight_at_arrival <= 0: self.weight_at_arrival = sample.weight
        if new_state == STATE_DEPARTURE: self.departure_t0 = self.state_t0
        if old_state == STATE_DEPARTURE and new_state == STATE_IDLE:
            self.idle_cooldown_t0 = self.state_t0
            self._cooldown_duration = 3.0
        sample.events.append(event)
        return event

    def camera_trigger(self) -> bool:
        if self.state != STATE_PRESENT or self.camera_sent: return False
        if time.monotonic() - self.present_t0 < CAMERA_DELAY: return False
        self.camera_sent = True
        return True

    def process_weight(self, sample) -> str | None:
        return self.handlers[self.state](sample)

    def state_idle(self, sample) -> str | None:
        if time.monotonic() - self.idle_cooldown_t0 < self._cooldown_duration:
            self.above_count = 0
            return None
        if sample.weight > self.threshold_on: self.above_count += 1
        else:
            self.above_count = 0
            return None
        if self.above_count >= 3:
            if sample.weight > weightlimit: return self._transition(STATE_OVERSIZE, sample, "IDLE->OVERSIZE")
            return self._transition(STATE_ARRIVAL, sample, "IDLE->ARRIVAL")
        return None

    def state_arrival(self, sample) -> str | None:
        if sample.weight < self.threshold_off: return self._transition(STATE_IDLE, sample, "ARRIVAL_CANCELLED")
        if sample.weight > weightlimit: return self._transition(STATE_OVERSIZE, sample, "ARRIVAL->OVERSIZE")
        self.above_count += 1
        if self.above_count >= ARRIVAL_CONFIRM_SAMPLES: return self._transition(STATE_PRESENT, sample, "ARRIVAL->PRESENT")
        return None

    def state_present(self, sample) -> str | None:
        if sample.weight > weightlimit: return self._transition(STATE_OVERSIZE, sample, "PRESENT->OVERSIZE")
        if sample.weight < self.threshold_off:
            self.below_count += 1
            if self.below_count >= DEPARTURE_CONFIRM_SAMPLES: return self._transition(STATE_DEPARTURE, sample, "PRESENT->DEPARTURE")
        else: self.below_count = 0
        return None

    def state_oversize(self, sample) -> str | None:
        if sample.weight < self.threshold_off:
            self.below_count += 1
            if self.below_count >= DEPARTURE_CONFIRM_SAMPLES: return self._transition(STATE_DEPARTURE, sample, "OVERSIZE->DEPARTURE")
        else: self.below_count = 0
        return None

    def state_departure(self, sample) -> str | None:
        if time.monotonic() - self.departure_t0 > 2.0: return self._transition(STATE_IDLE, sample, "DEPARTURE->IDLE")
        return None

# ============================================================
# RECORDERS
# ============================================================
def readable_time() -> str:
    return datetime.now().strftime("%H:%M:%S")

class SignalLogger:
    def __init__(self, sample: Sample) -> None:
        self.file = os.path.join(birdpath["ramdisk"], "signal_hx.csv")
        self._last_second = -1
        self._write_header(sample)

    def _write_header(self, sample: Sample) -> None:
        with open(self.file, "w") as f:
            f.write(f"# weightThreshold={weightThreshold}\n# threshold_off={OFF_RATIO * weightThreshold:.2f}\n# weightlimit={weightlimit}\n")
            f.write(f"# hxScale={hxScale}\n# CAMERA_DELAY={CAMERA_DELAY}\n# startup_offset={sample.offset:.0f}\n")
            f.write(f"# startup_note={'|'.join(sample.events)}\n# startup_attempts={sample.startup_attempts}\n# startup_delay={sample.startup_delay:.2f}\n")
            f.write("time,mono_t,raw,offset,weight,sigma,threshold,state,events\n")

    def _format_row(self, sample: Sample, readtime: str) -> str:
        return (f"{readtime},{sample.t:.3f},{sample.raw},{sample.offset:.0f},{sample.weight:.2f},{sample.sigma:.2f},"
                f"{sample.threshold:.2f},{STATE_NAME[sample.state]},{'|'.join(sample.events)}\n")

    def log(self, sample: Sample, readtime: str) -> None:
        important = any(e in ("CAMERA_TRIGGER", "DEPARTURE_TRIGGER", "BASELINE_RESET", "NOISY", "HX711_GLITCH") for e in sample.events)
        second = int(sample.t)
        if not important:
            if second == self._last_second: return
            self._last_second = second
        with open(self.file, "a", buffering=1) as f: f.write(self._format_row(sample, readtime))

class LiveLogger:
    def __init__(self) -> None:
        self.url = "http://127.0.0.1:8080/hxsignal/update"
        self.timeout = 0.2

    def log(self, sample: Sample) -> None:
        query = urllib.parse.urlencode({"t": f"{sample.t:.3f}", "weight": f"{sample.weight:.2f}", "offset": f"{sample.offset:.0f}",
                                        "sigma": f"{sample.sigma:.2f}", "threshold": f"{sample.threshold:.2f}",
                                        "state": STATE_NAME[sample.state], "hxscale": f"{hxScale:.0f}"})
        try:
            with urllib.request.urlopen(urllib.request.Request(f"{self.url}?{query}", method="GET"), timeout=self.timeout): pass
        except (urllib.error.URLError, TimeoutError, OSError): pass

class NullRecorder:
    def log(self, *args, **kwargs) -> None:
        pass

# ============================================================
# MAIN PROGRAM
# ============================================================
fifo = birdpath["fifo"]

def send_fifo(value: int) -> None:
    try: fd = os.open(fifo, os.O_WRONLY | os.O_NONBLOCK)
    except OSError as e:
        if e.errno == errno.ENXIO: return
        raise
    try:
        with os.fdopen(fd, "w") as f: f.write(f"{value}\n")
    except OSError as e:
        if e.errno in (errno.EAGAIN, errno.EWOULDBLOCK): ms.log(f"send_fifo({value}): pipe full, trigger dropped", terminal=False)
        else: raise

ms.init()
testmode = False
if len(sys.argv) > 1 and sys.argv[1] == "test": testmode = True
if getTestmode() > 0: testmode = True
ms.log(f"Testmode of {sys.argv[0]}" if testmode else sys.argv[0])
ms.log(f"... starting at {time.ctime()}")
writePID(1)
hx = HX711_CT(testmode=testmode)
sample = Sample()
baseline = Baseline(hx)

def rezero(sample: Sample) -> None:
    try: baseline.startup(sample)
    except RuntimeError as e:
        ms.log(f"Startup calibration failed: {e}")
        sys.exit(1)   # distinct code: "give the shell script a retry"

rezero(sample)
CRIT_NOISE = 6.0  # critical sigma in grams (retune: sigma is now a difference-based estimate)
MEDIAN_SAMPLES = 7
NOISEGUARD_SAMPLES = 210
NOISE_K = 3.0      # 3 * sigma is over 95%
MAX_THRESHOLD = 15
median = MedianFilter(size=MEDIAN_SAMPLES)
noiseguard = NoiseGuard(window_samples=NOISEGUARD_SAMPLES)
for _ in range(MEDIAN_SAMPLES):  # pre-fill MedianFilter only
    sample.raw_sample = hx.read()
    median.update(sample)
fsm = WeightFSM(weightThreshold)
if testmode:
    signal_logger = SignalLogger(sample)
    live_logger = LiveLogger()
else:
    signal_logger = NullRecorder()
    live_logger = NullRecorder()

try:
    while True:
        sample.events.clear()
        sample.t = time.monotonic()
        try:
            sample.raw_sample = hx.read()
            if sample.sigma > CRIT_NOISE: ms.setScalenoisy()
            else: ms.setScaleready()
        except RuntimeError as e:
            sample.events.append("HX711_GLITCH")
            ms.clearScaleready()
            ms.log(f"hx read: {e}", terminal=False)
            time.sleep(0.05)
            continue
        if ms.getHxReset() == 1:  # emergency switch
            ms.clearHxReset()
            rezero(sample)
            continue
        median.update(sample)
        baseline.process(sample)
        noiseguard.add_sample(sample.raw_sample)
        sample.sigma = noiseguard.current_std_grams()
        if fsm.state == STATE_IDLE: fsm.set_threshold(min(weightThreshold + NOISE_K * sample.sigma, MAX_THRESHOLD))
        sample.threshold = fsm.threshold_on
        event = fsm.process_weight(sample)
        sample.state = fsm.state
        if fsm.state == STATE_IDLE: baseline.follow_idle(sample, fsm.threshold_on)
        else: baseline.win.clear()
        if fsm.state in ACTIVE_STATES: sample.events.append(f"_{time.monotonic() - fsm.state_t0:.0f}s")
        if fsm.timed_out():
            rezero(sample)
            fsm.force_idle(time.monotonic())
            sample.events.append("BASELINE_RESET")
            sample.state = fsm.state
            event = None
        if fsm.camera_trigger():
            sample.events.append("CAMERA_TRIGGER")
            send_fifo(int(sample.weight))
        elif event and "->DEPARTURE" in event:
            sample.events.append("DEPARTURE_TRIGGER")
            send_fifo(-1)
        read_time = readable_time()
        signal_logger.log(sample, read_time)
        live_logger.log(sample)
        ms.log(f"{read_time} {sample.weight:.2f}g {STATE_NAME[sample.state]}", terminal=False)
        time.sleep(0.15)
except (KeyboardInterrupt, SystemExit):
    ms.log(f"shutdown {sys.argv[0]}")
finally:
    hx.close()
    ms.clearScaleready()
    clearPID(1)
    ms.log(f"{sys.argv[0]} stopped {time.ctime()}")
