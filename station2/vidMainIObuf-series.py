# model appied in station2/mainAckBird2.py
# repeatedly saving picam2 video first to ioBuf to investigate
# why does video get longer with each repetition? I could place a digital watch in front of the camera to find out about uncleared frames...
import libcamera
from picamera2.encoders import H264Encoder, Quality
from picamera2.outputs import CircularOutput
from picamera2 import Picamera2
#
import io
import time
from configBird2 import * # import all variables from ./configBird2.py

def record_video(vidNum):
    global circOut
    # video_filename = f'{vidNum}.h264'
    vidData = io.BytesIO() # binary video container for upload (stream cannot be uploaded directly)
    circOut.fileoutput = vidData
    circOut.start()
    time.sleep(2)
    # the following seems to also flush the output buffer and reset it to the beginning
    # do not touch the output buffer using .seek(0) and .truncate(), as this must be done thread safe for not interfering with picam!?
    circOut.stop()
    n = vidData.getbuffer().nbytes # gives the number of bytes in the buffer
    print("bytes before bufferread: " + str(n))
    vidData.seek(0)
    sendfile = vidData.read() # read memory buffer
    vidData.seek(0)
    vidData.truncate() # even with .truncate() video gets longer with each recording, albeit slowlier than without .truncate()
    n = vidData.getbuffer().nbytes
    print("bytes after: " + str(n))
    vidData.close()
    # no stream.clear() for CircularOutput() like in old picamera -> chatGPT (June 24) says, recreate instead buffer with same size using 'circOut = CircularOutput(buffer_size)'
    # circOut = CircularOutput() # but this produces 0 byte videos after the first
    with open(f'{vidNum}.h264', 'wb') as vfile:
        vfile.write(sendfile)



picam2 = Picamera2()
video_config = picam2.create_video_configuration(main={"size": vidsize, "format": "RGB888"}, lores={
                                                "size": losize, "format": "YUV420"})
video_config["transform"] = libcamera.Transform(hflip=hflip_val, vflip=vflip_val)
picam2.configure(video_config)
encoder = H264Encoder()
circOut = CircularOutput()
picam2.start_recording(encoder, circOut, quality=Quality.MEDIUM) # medium is default

video_number = 1
while True:
    try:
        # Wait for 8 seconds, till circOut refilled (what happens if less?)
        time.sleep(8)
        # Record a video
        record_video(video_number)
        print(f"Video {video_number} recorded.")
        # Increment video number
        video_number += 1
    except KeyboardInterrupt:
        break

print("Recording stopped.")