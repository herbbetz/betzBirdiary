"""
HX711 lean driver (fixed gain = 64)
-----------------------------------

Purpose:
- Long-running, low-rate load-cell reading (bird feeder scale)
- Maximum stability, minimal configuration surface
- Works with Raspbian Trixie lgpio (fd + module)

Design choices:
- Gain permanently fixed to 64 (3 post-read pulses)
- Blocking read with timeout + soft-reset recovery
- Median-style stabilization helper for boot calibration
- Simple averaging for runtime smoothing
- Explicit offset handling (no implicit tare drift)

Failure handling:
- If DATA stays high → soft reset → retry
- If still failing → raise TimeoutError so caller watchdog can react

Typical usage:
    import lgpio
    from HX711 import HX711

    fd = lgpio.gpiochip_open(0)
    hx = HX711(gpio=lgpio, gpio_fd=fd, dout_pin=17, sck_pin=23)
    offset = hx.stabilize()
    hx.set_offset(offset)
    raw = hx.read_average(5)
    weight = hx.get_weight()
"""

import time

class HX711:
    def __init__(self, gpio, gpio_fd, dout_pin, sck_pin):
        self.gpio = gpio          # lgpio module
        self.gpio_fd = gpio_fd    # integer file descriptor from gpiochip_open
        self.dout = dout_pin
        self.sck = sck_pin

        self.offset = 0.0
        self.scale = 1.0
        self.fail_count = 0
        self.last_read_time = None

        self._configure_pins()
        self._ensure_clock_low()

    # ----------------- GPIO helpers -----------------
    def _configure_pins(self):
        """Claim GPIO pins as input/output."""
        self.gpio.gpio_claim_input(self.gpio_fd, self.dout)
        self.gpio.gpio_claim_output(self.gpio_fd, self.sck)
        self.gpio.gpio_write(self.gpio_fd, self.sck, 0)

    def _data_low(self):
        """Check if HX711 DATA line is low."""
        return self.gpio.gpio_read(self.gpio_fd, self.dout) == 0

    def _set_clock(self, value: bool):
        """Set SCK high/low."""
        self.gpio.gpio_write(self.gpio_fd, self.sck, 1 if value else 0)

    def _ensure_clock_low(self):
        """Ensure clock line starts low."""
        self._set_clock(False)
        time.sleep(0.001)

    # ----------------- Reset / recovery -----------------
    def _soft_reset(self):
        """PD_SCK high >60µs → power down → release."""
        self._set_clock(True)
        time.sleep(0.00008)
        self._set_clock(False)
        time.sleep(0.01)

    def reinitialize(self):
        """Soft reset + reconfigure pins."""
        self._soft_reset()
        self._configure_pins()
        self._ensure_clock_low()

    # ----------------- Wait for conversion -----------------
    def wait_ready(self, timeout=1.0, retries=3):
        """Block until DATA goes low or retry/reset."""
        for _ in range(retries):
            start = time.monotonic()
            while time.monotonic() - start < timeout:
                if self._data_low():
                    return
                time.sleep(0.001)
            self._soft_reset()

        self.fail_count += 1
        raise TimeoutError("HX711 not ready (DATA stuck high)")

    # ----------------- Core read (24-bit + gain 64) -----------------
    def _read_once(self):
        """Read one signed 24-bit value from HX711."""
        self.wait_ready()
        value = 0
        for _ in range(24):
            self._set_clock(True)
            value = (value << 1) | self.gpio.gpio_read(self.gpio_fd, self.dout)
            self._set_clock(False)

        # 3 extra pulses for gain=64
        for _ in range(3):
            self._set_clock(True)
            self._set_clock(False)

        # convert to signed 24-bit
        if value & 0x800000:
            value -= 1 << 24

        self.last_read_time = time.monotonic()
        return value

    def read_raw(self):
        """Read raw value, auto-recover on timeout."""
        try:
            return self._read_once()
        except TimeoutError:
            self.reinitialize()
            return self._read_once()

    # ----------------- Averaging / stabilization -----------------
    def read_average(self, samples=10, delay=0.01):
        """Return average of multiple reads."""
        total = 0
        for _ in range(samples):
            total += self.read_raw()
            if delay:
                time.sleep(delay)
        return total / samples

    def stabilize(self, samples=30, delay=0.01):
        """Return stabilized median-of-5 around center."""
        readings = [self.read_raw() for _ in range(samples)]
        readings.sort()
        mid = len(readings) // 2
        window = readings[mid - 2: mid + 3] if len(readings) >= 5 else readings
        return sum(window) / len(window)

    # ----------------- Offset / scaling -----------------
    def set_offset(self, offset):
        self.offset = float(offset)

    def set_scale(self, scale):
        self.scale = float(scale)

    def get_weight(self, samples=5):
        """Return weight in grams/units, applying offset & scale."""
        raw = self.read_average(samples)
        return (raw - self.offset) / self.scale

    # ----------------- Diagnostics -----------------
    def health(self):
        return {
            "fail_count": self.fail_count,
            "last_read_time": self.last_read_time,
        }

    # ----------------- Close -----------------
    def close(self):
        """Release pins if needed (lgpio handles this on fd close)."""
        pass