#!/bin/bash
sudo apt update
sudo apt upgrade -y
sudo apt autoremove -y

/home/pi/birdvenv/bin/pip install --upgrade pip

# Export only venv packages by --local (not system)
/home/pi/birdvenv/bin/pip freeze --local > /home/pi/venv-requirements.txt

# Upgrade all packages in the requirements file
/home/pi/birdvenv/bin/pip install --upgrade -r /home/pi/venv-requirements.txt

echo "Venv packages upgraded!"