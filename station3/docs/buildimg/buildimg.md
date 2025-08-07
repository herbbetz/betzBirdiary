<!--keywords[balenaEtcher,Flashen,pishrink,Raspbian_Image,WLAN-Konfig]-->
## Installation des Image

Das Image der Vogelhaussoftware enthält das ganze Raspbian OS mit allen Softwarekomponenten. 
-  Das Raspbian Image 'birdDatum.img' wird z.B. mit '[balenaEtcher](https://etcher.balena.io/)' auf eine SD-Karte geflasht. 
-  Dort kann die Bootpartition aufgrund ihres fat32-Formates unter allen Betriebssystemen gelesen werden. Unter Linux ist  nicht nur das bootfs, sondern auch das rootfs editierbar (vom User 'root'). Früher unter Raspian 'bullseye' wurde in bootfs 'ssh' (leere Datei) und 'wpa_supplicant' mit den eigenen WLAN-Schlüsseln eingetragen. Das neue Raspbian 'bookworm' arbeitet jedoch mit 'NetworkManager' und wird anders ins Heim-WLAN gebracht.
-  In 'bookworm' ist das betzBirdiary als WLAN Hotspot (access point) konfiguriert mit IP '192.168.4.1' und dem Passwort 'bird24root'. Der Zugang entsteht nach WLAN-Verbindung mit 'bird-ap-dhcp'. 'ping rpibird.local' zeigt den Erfolg. Nach 'ssh pi@rpibird.local' in '/etc/NetworkManager/system-connections/bird-ap-dhcp.nmconnection' das 'autoconnect=false' setzen. In 'bird-static210.nmconnection' dagegen die Werte des eigenen Heimnetzwerkes eintragen (passende IP4, ssid=WLANname, psk=Passwort) und 'autoconnect=true' setzen. Alternativ kann auch die SD-Karte an einem Linux-Laptop gemountet werden, um als user 'root' in '.../rootfs/etc/NetworkManager/system-connections/bird-ap-dhcp.nmconnection' diese Werte einzutragen. In einem .nmconnection für 'wlan0' muss 'autoconnect=true', in den anderen 'autoconnect=false' eingetragen sein.
-  Danach den Raspberry mit der SD-Karte hochfahren und **Login mit pi/bird24** (su mit 'bird24root').
-  Mit putty/ssh die eigenen Schlüssel für Station bzw. Whatsapp in 'configBird2.py' und 'mdroid.sh' eintragen, jeweils dort wo 'XXXXXXXX' steht. Alternativ herunterladen der Dateien mit WinSCP/Filezilla, am PC bearbeiten, wieder hochladen.

Man kann mit 'nmtui' oder 'dhcpcd.conf' die statische IP '192.168.178.210' konfigurieren, also auf das Netzwerk des eigenen Fritzbox Routers. Das Webinterface der Vogelstation ist dann erreichbar unter 'http://192.168.178.210:8080' oder 'rpibird.local:8080'. Auch putty/ssh bzw. WinSCP/Filezilla finden die Station dann unter '192.168.178.210'.

Zur Konfiguration der Station siehe [config.json](../../configjson.md).

## Bau des Image aus der Vogelhaussoftware

- mache ein 'sudo apt update && sudo apt upgrade', reboote und teste, ob Deine Station noch funktioniert.
- Anonymisierung für Weitergabe des Image: bei laufender Station die eigenen Schlüssel überschreiben ('XXXXXXXX') in 'config.json' .
- Umstellung von statischer IP auf AP-Hotspot in nmtui. 
- Shutdown des Raspbian der Vogelstation und Entnehmen der SD-Karte.
- Einlesen der SD-Karte in ein Image 'birdDatum.img' auf dem PC mit Win32DiskImager (Windows 10/11) oder z.B. 'dd bs=4M if=/dev/sde of=birdDatum.img status=progress && sync' (Linux). Einlesen, Kopieren und Schrumpfen der 32GB-Kartendaten und testweises Flashen dauert leicht eine Stunde.
- Schrumpfen des Image mit dem Linuxskript '[pishrink.sh](pishrink.md)', unter Windows ausführen auf WSL oder über Docker Desktop mit 'borgesnotes/pishrink:latest' . 

*'./pishrink.sh -s bird.img' verhindert Autoexpansion auf der SD-Karte und reduziert deren Abnutzung durch mehr Kartenplatz für den SD-Karten-Controller. Bei Platzbedarf auf der SD-Karte kann die Expansion dort nachgeholt werden durch 'raspi-config' oder parted.*

- optional für Weitergabe Komprimieren von Image und Anweisungen z.B. mit 7-Zip und Hochladen in die Cloud.
- Restaurieren der SD-Karte, siehe obige 'Installation des Image' ab dem zweiten Punkt.