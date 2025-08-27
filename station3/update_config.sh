#!/bin/bash
# helper for scripts to put an flock for the writing of the json
# helper script for config-yaml.sh to avoid messy subshell quoting inside it
set -euo pipefail

msgfile="$1"

# ensure file exists
if [[ ! -f "$msgfile" ]] || ! jq empty "$msgfile" &>/dev/null; then
    exit 1
fi

# read current JSON
json_data=$(cat "$msgfile")
# write updated JSON atomically
printf '%s\n' "$json_data" > "$msgfile" # on structured data (json, csv,...) printf more reliable than echo with \n across different echo versions