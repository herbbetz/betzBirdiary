#!/bin/bash
# usage: python3 check_noise.py [duration_s] | python3 check_noise.py step
python3 check_noise.py "$@" 2>&1 | tee ramdisk/check_noise.log
