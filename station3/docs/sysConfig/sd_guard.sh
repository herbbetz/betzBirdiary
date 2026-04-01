#!/bin/bash
# chatGPT 1.4.26, check errors of sd card
STATE_FILE="/tmp/sd_error_state"

# Check for MMC errors in last boot
if dmesg | grep -qi "mmc.*error"; then
    if [ ! -f "$STATE_FILE" ]; then
        logger -t sd_guard "🚨 SD card I/O errors detected!"
        touch "$STATE_FILE"
    fi
else
    if [ -f "$STATE_FILE" ]; then
        logger -t sd_guard "✅ SD card errors cleared"
        rm "$STATE_FILE"
    fi
fi