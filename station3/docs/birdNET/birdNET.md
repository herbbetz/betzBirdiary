<!--keywords[birdNET, Cornell, Vogelstimmen]-->

Aktuelle "Nachtzuster" Codeversion von [BirdNET-PI](https://github.com/Nachtzuster/BirdNET-Pi) ist installierbar über dortiges `newinstaller.sh`.

- das **Webinterface** ist erreichbar unter `http://<IP4 des RPi>` mit dem Passwort `birdnet / <leer>`.
- Dort in `Tools-Settings` werden eingetragen: `Latitude (48,5335) / Longitude (12,1375)`, `BirdWeather Token` für `https://app.birdweather.com/stations/24979 (betzBirdNet)`, Zeitzone. All das landet in `~/BirdNET-Pi/birdnet.conf` (symlink `/etc/birdnet/birdnet.conf` von überall zugänglich).

​	In `-Advanced Settings`: eigenes BirdNet-Pi Passwort, Audio Settings samt RTSP-Audio-Source, ab welcher `Disk Usage` die Vogelaudios aus `~/BirdSongs` gelöscht werden.

​	Die Settings aus dem Webinterface werden gespeichert durch `scripts/config.php` bzw. `advanced.php` in `birdnet.conf`.  `service_controls.php` dagegen (de-)aktiviert verschiedene Services via `views.php`.

- **Installation**: `scripts/install_birdnet.sh` startet `install_config.sh` (->`birdnet.conf`) und `install_helpers.sh`. `systemd services` werden installiert durch `scripts/install_services.sh`.

- **WAV-Recording** wird gestartet durch `birdnet_recording.service` mit Aufruf von `~/BirdNET-Pi/scripts/birdnet-recording.sh`. Dort ab `line 49` startet `pulseaudio` (nicht das neuere `PipeWire`) und für die Einzelaufnahmen ```arecord -f S16_LE -c${CHANNELS} -r48000 -t wav --max-file-time {RECORDING_LENGTH} -D "${REC_CARD}" --use-strftime ${RECS_DIR}/StreamData/%F-birdnet-%H:%M:%S.wav```. 

  `--max-file-time ${RECORDING_LENGTH}` bedeutet, `arecord` nimmt kontinuierlich auf und erzeugt daraus eine .wav alle `RECORDING_LENGTH` Sekunden.

  Sobald die Einzelaufnahme schließt, sieht `birdnet_analysis.py` via `Linux Kernel Inotify` neue `~/BirdSongs/StreamData` und analysiert sie. Die `StreamData/` können auf eine Ramdisk (no size parameter, so grows dynamically up to 50% of system RAM, then stalls!) gemountet werden zwecks SD-Karten-Schonung in `WebIF-Tools-Services-Ram Drive`.

  Das USB-Mikrofon als Recording Quelle (`arecord -L`) wird festgelegt durch `default` im Webinterface-Tools-Settings-Advanced.

- 



[BirdNET-Analyzer](https://github.com/birdnet-team/BirdNET-Analyzer) kann wohl fixe Sounddateien vor Ort analysieren.

