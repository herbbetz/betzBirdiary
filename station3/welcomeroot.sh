#!/bin/bash
echo
echo " ----------------------------------------"
echo "| Important scripts for birdiary wlan:"
echo "|"
echo "| > /etc/netplan/"
echo "| > /etc/NetworkManager/system-connections"
echo "|" 
echo "| > /etc/systemd/system/bird-startup.service"
echo "|   contains After=network-online.target, Wants=network-online.target"
echo "|" 
echo "| > /home/pi/birdvenv owner root to protect against deletion"
echo "|   ref in bird-startup.service, crontab, config.sh, bashrc.sh, activate_venv.sh"
echo "|" 
echo "| > /etc/fstab for station3/ramdisk"
echo "| > /etc/hosts, hostname"
echo "| > /etc/avahi/avahi-daemon.conf wanted in bird-startup.service"
echo "| > /etc/logrotate.d/birdlogrotate"
echo " ----------------------------------------"
echo
# cd /etc/... put into root`s .bashrc
