#!/bin/bash
# convert line endings to unix

find /home/pi -type f -name "*.sh" -exec dos2unix {} +
