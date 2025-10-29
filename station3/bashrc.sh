#!/bin/bash
### loginsetup, called from .bashrc
### beware: 'exit 1' will drop login session, if bashrc.sh is sourced from .bashrc
# Change to station directory on login
APPDIR="$HOME/station3"
if [ -d "$APPDIR" ]; then
    cd "$APPDIR" # || exit 1 # Change directory, exit if it fails
    # echo "Changed to directory: $(pwd)" # Optional: confirm directory change
    chmod +x ./*.sh
    bash "$APPDIR/welcome.sh"
    bash "$APPDIR/diskAlert.sh"
    mail
fi
# source "$HOME/activate_birdvenv.sh"
