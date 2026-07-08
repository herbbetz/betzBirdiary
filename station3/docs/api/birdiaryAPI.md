<!--keywords[API,Statistik_API]-->

siehe die [API Doc](https://wiediversistmeingarten.org/doc/) auf https://wiediversistmeingarten.org/doc/

Das REST-API akzeptiert CRUD (create-read-update-delete) Kommandos von *request* Modul. Wird ein API-Key benötigt, ist er als "Stationsschlüssel" nach dem Einloggen zu sehen.

Die Birdiary Website zeigt Statistiken [aller Stationen](https://www.wiediversistmeingarten.org/view/statistics) und von jeder [einzelnen](https://www.wiediversistmeingarten.org/view/statistics/87bab185-7630-461c-85e6-c04cf5bab180) (https://www.wiediversistmeingarten.org/view/statistics bzw. /stationId).  Die Statistiken kommen von folgender API, aus der man auch eigene Grafiken erstellen kann.

Die Birdiary Website bietet ein API, das pro Station hochgeladene Videos und Umweltdaten listet:

- Videos: https://wiediversistmeingarten.org/api/movement/87bab185-7630-461c-85e6-c04cf5bab180
- Umweltdaten: https://wiediversistmeingarten.org/api/environment/87bab185-7630-461c-85e6-c04cf5bab180
- https://wiediversistmeingarten.org/api/station zeigt alle Stationen.
- eine Übersicht: https://wiediversistmeingarten.org/api/station/87bab185-7630-461c-85e6-c04cf5bab180 , siehe auch Wilfried's `count.py`.



**Pagination**

Die Birdiary API hat bereits einige Parameter, um nicht immer den kompletten Datensatz laden zu müssen:

- GET /api/movement/<station_id>?movements=N – liefert die letzten N Bewegungen, z. B. ?movements=100
-  ?date=YYYY-MM-DD – filtert auf einen bestimmten Tag, z. B. ?date=2026-07-07
-  ?from=2026-06-01 seit einem bestimmten Tag
- ?species=Parus_major – filtert nach Art (Leerzeichen durch `_` ersetzen) und bezieht sich auf detections (KI). Keine Abfrage bisher für Validations.
- Kombinationen sind möglich: ?date=2026-07-07&species=Parus_major
- GET /api/station/<station_id>?movements=N – Limit für die zurückgegebenen Bewegungen 
- ?movementsOffset=N – Offset für Pagination; die Antwort enthält dann zusätzlich movementsMeta mit total, returned und hasMore. Dies funktioniert Juli 26 aber nur in `api/station/<stationId>` und nicht in `api/movement/<stationId>`.
- die Station `999` kann für Tests mit Hochladen oder Löschen verwendet werden.
- weitere Beispiele: `https://wiediversistmeingarten.org/api/station/87bab185-7630-461c-85e6-c04cf5bab180?movementsOffset=500&movements=3`, `https://wiediversistmeingarten.org/api/movement/87bab185-7630-461c-85e6-c04cf5bab180?from=2026-06-01&species=Aphelocoma_californica`