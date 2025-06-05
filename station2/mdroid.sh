#!/bin/bash
logfile='/home/pi/station2/logs/curl.log'
if [[ -z $1 ]];then
    msg="noarg"
else
    msg=$1
fi
echo " `date` bird mdroid msg: "$msg >> $logfile
# MacroDroid APP, sh. whooktest.macro:
/usr/bin/curl "https://trigger.macrodroid.com/f9d9d0d0-f205-4ce2-a2d6-5875xxxxxxxx/herbwebhook?bird=$msg" &>> $logfile
sleep 1
# whatsapp callmebot api:
/usr/bin/curl "https://api.callmebot.com/whatsapp.php?phone=49871xxxxxxxx&text=$msg&apikey=xxxxxxxx" &>> $logfile
# signal callmebot api:
