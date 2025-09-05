#!/bin/bash
# went into config.json: mdroid_key="f9d9d0d0-XXX", wapp_key="", wapp_phone="", tasmota_ip=""
APPDIR="$HOME/station3"
LOGDIR="$APPDIR/logs"
VENVDIR="$HOME/birdvenv"
PYTHON="$VENVDIR/bin/python3"
RAMDISK="$APPDIR/ramdisk"
FIFO="$RAMDISK/birdpipe"