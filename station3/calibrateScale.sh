#!/bin/bash
# calibration of strain gauge scale hx711
# evaluate exit state $? of python script:
sudo python3 calibrateHxC.py && sudo reboot || echo "Calibration failed — not rebooting."
# python3 hxFiBirdState.py