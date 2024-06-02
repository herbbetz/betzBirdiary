The birdiary project 'https://www.wiediversistmeingarten.org' provides a [manual](https://docs.google.com/document/d/1ItowLull5JF3irzGtbR-fCmgelG3B7DSaU1prOeQXA4/edit#heading=h.d6tejpvjrrs8) and [software](https://github.com/Birdiary) to upload videos of birds feeding in your garden to their internet platform. The videos are taken with a raspicam and triggered by a balance on which the feeding bird sits. My code was derived from the project's 120423.img and https://abyz.me.uk/rpi/pigpio/ among others.

My own image for flashing to the SD card is configured with the password: 'pi / bird24' ('bird24root' for su). You can find the installation instructions [here](image/imgInstall.md).
Use your own API keys from birdiary in 'station2/configBird.py' (configBird2.py).
Also use your own API keys or credentials in any scripts that communicate with the outside world, such as Macrodroid (mdroid.sh).
Once this is done, reboot and point any browser to http://your-stations-ip4:8080 .

I recommend testing out my different versions of mainXXBird.py. To do this, first point the link station2/startup.sh to startupTest.sh, using 'rm startup.sh' and 'ln -s startupTest.sh startup.sh'.
Then reboot and kill the hxFiBird.py process, using 'kill PID' after finding its PID using 'ps aux | grep pi'.
Only when hxFiBird.py is not active, can you calibrate your scale with 'station2/calibrateHx711.py' and write hxScale to 'configBird.py' (or 'configBird2.py' for 'picamera2').

Decide for your version of the picamera software, i.e. for the python module 'picamera' choose legacy picamera in raspi-config and gpu_mem=256 in /boot/config.txt, but for 'picamera2' disable them both.
Picamera2 is more advanced and preinstalled with bullseye, but can only flip it's view. If you have built in your raspicam sideways, you may prefer the legacy 'picamera', which can rotate the view.

After a reboot you can try it:

- for 'picamera' my scripts mainFoBird.py (direct video upload on balance trigger) or mainAckBird.py (upload only after confirmation within browser)
- for 'picamera2' mainBird2.py (direct upload) or mainAckBird2.py (upload after confirmation)

After you have found your favourite setup, you can save it to startupNoTest.sh and link startup.sh to it. Watch the code working as a beta on my [station](https://www.wiediversistmeingarten.org/view/station/87bab185-7630-461c-85e6-c04cf5bab180) and learn [more](docs/ForkMakingof.md) about my making.
