# 3 min sensor test to detect drift, noise, and spikes in the HX711 load cell readings.
import ctypes
import time
import statistics
from collections import deque

lib = ctypes.CDLL("./libhx711.so")

lib.hx711_init.argtypes = [ctypes.c_int, ctypes.c_int]
lib.hx711_init.restype = ctypes.c_int

lib.hx711_read.restype = ctypes.c_long
lib.hx711_close.restype = None

if lib.hx711_init(17, 23) != 0:
    print("Init failed")
    exit(1)

# -------- parameters --------
DURATION_SEC = 180          # run 3 minutes
SAMPLE_DT = 0.5

window = deque(maxlen=30)
baseline_window = deque(maxlen=120)

spikes = 0
samples = 0

start = time.time()

print("Running HX711 diagnostic... (silent mode)")

while time.time() - start < DURATION_SEC:

    v = lib.hx711_read()
    samples += 1

    window.append(v)
    baseline_window.append(v)

    baseline = statistics.median(baseline_window)

    drift = v - baseline

    if len(window) > 5:
        noise = statistics.pstdev(window)
    else:
        noise = 0

    if abs(drift) > 150000:
        spikes += 1

    time.sleep(SAMPLE_DT)

lib.close()

# -------- final analysis --------

baseline_series = list(baseline_window)
drift_series = [x - statistics.median(baseline_series) for x in baseline_series]

drift_trend = drift_series[-1] - drift_series[0]
noise_level = statistics.mean([statistics.pstdev(window)])
spike_rate = spikes / max(samples, 1)

print("\n===== HX711 DIAGNOSTIC REPORT =====")
print(f"Samples: {samples}")
print(f"Spike rate: {spike_rate:.3f}")
print(f"Drift start→end: {drift_trend:.1f}")
print(f"Noise level (avg): {noise_level:.1f}")

# -------- interpretation --------

if abs(drift_trend) > 50000 and spike_rate < 0.01:
    verdict = "SLOW DRIFT (environment / thermal / humidity likely)"
elif spike_rate > 0.05:
    verdict = "SPIKE NOISE (wiring / power / rain interference)"
elif noise_level > 5000:
    verdict = "HIGH NOISE (mechanical instability or loose mount)"
else:
    verdict = "STABLE SENSOR"

print("Verdict:", verdict)
print("===================================")