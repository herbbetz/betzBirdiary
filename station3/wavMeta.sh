#!/bin/bash
# download empty .wav using 'wget https://audio_link.wav'
# analyse TAG by 'ffprobe -show_format min.wav|grep title'
appdir="/home/pi/station3"
inwav="$appdir/wav/base.wav"
outwav="$appdir/wav/min.wav"

today=$(date +%Y-%m-%d)

if [[ -z $1 ]]; then
    msg="betzBird$today"
else
    msg="$1"
fi

# -y for overwrite without asking, avoiding encoder TAG is difficult
ffmpeg -y -i "$inwav" -c copy -metadata title="$msg" "$outwav"