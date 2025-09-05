#!/bin/bash
# anonymize station files for public uploading to github
echo " ----------------------------------------------"
echo "|This script will anonymize your station setup."
echo "|Afterwards the station will no longer work, "
echo "|    but is conceived for building an anonymous image for GITHUB."
echo "|"
echo "|Enter 'Y' for proceeding or anything else to cancel the script."
echo " ----------------------------------------------"
read confirm
confirm=$(echo $confirm| tr -d '[:space:]')
if [[ $confirm != "Y" ]]; then
    echo "You cancelled the script."
    exit 0
fi
cd /home/pi/station2anon
echo "Script is anonymizing code ..."
#
echo "1) wpa_supplicant.conf"
sudo chown root.root wpa_supplicant.conf
sudo chmod 600 wpa_supplicant.conf
sudo cp wpa_supplicant.conf /etc/wpa_supplicant/wpa_supplicant.conf
# /boot is fat32, which does not know permissions and is editable from windows (raspbian mounts /boot as root)
sudo cp wpa_supplicant.conf /boot/wpa_supplicant.conf
sudo cp ssh /boot/ssh
#
echo "2) dhcpcd.conf"
sudo chown root.root dhcpcd.conf
sudo chmod 664 dhcpcd.conf
sudo cp dhcpcd.conf /etc/dhcpcd.conf
#
echo "3) mdroid.sh"
cp mdroid.sh /home/pi/station2/mdroid.sh
echo "4) configBird.py configBird2.py"
cp configBird.py /home/pi/station2/configBird.py
cp configBird2.py /home/pi/station2/configBird2.py
echo "... done"