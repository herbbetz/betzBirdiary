"""
Bird feeder scale runtime using blocking HX711 driver (C/ctypes version).

- Reads raw weight values from HX711 via libhx711.so
- FSM detects bird triggers and writes peak weights or -1 to birdpipe
- Maintains software offset and EMA baseline correction
- Performs safe baseline recalibration on startup and during run (spread-based)
- Persists calibration values from configBird3

Simple deterministic FSM:
IDLE -> ARRIVAL -> PRESENT -> DEPARTURE -> IDLE

- No None state
- Immediate trigger when threshold crossed
- Baseline recalibration only in IDLE
"""

from datetime import datetime
import time
import numpy as np
import os
import errno
import ctypes
import json

from sharedBird import roundFlt, fifoExists, writePID, clearPID
from configBird3 import (
    birdpath, hxDataPin, hxClckPin, hxScale,
    weightThreshold, weightlimit,
    update_config_json
)  # hxOffset from config.json is not used
import msgBird as ms


# ---------------- HX711 ctypes interface ----------------
class HX711_CT:

    def __init__(self, data_pin, clock_pin):

        libpath = f"{birdpath['appdir']}/c/libhx711.so"
        self.lib = ctypes.CDLL(libpath)

        self.lib.hx711_init.argtypes = [ctypes.c_int, ctypes.c_int]
        self.lib.hx711_init.restype = ctypes.c_int
        self.lib.hx711_read.restype = ctypes.c_long
        self.lib.hx711_close.restype = None

        ret = self.lib.hx711_init(data_pin, clock_pin)

        if ret != 0:
            raise RuntimeError(f"HX711 init failed {ret}")

    def read_raw(self):

        val = self.lib.hx711_read()

        # LONG_MIN → driver timeout/error
        if val == -9223372036854775808:
            raise RuntimeError("HX711 read timeout")

        return val

    def close(self):
        self.lib.hx711_close()


# ---------------- Constants ----------------
STARTUP_SETTLE_TIME = 1.2
SLEEP_TIME = 0.15

BASELINE_ZONE = 0.6 * weightThreshold
STABLE_COUNT = 8
DRIFT_ALPHA = 0.02
MAX_SPREAD_FOR_CAL = weightThreshold * hxScale
MAX_STARTUP_SPREAD = 0.5 * weightThreshold * hxScale

# --- Watchdog constants ---
RAW_JUMP_LIMIT = 120000
RAW_ABS_LIMIT = 8_000_000
GLITCH_LIMIT = 5
DEBUG_CSV = f"{birdpath['ramdisk']}/hx711debug.csv"

# ---------------- FIFO ----------------
fifo = birdpath["fifo"]
if not fifoExists(fifo):
    os.mkfifo(fifo)
    ms.log("hxFiBird created missing FIFO")


# --- Debugging to csv rather than to log file ---
def init_log_csv():
    with open(DEBUG_CSV, "w") as f:
        f.write("t,layer,event,value,raw,weight,state,delta,reason,extra,cycle_id\n")


def log_event(layer, event, value=None, cycle_id=None, **ctx):
    """
    Fault-diagnosis logger for HX711 + FSM pipeline.

    layer: SENSOR | WATCHDOG | MODEL | FSM | DRIFT
    event: string event name
    value: primary value (optional)
    ctx: extra key-value context
    """

    t = time.time()

    raw = ctx.get("raw", "")
    weight = ctx.get("weight", "")
    state = ctx.get("state", "")
    delta = ctx.get("delta", "")
    reason = ctx.get("reason", "")

    extra = json.dumps({
        k: v for k, v in ctx.items()
        if k not in {"raw", "weight", "state", "delta", "reason"}
    })

    row = [
        f"{t:.3f}",
        layer,
        event,
        "" if value is None else value,
        raw,
        weight,
        state,
        delta,
        reason,
        extra,
        cycle_id if cycle_id is not None else ""
    ]

    with open(DEBUG_CSV, "a", buffering=1) as f:
        f.write(",".join(map(str, row)) + "\n")


# ---------------- Helper ----------------
def get_median_spread(vals):
    return np.median(vals), np.max(vals) - np.min(vals)


def startup_zero(hx, retries=3):
    ms.log("Startup zeroing...")

    for attempt in range(retries):

        time.sleep(STARTUP_SETTLE_TIME)

        samples = [hx.read_raw() for _ in range(60)]
        median, spread = get_median_spread(samples)

        ms.log(f"Startup spread {spread}")

        if spread < MAX_STARTUP_SPREAD:
            ms.log(f"Startup hxOffset set to {median}")
            return median

        ms.log("Startup unstable — retrying")

    ms.log("Startup zero failed — using median anyway")
    return median


def calibOffset(samples, hxoffset):

    median, spread = get_median_spread(samples)
    ms.log(f"Calibration spread {spread}")

    if spread < MAX_SPREAD_FOR_CAL:
        hxoffset = median
        ms.log("hxOffset Cal OK")
    else:
        ms.log("hxOffset Cal SKIPPED")

    ms.log(f"hxOffset now {hxoffset}")

    return hxoffset


def sendFifo(weight):

    try:
        fd = os.open(fifo, os.O_WRONLY | os.O_NONBLOCK)

        with os.fdopen(fd, "w") as f:
            f.write(str(weight) + "\n")

    except OSError as e:
        if e.errno != errno.ENXIO:
            raise


# ---------------- FSM ----------------
STATE_IDLE = 0
STATE_ARRIVAL = 1
STATE_PRESENT = 2
STATE_DEPARTURE = 3


class WeightFSM:

    def __init__(self, threshold, weight_max):

        self.state = STATE_IDLE
        self.threshold = threshold
        self.weightMax = weight_max
        self.stable_counter = 0
        self.peak = 0.0
        self.departure_start = 0.0

    def update(self, w, tstr, cycle_id):

        # ---------- IDLE ----------
        if self.state == STATE_IDLE:
            if w > self.threshold:
                self.state = STATE_ARRIVAL
                self.stable_counter = 0
                self.peak = w

                ms.log(f"{tstr} ARRIVAL")
                log_event(
                    "FSM",
                    "TRANSITION",
                    "IDLE->ARRIVAL",
                    weight=w,
                    state="ARRIVAL",
                    reason="threshold_crossed",
                    cycle_id=cycle_id
                )

                return "ARRIVAL"

            return "IDLE"

        # ---------- ARRIVAL ----------
        elif self.state == STATE_ARRIVAL:

            if w > self.threshold:

                self.peak = max(self.peak, w)
                self.stable_counter += 1

                if self.stable_counter >= STABLE_COUNT:

                    self.state = STATE_PRESENT
                    sendFifo(self.peak)

                    ms.log(f"{tstr} PRESENT peak={self.peak}")
                    log_event(
                        "FSM",
                        "TRANSITION",
                        self.peak,
                        weight=self.peak,
                        state="PRESENT",
                        reason="stable_count_reached",
                        cycle_id=cycle_id
                    )

                    return "PRESENT"

            else:
                self.state = STATE_IDLE

            return "ARRIVAL"

        # ---------- PRESENT ----------
        elif self.state == STATE_PRESENT:

            self.peak = max(self.peak, w)

            if w < self.threshold:

                self.state = STATE_DEPARTURE
                self.departure_start = time.monotonic()
                self.stable_counter = 0

                sendFifo(-1)

                ms.log(f"{tstr} DEPARTURE")
                log_event(
                    "FSM",
                    "TRANSITION",
                    "PRESENT->DEPARTURE",
                    weight=w,
                    state="DEPARTURE",
                    reason="below_threshold",
                    cycle_id=cycle_id
                )

                return "DEPARTURE"

            return "PRESENT"

        # ---------- DEPARTURE ----------
        elif self.state == STATE_DEPARTURE:

            if time.monotonic() - self.departure_start > 10:

                ms.log("Departure timeout -> IDLE")
                self.state = STATE_IDLE
                self.stable_counter = 0
                self.peak = 0.0

                return "IDLE"

            if w < BASELINE_ZONE:

                self.stable_counter += 1

                if self.stable_counter >= STABLE_COUNT:

                    self.state = STATE_IDLE
                    self.stable_counter = 0

                    ms.log(f"{tstr} back to IDLE")
                    log_event(
                        "FSM",
                        "TRANSITION",
                        "DEPARTURE->IDLE",
                        weight=w,
                        state="IDLE",
                        reason="baseline_recovered",
                        cycle_id=cycle_id
                    )

                    return "IDLE"

            elif w > self.threshold:

                self.state = STATE_ARRIVAL
                self.stable_counter = 0

            else:
                self.stable_counter = 0

            return "DEPARTURE"


# ---------------- Main ----------------
ms.init()

ms.log(f"Start hxFiBirdStateCt {datetime.now()}")

writePID(1)

init_log_csv()

hx = HX711_CT(hxDataPin, hxClckPin)

hxOffset = startup_zero(hx)

fsm = WeightFSM(weightThreshold, weightlimit)

drift_est = 0.0
raw_idle_buffer = []

last_raw = None
glitch_count = 0

moving_window = []


try:

    while True:
        cycle_id = time.time()

        try:
            raw_sample = hx.read_raw()
        except RuntimeError:
            ms.log("HX711 read error")
            time.sleep(SLEEP_TIME)
            continue

        log_event(
            "SENSOR",
            "RAW_SAMPLE",
            raw_sample,
            raw=raw_sample,
            cycle_id=cycle_id
        )

        moving_window.append(raw_sample)
        if len(moving_window) > 3:
            moving_window.pop(0)

        raw = int(np.median(moving_window))

        log_event(
            "SENSOR",
            "RAW_FILTERED",
            raw,
            raw=raw,
            raw_sample=raw_sample,
            delta=raw - raw_sample,
            cycle_id=cycle_id
        )

        now = datetime.now()
        tstr = f"{now.hour}:{now.minute}:{now.second}"

        glitch = False

        if abs(raw) > RAW_ABS_LIMIT:
            glitch = True
            log_event("WATCHDOG", "RAW_OVERFLOW", raw,
                      raw=raw, reason="abs_limit", cycle_id=cycle_id)

        if last_raw is not None:
            if abs(raw - last_raw) > RAW_JUMP_LIMIT:
                glitch = True
                log_event("WATCHDOG", "RAW_JUMP", raw,
                          raw=raw, delta=raw-last_raw,
                          reason="jump_limit", cycle_id=cycle_id)

        if glitch:
            glitch_count += 1

            if glitch_count >= GLITCH_LIMIT:
                ms.log("HX711 reinit")

                hx.close()
                hx = HX711_CT(hxDataPin, hxClckPin)

                hxOffset = startup_zero(hx)

                fsm.state = STATE_IDLE
                fsm.stable_counter = 0
                fsm.peak = 0.0

                glitch_count = 0
                last_raw = None
                drift_est = 0.0
                raw_idle_buffer.clear()
                moving_window.clear()

                continue

            time.sleep(SLEEP_TIME)
            continue

        glitch_count = 0
        last_raw = raw

        weight = roundFlt((raw - hxOffset) / hxScale)

        log_event(
            "MODEL",
            "WEIGHT_CALC",
            weight,
            raw=raw,
            weight=weight,
            reason="offset_scale",
            cycle_id=cycle_id
        )

        if abs(weight) > weightlimit:
            ms.log(f"{tstr} WEIGHT glitch {weight}")
            time.sleep(SLEEP_TIME)
            continue

        state = fsm.update(weight, tstr, cycle_id)

        ms.log(f"{tstr} {weight:.1f}g {state}", terminal=False)

        if state in ("IDLE", "DEPARTURE"):

            if abs(weight) > 20:
                hxOffset = raw
                raw_idle_buffer.clear()
                drift_est = 0.0
                last_raw = raw
                time.sleep(SLEEP_TIME)
                continue

            drift_est = (1 - DRIFT_ALPHA) * drift_est + DRIFT_ALPHA * weight

            if abs(drift_est) > 0.5:
                hxOffset += drift_est * hxScale
                drift_est = 0.0

            raw_idle_buffer.append(raw)

            if len(raw_idle_buffer) >= 30:
                hxOffset = calibOffset(raw_idle_buffer, hxOffset)
                raw_idle_buffer.clear()

        else:
            raw_idle_buffer.clear()
            drift_est = 0.0

        time.sleep(SLEEP_TIME)


except (KeyboardInterrupt, SystemExit):
    ms.log("hxFiBirdStateCt shutting down")


finally:
    update_config_json({
        "hxOffset": hxOffset,
        "hxScale": hxScale
    })

    hx.close()
    clearPID(1)
    ms.log(f"End hxFiBirdStateCt {datetime.now()}")