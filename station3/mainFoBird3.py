'''
- Captures still images continuously to a RAM disk, rotating between a set number of image files.
- Monitors a FIFO pipe (ramdisk/birdpipe) for incoming weight data from a child process.
- Uses multiprocessing for sensor input (balance).
- Uses a custom messaging/logging system (msgBird) and local config files.
When weight data is received:
- It switches to video mode.
- Records a short H264 video (using a memory buffer).
- Loads a predefined audio sample.
- Packs this with metadata (weight, timestamp, etc.).
- Sends it via an HTTP POST request to remote birdiary server.
- Falls back to saving locally if upload fails.
'''
import os
import subprocess
import sys
from datetime import datetime
import time
import json
import requests
import multiprocessing
import io
import numpy as np

from picamera2 import Picamera2
from picamera2.encoders import H264Encoder, Quality
from picamera2.outputs import FileOutput, CircularOutput
import libcamera
import importlib.metadata # only for picamera2 version printing, because there is no 'picamera2.__version__'

import msgBird as ms
from sharedBird import fifoExists, write_gallery, write_binVideo
from configBird3 import *

testmode = False # define outside any block ('if __name__ == "__main__":' also is a block) and use 'global testmode' in all functions, that write to it (only main()), but not in the ones that only read it.

def capture_img(picam, dest):
    tmp_dest = dest + ".tmp"
    picam.capture_file(tmp_dest, name="lores", format="jpeg") # lores YUV420 and jpeg were not compatible (error: Buffer has wrong number of dimensions (expected 2, got 3))
    os.replace(tmp_dest, dest)
    if testmode: ms.log(f"Captured still to {dest}")

def whitebalance(picam):
    # Enable AWB to get correct gains
    picam.set_controls({"AwbEnable": True})
    time.sleep(1.5)
    gains = tuple(round(g, 2) for g in picam.capture_metadata()["ColourGains"])
    camsetting = {
        "AwbEnable": False,
        "ColourGains": gains
    }
    picam.set_controls(camsetting)


def get_brightness(picam, now):
    # frame = picam.capture_array(name="main")
    # if testmode: ms.log(f"frame shape in brightness calc: {frame.shape}")
    # avg_brightness = round(np.mean(frame[:, :, 0]))
    metadata = picam.capture_metadata()
    # luxdata = metadata.copy()
    metalux = round(metadata.get("Lux")) # metadata["Lux"], metadata.get("Lux", None)
    exposure = round(metadata.get("ExposureTime"))
    gain = round(metadata.get("AnalogueGain"))
    luxdata = {
        "timestamp": f"{now.year:04d}:{now.month:02d}:{now.day:02d}:{now.hour:02d}:{now.minute:02d}",
        "metaLux": metalux,
        "exposure": exposure,
        "gain": gain
    }

    if metalux < luxThreshold[0]: # luxThreshold is a list from config.json
        luxcategory = 1 # dark
    elif metalux < luxThreshold[1]:
        luxcategory = 2 # dim
    elif metalux < luxThreshold[2]:
        luxcategory = 3 # normal
    else:
        luxcategory = 4 # bright
    # check for over-/under-expo:
    # luxLimit = [500,10000] in config.json
    # expoScore = gain * exposure ? beware: high expoScore is low metaLux
    # luxcategory > 4 leads to standby in ms.setLux() and ms.getStandby()
    if metalux < luxLimit[0]:
        luxcategory = 5 # too dark
    elif metalux > luxLimit[1]:
        luxcategory = 6 # too bright

    # luxlabel = ["undef", "dark", "dim", "normal", "bright", "too dark", "too bright"]

    luxdata["luxcategory"] = luxcategory
    # if light_level != set_brightness.last_light_level:
    ms.setLux(luxcategory) # this also sets "autostdby" for bad light conditions
    # ms.setLuxRaw(f'{metalux} at {luxdata["timestamp"]}, gain {gain}/ expo {exposure}')
    ms.setLuxRaw(f'Lux {metalux}/ gain {gain}/ expo {exposure}') # format for desktop widgets.py
    if now.minute % 15 == 0 or get_brightness.last_logged_minute == -1: # log every 15 minutes or at first call
        if now.minute != get_brightness.last_logged_minute:
            get_brightness.last_logged_minute = now.minute
            whitebalance(picam)
            luxProtocol(luxdata)
            if luxcategory > 4:
                ms.log(f"stdby /resetting camera due to extreme metalux {metalux} at {now}")
                picam.set_controls({'ExposureTime': 0, 'AnalogueGain': 1.5}) # 0 means "AeEnable resets exposure according to preselected gain", see https://github.com/raspberrypi/picamera2/issues/1305
                time.sleep(0.5)

get_brightness.last_logged_minute = -1 #static var

def luxProtocol(lData):
    camdatafile = "camdata/camdata.json" # not suited for ramdisk/ to spare SD card, because data of several days/sessions
    data = []
    maxdata = 100
    if os.path.exists(camdatafile):
        with open(camdatafile, "r") as infile:
            try:
                data = json.load(infile)
            except json.JSONDecodeError:
                ms.log(f"Error decoding JSON from {camdatafile}")
                pass

        data.append(lData)
        if len(data) > maxdata:
            data = data[-maxdata:]

        with open(camdatafile, "w") as outfile:
            json.dump(data, outfile, indent=2)

def send_realtime_movement(files):
    uploadFail = True # in case of upload failure save locally
    try:
        ms.log('sending to ' + serverUrl + 'movement/' + boxId)
        r = requests.post(serverUrl + 'movement/' + boxId, files=files, timeout=60)
        ms.log('Movement data sent: ' + files['json'][1])
        ms.log('Corresponding movement_id: ' + r.text)
        resp = r.text.lower()
        if 'error' in resp:
            ms.log('files kept - server sent error text')
            return uploadFail
        else:
            uploadFail = False
            return uploadFail
    except requests.RequestException as e:
        ms.log(f"failed movement upload: {e}")
        return uploadFail

def send_movement(circ_output, picam, wght, stop_event): # first parameter is either circ_output OR picam, the latter in case of no circ_output
    if upmaxcnt > 0 and send_movement.vid_cnt >= upmaxcnt: # upmaxcnt=0 means no limit
        ms.log("upload limit reached")
        subprocess.call(f"bash {birdpath['appdir']}/tasmotaDown.sh limitdown", shell=True)
        time.sleep(2)
        return

    ms.log("***movement upload***")
    movementStartDate = datetime.now()
    movementStartStr = str(movementStartDate)

    video_filename = movementStartStr + ".h264"
    audio_filename = movementStartStr + ".wav"

    # for local review:
    daydir = "daydir"
    imgCnt, imgMax = 0, 9
    videoUrlStr = movementStartStr.replace(":", "").replace(" ", "_")

    # for video with circ output (dashcam):
    stop_event.clear()   # ensure clean state
    outmem = io.BytesIO()
    circ_output.fileoutput = outmem
    circ_output.start()

    # instead of 'time.sleep(videodurate)' poll for stop_event from readBalance():
    ms.log(f"video started at {time.time()}")
    deadline = time.time() + videodurate # time.time() returns seconds.msecs since epoch (1.1.1970)
    while time.time() < deadline:
        if imgCnt < imgMax:
            imgName = f"{daydir}/{videoUrlStr}.{imgCnt}.jpg"
            capture_img(picam, imgName)
            ms.log(f"img#{imgCnt} taken at {time.time()}")
            imgCnt += 1
        if stop_event.is_set():
            ms.log("Rec stop by -1 signal")
            time.sleep(1.0)  # record ~1 second extra
            break
        else:
            time.sleep(0.5) # record img interval
        time.sleep(0.05)
    
    circ_output.stop()
    stop_event.clear()
    outmem.seek(0)
    full_video = outmem.getvalue()
 
    '''
    # for video with no circ_output
    posttrigger = io.BytesIO()
    post_file_output = FileOutput(posttrigger)
    post_encoder = H264Encoder()
    picam.start_encoder(post_encoder, post_file_output, quality=Quality.MEDIUM) # picam.start_recording(post_encoder, post_file_output, quality=Quality.MEDIUM)
    start_ns = time.time_ns()
    time.sleep(videodurate)
    picam.stop_encoder() # picam.stop_recording() contains a picam.stop() and therefore will hang following .capture_file() or .capture_metadata()
    posttrigger.seek(0)
    full_video = posttrigger.read()
    '''

    if testmode:
        ms.log("Test mode: skipping upload")
        ms.log(f"full_video size: {len(full_video)} bytes")
        write_binVideo(movementStartStr, full_video)
        ms.log("Test video saved locally in /keep.")
        return

    movementEndDate = datetime.now()

    movementData = {
        "start_date": movementStartStr,
        "end_date": str(movementEndDate),
        "audio": "audioKey",
        "weight": wght,
        "video": "videoKey",
        "environment": {}
    }

    with open("wav/min.wav", "rb") as f:
        audio_data = f.read()
    files = {
        "json": (None, json.dumps(movementData), 'application/json'),
        "audioKey": (audio_filename, audio_data),
        "videoKey": (video_filename, full_video)
    }

    movementStart = movementStartStr.split('.')[0] # remove terminal msecs part
    send_movement.vid_cnt += 1
    ms.setVidCnt(send_movement.vid_cnt)

    upfail = send_realtime_movement(files)
    if upfail:
        write_gallery(movementData)
        write_binVideo(movementData["start_date"], full_video)
        ms.setVidDateStr(f"video#{send_movement.vid_cnt} at {movementStart} kept local")
        subprocess.call(f"bash {birdpath['appdir']}/mdroid.sh VideoUpfail_keepdir", shell=True)
    else:
        if upmaxcnt>0: ms.setVidDateStr(f"video#{send_movement.vid_cnt} of {upmaxcnt} at {movementStart}")
        else: ms.setVidDateStr(f"video#{send_movement.vid_cnt} at {movementStart}")
        subprocess.call(f"bash {birdpath['appdir']}/mdroid.sh newVideo{send_movement.vid_cnt}", shell=True)

    # On Feb.2026 module 'imp' is not available in tensorflow wheel for python 3.13 on arm64
    # ... so the following subprocess runs inside birdvenv, using python 3.11.8
    # start tflite_runtime on daydir:
    # .Popen runs asynchronously, .call does not
    cmd = f"{birdpath['appdir']}/{daydir}/run_classify.sh {birdpath['appdir']}/{daydir}/{videoUrlStr}"
    ms.log(f"running subprocess: {cmd}")
    subprocess.Popen(
        cmd,
        shell=True,
        stdout=sys.stdout,
        stderr=sys.stderr
    )

send_movement.vid_cnt = 0

def readBalance(bQ, stop_event):
    fifo = birdpath['fifo']
    if not fifoExists(fifo):
        os.mkfifo(fifo)
        ms.log(f"{sys.argv[0]} created {fifo}")

    with open(fifo, 'r') as fp:
        try:
            while True:
                line = fp.readline()
                data = line.strip()
                if data != "":
                    value = float(data)
                    ms.log("fifo rcvd: " + data)
                    if value == -1:
                        stop_event.set()
                    elif ms.getStandby() == 0:
                        bQ.put(float(data))
        except Exception as e:
            ms.log(f"Exception in readBalance: {e}")

def cleanAndExit(picam, child):
    try:
        ms.log(f"{sys.argv[0]} exiting {datetime.now()}")
        # if picam.running -> no .running or similar attribute
        try:
            picam.close() # freezes camsettings from the night before?
        except Exception:
            pass
        if child.is_alive():
            child.terminate()
            child.join()
    except Exception as e:
        ms.log(f"Error while exiting: {e}")
    finally:
        sys.exit(0)

def main():
    global testmode
    ms.init()
    # Check for available camera
    if not Picamera2.global_camera_info():
        ms.log("No camera detected. Exiting.")
        sys.exit(1)
    
    if len(sys.argv) > 1 and sys.argv[1] == "test":
        ms.log(f"{sys.argv[0]} running in test mode")
        testmode = True
    else: 
        testmode = False
        ms.log(f"Starting {sys.argv[0]} at {datetime.now()}")

    ms.log(f'picam2 version {importlib.metadata.version("picamera2")}')
    ms.setVidCnt(0)
    ms.emptyVidDateStr()
    # ms.setUpmode(1) # direct upload
    ms.setLux(3) # set luxcategory to normal
    ms.log("Set up balance receive as child process")
    bQueue = multiprocessing.Queue()
    stop_recording_event = multiprocessing.Event()
    child1 = multiprocessing.Process(target=readBalance, args=(bQueue, stop_recording_event))
    child1.start()
    camera_transform = libcamera.Transform(hflip=hflip_val, vflip=vflip_val)

    with Picamera2() as picam:
        config = picam.create_video_configuration(
            main={"size": vidsize, "format": "RGB888"},
            lores={"size": losize, "format": "YUV420"},
            transform=camera_transform
        )

        # encoder = H264Encoder() in send_movement()
        picam.configure(config)
        time.sleep(0.5)
        picam.start()
        '''
        # "AnalogueGain" and "ExposureTime" are managed best by picamera2 itself
        camsetting = {
            "AeEnable": False,
            "AnalogueGain": 1.5,
            "ExposureTime": 15000,
            "AwbEnable": False,
            "ColourGains": (1.5, 1.2)
        }
        picam.set_controls(camsetting)
        '''
        now = datetime.now()
        get_brightness(picam, now) # Set initial brightness, also calls whitebalance(picam)

        # for circular output:
        encoder = H264Encoder() # for no circ_output this is moved into send_movement() and the following 3 lines are omitted
        c_output = CircularOutput()
        picam.start_recording(encoder, c_output, quality=Quality.MEDIUM) # or better picam.start_encoder(...)
        time.sleep(5) # accumulate pretrigger frames

        sleepTime = 1.0
        dirName = birdpath['ramdisk']
        oldimg = []
        maxOldImg = 3
        inactive_counter = 0

        try:
            while True:
                if not bQueue.empty(): # child1 process 'readBalance()' fills bQueue after filtering for ms.getStandby()
                    ms.setRecording(1)
                    # trigger_ns = time.time_ns() # check for nanosecs till recording, is exaggerated
                    weight = bQueue.get()
                    # picam.set_controls(camsetting)
                    send_movement(c_output, picam, weight, stop_recording_event) # if no circ_output, replace c_output by picam
                    ms.setRecording(0)
                    # reset_camera(picam, camsetting, config)
                    while not bQueue.empty(): bQueue.get()
                    metadata = picam.capture_metadata() # read back from picam, after reset_camera()
                    ms.log(f"sent video with ExposureTime {metadata.get('ExposureTime')} and AnalogueGain {metadata.get('AnalogueGain')}")

                elif ms.getClientActive() == 1: # set by flaskBird.py
                    if testmode: ms.log("shooting a still")
                    inactive_counter = 0
                    timestamp = round(time.time() * 1000)
                    imgName = f"{dirName}/{timestamp}.jpg"
                    capture_img(picam, imgName)
                    ms.setImgCnt(timestamp)
                    oldimg.append(imgName)
                    if len(oldimg) > maxOldImg:
                        oldest = oldimg.pop(0)
                        if os.path.exists(oldest):
                            os.remove(oldest)
                else:
                    now = datetime.now()
                    if testmode: ms.log("brightness check instead of still possible")
                    # clear forgotten standby after 300 secs of webGUI inactivity:
                    inactive_counter += 1 if inactive_counter < 32760 else 0
                    if inactive_counter == 300: ms.clearStandby()
                    get_brightness(picam, now)

                time.sleep(sleepTime)

        except Exception as e:
            ms.log(f"Exception in main loop: {e}")
        finally:
            cleanAndExit(picam, child1)

if __name__ == "__main__":
    main()
