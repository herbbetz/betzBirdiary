<!--keywords[API,Statistik_API]-->

Die Birdiary Website zeigt Statistiken [aller Stationen](https://www.wiediversistmeingarten.org/view/statistics) und von jeder [einzelnen](https://www.wiediversistmeingarten.org/view/statistics/87bab185-7630-461c-85e6-c04cf5bab180) (https://www.wiediversistmeingarten.org/view/statistics bzw. /stationId).  Die Statistiken kommen von folgender API, aus der man auch eigene Grafiken erstellen kann.

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

	{"2024082410": {"count": 43, "temp": 23.4, "humid": 59.6}, 
	
	"2024080614": {"count": 41, "temp": 29.5, "humid": 51.4}

}, 

"created": "2025-05-31-14-28"}

Der "Hour" String in "data" (wie "2024082410") hat das Format "%Jahr%Monat%Tag%Stunde" und ist der Key für die Values "count" (=Videoanzahl in der Stunde), "temp" (durchschnittliche °C Temperatur in dieser Stunde) und "humid" (durchschnittliche rel. Feuchte). Um die Auswertung auf Zeitabschnitte (python slices) zu begrenzen, wird "data" nach dem Key sortiert.

In dateslice.py kann man die Auswertung aus apidata.json auf einen Datumsbereich einschränken.

Der ganze Ordner /statist kann auch auf einem PC arbeiten, wo Python/Python3 mit Modulen wie 'matplotlib' installiert ist. Die .sh Skripte funktionieren nur unter Linux Terminal (auch WSL), das .bat auf der Windows Kommandozeile. Die Utilities 'dloadRaw.py' oder 'dloadAstats.py' sind für Datendownload von fremden Birdiary Stationen gedacht. Sie werden aufgerufen wie 'python dloadRaw.py <stationId>'. dloadRaw.py erzeugt mehrere .json zur Betrachtung im Texteditor. dloadAstats.py baut eine apidata.json, aus der mit buildSVGs.sh oder .bat wieder Grafiken erzeugt werden, um sie dann in showstats.html zu betrachten.

Die Skripte sind mithilfe von github.com/copilot erstellt.

![divider](../../divider.png)

The Birdiary website displays statistics for all bird [stations](https://www.wiediversistmeingarten.org/view/statistics) and for each one [individually](https://www.wiediversistmeingarten.org/view/statistics/87bab185-7630-461c-85e6-c04cf5bab180) (https://www.wiediversistmeingarten.org/view/statistics resp. /stationId). The statistics are derived from the following API, which you can  use to make your own plots too.

The Birdiary website offers an API for each stationID (like "87bab185-7630-461c-85e6-c04cf5bab180"),

that lists videos and environmental data uploaded :

- Videos: https://wiediversistmeingarten.org/api/movement/87bab185-7630-461c-85e6-c04cf5bab180
- Environmental data: https://wiediversistmeingarten.org/api/environment/87bab185-7630-461c-85e6-c04cf5bab180

Required is installing the python3 module 'matplotlib', which builds SVGs: sudo apt-get install python3-matplotlib

The API data can then be statistically processed:

- getStats.sh coordinates the Python scripts and is initiated by crontab.
- dloadStats.py loads the API data from Birdiary and saves it to apidata.json.
- If this works, the Python scripts hours_histo.py, month_histo.py, and countsbytemp.py each generate an SVG graphic from apidata.json.
- showstats.html presents these SVG graphics.

apidata.json has the following structure:

{"data":

 {"2024082410": {"count": 43, "temp": 23.4, "humid": 59.6},

 "2024080614": {"count": 41, "temp": 29.5, "humid": 51.4}

},

"created": "2025-05-31-14-28"}

The "hour" string in "data" (like "2024082410") has the format "%Year%Month%Day%Hour" and is the key for the values "count" (=number of videos per hour), "temp" (average °C temperature during this hour), and "humid" (average relative humidity). 

To limit the analysis to time periods (Python slices), "data" is sorted by key. In dateslice.py you can limit evaluation of apidata.json to a date range.

The entire folder "/statist"  can also work on a PC where python or python3 is installed with modules like 'matplotlib'. The .sh scripts only work under Linux terminals (including WSL), while the .bat script works on the Windows command line. The utilities 'dloadRaw.py' and 'dloadAstats.py' are intended for downloading data from other birdiary stations with a known stationId. They are called like 'python dloadRaw.py <stationId>'. dloadRaw.py creates several .json files for viewing in a text editor, while dloadAstats.py creates an apidata.json file, from which graphics can be generated using buildSVGs.sh or .bat, which can then be viewed in showstats.html.

The scripts were created using github.com/copilot.