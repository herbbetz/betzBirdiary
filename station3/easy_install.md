<!--keywords[Installation_kurz,README]-->

## Installation Kurzfassung

- [Download](https://drive.google.com/drive/folders/11WduKyMzzzmW61bC7l0BlDjjx6e_ImHC?usp=sharing) des Disk Image 'betzBirdXXX.7z' oder 'betzBirdXXX.xz'. Ersteres entpacken mit [7-zip](https://www.7-zip.org/) und flashen auf SD-Card mit z.B. [balena etcher](https://etcher.balena.io/). `xz`-komprimierte Images kann der `balena etcher` ohne Entpacken flashen. Wird der `Raspberry Pi Imager` verwendet, können die eigenen WLAN-Daten dort bereits vorkonfiguriert werden (CTRL-Shift-X) und das WLAN kann bereits nach dem ersten Hochfahren vorhanden und im Router (Fritzbox) zu sehen sein.

  *Tipp: Teste die SD Karte erst in einem Raspi 4 indoors bezüglich Raspi LEDs und Integration ins Heim-WLAN. Meide WLAN-Passwörter mit Leerzeichen oder `\`.*

- Der einfachste Weg zur WLAN-Einbindung sind die Icons der Desktop-Oberfläche rechts oben, zugänglich z.B. über HDMI-Monitor oder RealVNC.  Diese Icons machen die folgenden Kenntnisse zu verschiedenen Mechanismen der WLAN-Verbindung (wie NetworkManager, Netplan) entbehrlich.

- Menü des eigenen Routers öffnen, Netzwerkkabel in den Raspi einstecken & booten, seine IP im Routernetzwerk suchen und mit `ssh pi@<IP>` einloggen (Login PW: bird24, Root PW: bird24root). `ping <IP>` sollte erfolgreich sein. **Achtung:** das LAN-Kabel schon vor dem Booten des Raspberry einstecken.

- Sollte weder der `RPi Imager` noch das `LAN Kabel` noch ein im Smartphone auffindbarer `WiFi Access Point namens bird-ap210 (PW: bird24root)` einen SSH-Zugang liefern, kann man die SD-Karte mittels Kartenleser auch an einen Ubuntu Laptop anschließen und vor dem Hochfahren in `/media/<user>/rootfs/etc/NetworkManager/system-connections/` eine eigene `wifi.nmconnections` kopieren. Und wenn alle Stricke reißen, hat man ja auch noch Zugang über USB-Keyboard und HDMI-Monitor.

- Das Heimnetz-WLAN aktivieren am besten über die Desktop Icons (s.o.) oder alternativ:

  - `sudo nmcli device wifi rescan`, dann `nmcli device wifi list`, dann `sudo nmcli dev wifi connect "SSID" password "PASSWORD"`. `SSID` ist der Name des eigenen WLAN.
  
  - oder innerhalb 2 min nach Drücken der WPS-Taste am Heimrouter: `sudo nmcli dev wifi connect "SSID" wps-pbc`
  
  - Diese Verbindungen macht `NetworkManager` automatisch permanent. Danach reicht ein `sudo systemctl restart NetworkManager`. Da die SSH-Sitzung noch über das Netzkabel läuft, bleibt sie erhalten. In `ifconfig` und im Router taucht jetzt auch die WLAN-Verbindung auf. Danach ist das Netzkabel entbehrlich.
  
  - Deaktiviere MAC-Sperren im Router, die neue WLAN-Geräte nicht zulassen.
  
- Ist die Station im Heimnetz-Router-WLAN angekommen, kann das WebGUI der Station unter `http://<wlan-ip>:8080` aufgerufen werden. Dort sind unter `actions-settings-edit` Parameter wie die birdiary `boxId` der eigenen Vogelstation einzugeben. Diese landen dann in `config.json`. Die neuen Parameter werden erst nach einem `actions-reboot` bzw. `sudo reboot` wirksam.

- Auf Kommandozeile mit `crontab crontab.txt` die `pi crontab` aktivieren. Wie `crontab -l` zeigt, sind dann auch Skripte aktiviert, die die Station abends und bei 'sunset' herunterfahren.

- Zuletzt noch ein ca. 100 g schweres Hängegewicht für die Sitzstange vorbereiten und `python3 calibrateHx711v2.py` aufrufen.

- Optional: `sudo raspi-config --expand-rootfs` schafft Platz für eigene Anwendungen (Nachinstallation Docker oder Desktop etc.) .

- Nach geglückter Installation und Kommunikation mit der birdiary Plattform die Datei `station3/config.json` sichern für künftige Versionen von betzBirdiary.





Feedback an herber7be7z@gmail.com .