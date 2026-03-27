<!--keywords[Audio,Soundprocessing]-->

- `arecord -l` listet USB-Mikrofon z.B. auf `card 3`, dann `arecord -D plughw:3,0 -c 1 -d 5 -vv test_mono.wav` -> 5 sec Monoaufnahme.
- Wiedergabe mit `aplay -l` -> headphones auf `card 2`, dann `aplay -D plughw:2,0 test_mono.wav`
- in `alsamixer (F6)` werden die Einstellungen getätigt und in fixiert in `etc/asound.conf`:
````/etc/asound.conf
pcm.!default {
    type asym
    playback.pcm "plughw:2,0"
    capture.pcm "plughw:3,0"
}

ctl.!default {
    type hw
    card 2
}
````

- Sox recording: `sudo apt install sox` kann mit oder ohne `arecord` die Stille am Anfang und Ende trimmen, ist aber letzendlich genauso überfordert mit dem ALSA buffering wie `python3-pyaudio, python3-soundfile und wave`.
- Zielführend ist eine C-Lösung `wavseries.c` mit `libasound2-dev`. Um sie auf *Librosa Mel Spektrogramme* und *BirdNET KI* abzustimmen erzeugt sie folgende .wav Files: 48000 Hz, normalized.
-  Für die Mel Spektrogramme: `apt install python3-librosa` noch nicht für Trixie verfügbar, wie oft bei wissenschaftlichen Libraries.  => `pyenv activate birdvenv` (Python 3.11) und `pip install librosa`. Leider kann `matplotlib` mit seiner engen Kopplung an `numpy` nicht aus dem System-Python verwendet werden und wird hier noch mal installiert. Grundsätzlich ist es nicht gut, Python Versionen zu mischen, also meide `python3 -m venv --system-site-packages birdvenv`(auch für pyenv) . Wir brauchen ja numpy < 2 auch für python tflite_runtime. Generate mel spectrograms in C (librosa?) and view with system matplotlib?