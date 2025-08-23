#!/bin/bash
set -euo pipefail
source ./config.sh

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
monitor["uptime"]="$(secs2hours "$uptime_secs")hrs"

# wlan0 IP (IPv4)
IP4=$(ip -4 addr show wlan0 2>/dev/null | grep -oP '(?<=inet\s)\d+(\.\d+){3}' || echo "N/A")
monitor["wlan0"]="$IP4"

# CPU voltage & temp (only works on Raspberry Pi)
if command -v vcgencmd &>/dev/null; then
    monitor["cpuvolt"]="$(vcgencmd measure_volts core | cut -d "=" -f 2)"
    monitor["cputemp"]="$(vcgencmd measure_temp | cut -d "=" -f 2 | sed "s/'//g")"
else
    monitor["cpuvolt"]="N/A"
    monitor["cputemp"]="N/A"
fi

# CPU load (custom 5 sec measure)
CPULOAD=$(bash "$APPDIR/cpu5sec.sh" || echo "N/A")
monitor["cpuload"]="${CPULOAD}%"

# --- build JSON safely with jq ---
outfile="$RAMDISK/sysmon.json"

jq -n \
  --arg date     "${monitor[date]}" \
  --arg uptime   "${monitor[uptime]}" \
  --arg wlan0    "${monitor[wlan0]}" \
  --arg cpuvolt  "${monitor[cpuvolt]}" \
  --arg cputemp  "${monitor[cputemp]}" \
  --arg cpuload  "${monitor[cpuload]}" \
  '{
      date: $date,
      uptime: $uptime,
      wlan0: $wlan0,
      cpuvolt: $cpuvolt,
      cputemp: $cputemp,
      cpuload: $cpuload
    }' > "$outfile"

# --- update sysmonEvt counter in vidmsg.json with advisory lock ---
msgfile="$RAMDISK/vidmsg.json"
touch "$msgfile"
flock "$msgfile" ./updateSysmonEvt.sh