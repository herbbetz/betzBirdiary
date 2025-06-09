#!/bin/bash
# softlink this to startup.sh for testing: hxFiBird is not restarted. Start any of the mainXXBird.py manually in terminal.
# despite found in 'which bash' the shebang !/usr/bin/bash is not working in bullseye
# called from pi crontab @reboot as pi (not from /etc/rc.local as root, see rclocal.sh)
# echo "Welcome to Birdiary!" # this provokes crontab to send a mail
cd /home/pi/station2
# 3.16 von https://picamera.readthedocs.io/en/release-1.13/recipes1.html : RPi.GPIO best with root privileges, therefore sudo respectively pigpiod
# starting with & -> don't wait for programm exit, but run parallel (in background)
# some unknown problem makes start with 'systemctl enable pigpiod' fail: pigpiod bind to port 8888 failed -> how get it more stable?
sudo pigpiod
# FIFO programming in bash simpler than in python -> https://www.linuxjournal.com/content/using-named-pipes-fifos-bash
fifo="ramdisk/birdpipe"
if [[ ! -p $fifo ]]; then
    mkfifo $fifo
    # echo "created: "$fifo
fi
sleep 2
# upload environment at start
# &> redirects stderr and stdout to file, &>> appends redirected to file, final & means background
python3 dhtBird.py &>> logs/envDHT.log # foreground script (no longterm loop)
sleep 2
# mainFoBird.py contains the only FIFO reader in child process:
# python3 mainAckBird.py &>> logs/main.log & # watch logs live on flask webserver or in terminal, using 'tail -f ~station/logs/main.log' or 'less +F ~station/logs/main.log'
# python3 mainFoBird.py &>> logs/main.log & # could be used instead for direct video upload without confirmation
# python3 mainAckBird2.py &>> logs/main.log & # <-- picamera2, could be used instead after disabling legacy cam in raspi-config and gpu_mem in /boot/config.txt
python3 mainFoBird2.py &>> logs/main.log &
#
sleep 8 # the child process takes time to establish
bash sysMon.sh &>> logs/sysmon.log # once at boot in foreground, then every 15 min via pi's crontab -l
# flaskBird thread can write to FIFO too:
python3 flaskBird.py &>> logs/flask.log & 
sleep 4
# after flaskBird, needs time to find cmd 'ifconfig':
bash sysMon.sh &>> logs/sysmon.log # once at boot in foreground, then every 15 min via pi's crontab -l
# looping shutdown scripts, when system more stable:
bash internetTest2.sh &>> logs/internet.log &
# bash birdActivTest.sh &>> logs/actity.log &
#
bash hxFiBirdStart.sh
bash mdroid.sh stationLoaded
exit # status reflects last cmds success