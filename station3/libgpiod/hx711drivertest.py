#!/usr/bin/env python3
"""
hx711drivertest.py — diagnostic for HX711 using portable v1 libgpiod driver.

Features:
- Reads raw ADC and converted weight
- Rolling window statistics
- Spike detection
- Offset stabilization at startup
"""

import time
import statistics
from datetime import datetime
from HX711 import HX711

# ---------------- CONFIG ----------------
CHIP = "/dev/gpiochip0"
DOUT = 17
SCK = 23
HX_SCALE = 2100.0
HX_OFFSET = None   # Auto-stabilize if None
SAMPLE_RATE = 0.2
WINDOW_SIZE = 50
SPIKE_THRESHOLD = 15000
# ----------------------------------------

hx = HX711(chip=CHIP, dout_line=DOUT, sck_line=SCK)
hx.set_scale(HX_SCALE)

print("HX711 Diagnostic Starting…")

# Stabilize offset at startup
if HX_OFFSET is None:
    print("Stabilizing offset… keep the scale empty")
    HX_OFFSET = hx.stabilize()
    print(f"Offset = {HX_OFFSET:.2f}")
hx.set_offset(HX_OFFSET)

# Rolling window for statistics
raw_window = []
last_raw = None

try:
    while True:
        raw = hx.read_raw()
        weight = (raw - HX_OFFSET) / HX_SCALE

        raw_window.append(raw)
        if len(raw_window) > WINDOW_SIZE:
            raw_window.pop(0)

        spike_warning = ""
        if last_raw is not None and abs(raw - last_raw) > SPIKE_THRESHOLD:
            spike_warning = "⚠ SPIKE"
        last_raw = raw

        if len(raw_window) >= 5:
            mean = statistics.mean(raw_window)
            std = statistics.pstdev(raw_window)
            mn = min(raw_window)
            mx = max(raw_window)
        else:
            mean = std = mn = mx = 0

        now = datetime.now().strftime("%H:%M:%S")
        print(
            f"{now} | raw={raw:8d} | g={weight:7.2f} | "
            f"μ={mean:8.1f} | σ={std:6.1f} | min={mn:8d} | max={mx:8d} {spike_warning}"
        )

        time.sleep(SAMPLE_RATE)

except KeyboardInterrupt:
    print("\nStopping diagnostic…")

finally:
    hx.close()
    print("HX711 GPIO released.")