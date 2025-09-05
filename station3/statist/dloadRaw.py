# Download any stationID's stats independant of formatting
from datetime import datetime
import json
import requests
import sys
# from configBird2 import boxId, serverUrl

def write_json(data, fname):
    with open(fname, "w", encoding="utf-8") as f:
        json.dump(data, f)

def main():
    if len(sys.argv) < 2:
        print("Usage: python ", sys.argv[0], " <stationID>")
        sys.exit(1)

    boxId = sys.argv[1]
    serverUrl = "https://wiediversistmeingarten.org/api/"

    tag = ["movement", "environment"]

    now = datetime.now()
    datestr = now.strftime("%Y%m%d%H%M")

    for t in tag:
        url = serverUrl + t + "/" + boxId
        fname = t + datestr + ".json"

        try:
            response = requests.get(url) # request from birdiary web api
            response.raise_for_status()  # Raises HTTPError for bad responses (4xx/5xx)
            data = response.json()       # May raise ValueError if response is not valid JSON
        except requests.exceptions.HTTPError as http_err:
            data = {"error": http_err}
            write_json(data, fname)
            sys.exit(1)
        except requests.exceptions.RequestException as req_err:
            data = {"error": req_err}
            write_json(data, fname)
            sys.exit(1)
        except ValueError as json_err:
            data = {"error": json_err}
            write_json(data, fname)
            sys.exit(1)

        if t == "movement":
            start_dates = [item["start_date"] for item in data if "start_date" in item]
            print("#Movements: ", len(start_dates), " from ", start_dates[0], " to ", start_dates[-1])
            write_json(start_dates, fname)
        elif t == "environment":
            env_data = [
                {
                    "date": item.get("date"),
                    "temperature": item.get("temperature"),
                    "humidity": item.get("humidity")
                }
                for item in data
                if "date" in item and "temperature" in item and "humidity" in item
            ]
            print("#Envirs: ", len(env_data), " from ", env_data[0]["date"], " to ", env_data[-1]["date"])
            write_json(env_data, fname)

if __name__ == "__main__":
    main()