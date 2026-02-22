#!/bin/bash
# called from startup1stage.sh, which is called from systemd bird-startup.service .
# nohup /setsid prevents kill of backgrounded processes when this script ends
# log to /dev/null for sparing the sd-card
APPDIR="$HOME/station3"
PYTHON="/usr/bin/python3"
LOGFILE="/dev/null" # "/home/pi/station3/logs/startup.log"
log() {
    echo "$*" >> "$LOGFILE" 2>&1
}

log "startup2stage.sh started at $(date)"
# All python scripts in subdirs of $APPDIR need this env var to find modules in $APPDIR, e.g. 'import msgBird as ms' in '$APPDIR/model/birdclassify.py':
log "PYTHONPATH=$PYTHONPATH"
if [ -z "${PYTHONPATH:-}" ] || [ ! -d "$PYTHONPATH" ]; then
    log "PYTHONPATH missing or invalid — exiting"
    exit 1
fi
# waits for internet, even /etc/systemd/system/bird-startup.service does not guarantee for this, despite 'After=network-online.target, Wants=network-online.target'
# Wait for DNS to resolve webhook target
dnshost=trigger.macrodroid.com # or cloudfare.com (1.1.1.1)
dns_ok=false
for i in {1..30}; do
    if getent hosts $dnshost >/dev/null; then # getent from 'apt install dnsutils'
        log "DNS is up ($dnshost, $i tries)"
        dns_ok=true
        break
    fi
    log "Waiting for DNS ($i)"
    sleep 2
done
if [ "$dns_ok" = false ]; then
    log "DNS lookup failed after 30 tries — hope continuing as hotspot" # hotspot activated by NetworkManagers system-connection priority
else
    setsid bash internetTest2.sh > /dev/null 2>&1 & # >> logs/internet.log 2>&1 & # not in hotspot without internet! will drop ssh connection after 3 min
fi
# from now on start programs
setsid bash "$APPDIR/mdroid.sh" stationLoaded & # mdroid.sh writes to startup.log
#
# sudo systemctl list-unit-files | grep avahi
# &> redirects stderr and stdout to file, &>> appends redirected to file, final & means background (works only for bash, but crontab is sh)
# example: python3 flaskBird.py &>> logs/flask.log & 
# better like in crontab: bash /home/pi/station2/statist/getStats.sh >> /home/pi/station2/logs/statist.log 2>&1 & (works for all posix shells like sh)
#
# flaskBird first, central to communication (WebGUI)
# flaskBird thread can write to FIFO too, but only when asked to:
setsid $PYTHON flaskBird3.py > /dev/null 2>&1 & # >> logs/flask.log 2>&1 &
sleep 4
# after flaskBird, needs time to find cmd 'ifconfig':
# mainFoBird.py contains the only FIFO reader in child process:
# python3 mainAckBird2.py &>> logs/main.log & # watch logs live on flask webserver or in terminal, using 'tail -f ~station/logs/main.log' or 'less +F ~station/logs/main.log'
setsid $PYTHON mainFoBird3.py > /dev/null 2>&1 & # >> logs/main.log 2>&1 &
sleep 8 # the child process takes time to establish
# looping shutdown scripts, when system more stable:
setsid bash sysmon2.sh > /dev/null 2>&1 & # >> logs/sysmon.log 2>&1 # once at boot in foreground, then every 15 min via pi's crontab -l
sleep 2
# upload environment at start
setsid $PYTHON dhtBird3.py > /dev/null 2>&1 & # >> logs/dht_sun.log 2>&1 &
#
# first FIFO writer, seems the most critical to init
# run in foreground inside a bash while loop, being restarted after each selfprogrammed end of process
# while true; do
#    bash hxFiBirdStart.sh
#    sleep 2
# done
setsid $PYTHON hxFiBirdState.py > /dev/null 2>&1 & # >> logs/hxFiBird.log 2>&1 & # first FIFO writer, seems the most critical to init
# widgets for wayfire desktop will not work here, because wayfire or vnc/X11 env not yet ready! Moreover no use running it, when no desktop shown.
# setsid $PYTHON widgets.py &
echo "startup2stage.sh ended at $(date)" > /dev/null 2>&1 # >> /home/pi/station3/logs/startup.log 2>&1
exit # status reflects last cmds success
