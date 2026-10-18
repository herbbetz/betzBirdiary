"""
calibrateHxC.py
Calibration tool for HX711 using the same C driver (c/libhx711.so) as hxFiBirdStateCt.py.
Workflow: stop hxFiBird, measure unloaded median, measure known weight, compute polarity and scale, verify zero, save hxPolScaleOff to config.json.
"""
import ctypes, os, signal, sys, time
import numpy as np
from sharedBird import roundFlt, pids
from configBird3 import birdpath, hxDataPin, hxClckPin, update_config_json

NUM_VALS = 100
SAMPLE_SLEEP = 0.15  # same cadence as the hxFiBird main loop
MAX_READ_ERRORS = 20
ERR_BASE = -10000000

class HX711_CT:  # copy of the driver class in hxFiBirdStateCt.py (that file runs its main loop on import)
    def __init__(self) -> None:
        self.lib = ctypes.CDLL(f"{birdpath['appdir']}/c/libhx711.so")
        self.lib.hx711_init.argtypes = [ctypes.c_int, ctypes.c_int]
        self.lib.hx711_read.restype = ctypes.c_int64
        self.lib.hx711_close.restype = None
        rc = self.lib.hx711_init(hxDataPin, hxClckPin)
        if rc != 0: raise RuntimeError(f"HX711 init failed (code {rc}: -1 gpiochip, -2 DOUT pin, -3 SCK pin; -2/-3 = pin held by another process)")

    def read(self) -> int:
        value = self.lib.hx711_read()
        if value <= ERR_BASE: raise RuntimeError(f"HX711 driver error code: {value}")
        return value

    def close(self) -> None:
        self.lib.hx711_close()

def read_ok() -> int:
    for _ in range(MAX_READ_ERRORS):
        try: return hx.read()
        except RuntimeError as e:
            print(f"read warning: {e}")
            time.sleep(0.1)
    sys.exit("HX711 keeps failing, check wiring")

def get_median(num_vals: int) -> tuple[float, float]:
    print(f"Sampling {num_vals} readings...")
    v = np.empty(num_vals)
    for i in range(num_vals):
        v[i] = read_ok()
        time.sleep(SAMPLE_SLEEP)
    median_val, spread = float(np.median(v)), float(v.max() - v.min())
    print(f"median: {median_val}, spread: {spread} ({v.min():.0f} to {v.max():.0f})")
    return median_val, spread

# ---------------- Stop hxFiBird if running (it holds the GPIO lines) ----------------
if os.geteuid() != 0: sys.exit(f"Run as root: sudo python3 {sys.argv[0]}")
processes_to_kill = ["hxFiBird.sh", "hxFiBirdStateCt.py"] # run as root, therefore calibrate as sudo
p = pids()
p.kill_list(processes_to_kill)

print("\nInitializing HX711...")
hx = HX711_CT()
print("HX711 ready.\n")

input("Remove all weights from scale and press ENTER...")
time.sleep(2)
median_no_load, spread_no_load = get_median(NUM_VALS)

while True:
    try:
        cal_weight = float(input("Place calibration weight and enter grams: "))
        if cal_weight > 0: break
    except ValueError: pass
    print("Enter a positive numeric value.")
print(f"Calibration weight: {cal_weight} g")
time.sleep(2)
median_load, spread_load = get_median(NUM_VALS)

# weight = (raw - offset) / scale * polarity, the formula used by hxFiBirdStateCt.py
delta = median_load - median_no_load
scale = round(abs(delta) / cal_weight)
if abs(delta) < 10 or scale < 1:
    print("No change, calibration weight < 10?")
    sys.exit(1)
polarity = 1 if delta > 0 else -1
offset = round(median_no_load)
spread_limit = int(max(spread_no_load, spread_load, 2000)) + 1000  # min 2000, +1000 margin, JSON compatible
print(f"\nScale factor: {scale} raw units per gram, polarity {polarity}")

input("\nRemove weight and press ENTER. Check readings near 0 g.")
for _ in range(10):
    print(f"{roundFlt((read_ok() - offset) / scale * polarity)} g")
    time.sleep(0.3)

print(f"\nSaving: polarity={polarity}, scale={scale}, offset={offset}, spread_limit={spread_limit}")
update_config_json({"hxPolScaleOff": [polarity, scale, offset, spread_limit]})
hx.close()
print("\nCalibration complete. Reboot recommended.")