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
- Zielführend ist eine C-Lösung mit `libasound2-dev`.