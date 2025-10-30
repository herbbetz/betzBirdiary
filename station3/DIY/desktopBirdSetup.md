<!--keywords[Desktop,HDMI-Monitor]-->

**Konfiguration der Trixie Desktop Version**

- Download des *betzBirdiary Desktop Image* von [hier]().
- Flashen mit dem *RPi Imager* oder *balena etcher* (beide akzeptieren `.img.xz`)
- SD-Karte in den Raspberry, Anschließen von HDMI-Monitor, USB-Keyboard und -Maus und in den *Trixie Desktop* booten.
- Im *Trixie Desktop* rechts oben die eigenen WLAN-Daten eintragen, bis das WLAN-Symbol zu sehen ist und stabil bleibt.
- Ein Terminal auf dem Desktop öffnen (`Ctrl-Alt-T`). Mit `ifconfig` oder `ip -a` die eigene `IP4` für WLAN auslesen.
- vorgegebene Passwörter: pi/bird24, root/bird24root
- dann Konfiguration eigener Werte:
  - im Browser `http://<IP4>:8080 (actions-settings-edit)` eigene `boxId` für die birdiary Plattform eintragen
  - Pi Crontab: `crontab crontab.txt`, verifizieren mit `crontab -l`.
  -  rebooten und testen, ob alles funktioniert.