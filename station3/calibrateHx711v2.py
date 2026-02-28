"""
calibrateHx711v2.py
-------------------

Calibration tool for HX711 using blocking HX711 driver.

Workflow:
1. Stop running hxFiBird process (if active)
2. Measure unloaded baseline
3. Measure known calibration weight
4. Compute scale factor
5. Refine offset
6. Save to config.json
"""

import os
import signal
import time
import numpy as np

from lgpioBird.HX711 import HX711
from sharedBird import roundFlt, readPID
from configBird3 import hxDataPin, hxClckPin, update_config_json


# ---------------- Configuration ----------------
NUM_VALS = 100
SLEEP_BETWEEN_SAMPLES = 0.2


# ---------------- Helper: sample median ----------------
def get_mean(sensor, num_vals):
    """Take multiple raw readings and return median + stats"""
    print(f"Sampling {num_vals} readings...")
    readings_np = np.empty(shape=num_vals, dtype=float)

    for i in range(num_vals):
        readings_np[i] = sensor.read_raw()
        time.sleep(SLEEP_BETWEEN_SAMPLES)

    median_val = np.median(readings_np)
    min_val = np.min(readings_np)
    max_val = np.max(readings_np)
    spread = max_val - min_val

    print(f"median: {median_val}, spread: {spread} ({min_val} to {max_val})")
    return median_val


# ---------------- Stop hxFiBird if running ----------------
hxFiPID = readPID(1)
if hxFiPID != -1:
    try:
        pid_int = int(hxFiPID)
        print(f"Stopping hxFiBird (PID {pid_int})...")
        os.kill(pid_int, signal.SIGTERM)
        time.sleep(1)
    except ProcessLookupError:
        print("Process already stopped.")
    except Exception as e:
        print(f"Could not stop hxFiBird: {e}")
else:
    print("hxFiBird not running.")


# ---------------- Initialize HX711 ----------------
print("\nInitializing HX711...")
hx = HX711(
    data_pin=hxDataPin,
    clock_pin=hxClckPin,
    chip=0
)
print("HX711 ready.\n")


# ---------------- Measure unloaded baseline ----------------
input("Remove all weights from scale and press ENTER...")
time.sleep(2)
mean_no_load = get_mean(hx, NUM_VALS)


# ---------------- Measure known weight ----------------
while True:
    cal_weight_str = input("Place calibration weight and enter grams: ")
    try:
        cal_weight = float(cal_weight_str)
        if cal_weight > 0:
            print(f"Calibration weight: {cal_weight} g")
            break
    except ValueError:
        pass
    print("Enter a positive numeric value.")

time.sleep(2)
mean_load = get_mean(hx, NUM_VALS)


# ---------------- Compute scale factor ----------------
delta = mean_load - mean_no_load
scale_factor = delta / cal_weight
print(f"\nScale factor: {scale_factor} raw units per gram")


# ---------------- Refine offset ----------------
offset = mean_no_load
print("\nRefining offset...")

for _ in range(10):
    raw = hx.read_raw()
    digress = roundFlt((raw - offset) / scale_factor - cal_weight)
    offset += digress * scale_factor

    print(f"Deviation: {digress} g")

    if abs(digress) <= 1:
        break

    time.sleep(0.5)


# ---------------- Verify zero ----------------
input("\nRemove weight and press ENTER. Check readings near 0 g.")

for _ in range(10):
    raw = hx.read_raw()
    reading = roundFlt((raw - offset) / scale_factor)
    print(f"{reading} g")
    time.sleep(0.3)


# ---------------- Save configuration ----------------
offset = round(offset)
scale_factor = round(scale_factor)

print(f"\nSaving: hxOffset={offset}, hxScale={scale_factor}")
update_config_json({"hxOffset": offset, "hxScale": scale_factor})


# ---------------- Cleanup ----------------
hx.close()
print("\nCalibration complete. Reboot recommended.")