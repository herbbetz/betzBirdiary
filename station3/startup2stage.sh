#!/bin/bash
# called from startup1stage.sh, which is called from systemd bird-startup.service .
# nohup /setsid prevents kill of backgrounded processes when this script ends,
#   but beware: without terminal '&' backgrounding these are blocking the following processes to execute!!!
# log to /dev/null for sparing the sd-card
APPDIR="/home/pi/station3"
PYTHON="/usr/bin/python3"
LOGFILE="$APPDIR/ramdisk/startup.log" # "/dev/null"
log() {
    echo "$*" >> "$LOGFILE" 2>&1
}

START_TIME=$(date +%s)
elapsed() {
    log "$1: $(( $(date +%s) - START_TIME )) seconds since startup"
}

log "startup2stage.sh started at $(date)"
# All python scripts in subdirs of $APPDIR need this env var to find modules in $APPDIR, e.g. 'import msgBird as ms' in '$APPDIR/model/birdclassify.py':
log "PYTHONPATH=$PYTHONPATH"
if [ -z "${PYTHONPATH:-}" ] || [ ! -d "$PYTHONPATH" ]; then
    log "PYTHONPATH missing or invalid — exiting"
    exit 1
fi
cd "$APPDIR" || { log "$APPDIR missing"; exit 1; } # {space ... ;space}

# from now on start programs
setsid bash "$APPDIR/mdroid.sh" stationLoaded & # mdroid.sh writes to startup.log
#
# sudo systemctl list-unit-files | grep avahi
# &> redirects stderr and stdout to file, &>> appends redirected to file, final & means background (works only for bash, but crontab is sh)
# better like in crontab: bash /home/pi/station2/statist/getStats.sh >> /home/pi/station2/logs/statist.log 2>&1 & (works for all posix shells like sh)
#
# flaskBird first, central to communication (WebGUI)
# flaskBird thread can write to FIFO too, but only when asked to:
setsid $PYTHON "$APPDIR/flaskBird3.py" > /dev/null 2>&1 & # >> "$APPDIR/logs/flask.log" 2>&1 &
sleep 1
elapsed "flaskBird3.py +sleep 1"
# after flaskBird, needs time to find cmd 'ifconfig':
# mainFoBird.py contains the only FIFO reader in child process:
# python3 mainAckBird2.py &>> logs/main.log & # watch logs live on flask webserver or in terminal, using 'tail -f ~station/logs/main.log' or 'less +F ~station/logs/main.log'
setsid $PYTHON "$APPDIR/mainFoBird3.py" > /dev/null 2>&1 & # >> "$APPDIR/logs/main.log" 2>&1 & # birdpipe reader
# setsid $PYTHON "$APPDIR/mainFoBird3.py" test > /dev/null 2>&1 &
sleep 1 # the child process takes time to establish
elapsed "mainFoBird3.py +sleep 1"
# looping shutdown scripts, when system more stable:
# these now have their own systemd timer:
# setsid bash "$APPDIR/sysmon2.sh" > /dev/null 2>&1 & # >> "$APPDIR/logs/sysmon.log" 2>&1 # once at boot in foreground, then every 15 min via pi's crontab -l
# sleep 2
# setsid $PYTHON "$APPDIR/dhtBird3.py" > /dev/null 2>&1 & # >> "$APPDIR/logs/dht_sun.log" 2>&1 &
#
# hxFiBirdStateCt.py is the first FIFO writer, seems the most critical to init, it is started in hxFiBird.service -> hxFiBird.sh

exit # status reflects last cmds success