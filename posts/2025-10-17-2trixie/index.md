---
layout: default
title: "betzBirdiary update auf Trixie und Fernsupport"
date: 2025-10-17
permalink: /posts/2025-10-17-2trixie/
---
<!--keywords[blog,Fernsupport,Installation,Trixie]-->
**Trixie-Portierung**

Die Portierung von `betzBirdiary` auf das diesen Monat erschienene Raspbian Trixie (Debian 13) verlief doch unerwartet reibungslos. Der Sprung im Sommer 25 von Bullseye auf Bookworm (erschienen 12/2023) war deutlich größer, weil sich Bookworm schon 18 Monate fortentwickelt hatte. Die Trixie-Version von betzBirdiary findet sich [hier](https://drive.google.com/drive/folders/11WduKyMzzzmW61bC7l0BlDjjx6e_ImHC) zum Download und Feedback. Ist die WLAN-Verbindung zum Heimrouter hergestellt und das crontab mit `crontab crontab.txt` aktiviert, aktualisiert sich das laufende Image monatlich selbst (, was man in crontab aber auch auskommentieren kann).

Gerade das zum Einstieg nötige Networking über LAN oder WLAN hat sich in Trixie aber wiederum verkompliziert zu einer Mischung aus `netplan` und `NetworkManager`. Jedes `nmcli connection add ...` oder `nmcli connection delete...` erzeugt ein `yaml` in `/etc/netplan`, siehe `station3/WLAN/wlan-howto.md` und `station3/easy_install.md`.

Deshalb ist meine Trixie-Version wieder von `headless` (Trixie light 64bit) zur Desktop-Vollversion als Basis zurückgekehrt. Einfaches Klicken auf das WLAN-Konnektion-Symbol rechts oben und schon funktionierts ohne Kopfschmerzen, auch mit dem Wechsel auf eine statische `IP4`.

Python kommt anders als in `bookworm` unter `trixie` auch wieder ohne `venv` und `pip` zurecht, also weg damit und nur noch Pythonmodule über `apt` installiert.



**Fernsupport mit ngrok**

In dieser neuen Version gibt es jetzt auch eine Möglichkeit zur Fernwartung. Sie basiert auf dem "reverse tunnel service" [*ngrok*](https://ngrok.com/), und muss erst vom Benutzer der Software angestoßen werden. Sie ist also nicht etwa eine "backdoor", sondern geschieht erst auf Anforderung durch den Nutzer, der dann temporäre Zugangsdaten über einen sicheren Messenger (wie Signal) an mich als Unterstützer mitteilt. Schließt der Nutzer das ngrok Fenster auf seinem Raspberry, ist der Support-SSH-Zugang wieder getrennt. Reverse Tunneling braucht auch keine Portfreigabe im Heimrouter des Benutzers. Voraussetzung für den kostenlosen Fernsupport ist natürlich die Verbindung zum Heimrouter. Die erreicht man am leichtesten mit einem Ethernet Kabel zum RPi4 oder wenn man das Image mit 'RPi Imager' geflasht hat und dabei zuvor seine WLAN-Daten dort konfiguriert hat (CTRL-Shift-X).

Angesichts der vielen grauen Häuschen finde ich das Thema "Fernsupport der Software" interessant. Gibt es zu Fernwartung andere Empfehlungen von Euch?

Feedback an *herber7be7z@gmail.com*. Happy Birding!