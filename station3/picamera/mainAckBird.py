# main.py file from birdiary station120423.img adapted for RPiZero and shortened
# for picamera enable legacy camera in raspi-config and gpu_mem=256 in /boot/config.txt (but not for picamera2!). picamera2 not preferred, because it lacks rotation.
# code for DHT22 sensor moved to dhtBird.py, which can be called by this script (os.system('python3 /home/pi/station2/dhtBird.py')) or crontab
# code for HX711 sensor moved to hxFiBird.py, which sends the measured weight via fifo to this script's child1 process. flaskBird webserver can send to this fifo pipe too.
# the ...Ack... means, no automatic upload, but watch video first, then confirm its upload
# microphone/audio removed apart from uploading empty audio file 'wav/min.wav' to requesting API
import os # for calling dhtBird.py and fifo receive
import subprocess
import shutil
import sys
import signal
from datetime import datetime
import time
import json
# picamera1:
# even the simplest standalone picamera program is multithread ('l' in 'ps aux')!
import picamera
# weight messages from hxFiBird.py and flaskBird.py are received by fifo within child1 process:
import multiprocessing
# own local modules:
from sharedBird import fifoExists # shared functions in shareBird.py
import msgBird as ms # imports different fcts to write json, later fetched by flaskBird webpage javascript
from configBird import dev_mode, camera_rotation, vidsize, losize # import variables from ./configBird.py

# these directories should exist within ./station2 and are no longer tested for by module os:
#   pigpioBird environments movements logs ramdisk wav

# logname = "logs/birdiary.log", replaced by 'python3 mainBird2.py >> logs/birdiary.log'
#### own logging functions:
# def ms.log(line) in msgBird.py

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
    camera.wait_recording(5) # continue camera recording
    stream.copy_to(video_filename)
    stream.clear()
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
    ms.log("clean up mainAckBird.py")
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
    # variables from configBird.py: dev_mode, vidsize, losize ...
    if dev_mode: ms.log("Dev Mode, files not sent (see json in ./movements)")

    # Setup Camera 
    ms.log("Setting up camera")

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
    while not bQueue.empty(): bQueue.get()

    ms.log("Start Birdiary and listen for fifo")
    # capture image for local webserver on http://192.168.178.210:8080 (flaskBird.py):
    # 1) disable browser cacheing of img.jpg 2) avoid serving incomplete img: browser JS displays (imgNum - 1).jpg
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
#### end