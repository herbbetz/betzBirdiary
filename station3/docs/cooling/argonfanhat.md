<!--keywords[Argon40,Cooling,Fan_Hat]-->

- [Argon40 Fan Hat](https://argon40.com/en-de/products/argon-fan-hat), gekauft Mai 2026 von [BerryBase](https://www.berrybase.de/argon-fan-hat-fuer-raspberry-pi). Anleitung auf [argon40.com](https://argon40.com/en-de/blogs/argon-resources/argon-fan-hat-installation-guide), sh. `Argon_Fan_Hat.pdf`.

- raspi-config: the fan hat is not attached to one GPIO, but to several over I2C, which needs therefore to be enabled and (after reboot) should show `1a` with `sudo i2cdetect -y 1`.
  - **I2C Communications:** **GPIO 2** (SDA) and **GPIO 3** (SCL). This is what controls the actual fan speed and the on-board LEDs.
  - **Power Button Management:** **GPIO 4** (configured as an active-low signaling pin) and **GPIO 17** (used to handle the system shutdown state/system power cut). `flags = 0x01` in `/etc/argononed.conf` should disable button logic and free GPIO4 and GPIO17.

- **mein Weg:** ohne Daemon und `dtoverlay in config.txt` arbeitet der Fan 100% unabhängig von OS und CPU Temperature (`vcgencmd measure_temp`) oder kann über I2C gesteuert, wenn auch nicht gelesen werden:
```
#!/bin/bash

# 1. Check if the I2C bus even exists
if [ ! -e /dev/i2c-1 ]; then
    echo "Error: I2C interface is disabled. Run raspi-config to enable it." >&2
    exit 1
fi

# Get the CPU temperature, more direct than 'vcgencmd measure_temp'
RAW_TEMP=$(cat /sys/class/thermal/thermal_zone0/temp)
TEMP=$((RAW_TEMP / 1000))

# 2. Run i2cset but suppress raw errors, then check if it succeeded
set_fan_speed() {
    local hex_speed=$1
    local percent=$2
    
    # Fan Hat sends back 'ACK' bit:
    if sudo i2cset -y 1 0x1a "$hex_speed" 2>/dev/null; then
        echo "Temp: ${TEMP}°C -> Fan: ${percent}"
    else
        echo "Error: Fan HAT not responding at I2C address 0x1a" >&2
        exit 1
    fi
}

# Execute based on temperature thresholds
if [ "$TEMP" -ge 65 ]; then
	# 'sudo i2cset -y 1 0x1a 0x64' runs fan on 100% speed
    set_fan_speed "0x64" "100%"
elif [ "$TEMP" -ge 55 ]; then
    set_fan_speed "0x32" "50%"
else
    set_fan_speed "0x00" "OFF"
fi
```

- On Trixie the official Argon legacy one-liner script (`curl https://download.argon40.com/argonfanhat.sh | bash`) will likely fail or misbehave. Gemini recommends the [Argon One Demon](https://gitlab.com/DarkElvenAngel/argononed) instead.
  ```
  git clone https://gitlab.com/DarkElvenAngel/argononed.git
  cd argononed
  ./configure
  make
  sudo ./install
  sudo systemctl status argononed
  ```
  - `boot/firmware/config.txt` enthält jetzt `dtoverlay=argonone`.
  
  - `argonone-cli --decode` zeigt die momentanen Settings. Sie können in einem `/etc/argononed.conf` geändert werden mit nachfolgendem `systemctl restart argononed`:
  
    ```
    # /etc/argononed.conf
    # Set the three temperature trip points (in Celsius)
    temps = 50, 60, 68
    
    # Set the corresponding fan speeds (0 to 100)
    fans = 20, 60, 100
    
    # Degrees drop required before lowering the fan speed
    hysteresis = 3
    
    ```
  
    
