---
layout: default
title: "hx711 Signalfehler"
date: 2026-07-29
permalink: /posts/2026-07-29-scaleglitch/
---
<!--keywords[bitbanging,blog,Fehlvideo,hx711,Medianfilter,SPI_Trick,state_maschine,Userspace_Treiber,Waage]-->

Wie schon am Ende von Blog "2025-12-16-scalestate" befürchtet, fand ich die X-te Version der Software für die Waage nötig. Dabei reichte diesmal die KI allein nicht mehr aus, sondern es bedurfte auch der Vorlage des etablierten C-Treibers von [Robertson](https://github.com/endail/hx711) (endail).

**Python Part**
- Der Anspruch ist die Vogelstation mittels Tasmota Zeitschalter jeden Morgen hochzufahren und dabei die Waage automatisch zu kalibrieren. Eine State-Maschine (FSM) ist ratsam, um Fehlkalibrationen durch *unbeobachtete*  Vogeleinwirkung auszugleichen.

- Ein C-Treiber ist die hardware-naheste Methode zur Abfrage der HX711 ADC Platine. Dazu verwenden Raspberry Distributionen zunehmend das LGPIO Interface. Die digitalen Counts der Platine werden dann eine Baseline um 0.0 g (hxOffset) und eine Gramm-Skala (hxScale) umgerechnet und ihr Verlauf wird in Python als vogeltypisch eingestuft oder nicht.

- Die Kombination aus Python und angebundenem C-Treiber (ctype Modul) dient auch der Überwachung von Verdrahtungsproblemen (Wägezellendefekt, Lötstellen) und der Umwelteinflüsse (Wind, Regen). Die **Temperaturdrift** im Tagesverlauf kann die Wägezelle durch Erwärmung in größerem Ausmaß als ein Vogelgewicht allmählich verändern, was eine automatische Anpassung der Nullinie (baseline) erfordert.

**C-Treiber Userspace Problem**
- *Trixie*  ist kein *Real Time Linux* oder RTOS wie FreeRTOS auf Mikrocontrollern. Es wird den unter User *Pi* laufenden Treiber der hx711-Platine immer mal wieder ausbremsen, um andere Aufgaben vorzuziehen. Dies kann durch Prioritätsbefehle wie `nice` oder noch besser `chrt` gemildert werden. Userspace Treiber leiden unter sog. `userspace bit banging`.

- Das betrifft auch den Kontroller der hx711-Platine. Merkt er, dass er 60 usecs nicht zu tun hat, dann legt er sich schlafen und kann anschließend bis 400 millisecs(!) zum Aufwachen benötigen. Während der Schlafübergänge liefert er korrupte Werte, die der C-Treiber auszufiltern versucht anhand der verlängerten Lesezeit der 24 Bits. Gelegentliches Versagen dieser Ausfilterung resultiert in **seltenen, plötzlichen Glitches von 4000 counts (ca. 7 g) im C-Treiber unabhängig von der Wägezelle**.

- Durch ein `dts overlay` könnte in *Trixie* auch der `iio Kerneltreiber` für den hx711 aktiviert werden. Diese Overlays sind aber schwierig zu debuggen und kommen einem Hacking von Processorregistern gleich, denen für RPi 4 und 5 unterschiedliche Prozessoren zugrunde lägen.

- Keine eigenen Erfahrung beim Debuggen von *Root Linux* oder *Yocto*, die ebenfalls Kerneltreiber (iio) einzubinden pflegen.

- Weniger Aufwand würde der **SPI Port Trick** in Trixie machen. Hier wird der hx711 Kontroller als SPI Device "mißbraucht". Das erfordert SPI Aktivierung und einen speziellen Python Treiber (Modul `spidev` oder `c-periphery`) und die folgende Verdrahtung:
```
DOUT -> SPI MISO (Pin 21 / GPIO 9)
SCK  -> SPI MOSI (Pin 19 / GPIO 10)
```
Zwar werden die SPI0-Pins belegt, aber instabiles Software-Bit-Banging und das ungewollte Einschlafen des HX711-Chips entfallen. Die kontinuierlichen ~15 mA (statt 1,5 mA im Sleep-Zustand) durch die Wheatstone-Brücke fallen bei Netzbetrieb kaum ins Gewicht.

- Mit **SCHED_FIFO** ist es möglich, den dritten CPU Core des RPi4 exklusiv zu isolieren (`isolcpus=3` in `/boot/firmware/cmdline.txt`) und im C Treiber des hx711 für den eigenen Thread zu reservieren (nur als root).

**Testaufbau**

- Die Station lief über Stunden im Wohnzimmer, um definiert die Sitzstange unbelastet zu lassen (oder sie definiert zu belasten).
- Das `hxFiBirdStateCt.py` bekam ein Kommandozeilenargument `test` zum Aktivieren von Debugging Code. Ebenso bekam `libhx711.c` ein `make -f hx_Makefile debug`.
- Um über Stunden Werte in einem auswertbaren Format (für Mensch oder begrenzten KI-Upload) aufzuzeichnen, braucht es 
	- 1) programm-interne *Event Recorder* , die nur wichtige Änderungen aufzeichnen (TraceRecorder),
	- 2) SignalLogger, die sekündlich alle Signale aufzeichnen und dann durch ein externes Skript wie `hx_signalanalyzer.py` offline zusammengefasst werden,
	- 3) ein externes `hx_sig_trace_analyzer.py`, das 1) und 2) anhand ihrer Zeitstempel korreliert,
	- 4) die Zeitstempel der Auslösung von Leervideos im Vergleich mit 1) bis 3) später im Einsatztest draussen .

**Softwarekonzepte**

Die KI ist zwar eine hervorragende Kodierhilfe. Sie nimmt es aber nicht ab, stabil gemessene *raw counts* (C Treiber) dann in Python auch sachgerecht zu interpretieren.

- Nach morgendlichem Systemboot kann die Sitzstange leer sein oder durch Vogelgezappel oder einen sitzenden Vogel beeinflusst. Die Temperatur kann viel kühler sein als noch am aufgeheizten Vorabend. Die erste Entscheidung ist, das bisherige hxOffset (Nullinie = *baseline*) zu verwerfen und durch eine Neukalibrierung zu ersetzen, die erst stabile Werte (im *Spreadlimit*) abwartet und einen ruhig sitzenden Vogel "wegkalibriert". Verschwindet der ruhig sitzende Vogel anschließend, löst die konstant abgefallene *baseline* ein Timeout mit Neukalibrierung aus.
- Eine minimale Sitzzeit von 2 secs wird festgelegt, ab der die Kamera getriggert wird (über FIFO). Die (lokale) KI benötigt eine gewisse Anwesenheitsdauer zur Vogelerkennung. Nicht jeder Windstoß oder fallende Regentropfen an der Stange soll ein Video auslösen. *Spread* und *Outlier* werden statistisch ermittelt (*Perzentile, Medianfilter* oder *Kalmanfilter*).
- Die Finite State Maschine (*FSM*) definiert States der Sitzstange wie IDLE, ARRIVAL, PRESENT, DEPARTURE, OVERWEIGHT. Im laufenden Betrieb wird immer wieder überprüft, ob IDLE noch der Nullinie entspricht und ob die anderen States nach einem stabilen Timeout nicht als das neue IDLE angesehen werden müssen.



Mit dieser Darstellung möchte ich andeuten, wieviel Zeit und Tokens in der Entwicklung eines verlässlichen hx711 Treibers (in C und Python) unter *Raspberry Trixie* stecken.

Feedback an *herber7be7z@gmail.com*. Happy Birding!