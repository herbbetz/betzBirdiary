from HX711 import HX711
import time

# Initialize with GPIO17 (DATA) and GPIO23 (CLOCK)
hx = HX711(data_pin=17, clock_pin=23)

# Tare the scale (no weight on it)
hx.tare()

# Set scale factor (raw units per gram or your chosen unit)
# Example: if 100g = 20000 raw units → scale = 20000 / 100 = 200
hxScale = 700
hxOffset = 0

try:
    while True:
        raw = hx.read_raw()
        weight = round((raw + hxOffset) / hxScale)
        print(f"Weight: {weight:.2f} g")
        time.sleep(1)
except KeyboardInterrupt:
    print("Exiting.")
finally:
    hx.close()
