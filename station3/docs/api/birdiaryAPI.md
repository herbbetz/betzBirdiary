<!--keywords[API,Statistik_API]-->

siehe die [API Doc](https://wiediversistmeingarten.org/doc/) auf https://wiediversistmeingarten.org/doc/

Das REST-API akzeptiert CRUD (create-read-update-delete) Kommandos von *request* Modul. Wird ein Access-Key (apikey) benötigt, ist er als "Stationsschlüssel" nach dem Einloggen zu sehen. Im Skript wird er dann folgendermaßen eingesetzt (kein `Authorization Header` nötig):

```
ACCESS_TOKEN = "XXXXXXXX"
url = f"{API_URL}/{mov_id}?apikey={ACCESS_TOKEN}"
response = session.delete(url, timeout=10)
```



Die Birdiary Website zeigt Statistiken [aller Stationen](https://www.wiediversistmeingarten.org/view/statistics) und von jeder [einzelnen](https://www.wiediversistmeingarten.org/view/statistics/87bab185-7630-461c-85e6-c04cf5bab180) (https://www.wiediversistmeingarten.org/view/statistics bzw. /stationId).  Die Statistiken kommen von folgender API, aus der man auch eigene Grafiken erstellen kann.

Die Birdiary Website bietet ein API, das pro Station hochgeladene Videos und Umweltdaten listet:

- Videos /movements: https://wiediversistmeingarten.org/api/movement/87bab185-7630-461c-85e6-c04cf5bab180
- Umweltdaten: https://wiediversistmeingarten.org/api/environment/87bab185-7630-461c-85e6-c04cf5bab180
- https://wiediversistmeingarten.org/api/station zeigt alle Stationen.
- eine Übersicht: https://wiediversistmeingarten.org/api/station/87bab185-7630-461c-85e6-c04cf5bab180 , siehe auch Wilfried's `count.py`.



**Pagination**

Die Birdiary API hat bereits einige Parameter, um nicht immer den kompletten Datensatz laden zu müssen:

- GET /api/movement/<station_id>?movements=N – liefert die letzten N Bewegungen, z. B. ?movements=100

- ?date=YYYY-MM-DD – filtert auf einen bestimmten Tag, z. B. ?date=2026-07-07

- ?from=2026-06-01 seit einem bestimmten Tag, ?to=2026-05-30 bis zu diesem Tag einschließlich.

- ?species=Parus_major – filtert nach Art (Leerzeichen durch `_` ersetzen) und bezieht sich auf detections (KI). Keine Abfrage bisher für Validations.

- Kombinationen sind möglich: ?date=2026-07-07&species=Parus_major

- GET /api/station/<station_id>?movements=N – Limit für die zurückgegebenen Bewegungen 

- ?movementsOffset=N – Offset für Pagination; die Antwort enthält dann zusätzlich movementsMeta mit total, returned und hasMore. Dies funktioniert Juli 26 aber nur in `api/station/<stationId>` und nicht in `api/movement/<stationId>`.

- die Station `999` kann für Tests mit Hochladen oder Löschen verwendet werden. Man kann sich nicht an ihr anmelden. Ihr API-Key: `a0d28a6d7004e466f2819384d1d3b398`. `https://wiediversistmeingarten.org/api/station/999` oder `.../api/movement/999`(leer) werden nach 1 Stunde zurückgesetzt. Für denselben Zweck kann auch die Betzbirdiary Station vom Typ *Test*  (nicht vom Typ *Observer*) verwendet werden.

- Für Schreibberechtigung auf das API, siehe obigen geheimen *Access Key*.

- weitere Beispiele: `https://wiediversistmeingarten.org/api/station/87bab185-7630-461c-85e6-c04cf5bab180?movementsOffset=500&movements=3`, `https://wiediversistmeingarten.org/api/movement/87bab185-7630-461c-85e6-c04cf5bab180?from=2026-06-01&species=Aphelocoma_californica`,  `https://wiediversistmeingarten.org/api/movement/87bab185-7630-461c-85e6-c04cf5bab180?from=2026-05-29&to=2026-05-30`,`https://wiediversistmeingarten.org/api/station/999`





**movements API Beispiel**

```
[
  {
    "station_id": "87bab185-7630-461c-85e6-c04cf5bab180",
    "mov_id": "2177f719-d11a-4238-8fe9-e87db8876652",
    "start_date": "2026-04-20 09:06:58.863742",
    "end_date": "2026-04-20 09:07:07.193855",
    "weight": 21,
    "detections": [
      {
        "latinName": "Nycticorax nycticorax",
        "germanName": "Nachtreiher",
        "score": 0.509803921568627
      },
      {
        "latinName": "Hemiphaga novaeseelandiae",
        "germanName": "",
        "score": 0.505882352941176
      }
    ],
    "audio": "https://wiediversistmeingarten.org/api/uploads/audios/audio_2026-04-2007:07:08.534156.wav",
    "video": "https://wiediversistmeingarten.org/api/uploads/videos/2026-04-20_090658.863742.mp4",
    "environment": {
      "env_id": "55511eb1-2125-4dcf-b670-8860264ca996"
    },
    "createdAt": "Mon, 20 Apr 2026 07:07:08 GMT",
    "validation": {
      "validations": [
        {
          "latinName": "Sitta europaea",
          "germanName": "Kleiber",
          "timestamp": "2026-04-20 17:54:44.743939"
        }
      ],
      "summary": {
        "Sitta europaea": {
          "latinName": "Sitta europaea",
          "amount": 1
        }
      }
    }
  },
  {
    "station_id": "87bab185-7630-461c-85e6-c04cf5bab180",
    "mov_id": "70d53139-33bf-4d8c-8686-b50e799c61fd",
    "start_date": "2026-04-20 09:05:23.867016",
    "end_date": "2026-04-20 09:05:29.343197",
    "weight": 21,
    "detections": [
      {
        "latinName": "Zenaida macroura",
        "germanName": "Carolinataube",
        "score": 0.403921568627451
      },
      {
        "latinName": "Nycticorax nycticorax",
        "germanName": "Nachtreiher",
        "score": 0.392156862745098
      },
      {
        "latinName": "Hemiphaga novaeseelandiae",
        "germanName": "",
        "score": 0.325490196078431
      }
    ],
    "audio": "https://wiediversistmeingarten.org/api/uploads/audios/audio_2026-04-2007:05:30.599809.wav",
    "video": "https://wiediversistmeingarten.org/api/uploads/videos/2026-04-20_090523.867016.mp4",
    "environment": {
      "env_id": "cfb5f89f-7037-4eb9-932f-b6a9bf4c2f96"
    },
    "createdAt": "Mon, 20 Apr 2026 07:05:30 GMT"
  },
...]

```