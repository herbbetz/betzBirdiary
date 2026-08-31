# msgBird.py is a module (used like a singleton class) for writing one json file, whose components are set by different functions.
# the JSON file can then be fetched by javascript of a webpage. JS will recognize JSON integer or float types without the need for conversion to and from strings.
#    Serializing (python dict -> JSON -> JS object) preserves data types and does NOT convert all into strings.
# beware: each script importing msgBird.py has one module instance, but each script has its own!
#    This is not "shared memory" between different scripts, no exchange between them as long as no files are written! 
#    And file writing from different scripts to the same file is hazardous, one overwriting the other, each with its own instance values!
import json
from json.decoder import JSONDecodeError
import fcntl # for file locking, locks are transparent in python or bash by 'lslocks' or 'cat /proc/locks'
import os
import time
from configBird3 import birdpath

# main json information for browser:
#   imgid: newly increased id num of captured img 
#   lastvid: date of last video upload, confirm: need for confirmation of video upload in vidshot.html, 'confirm' is 0 or 1 (0 for python->False, json->false, javascript->false)
#   linecnt, linetxt: for logging output
#   envirEvt, sysmonEvt: new data available as value increased
#   confirm and upmode are only, if several mainVideo scripts can be exchanged (old acknowlegde mode)
#   standby: 0 or 1, set by webGUI to stop video capturing
#   clientactive: 0 or 1, set by flaskBird3.py when webclient is active
#   lux: illumination category 1..6, set by mainFoBird3.py
#   luxraw: raw lux data string for webGUI display, set by mainFoBird3.py
#   recording: 0 or 1, set by mainFoBird3.py
#   scaleready: 0 or 1, set by hxFiBirdStateCt.py
message = {"imgid": 0, "lastvid": "", "vidcnt": 0, "linecnt": 0, "linetxt": "", "envirEvt": 0, "sysmonEvt": 0,
           "upmode": 0, "confirm": 0, "standby": 0, "clientactive": 0, "lux": 0, "luxraw": "", "recording": 0, "scaleready": 0} # define dictionary
# Use as cache for reducing read/write in params that might be changed often inside loops (only read/write if value changed), e.g. scaleready inside hxFiBird*.py
# However cache must not be used, if the function is not called by different scripts!?

filename = f"{birdpath['ramdisk']}/vidmsg.json" #serialized msg

def init(): # first create empty msg file
    global message
    badcontent = False

    if not os.path.exists(filename):
        writemsg(message)
        time.sleep(0.2)
    else: # exists but contains no JSON
        jfile = open(filename, 'r')
        fcntl.flock(jfile, fcntl.LOCK_EX)
        try:
            m = jfile.read() # gives no dict
            message = json.loads(m) # Sync module-level dict with actual file content
        except JSONDecodeError:
            print("no valid JSON in " + filename)
            badcontent = True
        finally:
            fcntl.flock(jfile, fcntl.LOCK_UN)
            jfile.close()

        if badcontent:
            os.remove(filename)
            writemsg(message)

def writemsg(msg): # also as init() before readmsg()
    with open(filename, 'w') as jfile:
        fcntl.flock(jfile, fcntl.LOCK_EX) # will wait for other locks to close
        try:
            json.dump(msg, jfile) # write
        finally:
            fcntl.flock(jfile, fcntl.LOCK_UN)

# in each function to get values from other scripts using this msgBird module
# flock this too, as read process may be disturbed by writing
def readmsg():
    with open(filename, 'r') as jfile:
        fcntl.flock(jfile, fcntl.LOCK_EX) # will wait for other locks to close
        try:
            msg = json.load(jfile) # read
        finally:
            fcntl.flock(jfile, fcntl.LOCK_UN)
    return msg

def readmsgProp(prop):
    m = readmsg()
    return m[prop]

def updatemsg(callback):
    global message
    with open(filename, 'r+') as jfile:
        fcntl.flock(jfile, fcntl.LOCK_EX)
        try:
            m = jfile.read()
            disk_data = json.loads(m)
            
            # Apply update function
            updated_data = callback(disk_data)
            
            # Write updated dict to disk
            upd = json.dumps(updated_data)
            jfile.seek(0)
            jfile.write(upd)
            jfile.truncate()
            
            # Sync local process cache with what was written
            message = updated_data

        except JSONDecodeError as e:
            print(f"{m} = invalid json read: {e}", flush=True)
        except TypeError as s:
            print(f"Not serializable to json: {s}", flush=True)
        finally:
            fcntl.flock(jfile, fcntl.LOCK_UN)

def setmsgprop(key, val):
    global message
    # 1. Memory Guard: Skip disk I/O entirely if local process cache already matches
    if message.get(key) == val:
        return

    # 2. File Lock & Update
    def change(data):
        data[key] = val
        return data

    updatemsg(change)


def setmsgProps(newDict):
    global message
    # 1. Memory Guard: Check if all values in dictionary match local cache
    if all(message.get(k) == v for k, v in newDict.items()):
        return

    # 2. File Lock & Update
    def change(data):
        for key, value in newDict.items():
            data[key] = value
        return data

    updatemsg(change)

def printmsg():
    m = readmsg()
    for key, value in m.items():
        print(key, ":", value)

###applying above functions:

def setImgCnt(id):
    setmsgprop('imgid', id)

def setVidCnt(cnt):
    setmsgprop('vidcnt', cnt)

def setVidDateStr(dateStr):
    # confirm need not be '1', because not every main*.py script needs confirmation of video upload
    setmsgprop('lastvid', dateStr)

def setConfirm(): # 0 or 1
    setmsgprop('confirm', 1)

def setUpmode(id): # 1=direct, 2=confirmed upload 
    setmsgprop('upmode', id)

def emptyVidDateStr():
    setmsgProps({'lastvid': '', 'confirm': 0})

def setClientActive(active):
    # webclient active is 0 or 1, set by flaskBird3.py
    # on inactive no picture is taken in mainFoBird3.py
    setmsgprop('clientactive', active)

def setLux(luxcategory):
    # lux is 6 (overexposed) to 1 (dark), set by mainFoBird3.py
    setmsgprop('lux', luxcategory)

def setLuxRaw(lux):
    # save current luxdata to watch in webGUI rawdata section, set by mainFoBird3.py
    setmsgprop('luxraw', lux)

def setRecording(state):
    # state: 1= recording in progress, else 0
    setmsgprop('recording', state)

# scaleready default = 1, till hxFiBird*.py started
def setScaleready():
    setmsgprop('scaleready', 1)

def clearScaleready():
    setmsgprop('scaleready', 0)

def getScaleready():
    m = readmsg()
    return m['scaleready']    

def getClientActive():
    m = readmsg()
    return m['clientactive']

def getVidDateStr():
    # used in uploadBird.py and keepBird.py
    # json.load() parses file with json content, json.loads() parses valid json string into dict
    m = readmsg()
    return m['lastvid']

def getVidCnt():
    # not used in my scripts, see grep
    m = readmsg()
    return m['vidcnt']

def getLogCnt():
    # not used in my scripts, see grep
    m = readmsg()
    return m['linecnt']

def getUpmode():
    m = readmsg()
    return m['upmode']

def getStandby():
    m = readmsg()
    anystdby = 0
    if m['standby'] or m['lux'] > 4: anystdby = 1 # manual standby activated or bad illumination
    return anystdby # 1 blocks weight fifo in readBalance(bQ) of mainFoBird.py

def chStandby():
    m = readmsg()
    if m['standby'] == 0: setmsgprop('standby', 1)
    else: setmsgprop('standby', 0)

def clearStandby(): # mainFoBird clears forgotten standby after 300 secs of webGUI inactivity
    setmsgprop('standby', 0)
    
def log(txt, terminal=True):
    def change(data):
        data['linecnt'] += 1
        data['linetxt'] = txt
        return data
    txt = txt.strip() # trim off newline
    if terminal: print(txt, flush=True) #show in terminal or mail
    updatemsg(change)

def setEnvirEvt():
    def change(data):
        data['envirEvt'] += 1
        return data
    updatemsg(change)

def setSysmonEvt():
    # this is set by bash script, so maybe not used by python
    def change(data):
        data['sysmonEvt'] += 1
        return data
    updatemsg(change)

'''
#### disk read/write VidDateStr for after reboot of mainAckBird2/uploadBird/keepBird:
viddateFname = 'movements/lastvid.txt'
def readSavedVidDate():
    if not os.path.exists(viddateFname): 
        return 'no VidDate'
    with open(viddateFname, 'r') as datefile:
        content = datefile.read()
    return content

def writeSavedVidDate(vidDate):
    with open(viddateFname, 'w') as datefile:
        datefile.write(vidDate)

def setSavedVidDate():
    setVidDateStr(readSavedVidDate())
'''