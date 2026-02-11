#!/bin/bash
# called from crontab and scripts of bash and python:
APPDIR="$HOME/station3"
LOGFILE=/home/pi/station3/logs/startup.log
config_file="$APPDIR/config.json"

log() {
    echo "$*" >> "$LOGFILE" 2>&1
}

tasmota_ip=$(jq -r '.tasmota_ip' "$config_file")

if [[ -z $1 ]];then
    msg="anyshutdown"
else
    msg=$1
fi

bash "$APPDIR/mdroid.sh" "$msg"
sleep 10
# https://tasmota.github.io/docs/Commands/
# %20 = ' ', %3B = ';', Backlog = 'command sequence with ; separator', Delay 1200 = '1200 * 0.1secs', Power means Power1 = relay 1
# /usr/bin/curl "http://192.168.178.50/cm?cmnd=Backlog%20Delay%201200%3BPower%20off"
CNT=0
RESPONSE=0
if [[ -n "$tasmota_ip" && "$tasmota_ip" != "null" && ! "$tasmota_ip" =~ X$ ]]; then # field empty or not existing or ends with X
    while [[ $CNT -lt 3 ]]; do
        sleep 5
        # could hang here without --connect-timeout 3 --max-time 5:
        status_code=$(/usr/bin/curl --connect-timeout 5 --max-time 10 -s -o /dev/null -w "%{http_code}" "http://$tasmota_ip/cm?cmnd=Backlog%20Delay%201200%3BPower1%20off") 
        # echo $CNT: $status_code
        if [[ $status_code == 200 ]]; then
            RESPONSE=1
            break
        fi
        CNT=$((CNT+1))
    done
    if [[ $RESPONSE == 0 ]]; then
        log "$tasmota_ip shutdown fail"
        bash "$APPDIR/mdroid.sh" "$tasmota_ip.down.fail"
    fi   
fi

# clean daydir/
rm $APPDIR/daydir/*.jpg >/dev/null 2>&1
rm $APPDIR/daydir/*.csv >/dev/null 2>&1

sudo sync
sudo shutdown -h +1