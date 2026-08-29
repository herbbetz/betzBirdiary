#!/bin/bash
# script to deploy betzBird.img anonymously
appdir="/home/pi/station3"

echo "Disable crontab..."
crontab "$appdir/crontab4test.txt"

echo "write wav RIFF metadata..."
$appdir/wavMeta.sh

echo "Anonymize config.json..."
$appdir/config-yaml.sh ANONconfig.yml

secrets=$appdir/BETZconfig.yml
if [ -f $secrets ]; then 
echo "Shred $secrets"
$appdir/shredfile.sh $secrets
fi 