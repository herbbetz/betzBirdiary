# model appied in station2/mainAckBird2.py
# repeatedly saving picam2 video to file
import libcamera
from picamera2.encoders import H264Encoder, Quality
from picamera2.outputs import CircularOutput
from picamera2 import Picamera2
#
import time
from configBird2 import * # import all variables from ./configBird2.py

def record_video(vidNum):
    video_filename = f'{vidNum}.h264'
    circOut.fileoutput = video_filename
    circOut.start()
    time.sleep(2)
    # the following seems to also flush the output buffer and reset it to the beginning
    # do not touch the output buffer using .seek(0) and .truncate(), as this must be done thread safe for not interfering with picam!?
    circOut.stop()


picam2 = Picamera2()
video_config = picam2.create_video_configuration(main={"size": vidsize, "format": "RGB888"}, lores={
                                                "size": losize, "format": "YUV420"})
video_config["transform"] = libcamera.Transform(hflip=hflip_val, vflip=vflip_val)
picam2.configure(video_config)

# encoder = H264Encoder()
# circOut = CircularOutput() # will not produce preload videos
# will produce 8 secs videos, increasing with each file:
encoder = H264Encoder(1000000, repeat=True) # 1 MBitPerSecond = 125 kByte/sec
circOut = CircularOutput(buffersize = 300, outputtofile=False) # 300 frames


picam2.start_recording(encoder, circOut, quality=Quality.MEDIUM) # medium is default

video_number = 1
sleeptime = 3
while True:
    try:
        # Wait for 8 seconds, till circOut refilled (what happens if less?)
        time.sleep(sleeptime) # this very much influences video length!?
        sleeptime += 1
        # Record a video
        record_video(video_number)
        print(f"Video {video_number} recorded.")
        # Increment video number
        video_number += 1
    except KeyboardInterrupt:
        break
picam2.stop_recording()
print("Recording stopped.")