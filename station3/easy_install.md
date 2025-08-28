<!--keywords[Installation_kurz,README]-->

## Installation Kurzfassung

- [Download](https://drive.google.com/drive/folders/11WduKyMzzzmW61bC7l0BlDjjx6e_ImHC?usp=sharing) des Disk Image 'betzBirdXXX.7z' oder 'betzBirdXXX.xz'. Ersteres entpacken mit [7-zip](https://www.7-zip.org/) und flashen auf SD-Card mit z.B. [balena etcher](https://etcher.balena.io/). `xz`-komprimierte Images kann der `balena etcher` ohne Entpacken flashen.

  *Tipp: Teste die SD Karte erst in einem Raspi 4 indoors bezüglich Raspi LEDs und Aufbau eines WLAN Hotspots namens 'bird-ap210'.*

- Menü des eigenen Routers öffnen, Netzwerkkabel in den Raspi einstecken & booten, seine IP im Routernetzwerk suchen und mit `ssh pi@<IP>` einloggen (Login PW: bird24, Root PW: bird24root).

- Nach dem Muster `wlan.yml` eine Datei mit den eigenen WLAN-Parametern erstellen und mit `sudo ./wlan-yaml.sh my-wlan.yml` der `station3` beibringen und rebooten. Meide WLAN-Passwörter mit Leerzeichen oder `\`.

- Ist die Station im Heimnetz-Router-WLAN angekommen, kann das WebGUI der Station unter `http://<wlan-ip>:8080` aufgerufen werden. Dort sind unter `action-settings-edit` Parameter wie die birdiary `boxId` der eigenen Vogelstation einzugeben. Diese landen dann in `config.json`.

- Mit `crontab crontab.txt` die `pi crontab` aktivieren. Wie `crontab -l` zeigt, sind dann auch Skripte aktiviert, die die Station abends und bei 'sunset' herunterfahren.

- Zuletzt noch ein ca. 100 g schweres Hängegewicht für die Sitzstange vorbereiten und `python3 calibrateHx711v2.py` aufrufen.