"""
Minimal HX711 raw read test using old lgpio behavior.
Ignores DATA pin claim failure, only reads raw HX711 values.
"""

import time
import lgpio

# HX711 pins (BCM)
DATA_PIN = 17   # DATA
CLOCK_PIN = 23  # SCK

print("Opening GPIO chip...")
gpio = lgpio
fd = gpio.gpiochip_open(0)
print(f"GPIO chip fd: {fd}")

# Try to claim CLOCK pin as output
try:
    gpio.gpio_claim_output(fd, 0, CLOCK_PIN, 0)
    print(f"CLOCK pin {CLOCK_PIN} claimed as output ✅")
except Exception as e:
    print(f"CLOCK pin claim failed ❌: {e}")

# Attempt to claim DATA pin as input (may fail)
try:
    gpio.gpio_claim_input(fd, 0, DATA_PIN)
    print(f"DATA pin {DATA_PIN} claimed as input ✅")
except Exception as e:
    print(f"DATA pin claim failed ❌: {e}")

def hx711_read_once():
    """Read one 24-bit sample from HX711 using old behavior."""
    # Wait for DATA low
    timeout = time.time() + 1.0
    while gpio.gpio_read(fd, DATA_PIN) != 0:
        if time.time() > timeout:
            print("Timeout waiting for DATA=0")
            return None
        time.sleep(0.001)

    # Read 24 bits
    value = 0
    for _ in range(24):
        gpio.gpio_write(fd, CLOCK_PIN, 1)
        bit = gpio.gpio_read(fd, DATA_PIN)
        value = (value << 1) | bit
        gpio.gpio_write(fd, CLOCK_PIN, 0)

    # 3 extra pulses for gain 64
    for _ in range(3):
        gpio.gpio_write(fd, CLOCK_PIN, 1)
        gpio.gpio_write(fd, CLOCK_PIN, 0)

    # Convert signed
    if value & 0x800000:
        value -= 1 << 24
    return value

print("Reading HX711 raw values (CTRL+C to stop)...")
try:
    while True:
        raw = hx711_read_once()
        if raw is not None:
            print(f"RAW={raw}")
        time.sleep(0.1)
except KeyboardInterrupt:
    print("Exiting...")

# Cleanup
gpio.gpiochip_close(fd)
print("GPIO chip closed.")