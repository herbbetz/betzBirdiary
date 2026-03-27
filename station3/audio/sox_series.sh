#!/bin/bash
# mic and headphone default set in /etc/asound.conf
# however sox loops with silence detect tend to be unreliable, restarting continuously and not stopping on ctrl-c
i=1
while true; do
  sox -c 1 -t alsa plughw:3,0 "${i}.wav" silence 1 0.1 2% 1 1.0 2%
  i=$((i+1))
done