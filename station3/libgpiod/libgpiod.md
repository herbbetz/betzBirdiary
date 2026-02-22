**libgpiod driver**

- anders als `lgpio` ist `libgpiod` auch kompatibel mit anderen Debian Systemen als Raspberry OS, z.B. auch mit Ubuntu oder DietPI.

- es gibt jedoch einige Varianten von `libgpiod`, was herauszufinden ist mit folgenden Kommandos:

  ```
  pi@rpibird:~/station3/libgpiod $ python3 -c "import gpiod; print(gpiod.__version__)"
  2.2.0
  pi@rpibird:~/station3/libgpiod $ python3 -c "import gpiod; print(dir(gpiod))"
  ['Chip', 'ChipClosedError', 'ChipInfo', 'EdgeEvent', 'InfoEvent', 'LineInfo', 'LineRequest', 'LineSettings', 'RequestReleasedError', '__builtins__', '__cached__', '__doc__', '__file__', '__loader__', '__name__', '__package__', '__path__', '__spec__', '__version__', '_ext', 'api_version', 'chip', 'chip_info', 'edge_event', 'exception', 'info_event', 'internal', 'is_gpiochip_device', 'line', 'line_info', 'line_request', 'line_settings', 'request_lines', 'version']
  ```
Nur `v1-compatible libgpiod API` ist kompatibel mit mehreren OS wie RPi/dietPi/Ubuntu.

chatGPT 21.2.26:
your Python binding is too old / too incomplete for any of the modern v2 driver patterns.
At this point, trying to write a “portable HX711 driver” in Python directly using libgpiod on your system is practically impossible. The API is inconsistent, incomplete, and undocumented in key areas.
If we continue to try, it will just produce more AttributeErrors — exactly what you’ve seen.

- d.h. im Feb.26 hat Trixie einen Mismatch von libgpiod v1 und v2 installiert, das auch bei freiem GPIO17 kein Skript ohne Attribute-Error zulässt.

- als root: `ls /dev/gpiochip*` zeigt das Interface und `gpioinfo | grep GPIO17`, ob GPIO 17 besetzt ist, wie hier z.B. durch lgpio: `line  17: "GPIO17" input consumer="lg"`.



Letztendlich wird **pigpio** empfohlen, solange `pigpiod` auf RPi /DietPi /Ubuntu läuft.