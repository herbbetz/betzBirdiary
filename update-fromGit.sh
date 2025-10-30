#!/bin/bash
cd /home/pi/githubRepo
echo "pulling from public https://github.com/herbbetz/betzBirdiary (no password needed)"
git pull
# --exclude='.git' excludes any .git, but there is no git in station3/ anyway
echo "updating station3/ from betzBirdiary download in githubRepo/"
rsync -av  --exclude-from=/home/pi/githubRepo/.rsync-exclude station3/ /home/pi/station3/
# rsync -av --delete githubRepo/station3/ /home/pi/stationtest/ # would also delete files removed on Github
# permissions were changed according to github repo
sudo chown -R pi:pi /home/pi/station3/
chmod +x /home/pi/station3/*.sh

