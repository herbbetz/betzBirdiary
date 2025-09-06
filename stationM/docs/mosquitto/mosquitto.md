<!--keywords[Mosquitto]-->

**Installation & Config**

- `sudo apt install mosquitto mosquitto-clients`
- `sudo systemctl status mosquitto`, `sudo systemctl is-enabled mosquitto`
- /etc/mosquitto/: 

**Clients**

- `mosquitto_sub -h localhost -t test`
- `mosquitto_pub -h localhost -t test -m "Hello from terminal 2"`

**Viewer**
- `mosquitto_sub -t "#" -h localhost -v`
- You cannot publish to # like in  `mosquitto_pub -h localhost -t "#" -r -m ""` .  This is wrong. So you cannot clear all topics. Only this is possible: `mosquitto_pub -h localhost -t "your/specific/topic" -r -m ""`.

**Python**

- `pip install paho-mqtt`
