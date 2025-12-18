# ChatGPT June 2025
# shows 350 g ghost spikes, a classic timing issue with “one bit shifted value”.
import lgpio
import time

class HX711:
    """
    HX711 load cell ADC reader using lgpio.
    Only raw 24-bit signed values are returned.
    Scaling and offset are handled externally.
    """

    def __init__(self, data_pin=17, clock_pin=23, chip=0):
        self.data_pin = data_pin
        self.clock_pin = clock_pin
        self.chip = lgpio.gpiochip_open(chip)

        lgpio.gpio_claim_input(self.chip, self.data_pin)
        lgpio.gpio_claim_output(self.chip, self.clock_pin, 0)

    def delay_us(self, microseconds):
        """Accurate microsecond delay using busy wait."""
        start = time.perf_counter_ns()
        end = start + int(microseconds * 1000)
        while time.perf_counter_ns() < end:
            pass

    def wait_ready(self, timeout=1.0):
        """Block until data line goes LOW (data ready)."""
        start_time = time.time()
        while time.time() - start_time < timeout:
            if lgpio.gpio_read(self.chip, self.data_pin) == 0:
                return True
            time.sleep(0.001)
        raise TimeoutError("HX711 not ready within timeout")

    def read_raw(self):
        """
        Read one signed 24-bit value from the HX711.
        External offset/scale should be applied in the application.
        """
        self.wait_ready()

        value = 0
        for _ in range(24):
            lgpio.gpio_write(self.chip, self.clock_pin, 1)
            self.delay_us(2)
            value = (value << 1) | lgpio.gpio_read(self.chip, self.data_pin)
            lgpio.gpio_write(self.chip, self.clock_pin, 0)
            self.delay_us(2)

        # Gain = 64: 3 extra clock pulses
        for _ in range(3):
            lgpio.gpio_write(self.chip, self.clock_pin, 1)
            self.delay_us(2)
            lgpio.gpio_write(self.chip, self.clock_pin, 0)
            self.delay_us(2)

        # Convert from 24-bit signed to Python int
        if value & 0x800000:
            value -= 0x1000000

        return value

    def tare(self, samples=15):
        """
        Return average reading as baseline for external offset.
        """
        total = 0
        for _ in range(samples):
            total += self.read_raw()
            time.sleep(0.1)
        return total / samples

    def power_down(self):
        """Power down the HX711 chip."""
        lgpio.gpio_write(self.chip, self.clock_pin, 1)
        self.delay_us(70)

    def power_up(self):
        """Wake up the HX711 chip."""
        lgpio.gpio_write(self.chip, self.clock_pin, 0)
        self.delay_us(100)

    def close(self):
        """Release GPIO resources."""
        lgpio.gpiochip_close(self.chip)
