<!--keywords[DHCP,nmcli,nmtui,NetworkManager,WLAN,wpa_supplicant,WPS]-->

In diesem Verzeichnis finden sich Skripte und Befehle zum Einbinden der Vogelstation ins Heimnetz. In `bookworm` erfolgt das über den `NetworkManager` und seine Werkzeuge `nmcli` und `nmtui`  (auch Desktop GUI Frontends).

- Anschluss an neues Wifi /Heim-WLAN nach Verbindung über Netzwerkkabel mit folgenden Konsolenbefehlen:

  - `sudo nmcli dev wifi connect "SSID" password "PASSWORD"`

  - innerhalb 2 min nach Drücken der WPS-Taste am Heimrouter: `sudo nmcli dev wifi connect "SSID" wps-pbc`

  - Diese Verbindungen macht `NetworkManager` automatisch permanent. Danach reicht ein `sudo systemctl restart NetworkManager`. Da die Verbindung über Netzkabel besteht, bleibt die Konsolenverbindung erhalten. Lediglich müsste im Router jetzt die WLAN-Verbindung auftauchen. Danach ist das Netzkabel entbehrlich.

    