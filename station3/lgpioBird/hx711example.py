"""
HX711 example using lean lgpio driver

- Initializes HX711 (DATA/CLOCK)
- Stabilizes offset at startup
- Applies scale
- Prints weight every second
- Compatible with Raspbian Trixie lgpio (fd + module)
"""

import lgpio
from lgpioBird.HX711 import HX711
import time

# ----------------- GPIO configuration -----------------
DATA_PIN = 17
CLOCK_PIN = 23

# ----------------- Open GPIO chip -----------------
# Returns an integer file descriptor in this lgpio version
GPIO_FD = lgpio.gpiochip_open(0)

# ----------------- Initialize HX711 driver -----------------
hx = HX711(gpio=lgpio, gpio_fd=GPIO_FD, dout_pin=DATA_PIN, sck_pin=CLOCK_PIN)

# ----------------- Startup stabilization -----------------
time.sleep(1.0)              # let analog front-end settle
hxOffset = hx.stabilize()    # median-of-5 stabilization
hx.set_offset(hxOffset)

# ----------------- Apply scale -----------------
hxScale = 700
hx.set_scale(hxScale)

print(f"Initial offset: {hxOffset}, scale: {hxScale}")

# ----------------- Main reading loop -----------------
try:
    while True:
        weight = hx.get_weight(samples=5)
        print(f"Weight: {weight:.2f} g")
        time.sleep(1.0)

except KeyboardInterrupt:
    print("Exiting.")

finally:
    hx.close()
    lgpio.gpiochip_close(GPIO_FD)