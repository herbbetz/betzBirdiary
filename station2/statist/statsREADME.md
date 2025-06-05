Die Birdiary Website bietet ein API, das pro Station hochgeladene Videos und Umweltdaten listet:

- Videos: https://wiediversistmeingarten.org/api/movement/87bab185-7630-461c-85e6-c04cf5bab180
- Umweltdaten: https://wiediversistmeingarten.org/api/environment/87bab185-7630-461c-85e6-c04cf5bab180

Voraussetzung ist ein installiertes Modul 'matplotlib' für Python3: sudo apt-get install python3-matplotlib. Dies erzeugt SVG Grafiken.

Dann werden die API Daten statistisch aufbereitet:

- getStats.sh koordiniert die Pythonskripte und wird von crontab initiiert.
- dloadStats.py lädt die APIdaten von Birdiary und speichert sie in apidata.json.
- Hat das geklappt, erzeugen die Pythonscripte hours_histo.py, month_histo.py und countsbytemp.py und countbyhumid.py aus apidata.json jeweils eine SVG Grafik mittels 'matplotlib'.
- showstats.html präsentiert diese SVG Grafiken.

apidata.json hat folgende Struktur:

{"data": 

​	{"2024082410": {"count": 43, "temp": 23.4, "humid": 59.6}, 

​	"2024080614": {"count": 41, "temp": 29.5, "humid": 51.4}

}, 

"created": "2025-05-31-14-28"}

Der "Hour" String in "data" (wie "2024082410") hat das Format "%Jahr%Monat%Tag%Stunde" und ist der Key für die Values "count" (=Videoanzahl in der Stunde), "temp" (durchschnittliche °C Temperatur in dieser Stunde) und "humid" (durchschnittliche rel. Feuchte). Um die Auswertung auf Zeitabschnitte (python slices) zu begrenzen, wird "data" nach dem Key sortiert.

In dateslice.py kann man die Auswertung aus apidata.json auf einen Datumsbereich einschränken.

Der ganze Ordner /statist kann auch auf einem PC arbeiten, wo Python/Python3 mit Modulen wie 'matplotlib' installiert ist. Die .sh Skripte funktionieren nur unter Linux Terminal (auch WSL), das .bat auf der Windows Kommandozeile. Die Utilities 'dloadRaw.py' oder 'dloadAstats.py' sind für Datendownload von fremden Birdiary Stationen gedacht. Sie werden aufgerufen wie 'python dloadRaw.py <stationId>'. dloadRaw.py erzeugt mehrere .json zur Betrachtung im Texteditor. dloadAstats.py baut eine apidata.json, aus der mit buildSVGs.sh oder .bat wieder Grafiken erzeugt werden, um sie dann in showstats.html zu betrachten.

Die Skripte sind mithilfe von github.com/copilot erstellt.