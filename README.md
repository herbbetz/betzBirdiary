# betzBirdiary
Code Fork of Birdiary project (https://www.wiediversistmeingarten.org)

The birdiary project 'https://www.wiediversistmeingarten.org/de/' provides a manual and software to upload videos of birds feeding in your garden to their internet platform. The videos are taken by a raspicam and triggered by a balance, that the feeding bird sits on. My code was derived from the project's 120423.img and https://abyz.me.uk/rpi/pigpio/ among others.

My own image for flashing to SD Card is configured to the password: pi/bird24 (bird24root for su).
Please adapt '/etc/wpa_supplicant/wpa_supplicant.conf' and '/etc/dhcpcd.conf' to your needs and use your own API keys for birdiary in 'station2/configBird.py' (configBird2.py).
Also use your own API keys or credentials in any communication scripts to the outside, like Macrodroid (mdroid.sh).
When this is done, reboot and point any browser to http://your-stations-ip4:8080 .

I recommend testing out my different versions of mainXXBird.py. For this first point the link station2/startup.sh to startupTest.sh, using 'rm startup.sh' and 'ln -s startupTest.sh startup.sh'.
Then reboot and kill the hxFiBird.py process, using 'kill PID' after you found its PID by 'ps aux|grep pi'.
Only when hxFiBird is not active, can you calibrate your scale with 'station2/calibrateHx711.py' and write hxScale to 'configBird.py' (and 'configBird2.py', if using picamera2).

Decide for your version of picamera software, i.e. for python module 'picamera' choose legacy picamera in raspi-config and gpu_mem=256 in /boot/config.txt, but for 'picamera2' disable them both.
Picamera2 is more advanced and preinstalled with bullseye, but can only flip it's view. If you have built in your raspicam sideways, you may prefer the legacy 'picamera', which can rotate it's view.

Then after rebooting you can try out:

- for 'picamera' my scripts mainFoBird.py (direct video upload on balance trigger) or mainAckBird.py (upload only after confirmation within browser)
- for 'picamera2' my script mainBird2.py (direct upload) or mainAckBird2.py (upload after confirmation)

After you found your favorite setup, you can save it to startupNoTest.sh and link startup.sh to it.

My station can be watched here: https://www.wiediversistmeingarten.org/view/station/87bab185-7630-461c-85e6-c04cf5bab180
