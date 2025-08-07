<!--keywords[Tasmota]-->

Ich habe der betzBirdiary Vogelstation eine smarte Steckdose mit Tasmota Firmware (Marke 'Nous') vorgeschaltet.

- '*http://192.168.178.50/cm?cmnd=Backlog%20Delay%201200%3BPower%20off*' in tasmotaDown.sh schaltet nach 120 sec die Steckdose aus. *%20* steht für Leerzeichen in dem Tasmota Skript, das auf '*cm?cmnd=*' folgt. Dieser REST Befehl funktioniert auch aus der Browser Adresszeile.
- der Steckdose kann auf der Tasmota Konsole auch ein mDNS Name gegeben werden mit '*Hostname birdplug*'. Statt mit *192.168.178.50* kann sie dann im Browser mit *birdplug/* aufgerufen werden. In tasmotaDown.sh oder Browser funktioniert dann auch '*http://birdplug/cm?cmnd=Backlog%20Delay%201200%3BPower%20off*'.
- weitere Parameter zum Einstellen in der Tasmota Konsole sind:
	- deutsche Sommerzeit und Zeitserver
	- eigene Geolocation

ein kombiniertes Kommando auf der Tasmota Konsole für Lokalzeit in Landshut: 
*Backlog Timezone 99; TimeDST 0,1,3,1,2,120; TimeSTD 0,1,10,1,3,60; NtpServer1 ptbtime1.ptb.de; Latitude 48.5335086; Longitude 12.1350147*

'*status 7*' frägt diese Parameter dort ab.