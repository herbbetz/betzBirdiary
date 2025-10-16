<!--keywords[bookworm,Pflege_bookworm,README]-->

**Pflege der Stationssoftware**

- Festplattenplatz: `df -h`, `sudo raspi-config --expand-rootfs`.
-  `sudo apt update && sudo apt upgrade`.
-  `pip3 install --upgrade ephem flask markdown matplotlib` (getrennt mit spaces).
-  siehe auch das Skript `/home/pi/update-system.sh`, das die vorangehenden beiden Punkte (Update sowohl mit `apt` als auch mit `pip` im `birdvenv`) zusammenfasst.
-  `/home/pi/update-fromGit.sh` erneuert die Dateien in station3 aus dem Github-Repository `https://github.com/herbbetz/betzBirdiary`.