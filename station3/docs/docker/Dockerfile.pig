# multistage build keeps build tools out of final image.
# 'docker build -f Dockerfile.pig -t dockerpig:0 --no-cache .'
# Build stage of pigpio
FROM debian:bullseye AS builder

RUN apt-get update && apt-get install -y wget unzip build-essential
RUN wget https://github.com/joan2937/pigpio/archive/master.zip
RUN unzip master.zip
WORKDIR /pigpio-master
RUN make

# Final stage, bullseye-slim being an even smaller docker hub img
FROM debian:bullseye-slim

COPY --from=builder /pigpio-master/libpigpio.so /usr/local/lib/
COPY --from=builder /pigpio-master/pigpiod /usr/local/bin/
COPY --from=builder /pigpio-master/pig2vcd /usr/local/bin/
COPY --from=builder /pigpio-master/pigs /usr/local/bin/

RUN apt-get update && \
apt-get install -y gnupg curl props cron && \
echo "deb http://archive.raspberrypi.org/debian/ bullseye main" > /etc/apt/sources.list.d/raspi.list && \
curl -fsSL https://archive.raspberrypi.org/debian/raspberrypi.gpg.key | gpg --dearmor -o /usr/share/keyrings/raspberrypi-archive-keyring.gpg && \
echo "deb [signed-by=/usr/share/keyrings/raspberrypi-archive-keyring.gpg] http://archive.raspberrypi.org/debian/ bullseye main" > /etc/apt/sources.list.d/raspi.list && \
apt-get update && \
apt-get upgrade -y && \
apt-get install -y python3 python3-pigpio && \
apt-get clean && \
rm -rf /var/lib/apt/lists/* && \
groupadd -g 997 gpio
# group 'video' in docker-compose is mostly '44' in container and host, but group 'gpio' is not as standardized and must be adapted, if this is '997' on the host.

# Set up environment
ENV PYTHONUNBUFFERED=1
ENV LD_LIBRARY_PATH=/usr/local/lib

WORKDIR /app

COPY app/start.sh .

CMD ["/bin/bash", "start.sh"]