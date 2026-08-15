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
    daydir = "ramdisk" # "ramdisk/daydir" would have to be created first
    model = "model"
    imgCnt, imgMax = 0, 30 # one img is below 20 kB, so enough space on ramdisk
    videoUrlStr = movementStartStr.replace(":", "").replace(" ", "_")

    # for video with circ output (dashcam):
    stop_event.clear()   # ensure clean state
    outmem = io.BytesIO()
    circ_output.fileoutput = outmem
    circ_output.start()

    # instead of 'time.sleep(videodurate)' poll for stop_event from readBalance():
    ms.log(f"video started at {datetime.now()}")
     # time.perf_counter() is monotonic and only for time diff, time.time() is different and returns seconds.msecs since epoch (1.1.1970)
    deadline = time.perf_counter() + videodurate
    while time.perf_counter() < deadline:
        # Check for stop signal first
        if stop_event.is_set():
            ms.log("Rec stop by -1 signal")
            time.sleep(1.0)  # record ~1 second extra
            break            # This exits the while loop completely!

        # Handle image capture
        if imgCnt < imgMax:
            imgName = f"{daydir}/{videoUrlStr}.{imgCnt}.jpg"
            capture_img(picam, imgName) # this slows the loop down implicitely
            # ms.log(f"img#{imgCnt} taken at {time.time()}")
            imgCnt += 1
            # record img interval:
            time.sleep(0.1) 
        else:
            # Once 30 images are taken, explicitly drop into a longer, 
            # low-overhead sleep to protect the CPU until the deadline hits
            time.sleep(0.25)
    
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
        if send_movement.vid_cnt % recordstep == 0: # send wapp message only on multiples of reportstep
            subprocess.call(f"bash {birdpath['appdir']}/mdroid.sh newVideo{send_movement.vid_cnt}", shell=True)
        else: # call mdroid.sh with 2nd arg 'w', which skips wapp message
            subprocess.call(f"bash {birdpath['appdir']}/mdroid.sh newVideo{send_movement.vid_cnt} w", shell=True)

    # On Feb.2026 module 'imp' is not available in tensorflow wheel for python 3.13 on arm64
    # ... so the following subprocess runs inside birdvenv, using python 3.11.8
    # start tflite_runtime on daydir:
    # .Popen runs asynchronously, .call does not
    cmd = f"{birdpath['appdir']}/{model}/run_classify.sh {videoUrlStr}"
    ms.log(f"running subprocess: {cmd}")
    subprocess.Popen(
        cmd,
        shell=True,
        stdout=sys.stdout,
        stderr=sys.stderr
    )

send_movement.vid_cnt = 0



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
