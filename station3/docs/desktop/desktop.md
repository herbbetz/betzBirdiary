<!--keywords[Desktop,xdg-Utilities]-->

- Trotz größerem Dateiimage bewährt sich der Desktop in Trixie durch eine schmerzlose WLAN-Einstellung, sowohl bei Erstinstallation über HDMI & Keyboard als auch später für die Einstellung der statischen Adresse via VNC.

- Firefox als Default Browser durch `xdg-settings set default-web-browser firefox.desktop`, verifiziert durch `xdg-settings get default-web-browser`.

- Desktop Links in `/home/pi/Desktop` müssen ausführbar gemacht werden mit `chmod +x *.desktop`.

  Beispiel `webgui.desktop`:

  ````
  [Desktop Entry]
  Type=Application
  Name=Browser View
  Exec=xdg-open http://127.0.0.1:8080
  Icon=/home/pi/station3/favicon.svg
  ````
- Dateizuordnungen laufen über `xdg-mime default retext.desktop text/markdown` und werden in `~/.config/mimeapps.list` gespeichert. Verifizierbar ist das mit `xdg-mime query default text/markdown`.
- Eine Kopie der `.desktop` Dateien nach `~/.local/share/applications/` listet die Programme in `ApplicationsMenu-Other`, wo sie durch Rechtsklick dem `Launcher (Topleiste)` oder `Desktop` zugeordnet werden können im `LXQt Windowmanager`.
- Wenn Browser `chromium` ein `keyring password` möchte, kann das deaktiviert werden, indem mit `seahorse (sudo apt install seahorse), Apps-Accessories-Passwords&Keys` für den `default keyring` ein leeres Passwort gesetzt wird.