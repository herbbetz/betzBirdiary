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
(https://wiediversistmeingarten.org/api/movement/87bab185-7630-461c-85e6-c04cf5bab180)
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

**one station's API Beispiel**
(https://wiediversistmeingarten.org/api/station/87bab185-7630-461c-85e6-c04cf5bab180)
```

  "station_id": "87bab185-7630-461c-85e6-c04cf5bab180",
  "location": {
    "lat": 48.5334147181626,
    "lng": 12.1375054121017
  },
  "name": "Betzbirdiary",
  "count": {
    "2026-01-26": {
      "sum": 3,
      "birds": [
        {
          "latinName": "Sitta europaea",
          "germanName": "Kleiber",
          "amount": 1
        },
        {
          "latinName": "Cyanistes caeruleus",
          "germanName": "Blaumeise",
          "amount": 1
        },
        {
          "latinName": "Larus argentatus",
          "germanName": "Silbermoewe",
          "amount": 1
        }
      ]
    },
    "2026-01-27": {
      "sum": 23,
      ...
},
  "sensebox_id": "6979002ebd5b9f0007f24fd9",
  "type": "observer",
  "advancedSettings": {

  },
  "lastMovement": {
    "station_id": "87bab185-7630-461c-85e6-c04cf5bab180",
    "mov_id": "b1eb563e-1da3-4320-a07e-87bf2ae1fafa",
    "start_date": "2026-07-19 12:33:21.987454",
    "end_date": "2026-07-19 12:33:23.527768",
    "weight": 9.57995668705683,
    "detections": [
      {
        "latinName": "Larus occidentalis",
        "germanName": "",
        "score": 0.419607843137255
      },
      {
        "latinName": "Mimus polyglottos",
        "germanName": "",
        "score": 0.313725490196078
      }
    ],
    "audio": "https://wiediversistmeingarten.org/api/uploads/audios/audio_2026-07-1910:33:24.156127.wav",
    "video": "https://wiediversistmeingarten.org/api/uploads/videos/2026-07-19_123321.987454.mp4",
    "environment": {
      "env_id": "206d6cd2-23f2-4aca-8b99-2c5d1310e26a"
    },
    "createdAt": "Sun, 19 Jul 2026 10:33:24 GMT"
  },
  "lastEnvironment": {
    "date": "2026-07-19 12:47:43.629818",
    "temperature": 23,
    "humidity": 55,
    "env_id": "06df307d-eafc-41a1-affd-a8ebcc83a0e0"
  },
  "ownerId": "6976653e4d166ef0f6385ff9",
  "stationSoftware": "birdiary",
  "measurements": {
    "movements": [
      {
        "station_id": "87bab185-7630-461c-85e6-c04cf5bab180",
        "mov_id": "b1eb563e-1da3-4320-a07e-87bf2ae1fafa",
        "start_date": "2026-07-19 12:33:21.987454",
        "end_date": "2026-07-19 12:33:23.527768",
        "weight": 9.57995668705683,
        "detections": [
          {
            "latinName": "Larus occidentalis",
            "germanName": "",
            "score": 0.419607843137255
          },
          {
            "latinName": "Mimus polyglottos",
            "germanName": "",
            "score": 0.313725490196078
          }
        ],
        "audio": "https://wiediversistmeingarten.org/api/uploads/audios/audio_2026-07-1910:33:24.156127.wav",
        "video": "https://wiediversistmeingarten.org/api/uploads/videos/2026-07-19_123321.987454.mp4",
        "environment": {
          "env_id": "206d6cd2-23f2-4aca-8b99-2c5d1310e26a"
        },
        "createdAt": "Sun, 19 Jul 2026 10:33:24 GMT",
        "statisticsCoreApplied": true
      },
...
      {
        "station_id": "87bab185-7630-461c-85e6-c04cf5bab180",
        "mov_id": "f3fd2ccc-55f2-47d5-89dd-4c3ab212e429",
        "start_date": "2024-03-08 11:46:14.559011",
        "end_date": "2024-03-08 11:46:17.626207",
        "weight": 8.71,
        "detections": [
          {
            "latinName": "Cyanistes caeruleus",
            "germanName": "Blaumeise",
            "score": 0.811764705882353
          },
          {
            "latinName": "Cyanocitta cristata",
            "germanName": "",
            "score": 0.309803921568627
          }
        ],
        "audio": "https://wiediversistmeingarten.org/api/uploads/audios/audio_2024-03-0810:46:29.762495.wav",
        "video": "https://wiediversistmeingarten.org/api/uploads/videos/2024-03-08_114614.559011.mp4",
        "environment": {
          "date": "2024-03-08 11:45:14.260699",
          "temperature": 11.39,
          "humidity": 50.59,
          "env_id": "e3331214-4fe3-4cfd-9241-c0dc8376574a"
        },
        "createdAt": "Fri, 08 Mar 2024 10:46:29 GMT",
        "validation": {
          "validations": [
            {
              "latinName": "Cyanistes caeruleus",
              "germanName": "Blaumeise",
              "timestamp": "2024-09-05 09:49:48.338646"
            }
          ],
          "summary": {
            "Cyanistes caeruleus": {
              "latinName": "Cyanistes caeruleus",
              "amount": 1
            }
          }
        }
      }
    ]
  },
  "statisticsSummary": {
    "specialBirds": [
      {
        "latinName": "Passer domesticus",
        "germanName": "Haussperling",
        "movements": [
          {
            "mov_id": "1dfa7c93-422d-4856-93a3-3e9d9c2ea845",
            "station_id": "87bab185-7630-461c-85e6-c04cf5bab180",
            "video": "https://wiediversistmeingarten.org/api/uploads/videos/2024-06-12_154037.344315.mp4",
            "start_date": "2024-06-12 15:40:37.344315",
            "score": 0.815686274509804
          },
          {
            "mov_id": "79394c74-8cad-496e-bc46-19779b849a9d",
            "station_id": "87bab185-7630-461c-85e6-c04cf5bab180",
            "video": "https://wiediversistmeingarten.org/api/uploads/videos/2024-07-02_134958.566139.mp4",
            "start_date": "2024-07-02 13:49:58.566139",
            "score": 0.901960784313726
          },
          {
            "mov_id": "04daa842-761f-49c4-be73-174c7601d3b2",
            "station_id": "87bab185-7630
            ...
            
          {
            "mov_id": "a778fbf9-a420-424b-b2d8-ef9a26190c30",
            "station_id": "87bab185-7630-461c-85e6-c04cf5bab180",
            "video": "https://wiediversistmeingarten.org/api/uploads/videos/2026-03-31_102448.218807.mp4",
            "start_date": "2026-03-31 10:24:48.218807",
            "score": 0.823529411764706
          }
        ]
      }
    ],
    "updatedAt": "Sun, 19 Jul 2026 10:33:27 GMT"
  }
}
```

**stations API Beispiel** 
(https://wiediversistmeingarten.org/api/station)
```
[
  {
    "station_id": "916c48da-19f6-4af4-80f3-8bf0abef02c7",
    "location": {
      "lat": 52.2563375562688,
      "lng": 7.90534973144531
    },
    "name": "Landsitz Lotte",
    "sensebox_id": "",
    "lastEnvironment": {
      "date": "2026-06-12 08:10:49.044873",
      "temperature": 13.6,
      "humidity": 98.1,
      "env_id": "103200f6-e20f-4477-8466-af2fb1fe707e"
    },
    "lastMovement": {
      "station_id": "916c48da-19f6-4af4-80f3-8bf0abef02c7",
      "mov_id": "2a4ea034-30bf-484f-9f4f-e9d6d8ed6f85",
      "start_date": "2026-06-02 18:56:26.421582",
      "end_date": "2026-06-02 18:56:29.449919",
      "weight": 5.02969246897057,
      "detections": [
        {
          "latinName": "Bubulcus ibis",
          "germanName": "Kuhreiher",
          "score": 0.458823529411765
        }
      ],
      "audio": "https://wiediversistmeingarten.org/api/uploads/audios/audio_2026-06-0216:56:35.687410.wav",
      "video": "https://wiediversistmeingarten.org/api/uploads/videos/2026-06-02_185626.421582.mp4",
      "environment": {
        "date": "2026-06-02 18:56:18.683214",
        "temperature": 19.9,
        "humidity": 86.3,
        "env_id": "0edb76cf-14e8-4950-a79a-999481d4829f"
      },
      "createdAt": "2026-06-02T16:56:35.695000"
    },
    "type": "observer"
  },
  {
    "station_id": "7ae3c569-ca32-43d7-883f-6280c1eefa89",
    ...}]
```
