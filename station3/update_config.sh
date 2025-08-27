#!/bin/bash
# helper for scripts to put an flock for the writing of the json
# helper script for config-yaml.sh to avoid messy subshell quoting inside it
set -euo pipefail
JSON_FILE="config.json"
msgfile="$1"

# ensure file exists
if [[ ! -f "$msgfile" ]] || ! jq empty "$msgfile" &>/dev/null; then
    exit 1
fi

# ensure staged file is in the same directory as JSON_FILE (needed for atomic mv)
# json_dir="$(dirname "$JSON_FILE")"
# msg_dir="$(dirname "$msgfile")"
# if [[ "$json_dir" != "$msg_dir" ]]; then
#    echo "Error: staged file is not in the same directory as $JSON_FILE (atomic mv not guaranteed)"
#    exit 1
# fi

# atomic promotion of staged file -> config.json
mv "$msgfile" "$JSON_FILE"
