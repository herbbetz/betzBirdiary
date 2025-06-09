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