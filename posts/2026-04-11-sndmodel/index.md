---
layout: default
title: "Bird Sounds"
date: 2026-04-11
permalink: /posts/2026-04-11-sndmodel/
---
<!--keywords[AI,audio,BirdNET,dawn_chorus]-->

**Wann Vögel singen**
Aus diversen Gründen erreicht das Zwitschern von Tagvögeln seinen Höhepunkt vor und während der Morgendämmerung (*dawn chorus*) und bei Abenddämmerung. Zu diesen Zeiten ist es für Vogelvideos eventuell zu dunkel.

**BirdNET KI-Modell**
- Das BirdNET-Projekt für Vogelstimmen-Analyse stammt vom Dpt. of Ornithology der Cornell University (New York) und findet sich auf Github [BirdNET-Analyzer](https://github.com/birdnet-team/BirdNET-Analyzer). Es wird von verschiedenen deutschen Unis und Institutionen unterstützt.
- Das KI-Modell für Vogelstimmen-Analyse findet sich im alten [BirdNET-Lite](https://github.com/birdnet-team/BirdNET-Lite) oder aktueller, aber 50+ MB groß in den ZIP-Versionen auf der [Projektseite](https://birdnet-team.github.io/BirdNET-Analyzer/models.html) (Version 2.4 -> 6522 Arten). Für Python gibt es auch `pip install birdnet` und `python -m birdnet.analyze`, für die *Tensorflow Lite C API* (ohne Python) verwendet man aus dem ZIP die `BirdNET_GLOBAL_6K_V2.4_Model_FP32.tflite`.
- WAV-Clips von 3 sec /48000 Hz/ mono /16-bit signed little-endian PCM (`pcm_s16le`) bilden den WAV-Input für das KI-Modell. Intern im Modell wird das WAV wohl erstmal in ein *MEL Spektrogramm* transformiert. Für das Training sind die WAV-Clips gelabelt, für die Anwendung entspricht jeder Output-Knoten der Logit-Wahrscheinlichkeit eines trainierten Labels.
- Die besten Ergebnisse erreicht man mit guten (USB-) Mikrophonen, mit denen auch das BirdNET seine Modelle trainiert. Konfiguration auf dem Raspberry in `etc/asound.conf` mit den Daten aus `arecord -l`.
- Das Trennen der Vogelstimmen (150 Hz bis 15000 Hz) von Wetter- und Verkehrslärm (< 150 - 500 Hz) erreicht man durch *band pass filter*, meist softwaremäßig (FFT), seltener elektronisch.
- KI ist menschlicher Beurteilung unterlegen. Andere Tierarten (Insekten, Frösche) und technische Geräusche führen zu Fehlbestimmungen.
- Quelle für Testsounds: [british-birdsongs](https://www.british-birdsongs.uk/) (263 Arten)
````
Download des bird songs: 1) Audacity: recording source to system audio 2) Mit Browser Tools (F12), Network-Media, Website reloaden und Song abspielen, Rechtsklick auf Name des Blob, Öffnen in neuem Tab, Download des mp3. Umwandlung zu 3 sec langem WAV Mono für BirdNET tflite mit 'ffmpeg -i input.mp3 -t 3 -ac 1 -ar 48000 -c:a pcm_s16le output.wav'(mit Filter: -af "highpass=f=150, lowpass=f=15000, loudnorm").
````

**Setup auf betzBird**

- Erfassung und Preprocessing der WAV Dateien.

- Ein zeitgleicher Run mehrerer Modelle (Sound- und Image-Klassifikation) wird verhindert durch einen File-Lock (`flock /tmp/model.lock python run_model.py`) oder durch Queueing (`run_birdnet(); wait_until_done; run_image_model()`). Andernfalls geht das Memory aus (`htop`, `watch -n 1 free -h`, `cat /proc/meminfo`). Swap sollte abgestellt werden, weil zu langsam und die SD-Karte schädigend (`CONF_SWAPSIZE=0` in `/etc/dphys-swapfile`).
- flask endpoint to watch todaysnd.csv via browser: daily time| wav clip| diagnoses . Hochladen zu birdweather?

**Trixie Probleme**

- die ALSA Sound Bibliothek auf Raspberry 4 macht unter Python erheblich mehr Probleme als unter C.

- wie bei vielen wissenschaftlichen Python-Bibliotheken, die meist auch noch ziemlich groß sind durch zahlreiche Abhängigkeiten, gibt es für Mel-Spektrogramme noch kein `python3-librosa`, sondern nur `pip install librosa`. Ähnliches gilt für KI-Modelle und Tensorflow-Runtime. Dies lässt sich aktueller und platzsparender in C lösen.

Feedback an herber7be7z@gmail.com