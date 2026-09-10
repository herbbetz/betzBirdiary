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
# for LiveLogger:
import urllib.parse
import urllib.error
import urllib.request

from sharedBird import fifoExists, writePID, clearPID, getTestmode
from configBird3 import (
    birdpath,
    hxDataPin,
    hxClckPin,
    hxScale,
    weightThreshold,
    weightlimit,
    update_config_json
)
import msgBird as ms

WEIGHTTHRESHOLD_off = 0.7 * weightThreshold

@dataclass
class Sample:
    t: float = 0.0

    raw_sample: int = 0 # single ADC value before MedianFilter (could be spike)
    raw: int = 0 # ADCount after MedianFilter

    offset: float = 0.0
    weight: float = 0.0
    sigma: float = 0.0  # Standard deviation in grams
    dyn_threshold: float = 0.0

    state: int = 0

    startup_spread: int = 0
    startup_attempts: int = 0 # HX711 samples read until a stable baseline was successfully found
    startup_maxspread: int = 0
    startup_delay: float = 0.0

    events: list[str] = field(default_factory=list) # '=[]' not allowed in dataclass

# ============================================================
# HX711 DRIVER
# ============================================================
import ctypes

# Updated error definitions matching libhx711.c
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

STARTUP_SETTLE_TIME = 2.0
STARTUP_MAX_TIME = 60.0
STABLE_SAMPLES = 60
STABLE_SPREAD_LIMIT = 3000 # rather high initially, the actual spread is usually < 1000.
STARTUP_MAX_ATTEMPTS  = 3 # max attempts before raising RuntimeError.
OFFSET_ALPHA = 0.0025

class Baseline:
    def __init__(self, hx: HX711_CT) -> None:
        self.hx = hx
        self.offset = 0.0
        self.stable_buf = deque(maxlen=STABLE_SAMPLES)

    def stable_buf_reset(self) -> None:
        self.stable_buf.clear()

    def update_stable_buffer(self, raw: int) -> None:
        if len(self.stable_buf) >= STABLE_SAMPLES:
            self.stable_buf.popleft()
        self.stable_buf.append(raw)

    def stable_raw(self) -> float | None:
        if len(self.stable_buf) < STABLE_SAMPLES:
            return None
        spread = self._stable_spread()
        if spread > STABLE_SPREAD_LIMIT:
            return None
        return float(np.median(self.stable_buf))

    def _stable_spread(self) -> float:
        values = np.array(self.stable_buf)
        p10, p90 = np.percentile(values, [10, 90])
        return p90 - p10

    def startup(self, sample: Sample) -> bool:
        attempts = 0
        best  = float("inf")
        for attempt in range(1, STARTUP_MAX_ATTEMPTS + 1):
            spread_limit = STABLE_SPREAD_LIMIT * (1 + 0.5 * (attempt - 1)) # allow more spread on subsequent attempts
            if attempt > 1:
                ms.log(f"Startup retry {attempt}/{STARTUP_MAX_ATTEMPTS}")
                # Re-init the C driver to flush any stuck state
                self.hx.close()
                self.hx.open(testmode=testmode)
            result = self._startup_attempt(sample, attempt, spread_limit)

            if result is None:
                return True  # clean success, sample already populated
            best = min(best, result)
            attempts += 1

        raise RuntimeError(
            f"HX711 startup did not stabilize "
            f"({attempts} attempts, "
            f"spread {best:.0f} > {spread_limit})"
        )

    def _startup_attempt(
        self,
        sample: Sample,
        attempt: int,
        spread_limit: int
    ) -> float | None:
        ms.log(f"Startup zeroing (attempt {attempt})...")
        time.sleep(STARTUP_SETTLE_TIME)

        # --- burn-in: discard 5 initial unstable readings ---
        for _ in range(5):
            try:
                self.hx.read()
            except RuntimeError:
                # On error, sleep 100ms to match 10Hz frame timing before retrying
                time.sleep(0.1)
                continue


        # --- fill stable buffer, tracking best window ---
        self.stable_buf.clear()

        best_spread  = float("inf")
        best_median  = 0.0
        t0 = time.monotonic()
        attempts = 0

        while time.monotonic() - t0 < STARTUP_MAX_TIME:
            try:
                raw = self.hx.read()
            except RuntimeError as e:
                ms.log(f"Startup sample warning: {e}", terminal=False)
                # On error, sleep 100ms to match 10Hz frame timing before retrying
                time.sleep(0.1)
                continue

            self.update_stable_buffer(raw)
            attempts += 1

            # Evaluate current window
            if len(self.stable_buf) >= STABLE_SAMPLES:
                spread = self._stable_spread()
                if spread < best_spread:
                    best_spread = spread
                    best_median = float(np.median(self.stable_buf))

                if spread <= spread_limit:
                    self.offset = best_median
                    sample.offset = self.offset
                    sample.weight = 0.0
                    sample.startup_spread = spread
                    sample.startup_attempts = attempt
                    sample.startup_maxspread = spread_limit
                    sample.startup_delay = time.monotonic() - t0
                    event = f"STARTUP_ZERO spread={spread:.0f} < {spread_limit}"
                    sample.events.append(event)
                    ms.log(event)
                    return None  # success

        # Window expired without meeting spread_limit
        return best_spread

    def process(self, sample: Sample) -> None:
        sample.offset = self.offset
        sample.weight = (sample.raw - self.offset) / hxScale

    # During IDLE, the baseline offset follows slow environmental drift using an exponential moving average (EMA):
    def follow_idle(self, sample: Sample) -> None:
        delta = sample.raw - self.offset
        drift_g = abs(delta) / abs(hxScale)
        if drift_g < 1.0:
            alpha = 0.0025
        elif drift_g < 5.0:
            alpha = 0.02
        else:
            alpha = 0.10
        self.offset += delta * alpha

    # raw_value is not sample.raw unless the 60-sample stable buffer is not yet filled, see Baseline.stable_raw() and caller weightFSM.check_timeout().
    def reacquire(self, sample: Sample, burst: int = 25) -> bool:
        readings: list[int] = []
        for _ in range(burst):
            try:
                readings.append(self.hx.read())
            except RuntimeError:
                time.sleep(0.05)
                continue
            time.sleep(0.1)

        if len(readings) < burst // 2:
            return False

        self.offset = float(np.median(readings))
        self.stable_buf.clear()
        sample.offset = self.offset
        sample.weight = 0.0
        return True

        # --- Direct snap, only from a validated stable-buffer candidate ---
    def adopt(self, sample: Sample, candidate: float) -> None:
        self.offset = candidate
        self.stable_buf.clear()
        sample.offset = self.offset
        sample.weight = 0.0

# ============================================================
# NoiseGuard using Welford's Standard Deviation in 30 secs windows
#   (is faster than Interquartile Range)
# uses raw ADC values
# ============================================================
class NoiseGuard:
    def __init__(
            self,
            window_samples: int = 210
        ) -> None:
        # window_samples in raw ADC units.
        self.max_samples = window_samples

        # Ring buffer and tracking state
        self.buf = np.zeros(
            self.max_samples,
            dtype=np.float64
        )
        self.count = 0
        self.head = 0

        # Welford running statistics
        self.mean = 0.0
        self.M2 = 0.0

    def reset(self) -> None:
        self.count = 0
        self.head = 0
        self.mean = 0.0
        self.M2 = 0.0

    def add_sample(self, raw: float) -> None:
        if self.count < self.max_samples:
            # Fill the buffer initially.
            self.count += 1

            delta = raw - self.mean
            self.mean += delta / self.count
            delta2 = raw - self.mean
            self.M2 += delta * delta2

            self.buf[self.head] = raw

        else:
            # Ring buffer full: remove outgoing value
            # before adding incoming value.
            old_val = self.buf[self.head]
            old_mean = self.mean

            self.mean += (
                raw - old_val
            ) / self.max_samples

            self.M2 += (
                (raw - old_val)
                * (raw - self.mean + old_val - old_mean)
            )

            self.buf[self.head] = raw

        self.head = (
            self.head + 1
        ) % self.max_samples

    def current_std(self) -> float:
        if self.count < 2:
            return 0.0
        variance = max(
            0.0,
            self.M2 / (self.count - 1)
        )
        return float(np.sqrt(variance))

    def current_std_grams(self) -> float:
        """Returns standard deviation in physical units (grams)."""
        if abs(hxScale) < 1:
            return 0.0

        return self.current_std() / abs(hxScale)

# ============================================================
# FSM (pure state machine, no I/O, no logging)
# abs(weight) makes it agnostic of decreasing ADC raw values on loading the cell.
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
STATE_TIMEOUT = 300.0  # 5-minute safety watchdog to auto-tare stuck readings
weightlimit = 300.0

class WeightFSM:
    def __init__(self, weight_threshold: float) -> None:
        self.state = STATE_IDLE
        self.state_t0 = time.monotonic()
        self.above_count = 0
        self.below_count = 0
        self.departure_t0 = 0.0
        self.present_t0 = 0.0
        self.idle_cooldown_t0 = 0.0  # Cooldown tracker after departure
        self.camera_sent = False
        self.baseline_at_arrival = 0.0
        self.threshold_on = 0.0
        self.threshold_off = 0.0
        self.set_thresholds(weight_threshold)

    def set_thresholds(self, base_threshold: float) -> None:
        """Updates active weight threshold and recalibrates hysteresis off-threshold."""
        self.threshold_on = base_threshold
        self.threshold_off = 0.7 * base_threshold

    def reset(self) -> None:
        """Resets sample confirmation counters."""
        self.above_count = 0
        self.below_count = 0

    def force_idle(self, current_time: float) -> None:
        """Forces the FSM back to IDLE state and resets counters."""
        self.state = STATE_IDLE
        self.state_t0 = current_time
        self.idle_cooldown_t0 = current_time
        self.reset()
        self.camera_sent = False

    def _transition(
        self,
        new_state: int,
        sample,
        event: str
    ) -> str:
        """Handles internal state transitions and resets state-specific timers/counters."""
        old_state = self.state
        self.state = new_state
        self.state_t0 = time.monotonic()
        self.reset()

        if new_state == STATE_ARRIVAL:
            self.baseline_at_arrival = sample.offset

        if new_state == STATE_PRESENT:
            self.present_t0 = self.state_t0
            self.camera_sent = False

        if new_state == STATE_DEPARTURE:
            self.departure_t0 = self.state_t0

        # Start 3-second IDLE cooldown when exiting DEPARTURE back to IDLE
        if old_state == STATE_DEPARTURE and new_state == STATE_IDLE:
            self.idle_cooldown_t0 = time.monotonic()

        sample.events.append(event)
        return event

    def camera_trigger(self, current_sample) -> bool:
        """Determines if a camera trigger event should fire during STATE_PRESENT."""
        if self.state != STATE_PRESENT:
            return False
        if self.camera_sent:
            return False
        if time.monotonic() - self.present_t0 < CAMERA_DELAY:
            return False

        # Guard: Ensure weight exceeds the active noise floor (2*sigma + 5g)
        # Prevents triggering camera on environmental noise spikes during PRESENT
        if abs(current_sample.weight) < (2.0 * current_sample.sigma + 5.0):
            return False

        self.camera_sent = True
        return True

    def check_timeout(
        self,
        sample,
        baseline
    ) -> str | None:
        current_time = time.monotonic()

        # --- active states stuck for > STATE_TIMEOUT ---
        if self.state in (STATE_ARRIVAL, STATE_PRESENT, STATE_DEPARTURE):
            if current_time - self.state_t0 > STATE_TIMEOUT:
                old = STATE_NAME[self.state]

                if not baseline.reacquire(sample):
                    baseline.offset = float(sample.raw)
                    sample.offset = baseline.offset
                    sample.weight = 0.0

                self.force_idle(current_time)
                event_str = f"BASELINE_RESET {old} -> IDLE"
                sample.events.append(event_str)
                return event_str

            since = current_time - self.state_t0
            sample.events.append(f"since_{since:.0f}s")
            return None

        # --- IDLE pinned above off-threshold for > STATE_TIMEOUT ---
        if self.state == STATE_IDLE:
            if abs(sample.weight) > self.threshold_off:
                if current_time - self.state_t0 > STATE_TIMEOUT:
                    if not baseline.reacquire(sample):
                        baseline.offset = float(sample.raw)
                        sample.offset = baseline.offset
                        sample.weight = 0.0

                    self.force_idle(current_time)
                    sample.events.append("BASELINE_RESET")
                    return "BASELINE_RESET"

        return None

    def process_weight(self, sample) -> str | None:
        """Main evaluation entrypoint. Dispatches execution to active state handler."""
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
        """IDLE State: Monitors for weight exceeding threshold over 3 consecutive samples."""
        # Ignore triggers during post-departure cooldown
        if time.monotonic() - self.idle_cooldown_t0 < 3.0:
            self.above_count = 0
            return None

        absweight = abs(sample.weight)
        # threshold_on is dyn_threshold (e.g. 14.5g during high noise)
        if absweight > self.threshold_on:
            self.above_count += 1
            if self.above_count >= 3:
                if absweight > weightlimit:
                    return self._transition(STATE_OVERSIZE, sample, "IDLE->OVERSIZE")
                return self._transition(STATE_ARRIVAL, sample, "IDLE->ARRIVAL")
        else:
            # Instantly clears counter if a sample dips below active noise threshold
            self.above_count = 0
        return None

    def state_arrival(self, sample) -> str | None:
        """ARRIVAL State: Confirms valid arrival over ARRIVAL_CONFIRM_SAMPLES."""
        if abs(sample.weight) < self.threshold_off:
            return self._transition(STATE_IDLE, sample, "ARRIVAL_CANCELLED")
        if abs(sample.weight) > weightlimit:
            return self._transition(STATE_OVERSIZE, sample, "ARRIVAL->OVERSIZE")

        self.above_count += 1
        if self.above_count >= ARRIVAL_CONFIRM_SAMPLES:
            return self._transition(STATE_PRESENT, sample, "ARRIVAL->PRESENT")
        return None

    def state_present(self, sample) -> str | None:
        """PRESENT State: Monitors subject presence and checks for departure signal."""
        if abs(sample.weight) > weightlimit:
            return self._transition(STATE_OVERSIZE, sample, "PRESENT->OVERSIZE")

        if abs(sample.weight) < self.threshold_off:
            self.below_count += 1
            # Requires 3 consecutive samples below threshold_off to confirm DEPARTURE
            if self.below_count >= 3:
                return self._transition(STATE_DEPARTURE, sample, "PRESENT->DEPARTURE")
        else:
            self.below_count = 0
        return None

    def state_oversize(self, sample) -> str | None:
        """OVERSIZE State: Handles weights exceeding weightlimit safety bounds."""
        if abs(sample.weight) < self.threshold_off:
            self.below_count += 1
            # Requires 3 consecutive samples below threshold_off to confirm DEPARTURE
            if self.below_count >= 3:
                return self._transition(STATE_DEPARTURE, sample, "OVERSIZE->DEPARTURE")
        else:
            self.below_count = 0
        return None

    def state_departure(self, sample) -> str | None:
        """DEPARTURE State: Holds state for 2.0s post-departure, then transitions to IDLE."""
        if time.monotonic() - self.departure_t0 > 2.0:
            return self._transition(STATE_IDLE, sample, "DEPARTURE->IDLE")
        return None
# ============================================================
# RECORDERS
# ============================================================

def readable_time() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

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
            f.write(
                f"# threshold_off={WEIGHTTHRESHOLD_off:.2f}\n"
            )
            f.write(f"# weightlimit={weightlimit}\n")
            f.write(f"# hxScale={hxScale}\n")
            f.write(f"# CAMERA_DELAY={CAMERA_DELAY}\n")
            f.write(
                f"# startup_offset={sample.offset:.0f}\n"
            )
            f.write(
                f"# startup_note={'|'.join(sample.events)}\n"
            )
            f.write(
                f"# startup_attempts={sample.startup_attempts}\n"
            )
            f.write(
                f"# startup_delay={sample.startup_delay:.2f}\n"
            )
            f.write(
                "time,mono_t,raw,offset,weight,sigma,threshold,state,events\n"
            )

    def _format_row(self, sample: Sample) -> str:
        return (
            f"{readable_time()},"
            f"{sample.t:.3f},"
            f"{sample.raw},"
            f"{sample.offset:.0f},"
            f"{sample.weight:.2f},"
            f"{sample.sigma:.2f},"
            f"{sample.dyn_threshold:.2f},"
            f"{STATE_NAME[sample.state]},"
            f"{'|'.join(sample.events)}\n"
        )

    def log(self, sample: Sample) -> None:
        # 1. Initialize important to False by default
        important = False
        
        # 2. Check if any event in the list qualifies as important
        for event in sample.events:
            if event in (
                "CAMERA_TRIGGER",
                "DEPARTURE_TRIGGER",
                "BASELINE_RESET",
                "NOISY",
                "HX711_GLITCH"
            ):
                important = True
                break  # Stop checking once we find one important event

        second = int(sample.t)

        # 3. Rate-limit standard sub-second samples, but write immediately if important
        if not important:
            if second == self._last_second:
                return
            self._last_second = second

        with open(self.file, "a", buffering=1) as f:
            f.write(self._format_row(sample))

class LiveLogger:
    def __init__(self) -> None:
        self.url = "http://127.0.0.1:8080/hxsignal/update" # absolute URL, only the browser can access "/hxsignal/update"
        self.timeout = 0.2

    def log(self, sample: Sample) -> None:
        query = urllib.parse.urlencode({
            "t": f"{sample.t:.3f}",
            "weight": f"{sample.weight:.2f}",
            "offset": f"{sample.offset:.0f}",
            "sigma": f"{sample.sigma:.2f}",
            "hxscale": f"{hxScale:.0f}"
        })

        request = urllib.request.Request(
            f"{self.url}?{query}",
            method="GET"
        )

        try:
            with urllib.request.urlopen(
                request,
                timeout=self.timeout
            ):
                pass
        except (
            urllib.error.URLError,
            TimeoutError,
            OSError
        ):
            pass

class NullRecorder:
    def __init__(self) -> None:
        self.raw_jump_count = 0
        self.raw_jump_events = 0

    def log(self, *args, **kwargs) -> None:
        pass


# ============================================================
# MAIN PROGRAM
# ============================================================

fifo = birdpath["fifo"]
'''
# easier to leave this to prepended bash code inside hxFiBird.sh:
if not fifoExists(fifo):
    os.mkfifo(fifo)
    ms.log("FIFO created")
# is the script running as root (sudo), then fifo may not be writable.
    if os.geteuid() == 0: os.chmod(fifo, 0o666)  # Allow read/write for all users

import pwd, grp
if os.geteuid() == 0:
    pi_uid = pwd.getpwnam("pi").pw_uid
    pi_gid = grp.getgrnam("pi").gr_gid
    os.chown(fifo, pi_uid, pi_gid)
'''
def send_fifo(value: int) -> None:
    try:
        fd = os.open(fifo, os.O_WRONLY | os.O_NONBLOCK)
    except OSError as e:
        if e.errno == errno.ENXIO:
            return  # no reader attached – expected during tests
        raise

    try:
        with os.fdopen(fd, "w") as f:
            f.write(f"{value}\n")
    except OSError as e:
        if e.errno in (errno.EAGAIN, errno.EWOULDBLOCK):
            ms.log(f"send_fifo({value}): pipe full, trigger dropped",
                   terminal=False)
        else:
            raise

# ============================================================
# INITIALIZATION
# ============================================================

ms.init()
testmode = False
if len(sys.argv) > 1 and sys.argv[1] == "test":
    testmode = True
# from lastdown.json:
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
MEDIAN_SAMPLES = 7
NOISEGUARD_SAMPLES = 210
# Adaptive threshold logic
dyn_threshold = weightThreshold
max_dyn_threshold = 15 # 15 grams

# Initialize filters
median = MedianFilter(size=MEDIAN_SAMPLES)
noiseguard = NoiseGuard(window_samples=NOISEGUARD_SAMPLES)

# Pre-fill MedianFilter only.
# NoiseGuard deliberately starts empty.
baseline_val = int(np.median(baseline.stable_buf))

for _ in range(MEDIAN_SAMPLES):
    median.buf.append(baseline_val)

fsm = WeightFSM(weightThreshold)

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
            if sample.sigma > 6.0:
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

        # ----------------------------------------------------
        # NOISEGUARD
        # check noise before FSM, also to avoid contamination of sample.sigma by bird arrival
        # Completely independent measurement lifecycle:
        #   IDLE     -> collect samples
        #   non-IDLE -> discard all samples
        # ----------------------------------------------------

        # if event == "IDLE->ARRIVAL": # avoid contamination of sample.sigma by bird arrival
        # Feed NoiseGuard continuously across ALL states to maintain valid rolling sigma
        noiseguard.add_sample(sample.raw)
        sample.sigma = noiseguard.current_std_grams()

        if fsm.state == STATE_IDLE:
            # Continuously update dynamic threshold during IDLE
            # unlatches dyn_threshold to weightThreshold, should sigma drop backto near zero
            # 3.0 * sigma covers 99% of wet/windy noise peaks
            dyn_threshold = min(3.0 * sample.sigma + weightThreshold, max_dyn_threshold)
        else:
            # During ARRIVAL/PRESENT/DEPARTURE, keep dyn_threshold latched at entry level
            pass

        sample.dyn_threshold = dyn_threshold
        fsm.set_thresholds(dyn_threshold)

        # ----------------------------------------------------
        # FSM
        # ----------------------------------------------------

        event = fsm.process_weight(sample)
        sample.state = fsm.state

        # ----------------------------------------------------
        # BASELINE
        #   candidate is the possible new baseline value produced by the stable-sample buffer
        # ----------------------------------------------------
        if fsm.state == STATE_IDLE:
            baseline.update_stable_buffer(sample.raw)
            candidate = baseline.stable_raw()

            if candidate is not None:
                delta_grams = abs(candidate - baseline.offset) / abs(hxScale)
                if delta_grams > 0.5:
                    baseline.adopt(sample, candidate)
                    sample.events.append("IDLE_STABLE_RECAL")
            else:
                baseline.follow_idle(sample)
        else:
            baseline.stable_buf_reset()

        # ----------------------------------------------------
        # FSM TIMEOUT / BASELINE RECOVERY
        # ----------------------------------------------------

        timeout_event = fsm.check_timeout(
            sample,
            baseline
        )
        if timeout_event:
            event = timeout_event
            sample.state = fsm.state

        # ----------------------------------------------------
        # CAMERA / DEPARTURE TRIGGERS
        # ----------------------------------------------------

        if fsm.camera_trigger(sample):
            sample.events.append("CAMERA_TRIGGER")
            send_fifo(int(sample.weight))

        elif (
            event
            and "DEPARTURE" in event
        ):
            sample.events.append("DEPARTURE_TRIGGER")
            send_fifo(-1)

        # in ramdisk/hxFiBird.log:
        # if event is not None:
        #     print(f"FSM Event Triggered: {event}", flush=True)

        # ----------------------------------------------------
        # RECORDERS
        # ----------------------------------------------------

        signal_logger.log(sample)
        live_logger.log(sample)

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
    ms.log(f"shutdown {sys.argv[0]}")

finally:
    update_config_json({
        "hxOffset": baseline.offset,
        "hxScale": hxScale
    })

    hx.close()
    ms.clearScaleready()
    clearPID(1)

    ms.log(
        f"{sys.argv[0]} stopped {time.ctime()}"
    )