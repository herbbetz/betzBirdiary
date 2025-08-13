#!/bin/bash

# Check if script is run as root or via sudo
if [ "$EUID" -ne 0 ]; then
    echo "Please run as root or with 'sudo ./${0##*/}'"
    exit 1
fi

set -e

CON_NAME="bird-static210"
OLD_CON="bird-ap-dhcp"

# Create or modify the connection
# Check if the connection already exists
if ! nmcli connection show "$CON_NAME" &>/dev/null; then
    echo "Connection '$CON_NAME' not found."
    exit 1
fi

# Validate non-empty SSID
while true; do
    read -rp "Enter WLAN SSID: " SSID
    if [[ -z "$SSID" ]]; then
        echo "SSID cannot be empty. Please enter a valid SSID."
    else
        break
    fi
done

# Validate password length (e.g., WPA2 requires at least 8 chars)
while true; do
    read -rp "Enter WLAN Password (min 8 chars): " PSK
    echo
    if [[ ${#PSK} -lt 8 ]]; then # '#PSK' is length of PSK
        echo "Password must be at least 8 characters."
    else
        break
    fi
done

# Simple IPv4 validation function
valid_ip() {
    local ip=$1
    # Strip leading/trailing whitespace
    ip="${ip#"${ip%%[![:space:]]*}"}"  # trim leading whitespace
    ip="${ip%"${ip##*[![:space:]]}"}"  # trim trailing whitespace

    local IFS=.
    local -a octets=($ip) # leave $ip unquoted, else octets will not be an array of 4 elems derived from ip split at the dots
    [[ ${#octets[@]} -eq 4 ]] || return 1
    for octet in "${octets[@]}"; do
        [[ $octet =~ ^[0-9]+$ ]] || return 1
        ((octet >= 0 && octet <= 255)) || return 1
    done
    return 0
}

while true; do
    read -rp "Enter IPv4 Address (e.g. 192.168.178.210): " IPADDR
    if valid_ip "$IPADDR"; then
        break
    else
        echo "Invalid IPv4 address format."
    fi
done

while true; do
    read -rp "Enter Gateway (e.g. 192.168.178.1): " GATEWAY
    if valid_ip "$GATEWAY"; then
        break
    else
        echo "Invalid Gateway IP format."
    fi
done

# Apply settings using nmcli modify
echo "Applying new settings to '$CON_NAME'..."

nmcli connection modify "$CON_NAME" wifi.ssid "$SSID"
nmcli connection modify "$CON_NAME" wifi-sec.key-mgmt wpa-psk wifi-sec.psk "$PSK"

# Set static IP configuration
nmcli connection modify "$CON_NAME" ipv4.method manual
nmcli connection modify "$CON_NAME" ipv4.addresses "${IPADDR}/24"
nmcli connection modify "$CON_NAME" ipv4.gateway "$GATEWAY"
nmcli connection modify "$CON_NAME" ipv4.dns "$GATEWAY"

# Enable autoconnect for the new connection
# nmcli connection modify "$CON_NAME" connection.autoconnect yes
echo "setting autoconnect priority of '$CON_NAME' over '$OLD_CON'..."
nmcli connection modify "$CON_NAME" connection.autoconnect yes connection.autoconnect-priority 100
# Disable autoconnect for the old connection
# echo "Disabling autoconnect for '$OLD_CON'..."
# nmcli connection modify "$OLD_CON" connection.autoconnect no
echo
echo "Reloading NetworkManager to apply changes..."
nmcli connection reload
sleep 3 # give time for reload

# Let user review the connection settings
echo
echo "Current configuration for '$CON_NAME':"
echo "----------------------------------------"
# nmcli -g all connection show "$CON_NAME" # this or 'nmcli connection show "$CON_NAME"' will show to many settings
cat "/etc/NetworkManager/system-connections/$CON_NAME.nmconnection"
echo "----------------------------------------"

echo
read -rp "Configuration saved. Reboot now to apply changes? (y/N): " reboot_confirm
if [[ "$reboot_confirm" =~ ^[Yy]$ ]]; then
# Use 'nohup' to run the remaining commands in the background
# This ensures they execute even after your SSH session disconnects
    setsid bash -c "sleep 5 && sudo nmcli connection up '$CON_NAME'" > logs/wlanChg.log 2>&1 & # setsid or nohup?
    shutdown -r +1
else
    echo "Please reboot later to apply the changes."
fi
