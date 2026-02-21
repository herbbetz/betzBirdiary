"""
HX711 driver — portable Python using v1-compatible libgpiod API
Gain fixed at 64, works on Raspberry Pi OS / Ubuntu / DietPi.
"""

import time
import gpiod

class HX711:
    def __init__(self, chip="/dev/gpiochip0", dout_line=17, sck_line=23):
        self.chip = gpiod.Chip(chip)

        # Use request_lines() with direction integers
        # Direction: 0=input, 1=output for your v1 bindings
        self.lines = self.chip.request_lines(
            [dout_line, sck_line],
            [0, 1],  # DATA=input (0), CLOCK=output (1)
            default_vals=[0, 0]
        )
        self.dout_idx = 0
        self.sck_idx = 1

        self.offset = 0.0
        self.scale = 1.0
        self.last_read = None
        self.fail_count = 0

    # GPIO helpers
    def _clock_high(self):
        vals = self.lines.get_values()
        vals[self.sck_idx] = 1
        self.lines.set_values(vals)

    def _clock_low(self):
        vals = self.lines.get_values()
        vals[self.sck_idx] = 0
        self.lines.set_values(vals)

    def _data_ready(self):
        return self.lines.get_values()[self.dout_idx] == 0

    def wait_ready(self, timeout=1.0):
        start = time.monotonic()
        while time.monotonic() - start < timeout:
            if self._data_ready():
                return
            time.sleep(0.001)
        self.fail_count += 1
        raise TimeoutError("HX711 not ready (DATA stuck high)")

    # Low-level read
    def _read_once(self):
        self.wait_ready()
        value = 0
        for _ in range(24):
            self._clock_high()
            value = (value << 1) | self.lines.get_values()[self.dout_idx]
            self._clock_low()
        # Gain 64 → 3 extra pulses
        for _ in range(3):
            self._clock_high()
            self._clock_low()
        if value & 0x800000:
            value -= 1 << 24
        self.last_read = time.monotonic()
        return value

    # Public read methods
    def read_raw(self):
        try:
            return self._read_once()
        except TimeoutError:
            # If stuck, retry once
            return self._read_once()

    def read_average(self, samples=10, delay=0.01):
        total = 0
        for _ in range(samples):
            total += self.read_raw()
            time.sleep(delay)
        return total / samples

    def stabilize(self, samples=30, delay=0.01):
        readings = [self.read_raw() for _ in range(samples)]
        readings.sort()
        mid = len(readings)//2
        window = readings[mid-2:mid+3] if len(readings) >=5 else readings
        return sum(window)/len(window)

    # Offset / scale
    def set_offset(self, offset):
        self.offset = float(offset)

    def set_scale(self, scale):
        self.scale = float(scale)

    def get_weight(self, samples=5):
        raw = self.read_average(samples=samples)
        return (raw - self.offset)/self.scale

    # Cleanup
    def close(self):
        self.lines.release()
        self.chip.close()