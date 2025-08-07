#!/bin/bash
# despite found in 'which bash' the shebang !/usr/bin/bash is not working in bullseye
# called from startup1stage.sh, which is called from systemd bird-startup.service .
# nohup /setsid prevents kill of backgrounded processes when this script ends
echo "startup2stage.sh started at $(date)" >> /home/pi/station3/logs/startup.log 2>&1
configfile="$HOME/station3/config.sh"
if [ -f "$configfile" ]; then
    echo "$configfile found"
    source "$configfile"
else
    echo "not found: $configfile" >&2
    exit 1
fi 
sleep 2
# &> redirects stderr and stdout to file, &>> appends redirected to file, final & means background (works only for bash, but crontab is sh)
# example: python3 flaskBird.py &>> logs/flask.log & 
# better like in crontab: bash /home/pi/station2/statist/getStats.sh >> /home/pi/station2/logs/statist.log 2>&1 & (works for all posix shells like sh)
#
# flaskBird first, central to communication (WebGUI)
# flaskBird thread can write to FIFO too, but only when asked to:
setsid $PYTHON flaskBird3.py >> logs/flask.log 2>&1 &
sleep 4
# after flaskBird, needs time to find cmd 'ifconfig':
# mainFoBird.py contains the only FIFO reader in child process:
# python3 mainAckBird2.py &>> logs/main.log & # watch logs live on flask webserver or in terminal, using 'tail -f ~station/logs/main.log' or 'less +F ~station/logs/main.log'
setsid $PYTHON mainFoBird3.py >> logs/main.log 2>&1 & # could be used instead for direct video upload without confirmation
sleep 8 # the child process takes time to establish
# looping shutdown scripts, when system more stable:
setsid bash sysMon.sh >> logs/sysmon.log 2>&1 # once at boot in foreground, then every 15 min via pi's crontab -l
setsid bash internetTest2.sh >> logs/internet.log 2>&1 &
# bash birdActivTest.sh >> logs/actity.log 2>&1
sleep 2
# upload environment at start
setsid $PYTHON dhtBird3.py >> logs/envDHT.log 2>&1 &
#
# first FIFO writer, seems the most critical to init
# run in foreground inside a bash while loop, being restarted after each selfprogrammed end of process
# while true; do
#    bash hxFiBirdStart.sh
#    sleep 2
# done
setsid $PYTHON hxFiBird3.py >> logs/hxFiBird.log 2>&1 & # first FIFO writer, seems the most critical to init
echo "startup2stage.sh ended at $(date)" >> /home/pi/station3/logs/startup.log 2>&1
exit # status reflects last cmds success