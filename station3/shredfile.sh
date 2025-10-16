#!/bin/bash

# shredfile.sh - A script to securely delete a file using the 'shred' command.
#
# Usage: ./shredfile.sh <filename>
#
# The script checks if a filename is provided and if the file exists before
# attempting to securely shred and delete it. It uses the following options:
#
# -u: Deallocates and removes the file after overwriting.
# -z: Adds a final overwrite with zeros to hide shredding.
# -v: Enables verbose mode to show the progress.
# -n 3: three times overwrite
# journaled file system (ext3, ext4) and solid state drive (SSD) with wear leveling might still be recoverable.

# Check if a filename argument was provided
if [ -z "$1" ]; then
    echo "Error: No filename provided."
    echo "Usage: $0 <filename>"
    exit 1
fi

FILE="$1"

# Check if the file exists
if [ ! -e "$FILE" ]; then
    echo "Error: File '$FILE' not found."
    exit 1
fi

echo "Shredding and securely deleting '$FILE'..."

# Use the shred command to overwrite and delete the file
if shred -u -n 3 -z -v "$FILE"; then
    echo "Successfully shredded and deleted '$FILE'."
else
    echo "An error occurred during shredding of '$FILE'."
fi

exit 0