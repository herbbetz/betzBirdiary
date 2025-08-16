<!--keywords[balenaEtcher,Flashen,pishrink,Raspbian_Image,WLAN-Konfig]-->
## Installation des Image

Das Image der Vogelhaussoftware enthält das ganze Raspbian OS mit allen Softwarekomponenten. 
- Das Raspbian Image 'birdDatum.img' wird z.B. mit '[balenaEtcher](https://etcher.balena.io/)' auf eine SD-Karte geflasht. 

- Dort kann die Bootpartition aufgrund ihres fat32-Formates unter allen Betriebssystemen gelesen werden. Unter Linux ist  nicht nur das bootfs, sondern auch das rootfs editierbar (vom User 'root'). Früher unter Raspian 'bullseye' wurde in bootfs 'ssh' (leere Datei) und 'wpa_supplicant' mit den eigenen WLAN-Schlüsseln eingetragen. Das neue Raspbian 'bookworm' arbeitet jedoch mit 'NetworkManager' und wird anders ins Heim-WLAN gebracht.

- In 'bookworm' ist das betzBirdiary als WLAN Hotspot (access point) konfiguriert mit IP '192.168.4.1' und dem Passwort 'bird24root'. Der Zugang entsteht nach WLAN-Verbindung mit 'bird-ap-dhcp'. 'ping 192.168.4.1' zeigt den Erfolg. Einloggen mit 'ssh pi@192.168.4.1'.

- Der folgende Prozess wird automatisch durch das Skript mit dem Kommando **sudo ./wlan-dialog.sh** (copy-paste aus vorbereiteter Textdatei) oder **sudo ./wlan-yaml.sh** (nach Eintragen der eigenen WLAN Parameter in **wlan.yml**) erledigt:

  In 'bird-static210.nmconnection' die Werte des eigenen Heimnetzwerkes eintragen (statische IP4, ssid=WLANname, psk=Passwort) und 'autoconnect=true'  und 'autoconnect-priority=100' setzen. Dabei verschwindet ein 'autoconnect=false' Parameter, weil fehlendes 'autoconnect' den Defaultwert 'true' bedeutet. Da auch bird-ap-dhcp.nmconnection kein 'autoconnect' also 'true' und keine 'autoconnect-priority' also default '0' beinhaltet, dient es für 'After=network-online.target, Wants=network-online.target' in 'bird-startup.service' als 'wifi failover priority fallback'. Der Hotspot 'bird-ap-dhcp' springt ein, wenn das WLAN von 'bird-static210' nicht zustande kommt. Ohne dieses failover hängt der Bootprocess an dem strikten 'After=network-online.target' in 'bird-startup.service' . Der Hotspot 'bird-ap-dhcp' hat keinen Internetzugang, weshalb DNS-Suche in 'startup1stage.sh' oder 'birdiary upload' nicht erfolgreich sind (selbst bei gültigen Werten in 'config.json'). 'systemctl status wpa_supplicant' läuft unter der Haube von NetworkManager.

  Alternativ kann auch die SD-Karte an einem Linux-Laptop gemountet werden, um als user 'root' in '.../rootfs/etc/NetworkManager/system-connections/bird-static210.nmconnection' diese Werte über ein 'nmcli' Kommando oder manuell einzutragen.

- Danach den Raspberry mit der SD-Karte hochfahren und **Login mit pi/bird24** (su mit 'bird24root').

-  Mit putty/ssh die eigenen Schlüssel für Station bzw. Whatsapp in 'config.json' eintragen, jeweils dort wo 'XXXXXXXX' steht. Alternativ herunterladen der Dateien mit WinSCP/Filezilla, am PC bearbeiten, wieder hochladen.

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

- ein Image, das zuvor nicht expandiert war ('raspi-config --expand-rootfs'), kann manchmal mit pishrink.sh nicht weiter verkleinert werden, wobei das Skript dann auch den abschließenden 'unallocated space' belässt. 'gparted betzBirdXXX.img' zeigt den 'unallocated space' und 'fdisk -l betzBirdXXX.img' zeigt sowas wie 'units sectors: 512, disklabel type: dos, betzBirdXXX.img2 end: 776544'. Bei dos (MBR) den 'unallocated space' entfernen nach der Formel `(end + 1) * sectorunits`, im Beispiel `truncate -s $((776545 * 512)) betzBirdXXX.img`.

  Bei 'disklabel type: gpt' bräuchte man zusätzlich noch `sgdisk -e betzBirdXXX.img # relocate the backup GPT table to the new end`.

- optional für Weitergabe Komprimieren von Image und Anweisungen z.B. mit 7-Zip und Hochladen in die Cloud.

- Restaurieren der SD-Karte, siehe obige 'Installation des Image' ab dem zweiten Punkt.