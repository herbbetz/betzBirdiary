<!--keywords[Desktop,HDMI-Monitor]-->

**Konfiguration der Trixie Desktop Version**

- Download des *betzBirdiary Desktop Image* von [hier](https://drive.google.com/drive/folders/11WduKyMzzzmW61bC7l0BlDjjx6e_ImHC).

- Flashen mit dem *RPi Imager* oder *balena etcher* (beide akzeptieren `.img.xz`)

- SD-Karte in den Raspberry, Anschließen von HDMI-Monitor, USB-Keyboard und -Maus und in den *Trixie Desktop* booten.

- Im *Trixie Desktop* rechts oben die eigenen WLAN-Daten eintragen, bis das WLAN-Symbol zu sehen ist und stabil bleibt.

- Ein Terminal auf dem Desktop öffnen (`Ctrl-Alt-T`). Mit `ifconfig` oder `ip -a` die eigene `IP4` für WLAN auslesen.

- vorgegebene Passwörter: pi/bird24, root/bird24root

- dann Konfiguration eigener Werte:
  - im Browser `http://<IP4>:8080 (actions-settings-edit)` eigene `boxId` für die birdiary Plattform eintragen.
  
    `(Trixie Desktop Chrome keyring PW: bird24)`
  
  - Pi `crontab`: `crontab crontab.txt`, verifizieren mit `crontab -l`.
  
    **Achtung:** *Eine aktivierte `crontab` fährt gelegentlich das System herunter, z.B. wegen Sonnenuntergang. Zum abendlichen Softwaretest diesen Schritt erst mal überspringen.*
  
  - rebooten und testen, ob alles funktioniert: Browserzugang, SSH / VNC, Kalibrierung der Waage usw.

Happy birding,
herber7be7z@gmail.com



**Bonus-Tipps**

- Dateien, die man selbst verändert, bitte ausserhalb der Station sichern (z.B. mittels WinSCP oder auf Nextcloud), damit sie das nächste Update überleben: `config.json, crontab, station3/keep, station3/mybirds`.
- eigene Vogelvideos und -bilder konfigurieren in `station3/keep/gallery.js` bzw. `station3/mybirds/species.js`. Videobearbeitung siehe `station3/docs/video`.
- die Desktop Version beinhaltet [*RPi Connect*](https://www.raspberrypi.com/documentation/services/connect.html) , das in `raspi-config` aktiviert werden muss und ein *Cloud Connect Account* benötigt. Das Desktop-Symbol ist über die Taskleiste in Plugins als `connect` aktivierbar.
- Integration in *Home Assistant* und andere IOT: Daten zu Belichtung, Temperatur und Systemdaten sind alle in `station3/ramdisk/*.json` und werden auch durch den *Flask Webserver* nach aussen geliefert. Bilder der Kamerasicht werden nur erzeugt bei aktivem Webbrowser, weshalb ein Image-Widget (siehe widget-img.py) keine kontinuierliche Sicht liefert.