'''
Copy the data from your https://wiediversistmeingarten.org/api/movement/<stationID> (e.g. mine is https://wiediversistmeingarten.org/api/movement/87bab185-7630-461c-85e6-c04cf5bab180 )
then look for the hour, where most videos were taken, and correlate this hour with environment values from https://wiediversistmeingarten.org/api/environment/<stationID>
example output:
    Hour: 2024081315, Count: 33, Avg Temp: 35.5, Avg Humidity: 44.8
meaning:
    on 13thAug 2024 between 15:00 and 15:59 there were 33 bird videos taken. During this hour was an average temperature of 35.5°C and humidity of 44.8 rel% .
apidata.json:
    {"data": {"2024082410": {"count": 43, "temp": 23.4, "humid": 59.6}, "2024080614": {"count": 41, "temp": 29.5, "humid": 51.4}}, "created": "2025-05-31-14-28"}
script from 30-5-2025 with the aid of github-copilot.
'''
from datetime import datetime
from collections import Counter, defaultdict
import requests
import json
import sys
import os
# sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))) # add parent directory to sys.path to import configBird2
# from configBird2 import boxId, serverUrl

def parse_datetime(dt_str):
    # Split on the decimal, keep only the first part (before microseconds) in records where .%f is not present
    main_part = dt_str.split('.')[0]
    return datetime.strptime(main_part, "%Y-%m-%d %H:%M:%S")

def main():
    serverUrl = "https://wiediversistmeingarten.org/api/"
    # boxId = "6ad61509-788c-4350-8ea1-81d0a1e5bd0a"

    if len(sys.argv) < 2:
        print("Usage: python ", sys.argv[0], " <stationID>")
        sys.exit(1)

    boxId = sys.argv[1]


    ### Download required data from birdiary api:
    tag = ["movement", "environment"]
    for t in tag:
        url = serverUrl + t + "/" + boxId
        try:
            response = requests.get(url) # request from birdiary web api
            response.raise_for_status()  # Raises HTTPError for bad responses (4xx/5xx)
            data = response.json()       # May raise ValueError if response is not valid JSON
        except requests.exceptions.HTTPError as http_err:
            print(http_err)
            sys.exit(1)
        except requests.exceptions.RequestException as req_err:
            print(req_err)
            sys.exit(1)
        except ValueError as json_err:
            print(json_err)
            sys.exit(1)

        if t == "movement":
            movement_data = [item["start_date"] for item in data if "start_date" in item]
        elif t == "environment":
            environment_data = [
                {
                    "date": item.get("date"),
                    "temperature": item.get("temperature"),
                    "humidity": item.get("humidity")
                }
                for item in data
                if "date" in item and "temperature" in item and "humidity" in item
            ]
    
    ### movement data: make a dictionary 'move_hour_counts' with hour_strings as keys and their counts as values
    hour_strings = [
        parse_datetime(dt).strftime("%Y%m%d%H")
        for dt in movement_data
    ]
    move_hour_counts = dict(Counter(hour_strings)) # example: {'2025053018': 3, '2025053019': 1}; hour_counts["2025053018"] = 3
    # print(move_hour_counts)

    ### envir data: make a dictionary 'envir_hour_vals' with hour_strings as keys and their average temp and humidity as values
    # Step 1: Aggregate values by hour string
    hourly = defaultdict(lambda: {"temperature": [], "humidity": []})

    for item in environment_data:
        hour = parse_datetime(item["date"]).strftime("%Y%m%d%H")
        hourly[hour]["temperature"].append(float(item["temperature"])) # convert to floats, if some values are strings like in values["temperature"] = [21.5, "22.0", 23.1] (-> type error)
        hourly[hour]["humidity"].append(float(item["humidity"]))

    # Step 2: Calculate averages
    envir_hour_vals = {}
    for hour, values in hourly.items():
        avg_temp = round(sum(values["temperature"]) / len(values["temperature"]), 1)
        avg_hum = round(sum(values["humidity"]) / len(values["humidity"]), 1)
        envir_hour_vals[hour] = {"avg_temp": avg_temp, "avg_hum": avg_hum}
    # print(envir_hour_vals)

    ### unite move_hour_counts and their corresponding envir_hour_vals into the dataset all_values. Both datasets are connected by the same hour_strings keys.
    # top5 = sorted(move_hour_counts.items(), key=lambda x: x[1], reverse=True)[:5] # sorts move_hour_counts by count and takes the top 5 entries
    # here sort for hour_strings keys to better apply time slices:
    sorted_move_hour = sorted(move_hour_counts.items())

    all_values = {}
    for hour, count in sorted_move_hour:
        if hour in envir_hour_vals:
            all_values[hour] = {
                "count": count,
                "temp": envir_hour_vals[hour]["avg_temp"],
                "humid": envir_hour_vals[hour]["avg_hum"]
            }
    # print(all_values)

    ### save as "data" and "created" in a json file "apidata.json"
    output = {
        "data": all_values,
        "created": datetime.now().strftime("%Y-%m-%d-%H-%M")
    }
    with open("apidata.json", "w") as f:
        json.dump(output, f)    

if __name__ == "__main__":
    main()