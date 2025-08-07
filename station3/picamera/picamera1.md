<!--keywords[Historie,legacy_picam, picamera1,Dashcam,Rotation]-->

Die Legacy 'picamera' Software ist nicht mehr in aktuellen Versionen von Raspian Bullseye (Debian 11) oder Bookworm (Debian 12) installiert. Sie kann aber mit 'sudo apt-get python3-picamera' dort nachinstalliert werden. Dann muss sie aber in 'raspi-config' bzw. in boot/config.txt mit 'gpu_mem=256' aktiviert werden. Diese Aktivierung stört wiederum die jetzt vorinstallierte 'picamera2'.

Diese Legacy picamera war Grundlage des Originalcodes der Uni Münster vom April 2023.

Insgesamt war die Legacy 'picamera' Software handlicher und für das Vogelprojekt ausreichend. Die Rotation der Kamerabildes ist jetzt bei 'picamera2' nicht mehr um 90° möglich, sondern nur noch der horizontale oder vertikale Flip. Ich musste die Kamera im Vogelhaus deshalb umbauen.

Die Dashcam Funktion (CircularOutput()) mit überschreibender Videospeicherung der Sekunden vor dem FIFO Trigger (Sitzstange) verlief mit 'legacy picamera' problemlos. Da war es kein Problem, das h264 Dashcam Video (pre-trigger) mit dem h264 post-trigger Video hintereinander in **dasselbe** File/ioMem zu schreiben. 'picamera2' benötigt für einen key-frame stimmigen Merge dieser beiden h264 Videos offenbar 'ffmpeg'. Vielleicht wäre es bei MJPEG Videos einfacher. Selbst Github Copilot schaffte es bei h264 mit picamera2 nicht, den CircularOutput vor das getriggerte Video keyframe-stimmig anzubauen und dann auch noch in einem ioBuffer zu speichern. Ich gab die pre-trigger Dashcam Funktion mit 'picamera2' deshalb auf.

Da ich aber nicht weiß, ob sich noch jemand um die Pflege von 'legacy picamera' kümmert, habe ich mich dennoch auf die neue 'picamera2' konzentriert.



