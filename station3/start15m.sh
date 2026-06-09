#!/bin/bash
# scripts run on boot and every 15 min by '/etc/systemd/system/bird15m.service'
/usr/bin/python3 /home/pi/station3/dhtBird3.py
/home/pi/station3/sysmon2.sh
/home/pi/station3/heatTest.sh
/home/pi/station3/argonset.sh