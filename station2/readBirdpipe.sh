#!/bin/bash
# script to demonstrate, how to read FIFO from bash
fifo="ramdisk/birdpipe"
# create fifo: if [[ ! -p $fifo ]]; then mkfifo $fifo; fi
# write to fifo: echo 'hallo'>ramdisk/birdpipe
# now for reading:
echo "stop by cmd: echo 'X'>ramdisk/birdpipe from other terminal"
line=""
while [[ $line != "X" ]]; do
    read line < $fifo
    echo "rcvd: "$line
done