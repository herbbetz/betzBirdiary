# needs hx711_gpiozero installed from https://pypi.org/project/hx711-gpiozero/, but which is deprecated according to https://github.com/cyrusn/hx711_gpiozero .
# => ERROR: "gpiozero.exc.SPIBadArgs: unrecognized keyword argument data_pin" nicht weiter verfolgt
from hx711_gpiozero import HX711
from time import sleep

DATA_PIN = 17
CLOCK_PIN = 23

spi = HX711(data_pin=DATA_PIN, clock_pin=CLOCK_PIN)
print("Initiatin ...")
init_reading = spi.value

sleep(1)
while True:
    weight = (spi.value - init_reading) # * scale_ratio
    print(weight)
    sleep(1)
'''
input("Put a known mass on the scale, then press `enter`.")

try:
    rel_weight = float(input("What is the weight of the known mass?\n"))
except ValueError as err:
    print(err)
    print("(The input of weight can only be numbers)")
    exit(1)
rel_reading = spi.value
scale_ratio = rel_weight / (rel_reading - init_reading)

sleep(1)
while True:
    weight = (spi.value - init_reading) * scale_ratio
    print(weight)
    sleep(1)
'''