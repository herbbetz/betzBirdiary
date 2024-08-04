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

# main json information for browser:
#   imgid: newly increased id num of captured img 
#   lastvid: date of last video upload, confirm: need for confirmation of video upload in vidshot.html, 'confirm' is 0 or 1 (0 for python->False, json->false, javascript->false)
#   linecnt, linetxt: for logging output
#   envirEvt, sysmonEvt: new data available as value increased
message = {"imgid": 0, "lastvid": "", "vidcnt": 0, "confirm": 0, "linecnt": 0, "linetxt": "", "envirEvt": 0, "sysmonEvt": 0, "upmode": 0} # define dictionary

filename = '/home/pi/station2/ramdisk/vidmsg.json' #serialized msg

def init(): # first create empty msg file
    # global msg
    badcontent = False

    if not os.path.exists(filename):
        writemsg(message)
        time.sleep(0.2)
    else: # exists but contains no JSON
        jfile = open(filename, 'r')
        # Acquire an exclusive lock
        fcntl.flock(jfile, fcntl.LOCK_EX) # will wait for other locks to close
        try:
            m = jfile.read() # gives no dict
            # or msg = json.load(jfile)
            msg = json.loads(m) # change to dict
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
    with open(filename, 'r+') as jfile:
        # Acquire an exclusive lock
        fcntl.flock(jfile, fcntl.LOCK_EX) # will wait for other locks to close
        try:
            m = jfile.read() # gives no dict
            # or msg = json.load(jfile)
            # JSONDecodeError from None, vidmsg.json sometimes empty? why?
            msg = json.loads(m) # change to dict
            msg = callback(msg) # update
            upd = json.dumps(msg)
            # and write:
            jfile.seek(0)
            jfile.write(upd) # will not change numerics to strings
            # json.dump(msg, jfile)
            jfile.truncate() # truncate before the write may leave back an empty file
        except JSONDecodeError as e:
            print(str(m) + " =read unvalid json: " + str(e), flush=True)
        except TypeError as s:
            print(str(upd) + " =not serializable to json: " + str(s), flush=True)
        finally:
            fcntl.flock(jfile, fcntl.LOCK_UN)

def setmsgprop(key, val):
    def change(data):
        data[key] = val
        return data
    updatemsg(change)

def setmsgProps(newDict):
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

def getVidDateStr():
    # json.load() parses file with json content, json.loads() parses valid json string into dict
    m = readmsg()
    return m['lastvid']

def getLogCnt():
    # nowhere used in my scripts
    m = readmsg()
    return m['linecnt']

def getUpmode():
    m = readmsg()
    return m['upmode']

def log(txt):
    def change(data):
        data['linecnt'] += 1
        data['linetxt'] = txt
        return data
    print(txt, flush=True) #show in terminal
    txt = txt.strip() # trim off newline
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