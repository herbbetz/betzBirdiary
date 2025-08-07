#!/bin/bash
source ./config.sh
# this is called by sysMon.sh to inform browser of new measurements by increasing the counter "sysmonEvt" in vidmsg.json
msgfile="$RAMDISK/vidmsg.json"
json_data=$(cat $msgfile)
# echo $json_data
cnt=$(jq .sysmonEvt <<< $json_data) # <<< here string
cnt=$((cnt + 1))
new_json=$(jq --argjson cnt $cnt '.sysmonEvt = $cnt' <<< $json_data)
# echo $new_json
echo $new_json > $msgfile