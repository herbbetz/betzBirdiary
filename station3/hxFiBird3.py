'''
- Initializes the HX711 with tare and scaling using your custom class
- Implements a resilient offset auto-calibration (calibOffset) using stability/spread checks
- Monitors weight changes and detects meaningful movements
- Sends weight via FIFO (ramdisk/birdpipe). This is read by an external fifo reader (video recorder program).
- Handles bounded memory (50 samples) to avoid drift while correcting offset mid-run
- Logs events with timestamps
- Saves updated calibration back to configBird3.py via update_config_json()
- Manages PID state, so calibrate.py can kill this program
'''
from datetime import datetime
import time
import numpy as np
import os
import errno
from lgpioBird.HX711 import HX711
from sharedBird import roundFlt, fifoExists, writePID, clearPID  # shared functions in shareBird.py
from configBird3 import birdpath, hxDataPin, hxClckPin, hxOffset, hxScale, weightThreshold, weightlimit, update_config_json # import variables from ./configBird.py
import msgBird as ms

def get_mean(sensor, num_vals, hOffset, sleeptime):
    # global hxScale -> not needed if read-only
    ms.log(f"hxFi samples {num_vals} readings...")
    readings_np = np.empty(shape=num_vals, dtype=float)

    for i in range(num_vals):
        raw = sensor.read_raw()
        readings_np[i] = roundFlt((raw + hOffset)/hxScale)
        time.sleep(sleeptime)

    mean_val = np.median(readings_np)
    min_val = np.min(readings_np)
    max_val = np.max(readings_np)
    ms.log(f"spread from {min_val} to {max_val}")
    spread = max_val - min_val
    return mean_val, spread

def calibOffset(tries, sensor, hxoffset, sleeptime):
    success = False
    for _ in range(tries):
        mean, spread = get_mean(sensor, 50, hxoffset, sleeptime) # get mean of 100 readings
        if (spread < weightThreshold):
            if (abs(mean) < 1.0): # if weight near '0' and spread is small enough, use this hxOffset
                success = True
                break 
            else: hxoffset -= mean * hxScale
        time.sleep(sleeptime)
    # meanVal = np.mean(npArr) # .median gives better results than .mean:
    ms.log("hxOffset Cal OK") if success else ms.log("hxOffset Cal FAILED")
    ms.log("hxOffset reset to: " + str(hxoffset))
    return hxoffset

def sendFifo(wght):
    # blocking:
    '''
    fifoFp = open(fifo, 'w')
    fifoFp.write(str(wght) + "\n")
    fifoFp.close()
    '''
    # nonblocking:
    try:
        fd = os.open(fifo, os.O_WRONLY | os.O_NONBLOCK)
        with os.fdopen(fd, 'w') as fifoFp:
            fifoFp.write(str(wght) + "\n")
    except OSError as e:
        if e.errno == errno.ENXIO: # ENXIO=6 usually, meaning no such device (FIFO reader)
            # No reader present
            ms.log("hxFiBird: No FIFO reader, skip write")
        else:
            raise  # Unexpected error (e.g. permission, missing file)    

def judgeWeight(wght, timeString, wghtBaseValid): # nested function, returns True if wght should be used for scaleAdjust
    # global weightThreshold, weightlimit -> read-only vars
    if (wght > weightlimit) or len(judgeWeight.vals) > 100: # often when balance strain gauge disconnected
        judgeWeight.vals = []
        ms.log(f"{wght} above {weightlimit}g OR over 100 cycles not plausible")
        return False
    if (wght < weightThreshold and len(judgeWeight.vals) == 0): return True # case1: no load & no values yet
    if wght > weightThreshold:
        if len(judgeWeight.vals) == 0: # case2: fst weight without values
            ms.log(f"{timeString} first movement above threshold")
            judgeWeight.vals.append(wght)
        else: # case3: 1 weight and more to come, movement continued
            judgeWeight.vals.append(wght)
            if wghtBaseValid and judgeWeight.sendactive and len(judgeWeight.vals) > 2: # at least 3 consecutive values above threshold
                judgeWeight.sendactive = False
                ms.log(f"{len(judgeWeight.vals)} moves between {weightThreshold} and {weightlimit} push fifo!")
                sendFifo(max(judgeWeight.vals)) # put the maximum value on bQueue, this triggers sending of video in main process
    if (wght < weightThreshold and len(judgeWeight.vals) > 0): # case4: weight released with values present
        judgeWeight.vals = [] # delete also single outliers
        judgeWeight.sendactive = True
    return False
judgeWeight.vals = [] # static variable belonging to function
judgeWeight.sendactive = True

def chckBaseValid(newWght, weightBaseline, weightBaseVals):
# returns True', if newWght was 'weightBaseVals' times within 'weightBaseline',
#    else returns False'
    chckBaseValid.vals.append(abs(newWght) < weightBaseline)
    # Trim buffer
    if len(chckBaseValid.vals) > weightBaseVals:
        chckBaseValid.vals.pop(0)
    # Only evaluate once we have enough values
    if len(chckBaseValid.vals) < weightBaseVals:
        return False
    # all() returns True if all are true, else returns false
    return all(chckBaseValid.vals)
# static
chckBaseValid.vals = []

#### main:
config_path = f"{birdpath['appdir']}/config.json"  # Adjust if using full path
samples, sampleIdx = 50, 0 # read 50 baseline samples into sampleArr to calculate median deviation from 0.0
sampleArr = np.empty(shape=samples, dtype=float)
sleepTime = 1.0 # shorter causes fixed value and unresponsive balance?
# baseline monitoring:
wghtBaseline = 0.5 * weightThreshold
wghtBaseVals = 7 # 7 last values should be below wghtBaseline
wghtBaseValid = False

ms.init()
ms.log(f"Start hxFiBird3 {datetime.now()}")
if (hxScale == 0):
    print('hxScale must not be zero')
    exit(0)

fifo = birdpath['fifo']
if not fifoExists(fifo):
    os.mkfifo(fifo)
    ms.log("hxFiBird created " + fifo)

ms.log("balance starting")
writePID(1) # so calibrateHx711.py can kill hxFiBird.py

hx = HX711(data_pin=hxDataPin, clock_pin=hxClckPin)
hx.tare()
hxOffset = calibOffset(2, hx, hxOffset, sleepTime)

try:
    while True:
        reading = hx.read_raw()
        # transform reading to grams using  hxOffset, hxScale, roundFlt
        # hxScale = reading units per gram
        weight = roundFlt((reading + hxOffset)/hxScale)
        nowDate = datetime.now()
        timeStr = str(nowDate.hour) + ":" + str(nowDate.minute) + ":" + str(nowDate.second)
        ms.log(timeStr + ' ' + str(weight) + ' grams')

        # wghtBaseValid = chckBaseValid(weight, wghtBaseline, wghtBaseVals) # after this baseline check the real weight surge never qualifies!
        # if not wghtBaseValid: ms.log("weight baseline unstable")
        if (judgeWeight(weight, timeStr, wghtBaseValid) == True):
            if (sampleIdx < samples):
                sampleArr[sampleIdx] = weight
                sampleIdx += 1
            else: # sample size 50 reached
                apartZero = np.median(sampleArr) # get new scaleAdjust out of 50 readings
                if (abs(apartZero) > 1.0): 
                    hxOffset -= apartZero * hxScale
                    ms.log("hxOffset now: " + str(hxOffset))
                sampleIdx = 0 # then start again sampling for scaleAdjust

        time.sleep(sleepTime)
except (KeyboardInterrupt, SystemExit):
    ms.log("balance going down")
finally:
    update_config_json({"hxOffset": hxOffset, "hxScale": hxScale})
    hx.close()
    clearPID(1)
    ms.log(f"End hxFiBird3 {datetime.now()}")