#!/bin/bash
# softlink this to startup.sh for testing and load all scripts manually:
APPDIR=/home/pi/station3
VENVDIR=/home/pi/station3/birdvenv
FIFO=/home/pi/station3/ramdisk/birdpipe
LOGFILE="/home/pi/station3/logs/startup.log"

log() {
    echo "$*" >> "$LOGFILE" 2>&1
}

# main:
log "$0 started at $(date)"
# following guarantees, that working dir is up at boot:
if cd "$APPDIR"; then
    log "cd $APPDIR succeeded"
else
    log "exit $0: cd $APPDIR failed! Current directory: $(pwd)"
    exit 1
fi
# Python venv:
if [ -d "$VENVDIR" ]; then
    source "$VENVDIR/bin/activate"
fi

# FIFO programming in bash simpler than in python -> https://www.linuxjournal.com/content/using-named-pipes-fifos-bash
if [[ ! -p "$FIFO" ]]; then
    mkfifo "$FIFO"
    # echo "created: "$fifo
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
# CON_NAME="bird-static210"
# OLD_CON="bird-ap-dhcp"
if [ "$dns_ok" = false ]; then
    log "DNS lookup failed after 30 tries — hope continuing as hotspot" # hotspot activated by NetworkManagers system-connection priority
    # sudo nmcli connection modify "$CON_NAME" connection.autoconnect no
    # sudo nmcli connection modify "$OLD_CON" connection.autoconnect yes
    # sudo nmcli connection reload
    ## setsid or nohup ->also workes after ssh session dropped, connection up involves previous_conn down:
    # setsid bash -c "sleep 5 && sudo nmcli connection up '$OLD_CON'" > /dev/null 2>&1 &
fi
# from now on start programs
setsid bash "$APPDIR/mdroid.sh" stationLoaded & # mdroid.sh writes to curl.log
# or start stage 2 with all scripts:
setsid bash "$APPDIR/startup2stage.sh" >> "$LOGFILE" 2>&1