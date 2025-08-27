<!--keywords[Installation_kurz,README]-->

## Installation Kurzfassung

- [Download](https://drive.google.com/drive/folders/11WduKyMzzzmW61bC7l0BlDjjx6e_ImHC?usp=sharing) des Disk Image 'betzBirdXXX.7z', entpacken mit [7-zip](https://www.7-zip.org/) und flashen auf SD-Card mit z.B. [balena etcher](https://etcher.balena.io/).

  *Tipp: Teste die SD Karte erst in einem Raspi 4 indoors bezüglich Raspi LEDs und Aufbau eines WLAN Hotspots namens 'bird-ap210'.*

- Menü des eigenen Routers öffnen, Netzwerkkabel in den Raspi einstecken & booten, seine IP im Routernetzwerk suchen und mit `ssh pi@<IP>` einloggen (Login PW: bird24, Root PW: bird24root).

- Nach den Mustern `wlan.yml` und `config.yml` eigene Dateien erstellen und mit `config-yaml.sh my-config.yml` und `sudo ./wlan-yaml.sh my-wlan.yml` der `station3` beibringen und rebooten. Meide WLAN-Passwörter mit Leerzeichen oder `\`.

- Mit `crontab crontab.txt` die `pi crontab` aktivieren. Wie `crontab -l` zeigt, sind dann auch Skripte aktiviert, die die Station abends und bei 'sunset' herunterfahren.

- Zuletzt noch ein ca. 100 g schweres Hängegewicht für die Sitzstange vorbereiten und `python3 calibrateHx711v2.py` aufrufen.