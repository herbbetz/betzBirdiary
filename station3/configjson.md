<!--keywords[API-keys,config.json,Einstellungen,Konfiguration,Settings]-->

Folgende Werte können in *config.json* an die eigene Station angepasst werden. Die Werte erscheinen auf dem Webinterface unter 'actions - settings'.

- "serverUrl": "https://wiediversistmeingarten.org/api/",  birdiary Plattform, dorthin werden die Vogelvideos hochgeladen.

- "boxId": "87bab185-7630-461c-85e6-c04cXXXXXXXX", diese ID wurde Deiner Vogelstation bei der Anmeldung zur birdiary Plattform zugeteilt.

- "upmaxcnt": 10, die Zahl der Vogelvideos ist auf zehn beschränkt. Danach fährt die Vogelstation herunter.

- "videodurate": 10, jedes Vogelvideo wird 10 Sekunden lang aufgenommen (ohne Dashcam Vorspann).

- "hflip_val": 1,  "vflip_val": 1, die Kamera ist so eingebaut, dass das Bild horizontal und vertikal seitenvertauscht ist.

- "vidsize": [1280, 960],   "losize": [320, 240], das Bildformat der Kamera ist 1280x960 Pixel, 320x240 Pixel für spezielle Aufnahmen.

- "luxThreshold": [1000, 2000, 4000], setzt die Kamerabelichtung in 4 Stufen: 'dark' unter 1000, 'dim' unter 2000, 'normal' unter 4000 und 'bright' über 4000. 'Indoor' sind die Schwellen anders als 'outdoor'.

- "luxLimit": [1000, 7000], Minimum und Maximum von `exposure * gain`. Obwohl die Autoregulation von picamera2 meist gute Belichtung reguliert, muss sie manchmal resettet werden.

- "weightlimit": 300,  "weightThreshold": 5, die Sitzstangenwaage löst ab 5 Gramm ein Video aus, aber nicht mehr über 300 Gramm.

- "hxScale": 546,   "hxOffset": -168307, diese Eichwerte setzen die Sitzstangenwaage auf 0 g (offset) und passen die Skala (scale) an die Grammschritte an. Die Waage der eigenen Station kann mit 'calibrateHx711v2.py' kalibriert werden.

- "dhtPin": 16, "hxDataPin": 17, "hxClckPin": 23, BCM GPIO Pins, der DHT22-Temperatursensor sitzt an GPIO16, der hx711-Wägezellen-ADC an Pin 17 und 23.

- "mdroid_key": "f9d9d0d0-f205-4ce2-a2d6-5875XXXXXXXX", API-Key (mdroid.sh) der Android App 'MacroDroid', deren Webhook hier als Messenger dient.

- "wapp_key": "25XXXXXXXX", "wapp_phone": "4987163XXXXXXXX", API-Key und Telefonnummer für WhatsApp 'callmebot' (mdroid.sh).

- "tasmota_ip": "192.168.178.50", die Tasmota-Smartsteckdose (Marke 'Nous') startet mit ihrem Timer die Vogelstation bzw. schaltet sie nach dem Shutdown stromlos (tasmotaDown.sh) und misst ihren Stromverbrauch.

  

  Bei 'XXXXXXXX' setze Deine eigenen Werte ein.

  Zum Einrichten von Messengern (MacroDroid, Whatsapp) für die Vogelstation siehe [hier](docs/messenger/whatsapp.md).