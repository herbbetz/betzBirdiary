# hx711_lgpio_hardened.py
#
# HX711 load cell ADC reader using lgpio
# Hardened against Linux scheduling jitter and HX711 timing glitches
#
# - Bit-banged clock with relaxed timing
# - Median-of-3 sampling to eliminate single-sample corruption
# - Spike rejection to suppress impossible jumps
# - Fixed gain (64) enforced every read
#
# Returns ONLY raw 24-bit signed values
# Scaling and offset are handled externally
# 12/2025 ChatGPT

import lgpio
import time
import numpy as np


class HX711:
    """
    HX711 load cell ADC reader using lgpio.
    Designed for Linux SBCs (Raspberry Pi).
    """

    def __init__(self, data_pin=17, clock_pin=23, chip=0):
        self.data_pin = data_pin
        self.clock_pin = clock_pin
        self.chip = lgpio.gpiochip_open(chip)

        # DATA is input, CLOCK is output
        lgpio.gpio_claim_input(self.chip, self.data_pin)
        lgpio.gpio_claim_output(self.chip, self.clock_pin, 0)

        # Keep last valid reading to reject impossible spikes
        self.last_value = None

    # ------------------------------------------------------------------
    # Timing helpers
    # ------------------------------------------------------------------

    def delay_us(self, microseconds):
        """
        Busy-wait microsecond delay.
        More stable than time.sleep() for sub-millisecond timing.
        """
        start = time.perf_counter_ns()
        end = start + int(microseconds * 1000)
        while time.perf_counter_ns() < end:
            pass

    def wait_ready(self, timeout=1.0):
        """
        Wait until HX711 pulls DATA low (conversion ready).
        """
        start = time.time()
        while time.time() - start < timeout:
            if lgpio.gpio_read(self.chip, self.data_pin) == 0:
                return True
            time.sleep(0.001)
        raise TimeoutError("HX711 not ready within timeout")

    # ------------------------------------------------------------------
    # Low-level single read
    # ------------------------------------------------------------------

    def _read_once(self):
        """
        Read one raw 24-bit signed value from HX711.
        This function performs NO filtering.
        """
        self.wait_ready()

        value = 0

        # Read 24 data bits, MSB first
        for _ in range(24):
            lgpio.gpio_write(self.chip, self.clock_pin, 1)
            self.delay_us(3)   # relaxed timing for Linux
            value = (value << 1) | lgpio.gpio_read(self.chip, self.data_pin)
            lgpio.gpio_write(self.chip, self.clock_pin, 0)
            self.delay_us(3)

        # Enforce gain = 64 by sending exactly 3 extra clock pulses
        for _ in range(3):
            lgpio.gpio_write(self.chip, self.clock_pin, 1)
            self.delay_us(3)
            lgpio.gpio_write(self.chip, self.clock_pin, 0)
            self.delay_us(3)

        # Convert unsigned 24-bit to signed Python int
        if value & 0x800000:
            value -= 0x1000000

        return value

    # ------------------------------------------------------------------
    # Public read with filtering
    # ------------------------------------------------------------------

    def read_raw(self):
        """
        Robust read:
        - read 3 consecutive samples
        - take integer median (sorted(vals)[1])
        - reject impossible single-step spikes
        """

        # Median-of-3 eliminates single corrupted samples
        vals = [self._read_once() for _ in range(3)]
        value = sorted(vals)[1]   # fastest integer median for 3 values

        # Reject sudden impossible jumps (bit-slip / gain glitch)
        if self.last_value is not None:
            # Threshold tuned for HX711 full-scale (adjust if needed)
            if abs(value - self.last_value) > 200_000:
                return self.last_value

        self.last_value = value
        return value

    # ------------------------------------------------------------------
    # Utilities
    # ------------------------------------------------------------------

    def tare(self, samples=15):
        """
        Average several readings to establish zero offset.
        """
        total = 0
        for _ in range(samples):
            total += self.read_raw()
            time.sleep(0.1)
        return total / samples

    def power_down(self):
        """
        Power down HX711 (CLOCK high for >60 us).
        """
        lgpio.gpio_write(self.chip, self.clock_pin, 1)
        self.delay_us(80)

    def power_up(self):
        """
        Wake up HX711.
        """
        lgpio.gpio_write(self.chip, self.clock_pin, 0)
        self.delay_us(100)

    def close(self):
        """
        Release GPIO resources.
        """
        lgpio.gpiochip_close(self.chip)
