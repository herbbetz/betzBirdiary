---
layout: default
title: "Debian Package betzbird"
date: 2026-01-10
permalink: /posts/2026-01-10-debianpkg/
---
<!--keywords[betzbird,blog,debianpkg]-->

Ende 2025 las ich in einer Zeitschrift von Jemand, der seine Software als Debian Package anbot. Ich hatte meine Hobbyversion *betzBirdiary* bisher immer in ein Diskimage verpackt. Was ist wohl der Vorteil eines Packages demgegenüber? Nun, ein Vorteil sei laut ChatGPT, dass das zugrunde liegende Betriebssystem über die Software Bescheid wisse. Ich wurde neugierig.

- Natürlich hatte ich wieder eine eigene Spielwiese hinsichtlich meines automatisierten Vogelhäuschens entdeckt. Es gibt eine umfangreiche Debian Package Policy, die sich in einem System von nötigen Buildtools und Config Files abbildet.
- Das Package wird als User gebaut, und zwar am besten auf dem Zielsystem, also einem Raspberry (oder einem Board mit ARM CPU). Es auf dem Laptop mit x68-Prozessor zu bauen, hätte Crosscompiler Tools nötig gemacht und bereits ohne diese benötigt man schon etliche Debian Build Packages: `sudo apt install -y build-essential devscripts debhelper dh-python python3-all`.
- Die wichtigsten Config Files heißen `debian/control /rules /install und /postinst`.  Unterscheide streng davon erzeugte Dateien und Verzeichnisse, wie `debian/betzbird/ und files`. Die erzeugten Dateien sind für das vorbereitende *Staging* der Installation gedacht, aber nicht zum Editieren oder Archivieren (`.gitignore`) .
- Das Package soll an keinen bestimmten User wie `pi` gebunden sein, damit es mit möglichst vielen debian-basierten Distributionen für ARM kompatibel ist, wie Raspberry OS, DietPi, Ubuntu usw. .
- Ich musste mich also für einen Namen meines Packages entscheiden und griff einfach zu `betzbird`. Den App Namen musste ich an mehreren Stellen in die Debian Config Files eintragen und auch laut Debian als Startskript meiner App verwenden. `betzbird.sh` war unerwünscht, trotz Shellskriptinhalt musste es einfach nur `betzbird` heißen. Ich brauchte auch einen User mit Group, der auf allen Systemen gelten sollte. User `betzbird.betzbird` war geboren. Aber es kam noch schlimmer.
- Nach Installation meines ersten Packages sah ich, dass es nach `/usr/betzbird` und `/usr/lib/betzbird` , auf Wunsch partiell auch nach `/usr/share/betzbird` installiert wurde, und zwar für Superuser `root.root`. Alle anderen User müssen `/usr/lib/betzbird` als *readonly* betrachten, denn schreiben darf man nur händische Config Files als Superuser nach `/etc/betzbird` und skriptweise als User nach `/var/log/betzbird` oder `/var/lib/betzbird` oder `/run/betzbird`. Also musste ich die Pfade in den Dateien meines Diskimage komplett neu aufsetzen.
- Dabei dient `/run/betzbird` als TMPFS (temporäres Filesystem, Memory statt SD-Karte) ähnlich einer `Ramdisk` für temporäre häufig geschriebene Betriebsdaten der App. Da es aber nicht nur durch Reboot gelöscht wird und zudem seine Größe nicht vorhersehbar ist, habe ich darauf verzichtet.
- Daten, die nur ab und zu erneuert werden und einen Reboot überleben sollen, gehören nach `/var/lib/betzbird`. Dort habe ich dann auch statt `/run/betzbird` ein eigenes definiertes TMPFS angelegt namens `/var/lib/betzbird/ramdisk`.
- Das `betzbird/` wegzulassen ist übrigens keine gute Idee, da sonst ja auch andere Apps z.B. ein `config.json` haben könnten, es also zu Verwechslungen kommt.
- `lgpio` ist Raspberry OS spezifisch, nicht in Ubuntu (for Pi), systemübergreifend besser ist `lgpiod`.

Feedback an *herber7be7z@gmail.com*. Happy Birding!