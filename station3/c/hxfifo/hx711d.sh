#!/usr/bin/env bash
set -euo pipefail

BASE_DIR="/home/pi/station3"
CONFIG_FILE="$BASE_DIR/config.json"
DAEMON="$BASE_DIR/c/hx711d"
PID_FILE="$BASE_DIR/ramdisk/hx711d.pid"
LOGFILE="$BASE_DIR/logs/hx711d.log"

log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') $*" >> "$LOGFILE" 2>&1
}

# --- dependency checks ---
if ! command -v jq >/dev/null 2>&1; then
    log "ERROR: jq not installed"
    exit 1
fi

if [[ ! -f "$CONFIG_FILE" ]]; then
    log "ERROR: config file not found: $CONFIG_FILE"
    exit 1
fi

if [[ ! -x "$DAEMON" ]]; then
    log "ERROR: daemon not executable: $DAEMON"
    exit 1
fi

# --- PID check ---
if [[ -f "$PID_FILE" ]]; then
    OLD_PID=$(cat "$PID_FILE")
    if [[ -n "$OLD_PID" ]] && kill -0 "$OLD_PID" 2>/dev/null; then
        log "hx711d already running with PID $OLD_PID — exiting"
        exit 0
    else
        log "Removing stale PID file"
        rm -f "$PID_FILE"
    fi
fi

# --- read pins from JSON ---
DATA_PIN=$(jq -r '.hxDataPin' "$CONFIG_FILE")
CLOCK_PIN=$(jq -r '.hxClckPin' "$CONFIG_FILE")

if [[ -z "$DATA_PIN" || -z "$CLOCK_PIN" || "$DATA_PIN" == "null" || "$CLOCK_PIN" == "null" ]]; then
    log "ERROR: hxDataPin or hxClckPin missing in config.json"
    exit 1
fi

log "Starting hx711d with DATA=$DATA_PIN CLOCK=$CLOCK_PIN"

# --- start daemon ---
"$DAEMON" "$DATA_PIN" "$CLOCK_PIN" &
PID=$!

echo "$PID" > "$PID_FILE"
log "hx711d started with PID $PID"

wait "$PID"
EXIT_CODE=$?

log "hx711d exited with code $EXIT_CODE"
rm -f "$PID_FILE"