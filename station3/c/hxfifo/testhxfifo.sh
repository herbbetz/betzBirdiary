#!/bin/bash
# see station3/test_fiforead.sh, but the daemon hx711d closes the fifo after each read, so 2 while loops:
FIFO="/home/pi/station3/ramdisk/hxfifo"

echo "Monitoring $FIFO (Ctrl+C to stop)"
echo "----------------------------------"

while true; do
    while read line; do date +"%H:%M:%S.%3N $line"; done < $FIFO
    sleep 0.1
done