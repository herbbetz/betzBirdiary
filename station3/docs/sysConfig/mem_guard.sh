#!/bin/bash
# chatGPT 1.4.26, terminate 'image_model' with memory exhaustion, exec every 15 sec by systemd timer
# =========================
# Memory Guard (SD-safe)
# =========================

# --- CONFIG ---
RAM_THRESHOLD=85          # warn level
CRITICAL_THRESHOLD=95     # pause level
RECOVERY_THRESHOLD=80     # resume level

MODEL_TO_PAUSE="image_model"   # adjust to your process name

STATE_FILE="/tmp/mem_guard_high"
PAUSE_FILE="/tmp/mem_guard_paused"

# --- GET MEMORY USAGE ---
MEM_TOTAL=$(grep MemTotal /proc/meminfo | awk '{print $2}')
MEM_AVAILABLE=$(grep MemAvailable /proc/meminfo | awk '{print $2}')
MEM_USED=$((MEM_TOTAL - MEM_AVAILABLE))
MEM_PERCENT=$((MEM_USED * 100 / MEM_TOTAL))

# --- DEBUG (optional) ---
# echo "RAM usage: $MEM_PERCENT%"

# =========================
# STATE MACHINE
# =========================

# --- HIGH MEMORY ---
if [ "$MEM_PERCENT" -gt "$RAM_THRESHOLD" ]; then
    if [ ! -f "$STATE_FILE" ]; then
        logger -t mem_guard "⚠️ RAM high: ${MEM_PERCENT}%"
        touch "$STATE_FILE"
    fi
fi

# --- CRITICAL MEMORY ---
if [ "$MEM_PERCENT" -gt "$CRITICAL_THRESHOLD" ]; then
    if [ ! -f "$PAUSE_FILE" ]; then
        logger -t mem_guard "🚨 CRITICAL RAM: ${MEM_PERCENT}% → pausing $MODEL_TO_PAUSE"
        pkill -STOP -f "$MODEL_TO_PAUSE"
        touch "$PAUSE_FILE"
    fi
fi

# --- RECOVERY ---
if [ "$MEM_PERCENT" -lt "$RECOVERY_THRESHOLD" ]; then

    # clear HIGH state
    if [ -f "$STATE_FILE" ]; then
        logger -t mem_guard "✅ RAM back to normal: ${MEM_PERCENT}%"
        rm "$STATE_FILE"
    fi

    # resume paused process
    if [ -f "$PAUSE_FILE" ]; then
        logger -t mem_guard "▶️ Resuming $MODEL_TO_PAUSE"
        pkill -CONT -f "$MODEL_TO_PAUSE" 2>/dev/null
        rm "$PAUSE_FILE"
    fi
fi

exit 0