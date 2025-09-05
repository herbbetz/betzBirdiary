<!--keywords[picamera2]-->

Picamera2 erforschen:

- in bookworm venv neuere Version 0.3.28 in 'apt install python3-picamera2' (Systemdateien nach 'birdvenv' durchgeleitet). Dann 'pip uninstall picamera2', da sonst dessen Version 0.3.27 bevorzugt wird. 

- Die neueste Version erhielte man aber durch Übersetzen der Source von 'https://github.com/raspberrypi/picamera2'. Dort wird ebenfalls 'apt' vor 'pip' bevorzugt, weil dann picamera2 auf das zugrunde liegende libcamera abgestimmt ist.

~~~
sudo apt remove python3-picamera2

# Install deps
sudo apt install -y python3-pip python3-pyqt5 libcamera-apps

# Clone the repo
git clone https://github.com/raspberrypi/picamera2.git
cd picamera2

# Optional: Check latest tag
git tag -l

# Install it into your venv or system-wide
pip install .
~~~

- `python -c "from picamera2 import Picamera2; print(Picamera2.__version__)"`oder `dpkg -s python3-picamera2 | grep Version`

- Welche Funktionen diese Version hat, testet man z.B. mit python s REPL:

~~~
from picamera2 import Picamera2
print(dir(Picamera2))  # Lists all class attributes and methods

picam = Picamera2() # () important, makes this an instance
print(dir(picam))  # Lists all instance attributes and methods
~~~

- oder gleich durch ein Testscript 'check_picamera_features.py':
~~~
from picamera2 import Picamera2

picam = Picamera2()

features = [
    "start_recording",
    "stop_recording",
    "capture_array",
    "capture_metadata",
    "configure",
]

for feat in features:
    print(f"{feat}: {hasattr(picam, feat)}")
~~~
- Beachte das [Manual](https://datasheets.raspberrypi.com/camera/picamera2-manual.pdf) von picamera2 und noch ausführlicher andere Datasheets auf datasheets.raspberrypi.com wie den [camera tuning guide](https://datasheets.raspberrypi.com/camera/raspberry-pi-camera-guide.pdf).
- Die Belichtung (exposure, gain) der PiCamera2 wird besser sich selbst überlassen, wie diskutiert mit Entwickler [davidplowman](https://github.com/raspberrypi/picamera2/issues/1305).
- Verwende `picam.stop_encoder()` zum Beenden der Videoaufzeichnung ! `picam.stop_recording()` contains a `picam.stop()` and therefore will hang following `picam.capture_file()` or `picam.capture_metadata()`.