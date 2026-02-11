#!/bin/bash
# this script 'log_vidmsg.sh' is like 'update_vidmsg.sh', but changes 2 fields of msgfile=vidmsg.json: linecnt, linetxt (compare log() in msgBird.py)
# caller.sh puts an flock on this script using a line like: flock "$msgfile" "$APPDIR/log_vidmsg.sh" "$msgfile"
# helper script to avoid messy subshell quoting inside it
set -euo pipefail

msgfile="$1"
linetxt="$2"

# ensure file exists
if [[ ! -f "$msgfile" ]] || ! jq empty "$msgfile" &>/dev/null; then
    exit 1
fi

if [[ -z "$linetxt" ]]; then exit 1; fi

# read current JSON
json_data=$(cat "$msgfile")
cnt=$(jq -r '.linecnt // 0' <<< "$json_data")
cnt=$((cnt + 1))
new_json=$(jq --argjson cnt "$cnt" --arg txt "$linetxt" '.linecnt = $cnt | .linetxt = $txt' <<< "$json_data")

# write updated JSON atomically
printf '%s\n' "$new_json" > "$msgfile" # on structured data (json, csv,...) printf more reliable than echo with \n across different echo versions