#!/bin/bash
# For bird stations running without nightly shutdown, called from premidnight.service

APPDIR="$HOME/station3"
LOGFILE="$APPDIR/logs/startup.log"

log() {
    echo "$*" >> "$LOGFILE" 2>&1
}

# Check for active SSH/SFTP/SCP (port 22) or WayVNC_0 (port 5900) sessions
if ss -H -tn state established '( sport = :22 or dport = :22 or sport = :5900 )' | grep -q .; then
    msg="$(date): Active connection (SSH/VNC) detected, skipping reboot."
    log "$msg"
    echo "$msg"
    exit 0
fi

# Write lastdown.json for config3.html
formatted_date=$(date "+%y-%m-%d %H:%M")
msg="plannedReboot"
jq -n \
  --arg msg "$msg" \
  --arg date "$formatted_date" \
  '{msg: $msg, date: $date}' > "$APPDIR/lastdown.json"

sudo sync
sudo reboot