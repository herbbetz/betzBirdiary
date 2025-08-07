#!/bin/bash
# Check if a command-line argument is provided
if [ -z "$1" ]; then
  echo "usage: $0 string_for_fifo"
  exit 1
fi

# Check if the FIFO exists and is a named pipe
FIFO="ramdisk/birdpipe"
if [ ! -p "$FIFO" ]; then
  echo "Error: FIFO '$FIFO' does not exist"
  exit 1
fi

echo "$1" > "$FIFO"
echo "wrote $1 to $FIFO"

exit 0