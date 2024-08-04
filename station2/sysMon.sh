#!/bin/bash  
# get easy to aquire system variables, write them to json for fetching by webpage
# define functions before usage:
function secs2hours {
    local mins=$(echo "$1/60" |bc) # bc allows float input, returns int (if no scale option)
    local hrs=$(( mins/60 ))
    mins=$(( $mins-(hrs*60) ))
    echo "$hrs:$mins"
}
# declare -A monitor # AssociativeArray -> output unsorted, therefore use indexed array:
monitor[0]=$(date)
key[0]="date"
#
UPTIME=$(cat /proc/uptime)
UPTIME=$(echo  $UPTIME |cut -d " " -f 1) #field 1
UPTIME=$(secs2hours $UPTIME)
monitor[1]=$(echo $UPTIME'hrs')
key[1]="uptime"
#
# echo "Power test vcgencmd"
# picamera1:
# CAMERA=$(echo $(vcgencmd get_camera) |cut -d " " -f 2)
# CAMERA=$(echo $CAMERA | sed "s/.$//") #remove last char (trailing comma)
# monitor[2]=$(echo $CAMERA); key[2]="camera"
THROTTLE=$(echo $(vcgencmd get_throttled) |cut -d "=" -f 2)
monitor[2]=$(echo $THROTTLE'(normal 0x0)'); key[2]="throttle"
CPUVOLT=$(echo $(vcgencmd measure_volts core) |cut -d "=" -f 2)
monitor[3]=$(echo $CPUVOLT); key[3]="cpuvolt"
CPUTEMP=$(echo $(vcgencmd measure_temp) |cut -d "=" -f 2)
CPUTEMP=$(echo $CPUTEMP | sed "s/'//g") # ' disturbs valid json
monitor[4]=$(echo $CPUTEMP); key[4]="cputemp"
CPULOAD=$(bash /home/pi/station2/cpu5sec.sh) # cpu5sec measures & blocks for 5 secs
monitor[5]=$(echo $CPULOAD'%'); key[5]="cpuload"
#
cd /home/pi/station2
# build JSON:
lastKey=$(( ${#key[@]}-1 )) #length of key[], zero-based
outfile="ramdisk/sysmon.json" #full path for crontab
# echo '' > $outfile # empty or touch create file
echo -n "{" >$outfile
for (( i=0; i<=$lastKey; i++ )); do
    echo -n '"'${key[i]}'":"'${monitor[i]}'"' >>$outfile
    if (( i<$lastKey )); then
        echo -n ", " >>$outfile
    else
        echo -n "}" >>$outfile
    fi
done
# update sysmonEvt counter in vidmsg.json
#   using advisory (= programmed) file lock, see https://www.baeldung.com/linux/file-locking
msgfile="ramdisk/vidmsg.json"
flock $msgfile ./updateSysmonEvt.sh