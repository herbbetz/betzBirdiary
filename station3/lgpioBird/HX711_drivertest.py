import time
from HX711 import HX711

DATA_PIN = 17
CLOCK_PIN = 23

print("Initializing HX711…")

hx = HX711(DATA_PIN, CLOCK_PIN)

print("Reading raw values (CTRL+C to stop)")

try:
    while True:
        raw = hx.read_raw()
        print(raw)
        time.sleep(0.2)

except KeyboardInterrupt:
    pass

finally:
    hx.close()
    print("Done")