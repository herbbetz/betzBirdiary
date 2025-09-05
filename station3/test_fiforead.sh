#!/bin/bash

FIFO="ramdisk/birdpipe"

# Create the FIFO if it doesn't exist
if [ ! -p "$FIFO" ]; then
    mkfifo "$FIFO"
    echo "$0 created $FIFO"
fi

echo "Reading from $FIFO..."
while read line; do
    echo "Received: $line"
done < "$FIFO"