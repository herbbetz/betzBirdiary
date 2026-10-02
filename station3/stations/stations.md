<!--keywords[rare_birds,Stations,Videoking]-->

- im Verzeichnis `stations/`  werden vorab `stations.json` und `stations.js` durch `stations.py`von `https://wiediversistmeingarten.org/api/station` heruntergeladen.
- Dies passiert über `startLateBird.service` und `startLateNet.sh` bei jedem Hochfahren der Station.
- Siehe dazu auch `docs/api/birdiaryAPI.md`.
- Später werden daraus `action - rare birds` und `- videoking` bedient.
- Für Videoking ist wichtig, dass `stations.json` aktuell ist, besonders das `lastMovement` der jeweiligen Station, die sonst für letzten Monat nicht angezeigt werden kann.
- Für den Auswahldialog in `stations/` und Videoking ist wieder das Verzeichnis `select/` zuständig (wie bei `validate/`).