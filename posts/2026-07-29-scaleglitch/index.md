---
layout: default
title: "hx711 Signalfehler"
date: 2026-07-29
permalink: /posts/2026-07-29-scaleglitch/
---
<!--keywords[bitbanging,blog,Fehlvideo,hx711,SPI_Trick,state_maschine,userspace,Waage]-->

Wie schon am Ende von Blog "2025-12-16-scalestate" befürchtet, fand ich die X-te Version der Software für die Waage nötig. Dabei reichte diesmal die KI allein nicht mehr aus, sondern es bedurfte auch der Vorlage des etablierten C-Treibers von [Robertson](https://github.com/endail/hx711)(endail).

**Python Part**
- Der Anspruch ist die Vogelstation mittels Tasmota Zeitschalter jeden Morgen hochzufahren und dabei die Waage zu kalibrieren. Eine State-Maschine (FSM) ist ratsam, um Fehlkalibrationen durch *unbeobachtete*  Vogeleinwirkung auszugleichen.

- Ein C-Treiber ist die hardware-naheste Methode zur Abfrage der HX711 ADC Platine. Dazu verwenden Raspberry Distributionen zunehmend das LGPIO Interface. Die digitalen Counts der Platine werden dann eine Baseline um 0.0 g (hxOffset) und eine Gramm-Skala (hxScale) umgerechnet und ihr Verlauf wird in Python als vogeltypisch eingestuft oder nicht.

- Die Kombination aus Python und angebundenem C-Treiber (ctype Modul) dient auch der Überwachung von Verdrahtungsproblemen (Wägezellendefekt, Lötstellen) und der Umwelteinflüsse (Wind, Regen). Die Temperaturdrift im Tagesverlauf kann die Wägezelle durch Erwärmung in größerem Ausmaß als ein Vogelgewicht allmählich verändern, was eine automatische Anpassung der Nullinie (baseline) erfordert.

**C-Treiber Userspace Problem**
- *Trixie*  ist kein *Real Time Linux* oder RTOS wie FreeRTOS auf Mikrocontrollern. Es wird den unter User *Pi* laufenden Treiber der hx711-Platine immer mal wieder ausbremsen, um andere Aufgaben vorzuziehen. Dies kann durch Prioritätsbefehle wie `nice` oder noch besser `chrt` gemildert werden. Userspace Treiber leiden unter sog. `userspace bit banging`.

- Das betrifft auch den Kontroller der hx711-Platine. Merkt er, dass er 60 usecs nicht zu tun hat, dann legt er sich schlafen und kann anschließend bis 400 millisecs(!) zum Aufwachen benötigen. Während dieser Zeiten liefert er korrupte Werte (Glitches), die ausgefiltert werden müssen.

- Durch ein `dts overlay` könnte in *Trixie* auch der `iio Kerneltreiber` für den hx711 aktiviert werden. Diese Overlays sind aber schwierig zu debuggen und kommen einem Hacking von Processorregistern gleich, denen für RPi 4 und 5 unterschiedliche Prozessoren zugrunde lägen. Keine eigenen Erfahrung beim Debuggen von *Root Linux* oder *Yocto*.

- Weniger Aufwand würde der **SPI Port Trick** in Trixie machen. Hier wird der hx711 Kontroller als SPI Device "mißbraucht". Das erfordert SPI Aktivierung und einen speziellen Python Treiber (Modul `spidev` oder `c-periphery`) und die folgende Verdrahtung:
```
DOUT -> SPI MISO (Pin 21 / GPIO 9)
SCK  -> SPI MOSI (Pin 19 / GPIO 10)
```
Zwar werden die SPI0-Pins belegt, aber instabiles Software-Bit-Banging und das ungewollte Einschlafen des HX711-Chips entfallen. Die kontinuierlichen ~15 mA (statt 1,5 mA im Sleep-Zustand) durch die Wheatstone-Brücke fallen bei Netzbetrieb kaum ins Gewicht.

Mit dieser Darstellung möchte ich andeuten, wieviel Zeit und Tokens in der Entwicklung eines verlässlichen hx711 Treibers unter *Raspberry Trixie* stecken.

Feedback an *herber7be7z@gmail.com*. Happy Birding!