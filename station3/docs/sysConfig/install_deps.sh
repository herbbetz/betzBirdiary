#!/bin/bash
# run using: sudo bash install_deps.sh
# Check if script is running as root
if [ "$EUID" -ne 0 ]; then 
  echo "Please run as root (use sudo)"
  exit 1
fi

echo "--- Updating package lists ---"
apt update

# List of required dependencies
DEPENDENCIES=(
    python3
    python3-requests
    python3-lgpio
    python3-picamera2
    libcamera-apps
    libcamera-tools
    bc
    curl
    jq
    screen
    ffmpeg
    mosquitto-clients
    python3-ephem
    python3-flask
    python3-markdown
    python3-matplotlib
)

echo "--- Checking and installing dependencies ---"

for package in "${DEPENDENCIES[@]}"; do
    if dpkg -l | grep -qw "$package"; then
        echo "[INSTALLED] $package is already present."
    else
        echo "[MISSING] $package. Installing..."
        apt install -y "$package"
        
        if [ $? -eq 0 ]; then
            echo "[SUCCESS] $package installed successfully."
        else
            echo "[ERROR] Failed to install $package." >&2
        fi
    fi
done

echo "--- Installation process complete ---"