FROM debian:bullseye-slim
# FROM debian:bullseye
# 'docker build -t dockercam:0 --no-cache .' builds the img 'dockercam:0' from this dockerfile. The img then contains python3-picamera2 and -libcamera and -pyqt5 (apt-get versions).
# Add Raspberry Pi repository, else python3-picamera2 not found ('pip3 picamera2' fails on PyQt5 download)
# one RUN cmd means only one additional layer:

RUN apt-get update && \
apt-get install -y gnupg curl && \
echo "deb http://archive.raspberrypi.org/debian/ bullseye main" > /etc/apt/sources.list.d/raspi.list && \
curl -fsSL https://archive.raspberrypi.org/debian/raspberrypi.gpg.key | gpg --dearmor -o /usr/share/keyrings/raspberrypi-archive-keyring.gpg && \
echo "deb [signed-by=/usr/share/keyrings/raspberrypi-archive-keyring.gpg] http://archive.raspberrypi.org/debian/ bullseye main" > /etc/apt/sources.list.d/raspi.list && \
apt-get update && \
apt-get upgrade -y && \
apt-get install -y python3 procps python3-picamera2 python3-flask && \
apt-get clean && \
rm -rf /var/lib/apt/lists/* && \
groupadd -g 997 gpio
# group 'video' in docker-compose is mostly '44' in container and host, but group 'gpio' is not as standardized and must be adapted, if this is '997' on the host.

WORKDIR /app

COPY app/start.sh .

CMD ["bash", "start.sh"]