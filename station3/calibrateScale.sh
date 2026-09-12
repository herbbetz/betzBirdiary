#!/bin/bash
# calibration of strain gauge scale hx711
# evaluate exit state $? of python script:
python3 calibrateHx.py && sudo reboot || echo "Calibration failed — not rebooting."
# python3 hxFiBirdState.py