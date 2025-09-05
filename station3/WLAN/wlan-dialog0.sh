#!/bin/bash
# direct .connection editing necessary as this will fail for connection test (id=test in testXXX.nmconnection): 
#   sudo nmcli connection modify test 802-11-wireless-security.psk "blubber"
#   because it will not change a hashed PW. A manually edited password is probably hashed by NetworkManager on first use.
# graphical command line UIs like whiptail or dialog will fail, because of STDIN/OUT conflicts when run in bash scripts
#
# Check if script is run as root or via sudo
if [ "$EUID" -ne 0 ]; then
    echo "Please run as root or with 'sudo ./${0##*/}'"
    exit 1
fi

set -e

CON_NAME="bird-static210"
OLD_CON="bird-ap-dhcp"
NM_DIR="/etc/NetworkManager/system-connections"
FILE="$NM_DIR/$CON_NAME.nmconnection"

if [ ! -f "$FILE" ]; then
    echo "File $FILE not found!"
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
SSID="${SSID//[[:space:]]/}"  # remove all whitespace

# Validate password length (e.g., WPA2 requires at least 8 chars)
# read -rsp will not echo PW
while true; do
  read -rp "Enter WLAN Password (min 8 chars): " PSK
  echo
  if [[ ${#PSK} -lt 8 ]]; then # '#PSK' is length of PSK
    echo "Password must be at least 8 characters."
  else
    break
  fi
done
PSK="${PSK//[[:space:]]/}"

# Simple IPv4 validation function
valid_ip() {
  local ip=$1
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
IPADDR="${IPADDR//[[:space:]]/}"

while true; do
  read -rp "Enter Gateway (e.g. 192.168.178.1): " GATEWAY
  if valid_ip "$GATEWAY"; then
    break
  else
    echo "Invalid Gateway IP format."
  fi
done
GATEWAY="${GATEWAY//[[:space:]]/}"

# read -rp "Enter DNS Servers (space-separated): " DNS

# Escape slashes and special chars in variables for sed
esc() {
  echo "$1" | sed 's/[\/&]/\\&/g'
}

SSID_esc=$(esc "$SSID")
PSK_esc=$(esc "$PSK")
IPADDR_esc=$(esc "$IPADDR")
GATEWAY_esc=$(esc "$GATEWAY")

# Set DNS to gateway with semicolon appended
DNS_esc="${GATEWAY_esc};"

# Replace ssid in [wifi]
sed -i "/^\[wifi\]/, /^\[/ s/^ssid=.*/ssid=$SSID_esc/" "$FILE"

# Replace psk in [wifi-security]
sed -i "/^\[wifi-security\]/, /^\[/ s/^psk=.*/psk=$PSK_esc/" "$FILE"

# Replace address1 in [ipv4]
sed -i "/^\[ipv4\]/, /^\[/ s/^address1=.*/address1=${IPADDR_esc}\/24,${GATEWAY_esc}/" "$FILE"

# Replace dns in [ipv4]
sed -i "/^\[ipv4\]/, /^\[/ s/^dns=.*/dns=$DNS_esc/" "$FILE"

echo "Updated $FILE successfully."

echo "Reloading NetworkManager connections..."
nmcli connection reload
sleep 3 # give time for reload

# Enable autoconnect for 'test'
nmcli connection modify "$CON_NAME" connection.autoconnect yes

# Disable autoconnect for 'bird-ap-dhcp'
nmcli connection modify "$OLD_CON" connection.autoconnect no

# Let user review .nmconnection file
echo
echo "Contents of $FILE:"
echo "----------------------------------------"
cat "$FILE"
echo "----------------------------------------"

echo
read -rp "Configuration saved. Reboot now to apply changes? (y/N): " reboot_confirm
if [[ "$reboot_confirm" =~ ^[Yy]$ ]]; then
  reboot
else
  echo "Please reboot later to apply the changes."
fi