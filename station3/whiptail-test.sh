#!/bin/bash
# whiptail just hanging inside a script (not interactively on cmd line) because of conflicts between script stdin/out and those expected by whiptail
tempfile=$(mktemp)
whiptail --inputbox "Enter test" 8 40 --title "Direct test" < /dev/tty > /dev/tty 2> "$tempfile"
answer=$(< "$tempfile")
rm "$tempfile"
echo "You entered: $answer"
