import numpy as np
import subprocess
import time
from lgpioBird.HX711 import HX711
from sharedBird import roundFlt, readPID
from configBird3 import birdpath, hxDataPin, hxClckPin, update_config_json

NUM_VALS = 100
SLEEP_BETWEEN_SAMPLES = 0.2
config_path = f"{birdpath['appdir']}/config.json"  # Adjust if using full path

def get_mean(sensor, num_vals):
    print(f"Sampling {num_vals} readings...")
    readings_np = np.empty(shape=num_vals, dtype=float)

    for i in range(num_vals):
        raw = sensor.read_raw()
        readings_np[i] = raw
        time.sleep(SLEEP_BETWEEN_SAMPLES)

    mean_val = np.median(readings_np)
    min_val = np.min(readings_np)
    max_val = np.max(readings_np)
    spread = max_val - min_val

    print(f"{num_vals} elements read")
    print(f"median: {mean_val}")
    print(f"spread: {spread} ({min_val} to {max_val})")

    return mean_val

# --- Stop any running script that uses the HX711
hxFiPID = readPID(1)
if hxFiPID == -1:
    print("hxFiBird.py not running...")
else:
    print("Stopping hxFiBird.py...")
    subprocess.call(f"kill {hxFiPID}", shell=True)
    time.sleep(1)

# --- Init sensor
hx = HX711(data_pin=hxDataPin, clock_pin=hxClckPin)

# --- Unloaded measurement
input("Remove all loads from balance, then press ENTER...")
print("Sampling unloaded state...")
time.sleep(2)
mean_no_load = get_mean(hx, NUM_VALS)

# --- Known weight
while True:
    cal_weight_str = input("Now load the balance with a known calibration weight.\nEnter its weight in full grams (digits only): ")
    if cal_weight_str.isnumeric():
        cal_weight = float(cal_weight_str)
        if cal_weight > 0:
            print(f"You entered: {cal_weight} grams")
            break
        else:
            print("Please enter a positive number.")
    else:
        print("Digits only, please.")

# --- Loaded measurement
print("Sampling loaded state...")
time.sleep(2)
mean_load = get_mean(hx, NUM_VALS)

delta = mean_load - mean_no_load
scale_factor = delta / cal_weight
print(f"Scale factor: {scale_factor} reading units / gram")

# --- Adjust offset to match calibration weight
print("Adjusting offset to make reading match calibration weight...")
hx.offset = mean_no_load

for _ in range(10):
    raw = hx.read_raw()
    digress = roundFlt((raw - mean_no_load) / scale_factor - cal_weight)
    mean_no_load += digress * scale_factor
    print(f"Still deviates by: {digress} g")
    if abs(digress) <= 1:
        break
    time.sleep(0.5)

# --- Unload and verify zero
input("Now unload the balance, then press ENTER. You should see values near 0.0")
for _ in range(10):
    raw = hx.read_raw()
    reading = roundFlt((raw - mean_no_load) / scale_factor)
    print(f"{reading} g")

# --- Final output
mean_no_load = round(mean_no_load)
scale_factor = round(scale_factor)
print("---- SAVED THESE VALUES TO YOUR CONFIG FILE ----")
print(f"offset (units without load): {mean_no_load}")
print(f"scaleFactor (units per gram): {scale_factor}")

update_config_json({"hxOffset": mean_no_load, "hxScale": scale_factor})
print("If no more gram measurements please reboot.")
hx.close()