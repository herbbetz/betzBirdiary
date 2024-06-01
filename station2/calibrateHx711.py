# start the daemon with the command 'sudo pigpiod' before running this script.
# from example code at the end of pigpioBird/HX711.py
import pigpio
import pigpioBird.HX711 as HX711
import numpy as np
import time
from sharedBird import roundFlt # shared functions in shareBird.py
from configBird import hxDataPin, hxClckPin # import variables from ./configBird.py, but not hxOffset or hxScale because those should be this scripts result

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

print("Now load balance with calibration weight")
print("Please type in the value of this weight in full grams (only digits - no dot or letter)")
while True:
    stdin = input()
    if (stdin.isnumeric()):
        calWght = float(stdin)
        if (calWght > 0.0):
            print('you entered: ' + str(calWght) + ' grams')
            break
        else:
            print('Please type positive integer number:')

print("wait for some seconds ...")
# readings loaded:
meanLoad = getMean(s, numVals)

delta = meanLoad - meanNoLoad
scaleFactor = delta/calWght
print('scalefactor ' + str(scaleFactor) + ' = reading units /gram')
# reciprocal = calWght/delta # very unwieldy number
# print('reciprocal of sf ' + str(reciprocal))

print("measure&&calc ... adjusting offset") # should approximate to calWght by adjusting offset
c, m, reading = s.get_reading()
digress = roundFlt((reading + meanNoLoad)/scaleFactor) - calWght
meanNoLoad -= digress * scaleFactor # adjust in units of grams
while (digress > 1):
    c, m, reading = s.get_reading()
    digress = ((reading + meanNoLoad)/scaleFactor) - calWght
    meanNoLoad -= digress * scaleFactor 
    print("still deviate: " + str(digress))
    time.sleep(0.5)

print("Now unload balance, then press enter")
print("... then 10 readings near 0.0 should result")
stdin = input()
for x in range(10):
    c, m, reading = s.get_reading()
    digress = roundFlt((reading + meanNoLoad)/scaleFactor)
    print(str(digress))

print("----------------------------------------")
print('offset (scale units without load): ' + str(meanNoLoad))
print('scaleFactor sf: ' + str(scaleFactor))

s.cancel() # includes s.pause()
pi.stop()