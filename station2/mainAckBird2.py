# main.py file from birdiary station120423.img adapted for RPiZero and shortened
# picamera2: DO NOT enable legacy camera in raspi-config nor gpu_mem in /boot/config.txt, else: 'Not enough buffers provided by V4L2VideoDevice' on RPi02W .
# my main problem with picamera2: no 270° rotation option like in picamera1, just hflip/vflip (sky direction at the side, never the top, when camera built in sideways)
# code for environnement and DHT22 sensor has moved to dhtBird.py, which can be called by this script (os.system('python3 /home/pi/station2/dhtBird.py')) or crontab
# microphone/audio removed apart from uploading empty audio file 'wav/min.wav' to requesting API
import os
import subprocess
import shutil
import sys
import signal
from datetime import datetime
import time
import json
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
def set_filenames(movementStartS):
    global audio_filename, video_filename, data_filename
    audio_filename = 'movements/' + movementStartS + '.wav'
    video_filename = 'movements/' + movementStartS + '.h264'
    data_filename = 'movements/' + movementStartS + '.json'

def save_movement(wght):
    global video_filename, temp_audio_filename, audio_filename, data_filename
    ms.log("***movement saving***")
    movementStartDate = datetime.now()
    movementStartStr = str(movementStartDate)
    movementStartStr = movementStartStr.replace(' ', '_') # space gives problems with ffmpeg cmd
    set_filenames(movementStartStr)
    ms.setVidDateStr(movementStartStr) # for webserver and uploadBird.py

    # os.system() maybe problematic, module subprocess should be used (compare flaskBird.py)
    # os.system('python3 /home/pi/station2/dhtBird.py') # send environment

    # send circBuff + following 5 secs video to vidData
    # guards against video size being unlimited
    circOut.start()
    time.sleep(5)
    circOut.stop()

    vidData.seek(0)
    with open(video_filename, "wb") as f:
        f.write(vidData.read())
    # clear io buffer:
    vidData.seek(0)
    vidData.truncate()

    movementEndDate = datetime.now()

    # /usr/bin/ffmpeg, testVideo generated for confirm webpage 'video.html' (confirmation before being uploaded)
    testVideo = '/home/pi/station2/movements/lastvideo.mp4'
    if os.path.isfile(testVideo): os.remove(testVideo) # only the latest
    cmd = 'ffmpeg -framerate 24 -i /home/pi/station2/' + video_filename + ' -c copy ' + testVideo
    ms.log("ffmpeg cmd: " + cmd)
    # subprocess.run() waits for cmd to complete, with check=true would raise CalledProcessError on exit code not 0
    # subprocess.call() waits for completion and returns exit code
    ffproc = subprocess.Popen(cmd, shell=True)
    ret = ffproc.wait() # await cmd completion
    if ret == 0: ms.setConfirm()
    ms.log("ffmpeg exit code: " + str(ret))

    # /usr/bin/curl
    cmd = "bash /home/pi/station2/mdroid.sh newVideo"
    subprocess.call(cmd, shell=True) # returns exit code of cmd
    # ms.log("curl exit code: " + str(ret))


    shutil.copy(temp_audio_filename, audio_filename)

    movementData = {}
    movementData["start_date"] = movementStartStr
    movementData["end_date"] = str(movementEndDate)
    movementData["audio"] = "audioKey"
    movementData["weight"] = wght # just the max
    movementData["video"] = "videoKey"
    movementData["environment"] = {}
    # ms.log(str(movementData)) # type dict
    with open(data_filename, 'w') as wfile:
        json.dump(movementData, wfile)

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
        ms.log("mainAckBird created " + fifo)

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
    # variables from configBird.py: dev_mode, vidsize, losize, hflip_val, vflip_val

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
                save_movement(weight) # blocking function for video creation/upload, besides python non blocking I/O functions not as easy as in nodeJS
                # empty bQueue?:
                while not bQueue.empty(): bQueue.get()

            time.sleep(sleepTime) # for fastest process in loop = video img capture
        except (SystemExit):
            # simply except() does not show scripting errors
            cleanAndExit()
#### end of main process