"""
hxFiBirdStateCt.py
dependent on c/libhx711.so

HX711 -> MedianFilter -> Baseline -> WeightFSM -> Recorders

raw      : median-filtered HX711 reading
offset   : current zero reference (baseline)
weight   : (raw - offset) / hxScale

- Baseline calibration is based on current stable raw values only.
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

from dataclasses import dataclass
from collections import deque
from datetime import datetime
import ctypes
import errno
import os
import sys
import time
import numpy as np
# for LiveLogger:
import urllib.error
import urllib.request

from sharedBird import fifoExists, writePID, clearPID
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
    startup_attempts: int = 0 # HX711 samples read until a stable baseline was successfully found (ideally equals STABLE_SAMPLES = 60)
    startup_maxspread: int = 0
    startup_delay: float = 0.0

    event: str = ""


# ============================================================
# HX711 DRIVER
# ============================================================
ERR_WAIT_TIMEOUT  = -9223372036854775808
ERR_FRAME_PREEMPT = -9223372036854775807

class HX711_CT:
    def __init__(self) -> None:
        global testmode

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

    def read(self) -> int:
            value = self.lib.hx711_read()

            if value == ERR_WAIT_TIMEOUT:
                raise RuntimeError("HX711 timeout: DOUT pin remained HIGH (Hardware disconnect or unready)")
            elif value == ERR_FRAME_PREEMPT:
                raise RuntimeError("HX711 preemption: OS scheduling delay invalidated frame timing")

            return value

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
STARTUP_MAX_TIME = 30.0
STABLE_SAMPLES = 60
STABLE_SPREAD_LIMIT = 3000
IDLE_RECAL_WINDOW = 60
IDLE_RECAL_SPREAD_LIMIT = 3000
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

        values = np.array(self.stable_buf)
        p10, p90 = np.percentile(values, [10, 90])
        spread = p90 - p10

        if spread > STABLE_SPREAD_LIMIT:
            return None

        return float(np.median(values))

    def stable_spread(self) -> float:
        if not self.stable_buf:
            return 0

        values = np.array(self.stable_buf)
        p10, p90 = np.percentile(values, [10, 90])

        return p90 - p10

    def startup(self, sample: Sample) -> bool:
            time.sleep(STARTUP_SETTLE_TIME)
            ms.log("Startup zeroing...")

            t0 = time.monotonic()
            attempts = 0
            self.stable_buf.clear()

            while time.monotonic() - t0 < STARTUP_MAX_TIME:
                try:
                    # hx.read() naturally blocks for ~100ms in 10Hz mode
                    raw = self.hx.read()
                except RuntimeError as e:
                    ms.log(f"Startup sample warning: {e}", terminal=False)
                    # On error, sleep 100ms to match 10Hz frame timing before retrying
                    time.sleep(0.1)
                    continue

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
                    sample.event = (
                        f"STARTUP_ZERO "
                        f"spread={sample.startup_spread:.0f}"
                    )

                    ms.log(sample.event)
                    return True

                # No extra sleep needed here on success; hx.read() on the next loop 
                # will cleanly block until the next hardware conversion completes (~100ms).

            raise RuntimeError("HX711 startup did not stabilize within 30s")

    def process(self, sample: Sample) -> None:
        sample.offset = self.offset
        sample.weight = (
            sample.raw - self.offset
        ) / hxScale

    def follow_idle(self, sample: Sample) -> None:
        self.offset += (
            sample.raw - self.offset
        ) * OFFSET_ALPHA

    def adopt_raw_value(
        self,
        raw_value: float,
        sample: Sample
    ) -> None:
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
    def __init__(self) -> None:
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

    def reset(self, keep_peak: bool = True) -> None:
        self.above_count = 0
        self.below_count = 0

        if not keep_peak:
            self.peak = 0.0

    def force_idle(self) -> None:
        self.state = STATE_IDLE
        self.state_t0 = time.monotonic()
        self.reset(keep_peak=False)
        self.camera_sent = False

    def _transition(
        self,
        new_state: int,
        sample: Sample,
        event: str,
        keep_peak: bool = True,
        departure: bool = False
    ) -> str:
        self.state = new_state
        self.state_t0 = time.monotonic()
        self.reset(keep_peak=keep_peak)

        if new_state == STATE_PRESENT:
            self.present_t0 = self.state_t0
            self.camera_sent = False

        if departure:
            self.departure_t0 = self.state_t0

        sample.event = event
        return STATE_NAME[new_state]

    def camera_trigger(self) -> bool:
        if self.state != STATE_PRESENT:
            return False

        if self.camera_sent:
            return False

        if time.monotonic() - self.present_t0 < CAMERA_DELAY:
            return False

        self.camera_sent = True
        return True

    def check_timeout(
        self,
        sample: Sample,
        baseline: Baseline
    ) -> str | None:
        # Recover stuck non-IDLE states using a stable baseline.
        if self.state in (
            STATE_ARRIVAL,
            STATE_PRESENT,
            STATE_DEPARTURE
        ):
            if time.monotonic() - self.state_t0 > STATE_TIMEOUT:
                raw_value = baseline.stable_raw()

                if raw_value is not None:
                    old_state = STATE_NAME[self.state]
                    baseline.adopt_raw_value(
                        raw_value,
                        sample
                    )
                    self.force_idle()
                    sample.event = (
                        f"BASELINE_RESET "
                        f"{old_state} -> IDLE"
                    )
                    return "BASELINE_RESET"

            return None

        # Reset an IDLE baseline that remains off-center too long.
        if self.state == STATE_IDLE:
            if abs(sample.weight) > WEIGHTTHRESHOLD_off:
                if time.monotonic() - self.state_t0 > STATE_TIMEOUT:
                    raw_value = baseline.stable_raw()

                    if raw_value is not None:
                        baseline.adopt_raw_value(
                            raw_value,
                            sample
                        )
                        self.reset(keep_peak=False)
                        sample.event = "BASELINE_RESET"
                        return "BASELINE_RESET"

            return None

        # OVERSIZE never auto-calibrates.
        return None

    def process_weight(
        self,
        weight: float,
        sample: Sample
    ) -> str | None:
        sample.event = ""

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

    def state_idle(
        self,
        weight: float,
        sample: Sample
    ) -> str | None:
        if weight > self.threshold_on:
            self.above_count += 1

            if self.above_count >= 3:
                self.peak = weight

                if weight > weightlimit:
                    return self._transition(
                        STATE_OVERSIZE,
                        sample,
                        "IDLE->OVERSIZE"
                    )

                return self._transition(
                    STATE_ARRIVAL,
                    sample,
                    "IDLE->ARRIVAL"
                )

        else:
            self.above_count = 0

        return None

    def state_arrival(
        self,
        weight: float,
        sample: Sample
    ) -> str | None:
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
                "ARRIVAL->OVERSIZE"
            )

        self.above_count += 1

        if (
            self.above_count >= ARRIVAL_CONFIRM_SAMPLES
            and self.peak > weightThreshold + 2.0
        ):
            return self._transition(
                STATE_PRESENT,
                sample,
                "ARRIVAL->PRESENT"
            )

        return None

    def state_present(
        self,
        weight: float,
        sample: Sample
    ) -> str | None:
        self.peak = max(self.peak, weight)

        if self.peak > weightlimit:
            return self._transition(
                STATE_OVERSIZE,
                sample,
                "PRESENT->OVERSIZE"
            )

        if weight < self.threshold_off:
            self.below_count += 1

            if self.below_count >= 2:
                return self._transition(
                    STATE_DEPARTURE,
                    sample,
                    "PRESENT->DEPARTURE",
                    departure=True
                )

        else:
            self.below_count = 0

        return None

    def state_oversize(
        self,
        weight: float,
        sample: Sample
    ) -> str | None:
        self.peak = max(self.peak, weight)

        if weight < self.threshold_off:
            self.below_count += 1

            if self.below_count >= 2:
                return self._transition(
                    STATE_DEPARTURE,
                    sample,
                    "OVERSIZE->DEPARTURE",
                    departure=True
                )

        else:
            self.below_count = 0

        return None

    def state_departure(
        self,
        weight: float,
        sample: Sample
    ) -> str | None:
        if time.monotonic() - self.departure_t0 > 2:
            return self._transition(
                STATE_IDLE,
                sample,
                "TIMEOUT->IDLE",
                keep_peak=False
            )

        if weight > self.threshold_on:
            self.peak = weight

            if weight > weightlimit:
                return self._transition(
                    STATE_OVERSIZE,
                    sample,
                    "DEPARTURE->OVERSIZE"
                )

            return self._transition(
                STATE_ARRIVAL,
                sample,
                "DEPARTURE->ARRIVAL"
            )

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
                f"# startup_note={sample.event} "
                f"(within {sample.startup_maxspread})\n"
            )
            f.write(
                f"# startup_attempts={sample.startup_attempts}\n"
            )
            f.write(
                f"# startup_delay={sample.startup_delay:.2f}\n"
            )
            f.write(
                "time,mono_t,raw,offset,weight,state,event\n"
            )

    def _format_row(self, sample: Sample) -> str:
        return (
            f"{readable_time()},"
            f"{sample.t:.3f},"
            f"{sample.raw},"
            f"{sample.offset:.0f},"
            f"{sample.weight:.2f},"
            f"{STATE_NAME[sample.state]},"
            f"{sample.event}\n"
        )

    def log(self, sample: Sample) -> None:
        important = sample.event in (
            "CAMERA_TRIGGER",
            "DEPARTURE_TRIGGER",
            "BASELINE_RESET"
        )

        second = int(sample.t)

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

if not fifoExists(fifo):
    os.mkfifo(fifo)
    ms.log("FIFO created")


def send_fifo(value: int) -> None:
    try:
        fd = os.open(
            fifo,
            os.O_WRONLY | os.O_NONBLOCK
        )

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

writePID(1)

hx = HX711_CT()
sample = Sample()

baseline = Baseline(hx)
baseline.startup(sample)

median = MedianFilter()

for value in baseline.stable_buf:
    median.buf.append(int(value))

fsm = WeightFSM()

ms.setScaleready()
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
            baseline.update_stable_buffer(sample.raw)

            candidate = baseline.stable_raw()

            if (
                candidate is not None
                and abs(candidate - baseline.offset) > 0
            ):
                baseline.adopt_raw_value(
                    candidate,
                    sample
                )
                sample.event = "IDLE_STABLE_RECAL" # baseline recalibration during IDLE state

            elif abs(sample.weight) < WEIGHTTHRESHOLD_off:
                # Follow small drift near a correct baseline.
                baseline.follow_idle(sample)

        else:
            baseline.stable_buf_reset()

        timeout_event = fsm.check_timeout(
            sample,
            baseline
        )

        if timeout_event:
            event = timeout_event

        signal_logger.log(sample)
        live_logger.log(sample)

        if fsm.camera_trigger():
            sample.event = "CAMERA_TRIGGER"
            signal_logger.log(sample)
            send_fifo(sample.peak)

        elif event == "DEPARTURE":
            sample.event = "DEPARTURE_TRIGGER"
            signal_logger.log(sample)
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
    ms.clearScaleready()
    clearPID(1)

    ms.log(f"hxFiBird stopped {time.ctime()}")