"""
HX711.py — Lean, stable HX711 driver for Raspberry Pi (lgpio, Trixie+)
=====================================================================

Design goals
------------
• Deterministic behavior (no implicit tare or drift)
• Minimal API surface (bird scale = low sample rate, long uptime)
• Works with lgpio modern signature (gpiochip fd + flags)
• Robust against HX711 lockups (soft reset + retry)

Electrical assumptions
----------------------
• Gain fixed to 64 (Channel B not used)
• PD_SCK idles LOW
• Blocking reads are acceptable (typical 10–80 ms)

Typical usage
-------------
import lgpio
from HX711 import HX711

hx = HX711.create(lgpio, dout_pin=17, sck_pin=23)

offset = hx.stabilize()
hx.set_offset(offset)
hx.set_scale(1234.5)

weight = hx.get_weight()
"""

import time


class HX711:
    # ------------------------------------------------------------------
    # Construction helpers
    # ------------------------------------------------------------------

    @classmethod
    def create(cls, gpio, dout_pin, sck_pin, chip=0):
        """
        Convenience factory:
        Opens gpiochip and returns initialized HX711.
        """
        fd = gpio.gpiochip_open(chip)
        return cls(gpio=gpio, gpio_fd=fd, dout_pin=dout_pin, sck_pin=sck_pin)

    # ------------------------------------------------------------------

    def __init__(self, gpio, gpio_fd, dout_pin, sck_pin):
        """
        Parameters
        ----------
        gpio : lgpio module
        gpio_fd : file descriptor from gpiochip_open()
        dout_pin : HX711 DATA pin (BCM numbering)
        sck_pin  : HX711 CLOCK pin (BCM numbering)
        """
        self.gpio = gpio
        self.gpio_fd = gpio_fd
        self.dout = dout_pin
        self.sck = sck_pin

        self.offset = 0.0
        self.scale = 1.0
        self.fail_count = 0
        self.last_read_time = None

        self._configure_pins()
        self._ensure_clock_low()

    # ------------------------------------------------------------------
    # GPIO configuration
    # ------------------------------------------------------------------

    def _configure_pins(self):
        """
        Claim GPIO lines using Trixie lgpio signature:

            gpio_claim_input(handle, flags, gpio)
            gpio_claim_output(handle, flags, gpio, initial_level)

        flags = 0  → normal user-space safe claim
        """
        self.gpio.gpio_claim_input(self.gpio_fd, 0, self.dout)
        self.gpio.gpio_claim_output(self.gpio_fd, 0, self.sck, 0)

    def _ensure_clock_low(self):
        """Ensure HX711 starts in normal conversion mode."""
        self.gpio.gpio_write(self.gpio_fd, self.sck, 0)
        time.sleep(0.001)

    # ------------------------------------------------------------------
    # Low-level helpers
    # ------------------------------------------------------------------

    def _data_low(self):
        """HX711 ready when DATA line goes LOW."""
        return self.gpio.gpio_read(self.gpio_fd, self.dout) == 0

    def _set_clock(self, high: bool):
        """Toggle SCK line."""
        self.gpio.gpio_write(self.gpio_fd, self.sck, 1 if high else 0)

    # ------------------------------------------------------------------
    # Recovery / reset
    # ------------------------------------------------------------------

    def _soft_reset(self):
        """
        HX711 reset:
        Hold clock HIGH > 60 µs → power-down → release.
        """
        self._set_clock(True)
        time.sleep(0.00008)
        self._set_clock(False)
        time.sleep(0.01)

    def reinitialize(self):
        """Reset and re-claim pins (used after timeout)."""
        self._soft_reset()
        self._configure_pins()
        self._ensure_clock_low()

    # ------------------------------------------------------------------
    # Wait for conversion ready
    # ------------------------------------------------------------------

    def wait_ready(self, timeout=1.0, retries=3):
        """
        Block until HX711 signals ready.
        Raises TimeoutError after retries.
        """
        for _ in range(retries):
            start = time.monotonic()
            while time.monotonic() - start < timeout:
                if self._data_low():
                    return
                time.sleep(0.001)

            self._soft_reset()

        self.fail_count += 1
        raise TimeoutError("HX711 not ready (DATA stuck high)")

    # ------------------------------------------------------------------
    # Core read
    # ------------------------------------------------------------------

    def _read_once(self):
        """
        Read one signed 24-bit sample.
        Gain fixed to 64 → 3 extra pulses.
        """
        self.wait_ready()

        value = 0
        for _ in range(24):
            self._set_clock(True)
            value = (value << 1) | self.gpio.gpio_read(self.gpio_fd, self.dout)
            self._set_clock(False)

        # Gain = 64 → 3 pulses
        for _ in range(3):
            self._set_clock(True)
            self._set_clock(False)

        # Convert to signed
        if value & 0x800000:
            value -= 1 << 24

        self.last_read_time = time.monotonic()
        return value

    def read_raw(self):
        """
        Read raw value with automatic recovery.
        """
        try:
            return self._read_once()
        except TimeoutError:
            self.reinitialize()
            return self._read_once()

    # ------------------------------------------------------------------
    # Averaging / stabilization
    # ------------------------------------------------------------------

    def read_average(self, samples=10, delay=0.01):
        """Simple mean of multiple readings."""
        total = 0
        for _ in range(samples):
            total += self.read_raw()
            if delay:
                time.sleep(delay)
        return total / samples

    def stabilize(self, samples=30, delay=0.01):
        """
        Robust startup baseline:
        median-window around center to reject spikes.
        """
        readings = [self.read_raw() for _ in range(samples)]
        readings.sort()

        mid = len(readings) // 2
        window = readings[mid - 2: mid + 3] if len(readings) >= 5 else readings
        return sum(window) / len(window)

    # ------------------------------------------------------------------
    # Calibration parameters
    # ------------------------------------------------------------------

    def set_offset(self, offset):
        """Set raw offset (zero reference)."""
        self.offset = float(offset)

    def set_scale(self, scale):
        """Set raw units per gram (or chosen unit)."""
        self.scale = float(scale)

    def get_weight(self, samples=5):
        """
        Return scaled weight using current calibration.
        """
        raw = self.read_average(samples)
        return (raw - self.offset) / self.scale

    # ------------------------------------------------------------------
    # Diagnostics
    # ------------------------------------------------------------------

    def health(self):
        """Return diagnostic counters."""
        return {
            "fail_count": self.fail_count,
            "last_read_time": self.last_read_time,
        }

    # ------------------------------------------------------------------
    # Cleanup
    # ------------------------------------------------------------------

    def close(self):
        """
        Optional cleanup.
        lgpio releases lines automatically when fd closes.
        """
        try:
            self.gpio.gpiochip_close(self.gpio_fd)
        except Exception:
            pass