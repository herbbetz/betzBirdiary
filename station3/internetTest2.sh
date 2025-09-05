#!/bin/bash
# test for working internet connection, take action (shutdown) when connection off
ONLINE=1
CNT=0
CNTLIMIT=3
# logfile="/home/pi/station/logs/internetTest.log" replaced by redirect >
# echo "deactivate wlan0, wlan1 is on USB"
# wlan0 deactivated in /etc/dhcpcd.conf by denyinterfaces wlan0
# sudo ip link set wlan0 down

while true; do
  sleep 60
  echo "Internet Test"
  ping -q -c 1 -w 1 www.google.com >/dev/null 2>&1
  #save return code in variable:
  ONLINE=$?
  if [[ $ONLINE != 0 ]]
  then
     echo "`date` Internet not online!"
     CNT=$((CNT+1))
     if [[ $CNT -lt $CNTLIMIT ]] # single brackets enough?
     then
       # try restarting internet:
       echo "`date` Internet Problem"
       # wlan0 oder wlan1:
       sudo ip link set wlan0 down
       sleep 5
       sudo ip link set wlan0 up
     else
       # software shutdown:
       echo "`date` shutdown due to internet lost for $CNTLIMIT minutes" | mail -s "internet lost" pi@localhost
       /home/pi/station2/tasmotaDown.sh internetdown # my dedicated shutdown script
       break
     fi
  fi
  if [[ $ONLINE == 0 ]]
  then
     CNT=0
     echo "`date` Internet good"
  fi
done
exit
