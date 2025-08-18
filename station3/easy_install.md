<!--keywords[Installation_kurz,README]-->

## Installation Kurzfassung

- [Download](https://drive.google.com/drive/folders/11WduKyMzzzmW61bC7l0BlDjjx6e_ImHC?usp=sharing) von 'betzBirdXXX.img' und Flashen auf SD-Card mit z.B. [balena etcher](https://etcher.balena.io/).
- Nach dem Booten sich mit dem Bird-WLAN-Hotspot verbinden (WLAN PW: bird24root) und mit `ssh pi@192.168.4.1` einloggen (Login PW: bird24, Root PW: bird24root).
- Nach den Mustern `wlan.yml` und `config.yml` eigene Dateien erstellen und mit `config-yaml.sh my-config.yml` und `sudo ./wlan-yaml.sh my-wlan.yml` der `station3` beibringen und rebooten.
- Mit `crontab crontab.txt` die `pi crontab` aktivieren. Wie `crontab -l` zeigt, sind dann auch Skripte aktiviert, die die Station abends und bei 'sunset' herunterfahren.