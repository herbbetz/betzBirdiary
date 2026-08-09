#!/bin/bash
# For bird stations running without nightly shutdown, called from premidnight.service

APPDIR="/home/pi/station3"
LOGFILE="$APPDIR/logs/startup.log"

log() {
    echo "$*" >> "$LOGFILE" 2>&1
}

CURRENT_HM=$(date +%H%M)

# 1. Time-window guard (exit if outside 23:53 - 23:58)
if ! [[ "$CURRENT_HM" -ge 2353 && "$CURRENT_HM" -le 2358 ]]; then
    msg="${CURRENT_HM}_outside_reboot_window"
    log "$msg"
    exit 0
fi

# 2. Check for active SSH/SFTP/SCP (port 22) or WayVNC_0 (port 5900) sessions
if ss -H -tn state established '( sport = :22 or dport = :22 or sport = :5900 )' | grep -q .; then
    msg="${msg}_skipping_ssh"
    log "$msg"
    echo "$msg"
    exit 0
fi

# 3. Write lastdown.json for config3.html
formatted_date=$(date "+%y-%m-%d %H:%M")
msg="plannedReboot"
jq -n \
  --arg msg "$msg" \
  --arg date "$formatted_date" \
  '{msg: $msg, date: $date}' > "$APPDIR/lastdown.json"

log "$(date): Initiating planned reboot."

sudo sync
sudo reboot