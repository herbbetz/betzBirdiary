<!--keywords[C++,lgpio,hx711]-->

**HX711 C++ Treiber mit lgpio**

- Nachteile von C-Daemon via `hxfifo` gegenüber`ctypes binding` : mkfifo /Verifizierung von `ramdisk/hxfifo`, extra Startbefehl von `hx711d`, Monitoring von `hx711d` und Reaktion auf dessen Absturz (ermitteln durch simples Testskript). Vorteil von `hxfifo`: leichtes Monitoring der hxfifo Values, unabhängige Absturz/Restart-Möglichkeit.

- alternatives Python binding wie bei `https://github.com/endail`?

- requirement: [lgpio](http://abyz.me.uk/lg/index.html)

  ````
  sudo apt-get install -y liblgpio-dev (verified by: ls /usr/include/lgpio.h)
  cd ~/station3/c
  make clean
  make OR gcc -O2 -Wall -o hx711d hx711d.c -llgpio
  ````
- anders als python3-lgpio 0.2.2 braucht der C-Daemon auf Trixie keine veraltete Syntax.
- 