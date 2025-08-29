#!/bin/bash
# https://medium.com/@jhh3/poor-mans-disk-monitoring-adc6093b680d
# @daily in pi crontab
THRESHOLD=90
CURRENT=$(df --output=pcent / | tail -n 1 | sed 's/%//g')
if [ "$CURRENT" -gt "$THRESHOLD" ] ; then
#     mail -s 'Disk Space Alert' pi@localhost << EOF
# Used disk space ${CURRENT}% is over ${THRESHOLD}%! 
# EOF
    echo "Used disk space ${CURRENT}% is over ${THRESHOLD}%!"
    df -h
else 
    echo "Used disk space ${CURRENT}%"
fi