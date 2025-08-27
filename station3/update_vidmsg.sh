#!/bin/bash
# sysmon2.sh puts an flock on this script
# helper script for sysmon2.sh to avoid messy subshell quoting inside it
set -euo pipefail

msgfile="$1"

# ensure file exists
if [[ ! -f "$msgfile" ]] || ! jq empty "$msgfile" &>/dev/null; then
    exit 1
fi

# read current JSON
json_data=$(cat "$msgfile")
cnt=$(jq -r '.sysmonEvt // 0' <<< "$json_data")
cnt=$((cnt + 1))
new_json=$(jq --argjson cnt "$cnt" '.sysmonEvt = $cnt' <<< "$json_data")

# write updated JSON atomically
printf '%s\n' "$new_json" > "$msgfile" # on structured data (json, csv,...) printf more reliable than echo with \n across different echo versions