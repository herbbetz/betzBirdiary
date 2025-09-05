<!--keywords[Mosquitto]-->

**Installation & Config**

- `sudo apt install mosquitto mosquitto-clients`
- `sudo systemctl status mosquitto`, `sudo systemctl is-enabled mosquitto`
- /etc/mosquitto/: 

**Clients**

- `mosquitto_sub -h localhost -t test`
- `mosquitto_pub -h localhost -t test -m "Hello from terminal 2"`

**Python**

- `pip install paho-mqtt`
