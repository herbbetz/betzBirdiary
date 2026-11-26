<!--keywords[Autofokus,picam2,RPi_cam_v3]-->

- RPiCam v3 hat einen Autofokus, der in der `picamera2 /mainFoBird3.py`  gesetzt wird mit `picam.set_controls()`. Für die RPiCams v1.3 und v2 ist dies nötig: `if "AfMode" not in picam.camera_controls:`.
- With boot `config.json` has the initial focus value (in cm = 100/dioptres), which `configBird3.py` conveys to `mainFoBird3.py (setFocus() and ms.setFocus()/vidmsg.json)` .
- in `vidshot3.html` is the `focus slider` initialized by `ramdisk/vidmsg.json`, which can change the focus (on being released) and by `flaskBird3.py` refers this back to `vidmsg.json` and `mainFoBird3.py`, which in turn applies it in it's loop and writes it back to `config.json` on shutdown. 
- Das Kommando `rpicam-hello --list-cameras` zeigt den Kameratyp.
- Umstellung von RPiCam v1.3 auf RPiCam v3 (Autofocus):
  - 3D-Halterung, Kabel zur Kamera und Vogelhaus sind gleich für RPiCam v1.3 und v3 .
  - Der größere Sensor in v3 bedingt einen horizontalen `4/3 crop` (kleinerer Bildausschnitt der Vogelsitzstange), der in Python ausgeglichen wird. Die Videodatei ist unter v3 etwa 1.3fach größer als unter v1 . Über der Sitzstange bleiben mit v3 60% Freiraum versus früher 70% mit v1.3 . Die Sitzstange muss also gekürzt werden um 1,2 cm.
