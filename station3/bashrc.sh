#!/bin/bash
### loginsetup, called from .bashrc
### beware: 'exit 1' will drop login session, if bashrc.sh is sourced from .bashrc
configfile="$HOME/station3/config.sh"
if [ -f "$configfile" ]; then
    source "$configfile"
else
    echo "not found: $configfile" >&2
    # exit 1
fi    
# Change to station directory on login
if [ -d "$APPDIR" ]; then
    cd "$APPDIR" # || exit 1 # Change directory, exit if it fails
    # echo "Changed to directory: $(pwd)" # Optional: confirm directory change
    chmod +x ./*.sh
    bash "$APPDIR/welcome.sh"
    bash "$APPDIR/diskAlert.sh"
    mail
fi
source "$HOME/activate_birdvenv.sh"