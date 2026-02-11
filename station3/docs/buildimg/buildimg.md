<!--keywords[balenaEtcher,card_image_build,Flashen,Installation,pishrink,Raspbian_Image,WLAN-Konfig,WSL2]-->

## Installation des Image

Das Image der Vogelhaussoftware enthält das ganze Raspbian OS mit allen Softwarekomponenten. 
- Das Raspbian Image 'birdDatum.img' wird z.B. mit '[balenaEtcher](https://etcher.balena.io/)' auf eine SD-Karte geflasht. Unter Linux mit `lsblk` das Blockdevice `/dev/sdX` der gemounteten SD Card ermitteln, dann `dd if=betzBirdXXX.img of=/dev/sdX bs=4M status=progress && sync`, dann eject.

- Verwendet man den 'Raspberry Pi Imager', dann legt 'trixie' ein `/etc/NetworkManager/system-connections/preconfigured.nmconnection` aus den im Imager vorkonfigurierten WLAN-Daten an. Über Ethernetkabel ist 'trixie' immer erreichbar.

- Dort kann die Bootpartition aufgrund ihres fat32-Formates unter allen Betriebssystemen gelesen werden. Unter Linux ist  nicht nur das bootfs, sondern auch das rootfs editierbar (vom User 'root'). Früher unter Raspian 'bullseye' wurde in bootfs 'ssh' (leere Datei) und 'wpa_supplicant' mit den eigenen WLAN-Schlüsseln eingetragen. Das neue Raspbian 'bookworm' arbeitet jedoch mit 'NetworkManager' und wird anders ins Heim-WLAN gebracht.

- In 'bookworm' ist das betzBirdiary als WLAN Hotspot (access point) konfiguriert mit IP '192.168.4.1' und dem Passwort 'bird24root'. Der Zugang entsteht nach WLAN-Verbindung mit 'bird-ap-dhcp'. 'ping 192.168.4.1' zeigt den Erfolg. Einloggen mit 'ssh pi@192.168.4.1'.

- Android ssh clients mögen Hotspots ohne Internet nicht öffnen (Captive Portal Detection), z.B. Termius. Nicht getestet: JuiceSSH, ConnectBot.

- Der folgende Prozess wird automatisch durch das Skript mit dem Kommando **sudo ./wlan-dialog.sh** (copy-paste aus vorbereiteter Textdatei) oder **sudo ./wlan-yaml.sh** (nach Eintragen der eigenen WLAN Parameter in **wlan.yml**) erledigt:

  In 'bird-static210.nmconnection' die Werte des eigenen Heimnetzwerkes eintragen (statische IP4, ssid=WLANname, psk=Passwort) und 'autoconnect=true'  und 'autoconnect-priority=100' setzen. Dabei verschwindet ein 'autoconnect=false' Parameter, weil fehlendes 'autoconnect' den Defaultwert 'true' bedeutet. Da auch bird-ap-dhcp.nmconnection kein 'autoconnect' also 'true' und keine 'autoconnect-priority' also default '0' beinhaltet, dient es für 'After=network-online.target, Wants=network-online.target' in 'bird-startup.service' als 'wifi failover priority fallback'. Der Hotspot 'bird-ap-dhcp' springt ein, wenn das WLAN von 'bird-static210' nicht zustande kommt. Ohne dieses failover hängt der Bootprocess an dem strikten 'After=network-online.target' in 'bird-startup.service' . Der Hotspot 'bird-ap-dhcp' hat keinen Internetzugang, weshalb DNS-Suche in 'startup1stage.sh' oder 'birdiary upload' nicht erfolgreich sind (selbst bei gültigen Werten in 'config.json'). 'systemctl status wpa_supplicant' läuft unter der Haube von NetworkManager.

  Falls dies nicht funktioniert, kann auch ein eigenes WLAN-Profil mit nmtui erstellt werden (edit-add). Die autoconnect-priority muss dabei aber mit `nmcli con modify ...` oder `nano .nmconnection` gemacht werden. Meide WLAN-Passwörter mit Leerzeichen oder `\`.

  Alternativ kann auch die SD-Karte an einem Linux-Laptop gemountet werden, um als user 'root' in '.../rootfs/etc/NetworkManager/system-connections/bird-static210.nmconnection' diese Werte über ein 'nmcli' Kommando oder manuell einzutragen.

- Danach den Raspberry mit der SD-Karte hochfahren und **Login mit pi/bird24** (su mit 'bird24root').

-  Mit putty/ssh die eigenen Schlüssel für Station bzw. Whatsapp in 'config.json' eintragen, jeweils dort wo 'XXXXXXXX' steht. Alternativ herunterladen der Dateien mit WinSCP/Filezilla, am PC bearbeiten, wieder hochladen.

Man kann mit 'nmtui' oder 'dhcpcd.conf' die statische IP '192.168.178.210' konfigurieren, also auf das Netzwerk des eigenen Fritzbox Routers. Das Webinterface der Vogelstation ist dann erreichbar unter 'http://192.168.178.210:8080' oder 'rpibird.local:8080'. Auch putty/ssh bzw. WinSCP/Filezilla finden die Station dann unter '192.168.178.210'.

Zur Konfiguration der Station siehe [config.json](../../configjson.md).

## Bau des Disc Image zur Weitergabe

- mache ein `sudo apt update && sudo apt upgrade`.

- in 'birdvenv': `pip3 install --upgrade ephem flask markdown matplotlib` (getrennt mit spaces) und `pip3 uninstall numpy` (Inkompat. zu `apt install python3-picamera2` ).

- reboote und teste, ob Deine Station noch funktioniert.

- Anonymisierung für Weitergabe des Image: bei laufender Station die eigenen Schlüssel überschreiben ('XXXXXXXX') in 'config.json' .
  `sudo ./wlan-yaml.sh wlan.yml` (noch ohne reboot) und `./config-yaml.sh config.yml`.

- pi crontab deaktivieren (abendliche Shutdown Skripts): `crontab crontab4test.txt` und `crontab -l`.

- Umstellung von statischer IP auf AP-Hotspot mit nmcli.
  `sudo nmcli connection modify "bird-static210" connection.autoconnect-priority -100`,
  `sudo cat "/etc/NetworkManager/system-connections/bird-static210.nmconnection"`,
  teste nach reboot.
  Bei ungültigen WLAN-Daten in "bird-static210" sollte AP-Hotspot "bird-ap-dhcp" sich auch automatisch aktivieren.

- Shutdown des Raspbian der Vogelstation und Entnehmen der SD-Karte.

- Einlesen der SD-Karte in ein Image 'birdDatum.img' auf dem PC mit Win32DiskImager (Windows 10/11, "read only allocated partitions"!) dauert 5 min. 

  In Linux:

- `lsblk -o NAME,SIZE,TYPE,FSTYPE,MOUNTPOINT`
`sudo fdisk -l /dev/sdX`
`sudo dd if=/dev/sdX of=raw.img bs=512 count=$((END_rootfs+1)) status=progress
&& sync`(nicht `count=$(((END+1)*512))`, weil bereits `bs=512`). Betrachte mit `gparted raw.img`.
`sudo ./pishrink.sh -s 512 raw.img` Shrinks rootfs to its minimum + 512 MiB headroom. Bei -s wird nicht expandiert außer später mit `sudo raspi-config --expand-rootfs`.
`fdisk -l raw.img`
`truncate -s $(( (END_rootfs+1) * 512 )) raw.img`

- verifizieren des img unter Linux:

  `sudo losetup -fP raw.img` 	`-f` = find the next free loop device. `-P` = automatically scan and map the partitions inside the image.

  `lsblk` shows loop devices.

  `sudo fsck.ext4 -f /dev/loop0p2` checks and fixes rootfs. 

  (gparted macht eigenen 'check', aber nicht mit `gparted raw.img` sondern `gparted /dev/loopX`. Selbst dann scheitert es am bootfs, das es wohl versucht `to grow` , aber Raspbian eine fixierte und nicht ans filesystem angepasste partitionsize hat.)

  `sudo fsck.vfat -a /dev/loop0p1` same with bootfs.

  `sudo losetup -d /dev/loop0` detaches img.

  `xz -k -9v raw.img` (-k keeps raw.img, v mit Progressbar) , dauert 15 min auf altem 'Satellite C660 Toshiba Laptop'. xz Kompression kann von balena etcher oder RPiImager unter Win/Ubuntu direkt geflasht werden in 10 min. Unpack: `xz -dk raw.img.xz`. Vielleicht kann hohe Kompression (-9 oder -9e) dem balena etcher manchmal auch Probleme (Memoryverbrauch) machen.

- Schrumpfen des Image mit dem Linuxskript '[pishrink.sh](pishrink.md)', unter Windows ausführen auf WSL oder über Docker Desktop mit 'borgesnotes/pishrink:latest' . 

*'./pishrink.sh -s bird.img' verhindert Autoexpansion auf der SD-Karte und reduziert deren Abnutzung durch mehr Kartenplatz für den SD-Karten-Controller. Bei Platzbedarf auf der SD-Karte kann die Expansion dort nachgeholt werden durch 'raspi-config --expand-rootfs' oder besser dosiert durch parted/resize2fs.*

Ein Filesystemcheck vor pishrink.sh kann im hochgefahrenen Raspbian erreicht werden mit `sudo touch /forcefsck && sudo reboot`.

- `parted /dev/mmcblk0 resizepart 2` und anschließend `resize2fs /dev/mmcblk0p2` erweitern das rootfs dosiert. `fstab` muss nicht beachtet werden, da die `UUID` nicht verändert wird. Zuvor kann noch ein `lsblk` oder `parted /dev/mmcblk0 print free` die Übersicht herstellen und mit `df -h` das Vergrößern verifiziert werden.

- ein Image, das zuvor nicht expandiert war ('raspi-config --expand-rootfs'), kann manchmal mit pishrink.sh nicht weiter verkleinert werden, wobei das Skript dann auch den abschließenden 'unallocated space' belässt. 'gparted betzBirdXXX.img' zeigt den 'unallocated space' und `fdisk -l betzBirdXXX.img` zeigt sowas wie 'units sectors: 512, disklabel type: dos, betzBirdXXX.img2 end: 776544'. Bei dos (MBR) den 'unallocated space' entfernen nach der Formel `(end + 1) * sectorunits`, im Beispiel `truncate -s $((776545 * 512)) betzBirdXXX.img` oder von vornherein nur:

- `dd if=myraw.img of=final.img bs=512 count=$((END+1)) status=progress` (nicht `count=$(((END+1)*512))`, weil bereits `bs=512`).

- Bei 'disklabel type: gpt' bräuchte man zusätzlich noch `sgdisk -e betzBirdXXX.img # relocate the backup GPT table to the new end`.

- optional für Weitergabe Komprimieren von Image und Anweisungen z.B. mit 7-Zip und Hochladen in die Cloud.

- Restaurieren der SD-Karte, siehe obige 'Installation des Image' ab dem zweiten Punkt.

- Mounten einer SDcard als block device in Win11 WSL2 System **nur mit Powershell 5** (admin):

​	`Get-Disk` zeigt die disknumber der SD card, z.B. '4'
 	unmount von win drive 'H:' in Win Explorer oder `offline disk` in diskpart funktionieren nicht. Das geht wohl nur mit `Dismount-Volume`, was nur in 	**Powershell 5/Windows Pro**  verfügbar ist: `Get-Volume -DiskNumber 4 | Dismount-Volume -Force`.
  	`mount \\.\PHYSICALDRIVE4 --bare` macht device mount ins WSL.
​	Jetzt seien obige Befehle möglich in WSL Linux wie `fdisk -l`.
​	`wsl --unmount \\.\PHYSICALDRIVE4` später nach abgeschlossener Arbeit in WSL.

