<!--keywords[Audiodatei,Audiolinks,ffmpeg,RIFF_metadata]-->

'wav/min.wav' ist eine minimale Audiodatei, deren Upload die Birdiary Plattform immer noch obligatorisch fordert.

- `wavMeta.sh` zeigt, wie die Datei `min.wav` für Metainformation Verwendung findet. Enthält sie aber keine Audiodaten, kann sie nur als Audiolink gedownloadet werden (mit `wget`) und durch `ffprobe` ihre Metadaten zeigen. Alternativ kann die `base.wav` (ohne Audio und Metainfo 44 Byte) als Vorlage der `min.wav` eine Stille von 0.1 sec enthalten, was wie folgt erzeugt wird: `ffmpeg -f lavfi -i anullsrc=r=8000:cl=mono -t 0.1 -metadata title="ABC" base.wav`. Dann hat `base.wav` aber 1690 Byte. Deshalb verwende ich momentan die leere `base.wav` als Vorlage für `min.wav`, das ohne Audio aber mit kurzer Metainfo dann 106 Byte hat.
- `ffprobe` zeigt die RIFF Metadaten zuverlässig, `Audacity Audio Export` nur bei enthaltenen Audiodaten (Stille),  `Win11Explorer Details` oder `VLC` dagegen gar nicht.

Für die Vogelstimmen verwende ich in /mybirds die Site [british-birdsongs](www.british-birdsongs.uk/).

Für Vogelstimmenanalyse verweise auf [BirdNET-PI](https://github.com/mcguirepr89/BirdNET-Pi).