<!--keywords[DHCP,ethernet,nmcli,nmtui,LAN,Netplan,NetworkManager,Trixie,WLAN,wpa_supplicant,WPS]-->

In diesem Verzeichnis finden sich Skripte und Befehle zum Einbinden der Vogelstation ins Heimnetz. In `bookworm` erfolgt das über den `NetworkManager` und seine Werkzeuge `nmcli` und `nmtui`  (auch Desktop GUI Frontends).

- Anschluss an neues Wifi /Heim-WLAN nach Verbindung über Netzwerkkabel mit folgenden Konsolenbefehlen:

  - `sudo nmcli dev wifi connect "SSID" password "PASSWORD"`

  - innerhalb 2 min nach Drücken der WPS-Taste am Heimrouter: `sudo nmcli dev wifi connect "SSID" wps-pbc`

  - Diese Verbindungen macht `NetworkManager` automatisch permanent. Danach reicht ein `sudo systemctl restart NetworkManager`. Da die Verbindung über Netzkabel besteht, bleibt die Konsolenverbindung erhalten. Lediglich müsste im Router jetzt die WLAN-Verbindung auftauchen. Danach ist das Netzkabel entbehrlich.

Trixie hat hier wieder eine Besonderheit: es verwendet sowohl `netplan` wie `NetworkManager`:

`nmcli -f NAME,FILENAME connection show` zeigt, dass LAN in `/run/NetworkManager/system-connections/` läuft, statt in `/etc/NetworkManager/system-connections/`. In `/run/...`  und `/etc/netplan` landen dann auch mit `nmcli` neu angelegte Connections.

- siehe `/etc/netplan/90-NM-2aff47d5-2705-3876-926e-79651215340b.yaml`

- die LAN-Verbindung kann erfolgreich sein während `boot`, aber nicht bei `hotplugging`.

- die neuen Einstellungen werden ohne reboot aktiv durch `systemctl restart NetworkManager`, vielleicht auch durch `netplan apply`.

    