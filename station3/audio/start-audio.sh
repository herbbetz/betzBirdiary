#!/bin/bash
sleep 5
# loopback connects mic to headphone (background), GUI: pavucontrol
/usr/bin/pw-loopback --latency=100ms &