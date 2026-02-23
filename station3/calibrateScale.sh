#!/bin/bash
# calibration of strain gauge scale hx711
python3 calibrateHx711v2.py
# test reading:
python3 - <<EOF
from lgpioBird.HX711 import HX711
hx = HX711(17,23)   # your pins for data and clock
for _ in range(10):
    print(hx.get_weight())
EOF
python3 hxFiBirdState.py