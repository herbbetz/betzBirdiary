#!/bin/bash
# shellcheck is a developer lint utility, sudo apt install shellcheck

find /home/pi/station3 -name '*.sh' -print0 \
  | xargs -0 shellcheck 2>&1 | tee shellcheck-report.txt
echo "shellcheck-report.txt created, check for errors/warnings"