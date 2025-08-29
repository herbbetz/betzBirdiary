#!/bin/bash

# Check if script is run as root or via sudo
if [ "$EUID" -ne 0 ]; then
    echo "Please run as root or with 'sudo ./${0##*/}'"
    exit 1
fi

set -e

# WLAN_YML="wlan.yml"
if [[ $# -ne 1 ]]; then
    echo "Usage: ${0##*/} <yaml_file>"
    exit 1
fi
WLAN_YML="$1"
if [ ! -f "$WLAN_YML" ]; then
    echo "YAML file '$WLAN_YML' not found."
    exit 1
fi

## You need yq installed for YAML parsing
#if ! command -v yq >/dev/null 2>&1; then
#    echo "This script requires 'yq' (YAML parser). Install it with:"
#    echo "  sudo apt install yq"
#    exit 1
#fi
## Read values from YAML
#CON_NAME=$(yq '.con_name' "$WLAN_YML")

# Function to read key:value from YAML without yq, as long as simplest flat YAML
get_yaml_value() {
    local key=$1
    grep -E "^${key}:" "$WLAN_YML" | sed -E "s/^${key}:[[:space:]]*//" | tr -d '"' | tr -d '\r' # Remove quotes and carriage returns from win11
}

CON_NAME="bird-static210"
OLD_CON="bird-ap-dhcp"
SSID=$(get_yaml_value "ssid")
PSK=$(get_yaml_value "psk")
IPADDR=$(get_yaml_value "ipaddr")
GATEWAY=$(get_yaml_value "gateway")

# Simple IPv4 validation function
valid_ip() {
    local ip=$1
    # Strip leading/trailing whitespace and carriage returns
    # ip="${ip//$'\r'/}"           # remove carriage returns is already done by get_yaml_value()
    ip="${ip#"${ip%%[![:space:]]*}"}"  # trim leading whitespace
    ip="${ip%"${ip##*[![:space:]]}"}"  # trim trailing whitespace

    local IFS=.
    local -a octets=($ip)
    [[ ${#octets[@]} -eq 4 ]] || return 1
    for octet in "${octets[@]}"; do
        [[ $octet =~ ^[0-9]+$ ]] || return 1
        ((octet >= 0 && octet <= 255)) || return 1
    done
    return 0
}

# Validation
if [[ -z "$SSID" ]]; then
    echo "SSID is missing in '$WLAN_YML'."
    exit 1
fi

if [[ ${#PSK} -lt 8 ]]; then
    echo "Password must be at least 8 characters."
    exit 1
fi

if ! valid_ip "$IPADDR"; then
    echo "Invalid IP address format in '$WLAN_YML'."
    exit 1
fi

if ! valid_ip "$GATEWAY"; then
    echo "Invalid Gateway IP format in '$WLAN_YML'."
    exit 1
fi

# Check if the connection exists
if ! nmcli connection show "$CON_NAME" &>/dev/null; then
    echo "Connection '$CON_NAME' not found."
    exit 1
fi

# Apply settings
echo "Applying new settings to '$CON_NAME'..."
nmcli connection modify "$CON_NAME" wifi.ssid "$SSID"
nmcli connection modify "$CON_NAME" wifi-sec.key-mgmt wpa-psk wifi-sec.psk "$PSK"
nmcli connection modify "$CON_NAME" ipv4.method manual
nmcli connection modify "$CON_NAME" ipv4.addresses "${IPADDR}/24"
nmcli connection modify "$CON_NAME" ipv4.gateway "$GATEWAY"
nmcli connection modify "$CON_NAME" ipv4.dns "$GATEWAY"

echo "Setting autoconnect priority of '$CON_NAME' over '$OLD_CON'..."
nmcli connection modify "$CON_NAME" connection.autoconnect yes connection.autoconnect-priority 100

echo
echo "Reloading NetworkManager..."
nmcli connection reload
sleep 3

echo
echo "Current configuration for '$CON_NAME':"
echo "----------------------------------------"
# nmcli -g all connection show "$CON_NAME" # this or 'nmcli connection show "$CON_NAME"' will show to many settings
cat "/etc/NetworkManager/system-connections/$CON_NAME.nmconnection"
echo "----------------------------------------"

echo
read -rp "Configuration saved. Reboot now to apply changes? (y/N): " reboot_confirm
if [[ "$reboot_confirm" =~ ^[Yy]$ ]]; then
    setsid bash -c "sleep 5 && sudo nmcli connection up '$CON_NAME'" > logs/wlanChg.log 2>&1 &
    shutdown -r +1
else
    echo "Please reboot later to apply the changes."
fi