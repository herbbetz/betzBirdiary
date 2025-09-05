<!--keywords[Konfiguration,Markdown,Startup,Tasmota,Whatsapp]-->

## Dateien in 'station3'

### Einstellmöglichkeiten der Software

- Herunterfahren nach zuviel Vogelvideos: configBird3.py (*upmaxcnt = 10*)
- Herunterfahren am Abend bzw. bei Sonnenuntergang: crontab (*... tasmotaDown.sh, ... sunset2.py*)
- Upload-Intervall für Umweltdaten: crontab (*... dhtBird.py*)
- Länge des einzelnen Vogelvideos: configBird3.py (*videodurate*)

### Konfiguration und persönliche Schlüssel

Trage Deine persönlichen Schlüssel dort ein, wo Du in den Dateien einen Ausdruck mit 8x am Ende findest: "....XXXXXXXX"

- configBird3.py: zentrale Konfigurationsdatei, hier die eigene 'stationId' von Birdiary eintragen.
- config.sh: zentrales Bashskript für die Kommunikation nach außen, zu Whatsapp, MacroDroid (Automatisierung auf Android Phones) oder Tasmota Smartplug. Auch MQTT wäre denkbar...
- crontab.txt (im passendem Format) kann in pi's crontab importiert werden mit dem Terminalkommando 'crontab crontab.txt' . Sicherung durch 'crontab -l > oldcrontab.txt' und Merge durch 'cat crontab1.txt crontab2.txt > crontab.txt' . 

### Hochfahren, Überwachung und Runterfahren

- startup.sh und seine Varianten (startup1stage.sh, startup2stage.sh): startet die Pythonskripte sowie auch Bashskripte für Monitoring. Gib ein 'less startup.sh' oder 'ps aux' zum Betrachten der geladenen Skripte. startup.sh wird beim Hochfahren gestartet von '/etc/birdconfig/bird-startup.service'. Siehe 'systemctl status bird-startup.service'. 

  startup.sh ist ein Softlink, der zum Debuggen auf startupNoInet.sh gesetzt wird. startup1stage.sh führt startupNoInet.sh und anschließend startup2stage.sh (Internet und Programme) aus. startup1stage.sh wird also nach dem Debugging über startup.sh verlinkt.

- die crontab von User 'pi' startet solche Skripte ebenfalls. Gib ein das Kommando 'crontab -l' (für -list).

- test_crontab.sh testet die Funktionsfähigkeit der Kommandos in crontab (Vorsicht: auch Kommandos zum Herunterfahren)

- diskAlert.sh testet anfangs auf volle SD-Karte.

- internetTest2.sh fährt herunter, wenn die Internetverbindung ausfällt.

- sysMon.sh überträgt Systemdaten an das Webinterface.

- sunset2.py fährt herunter bei Sonnenuntergang. Pythonmodul 'ephem' muss dazu installiert sein und die eigenen Ortskoordinaten gehören in das Skript eingetragen: 'sudo apt-get install python3-ephem'.

- pip Python Manager wird vermieden, zeigt apt-get installierte Module nicht immer an und erneuert Python Module nicht über 'apt-get update'.

- [tasmotaDown.sh](docs/tasmota/tasmota.md) schickt eine REST-Botschaft (Browseradresse mit Parametern) an einen der Vogelstation vorgeschalteten Smart-Netzstecker mit Tasmota Firmware und schaltet ihn damit nach dem Shutdown des Raspberry aus. Die richtige lokale IP des Smartsteckers muss dazu in config.sh eingetragen sein.

### Wiegevorgang über Dehnmesstreifen, Umweltdaten hochladen

- calibrateHx711v2.py dient zum Kalibrieren der Waage: Skript bei leerer Waage starten, auf Aufforderung Gewicht von etwa 100g an die Vogelsitzstange hängen, Werte tragen sich selbst in configBird3.py ein, dann reboot. Dieses Vollkalibrieren sollte nur selten nötig sein.
- hxFIBird3.py liest die Wiegewerte und ab einem dort eingetragenen Schwellenwert gibt es an mainFoBird3.py das Signal zur Videoaufnahme. Dieses Signal übermittelt es durch eine 'FIFO Pipe'. Anhand der Werte unterhalb der Schwelle kalibriert es die Waage nach, falls z.B. Sonne auf den Dehnmesstreifen einwirkt. Damit es von calibrateHx711v2.py automatisch beendet werden kann, schreibt es seine PID nach 'hxFiBird.txt' (Funktionen dazu in sharedBird.py).
- dhtBird.py wird in regelmäßigen Abständen von crontab veranlasst, Temperatur- und Feuchtewerte auf die Birdiary Platform hochzuladen.
- dhtTest.py und hx711Test.py sind einfache Skripte, falls die entsprechende Hardware mal Probleme macht. Wie für die Kamera Hardware funktionieren solche Testskripte aber nur, wenn kein anderes Programm auf die Hardware zugreift, siehe Kommando 'ps aux'.

### Das Webinterface von rpibird.local:8080

- vidshot.html samt bird.css: Hauptseite des Webinterface von rpibird.local:8080 . Die angezeigten Daten und Bilder bekommt diese Seite vom Port 8080 des lokalen Webservers flaskBird.py. Die Adresse "rpibird" macht der 'avahi (bonjour) mDNS service' publik. (viddata.html dient zum Debuggen der JSON Daten.)
- config.html: Inhalt hinter dem "config/action" Button der Hauptseite .
- flaskBird.py ist der Webserver, von dem das Webinterface seine Infos als JSON bezieht. Der Endpunkt '/upload' (d.h. rpibird.local:8080/upload) löst über die oben erwähnte 'FIFO Pipe' ein Video aus unabhängig von der Sitzstange.
- msgBird.py, wo das JSON für den Webserver zusammengesetzt wird. Alle Skripte, deren Werte im Webinterface auftauchen, haben Funktionen von msgBird.py importiert im Format ms.function() .
- mainFoBird3.py ist das Hauptskript für **direkte** Aufnahme und Upload der Vogelvideos. Die '2' ist wegen Verwendung des vorinstallierten Moduls 'picamera2', das leider [Komplikationen](picamera/picamera1.md) u.a. mit CircularBuffer macht. Es gibt auch noch ein älteres (legacy) und einfacheres 'picamera' Modul, das aber extra installiert und in 'raspi-config' aktiviert werden muss. 'picamera2' in mainFoBird3.py passt die Kamera per Code an das Tageslicht an (in 4 Stufen). `python3 mainFoBird3.py test` erzeugt ein Testvideo in /keep ohne Upload zur birdiary Plattform.
- sharedBird.py beinhaltet kleine Funktionen, die in mehreren Pythonskripten nützlich sind.

### Dokumentation
- flaskBird.py sorgt durch das Modul 'markdown' auch dafür, dass die Markdown Dokumentation als HTML im Webinterface sichtbar ist (rpibird.local:8080/README.md).
- content.md wird  erstellt mit 'build_md_contents.py', wenn entsprechende 'keywords[]' innerhalb HTML Kommentaren in die .md Dateien eingetragen wurden.
- Alternative für Inhaltsverzeichnis (nicht getestet): [Mkdocs](https://www.mkdocs.org/)
- /blog: index.md, about.md, _config.yml und /assets und /posts bilden einen Blog für Github auf Jekyll Basis.

### debugging, update and other tools
- test_crontab.sh: only tests for timed commands (after '* * * * *')
- test_fiforead.sh: FIFO reader for testing hxFiBird output.
- pip_upgrade.sh from within (birdvenv)


## Verzeichnisse in 'station3'

- /movements, /environments verwendet die originale Birdiary Software zum Speichern von Videodaten bzw. Umweltdaten vor dem Upload. Die API der Birdiary Plattform speichert diese später unter https://wiediversistmeingarten.org/api/[movement, environment]/[stationId].

- /ramdisk: Für ein längeres Leben der SD-Karte ist gut, wenn station2/ramdisk im System tatsächlich als Ramdisk konfiguriert ist. Über dieses Memory des Raspberry laufen häufige Schreibprozesse von Bildern und JSON. Die Installation von station2 auf ein unvorbereitetes Raspbian empfehle ich nicht. SSD-Festplatte oder USB-Stick statt SD-Karte wäre weniger outdoor tauglich.

- Statistikpaket [/statist](statist/doc/statsREADME.md)

- /pigpioBird: [Pigpio](https://abyz.me.uk/rpi/pigpio/examples.html) Treiberskripte für die Platine der Dehnmesswaage (Hx711) und für den Temperatur-Feuchtemesser (DHT22). Das System startet dafür den Daemon "pigpiod", der die permissions regelt, dass auf die Hardware zugegriffen werden darf.

- /log Logdateien, meist in Form umgeleiteter Ausgaben der Skripte. Logrotation und automatische Löschung älterer Logs durch das System. Hier nicht aufgefangene Kommandozeilenausgaben von Skripten (stdout, stderr) sieht man mit dem Kommando 'mail'.

- /keep eine von configbird.html (s.o.) referenzierte HTML-Seite für Videos, deren gallery.js auch eigene Einträge erlaubt. Verweigert die Birdiary Plattform das Hochladen, werden die Videos hier konserviert.

- /mybirds eine von configbird.html (s.o.) referenzierte HTML-seite für Vogelbilder, deren species.js eigene Einträge erlaubt.

- /wav beinhaltet nur eine Audiodatei ohne Inhalt, die von der Birdiary Plattform verlangt wird.

- /picamera beinhaltet Dateien der [alten Version](picamera/picamera1.md). Das neue picamera2 findet sich dagegen in [/camtest](camtest/picamera2.md)

- die [Acknowledge-Version](acknowledge/ackVersion.md) wird nicht mehr gepflegt und ihre Dateien sind in /acknowledge archiviert:

    - mainAckBird2.py: das alternative Hauptskript, bei dem jedes Vogelvideo vor dem Upload im Webinterface **erst gesichtet** wird (Ack für acknowledge).
    - video.html: hier wird das Video aus mainAckBird2.py vor dem Upload im Webinterface gesichtet (nach Umwandlung zu .mp4 durch ffmpeg).
    - keepBird.py und uploadBird.py führen die Optionen auf der Website video.html aus, nämlich das Video selbst zu behalten oder auf Birdiary hochzuladen oder zu verwerfen. video.html informiert dazu das jeweilige Skript über den Webserver flaskBird.py.

- /buildimg Installieren & Erstellen eines [Image](buildimg/buildimg.md) der Vogelhaus-Software.

- /docs: Dokumentation zu verschiedenen Themen:

	- /webGUI Über das Webinterface 'rpibird.local:8080' (s.o.)
	- /birdhouse Das [Vogelhaus](docs/birdhouse/birdhouse.md): Aufbau, Restaurierung, Modelle
	- /messenger Infos zu Kommunikation des Vogelhauses mit [Whatsapp](docs/messenger/whatsapp.md) oder MacroDroid.
	- /video Tipps zur [Bearbeitung](docs/video/videoHowto.md) der Vogelvideos.
	- /sysConfig einige Systemkonfig Dateien in Raspbian, z.B. zum Abschalten des WLAN-Energiesparmodus
	- /makingOf [Ableitung](docs/makingOf/ForkMakingof.md) von betzBirdiary aus dem station120423.img der Uni Münster.
	- /github Tricks für Github