## Installation des Image

Das Image der Vogelhaussoftware enthält das ganze Raspbian OS mit allen Softwarekomponenten. 
-  Das Raspbian Image 'birdDatum.img' wird z.B. mit '[balenaEtcher](https://etcher.balena.io/)' auf eine SD-Karte geflasht. 
-  Dort kann die Bootpartition aufgrund ihres fat32-Formates unter allen Betriebssystemen gelesen und im Hauptverzeichnis mit den Dateien 'ssh' (leere Datei) und 'wpa_supplicant' versehen werden. Zuvor werden in 'wpa_supplicant' noch die eigenen WLAN-Schlüssel eingetragen.
-  Danach den Raspberry mit der SD-Karte hochfahren und **Login mit pi/bird24** (su mit 'bird24root').
-  Mit putty/ssh die eigenen Schlüssel für Station bzw. Whatsapp in 'configBird2.py' und 'mdroid.sh' eintragen, jeweils dort wo 'XXXXXXXX' steht. Alternativ herunterladen der Dateien mit WinSCP/Filezilla, am PC bearbeiten, wieder hochladen.

Man kann 'dhcpcd.conf' auf die statische IP '192.168.178.210' konfigurieren, also auf das Netzwerk des eigenen Fritzbox Routers. Das Webinterface der Vogelstation ist dann erreichbar unter 'http://192.168.178.210:8080' oder 'rpibird:8080'. Auch putty/ssh bzw. WinSCP/Filezilla finden die Station dann unter '192.168.178.210'.

## Bau des Image aus der Vogelhaussoftware

- mache ein 'sudo apt update && sudo apt upgrade', reboote und teste, ob Deine Station noch funktioniert.
- optionale Anonymisierung für Weitergabe des Image: bei laufender Station die eigenen Schlüssel entfernen aus 'configBird2.py' und 'mdroid.sh' . Optional auch Umstellung der 'etc/dhcpcd.conf' von statischer IP auf DHCP. Die '/etc/wpa_supplicant/wpa_supplicant.conf' enthält keine missbrauchbaren Daten.
- Shutdown des Raspbian der Vogelstation und Entnehmen der SD-Karte.
- Einlesen der SD-Karte in ein Image 'birdDatum.img' auf dem PC mit Win32DiskImager (Windows 10/11) oder z.B. 'dd bs=4M if=/dev/sde of=birdDatum.img status=progress && sync' (Linux). Das dauert 15 bis 30 min.
- Schrumpfen des Image mit dem Linuxskript '[pishrink](pishrink.md)', unter Windows für Docker Desktop erhältlich als 'borgesnotes/pishrink:latest' .
- optional für Weitergabe Komprimieren von Image und Anweisungen z.B. mit 7-Zip und Hochladen in die Cloud.
- Restaurieren der SD-Karte, siehe obige 'Installation des Image' ab dem zweiten Punkt.