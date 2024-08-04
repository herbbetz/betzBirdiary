# start the daemon with the command 'sudo pigpiod' before running this script.
# from example code at the end of pigpioBird/HX711.py
import pigpio
import pigpioBird.HX711 as HX711
import time

# hxOffset = -22770 # minus of weight reading when balance is empty
# hxScale = 1580 # hang 100 g waterbottle on balance and get the factor weight_increase/100
# BCM GPIO Pins attached to sensors:
# hxDataPin, hxClckPin = 17, 23
# test my configBird.py values:
from configBird import hxDataPin, hxClckPin, hxOffset, hxScale

pi = pigpio.pi()
if not pi.connected:
    print('no pigpio')
    exit(0)
if (hxScale == 0):
    print('hxScale must not be zero')
    exit(0)

def roundFlt(flt):
# round float down to 2 decimal
    return (round(flt, 2))

#### main:
if __name__ == "__main__":

    s = HX711.sensor(pi, DATA=hxDataPin, CLOCK=hxClckPin, mode=HX711.CH_A_GAIN_64, callback=None) # oder mode=HX711.CH_A_GAIN_128
    s.start()
    time.sleep(2) # let sensor settle

    sleepTime = 0.2
    while True:
        try: 
            time.sleep(sleepTime)
            count, mode, reading = s.get_reading()
            # transform reading to grams using  hxOffset, hxScale, roundFlt
            grams = roundFlt((reading + hxOffset)/hxScale)
            print('weight: ' + str(grams) + ' grams')
            # could count be twice the same? see example code
            # print("{} {} {}".format(count, mode, reading))
            # s.pause() # und danach wieder s.start()?
        except KeyboardInterrupt:
            break

    s.cancel() # includes s.pause()
    pi.stop()