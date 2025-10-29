<!--keywords[DIY,Selbstbauprojekt,Trixie]-->

**Selbstbau der betzBirdiary Software in eigenes Trixie**  (Stand Okt.2025)

1. Flashen von `Raspbian Trixie 64bit Desktop` mit `RPi Imager v1.9.6 (Windows)`, dabei dort eigene PasswortLogin- und WLAN-Einstellungen vorgeben mit `Ctrl-Shift-X` und anwenden.

   *Hochfahren und LAN/WLAN im Router testen, dann `ssh pi@<IP4>`*. Frägt das Login nach `publickey`, dann mit HDMI/Monitor einloggen und Umstellen in `/etc/ssh/sshd_config`. Auch sonst ist zum Debuggen bes. des Bootvorganges beim Raspberry4 das *Mikro-HDMI-Kabel/USB-Keyboard* ratsam.

   `sudo apt update && sudo apt upgrade`

2. In `/home/pi` eingeben `git clone https://github.com/herbbetz/betzBirdiary`, dann `cd betzBirdiary` und `mv station3 /home/pi` und `cd /home/pi/station3`. Aktiviere die Shell Skripte in `station3` mit `chmod +x *.sh`.

   *Etliche birdiary Skripte gehen davon aus, dass `/home/betz/station3` das Appdir ist.*


3. Installiere Module für `station3`: `sudo apt install python3-ephem python3-flask python3-markdown python3-matplotlib` und `sudo apt install bc curl dnsutils ffmpeg jq screen`.

4. Teste die wesentlichen Skripte in `station3` auf fehlende Module:

   Beende jeweils mit `Ctrl-C`, wenn keine Fehlermeldung auftaucht. Die Fehlermeldungen auf `Ctrl-C` hin zählen nicht.

   - `python3 flaskBird3.py` macht die Weboberfläche im Browser unter `http://<IP4>:8080` sichtbar.
   
   - `python3 mainFoBird3.py test` macht Bilder und Videos.
   
   - `python3 hxFiBird3.py` frägt die Waage ab.
   
   - `python3 dhtBird3.py` frägt den DHT22-Temperatursensor ab.
   
     
   
5. Ein *root-Passwort* erhältst Du mit `sudo passwd root`.

6. Als `root` füge am Ende von `/etc/fstab` folgende Zeilen ein:
````
# 50 MB ramdisk for /home/pi/station3/ramdisk:
tmpfs /home/pi/station3/ramdisk tmpfs defaults,size=50M,noatime,uid=1000,gid=1000,mode=0700 0 0
````
​      danach `systemctl daemon-reload`, dann zeigt `df -h`, dass `station3/ramdisk` jetzt als *Ramdisk* läuft.

​     *Nach `station3/ramdisk` schreiben alle Skripte ihre häufig wechselnden Betriebsdaten. Da das jetzt memory ist, wird die SD-Karte geschont.*

7. Start der Skripte:

   - in station3/ wird ein Link erstellt: `ln -s startup1stage.sh startup.sh`. Beim Aufruf von `./startup.sh` starten alle Programme, was aber eine Minute dauern kann. Das Ergebnis ist im Browser zu beobachten unter `http://<IP4>:8080` oder im Terminal mit `ps aux|grep pi`.

   - Programmstart beim Booten: `startup.sh` wird gestartet von `bird-startup.service`. Diese Datei aus `station3/docs/sysConfig` muss man als `root` nach `etc/systemd/system` kopieren, danach folgende Befehle:
   
     ````
     chown root:root bird-startup.service
     chmod 644 bird-startup.service
     systemctl enable bird-startup.service
     reboot
     sudo systemctl status bird-startup.service
     ````
   
     
   
8. Konfiguration eigener Werte:
   - Pi Crontab: `crontab crontab.txt`, verifizieren mit `crontab -l`
   - in `http://<IP4>:8080`(actions-settings-edit) oder `config.json` eigene `boxId` für die birdiary Plattform eintragen und rebooten.


**Fehlersuche**

- Startprobleme: schaue in `station3/logs` oder `dmesg` oder `journalctl -xeu NetworkManager` oder `sudo systemd-analyze blame`.
- Wifi Probleme: Hardware, Reichweite

**Optionale Optimierungen**

- WLAN Powersave und IP6 in NetworkManager/Netplan deaktivieren: 

  - `nano /etc/NetworkManager/conf.d/wifi-powersave.conf` trage ein:
    `````
    [connection]
    wifi.powersave = 2
    ````
    
  - `nano /etc/NetworkManager/conf.d/no-ipv6.conf` trage ein:    
    ````
    [connection]
    ipv6.method = disabled
    ````
   - `systemctl restart NetworkManager`

   Verifizieren mit `iw dev wlan0 get power_save` bzw. `ip a | grep inet6`.

- regelmässig aus pi crontab: `update-system.sh` und `update-fromGit.sh`. Letzteres erfordert ein Github-Setup in `home/pi`, das  von `https://github.com/herbbetz/betzBirdiary` nur `station3 ohne ramdisk/, logs/, debug/ u.a.` aktualisiert.

- bei `boot`abschalten:  `sudo systemctl disable bluetooth`(Bluetooth), `sudo systemctl disable alsa-restore alsa-state`(Sound), `sudo systemctl disable cups cups-browsed`(Drucker), `sudo systemctl disable ModemManager`(Mobilfunk).

- das braucht man sicher nicht: `sudo apt remove cloud-init`