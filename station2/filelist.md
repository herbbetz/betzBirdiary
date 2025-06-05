## Dateien in 'station2'

### Konfiguration und persönliche Schlüssel

Trage Deine persönlichen Schlüssel dort ein, wo Du in den Dateien einen Ausdruck mit 8x am Ende findest: "....xxxx xxxx"

- configBird2.py: zentrale Konfigurationsdatei, hier die eigene 'stationId' von Birdiary eintragen.
- mdroid.sh: zentrales Bashskript für die Kommunikation nach außen, zu Whatsapp, Makrodroid (Automatisierung auf Android Phones), auch MQTT wäre denkbar...
- crontab.txt (im passendem Format) kann in pi's crontab importiert werden mit dem Terminalkommando 'crontab crontab.txt' . Sicherung durch 'crontab -l > oldcrontab.txt' und Merge durch 'cat crontab1.txt crontab2.txt > crontab.txt' . 

### Hochfahren, Überwachung und Runterfahren

- startup.sh und seine Varianten (startupTest.sh, startupNoTest.sh): startet die Pythonskripte sowie auch Bashskripte für Monitoring. Gib ein 'less startup.sh' oder 'ps aux' zum Betrachten der geladenen Skripte.
- die crontab von User 'pi' startet solche Skripte ebenfalls. Gib ein das Kommando 'crontab -l' (für -list).
- test_crontab.sh testet die Funktionsfähigkeit der Kommandos in crontab (Vorsicht: auch Kommandos zum Herunterfahren)
- diskAlert.sh testet anfangs auf volle SD-Karte.
- internetTest2.sh fährt herunter, wenn die Internetverbindung ausfällt.
- sysMon.sh überträgt Systemdaten an das Webinterface.
- sunset2.py fährt herunter bei Sonnenuntergang. Pythonmodul 'ephem' muss dazu installiert sein und die eigenen Ortskoordinaten gehören in das Skript eingetragen: 'sudo apt-get install python3-ephem'. (pip wird vermieden, zeigt apt-get installierte Module nicht immer an.)
- tasmotaDown.sh schickt eine REST-Botschaft (Browseradresse mit Parametern) an einen der Vogelstation vorgeschalteten Smart-Netzstecker mit Tasmota Firmware und schaltet ihn damit nach dem Shutdown des Raspberry aus. Die richtige lokale IP des Smartsteckers muss dazu in tasmotaDown.sh eingetragen sein.

### Wiegevorgang über Dehnmesstreifen, Umweltdaten hochladen

- hxFiBirdStart.sh ist ein Shellskript das die folgenden zwei Skripte startet.
- calibHxOffset.py macht eine vorläufige Kalibrierung der Waage.
- hxFiBird.py liest die Wiegewerte und ab einem dort eingetragenen Schwellenwert gibt es an mainFoBird2.py das Signal zur Videoaufnahme. Dieses Signal übermittelt es durch eine 'FIFO Pipe'. Anhand der Werte unterhalb der Schwelle kalibriert es die Waage nach, falls z.B. Sonne auf den Dehnmesstreifen einwirkt.
- dhtBird.py wird in regelmäßigen Abständen von crontab veranlasst, Temperatur- und Feuchtewerte auf die Birdiary Platform hochzuladen.
- dhtTest.py und hx711Test.py sind einfache Skripte, falls die entsprechende Hardware mal Probleme macht. Wie für die Kamera Hardware funktionieren solche Testskripte aber nur, wenn kein anderes Programm auf die Hardware zugreift, siehe Kommando 'ps aux'.

### Das Webinterface von rpibird:8080

- vidshot.html samt bird.css: Hauptseite des Webinterface von rpibird:8080 . Die angezeigten Daten und Bilder bekommt diese Seite vom Port 8080 des lokalen Webservers flaskBird.py. Die Adresse "rpibird" macht der 'avahi (bonjour) mDNS service' publik. (viddata.html dient zum Debuggen der JSON Daten.)
- config.html: Inhalt hinter dem "config/action" Button der Hauptseite .
- flaskBird.py ist der Webserver, von dem das Webinterface seine Infos als JSON bezieht. Der Endpunkt '/upload' (d.h. rpibird:8080/upload) löst über die oben erwähnte 'FIFO Pipe' ein Video aus unabhängig von der Sitzstange.
- msgBird.py, wo das JSON für den Webserver zusammengesetzt wird. Alle Skripte, deren Werte im Webinterface auftauchen, haben Funktionen von msgBird.py importiert im Format ms.function() .
- mainFoBird2.py ist das Hauptskript für **direkte** Aufnahme und Upload der Vogelvideos. Die '2' ist wegen Verwendung des vorinstallierten Moduls 'picamera2'. Es gibt auch noch ein älteres und einfacheres 'picamera' Modul, das aber extra installiert und in 'raspi-config' aktiviert werden muss.

- mainAckBird2.py: das alternative Hauptskript, bei dem jedes Vogelvideo vor dem Upload im Webinterface **erst gesichtet** wird (Ack für acknowledge).
- video.html: hier wird das Video aus mainAckBird2.py vor dem Upload im Webinterface gesichtet (nach Umwandlung zu .mp4 durch ffmpeg).
- keepBird.py und uploadBird.py führen die Optionen auf der Website video.html aus, nämlich das Video selbst zu behalten oder auf Birdiary hochzuladen oder zu verwerfen. video.html informiert dazu das jeweilige Skript über den Webserver flaskBird.py.




## Verzeichnisse in 'station2'

- /ramdisk: Für ein längeres Leben der SD-Karte ist gut, wenn station2/ramdisk im System tatsächlich als Ramdisk konfiguriert ist. Über dieses Memory des Raspberry laufen häufige Schreibprozesse von Bildern und JSON. Die Installation von station2 auf ein unvorbereitetes Raspbian empfehle ich nicht. SSD-Festplatte oder USB-Stick statt SD-Karte wäre weniger outdoor tauglich.

- Statistikpaket [/statist](statist/statsREADME.md)

- /pigpioBird: Pigpio Treiberskripte für die Platine der Dehnmesswaage (Hx711) und für den Temperatur-Feuchtemesser (DHT22). Das System startet dafür den Daemon "pigpiod", der die permissions regelt, dass auf die Hardware zugegriffen werden darf.

- /log Logdateien, meist in Form umgeleiteter Ausgaben der Skripte. Logrotation und automatische Löschung älterer Logs durch das System. Hier nicht aufgefangene Kommandozeilenausgaben von Skripten (stdout, stderr) sieht man mit dem Kommando 'mail'.

- /keep eine von configbird.html (s.o.) referenzierte HTML-Seite für Videos, deren gallery.js auch eigene Einträge erlaubt. Verweigert die Birdiary Plattform das Hochladen, werden die Videos hier konserviert.

- /mybirds eine von configbird.html (s.o.) referenzierte HTML-seite für Vogelbilder, deren species.js eigene Einträge erlaubt.

- /wav beinhaltet nur eine Audiodatei ohne Inhalt, die von der Birdiary Plattform verlangt wird.

- /picamera beinhaltet Dateien der alten (einfacheren aber genügenden) Version, die nachistalliert werden müsste mit 'sudo apt-get python3-picamera' und Aktivierung in /boot/config.txt (raspi-config) benötigt.