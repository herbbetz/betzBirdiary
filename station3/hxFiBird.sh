#!/bin/bash
# hxFiBird.sh is (re-)started by hxFiBird.service after startupNoInet.sh (creates FIFO owned by pi)
APPDIR="/home/pi/station3"
PYTHON="/usr/bin/python3"
LOGFILE="$APPDIR/ramdisk/hxFiBird.log"
FIFO="$APPDIR/ramdisk/birdpipe"

if [[ $EUID -ne 0 ]]; then
    echo "$0 not running as root" >> $LOGFILE 2>&1
    exit 1
fi
# no 'sudo chown' because we are root
if [ ! -p "$FIFO" ]; then
    mkfifo "$FIFO"
    chown pi:pi "$FIFO"
    chmod 666 "$FIFO"
    echo "$0 creates $FIFO" >> $LOGFILE 2>&1
fi
# first FIFO writer, seems the most critical to init
# high user space priority: sudo chrt -f 80 <script> (chrt needs root permissions, later run 'sudo python hxFiBirdStateCt.py test' as 'ramdisk/hxFiPID.txt' will belong to root)
# dedicated CPU core: taskset -c 3 <script> (CPU core 3 is least used by system, see 'top' or 'htop'), set isolcpus=3 in /boot/firmware/cmdline.txt to isolate CPU core 3 from system tasks, so it can be used for real-time tasks.
# nproc --all ensures isolated cores like isolcpus=3 are counted
TOTAL_CPUS=$(nproc --all)
if [ "$TOTAL_CPUS" -ge 4 ]; then
    # Pass taskset directly with sudo
    taskset -c 3 chrt -f 80 "$PYTHON" "$APPDIR/hxFiBirdStateCt.py" | tee -a "$LOGFILE" 2>&1
    # setsid sudo taskset -c 3 chrt -f 80 "$PYTHON" "$APPDIR/hxFiBirdStateCt.py" test >> "$APPDIR/ramdisk/hxFiBird.log" 2>&1 &
else
    chrt -f 80 "$PYTHON" "$APPDIR/hxFiBirdStateCt.py" | tee -a "$LOGFILE" 2>&1
fi
bash "$APPDIR/mdroid.sh" scale_ended # mdroid.sh writes to startup.log