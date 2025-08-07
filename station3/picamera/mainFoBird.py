# main.py file from birdiary station120423.img adapted for RPiZero and shortened
# for picamera enable legacy camera in raspi-config and gpu_mem=256 in /boot/config.txt (but not for picamera2!). picamera2 not preferred, because it lacks rotation.
# code for DHT22 sensor moved to dhtBird.py, which can be called by this script (os.system('python3 /home/pi/station2/dhtBird.py')) or crontab
# code for HX711 sensor moved to hxFiBird.py, which sends the measured weight via fifo to this script's child1 process
# flaskBird webserver can send to this fifo pipe too
# microphone/audio removed apart from uploading empty audio file 'wav/min.wav' to requesting API
import os # for calling dhtBird.py and fifo receive
import subprocess
import sys
import signal
from datetime import datetime
import time
import json
import requests
# picamera1:
# even the simplest standalone picamera program is multithread ('l' in 'ps aux')!
import io
import picamera
# weight messages from hxFiBird.py and flaskBird.py are received by fifo within child1 process:
import multiprocessing
# own local modules:
from sharedBird import fifoExists # shared functions in shareBird.py
import msgBird as ms # imports different fcts to write json, later fetched by flaskBird webpage javascript
from configBird import * # import all variables from ./configBird.py

# these directories should exist within ./station2 and are no longer tested for by module os:
#   pigpioBird environments movements logs ramdisk wav

# logname = "logs/birdiary.log", replaced by 'python3 mainBird2.py >> logs/birdiary.log'
#### own logging functions:
# def ms.log(line) in msgBird.py

def write_movement(movement_data):
    # for dev_mode
    global data_filename
    with open(data_filename, 'w') as f:
        f.write(movement_data) # simple string write

def capture_img(dest):
    if os.path.exists(dest): 
        os.remove(dest)
        # ms.log("remove on capture save: " + dest)
    camera.capture(dest, resize=losize, use_video_port=True) # 3.4 of https://picamera.readthedocs.io/en/release-1.13/recipes1.html

def preloadCaptures(maxImg, sleep):
    for img in range(maxImg):
        imgName = 'ramdisk/img' + str(img) + '.jpg'
        capture_img(imgName) 
        ms.setImgCnt(imgNum)
        time.sleep(sleep)
    return maxImg

#### sending functions:
def set_filenames(movementStartDate):
    movementStartStr = str(movementStartDate)
    global audio_filename
    audio_filename = movementStartStr + '.wav' # basename, not saved as file
    global video_filename
    video_filename = movementStartStr + '.h264' # basename, not saved as file
    global data_filename
    data_filename = 'movements/' + movementStartStr + '.json'

# Function to send movement data to the server
def send_realtime_movement(files):
    global dev_mode, serverUrl, boxId
    if dev_mode: 
        write_movement(files['json'][1])
        return

    try:
        ms.log('sending to ' + serverUrl + 'movement/' + boxId)
        r = requests.post(serverUrl + 'movement/' + boxId, files=files, timeout=60)
        ms.log('Movement data sent: ' + files['json'][1]) # files['json'][1] is string inside tuple files['json'], files is dictionary of files to send, str(dict)
        ms.log('Corresponding movement_id: ' + r.text) # type(r.content) -> bytes

        cmd = "bash /home/pi/station2/mdroid.sh newVideo"
        subprocess.call(cmd, shell=True) # returns exit code of cmd
    except (requests.ConnectionError, requests.Timeout) as exception:
        ms.log('failed movement upload - ' + str(exception))

def send_movement(wght):
    ms.log("***movement upload***")
    movementStartDate = datetime.now()
    set_filenames(movementStartDate)
    ms.setVidDateStr(str(movementStartDate)) # for webserver

    # os.system() maybe problematic, module subprocess should be used (compare flaskBird.py)
    # os.system('python3 /home/pi/station2/dhtBird.py') # send environment

    vidData = io.BytesIO() # binary video container for upload (stream cannot be uploaded directly)
    # send circBuff + following 5 secs video to vidData
    # guards against video size being unlimited
    camera.wait_recording(5) # continue camera recording
    stream.copy_to(vidData) # copy to bytes container instead of file
    stream.clear()
    movementEndDate = datetime.now()

    movementData = {}
    movementData["start_date"] = str(movementStartDate)
    movementData["end_date"] = str(movementEndDate)
    movementData["audio"] = "audioKey"
    movementData["weight"] = wght # just the max
    movementData["video"] = "videoKey"
    movementData["environment"] = {}
    # ms.log(str(movementData)) # type dict

    files = {}
    files["json"] = (None, json.dumps(movementData), 'application/json')
    # files['json'] is tuple like:
    # (None, '{"audio": "audioKey", "video": "videoKey", "weight": 99, "environment": {}}', 'application/json')

    # Audio required by API
    audData = io.open(temp_audio_filename, "rb", buffering = 0)
    files['audioKey'] = (audio_filename, audData.readall())
    audData.close()

    vidData.seek(0) # without this, vidData.read() will be empty
    files['videoKey'] = (video_filename, vidData.read()) # or just vidData?
    vidData.seek(0)
    vidData.truncate() # clear for reuse, problematic write without threading lock?
    vidData.close()

    send_realtime_movement(files)

#### system functions:
def handle_exit(sig, frame):
    raise(SystemExit) # better signal.raise_signal(signal.SIGTERM) ?

# https://www-uxsup.csx.cam.ac.uk/courses/moved.Building/signals.pdf
signal.signal(signal.SIGTERM, handle_exit)

# def send_movement(sig, frame): # needs this args when called by SIGINT
# signal.signal(signal.SIGINT, send_movement)

def cleanAndExit():
    ms.log("clean up mainFoBird.py")
    # unload balance:
    child1.terminate()
    child1.join() # block until terminated
    # unload video:
    if camera.recording:
        camera.stop_recording()
    camera.close()
    sys.exit(0)

def readBalance(bQ):
# process 'child1': fifo receives weight and puts it into bQ
# inside child process can be:
    fifo = "ramdisk/birdpipe"

    if not fifoExists(fifo):
        os.mkfifo(fifo)
        ms.log("mainFoBird created " + fifo)

    fp = open(fifo, 'r')
    while True:
        try:
            line = fp.readline()
            data = line.strip() # remove whitespace
            if (data != ""):
                ms.log("fifo rcvd: " + data)
                bQ.put(float(data))
        except(SystemExit): # only except: won't catch nameError (unknown vars)
            fp.close()
            break

#### main program:
if __name__ == "__main__": # must define process main for multiprocessing
    # predefined variables for sending functions:
    audio_filename = None
    video_filename = None
    temp_audio_filename = 'wav/min.wav'
    data_filename = None

    ms.init() # init module msgBird
    # variables from configBird.py: dev_mode, vidsize, losize ...
    if dev_mode: ms.log("Dev Mode, files not sent (see json in ./movements)")

    # Setup Camera 
    ms.log("Set up camera")

    camera = picamera.PiCamera()
    camera.rotation = camera_rotation
    camera.resolution = vidsize
    # dashcam mode, overwrites the same 5 secs continuously, before video is finally triggered and appended in track_movement():
    stream = picamera.PiCameraCircularIO(camera, seconds=5)
    camera.start_recording(stream, format='h264')

    ms.log("Set up balance fifo as child process")
    bQueue = multiprocessing.Queue()
    child1 = multiprocessing.Process(target=readBalance, args=(bQueue,)) # important comma, because type(args) = tuple
    child1.start()

    ms.log("Start Birdiary and listen for fifo")
    # capture image for local webserver on http://192.168.178.210:8080 (flaskBird.py):
    # 1) disable browser cacheing of img.jpg 2) avoid serving incomplete img: browser displays (imgNum - 1).jpg
    imgNum, imgStore, imgCntRestart = 0, 3, 32767 # imgNum current img, imgStore quantity of stored images
    sleepTime = 1.0
    imgNum = preloadCaptures(imgStore, sleepTime) # capture imgStore times a picture
    dirName = 'ramdisk/' # ending with /
    while True:
        try:
            # capture new img:
            imgName = dirName + 'img' + str(imgNum) + '.jpg'
            capture_img(imgName)
            # ms.log("img capture: " + str(imgNum))
            ms.setImgCnt(imgNum)
            # delete older img:
            imgDel = imgNum - imgStore
            if imgDel < 0: imgDel = imgCntRestart + imgDel + 1 # after img counter reset, + imgDel means subtract as imgDel is negative
            imgDelName = dirName + 'img' + str(imgDel) + '.jpg'
            if os.path.exists(imgDelName): 
                os.remove(imgDelName)
                # ms.log("img remove: " + str(imgDel))
            else: ms.log("missing for removal: " + imgDelName) # should not happen? adapt capture too fast?
            # reset img counter:
            if imgNum < imgCntRestart: imgNum += 1 # test of overflow, debug with imgCtnRestart = 16
            # if imgNum < 32767: imgNum += 1 # 32767 = 16bit 0x7fff
            else: imgNum = 0 # reset img counter

            time.sleep(sleepTime) # for fastest process in loop = video img capture
        except (SystemExit):
            # simply except() does not show scripting errors
            cleanAndExit()
#### end