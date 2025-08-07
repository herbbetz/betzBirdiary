#!/bin/bash
# or 'pip install -r /home/pi/station3/4venv/requirements.txt --upgrade' after doing from (birdvenv) 'pip freeze > 4venv/requirements.txt'
for i in $(pip list --outdated --format=columns | tail -n +3 | cut -d" " -f1);
    do pip install --upgrade $i;
    done