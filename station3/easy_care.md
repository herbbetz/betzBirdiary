<!--keywords[bookworm,Pflege_bookworm,README]-->

**Pflege der Stationssoftware**

- Festplattenplatz: `df -h`, `sudo raspi-config --expand-rootfs`.
-  `sudo apt update && sudo apt upgrade`.
-  `pip3 install --upgrade ephem flask markdown matplotlib` (getrennt mit spaces) und `pip3 uninstall numpy` (Inkompat. zu `apt install python3-picamera2` ).