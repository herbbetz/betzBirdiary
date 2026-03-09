#!/bin/bash
# called from mainFoBird3.py, activates the pyenv for tflite_runtime in birdclassify.py.
# Usage: ./run_classify.sh <filename_prefix>
# version for debugging
# Exit on error
set -e

# --- Activate birdvenv ---
if [ -f "$HOME/.pyenv/versions/birdvenv/bin/activate" ]; then
    # source the virtualenv
    source "$HOME/.pyenv/versions/birdvenv/bin/activate"
else
    echo "ERROR: birdvenv not found at $HOME/.pyenv/versions/birdvenv"
    exit 1
fi

# Log Python version and tflite_runtime version for debug
echo "Using Python: $(which python) ($(python --version))"
python -c "import tflite_runtime as tflite; print('tflite_runtime version:', tflite.__version__)"
python -c "import numpy as np; print('numpy version:', np.__version__)"

# Pass all arguments to birdclassify.py
python "$HOME/station3/model/birdclassify.py" "$@"