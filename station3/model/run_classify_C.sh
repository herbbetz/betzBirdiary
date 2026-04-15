#!/bin/bash
# called from mainFoBird3.py
# Version for libbird_tflite.so classifiers, no tflite_runtime or pyenv like in ./run_classify_orig.sh
# Usage: ./run_classify.sh <filename_prefix>

# run birdclassify.py with all arguments passed
python /home/pi/station3/model/birdclassify0C.py "$@"
# python /home/pi/station3/model/birdclassify1C.py "$@"
python /home/pi/station3/model/birdclassify2C.py "$@"
python /home/pi/station3/model/crop_imgpool.py "$@"
# deactivate only needed for interactive shell, script is called in a subprocess/ subshell, which will exit after python finishes.