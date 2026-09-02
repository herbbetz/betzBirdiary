#!/bin/bash
# these scripts start after all other systemd services have started, but before the user logs in (ssh or GUI)
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

log "$0 started at $(date)"
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
    setsid bash internetTest2.sh > /dev/null 2>&1 & # >> "$APPDIR/logs/internet.log" 2>&1 & # not in hotspot without internet! will drop ssh connection after 3 min
fi
elapsed "DNS check/internetTest2.sh"

# widgets for wayfire desktop will not work here, because wayfire or vnc/X11 env not yet ready! Moreover no use running it, when no desktop shown.
# setsid $PYTHON widgets.py &
STATDIR="$APPDIR/statist"
cd "$STATDIR" || { log "$STATDIR missing"; exit 1; } # avoids output into wrong path
bash "$STATDIR/getStats.sh" > /dev/null 2>&1 # >> "$APPDIR/logs/statist.log" 2>&1 # only once at boot, fst contact with birdiary platform
sleep 1
elapsed "getStats.sh +sleep 1"
STATIONSDIR="$APPDIR/stations"
cd "$STATIONSDIR" || { log "$STATIONSDIR missing"; exit 1; } # avoids output into wrong path
$PYTHON "$STATIONSDIR/stations.py" > /dev/null 2>&1
sleep 1
elapsed "stations.py +sleep 1"
$PYTHON "$STATIONSDIR/vk_lastmonth_pag.py" > /dev/null 2>&1
cd "$APPDIR"
elapsed "vk_lastmonth_pag.py -> last task, all done"
log "$0 ended at $(date)"
exit # status reflects last cmds success