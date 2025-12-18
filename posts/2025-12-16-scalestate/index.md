---
layout: default
title: "Fehlauslösung der Waage"
date: 2025-12-16
permalink: /posts/2025-12-16-scalestate/
---
<!--keywords[blog,Fehlvideo,hx711,state_maschine,Waage]-->

Im Dezember 2025 bemerkte ich plötzlich eine Reihe Fehlauslösungen meiner Vogelwaage, die zu einer Reihe vogelloser Videos führten. Wie frustrierend. In der Discord-Onlinesitzung sprach ich das auch an. Vielleicht ist das ja ein wenig beachtetes Problem, das unnötig Speicherressourcen auf der Plattform verschwendet? Wie häufig tritt das bei allen Vogelstationen auf und ist die KI schon fähig, vogellose Videos zu löschen? ChatGPT weißt auf mehrere programmtechnische Maßnahmen hin, mit der die Software zur Waage das verhindern könnte.

**Ausgangslage**

- Der Wäagebalken ist eine Aluminiumstange mit aufgeklebter Widerstandsbrücke. Die reagiert nicht nur auf Gewicht, sondern auch auf schnelle Wärmeschwankungen oder elektrische Instabilität (Messausreißer, Kaltlötstellen, Diskonnektion). Die HX711-Platine verwandelt den Strom durch die Widerstandsbrücke in digitale Messwerte, die über eine Treibersoftware ausgelesen werden.
- Für jedes Waagensystem muss dann ermittelt werden, welcher digitale Werte 0 Gramm entspricht (Variable `hxOffset`) und um wieviel sich der digitale Wert pro Gramm verändert (Variable `hxScale`).
-  Diskonnektion zeigt sich in *exakt* demselben Messwert nahe 0.0 oder über 100.0 über viele Messzyklen ohne die üblichen Minischwankungen.
- Immer wieder sind auch einzelne Messausreißer ("signal noise") unter den sonst ruhigen Baseline-Messungen zu beobachten. Die seien laut chatGPT charakteristisch für ein Timingproblem des hx711-Treibers (*300–400 g is a classic “one bit shifted” value.*).
- Auch nach erfolgter Eichung mit einem bekannten Gewicht führen Tagestemperaturschwankungen zu einer Drift der Nullage. Diese kann schneller stattfinden, wenn eine Wolke plötzlich die Sonne freigibt oder sich Wetterlagen wie jetzt im Winter von -4 °C schnell auf  +20°C drehen.
- Deshalb macht die Treibersoftware gelegentlich einen Reset ("Tare"), der aber durch gleichzeitige Vogelaktivität gestört werden könnte. Ein Vogel kann auch schon mal eine Minute auf der Stange rasten und so ein übermäßig langes, langweiliges Video produzieren.
- Je nach Stangengröße variiert das Gewicht der Vögel zwischen 8 Gramm und 250 Gramm. Gelegentlich streift auch nur ein Flügel die Sitzstange.

**Vogelerkennung**
- Angestrebt wird eine Vogelerkennung der Waage über 90%. Dazu verhelfen plausible Gewichtsfenster und plausible Zeitfenster des Gewichtsverlaufes.
- Die Baseline sollte nach Eichung um die Null schwanken. Minischwankungen legen ein vitales und reaktives Messystem nahe.
- Die langsame Temperaturdrift des Tages muss angepasst werden durch Retarierung der Baseline. Die Baseline kann kontinuierlich durch *EMA (Exponential Moving Average)* und intervallmäßig durch Sampling (50 "unverdächtige" Werte der letzten 50 Sekunden) und folgliche Anpassung des `hxOffset` geschehen.
- Ein Vogel oder sonstiges Tier auf der Sitzstange ist wahrscheinlich, wenn aus ruhiger Basismessung mehrmals ohne Unterbrechung hintereinander ein überschwelliges, aber auch nicht zu großes Gewicht (zwischen 5 und 300 Gramm) gemessen wird. Dann soll eine Videoaufnahme von einigen Sekunden ausgelöst werden, durch die der Vogel später identifiziert werden kann.
- Weder darf die Baseline-Temperaturanpassung die Vogelbewegung verdecken noch soll die Vogelbewegung auf die Baseline-Tarierung Einfluss nehmen. Deshalb habe ich jetzt auf Vorschlag von chatGPT in Python eine *State Machine* implementiert, die klar zwischen 3 Zuständen unterscheidet, nämlich der Baseline, dem Vogelsitz und einem Entscheidungsstadium dazwischen. Das entspricht dem Status `IDLE, SURGE_CONFIRMED und SURGE_CANDIDATE` in `hyFiBirdState.py`. Die *State Machine* löste einen immer schwerer zu pflegenden Baum aus *If-Bedingungen* ab.



Insgesamt habe ich das Gefühl, erst an der Oberfläche der professionellen Signalverarbeitung gekratzt zu haben, selbst wenn es sich nur um eine simple Vogelsitzstange handelt. Ich hoffe, dass ich nicht durch weitere Fehlvideos noch tiefer in dieses Thema einsteigen muss.

Feedback an *herber7be7z@gmail.com*. Happy Birding!