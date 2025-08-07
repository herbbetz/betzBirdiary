# class for DHT22 only, derived from DHT.py by chatGPT (June 2025)
import time
import lgpio as sbc

DHT22 = 2
DHT_GOOD = 0
DHT_TIMEOUT = 3

class DHT22Sensor:
    def __init__(self, chip=0, gpio=16):
        self._chip = chip
        self._gpio = gpio
        self._model = DHT22

        self._new_data = False
        self._bits = 0
        self._code = 0
        self._last_edge_tick = 0

        self._timestamp = 0
        self._temperature = 0.0
        self._humidity = 0.0
        self._status = DHT_TIMEOUT

        # watchdog after 1 ms
        sbc.gpio_set_watchdog_micros(self._chip, self._gpio, 1000)
        self._cb = sbc.callback(self._chip, self._gpio, sbc.RISING_EDGE, self._rising_edge)

    def _decode_dht22(self):
        b0 =  self._code        & 0xff
        b1 = (self._code >>  8) & 0xff
        b2 = (self._code >> 16) & 0xff
        b3 = (self._code >> 24) & 0xff
        b4 = (self._code >> 32) & 0xff

        chksum = (b1 + b2 + b3 + b4) & 0xFF

        if chksum == b0:
            # decode temperature
            if b2 & 128:
                div = -10.0
            else:
                div = 10.0
            t = float(((b2 & 127) << 8) + b1) / div
            # decode humidity
            h = float((b4 << 8) + b3) / 10.0

            if (h <= 110.0) and (t >= -50.0) and (t <= 135.0):
                self._timestamp = time.time()
                self._temperature = t
                self._humidity = h
                self._status = DHT_GOOD
                self._new_data = True
                return

        # If checksum or validation fails
        self._status = DHT_TIMEOUT
        self._new_data = False

    def _rising_edge(self, chip, gpio, level, tick):
        if level != sbc.TIMEOUT:
            edge_len = tick - self._last_edge_tick
            self._last_edge_tick = tick
            if edge_len > 2e8:  # 0.2 seconds, reset on long pause
                self._bits = 0
                self._code = 0
            else:
                self._code <<= 1
                if edge_len > 1e5:  # 100 us pulse means bit 1
                    self._code |= 1
                self._bits += 1
        else:
            # watchdog timeout: data ready?
            if self._bits >= 30:
                self._decode_dht22()

    def _trigger(self):
        sbc.gpio_claim_output(self._chip, self._gpio, 0)
        time.sleep(0.001)  # DHT22 trigger pulse
        self._bits = 0
        self._code = 0
        sbc.gpio_claim_alert(self._chip, self._gpio, sbc.RISING_EDGE)

    def read(self):
        self._new_data = False
        self._status = DHT_TIMEOUT
        self._trigger()

        # Wait up to 1 second for data
        for _ in range(20):
            time.sleep(0.05)
            if self._new_data:
                break

        if not self._new_data:
            raise RuntimeError("DHT22 data timeout")

        return (self._timestamp, self._temperature, self._humidity)

    def cancel(self):
        if self._cb is not None:
            self._cb.cancel()
            self._cb = None
