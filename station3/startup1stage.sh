#!/bin/bash
# softlink this to startup.sh for testing and load all scripts manually:
APPDIR=/home/pi/station3
LOGFILE="/home/pi/station3/logs/startup.log"
bash $APPDIR/startupNoInet.sh
setsid bash "$APPDIR/startup2stage.sh" >> "$LOGFILE" 2>&1 # why setsid or nohup?