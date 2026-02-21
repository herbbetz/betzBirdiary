<!--keywords[lgpio,Treiber,Testdatei_Sensor]-->

- Im Verzeichnis `station3/lgpioBird` finden sich die `lgpio` Treiberdateien für die Sensoren Dehnmesstreifen/hx711 und DHT22 Temperatur-Feuchte-Sensor
- die `example` Dateien zeigen einfache Testskripte, die aber nur funktionieren, wenn nicht bereits ein anderes Programm auf die Hardware zugreift.
- Revision am 21.2.26:
  - immer wieder nach dem booting auftretende  '-629.5 grams None' statt '0.2 grams Idle' führten zur erneuten Revision von Treiber 'HX711.py' und zur Einführung von *self-healing Surge Detection* und *Watchdog* in hxFiBirdState.py .
  - Umstieg auf libgpiod gescheitert (siehe `station3/libgpiod`) und stattdessen pigpiod empfohlen zwecks Abdeckung von hx711 und dht22 auf RPi/ Ubuntu/ dietPi (Debian Systeme mit funktionierendem `pigpiod`).