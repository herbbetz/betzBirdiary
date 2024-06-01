#!/bin/bash
# detect inactivity of mainBird.py, because then it no longer changes ramdisk/line.json
# to read json, best 'apt install jq' (command line JSON processor)
# 'jq .cnt line.json' prints value of "cnt"
# jsonStr=$(< ramdisk/line.json)
minLim=3
minsCnt=0
savedCnt=0
# echo "$cntVal is here"
while true; do
    cntVal=$(jq .linecnt /home/pi/station2/ramdisk/vidmsg.json)
    if [[ $cntVal -eq $savedCnt ]]
    then
        minsCnt=$((minsCnt+1))
    else
        minsCnt=0
    fi

    if [[ $minsCnt -eq $minLim ]]
    then
        echo "value $cntVal was for $minLim mins the same"
        # software shutdown:
        echo "`date` shutdown due to mainBird.py inactivity for $minLim minutes" | mail -s "mainBird.py inactive" pi@localhost
        /home/pi/station2/birdShutdown.sh # my dedicated shutdown script
        break
    fi
    savedCnt=$cntVal
    sleep 60
done
