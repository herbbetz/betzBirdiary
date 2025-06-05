# this is for quick recalibration of hxOffset only, when the more constant hxScale has already been measured by calibrateHx711.py and use of a calibration weight, that is not necessary here.
# start the daemon with the command 'sudo pigpiod' before running this script.
# from example code at the end of pigpioBird/HX711.py
import pigpio
import pigpioBird.HX711 as HX711
import numpy as np
import os
import time
from sharedBird import roundFlt # shared functions in shareBird.py
from configBird2 import hxDataPin, hxClckPin, hxScale, offsetFname # import variables from ./configBird.py, but not hxOffset, 
#   which results from this script on startup and is read in by other scripts from configBird thereafter.

def getMean(sensor, numvals):
    sleepTime = 0.2
    for n in range(numvals):
        count, mode, reading = sensor.get_reading()
        npArr[n] = reading
        time.sleep(sleepTime)
    # meanVal = np.mean(npArr) # .median gives better results than .mean:
    meanVal = np.median(npArr)
    return meanVal

pi = pigpio.pi()
if not pi.connected:
    print('no pigpio')
    exit(0)

numVals = 100
npArr = np.empty(shape=numVals, dtype=float)  # numVals element array
s = HX711.sensor(pi, DATA=hxDataPin, CLOCK=hxClckPin, mode=HX711.CH_A_GAIN_64, callback=None) # oder mode=HX711.CH_A_GAIN_128

# sampling:
s.start()
time.sleep(2) # let sensor settle

# basic readings unloaded
meanNoLoad = getMean(s, numVals)

#measure and calculate, should approximate to calWght by adjusting offset
c, m, reading = s.get_reading()
digress = roundFlt((reading + meanNoLoad)/hxScale)
meanNoLoad -= digress * hxScale # adjust in units of grams
while (digress > 1):
    c, m, reading = s.get_reading()
    digress = ((reading + meanNoLoad)/hxScale)
    meanNoLoad -= digress * hxScale 
    time.sleep(0.5)

if os.path.exists(offsetFname):
    os.remove(offsetFname)
with open(offsetFname, 'w') as wfile:
    wfile.write(str(meanNoLoad))

s.cancel() # includes s.pause()
pi.stop()