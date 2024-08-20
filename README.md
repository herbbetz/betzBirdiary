![](station2/favicon.svg)
The [birdiary project](https://www.wiediversistmeingarten.org) provides a [manual](https://docs.google.com/document/d/1ItowLull5JF3irzGtbR-fCmgelG3B7DSaU1prOeQXA4/edit#heading=h.d6tejpvjrrs8) and [software](https://github.com/Birdiary) to upload videos of birds feeding in your garden to their internet platform. The videos are taken with a raspicam and triggered by a balance on which the feeding bird sits. My code was derived from the project's [120423.img](https://uni-muenster.sciebo.de/s/ZZWtPM9miId9ctM) and the [pigpio library](https://abyz.me.uk/rpi/pigpio/) among others.

My own image for flashing to the SD card is configured with the password: 'pi / bird24' ('bird24root' for su). You can find the installation instructions [here](image/imgInstall.md).
Use your own API keys from birdiary in 'station2/configBird.py' (configBird2.py for 'picamera2').
Also use your own API keys or credentials in any scripts that communicate with the outside world, such as Macrodroid (mdroid.sh).
Once this is done, reboot and point any browser to 'http:// your-stations-ip4 :8080'. Thanks to the 'avahi' (bonjour) mDNS service, you can also use http://rpibird:8080 .

Decide for your version of the picamera software, i.e. for the python module 'picamera' choose legacy picamera in raspi-config and gpu_mem=256 in /boot/config.txt, but for 'picamera2' disable them both.
'picamera2' is more advanced and preinstalled with bullseye, but can only flip it's view. If you have built in your raspicam sideways, you may prefer the legacy 'picamera', which can rotate the view. 'picamera2' also gives me difficulties with the CircularOutput(), i.e. the permanent video buffer of a few seconds prepended to the bird's landing.

After a reboot you can try it:

- for 'picamera' my scripts mainFoBird.py (direct video upload on balance trigger) or mainAckBird.py (upload after acknowledgement)
- for 'picamera2' mainFoBird2.py (direct upload) or mainAckBird2.py (upload after confirmation). Here you can toggle between those 2 scripts in the config webpage.
- with the mainAckBirdX versions you do not need the old debug mode, as the bird's video is not uploaded to birdiary, before you viewed it in the browser.

Have a look at 'startup.sh' to find out my choices. Watch the code working as a beta on my [station](https://www.wiediversistmeingarten.org/view/station/87bab185-7630-461c-85e6-c04cf5bab180) and learn [more](docs/ForkMakingof.md) about my making. There are also some [pictures](./fotos/fotos.md) as well as a [troubleshooting](debug/troubleshoot.md) guide in case of issues with my software.

If you need to calibrate your scale, run 'python3 calibrateHx711.py' (which kills hxFiBird.py, watch 'ps aux|grep pi') and put your scales values into configBirdX.py . Then 'sudo reboot'.

Using the python3 modules 'picamera2' and 'pigpio' (for DHT20 and HX711) the code should work on RaspberryZero2W as well as Raspberry4 and with Raspbian Bullseye (Debian 11) and Bookworm (Debian 12).

I did not install any code for the microfone. Adafruit I2S MEMS Mikrofon SPH0645LM4H may not yet be working with Bookworm anyway. Bird song monitoring can be an RPi project of its own, using an USB soundcard mic, sonograms and a sound world map like in [BirdNET-PI](https://github.com/mcguirepr89/BirdNET-Pi).

Models for the manufacturing of the birdhouse as described in the above project manual can be viewed in /birdhouse or on my [website](https://herbertbetz.de/birdiaryhouse). Github will display the .stl model on its own.

A video of my browser view is available at [here](https://dateicloud.de/index.php/s/Hf4oQaenDDJwWtD).
