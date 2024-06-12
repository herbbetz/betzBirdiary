# hx711 writes weight (float) to fifo, so needs an external fifo reader to continue
from datetime import datetime
import time
import numpy as np
import os
import pigpio
import pigpioBird.HX711 as HX711
from sharedBird import roundFlt, fifoExists # shared functions in shareBird.py
from configBird import hxDataPin, hxClckPin, hxOffset, hxScale, weightThreshold # import variables from ./configBird.py
import msgBird as ms

pi = pigpio.pi()
if not pi.connected:
    print('no pigpio')
    exit(0)
if (hxScale == 0):
    print('hxScale must not be zero')
    exit(0)

fifo = "ramdisk/birdpipe"
if not fifoExists(fifo):
    os.mkfifo(fifo)
    ms.log("hxFiBird created " + fifo)

def sendFifo(wght):
    fifoFp = open(fifo, 'w')
    fifoFp.write(str(wght) + "\n")
    fifoFp.close()

def judgeWeight(wght): # nested function, returns True if wght should be used for scaleAdjust
    global weightThreshold
    if (wght > 40) or len(judgeWeight.vals) > 100: # often when balance strain gauge disconnected
        judgeWeight.vals = []
        ms.log("weight above 40g OR over 100 cycles not plausible")
        return False
    if (wght < weightThreshold and len(judgeWeight.vals) == 0): return True # case1: no load & no values yet
    if wght > weightThreshold:
        if len(judgeWeight.vals) == 0: # case2: fst weight without values
            nowDate = datetime.now()
            timeStr = str(nowDate.hour) + ":" + str(nowDate.minute) + ":" + str(nowDate.second)
            ms.log(timeStr + " Movement recognized!")
            judgeWeight.vals.append(wght)
        else: # case3: 1 weight and more to come, movement continued
            judgeWeight.vals.append(wght)
    if (wght < weightThreshold and len(judgeWeight.vals) > 0): # case4: weight released with values present
        if len(judgeWeight.vals) > 2: # at least 3 consecutive values above threshold
            ms.log("Movement complete for fifo!")
            sendFifo(max(judgeWeight.vals)) # put the maximum value on bQueue, this triggers sending of video in main process
            # bQ.put(max(judgeWeight.vals)) for mainBird{12}.py
        judgeWeight.vals = [] # delete also single outliers
    return False
judgeWeight.vals = [] # static variable belonging to function

#### main:
ms.log("balance starting")
s = HX711.sensor(pi, DATA=hxDataPin, CLOCK=hxClckPin, mode=HX711.CH_A_GAIN_64, callback=None) # mode=HX711.CH_A_GAIN_128 to sensitive?
s.start()
time.sleep(2) # let sensor settle

samples, sampleIdx = 50, 0 # read 50 baseline samples into sampleArr to calculate median deviation from 0.0
sampleArr = np.empty(shape=samples, dtype=float)

sleepTime = 1.0 # shorter causes fixed value and unresponsive balance?
count, mode, reading = s.get_reading() # first test reading
checkcnt = count
hanging, hanglimit = 0, 5
while True:
    try: 
        time.sleep(sleepTime)
        count, mode, reading = s.get_reading()
        if (count == checkcnt): # only read new values
            hanging += 1
            ms.log('hanging #' + str(hanging))
            if hanging > hanglimit: break # end program to be restarted by bash
            sleepTime += 0.2
            time.sleep(sleepTime)
            continue
        else: 
            checkcnt = count
            hanging = 0

        # transform reading to grams using  hxOffset, hxScale, roundFlt
        # hxScale = reading units per gram
        weight = roundFlt((reading + hxOffset)/hxScale)
        nowDate = datetime.now()
        timeStr = str(nowDate.hour) + ":" + str(nowDate.minute) + ":" + str(nowDate.second)
        ms.log(timeStr + ' ' + str(weight) + ' grams')
        # s.pause(), then s.start() for balance to recover?
        if (judgeWeight(weight) == True):
            if (sampleIdx < samples):
                sampleArr[sampleIdx] = weight
                sampleIdx += 1
            else: # sample size 50 reached
                apartZero = np.median(sampleArr) # get new scaleAdjust out of 50 readings
                if (abs(apartZero) > 1.0): 
                    hxOffset -= apartZero * hxScale
                    ms.log("hxOffset now: " + str(hxOffset))
                sampleIdx = 0 # then start again sampling for scaleAdjust
    except(KeyboardInterrupt, SystemExit):
        break
ms.log("balance going down")
s.cancel()
pi.stop()