#!/bin/bash
# do not rely on sourced path variables during boot!
appdir=/home/pi/station3
logfile="/home/pi/station3/logs/curl.log"
echo >> $logfile # just a newline
echo "***mdroid.sh**************************" >> $logfile
if cd "$appdir"; then
    echo "cd $appdir succeeded" >> $logfile
else
    echo "exit $0: cd $appdir failed! Current directory: $(pwd)" >> $logfile
    exit 1
fi

# source /home/pi/station3/config.sh

if [[ -z $1 ]];then
    msg="noarg"
else
    msg=$1
fi

echo "$(date) message: "$msg >> $logfile

curl_host="https://www.google.com"
curl_ok=false
for i in {1..30}; do
    if /usr/bin/curl -s --head $curl_host | /usr/bin/grep "200 OK" > /dev/null; then
        echo "curl $curl_host succeeded ($i tries)" >> "$logfile"
        curl_ok=true
        break
    fi
    echo "Waiting for DNS & curl ($i)" >> "$logfile"
    sleep 3
done
if [ "$curl_ok" = false ]; then
    echo "curl failed after 30 tries... continuing anyway" >> "$logfile"
    # Optionally: exit 1
fi

config_file="$appdir/config.json"
mdroid_key=$(jq -r '.mdroid_key' "$config_file")
wapp_phone=$(jq -r '.wapp_phone' "$config_file")
wapp_key=$(jq -r '.wapp_key' "$config_file")
# MacroDroid APP, sh. whooktest.macro:
/usr/bin/curl "https://trigger.macrodroid.com/$mdroid_key/herbwebhook?bird=$msg" >> $logfile 2>&1 &
sleep 1
# whatsapp callmebot api:
/usr/bin/curl "https://api.callmebot.com/whatsapp.php?phone=$wapp_phone&text=$msg&apikey=$wapp_key" >> $logfile 2>&1 &
# signal callmebot api, MQTT or else could follow