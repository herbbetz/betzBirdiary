<!--keywords[C++,endail,lgpio,hx711]-->

**HX711 C++ Treiber von endail**

- `https://github.com/endail/hx711`, Maintainer: Daniel Robertson

- Python binding: `https://github.com/endail/hx711-rpi-py`

- requirement: [lgpio](http://abyz.me.uk/lg/index.html)

  ````
  sudo apt-get install -y liblgpio-dev
  git clone --depth=1 https://github.com/endail/hx711
  cd hx711
  make && sudo make install
  sudo ldconfig
  ````
- usw