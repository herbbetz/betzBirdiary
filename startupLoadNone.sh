#!/bin/bash
# softlink this to startup.sh for testing and load all scripts manually:
cd /home/pi/station2
# starting with & -> don't wait for programm exit, but run parallel (in background)
# some unknown problem makes start with 'systemctl enable pigpiod' fail: pigpiod bind to port 8888 failed -> how get it more stable?
sudo pigpiod
# FIFO programming in bash simpler than in python -> https://www.linuxjournal.com/content/using-named-pipes-fifos-bash
fifo="ramdisk/birdpipe"
if [[ ! -p $fifo ]]; then
    mkfifo $fifo
    # echo "created: "$fifo
fi
# sleep 1
# upload environment at start
# &> redirects stderr and stdout to file, &>> appends redirected to file, final & means background
# python3 dhtBird.py &>> logs/envDHT.log # foreground script (no longterm loop)
# sleep 2
# mainFoBird.py contains the only FIFO reader in child process:
# python3 mainAckBird2.py &>> logs/main.log & # <-- picamera2, could be used instead after disabling legacy cam in raspi-config and gpu_mem in /boot/config.txt
# alternative for picamera2: mainBird2.py, for picamera: mainFoBird.py, mainAckBird.py
# sleep 8 # the child process takes time to establish
# bash sysMon.sh &>> logs/sysmon.log # once at boot in foreground, then every 15 min via pi's crontab -l
# flaskBird thread can write to FIFO too:
# python3 flaskBird.py &>> logs/flask.log & 
# sleep 4
# looping shutdown scripts, when system more stable:
# bash internetTest2.sh &>> logs/internet.log &
# bash birdActivTest.sh &>> logs/actity.log &
#
# bash hxFiBirdStart.sh
exit # status reflects last cmds success