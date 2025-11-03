<!--keywords[Desktop,LXQt_Windowmanager,Wayfire_Desktop,Widgets,xdg-Utilities]-->

- Trotz größerem Dateiimage bewährt sich der Desktop in Trixie durch eine schmerzlose WLAN-Einstellung, sowohl bei Erstinstallation über HDMI & Keyboard als auch später für die Einstellung der statischen Adresse via VNC.

- Firefox als Default Browser durch `xdg-settings set default-web-browser firefox.desktop`, verifiziert durch `xdg-settings get default-web-browser`.

- Wenn Browser `chromium` ein `keyring password` möchte, kann das deaktiviert werden, indem mit `seahorse (sudo apt install seahorse), Apps-Accessories-Passwords&Keys` für den `default keyring` ein leeres Passwort gesetzt wird.

- Dateizuordnungen laufen über `xdg-mime default retext.desktop text/markdown` und werden in `~/.config/mimeapps.list` gespeichert. Verifizierbar ist das mit `xdg-mime query default text/markdown`.

**Desktop Links** (`LXQt Windowmanager`)

- Desktop Links in `~/.local/share/applications/` oder  `/home/pi/Desktop` müssen ausführbar gemacht werden mit `chmod +x *.desktop`.

  Beispiel `webgui.desktop`:

  ````
  [Desktop Entry]
  Type=Application
  Name=Browser View
  Exec=xdg-open http://127.0.0.1:8080
  Icon=/home/pi/station3/favicon.svg
  ````
  oder auch `Exec=retext --preview /home/pi/station3/README.md`

- Eine`.desktop` Datei in `~/.local/share/applications/` erscheint in `ApplicationsMenu-Other`, wo sie durch Rechtsklick dem `Launcher (Taskleiste)` oder `Desktop` als Link zugeordnet werden kann. Der Desktop-Link in `~/Desktop` sieht dann so aus:

  ````
  [Desktop Entry]
  Type=Link
  Name=view README
  Icon=/home/pi/station3/favicon.svg
  URL=/home/pi/.local/share/applications/readme.desktop
  ````

**Launcher Plugins** (`wf-panel-pi`)

- die anklickbaren Plugins der Taskleiste sind `.so` Dateien in `/usr/lib/aarch64-linux-gnu/wf-panel-pi`.

**Desktop Widgets** (wayfire `wf-desktop`)

- Transparente Widgets auf dem Desktop sind machbar mit `python/GTK`, siehe `widgets.py`.

- `dpkg -l | grep vnc`zeigt, dass `wayvnc` als VNC Server verwendet wird.

- der Autostart von `station3/widgets.py` ist nur sinnvoll und funktioniert erst, wenn das `wayland_display` garantiert bereit ist. Deshalb wird es durch einen `userspace service` gestartet in ` ~/.config/systemd/user/widgets.service`. Anders als `root services` zum Booten (in `etc/systemd/system`) hat ein `userspace service` Zugriff auf das `env` von `pi`, z.B.  auch auf `"desktop ready" (/run/user/1000/wayland-0)`.

  ````
  cd ~/.config; mkdir systemd; chmod 700 systemd; mkdir user; chmod 700 user
  cd ~/.config/systemd/user; nano widgets.service; chmod 644 widgets.service
  systemctl --user daemon-reload
  systemctl --user enable widgets.service
  systemctl --user start widgets.service
  systemctl --user status widgets.service
  
  ````
  wobei in widgets.service steht:
    ````
    [Unit]
    Description=Bird desktop widgets (Wayfire)
    After=graphical-session.target
    Wants=graphical-session.target
  
    [Service]
    Type=simple
    ExecStart=/usr/bin/python3 /home/pi/station3/widgets.py >> /home/pi/station3/logs/widgets.log 2>&1
    # No Restart= line, so service stops on failure
  
    [Install]
    WantedBy=default.target
    ````



