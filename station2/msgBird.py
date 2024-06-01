# msgBird.py is a module (used like a singleton class) for writing one json file, whose components are set by different functions.
# the JSON file can then be fetched by javascript of a webpage. JS will recognize JSON integer or float types without the need for conversion to and from strings.
#    Serializing (python dict -> JSON -> JS object) preserves data types and does NOT convert all into strings.
# beware: each script importing msgBird.py has one module instance, but each script has its own!
#    This is not "shared memory" between different scripts, no exchange between them as long as no files are written! 
#    And file writing from different scripts to the same file is hazardous, one overwriting the other, each with its own instance values!
import json
import fcntl # for file locking, locks are transparent in python or bash by 'lslocks' or 'cat /proc/locks'
import os
import time

# main json information for browser:
#   imgid: newly increased id num of captured img 
#   lastvid: date of last video upload, confirm: need for confirmation of video upload in vidshot.html, 'confirm' is 0 or 1 (0 for python->False, json->false, javascript->false)
#   linecnt, linetxt: for logging output
#   envirEvt, sysmonEvt: new data available as value increased
msg = {"imgid": 0, "lastvid": "", "confirm": 0, "linecnt": 0, "linetxt": "", "envirEvt": 0, "sysmonEvt": 0} # define dictionary, 

filename = '/home/pi/station2/ramdisk/vidmsg.json' #serialized msg

def init(): # first create empty msg file
    if not os.path.exists(filename):
        writemsg()
        time.sleep(0.2)

def writemsg(): # also as init() before readmsg()
    global msg
    with open(filename, 'w') as jfile:
        fcntl.flock(jfile, fcntl.LOCK_EX) # will wait for other locks to close
        json.dump(msg, jfile) # write
        fcntl.flock(jfile, fcntl.LOCK_UN)

# in each function to get values from other scripts using this msgBird module
# flock this too, as read process may be disturbed by writing
def readmsg():
    global msg
    with open(filename, 'r') as jfile:
        fcntl.flock(jfile, fcntl.LOCK_EX) # will wait for other locks to close
        msg = json.load(jfile) # read
        fcntl.flock(jfile, fcntl.LOCK_UN)

def updatemsg(callback):
    global msg
    with open(filename, 'r+') as jfile:
        # Acquire an exclusive lock
        fcntl.flock(jfile, fcntl.LOCK_EX) # will wait for other locks to close
        # msg = jfile.read() 
        msg = json.load(jfile) # read
        msg = callback(msg) # update
        # and write:
        jfile.seek(0)
        jfile.truncate()
        # jfile.write(str(msg))
        json.dump(msg, jfile)
        fcntl.flock(jfile, fcntl.LOCK_UN)

def printmsg():
    readmsg()
    for key, value in msg.items():
        print(key, ":", value)

def setImgCnt(id):
    def change(data):
        data['imgid'] = id
        return data
    updatemsg(change)

def setVidDateStr(dateStr):
    def change(data):
        data['lastvid'] = dateStr
        # confirm need not be '1', because not every main*.py script needs confirmation of video upload
        return data
    updatemsg(change)

def emptyVidDateStr():
    def change(data):
        data['lastvid'] = ""
        data['confirm'] = 0
        return data
    updatemsg(change)

def setConfirm(): # 0 or 1
    def change(data):
        data['confirm'] = 1
        return data
    updatemsg(change)

def getVidDateStr():
    # json.load() parses file with json content, json.loads() parses valid json string into dict
    readmsg()
    return msg['lastvid']

def log(txt):
    def change(data):
        data['linecnt'] += 1
        data['linetxt'] = txt
        return data
    print(txt) #show in terminal
    updatemsg(change)

def getLogCnt():
    readmsg()
    return msg['linecnt']

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