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
    echo "To change to old python3.11 for tensorflow: pyenv activate birdvenv"
    echo "... later return to system Python 3.13: pyenv deactivate"
fi
# for imports in subdir python scripts:
# export PYTHONPATH=$HOME/station3
# but this works only with interactive shells
# and 'Environment=PYTHONPATH=/home/pi/station3' in bird-startup.service works only with scripts called from 'startup.sh' (not with interactive shells)
# => in subdir python scripts use 'BASE_DIR = os.path.abspath(os.path.dirname(__file__))'
# or use empty __init__.py files to make subdirs packages and use relative imports like 'from station3.configBird3 import birdpath'
export PYENV_ROOT="$HOME/.pyenv"
[[ -d $PYENV_ROOT/bin ]] && export PATH="$PYENV_ROOT/bin:$PATH"
eval "$(pyenv init - bash)"
# Load pyenv-virtualenv automatically by adding
# the following to ~/.bashrc:
eval "$(pyenv virtualenv-init -)"

# source "$HOME/activate_birdvenv.sh"
