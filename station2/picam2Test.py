# 7.2.3 of picam2 manual
import time
import libcamera
from picamera2.encoders import H264Encoder, Quality
from picamera2.outputs import CircularOutput
from picamera2 import Picamera2
picam2 = Picamera2()
vidsize = (1280, 960) # (1280, 960) or adapt to sensor's selection 1296x972, see prog. output?
losize = (320, 240)
video_config = picam2.create_video_configuration(main={"size": vidsize, "format": "RGB888"}, lores={
                                                 "size": losize, "format": "YUV420"})
video_config["transform"] = libcamera.Transform(hflip=0, vflip=1) # 270° ?
picam2.configure(video_config)
# capture_config = picam2.create_still_configuration(main={"size": (320, 240)})
encoder = H264Encoder()
# encoder = H264Encoder(qp=30)
output = CircularOutput()
picam2.start_recording(encoder, output, quality=Quality.MEDIUM) # medium is default
# picam2.start_recording(encoder, 'medium.h264', quality=Quality.MEDIUM)
print(picam2.sensor_resolution) # on RPi4 (2592, 1944)
# Now when it's time to start recording the output, including the previous 5 seconds:
output.fileoutput = "file.h264"
output.start()
for num in range(3):
    # img = picam2.capture_buffer("lores")
    # img.fileoutput = f"{num}.jpg"
    # img = picam2.capture_request(capture_config) #capture_config no effect on img size
    # JpegEncoder does not read any YUV, and lores can be only that. Funny: H264Encoder and MJPEGEncoder can read YUV420
    # for YUV to RGB you need module cv2 -> https://github.com/raspberrypi/picamera2/blob/main/examples/yuv_to_rgb.py
    # https://www.geeksforgeeks.org/python-pillow-tutorial/
    req = picam2.capture_request()
    img = req.make_image("main")
    img = img.resize(losize)
    img.save(f"{num}.jpg", quality=70) # quality default 95
    # req.save("main", f"{num}.jpg")
    req.release()
    time.sleep(3)
# And later it can be stopped with:
output.stop() # ends video recording

# unloads picam2, see picam2 manual 7.0
picam2.stop_recording() # includes picam2.stop() and picam2.stop_encoder()