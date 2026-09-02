#!/bin/bash
# set -e  # Exit immediately if a command exits with a non-zero status
# exec >> /home/pi/station2/logs/statist.log 2>&1 # Redirect stdout and stderr to a log file
DIR="/home/pi/station3/statist"
# PYTHON="/home/pi/birdvenv/bin/python3"
PYTHON="/usr/bin/python3"
LOGFILE="/home/pi/station3/ramdisk/stats.log" # "/dev/null"
log() {
    echo "$*" >> "$LOGFILE" 2>&1
}

START_TIME=$(date +%s)
elapsed() {
    log "$1: $(( $(date +%s) - START_TIME )) seconds since startup"
}

cd "$DIR"

# 1) download from birdiary api's to apidata.json
$PYTHON "$DIR/dloadStats.py"
elapsed "dloadStats.py"
# 2) only if download successful, then create new statistical SVGs from apidata.json
if [ $? -eq 0 ]; then
    $PYTHON "$DIR/hours_histo.py"
    elapsed "hours_histo.py"
    $PYTHON "$DIR/month_histo.py"
    elapsed "month_histo.py"
    $PYTHON "$DIR/countsbytemp.py"
    elapsed "countsbytemp.py"
    $PYTHON "$DIR/countsbyhumid.py"
    elapsed "countsbyhumid.py"
    log "API data downloaded and SVGs generated at $(date +'%Y-%m-%d %H:%M:%S')"
    elapsed "getStats.sh completed"
else
    log "Data download failed. SVG generation aborted."
    exit 1
fi
