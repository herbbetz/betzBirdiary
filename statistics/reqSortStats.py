from datetime import datetime
from collections import Counter, defaultdict
import requests
import sys
# from configBird2 import boxId, serverUrl

'''
def read_json_file(filename):
    with open(filename, "r", encoding="utf-8") as f:
        return json.load(f)
'''

def main():
    serverUrl = "https://wiediversistmeingarten.org/api/"
    boxId = "87bab185-7630-461c-85e6-c04cf5bab180"

    ### Download required data from birdiary api:
    # movement_data = read_json_file("movement.json")
    # environment_data = read_json_file("environment.json")
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
        datetime.strptime(dt, "%Y-%m-%d %H:%M:%S.%f").strftime("%Y%m%d%H")
        for dt in movement_data
    ]
    move_hour_counts = dict(Counter(hour_strings)) # example: {'2025053018': 3, '2025053019': 1}; hour_counts["2025053018"] = 3
    # print(move_hour_counts)

    ### envir data: make a dictionary 'envir_hour_vals' with hour_strings as keys and their average temp and humidity as values
    # Step 1: Aggregate values by hour string
    hourly = defaultdict(lambda: {"temperature": [], "humidity": []})

    for item in environment_data:
        hour = datetime.strptime(item["date"], "%Y-%m-%d %H:%M:%S.%f").strftime("%Y%m%d%H")
        hourly[hour]["temperature"].append(item["temperature"])
        hourly[hour]["humidity"].append(item["humidity"])

    # Step 2: Calculate averages
    envir_hour_vals = {}
    for hour, values in hourly.items():
        avg_temp = round(sum(values["temperature"]) / len(values["temperature"]), 1)
        avg_hum = round(sum(values["humidity"]) / len(values["humidity"]), 1)
        envir_hour_vals[hour] = {"avg_temp": avg_temp, "avg_hum": avg_hum}
    # print(envir_hour_vals)

    ### show the top 5 move_hour_counts and their corresponding envir_hour_vals. Both datasets are connected by the same hour_strings keys.
    top5 = sorted(move_hour_counts.items(), key=lambda x: x[1], reverse=True)[:5]

    for hour, count in top5:
        if hour in envir_hour_vals:
            avg_temp = envir_hour_vals[hour]['avg_temp']
            avg_hum = envir_hour_vals[hour]['avg_hum']
            print(f"Hour: {hour}, Count: {count}, Avg Temp: {avg_temp}, Avg Humidity: {avg_hum}")
        else:
            print(f"Hour: {hour}, Count: {count}, No environment data")

if __name__ == "__main__":
    main()