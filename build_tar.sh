#!/bin/bash
# convert line endings to unix
find /home/pi -type f -name "*.sh" -exec dos2unix {} +
# archive
tar -cvzf stat3.tar.gz --exclude='*/__pycache__' --exclude='station3/ramdisk' station3/