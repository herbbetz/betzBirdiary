<!--keywords[birdNET, Cornell, Vogelstimmen]-->

Aktuelle "Nachtzuster" Codeversion von [BirdNET-PI](https://github.com/Nachtzuster/BirdNET-Pi) ist installierbar über dortiges `newinstaller.sh`.

- das **Webinterface** ist erreichbar unter `http://<IP4 des RPi>` mit dem Passwort `birdnet / <leer>`.
- Als Server installiert sich Caddy mit PHP-FPM = *FastCGI Process Manager* (`install-services.sh`).

```
  -> /etc/caddy/Caddyfile:
http://  {
  root * /home/pi/BirdSongs/Extracted
  file_server browse
  handle /By_Date/* {
    file_server browse
  }
  handle /Charts/* {
    file_server browse
  }
  reverse_proxy /stream localhost:8000
  php_fastcgi unix//run/php/php-fpm.sock
  reverse_proxy /log* localhost:8080
  reverse_proxy /stats* localhost:8501
  reverse_proxy /terminal* localhost:8888
}
```
Caddy dient als Proxy für verschiedene Interfaces:
```
:80    Caddy public web UI
:8080  gotty log service, localhost only
:8501  Streamlit stats, localhost only
:8888  gotty web terminal, localhost only
:8000  Icecast live audio stream, localhost only
```
d.h. `http://<IP4>:8080` ist nicht erreichbar (`localhost only binding`), stattdessen `http://<IP4>/logs>`.

Icecast Audio Stream wird gehört mit VLC unter `http://<IP4>/stream`.

Der **Birdiary Flaskserver**  braucht also einen anderen Port wie 8090. Er kann dann auch über den Caddy Proxy erreichbar gemacht werden.

- Im WebUI in `Tools-Settings` werden eingetragen: `Latitude (48,5335) / Longitude (12,1375) => 48.5335/12.1375 in birdnet.conf`, `BirdWeather Token` für `https://app.birdweather.com/stations/24979 (betzBirdNet)`, Zeitzone. All das landet in `~/BirdNET-Pi/birdnet.conf` (symlink `/etc/birdnet/birdnet.conf` von überall zugänglich).

​	In `-Advanced Settings`: eigenes BirdNet-Pi Passwort, Audio Settings samt RTSP-Audio-Source, ab welcher `Disk Usage` die Vogelaudios aus `~/BirdSongs` gelöscht werden.

​	Die Settings aus dem Webinterface werden gespeichert durch `scripts/config.php` bzw. `advanced.php` in `birdnet.conf`.  `service_controls.php` dagegen (de-)aktiviert verschiedene Services via `views.php`.

- **Installation**: `scripts/install_birdnet.sh` startet `install_config.sh` (->`birdnet.conf`) und `install_helpers.sh`. `systemd services` werden installiert durch `scripts/install_services.sh`.

- **WAV-Recording** wird gestartet durch `birdnet_recording.service` mit Aufruf von `~/BirdNET-Pi/scripts/birdnet-recording.sh`. Dort ab `line 49` startet `pulseaudio` (nicht das neuere `pipewire` mit `pw-record`) und für die Einzelaufnahmen ```arecord -f S16_LE -c${CHANNELS} -r48000 -t wav --max-file-time {RECORDING_LENGTH} -D "${REC_CARD}" --use-strftime ${RECS_DIR}/StreamData/%F-birdnet-%H:%M:%S.wav```. 

  `--max-file-time ${RECORDING_LENGTH}` bedeutet, `arecord` nimmt kontinuierlich auf und erzeugt daraus eine .wav alle `RECORDING_LENGTH` Sekunden.

  Sobald die Einzelaufnahme schließt, sieht `birdnet_analysis.py` via `Linux Kernel Inotify` neue `~/BirdSongs/StreamData` und analysiert sie. Die `StreamData/` können auf eine Ramdisk (no size parameter, so grows dynamically up to 50% of system RAM, then stalls!) gemountet werden zwecks SD-Karten-Schonung in `WebIF-Tools-Services-Ram Drive`.

  Das USB-Mikrofon als Recording Quelle (`arecord -L`) wird festgelegt durch `default` im Webinterface-Tools-Settings-Advanced.

  Das Desktop **Pavucontrol** ist wirksam, wenn `REC_CARD=default` und nicht explizit ein ALSA Device wie bei `REC_CARD=plughw:CARD=Device,DEV=0`.

- **SoX Spectrogram**: Die SoX Spektrogramme auf dem Webinterface sind nicht die Mel Spektrogramme innerhalb dem KI Modell, sondern separat erzeugt in `scripts/spectrogram.sh`, Zeile 31: `sox -V1 "${analyzing_now}" -n remix 1 rate 24k spectrogram ...`.

- **KI**: 

  - BirdNET arbeitet wohl mit einer `tflite_runtime` kompatibel zum Trixie System Python 3.13 . Seine **Venv** installiert kein älteres Python, sondern pinnt lediglich einige Versionen:
    ```
    streamlit==1.44.0
    apprise==1.9.5
    pytest==7.1.2
    suntime==1.3.2
    pyarrow==20.0.0    
    
    ```
  - The FFT / spectrogram / mel preprocessing is very likely **inside the .tflite model graph**, not in BirdNET-Pi’s Python code. The Python code only prepares waveform chunks and metadata/species filtering.
  - There is also a separate metadata model for species range filtering. That one takes 'latitude, longitude, week' and outputs a likely-species list. That is separate from audio classification.
  



- **Upload zur birdweather API**

​	`scripts/birdnet-analysis.py (line119)` aktiviert `scripts/utils/reporting.py`, dessen Funktion `bird_weather(file, detections)` die Sounds als FLAC hochlädt zu `https://app.birdweather.com/api/v1/stations/{BIRDWEATHER_ID}/soundscapes` und die Daten zu `https://app.birdweather.com/api/v1/stations/{BIRDWEATHER_ID}/detections`. BIRDWEATHER_ID  aus `birdnet.conf` ist identisch mit dem birdweather_token.



**Zusammenfassung** der Pipeline:

```
arecord / ffmpeg -> creates raw WAV chunks
Python + TFLite -> analyzes bird sounds
SoX -> makes spectrogram images and extracted audio clips
Caddy/PHP -> shows them in the web UI
```

[BirdNET-Analyzer](https://github.com/birdnet-team/BirdNET-Analyzer) kann wohl fixe Sounddateien vor Ort analysieren.

