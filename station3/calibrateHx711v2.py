"""
HX711 calibration utility (compatible with lean lgpio driver)
-------------------------------------------------------------

Purpose
- Determine hxOffset (raw baseline)
- Determine hxScale (raw units per gram)

Procedure
1. Stop hxFiBirdState if running (releases GPIO)
2. Measure unloaded baseline (median)
3. Measure loaded baseline (known weight)
4. Compute scale
5. Save both values to config.json

Design notes
- Driver does NOT manage offset internally
- All calibration is purely mathematical
- Median is used instead of mean for robustness
"""
import numpy as np
import time
import os

from lgpioBird.HX711 import HX711
from sharedBird import roundFlt, readPID
from configBird3 import birdpath, hxDataPin, hxClckPin, update_config_json

NUM_VALS = 100
SLEEP_BETWEEN_SAMPLES = 0.2
config_path = f"{birdpath['appdir']}/config.json"


def get_mean(sensor, num_vals):
    print(f"Sampling {num_vals} readings...")
    readings_np = np.empty(shape=num_vals, dtype=float)

    for i in range(num_vals):
        readings_np[i] = sensor.read_raw()
        time.sleep(SLEEP_BETWEEN_SAMPLES)

    median_val = np.median(readings_np)
    min_val = np.min(readings_np)
    max_val = np.max(readings_np)
    spread = max_val - min_val

    print(f"{num_vals} elements read")
    print(f"median: {median_val}")
    print(f"spread: {spread} ({min_val} to {max_val})")

    return median_val


# -------------------------------------------------
# Stop hxFiBird if running
# -------------------------------------------------
hxFiPID = readPID(1)

if hxFiPID == -1 or not str(hxFiPID).strip():
    print("hxFiBird not running...")
else:
    try:
        pid_int = int(hxFiPID)
        print(f"Stopping hxFiBird (PID {pid_int})...")
        os.kill(pid_int, 15)  # SIGTERM
        time.sleep(1)
    except Exception as e:
        print(f"Could not stop hxFiBird: {e}")


# -------------------------------------------------
# Init HX711
# -------------------------------------------------
hx = HX711(data_pin=hxDataPin, clock_pin=hxClckPin)

# -------------------------------------------------
# Unloaded measurement
# -------------------------------------------------
input("Remove all loads from balance, then press ENTER...")
print("Sampling unloaded state...")
time.sleep(2)

mean_no_load = get_mean(hx, NUM_VALS)

# -------------------------------------------------
# Ask for calibration weight
# -------------------------------------------------
while True:
    cal_weight_str = input(
        "Load a known weight and enter grams (digits only): "
    )
    if cal_weight_str.isnumeric():
        cal_weight = float(cal_weight_str)
        if cal_weight > 0:
            break
    print("Please enter a positive number.")

# -------------------------------------------------
# Loaded measurement
# -------------------------------------------------
print("Sampling loaded state...")
time.sleep(2)

mean_load = get_mean(hx, NUM_VALS)

delta = mean_load - mean_no_load
scale_factor = delta / cal_weight

print(f"\nScale factor: {scale_factor} units/gram")

# -------------------------------------------------
# Verify zero again
# -------------------------------------------------
input("Remove weight again and press ENTER...")
time.sleep(2)

for _ in range(10):
    raw = hx.read_raw()
    reading = roundFlt((raw - mean_no_load) / scale_factor)
    print(f"{reading} g")
    time.sleep(0.2)

# -------------------------------------------------
# Save rounded values
# -------------------------------------------------
offset_rounded = round(mean_no_load)
scale_rounded = round(scale_factor)

print("\n---- SAVING TO CONFIG ----")
print(f"hxOffset: {offset_rounded}")
print(f"hxScale:  {scale_rounded}")

update_config_json({
    "hxOffset": offset_rounded,
    "hxScale": scale_rounded
})

print("Calibration finished — reboot recommended.")
hx.close()