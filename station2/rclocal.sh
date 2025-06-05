#!/bin/bash
# called from /etc/rc.local as root
sleep 5 #give wlan time to establish
/usr/sbin/iwconfig wlan0 power off