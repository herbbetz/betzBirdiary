<!--keywords[Autofokus,picam2,RPi_cam_v3]-->

- RPiCam v3 hat einen Autofokus, der in der `picamera2 /mainFoBird3.py`  gesetzt wird mit `picam.set_controls()`. Für die RPiCams v1.3 und v2 werden diese Settings ignoriert.
- With boot `config.json` has the initial focus value (in cm = 100/dioptres), which `configBird3.py` conveys to `mainFoBird3.py (setFocus() and ms.setFocus()/vidmsg.json)` .
- in `vidshot3.html` is the `focus slider` initialized by `ramdisk/vidmsg.json`, which can change the focus (on being released) and by `flaskBird3.py` refers this back to `vidmsg.json` and `mainFoBird3.py`, which in turn applies it in it's loop and writes it back to `config.json` on shutdown. 
