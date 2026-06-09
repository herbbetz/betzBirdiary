#!/bin/bash
# simply set the argon fan hat without any demon of dtoverlay in config.txt
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