#!/bin/bash
# run using: sudo bash setup_system.sh
ME=$(basename "$0")
if [ "$EUID" -ne 0 ]; then 
  echo "Run as root (sudo bash $ME)"
  exit 1
fi

PROJECT_DIR="/home/pi/station3"
TEMPLATE_DIR=$PROJECT_DIR/docs/sysConfig

echo "--- 1. Configuring Ramdisk ---"
# fstab has 644
if ! grep -q "station3/ramdisk" /etc/fstab; then
    mkdir -p $PROJECT_DIR/ramdisk
    echo "tmpfs  $PROJECT_DIR/ramdisk  tmpfs defaults,size=50M,noatime,uid=1000,gid=1000,mode=0700 0 0" >> /etc/fstab
    mount -a
    echo "[SUCCESS] Ramdisk added to fstab and mounted."
else
    echo "[SKIP] Ramdisk already in fstab."
fi

echo "--- 2. Installing System Config Files ---"
# Define destination as a key-value pair if you have many subdirs, 
# but for this scale, two arrays or a simple loop works best:

ETC_FILES=("environment" "hostname" "hosts")

for file in "${ETC_FILES[@]}"; do
    if [ -f "$TEMPLATE_DIR/$file" ]; then
        cp "$TEMPLATE_DIR/$file" /etc/
        chown root:root "/etc/$file"
        chmod 644 "/etc/$file"
        echo "[SUCCESS] /etc/$file installed."
    else
        echo "[ERROR] $file not found in $TEMPLATE_DIR" >&2
    fi
done

# Handle logrotate separately since it has a unique destination
if [ -f "$TEMPLATE_DIR/birdlogrotate" ]; then
    cp "$TEMPLATE_DIR/birdlogrotate" /etc/logrotate.d/
    chown root:root /etc/logrotate.d/birdlogrotate
    chmod 644 /etc/logrotate.d/birdlogrotate
    echo "[SUCCESS] Logrotate config installed."
fi

echo "--- 3. Installing Systemd Services ---"
SERVICES=("bird-startup.service" "bird15m.service" "bird15m.timer")
for service in "${SERVICES[@]}"; do
    cp "$TEMPLATE_DIR/$service" /etc/systemd/system/
    chown root:root "/etc/systemd/system/$service"
    chmod 644 "/etc/systemd/system/$service"    
    systemctl enable "$service"
    systemctl start "$service"
    echo "[SUCCESS] Service $service enabled and started."
done
systemctl daemon-reload

echo "--- 4. Creating Desktop Link ---"
DESKTOP_DIR="/home/pi/Desktop"
# mkdir -p just moves on, if Desktop/ already exists:
mkdir -p "$DESKTOP_DIR"
cat <<EOF > "$DESKTOP_DIR/Widgets.desktop"
[Desktop Entry]
Type=Application
Name=BirdWidget
Exec=python3 $PROJECT_DIR/widgets.py
Terminal=false
Categories=Utility;
EOF
# Allow execution without confirmation (for Wayfire/Labwc on Trixie)
chown pi:pi "$DESKTOP_DIR/Widgets.desktop"
chmod +x "$DESKTOP_DIR/Widgets.desktop"
gio set "$DESKTOP_DIR/Widgets.desktop" metadata::trusted true 2>/dev/null || true

echo "--- 5. Appending to .bashrc (pi & root) ---"
# define a heredoc:
read -r -d '' BASH_APPEND << 'EOF'
### betzBirdiary:
alias px='ps aux|grep -e "^pi" -e "gpio"' # not only ^pi but also pigpiod/lgpiod is wanted
loginsetup="$HOME/station3/bashrc.sh"
if [ -f "$loginsetup" ]; then
    source "$loginsetup" # bash $loginsetup would execute in a subshell, we need execute it in login shell
else
    echo "not found: $loginsetup" >&2
fi
EOF

if ! grep -q "betzBirdiary" /home/pi/.bashrc; then
    echo "$BASH_APPEND" >> /home/pi/.bashrc
    echo "[SUCCESS] Appended to /home/pi/.bashrc"
fi

# For root
read -r -d '' ROOT_APPEND << 'EOF'
### betzBirdiary:
/home/pi/station3/welcomeroot.sh
EOF

if ! grep -q "betzBirdiary" /root/.bashrc; then
    echo "$ROOT_APPEND" >> /root/.bashrc
    echo "[SUCCESS] Appended to /root/.bashrc"
fi

echo "--- 6. Reconfiguring Exim4 (Local Only) ---"
# This non-interactive command sets exim4 to local delivery only
DEBCONF_DB_FALLBACK='File{/var/cache/debconf/config.dat}' \
debconf-set-selections <<EOF
exim4-config exim4/dc_eximconfig_configtype string local delivery only; not on a network
exim4-config exim4/dc_local_interfaces string 127.0.0.1 ; ::1
exim4-config exim4/dc_readhost string $(hostname)
exim4-config exim4/dc_postmaster string pi
EOF
dpkg-reconfigure -f noninteractive exim4-config

echo "--- 7. Initializing Mailboxes ---"
# Set directory permissions (1777 allows users to create files but not delete others')
chmod 1777 /var/mail

# Create pi mailbox if it doesn't exist
if [ ! -f /var/mail/pi ]; then
    touch /var/mail/pi
    chown pi:mail /var/mail/pi
    chmod 660 /var/mail/pi
    echo "[SUCCESS] Mailbox for pi initialized."
fi

# Send a test mail to trigger the system
echo "Station3 setup complete on $(date)" | mail -s "System Ready" pi

# Run this script only from inside its own directory:
cd /home/pi/station3 && python3 build_md_contents.py
echo "--- All System Configurations Complete ---"
sleep 2
echo "--- rebooting ... ---"
# to activate .bashrc and avoid starting several instances of mainFoBird3:
reboot