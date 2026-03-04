<!--keywords[Changelog,edgeKI,ESP32,Historie,SVGA]-->
Changelog

- 3.3.2026: Auflösung vidsize in config.json bisher 1280x960px (30 FPS, 4830 kb/sec) reduziert auf SVGA = 800x600px

````
800 * 600 = 480 000, 1280 * 960 = 1230 000 also 2.5mal größer
````

| **Feature**     | **ESP32-CAM (OV2640)**            | **Raspberry Pi Cam v1.3 (OV5647)**    |
| --------------- | --------------------------------- | ------------------------------------- |
| **Resolution**  | 2 Megapixels ($1600 \times 1200$) | **5 Megapixels** ($2592 \times 1944$) |
| **Sensor Size** | 1/4 inch                          | 1/4 inch                              |
| **Pixel Size**  | $2.2 \mu m \times 2.2 \mu m$      | $1.4 \mu m \times 1.4 \mu m$          |
| **Video Modes** | 15 fps @ UXGA (Raw)               | **30 fps @ 1080p**, 60 fps @ 720p     |
| **Interface**   | 8-bit Parallel (DVP)              | **MIPI CSI-2** (High speed)           |
| **Color Depth** | 8-bit / 10-bit Raw                | 10-bit Raw                            |

Laut Gemini KI ist der 3. Faktor (neben SVGA 800x600 und FPS 15/sek), warum die Duisbird MP4 10-fach kleiner sind, die Grobkörnigkeit der ESP-Cam OV2640. Ein Korn = Pixel hat dort 2.2 µm (dynamic range 50 dB, dazu begrenzter JPGEG Speicher der Kamera mit Hardware-Kompression), während die einfachste Raspicam v1.3 1.4 µm hat und deshalb in hellen/ dunklen Bereichen auch mehr Abstufungen /Informationen aufnimmt (dynamic range 68 dB). FFMPEG könnte die Raspicam Körnigkeit auf ESPcam Niveau zurückfahren mit Parametern wie `-crf 28`(Constant Rate Factor) und damit auf der Plattform Speicherplatz sparen. Die bessere Auflösung der Raspicam geht beim Umwandeln zu 224x224 Images für das KI-Training wieder verloren und die ESPcam Qualität reicht dafür gut aus, wenn ungünstige Beleuchtungen (Gegenlicht, high contrast = OV2640 "blindness") vermieden werden. Allerdings sollen die Modelle auf ESPcam am besten laufen, die auch dort trainiert wurden. Beachte auch die spezielle "Fischaugenperspektive" beim Duisbird. Deshalb müsste man die Trainingsdaten aus dem Duisbird von denen aus der Raspicam trennen. Als leichtgewichtige Runtime bei einmal trainiertem Model gibt es für ESP32 verschiedene spezialisierte: TFLM (=tensorflow lite for microcontrollers), edge impulse (most popular), ESP-DL ...