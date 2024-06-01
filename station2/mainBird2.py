# main.py file from birdiary station120423.img adapted for RPiZero and shortened
# picamera2: DO NOT enable legacy camera in raspi-config nor gpu_mem in /boot/config.txt, else: 'Not enough buffers provided by V4L2VideoDevice' on RPi02W .
# my main problem with picamera2: no 270° rotation option like in picamera1, just hflip/vflip (sky direction at the side, never the top, when camera built in sideways)
# code for environnement and DHT22 sensor has moved to dhtBird.py, which can be called by this script (os.system('python3 /home/pi/station2/dhtBird.py')) or crontab
# microphone/audio removed apart from uploading empty audio file 'wav/min.wav' to requesting API
import os
import sys
import signal
from datetime import datetime
import time
import json
import requests
# picamera2:
import io
import libcamera
from picamera2.encoders import H264Encoder, Quality
from picamera2.outputs import CircularOutput
from picamera2 import Picamera2
# balance:
import multiprocessing # give to balance its own process -> readBalance(), this puts measured weight into bQueue
# own local modules:
import msgBird as ms # imports different fcts to write json, later fetched by flaskBird webpage javascript
from sharedBird import fifoExists
from configBird2 import * # import all variables from ./configBird2.py

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
    global picam2
    try:
        req = picam2.capture_request()
        img = req.make_image("main")
        img = img.resize(losize)
        img.save(dest, format='jpeg', quality=75) # quality default 95
        req.release()
    except Exception as error:
        ms.log('birdCaptureError: ' + error)

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
    except (requests.ConnectionError, requests.Timeout) as exception:
        ms.log('failed movement upload - ' + str(exception))

def send_movement(wght):
    print("***movement upload***")
    movementStartDate = datetime.now()
    set_filenames(movementStartDate)
    ms.setVidDateStr(str(movementStartDate))
    # os.system('python3 /home/pi/station2/dhtBird.py') # send environment

    # send circBuff + following 5 secs video to vidData
    # guards against video size being unlimited
    circOut.start()
    time.sleep(5)
    circOut.stop()
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

    vidData.seek(0)
    files['videoKey'] = (video_filename, vidData.read()) # oder nur vidData?
    vidData.seek(0)
    vidData.truncate() # clear for reuse

    send_realtime_movement(files)

#### system functions:
def handle_exit(sig, frame):
    raise(SystemExit) # better signal.raise_signal(signal.SIGTERM) ?

# https://www-uxsup.csx.cam.ac.uk/courses/moved.Building/signals.pdf
signal.signal(signal.SIGTERM, handle_exit)

# def send_movement(sig, frame): # needs this args when called by SIGINT
# signal.signal(signal.SIGINT, send_movement)

def cleanAndExit():
    ms.log("clean up mainBird2.py")
    # unload balance:
    child1.terminate()
    child1.join() # block until terminated
    # unload video:
    picam2.stop_recording()
    vidData.close()
    sys.exit(0)

#### sensor processing: balance in child1, camera in main process
def readBalance(bQ):
# process 'child1': fifo receives weight and puts it into bQ
# inside child process can be:
    fifo = "ramdisk/birdpipe"

    if not fifoExists(fifo):
        os.mkfifo(fifo)
        ms.ms.log("mainAckBird created " + fifo)

    fp = open(fifo, 'r')
    while True:
        try:
            line = fp.readline()
            data = line.strip() # remove whitespace
            if (data != ""):
                ms.ms.log("fifo rcvd: " + data)
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
    # variables from configBird.py: dev_mode, vidsize, losize, hflip_val, vflip_val
    if dev_mode: ms.log("Dev Mode, files not sent (see json in ./movements)")

    # Setup Camera 
    ms.log("Set up camera and ioBuffer")
    vidData = io.BytesIO() # binary video container for upload (stream cannot be uploaded directly)

    picam2 = Picamera2()
    video_config = picam2.create_video_configuration(main={"size": vidsize, "format": "RGB888"}, lores={
                                                    "size": losize, "format": "YUV420"})
    video_config["transform"] = libcamera.Transform(hflip=hflip_val, vflip=vflip_val)
    picam2.configure(video_config)
    encoder = H264Encoder()
    circOut = CircularOutput()
    circOut.fileoutput = vidData
    picam2.start_recording(encoder, circOut, quality=Quality.MEDIUM) # medium is default

    ms.log("Set up balance as child process")
    bQueue = multiprocessing.Queue()
    child1 = multiprocessing.Process(target=readBalance, args=(bQueue,)) # important comma, because type(args) = tuple
    child1.start()

    ms.log("Start Birdiary and listen for child")
    ms.init() # init module msgBird
    # capture image for local webserver on http://192.168.178.210:8080 (separate flask python program):
    # 1) disable browser cacheing of img.jpg 2) avoid serving incomplete img: browser displays (imgNum - 1).jpg
    # For convenience the code is not yet checking for the 32 bit upper limit of imgNum (2,147,483,647)
    imgNum, imgStore = 0, 5 # imgNum current img, imgStore quantity of stored images
    sleepTime = 1.0
    imgNum = preloadCaptures(imgStore, sleepTime) # capture imgStore times a picture

    while True:
        try:
            imgDelName = 'ramdisk/img' + str(imgNum - imgStore) + '.jpg'
            if os.path.exists(imgDelName): os.remove(imgDelName)
            else: ms.log("missing for removal: " + imgDelName) # should not happen? adapt capture too fast?
            imgName = 'ramdisk/img' + str(imgNum) + '.jpg'
            capture_img(imgName)
            ms.setImgCnt(imgNum)
            if imgNum < 32767: imgNum += 1 # 32767 = 16bit 0x7fff
            else: imgNum = preloadCaptures(imgStore, sleepTime)

            # look for weight posted by readBalance()
            if not bQueue.empty():
                weight = bQueue.get()
                # print(str(weight))
                send_movement(weight) # blocking function for video creation/upload, besides python non blocking I/O functions not as easy as in nodeJS
                # empty bQueue?:
                while not bQueue.empty(): bQueue.get()

            time.sleep(sleepTime) # for fastest process in loop = video img capture
        except (SystemExit):
            # simply except() does not show scripting errors
            cleanAndExit()
#### end of main process