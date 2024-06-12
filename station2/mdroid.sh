#!/bin/bash
logfile='/home/pi/station2/logs/curl.log'
if [[ -z $1 ]];then
    msg="noarg"
else
    msg=$1
fi
echo " `date` bird mdroid msg: "$msg >> $logfile
/usr/bin/curl https://trigger.macrodroid.com/f9d9d0d0-f205-4ce2-a2d6-58752613c975/herbwebhook?bird=$msg &>> $logfile