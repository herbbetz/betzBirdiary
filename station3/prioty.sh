#!/bin/bash

# 1. Check if argument was provided
if [[ -z "$1" ]]; then
    echo "Usage: $0 <your_program_name>"
    echo "Shows CPU affinity and scheduling policy for matching process(es)."
    exit 1
fi

# 2. Get process ID(s)
# Exclude the pgrep/script itself from search results
PIDS=$(pgrep -f "$1" | grep -v "$$")

# 3. Check if any process was found
if [[ -z "$PIDS" ]]; then
    echo "Error: No process matching '$1' found."
    exit 1
fi

# 4. Iterate over each matching PID safely
for PID in $PIDS; do
    # Get executable / command name for clarity
    CMD=$(ps -p "$PID" -o comm= 2>/dev/null)
    
    echo "========================================"
    echo " PID: $PID ($CMD)"
    echo "========================================"
    
    # Check CPU affinity
    taskset -p "$PID" 2>/dev/null
    
    # Check scheduling policy and priority
    chrt -p "$PID" 2>/dev/null
    echo ""
done
echo "Press any key to show processes on CPU 3 ...end by Ctrl+C"
read -n1 -s
watch -n 1 "ps -eo pid,psr,user,pcpu,comm | awk '\$2 == 3'"