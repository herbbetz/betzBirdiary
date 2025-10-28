#!/bin/bash
# softlink this to startup.sh for testing and load all scripts manually:
APPDIR=/home/pi/station3
FIFO=/home/pi/station3/ramdisk/birdpipe
LOGFILE="/home/pi/station3/logs/startup.log"
log() {
    echo "$*" >> "$LOGFILE" 2>&1
}

# main:
log "$0 started at $(date)"
# following guarantees, that working dir is up at boot:
if cd "$APPDIR"; then
    log "cd $APPDIR succeeded"
else
    log "exit $0: cd $APPDIR failed! Current directory: $(pwd)"
    exit 1
fi
# Python venv: in bird-startup.service and bashrc.sh

# FIFO programming in bash simpler than in python -> https://www.linuxjournal.com/content/using-named-pipes-fifos-bash
if [[ ! -p "$FIFO" ]]; then
    mkfifo "$FIFO"
    # echo "created: "$fifo
fi