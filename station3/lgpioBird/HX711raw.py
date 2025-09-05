# script for testing out hx711 with lgpio as a preparation to building the class (ChatGPT June 2025)
import lgpio
import time

# Pin configuration
DATA_PIN = 17   # GPIO17 -> HX711 DT
CLOCK_PIN = 23  # GPIO23 -> HX711 SCK

# Open GPIO chip
chip = lgpio.gpiochip_open(0)

# Configure pins
lgpio.gpio_claim_input(chip, DATA_PIN)
lgpio.gpio_claim_output(chip, CLOCK_PIN, 0)

def delay_us(microseconds):
    """Busy-wait delay for accurate microsecond timing."""
    start = time.perf_counter_ns()
    duration = int(microseconds * 1000)  # µs to ns
    while time.perf_counter_ns() - start < duration:
        pass

def wait_for_ready(timeout=1.0):
    """Wait for HX711 DATA line to go LOW (ready)."""
    start_time = time.time()
    while time.time() - start_time < timeout:
        if lgpio.gpio_read(chip, DATA_PIN) == 0:
            return True
        time.sleep(0.001)
    raise TimeoutError("HX711 not ready: DATA pin stayed HIGH")

def read_raw_debug():
    """Read 24-bit raw data from HX711 and print bitstream."""
    wait_for_ready()

    bits = []

    for _ in range(24):
        lgpio.gpio_write(chip, CLOCK_PIN, 1)
        delay_us(2)
        bit = lgpio.gpio_read(chip, DATA_PIN)
        bits.append(str(bit))
        lgpio.gpio_write(chip, CLOCK_PIN, 0)
        delay_us(2)

    # Pulse clock 3 more times for GAIN = 64
    for _ in range(3):
        lgpio.gpio_write(chip, CLOCK_PIN, 1)
        delay_us(2)
        lgpio.gpio_write(chip, CLOCK_PIN, 0)
        delay_us(2)

    bitstring = ''.join(bits)
    print("Raw bits:       ", bitstring)

    value = int(bitstring, 2)
    if value & 0x800000:
        value -= 0x1000000  # Convert from 24-bit two's complement
    print("Converted value:", value)
    return value

try:
    while True:
        read_raw_debug()
        time.sleep(1.0)
except KeyboardInterrupt:
    print("\nExiting.")
finally:
    lgpio.gpiochip_close(chip)
