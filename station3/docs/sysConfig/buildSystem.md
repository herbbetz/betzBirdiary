<!--keywords[Bash,Bookworm,crontab,FFMPEG,GPIO,lgpio,logrotate,Markdown,mDNS,Network,Ramdisk,Startup,service,Systembuild,Trixie,venv,WLAN]-->

### Installation von betzBirdiary auf Bookworm & Trixie

- Raspian OS "Bookworm" (Debian 12) bzw. "Trixie" (Debian 13) verspricht die aktuellste Unterstützung von Pythonmodul "picamera2". Version siehe 'apt show python3-picamera2', oder 'pip show picamera2'.
- Installation von "bookworm light 64bit" mit "Raspberry Pi Imager" (*pi/bird24* Passwort, Fat32 Bootpartition mit ssh und wpa_supplicant.conf versehen), hochfahren und im Heimnetz suchen (DHCP). Sollte zumindest im LAN konnektieren.
- Login von `public-key` auf Passwort umstellen in `etc/ssh/sshd.conf` und `rm .ssh/autorized_keys`. (Trixie)
- putty/ssh bzw. WinSCP/Filezilla, 'sudo passwd root' ("*bird24root*""), 'sudo apt update && sudo apt full-upgrade' 🕦= *takes time*
- static IP (192.168.178.210), mit **NetworkManager** (default on fst boot, nmtui/nmcli, wpa_supplicant service) **oder** 'systemd-networkd' **oder** '/etc/network/interfaces (dhcdcp.conf)'. 'rpibird' als hostname. IPv6 can be disabled for wlan0. In nmtui benannte ich meine statische IP configuration mit 'bird-static210' ('nmcli connection show'). Later reset to DHCP Hotspot, before you produce an OS image for distribution to others (and remove credentials from config.json), see [buildimg](../buildimg/buildimg.md).
- prevent wlan0 sleeping mode: 'sudo nmcli connection modify static210 802-11-wireless.powersave 2' oder in '/etc/NetworkManager/conf.d/disable-powersave.conf', verifiziere mit 'iw wlan0 get power_save'
- I also disable bluetooth by blacklisting its modules from loading. Or `systemctl disable bluetooth`.
- mDNS (avahi, bonjour): 'ping rpibird' statt 'ping 192.168.178.210' zeigt den Erfolg. 'rpibird' eintragen in /etc/hosts und /etc/hostname.
- für user 'pi':
	- mail for 'local only'(rpibird.local): 'sudo apt install mailutils -y', 'sudo dpkg-reconfigure exim4-config', 'sudo usermod -a -G mail pi' ('groups pi' then includes group 'mail')
	- crontab: 'crontab yourcrontab.txt' . Siehe auch 'test_crontab.sh'.
	- ramdisk: in /etc/fstab "tmpfs /home/pi/station3/ramdisk tmpfs defaults,size=50M,noatime,uid=1000,gid=1000,mode=0700 0 0", see 'df -h /home/pi/station3/ramdisk'
	- [logrotate](https://linuxconfig.org/logrotate): mit /etc/logrotate.d/birdlogrotate werden von cron.daily /home/pi/station3/logs/\*.log die angefallenen Logfiles aufgeräumt ('logrotate -d /etc/logrotate.conf'). Dazu wird in `/etc/logrotate.d` die Datei `birdlogrotate` abgelegt. Kein Eintrag in `pi crontab`, da Link in  `/etc/systemd/system/multi-user.target.wants` das aktiviert, siehe `systemctl status cron`.

'/var/log/syslog' wurde in bookworm ersetzt durch journalctl (systemd-journald). 'journalctl' wird konfiguriert in '/etc/systemd/journald.conf' und ist unabhängig von logrotate.

- 'sudo apt install ffmpeg' für 'ffmpeg -i input_video.mjpeg -c:v copy output_video.avi'

- 'sudo apt install dnsutils' for diagnostics of delay issues on booting (getent).

- 'sudo apt install -y mosquitto-clients' for 

  ````
  mosquitto_pub \
    -h mqtt.example.com \
    -p 1883 \
    -t birdiary/message \
    -m "Hello from Raspberry Pi"
  ````

  

- Markdown Doku:
	- Hier praktiziert:  keywords innerhalb Markdown in HTML comments verstecken.
	- Alternative: [Mkdocs](https://www.mkdocs.org/) (birdvenv) 'pip install mkdocs' , um die Markdown Doku durchsuchbar zu machen.
	
- Bash Shell:
	- .bashrc und bashrc.sh zur Konfiguration der Login Shell (ssh login 'pi/bird24').
	- 'config.sh' mit zentralen Variablen für die bash Skripte.
	- **systemd Services**: Besser als mit 'crontab' oder dem 'rc.local' (rc-local.service) wird mein 'startup.sh' über ein eigenes /etc/systemd/system/bird-startup.service ('systemctl enable bird-startup.service') gestartet, so dass es erst nach Aufbau des Netzwerkes abläuft. Auch das Startup der Programme ist seit bookworm hier besser aufgehoben als in einem Shellscript. Abhängigkeiten können festgelegt und Gruppen (.target) organisiert werden.
	- Bash Utilities: 'sudo apt-get install bc curl iperf jq screen'
	- das Systemmonitoring mit Anbindung an WebInterface: sysMon.sh, cpu5sec.sh, updateSysmonEvt.sh .
	
- C-Module:
	- 'sudo apt install libcamera-apps libcamera-apps-lite libcamera-dev python3-libcamera python3-kms++'
	- teste libcamera: `rpicam-still --list-cameras`, `rpicam-still -o test_image.jpg -t 2000 --shutter 10000 --gain 4.0 --awbgains 1.5,1.2`
	
- python:
	- 'sudo apt install libcap-dev python3-dev' nötig zur pip-Installation von Pythonmodulen mit C-Komponenten. Diese Buildtools können später wieder weg: 'sudo apt remove libcap-dev python3-dev' und 'sudo apt autoremove'.
	- `sudo apt install python3-picamera2`.
	- auch mit nur einer Python3 Version sollte 'venv' verwendet werden, u.a. wegen der requirements.txt
	- aus /station3 gib ein 'python3 -m venv birdvenv --system-site-packages' (bzw. 'deactivate'). '--system-site-packages' notwendig, weil mit  apt-get installierte Pakete (dpkg -l | grep python3-) gebraucht werden (libcamera, pykms).
	für libcamera nötig: /home/pi/station3/birdvenv/lib/python3.11/site-packages/libcamera_path.pth mit Inhalt "/usr/lib/python3/dist-packages", in Trixie nicht länger nötig.
	- aktiviere mit `source birdvenv/bin/activate` (`. birdvenv/bin/activate`).
	- innerhalb des birdvenv installiere alle Module mit 'pip' (venv beinhaltet pip) und update sie später dort mit 'pip install --upgrade'.
	- 'pip freeze > requirements.txt' listet dorthin alle im birdvenv installierten Module. Kann verwendet werden mit 'pip install -r requirements.txt' (anders als 'pip list > requirements.txt').
	- (birdvenv) 'pip3 install ephem flask markdown matplotlib' und 'apt install python3-picamera2' (aktueller als mit pip3), dann in bookworm 'pip3 uninstall numpy' wegen Inkompat. des "pip numpy" zu "apt picamera2". In Trixie: `pip uninstall types-flask-migrate types-seaborn`, "pip numpy" bleibt in Trixie.
	- um birdvenv nicht ständig zu überschreiben, wird es außerhalb station3 in /home/pi unter root betrieben, ebenso wie seine Begleiter ''/4venv' und 'activate_birdvenv.sh'. Letzteres aus der Kommandozeile sourcen ('.' oder 'source activate_venv.sh'), damit es nicht in einer Subshell ausgeführt und sofort wieder beendet wird. 'birdvenv activ' bedeutet 'echo $VIRTUAL_ENV' zeigt 'birdvenv' an.
	- andere 'apt installs': python3-ephem (sunset2.py), aber aktueller ist 'pip install ephem'
	- Tensorflow und TFlite seien mit 'pip3' aktueller als mit 'apt'. Im Feb.26 funktionierte nicht 'pip3 install tflite-runtime' (full tensorflow only needed for training). Es gab noch kein 'sudo apt python3-tensorflow' oder 'sudo pip3 install tflite-runtime' für aktuelles Python, wobei pip3 allgemein zu 'venv' verpflichtet. Auch 'sudo pip3 install --break-system-packages tensorflow' (--break-system-packages -> kein venv) war nicht mit Python 3.13 kompatibel (installierte sich, dann aber 'missing module imp'). Deshalb ist noch ein extra 'pyenv' nötig für paralleles Python 3.11, das die Tensorflow Skripte dann aufrufen. Zum Nutzen eines fertigen tflite Model braucht es kein Tensorflow, sondern nur 'tflite_runtime'. Das ist im Feb.26 aber nur für numpy<2 kompatibel, wieder ein Fall für pyenv. Erst wenn eine Debian-Version statt pip verwendet werden kann, ist sicher, dass alles an 'Trixie' angepasst ist, siehe `apt search python3 | grep -i tensorflow` oder `apt search tflite (or tensorflow)`.
	- Um mehrere Python Versionen unter Trixie laufen zu lassen gibt es 'pyenv': `curl https://pyenv.run | bash`, `pyenv --version`, `pyenv install 3.11.8`, `pyenv install --list`, `pyenv virtualenv 3.11.8 birdvenv` , `pyenv activate birdvenv`,  then within (birdvenv): `python -c "import tensorflow as tf; print(tf.__version__)"`und ` python -c "import tflite_runtime.interpreter as tflite; print('TFLite OK')"`. In dieser Umgebung funktioniert dann `pip install tensorflow tflite_runtime`. tflite_runtime ohne Tensorflow benötigt auch ein numpy < 2 (-> 1.26), das innerhalb (birdvenv) ausgewechselt werden muss.
	**Achtung**: Anders als das herkömmliche 'python venv' benützt 'pyenv' nicht das directory 'birdvenv/', sondern erzeugt selbst `/home/pi/.pyenv/versions/birdvenv/bin/python`.
	- Statt 'pyenv' wäre auch 'docker' möglich, aber schwergewichtiger.
	
- GPIO
	Für den GPIO Zugriff im Raspberry ist bei zeitkritischen Sensoren (bit banging) wie Hx711 oder Dht22 eine C-Schicht erforderlich, die mit Python (lgpio, pigpio) dann gesteuert wird. lgpio und pigpio können wiederum mit gpiozero abstrahiert werden, aber nur für einfache Geräte (LED, Motoren), nicht für Hx711 oder DHT.
	
- **[pigpio](https://abyz.me.uk/rpi/pigpio/examples.html)**:
	- Für RPi4 und älter immer noch die einfachste [C-Schicht](https://github.com/joan2937/pigpio) in Form des Daemon 'pigpiod'. Die direkte Hardware-Adressierung funktioniert jedoch nicht mehr ab RPi5, für das lgpio gebraucht wird.
	- 'apt list --installed | grep pigpio', 'sudo pigpiod' bzw. 'sudo killall pigpiod' .
	- pigpio-tools (bei laufendem pigpiod): pigs (e.g. 'pigs r 4' reads GPIO 4), pig2vcd .
	
- [**lgpio**](https://abyz.me.uk/lg/py_lgpio.html) >> wurde für station3 verwendet:
	- 'python3-lgpio' bereits installiert in system-site-packages.
	- ein 'lgpiod' ist unter bookworm nicht zu finden und auch nicht nötig.
	- siehe [Testskripte](../../lgpioBird/lgpio.md) für Hardware
	- hx711: station3/lgpioBird/HX711.py von ChatGPT abgeleitet (schnelles Timing!), alternativ: https://github.com/endail/hx711-rpi-py and https://pypi.org/project/hx711-rpi-py/
	- DHT22: https://abyz.me.uk/lg/examples.html#Python%20lgpio
	
- **gpiozero** als frontend to lgpio oder pigpio:
	- sources: https://gpiozero.readthedocs.io/en/stable/
	- für hx711 oder dht22 scheint es aber auf so hoher Abstraktionsebene nichts zu geben.
	- deprecated: https://pypi.org/project/hx711-gpiozero/ (pip install hx711-gpiozero, https://github.com/cyrusn/hx711_gpiozero -> falscher Ansatz laut issues)
	
- **andere**:
	- https://github.com/adafruit/Adafruit_CircuitPython_DHT, https://randomnerdtutorials.com/raspberry-pi-dht11-dht22-python/