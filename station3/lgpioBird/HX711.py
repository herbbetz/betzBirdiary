# HX711_lgpio_v2.py
#
# Hardened HX711 load cell ADC reader using lgpio
# Pure raw driver (no offset / scaling)
#
# Improvements:
# - Startup stabilization helper
# - Timeout protection in wait_ready()
# - Median-of-3 filtering
# - Spike rejection with safe initialization
# - read_average() replaces misleading tare()
#
# Returns ONLY raw signed 24-bit values
#
# 02/2026

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
        end = time.perf_counter_ns() + int(microseconds * 1000)
        while time.perf_counter_ns() < end:
            pass

    # ------------------------------------------------------------
    # Blocking wait with timeout
    # ------------------------------------------------------------

    def wait_ready(self, timeout=1.0):
        start = time.time()
        while lgpio.gpio_read(self.chip, self.data_pin) == 1:
            if (time.time() - start) > timeout:
                raise TimeoutError("HX711 not ready (DATA stuck high)")
            time.sleep(0.001)

    # ------------------------------------------------------------
    # Low-level single read (NO filtering)
    # ------------------------------------------------------------

    def _read_once(self):
        self.wait_ready()

        value = 0

        for _ in range(24):
            lgpio.gpio_write(self.chip, self.clock_pin, 1)
            self.delay_us(3)
            value = (value << 1) | lgpio.gpio_read(self.chip, self.data_pin)
            lgpio.gpio_write(self.chip, self.clock_pin, 0)
            self.delay_us(3)

        # Gain = 64 (3 pulses)
        for _ in range(3):
            lgpio.gpio_write(self.chip, self.clock_pin, 1)
            self.delay_us(3)
            lgpio.gpio_write(self.chip, self.clock_pin, 0)
            self.delay_us(3)

        # Convert signed 24-bit
        if value & 0x800000:
            value -= 0x1000000

        return value

    # ------------------------------------------------------------
    # Public read (median + spike rejection)
    # ------------------------------------------------------------

    def read_raw(self):
        samples = [
            self._read_once(),
            self._read_once(),
            self._read_once(),
        ]

        value = sorted(samples)[1]

        if self.last_value is None:
            self.last_value = value
            return value

        if abs(value - self.last_value) > 200_000:
            return self.last_value

        self.last_value = value
        return value

    # ------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------

    def stabilize(self, samples=10, delay=0.05):
        """
        Flush initial conversions to allow
        analog front-end + gain cycle to settle.
        Call once after power-up.
        """
        for _ in range(samples):
            try:
                self._read_once()
            except TimeoutError:
                pass
            time.sleep(delay)

    def read_average(self, samples=15, delay=0.1):
        """
        Return average raw reading.
        Useful for external calibration routines.
        """
        total = 0
        for _ in range(samples):
            total += self.read_raw()
            time.sleep(delay)
        return total / samples

    # ------------------------------------------------------------
    # Power control
    # ------------------------------------------------------------

    def power_down(self):
        lgpio.gpio_write(self.chip, self.clock_pin, 1)
        self.delay_us(80)

    def power_up(self):
        lgpio.gpio_write(self.chip, self.clock_pin, 0)
        self.delay_us(100)

    # ------------------------------------------------------------
    # Cleanup
    # ------------------------------------------------------------

    def close(self):
        lgpio.gpiochip_close(self.chip)