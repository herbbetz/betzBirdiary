#!/bin/bash
# chatGPT 5.7.25, each .nmconnection needs its own uuid
# Set the directory containing .nmconnection files
CONNECTION_DIR="/etc/NetworkManager/system-connections"

# Check if the directory exists
if [ ! -d "$CONNECTION_DIR" ]; then
    echo "❌ Directory $CONNECTION_DIR does not exist."
    exit 1
fi

echo "🔍 Checking for duplicate UUIDs in $CONNECTION_DIR..."

# Extract UUIDs and filenames
grep -h -r '^uuid=' "$CONNECTION_DIR" | cut -d= -f2 | sort | uniq -d > /tmp/duplicate_uuids.txt

if [ -s /tmp/duplicate_uuids.txt ]; then
    echo "⚠️ Duplicate UUIDs found:"
    while read -r uuid; do
        echo "UUID: $uuid"
        grep -r "uuid=$uuid" "$CONNECTION_DIR" | awk -F: '{print "  ↳ " $1}'
    done < /tmp/duplicate_uuids.txt
    exit 2
else
    echo "✅ No duplicate UUIDs found."
    exit 0
fi
