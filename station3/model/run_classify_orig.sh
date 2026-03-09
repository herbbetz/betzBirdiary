#!/bin/bash
# called from mainFoBird3.py, activates the pyenv for tflite_runtime in birdclassify.py.
# Runs birdclassify.py inside the pyenv 'birdvenv' (Python 3.11 + numpy 1.26 + tflite_runtime)
# Usage: ./run_classify.sh <filename_prefix>

# activate the birdvenv virtualenv
source /home/pi/.pyenv/versions/birdvenv/bin/activate

# run birdclassify.py with all arguments passed
python /home/pi/station3/model/birdclassify0.py "$@"
python /home/pi/station3/model/birdclassify1.py "$@"
python /home/pi/station3/model/birdclassify2.py "$@"
python /home/pi/station3/model/crop_imgpool.py "$@"
# deactivate only needed for interactive shell, script is called in a subprocess/ subshell, which will exit after python finishes.