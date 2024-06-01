#!/bin/bash
logfile='/home/pi/station2/logs/curl.log'
if [[ -z $1 ]];then
    msg="noarg"
else
    msg=$1
fi
echo 'bird mdroid msg: '$msg >> $logfile
/usr/bin/curl https://trigger.macrodroid.com/<your-macrodroid-api-key>/herbwebhook?bird=$msg &>> $logfile