#!/bin/bash
# shut down on cpu too hot
APPDIR="$HOME/station3"
config_file="$APPDIR/config.json"

temp_limit=$(jq -r '.heatdown' "$config_file")
# Extract ONLY the whole number (e.g., 53.2'C becomes 53)
curr_temp=$(vcgencmd measure_temp | grep -oE '[0-9]+' | head -n 1)

if [[ "$curr_temp" -gt "$temp_limit" ]]
then
    echo "$(date) shutdown due to CPU $curr_temp > $temp_limit °C" | mail -s "CPU too hot" pi@localhost
    "$APPDIR/tasmotaDown.sh" heatdown
fi