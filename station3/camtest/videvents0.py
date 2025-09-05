'''When this webcam script is filming a stop watch, the timing of recordings can be controlled.
    https://github.com/raspberrypi/picamera2'''
import os
import subprocess
import time
import io
from picamera2 import Picamera2
from picamera2.encoders import H264Encoder, Quality
from picamera2.outputs import FileOutput, CircularOutput
import libcamera
import importlib.metadata # only for picamera2 version printing, because there is no 'picamera2.__version__'

def capture_img(picam, dest):
    picam.capture_file(dest, name="main", format="jpeg") # lores YUV420 and jpeg are not compatible (error: Buffer has wrong number of dimensions (expected 2, got 3))

def reset_camera(picam, camsetting, config):
    start_ns = time.time_ns()
    picam.stop()
    picam.configure(config)
    picam.start()
    picam.set_controls(camsetting)
    print(f"reset_cam_time {(time.time_ns() - start_ns) // 1_000_000} ms")

def write_binVideo(newfname, binVideo):
    fname = newfname + '.h264'
    with open(fname, 'wb') as vfile:
        vfile.write(binVideo)

    mp4video = newfname + '.mp4'
    cmd = f'ffmpeg -y -framerate 24 -i "{fname}" -c copy "{mp4video}"'
    ffproc = subprocess.Popen(cmd, shell=True)
    ret = ffproc.wait() # await cmd completion
    if ret == 0: os.remove(fname)

def main():
    print(f'picam2 version {importlib.metadata.version("picamera2")}')

    camsetting = {
        "AeEnable": False,
        "AnalogueGain": 2.0,
        "ExposureTime": 50000,
        "AwbEnable": False,
        "ColourGains": (1.5, 1.2)
    }

    camera_transform = libcamera.Transform(hflip=1, vflip=1)

    with Picamera2() as picam:
        config = picam.create_video_configuration(
            main={"size": (1280, 960), "format": "RGB888"},
            lores={"size": (320, 240), "format": "YUV420"},
            transform=camera_transform
        )

        picam.configure(config)
        time.sleep(0.5)
        picam.start()
        picam.set_controls(camsetting)

        timestamp = round(time.time() * 1000)
    
        print("shooting a still-1")
        imgName = f"{timestamp}pre.jpg"
        capture_img(picam, imgName)

        post_encoder = H264Encoder()
        posttrigger = io.BytesIO()
        post_file_output = FileOutput(posttrigger)

        print("posttrigger video-1")
        picam.start_encoder(post_encoder, post_file_output, quality=Quality.MEDIUM)
        time.sleep(3)
        # picam.stop_recording() contains a picam.stop() and therefore hangs a following picam.capture_file(). Also do not use together with picam.stop_encoder()!
        picam.stop_encoder() # replaces reset_camera() !!
        # reset_camera(picam, camsetting, config) # containing picam.stop() and .start()

        posttrigger.seek(0)
        postdata = posttrigger.getvalue()
        print(f"posttrigger_video size: {len(postdata)} bytes")
        write_binVideo(f"{timestamp}post-1", postdata)
        # clear ioBuffer for reuse:
        posttrigger.seek(0)
        posttrigger.truncate(0)

        print("shooting a still-2")
        imgName = f"{timestamp}post.jpg"
        capture_img(picam, imgName)

        print("posttrigger video-2")
        picam.start_encoder(post_encoder, post_file_output, quality=Quality.MEDIUM)
        time.sleep(3)
        picam.stop_encoder()
        posttrigger.seek(0)
        postdata = posttrigger.getvalue()
        print(f"posttrigger_video size: {len(postdata)} bytes")
        write_binVideo(f"{timestamp}post-2", postdata)

        print("end")

if __name__ == "__main__":
    main()