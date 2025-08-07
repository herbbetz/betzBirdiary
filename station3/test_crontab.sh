#!/bin/bash

# Define the minimal cron-like environment
export SHELL=/bin/sh
export USER="$USER"
export HOME="$HOME"
export LOGNAME="$LOGNAME"
export PATH="/usr/bin:/bin"

# Get all non-comment, non-blank lines from the user's crontab
crontab -l | grep -vE '^\s*#|^\s*$' | while read -r line; do
  # Remove the first 5 fields (schedule), keep the command
  cmd=$(echo "$line" | awk '{for(i=6;i<=NF;++i) printf $i" "; print ""}')
  # Skip if command is empty
  [ -z "$cmd" ] && continue
  echo "only testing timed commands from crontab, not directives like @reboot"
  echo "-----------------------------"
  echo "Executing: $cmd"
  env -i SHELL=$SHELL USER=$USER PATH=$PATH HOME=$HOME LOGNAME=$LOGNAME /bin/sh -c "$cmd"
  status=$?
  if [ $status -eq 0 ]; then
    echo "Command succeeded (exit code 0)"
  else
    echo "Command failed (exit code $status)"
  fi
  echo "-----------------------------"
done
