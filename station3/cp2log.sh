#!/bin/bash
set -euo pipefail  # Exit on error, undefined vars, pipe failures

# copy files from ramdisk to log (e.g. on reboot or shutdown)
SRCDIR="/home/pi/station3/ramdisk"
DSTDIR="/home/pi/station3/logs"

# Source files array
src_files=("signal_hx.csv" "cam_event.csv" "hxFiBird.log" "startup.log")

# Ensure destination exists
if [[ ! -d "$DSTDIR" ]]; then
    echo "Error: Destination directory $DSTDIR does not exist."
    exit 1
fi

# Loop and transfer with renaming
for src in "${src_files[@]}"; do
    if [[ -f "$SRCDIR/$src" ]]; then
        # Extract base name without extension (renamed to avoid collision)
        file_base="${src%.*}"
        extension="${src##*.}"
        
        # New name with date suffix (MMDDHHMMSS for uniqueness)
        suffix=$(date +%m%d%H%M)
        new_name="${file_base}_${suffix}.${extension}"
        
        # Copy and rename
        if cp "$SRCDIR/$src" "${DSTDIR}/${new_name}"; then
            echo "Transferred: $SRCDIR/$src -> ${DSTDIR}/${new_name}"
        else
            echo "Error: Failed to copy $src" >&2
        fi
    else
        echo "Warning: $SRCDIR/$src not found" >&2
    fi
done