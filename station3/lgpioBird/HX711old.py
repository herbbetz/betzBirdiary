# hx711_lgpio_blocking.py
#
# HX711 load cell ADC reader using lgpio
# Designed for low-rate, high-reliability operation (≤10 SPS)
#
# - _read_once() blocks until DATA goes low
# - Median-of-3 filtering in read_raw()
# - Spike rejection to suppress bit-slip errors
# - Fixed gain = 64 enforced every read
#
# Returns ONLY raw signed 24-bit values
# Offset and scaling handled externally
#
# 12/2025 ChatGPT (refactored)

import lgpio
import time


class HX711:
    def __init__(self, data_pin=17, clock_pin=23, chip=0):
        self.data_pin = data_pin
        self.clock_pin = clock_pin
        self.chip = lgpio.gpiochip_open(chip)

        lgpio.gpio_claim_input(self.chip, self.data_pin)
        lgpio.gpio_claim_output(self.chip, self.clock_pin, 0)

        self.last_value = None

    # ------------------------------------------------------------
    # Timing helper
    # ------------------------------------------------------------

    def delay_us(self, microseconds):
        """Busy-wait microsecond delay (Linux-safe)."""
        end = time.perf_counter_ns() + int(microseconds * 1000)
        while time.perf_counter_ns() < end:
            pass

    # ------------------------------------------------------------
    # Blocking wait
    # ------------------------------------------------------------

    def wait_ready(self):
        """
        Block until HX711 DATA goes low.
        Safe because read rate is very low (≤10 SPS).
        """
        while lgpio.gpio_read(self.chip, self.data_pin) == 1:
            time.sleep(0.001)  # yield CPU

    # ------------------------------------------------------------
    # Low-level single read (NO filtering)
    # ------------------------------------------------------------

    def _read_once(self):
        """
        Blocking read of one 24-bit signed HX711 value.
        """
        self.wait_ready()

        value = 0

        # Read 24 bits MSB first
        for _ in range(24):
            lgpio.gpio_write(self.chip, self.clock_pin, 1)
            self.delay_us(3)
            value = (value << 1) | lgpio.gpio_read(self.chip, self.data_pin)
            lgpio.gpio_write(self.chip, self.clock_pin, 0)
            self.delay_us(3)

        # Set gain = 64 (3 extra pulses)
        for _ in range(3):
            lgpio.gpio_write(self.chip, self.clock_pin, 1)
            self.delay_us(3)
            lgpio.gpio_write(self.chip, self.clock_pin, 0)
            self.delay_us(3)

        # Convert to signed 24-bit
        if value & 0x800000:
            value -= 0x1000000

        return value

    # ------------------------------------------------------------
    # Public read (median + spike rejection)
    # ------------------------------------------------------------

    def read_raw(self):
        """
        Robust read:
        - Take 3 blocking samples
        - Median-of-3 filtering
        - Reject impossible jumps
        """

        samples = [
            self._read_once(),
            self._read_once(),
            self._read_once(),
        ]

        value = sorted(samples)[1]

        # Spike rejection (bit-slip / gain glitch)
        if self.last_value is not None:
            if abs(value - self.last_value) > 200_000:
                return self.last_value

        self.last_value = value
        return value

    # ------------------------------------------------------------
    # Utilities
    # ------------------------------------------------------------

    def tare(self, samples=15):
        total = 0
        for _ in range(samples):
            total += self.read_raw()
            time.sleep(0.1)
        return total / samples

    def power_down(self):
        lgpio.gpio_write(self.chip, self.clock_pin, 1)
        self.delay_us(80)

    def power_up(self):
        lgpio.gpio_write(self.chip, self.clock_pin, 0)
        self.delay_us(100)

    def close(self):
        lgpio.gpiochip_close(self.chip)
