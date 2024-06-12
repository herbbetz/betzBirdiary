How to debug some issues I had with station2:

- station shutting down:
     internetTest2.sh shuts down after 3 minutes of bad internet connection, see logs/internet.log and type 'mail' on next terminal login.
- weight constantly over 40 or unexplained weight swings leading to unwanted video capturing /upload:
    double check the wiring of balance strain gauge to hx711 unit, as the thin leads can become disconnected easily.
    recalibrate offset automatically using calibHxOffset.py or manually using calibrateHx711.py, while hxFiBird.py is not active.
- weight measurement freezes on one fixed value that is no longer dependant on balance:
    two processes talked to the same GPIO, e.g. running hx711Test.py or calibrateHx711.py, while hxFiBird.py is active (and constantly being restarted by startupNoTest.sh)
- error 'OLD_img', image stream view in browser no longer updating: mainXXBird.py failure, see logs/main.log and 'ps aux|grep pi'
- http://IP4:8080/viddata.html shows viddata (main JSON data) instead of image, used for debugging
- http://IP4:8080/upload fakes an empty bird video, used for debugging
- If you built in your camera sideways, you cannot get the sky to the top by the flip options of picamera2. Instead use the legacy picamera, which can rotate its view.

further hints also in docs/howto.txt