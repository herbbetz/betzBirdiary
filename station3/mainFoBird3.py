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
    picam.capture_file(tmp_dest, name="main", format="jpeg") # lores YUV420 and jpeg are not compatible (error: Buffer has wrong number of dimensions (expected 2, got 3))
    os.replace(tmp_dest, dest)
    if testmode: ms.log(f"Captured still to {dest}")

'''
# only needed when using picam.stop_recorder(), which contains a picam.stop() and will therefore hang a following .capture_file() or .capture_metadata()! Use picam.stop_encoder() instead!
def reset_camera(picam, camsetting, config):
    start_ns = time.time_ns()
    picam.stop()
    picam.configure(config)
    picam.start()
    picam.set_controls(camsetting)
    ms.log(f"reset_cam_time {(time.time_ns() - start_ns) // 1_000_000} ms")
'''
def get_brightness(picam, camsetting, now):
    # frame = picam.capture_array(name="main")
    # if testmode: ms.log(f"frame shape in brightness calc: {frame.shape}")
    # avg_brightness = round(np.mean(frame[:, :, 0]))
    metadata = picam.capture_metadata()
    # luxdata = metadata.copy()
    metalux = round(metadata.get("Lux")) # metadata["Lux"], metadata.get("Lux", None)
    exposure = round(metadata.get("ExposureTime"))
    gain = round(metadata.get("AnalogueGain"))
    # reset cam for extreme cases:
    expoScore = gain * exposure
    if expoScore < luxLimit[0] or expoScore > luxLimit[1]: # luxLimit = [1000,7000] in config.json
        ms.log(f"resetting camera due to extreme exposure score {expoScore} at {now}")
        picam.set_controls({'ExposureTime': 0, 'AnalogueGain': 1.5}) # 0 means "AeEnable resets exposure according to preselected gain", see https://github.com/raspberrypi/picamera2/issues/1305
        time.sleep(0.5)
    '''avg_brightness is dependant on the exposure/gain of the camsetting, so if it hits light_level thresholds (i.e. avg_brightness <40 or <80 or <150 or else),
        it will alternate between two levels despite the same scene illumination.
        Therefore make an independant scene_brightness (a lux estimate, that could be calibrated by a scale factor to an external lux meter)
    scalefactor = 1e6
    # read back camsetting from picam might be delayed:
    # exposure = metadata.get("ExposureTime")
    # gain = metadata.get("AnalogueGain")
    exposure = camsetting["ExposureTime"]
    gain = camsetting["AnalogueGain"]

    if not exposure or not gain:
        return  # Skip frame if metadata invalid and div by zero
    sc_brightness = (avg_brightness * scalefactor) / (gain * exposure)
    sc_brightness = round(sc_brightness)
    # luxThreshold = [600, 3000, 6000] in config.json, lux thresholds for dark, dim, normal, bright'''
    luxdata = {
        "timestamp": f"{now.year:04d}:{now.month:02d}:{now.day:02d}:{now.hour:02d}:{now.minute:02d}",
        "metaLux": metalux,
        "exposure": exposure,
        "gain": gain
    }

    if metalux < luxThreshold[0]: # luxThreshold is a list from config.json
        light_level, luxcategory = "dark", 1
    elif metalux < luxThreshold[1]:
        light_level, luxcategory = "dim", 2
    elif metalux < luxThreshold[2]:
        light_level, luxcategory = "normal", 3
    else:
        light_level, luxcategory = "bright", 4
    
    luxdata["luxcategory"] = luxcategory

    # if light_level != set_brightness.last_light_level:
    ms.setLux(luxcategory)
    ms.setLuxRaw(f'{metalux} at {luxdata["timestamp"]}, gain {gain}/ expo {exposure}')
    if now.minute % 15 == 0 or get_brightness.last_logged_minute == -1: # log every 15 minutes or at first call
        if now.minute != get_brightness.last_logged_minute:
            get_brightness.last_logged_minute = now.minute
            luxProtocol(luxdata)
    '''
    camsetting.update({
        "ExposureTime": { "dark": 50000, "dim": 30000, "normal": 15000, "bright": 6000 }[light_level], # 100–1,000,000 µs (e.g., 50,000 µs = 1/20s)
        "AnalogueGain": { "dark": 6.0, "dim": 3.0, "normal": 1.5, "bright": 1.0 }[light_level] # Set gain (e.g., 1.0 to 16.0 typical range)
    })
    picam.set_controls({
        "ExposureTime": camsetting["ExposureTime"],
        "AnalogueGain": camsetting["AnalogueGain"]
    })
    ms.log(f'changed when scene_bright={sc_brightness}/ avg_bright={avg_brightness}/ metaLux={metalux} to exposure:{camsetting["ExposureTime"]}/ gain:{camsetting["AnalogueGain"]}')        
    set_brightness.last_light_level = light_level
    '''
# set_brightness.last_light_level = "normal" # static variable
get_brightness.last_logged_minute = -1

def luxProtocol(lData):
    camdatafile = "camdata/camdata.json"
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

def send_movement(circ_output, wght, trigger_ns): # first parameter is either circ_output OR picam, the latter in case of no circ_output
    if send_movement.vid_cnt >= upmaxcnt:
        ms.log("upload limit reached")
        subprocess.call(f"bash {birdpath['appdir']}/tasmotaDown.sh limitdown", shell=True)
        time.sleep(2)
        return

    ms.log("***movement upload***")
    movementStartDate = datetime.now()
    movementStartStr = str(movementStartDate)

    video_filename = movementStartStr + ".h264"
    audio_filename = movementStartStr + ".wav"

    # for video with circ output (dashcam):
    outmem = io.BytesIO()
    circ_output.fileoutput = outmem
    circ_output.start()
    start_ns = time.time_ns()
    time.sleep(videodurate)
    circ_output.stop()
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

    record_latency_ms = (start_ns - trigger_ns) // 1_000_000
    ms.log(f"Trigger latency: {record_latency_ms} ms till video {movementStartStr}")
    ms.setVidDateStr(movementStartStr)

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

    upfail = send_realtime_movement(files)
    if upfail:
        write_gallery(movementData)
        write_binVideo(movementData["start_date"], full_video)
        subprocess.call(f"bash {birdpath['appdir']}/mdroid.sh VideoUpfail_keepdir", shell=True)
    else:
        send_movement.vid_cnt += 1
        ms.setVidCnt(send_movement.vid_cnt)
        subprocess.call(f"bash {birdpath['appdir']}/mdroid.sh newVideo{send_movement.vid_cnt}", shell=True)

send_movement.vid_cnt = 0

def readBalance(bQ):
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
                    ms.log("fifo rcvd: " + data)
                    if ms.getStandby() == 0:
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
    ms.log("Set up balance as child process")
    bQueue = multiprocessing.Queue()
    child1 = multiprocessing.Process(target=readBalance, args=(bQueue,))
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

        # Enable AWB to get correct gains
        picam.set_controls({"AwbEnable": True})
        time.sleep(1.5)
        gains = tuple(round(g, 2) for g in picam.capture_metadata()["ColourGains"])
        camsetting = {
            "AwbEnable": False,
            "ColourGains": gains
        }
        picam.set_controls(camsetting)
        now = datetime.now()
        get_brightness(picam, camsetting, now) # Set initial brightness

        # for circular output:
        encoder = H264Encoder() # for no circ_output this is moved into send_movement() and the following 3 lines are omitted
        c_output = CircularOutput()
        picam.start_recording(encoder, c_output, quality=Quality.MEDIUM) # or better picam.start_encoder(...)
        time.sleep(5) # accumulate pretrigger frames

        sleepTime = 1.0
        dirName = birdpath['ramdisk']
        oldimg = []
        maxOldImg = 3
        # last_logged_minute = -1

        try:
            while True:
                if not bQueue.empty():
                    trigger_ns = time.time_ns() # check for nanosecs till recording
                    weight = bQueue.get()
                    # picam.set_controls(camsetting)
                    send_movement(c_output, weight, trigger_ns) # if no circ_output, replace c_output by picam
                    # reset_camera(picam, camsetting, config)
                    while not bQueue.empty(): bQueue.get()
                    metadata = picam.capture_metadata() # read back from picam, after reset_camera()
                    ms.log(f"sent video with ExposureTime {metadata.get('ExposureTime')} and AnalogueGain {metadata.get('AnalogueGain')}")

                elif ms.getClientActive() == 1:
                    if testmode: ms.log("shooting a still")
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
                    # if now.minute % 15 == 0 and now.minute != last_logged_minute: last_logged_minute = now.minute
                    get_brightness(picam, camsetting, now)

                time.sleep(sleepTime)

        except Exception as e:
            ms.log(f"Exception in main loop: {e}")
        finally:
            cleanAndExit(picam, child1)

if __name__ == "__main__":
    main()

