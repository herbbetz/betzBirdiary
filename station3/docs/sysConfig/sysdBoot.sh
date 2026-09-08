#!/bin/bash
# check boot up duration (systemd), c't 161-17-2026
LOGDIR="/home/pi/station3/ramdisk"
LOGFILE="$LOGDIR/boot_duration.log"
LOGSVG="$LOGDIR/boot_duration.svg"
log() {
    echo "$*" >> "$LOGFILE" 2>&1
}
echo "Boot up duration logged to $LOGFILE and $LOGSVG"

log "$(systemd-analyze blame)"
systemd-analyze plot > "$LOGSVG"
