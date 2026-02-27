# HX711.py
# Stable HX711 driver for lgpio 0.2.x
# Pure raw reader — no scaling, no calibration

import lgpio
import time


class HX711:
    def __init__(self, data_pin=17, clock_pin=23, chip=0):
        self.data_pin = data_pin
        self.clock_pin = clock_pin

        # Open GPIO chip (old lgpio style)
        self.chip = lgpio.gpiochip_open(chip)

        # Claim pins (this order is known to work)
        lgpio.gpio_claim_input(self.chip, self.data_pin)
        lgpio.gpio_claim_output(self.chip, self.clock_pin, 0)

        self.last_value = None

    # ------------------------------------------------------------
    # Small timing helper (µs)
    # ------------------------------------------------------------
    def _delay_us(self, us):
        end = time.perf_counter_ns() + us * 1000
        while time.perf_counter_ns() < end:
            pass

    # ------------------------------------------------------------
    # Wait until HX711 is ready (DATA goes LOW)
    # ------------------------------------------------------------
    def wait_ready(self):
        while lgpio.gpio_read(self.chip, self.data_pin) == 1:
            time.sleep(0.001)

    # ------------------------------------------------------------
    # Single raw 24-bit read
    # ------------------------------------------------------------
    def _read_once(self):
        self.wait_ready()

        value = 0

        for _ in range(24):
            lgpio.gpio_write(self.chip, self.clock_pin, 1)
            self._delay_us(3)

            bit = lgpio.gpio_read(self.chip, self.data_pin)
            value = (value << 1) | bit

            lgpio.gpio_write(self.chip, self.clock_pin, 0)
            self._delay_us(3)

        # Gain = 64 (3 pulses)
        for _ in range(3):
            lgpio.gpio_write(self.chip, self.clock_pin, 1)
            self._delay_us(3)
            lgpio.gpio_write(self.chip, self.clock_pin, 0)
            self._delay_us(3)

        # Convert to signed 24-bit
        if value & 0x800000:
            value -= 0x1000000

        return value

    # ------------------------------------------------------------
    # Public read with filtering
    # ------------------------------------------------------------
    def read_raw(self):
        s1 = self._read_once()
        s2 = self._read_once()
        s3 = self._read_once()

        value = sorted([s1, s2, s3])[1]

        # Spike rejection
        if self.last_value is not None:
            if abs(value - self.last_value) > 200000:
                return self.last_value

        self.last_value = value
        return value

    # ------------------------------------------------------------
    # Cleanup
    # ------------------------------------------------------------
    def close(self):
        lgpio.gpiochip_close(self.chip)