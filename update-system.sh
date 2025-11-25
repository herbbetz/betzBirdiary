#!/bin/bash
sudo apt update
sudo apt upgrade -y
sudo apt autoremove -y

echo "Update complete! Press enter to exit."
read -r # for 'screen update-system.sh', Ctrl-A,D to be left open to reattach using 'screen -r', when long update finishes that was started in ssh session
# alternative: './your_script.sh > update.log 2>&1 &', then 'disown' to detach from ssh session and later 'cat update.log' or 'tail -f update.log' to watch progress

# /home/pi/birdvenv/bin/pip install --upgrade pip

# Export only venv packages by --local (not system)
# /home/pi/birdvenv/bin/pip freeze --local > /home/pi/venv-requirements.txt

# Upgrade all packages in the requirements file
# /home/pi/birdvenv/bin/pip install --upgrade -r /home/pi/venv-requirements.txt

# echo "Venv packages upgraded!"
