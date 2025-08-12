#!/bin/bash
echo
echo " ----------------------------------------"
echo "| Important scripts for birdiary wlan:"
echo "|"
echo "| > /etc/NetworkManager/system-connections"
echo "|" 
echo "| > /etc/systemd/system/bird-startup.service"
echo "|   contains After=network-online.target, Wants=network-online.target"
echo " ----------------------------------------"
echo
# cd /etc/... put into root`s .bashrc
