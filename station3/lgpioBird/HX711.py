"""
HX711 driver for OLD lgpio versions
Compatible with environments where gpio_claim_input fails
but gpio_read works.

Only minimal GPIO calls are used.
"""

import time


class HX711:
    def __init__(self, dout_pin, sck_pin, chip=0, gpio_module=None):
        import lgpio

        self.gpio = gpio_module if gpio_module else lgpio
        self.chip = chip
        self.dout = dout_pin
        self.sck = sck_pin

        # open gpiochip
        self.fd = self.gpio.gpiochip_open(self.chip)

        # claim CLOCK as output (DATA left unclaimed!)
        try:
            self.gpio.gpio_claim_output(self.fd, 0, self.sck, 0)
        except Exception:
            pass

        self.offset = 0
        self.scale = 1.0

    # -------------------------------------------------

    def is_ready(self):
        return self.gpio.gpio_read(self.fd, self.dout) == 0

    # -------------------------------------------------

    def read_raw(self):
        # wait until chip ready
        timeout = time.time() + 1
        while not self.is_ready():
            if time.time() > timeout:
                raise RuntimeError("HX711 not ready")
            time.sleep(0.001)

        count = 0

        for _ in range(24):
            self.gpio.gpio_write(self.fd, self.sck, 1)
            count = count << 1
            self.gpio.gpio_write(self.fd, self.sck, 0)

            if self.gpio.gpio_read(self.fd, self.dout):
                count += 1

        # set channel/gain (1 pulse = channel A gain 128)
        self.gpio.gpio_write(self.fd, self.sck, 1)
        self.gpio.gpio_write(self.fd, self.sck, 0)

        # convert to signed 24-bit
        if count & 0x800000:
            count -= 1 << 24

        return count

    # -------------------------------------------------

    def stabilize(self, samples=10):
        vals = [self.read_raw() for _ in range(samples)]
        return sum(vals) / len(vals)

    # -------------------------------------------------

    def set_offset(self, offset):
        self.offset = offset

    def set_scale(self, scale):
        self.scale = scale

    def get_weight(self):
        return (self.read_raw() - self.offset) / self.scale

    # -------------------------------------------------

    def close(self):
        try:
            self.gpio.gpiochip_close(self.fd)
        except Exception:
            pass