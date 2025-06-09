Die Legacy 'picamera' Software ist nicht mehr in aktuellen Versionen von Raspian Bullseye (Debian 11) oder Bookworm (Debian 12) installiert. Sie kann aber mit 'sudo apt-get python3-picamera' dort nachinstalliert werden. Dann muss sie aber in 'raspi-config' bzw. in boot/config.txt mit 'gpu_mem=256' aktiviert werden. Diese Aktivierung stört wiederum die jetzt vorinstallierte 'picamera2'.

Diese Legacy picamera war Grundlage des Originalcodes der Uni Münster vom April 2023.

Insgesamt war die Legacy 'picamera' Software handlicher und für das Vogelprojekt ausreichend. Die Rotation der Kamerabildes ist jetzt bei 'picamera2' nicht mehr um 90° möglich, sondern nur noch der horizontale oder vertikale Flip. Ich musste die Kamera im Vogelhaus deshalb umbauen. Auch die Dashcam Funktion (CircularOutput()) mit überschreibender Videospeicherung der Sekunden vor der Triggerung verlief mit Legacy picamera überzeugender.

Da ich aber nicht weiß, ob sich noch jemand um die Pflege dieser älteren Software kümmert, habe ich mich auf die neue 'picamera2' konzentriert.



