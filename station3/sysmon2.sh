#!/bin/bash
set -euo pipefail

APPDIR="$HOME/station3"
RAMDISK="$APPDIR/ramdisk"

# --- functions ---
secs2hours() {
    local total_secs="$1"
    local mins=$(( total_secs / 60 ))
    local hrs=$(( mins / 60 ))
    mins=$(( mins - (hrs * 60) ))
    echo "${hrs}:${mins}"
}

# --- collect values ---
declare -A monitor

monitor["date"]="$(date)"

# uptime
uptime_secs=$(cut -d " " -f1 /proc/uptime | cut -d"." -f1)
monitor["uptime"]="$(secs2hours "$uptime_secs")hrs ($uptime_secs secs)"

# wlan0 IP
IP4=$(ip -4 addr show wlan0 2>/dev/null | grep -oP '(?<=inet\s)\d+(\.\d+){3}' || echo "N/A")
HOSTNAME=$(hostname)
monitor["wlan0"]="$IP4 $HOSTNAME"

# --- WLAN Stats (Fixed Logic) ---
# We use || true so the script doesn't crash if wlan0 is missing from the file
WLAN_RAW=$(grep "wlan0" /proc/net/wireless || true)

if [ -n "$WLAN_RAW" ]; then
    # Extract quality and dBm, removing trailing dots
    QUAL=$(echo "$WLAN_RAW" | awk '{print $3}' | tr -d '.')
    DBM=$(echo "$WLAN_RAW" | awk '{print $4}' | tr -d '.')
    monitor["WLANquality"]="${QUAL} (${DBM}dBm)"
else
    monitor["WLANquality"]="Disconnected"
fi

# CPU Temp
if command -v vcgencmd &>/dev/null; then
    # monitor["cpuvolt"]="$(vcgencmd measure_volts core | cut -d "=" -f 2)"
    monitor["cputemp"]="$(vcgencmd measure_temp | cut -d "=" -f 2 | sed "s/'//g")"
else
    monitor["cputemp"]="N/A"
fi

# CPU load
CPULOAD=$(bash "$APPDIR/cpu5sec.sh" || echo "N/A")
monitor["cpuload"]="${CPULOAD}%"

# --- build JSON safely with jq ---
outfile="$RAMDISK/sysmon.json"

jq -n \
  --arg date         "${monitor[date]}" \
  --arg uptime       "${monitor[uptime]}" \
  --arg wlan0        "${monitor[wlan0]}" \
  --arg WLANquality  "${monitor[WLANquality]}" \
  --arg cputemp      "${monitor[cputemp]}" \
  --arg cpuload      "${monitor[cpuload]}" \
  '{
      date: $date,
      uptime: $uptime,
      wlan0: $wlan0,
      WLANquality: $WLANquality,
      cputemp: $cputemp,
      cpuload: $cpuload
    }' > "$outfile"

# --- update sysmonEvt counter in vidmsg.json with advisory lock ---
msgfile="$RAMDISK/vidmsg.json"

# flock the file and run the helper script
flock "$msgfile" "$APPDIR/update_vidmsg.sh" "$msgfile" # lock file as long as child script runs in subshell
# do not put the code of ./update_vidmsg.sh in here. This would lead to messy subshell quoting issues.
