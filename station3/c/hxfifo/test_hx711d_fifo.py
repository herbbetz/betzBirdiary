#!/usr/bin/env python3

"""
Minimal test for hx711d C daemon.
Reads raw values from FIFO and prints them.
- Terminal 1: /home/pi/station3/c/hx711d 17 23
- Terminal 2: python3 test_hx711d_reader.py
"""
import time
from configBird3 import hxOffset, hxScale

FIFO_PATH = "/home/pi/station3/ramdisk/hxfifo"

print("Opening FIFO...")
print("Waiting for hx711d to send data...\n")

with open(FIFO_PATH, "r") as fifo:
    while True:
        line = fifo.readline()
        if not line:
            time.sleep(1) # or 0.01
            continue

        raw = int(line.strip())
        print(f"RAW={raw}")
        # grams = (raw - hxOffset) / hxScale
        # print(f"RAW={raw}  {grams:.2f} g")