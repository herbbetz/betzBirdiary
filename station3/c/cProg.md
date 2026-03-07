<!--keywords[C-Daemon,lgpio,dht22,hx711,glitches]-->

**C-Treiber mit lgpio für HX711 und DHT22 **

- besserer Schutz vor *Glitches* durch maßgeschneiderte C-Treiber in `station3/c/` als bloßes *python bit-banging* mittels `lgpioBird/HX711.py`.

- Nachteile von C-Daemon via `hxfifo` gegenüber`ctypes binding` : mkfifo /Verifizierung von `ramdisk/hxfifo`, extra Startbefehl von `hx711d`, hx711d.sh zum Auslesen der hxPins aus `config.json`, Monitoring von `hx711d` aus `hxFiBirdStateC.py` und Reaktion auf dessen Absturz (ermitteln durch simples Testskript). Vorteil von `hxfifo`: leichtes Monitoring der hxfifo Values, unabhängige Absturz/Restart-Möglichkeit.

- alternatives Python binding wie bei `https://github.com/endail`?

- requirement: [lgpio](http://abyz.me.uk/lg/index.html)

  ````
  sudo apt-get install -y liblgpio-dev (verified by: ls /usr/include/lgpio.h)
  cd ~/station3/c
  gcc -std=c17 -Wall -Wextra -O2 -shared -fPIC libhx711.c -llgpio -o libhx711.so
  oder Makefile
  ````
- anders als python3-lgpio 0.2.2 braucht der C-Daemon auf Trixie keine veraltete Syntax.
- 