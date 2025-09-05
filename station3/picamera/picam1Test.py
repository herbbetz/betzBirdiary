# extrakt aus birdiary's main.py
from datetime import datetime
import picamera

camera = picamera.PiCamera()
camera.rotation = 270 # from config.yaml
camera.resolution = (1280, 960)
stream = picamera.PiCameraCircularIO(camera, seconds=5)
camera.start_recording(stream, format='h264')

secs = 5
movementStartDate = datetime.now()
video_filename = str(movementStartDate) + '.h264'
capture_filename = str(movementStartDate) + '.jpg'

print("record video for seconds: ", secs)

while (int((datetime.now() - movementStartDate).total_seconds()) < secs):
    camera.wait_recording(1) # continue camera recording 

camera.capture(capture_filename, resize=(320,240), use_video_port=True)

stream.copy_to(video_filename, seconds=secs+5)
stream.clear()
print("recorded to: " + video_filename + " and " + capture_filename)
camera.stop_recording()
camera.close()