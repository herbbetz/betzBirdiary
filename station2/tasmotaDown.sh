#!/bin/bash
if [[ -z $1 ]];then
    msg="anyshutdown"
else
    msg=$1
fi
cd /home/pi/station2
bash mdroid.sh $msg
# https://tasmota.github.io/docs/Commands/
# %20 = ' ', %3B = ';', Backlog = 'command sequence with ; separator', Delay 1200 = '1200 * 0.1secs'
# /usr/bin/curl "http://192.168.178.50/cm?cmnd=Backlog%20Delay%201200%3BPower%20off"
CNT=0
while [[ $CNT < 3 ]]; do
    sleep 5
    status_code=$(/usr/bin/curl -s -o /dev/null -w "%{http_code}" "http://192.168.178.50/cm?cmnd=Backlog%20Delay%201200%3BPower%20off")
    # echo $CNT: $status_code
    if [[ $status_code == 200 ]]; then
        break
    fi
    CNT=$((CNT+1))
done
sudo shutdown -h +1