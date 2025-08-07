import lgpio as sbc
from DHT22 import DHT22Sensor

chip = sbc.gpiochip_open(0)  # open gpiochip 0
sensor = DHT22Sensor(chip=chip, gpio=16)

try:
    timestamp, temperature, humidity = sensor.read()
    print(f"Time: {timestamp}, Temp: {temperature:.1f}C, Humidity: {humidity:.1f}%")
finally:
    sensor.cancel()
    sbc.gpiochip_close(chip)
