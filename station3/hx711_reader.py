"""
hx711_reader.py
-----------------------

Minimal runtime test for calibrated HX711.

• Uses current HX711.py driver
• Loads hxOffset + hxScale from config.json
• Prints RAW and grams continuously

Purpose:
Verify live response and drift before integrating
into hxFiBirdState logic.
"""

import time
import json
from lgpioBird.HX711 import HX711
from configBird3 import hxDataPin, hxClckPin, hxOffset, hxScale

# ------------------------------------------------------------
# Load calibration values
# ------------------------------------------------------------
print("Loaded calibration:")
print(f"  Offset: {hxOffset}")
print(f"  Scale : {hxScale} raw/g")

# ------------------------------------------------------------
# Initialize HX711
# ------------------------------------------------------------
print("\nInitializing HX711...")
hx = HX711(data_pin=hxDataPin, clock_pin=hxClckPin)
print("HX711 ready. Reading continuously (CTRL+C to stop)\n")

# ------------------------------------------------------------
# Continuous read loop
# ------------------------------------------------------------
try:
    while True:
        raw = hx.read_raw()
        grams = (raw - hxOffset) / hxScale
        print(f"RAW={raw:8d}   {grams:7.2f} g")
        time.sleep(0.2)

except KeyboardInterrupt:
    print("\nStopping...")

finally:
    hx.close()
    print("HX711 closed.")