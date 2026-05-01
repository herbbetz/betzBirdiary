#!/bin/bash
# run using: sudo bash setup_system.sh

if [ "$EUID" -ne 0 ]; then 
  echo "Please run as root"
  exit 1
fi

PROJECT_DIR="/home/pi/station3"

echo "--- 1. Configuring Ramdisk ---"
if ! grep -q "station3/ramdisk" /etc/fstab; then
    mkdir -p $PROJECT_DIR/ramdisk
    echo "tmpfs  $PROJECT_DIR/ramdisk  tmpfs  nodev,nosuid,size=50M  0  0" >> /etc/fstab
    mount -a
    echo "[SUCCESS] Ramdisk added to fstab and mounted."
else
    echo "[SKIP] Ramdisk already in fstab."
fi

echo "--- 2. Installing Logrotate ---"
cp "$PROJECT_DIR/birdlogrotate" /etc/logrotate.d/
chmod 644 /etc/logrotate.d/birdlogrotate
echo "[SUCCESS] Logrotate config installed."

echo "--- 3. Installing Systemd Services ---"
SERVICES=("bird-startup.service" "bird15m.service" "bird15m.timer")
for service in "${SERVICES[@]}"; do
    cp "$PROJECT_DIR/$service" /etc/systemd/system/
    systemctl daemon-reload
    systemctl enable "$service"
    systemctl start "$service"
    echo "[SUCCESS] Service $service enabled and started."
done

echo "--- 4. Creating Desktop Link ---"
DESKTOP_DIR="/home/pi/Desktop"
mkdir -p "$DESKTOP_DIR"
cat <<EOF > "$DESKTOP_DIR/Widgets.desktop"
[Desktop Entry]
Type=Application
Name=Bird Widgets
Exec=python3 $PROJECT_DIR/widgets.py
Terminal=false
Categories=Utility;
EOF
# Allow execution without confirmation (for Wayfire/Labwc on Trixie)
chown pi:pi "$DESKTOP_DIR/Widgets.desktop"
chmod +x "$DESKTOP_DIR/Widgets.desktop"
gio set "$DESKTOP_DIR/Widgets.desktop" metadata::trusted true 2>/dev/null || true

echo "--- 5. Appending to .bashrc (pi & root) ---"
CMDS="\nalias ls='ls -lah'\nalias birds='screen -ls'\ncd $PROJECT_DIR"
# For pi
echo -e "$CMDS" >> /home/pi/.bashrc
# For root
echo -e "$CMDS" >> /root/.bashrc

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

echo "--- All System Configurations Complete ---"