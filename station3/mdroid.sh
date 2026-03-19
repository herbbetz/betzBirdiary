#!/bin/bash
# do not rely on sourced path variables during boot!
appdir=/home/pi/station3
msgfile=$appdir/ramdisk/vidmsg.json
LOGFILE=$appdir/logs/startup.log
config_file="$appdir/config.json"

log() {
    echo "$*" >> "$LOGFILE" 2>&1
}

check4speed(){
    local func_name=$1
    local target=$2
    start=$(date +%s%3N)
    $func_name  # Don't background here - wait for completion
    local exit_code=$?
    end=$(date +%s%3N)
    duration=$((end - start))
    local linetxt="$target ${duration} ms (exit: $exit_code)"
    log "$linetxt"
    if [[ -f "$msgfile" ]]; then
        flock "$msgfile" "$appdir/log_vidmsg.sh" "$msgfile" "$linetxt"
    fi
    sleep 1
}

check_google(){
    curl --max-time 5 -s --head "https://www.google.com" | grep "HTTP/2 200" >> $LOGFILE 2>&1
}

check_mdroid(){
    /usr/bin/curl --max-time 5 "https://trigger.macrodroid.com/$mdroid_key/herbwebhook?bird=$msg" >> $LOGFILE 2>&1
}

check_wapp(){
    /usr/bin/curl --max-time 5 "https://api.callmebot.com/whatsapp.php?phone=$wapp_phone&text=$msg&apikey=$wapp_key" >> $LOGFILE 2>&1
}

check_mqtt(){
    /usr/bin/mosquitto_pub -h "$mqtt_broker" -p 1883 -t "birdiary/message" -m "$msg" --connection-timeout 5 >> $LOGFILE 2>&1
}


log # just a newline
log "***$0**************************"

if [[ ! -f "$config_file" ]]; then
    log "exit - no $config_file"
    exit 1
fi

if [[ -z $1 ]];then
    msg="noarg"
else
    msg=$1
fi

# second cmdline arg: "w" for skipping wapp
if [[ -z $2 ]];then
    select="0"
else
    select="$2"
fi

log "$(date) message: $msg"
log "select: $select"

check4speed check_google "curl -> google" # check connection to google.com

mdroid_key=$(jq -r '.mdroid_key' "$config_file")
wapp_phone=$(jq -r '.wapp_phone' "$config_file")
wapp_key=$(jq -r '.wapp_key' "$config_file")
mqtt_broker=$(jq -r '.mqtt_broker' "$config_file")

is_valid_key() {
    local key="$1"
    [[ -n "$key" && "$key" != "null" && ! "$key" =~ X$ ]]
}
# MacroDroid APP, sh. whooktest.macro:
# curl could hang without --connect-timeout 3 --max-time 5
if is_valid_key "$mdroid_key"; then # field empty or not existing or ends with X
    check4speed check_mdroid "curl -> mdroid.com"
else
    log "mdroid_key not set: *$mdroid_key*"
fi

# whatsapp callmebot api, skipping with 'w' as 2nd cmdline arg:
# globbing (any-w-any), regex alternative: "$select" =~ w
# DO NOT quote globbing or regex pattern, as this makes them into strings!
if [[ "$select" == *w* ]]; then
    log "skipping wapp due to select flag"
elif is_valid_key "$wapp_key"; then
    check4speed check_wapp "curl -> wapp callmebot"
else
    log "wapp_key not set: *$wapp_key*"
fi

# MQTT:
if is_valid_key "$mqtt_broker"; then
    check4speed check_mqtt "pub -> MQTT broker"
else
    log "mqtt_broker not set: *$mqtt_broker*"
fi
# signal callmebot and else could follow
