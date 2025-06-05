# this is for quick recalibration of hxOffset only, when the more constant hxScale has already been measured by calibrateHx711.py and use of a calibration weight, that is not necessary here.
# start the daemon with the command 'sudo pigpiod' before running this script.
# from example code at the end of pigpioBird/HX711.py
import pigpio
import pigpioBird.HX711 as HX711
import numpy as np
import time
from sharedBird import roundFlt # shared functions in shareBird.py
from configBird2 import hxDataPin, hxClckPin, hxScale # import variables from ./configBird.py, but not hxOffset or hxScale because those should be this scripts result

def getMean(sensor, numvals):
    sleepTime = 0.2
    for n in range(numvals):
        count, mode, reading = sensor.get_reading()
        npArr[n] = reading
        time.sleep(sleepTime)

    # meanVal = np.mean(npArr) # .median gives better results than .mean:
    meanVal = np.median(npArr)
    minVal = np.min(npArr)
    maxVal = np.max(npArr)
    spread = maxVal - minVal
    print(str(numVals) + ' elements read')
    print('average: ' + str(meanVal))
    print('spread: ' + str(spread) + ' (' + str(minVal) + ' to ' + str(maxVal) + ')')
    return meanVal

pi = pigpio.pi()
if not pi.connected:
    print('no pigpio')
    exit(0)

scaleFactor = hxScale # taken from configBird ...
'''
# ... or if you like to give in scalefactor as cmd line argument:
if len(sys.argv) < 2:
    print('give scalefactor as argument (measured by calibrateHx711.py)')
    exit(0)
if not sys.argv[1].isnumeric():
    print('argument scalefactor must be numeric')
    exit(0)
scaleFactor = float(sys.argv[1])
'''

numVals = 100
npArr = np.empty(shape=numVals, dtype=float)  # numVals element array
s = HX711.sensor(pi, DATA=hxDataPin, CLOCK=hxClckPin, mode=HX711.CH_A_GAIN_64, callback=None) # oder mode=HX711.CH_A_GAIN_128

print("Remove all loads from balance, then press enter...")
stdin = input()
print("sampling ... wait some seconds")
s.start()
time.sleep(2) # let sensor settle

# basic readings unloaded
meanNoLoad = getMean(s, numVals)

print("measure&&calc ... adjusting offset") # should approximate to calWght by adjusting offset
c, m, reading = s.get_reading()
digress = roundFlt((reading + meanNoLoad)/scaleFactor)
meanNoLoad -= digress * scaleFactor # adjust in units of grams
while (digress > 1):
    c, m, reading = s.get_reading()
    digress = ((reading + meanNoLoad)/scaleFactor)
    meanNoLoad -= digress * scaleFactor 
    print("still deviate: " + str(digress))
    time.sleep(0.5)

print("... then 10 readings near 0.0 should result")
for x in range(10):
    c, m, reading = s.get_reading()
    digress = roundFlt((reading + meanNoLoad)/scaleFactor)
    print(str(digress))

print("----------------------------------------")
print('offset (scale units without load): ' + str(meanNoLoad))
print('scaleFactor sf: ' + str(scaleFactor))

s.cancel() # includes s.pause()
pi.stop()