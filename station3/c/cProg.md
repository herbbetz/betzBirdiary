<!--keywords[C++,lgpio,hx711]-->

**HX711 C++ Treiber mit lgpio**

- kein Python binding wie bei `https://github.com/endail`, sondern C-Daemon spricht mit hxFiBirdState.py via  `ramdisk/hxfifo`. Output einfach über `cat ../ramdisk/hxfifo` im anderen Terminal.

- requirement: [lgpio](http://abyz.me.uk/lg/index.html)

  ````
  sudo apt-get install -y liblgpio-dev (verified by: ls /usr/include/lgpio.h)
  cd ~/station3/c
  make clean
  make OR gcc -O2 -Wall -o hx711d hx711d.c -llgpio
  ````
- anders als python3-lgpio 0.2.2 braucht der C-Daemon auf Trixie keine veraltete Syntax.
- 