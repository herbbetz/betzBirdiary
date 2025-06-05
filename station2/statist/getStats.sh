#!/bin/bash
# script executed from crontab
# set -e  # Exit immediately if a command exits with a non-zero status
# exec >> /home/pi/station2/logs/statist.log 2>&1 # Redirect stdout and stderr to a log file
DIR="/home/pi/station2/statist"
cd "$DIR"

# 1) download from birdiary api's to apidata.json
python3 "$DIR/dloadStats.py"

# 2) only if download successful, then create new statistical SVGs from apidata.json
if [ $? -eq 0 ]; then
    python3 "$DIR/hours_histo.py"
    python3 "$DIR/month_histo.py"
    python3 "$DIR/countsbytemp.py"
    python3 "$DIR/countsbyhumid.py"
    echo "API data downloaded and SVGs generated at $(date +'%Y-%m-%d %H:%M:%S')"
else
    echo "Data download failed. SVG generation aborted."
    exit 1
fi