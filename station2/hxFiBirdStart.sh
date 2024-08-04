#!/bin/bash
# these two belong together
python3 calibHxOffset.py # produces hxOffset.txt later read in by configbird.py
python3 hxFiBird.py &>> logs/hxFiBird.log # first FIFO writer, seems the most critical to init