# import csv
import json
import requests

STATION_API_URL = "https://wiediversistmeingarten.org/api/station"
# OUTPUT_CSV = "stations.csv"
OUTPUT_JS = "stations.js"  # Added JS output constant

def export_stations():
    try:
        # Fetch data from the API
        response = requests.get(STATION_API_URL, timeout=30)
        response.raise_for_status()
        stations = response.json()
        
        if not isinstance(stations, list):
            print("Expected a list of stations from the API.")
            return

        # Extract only the required fields safely
        extracted_data = []
        for s in stations:
            name = s.get("name", "").strip()
            station_id = s.get("station_id", "").strip()
            
            # Only add to list if we have data to write
            if name and station_id:
                extracted_data.append({"name": name, "station_id": station_id})

        # Sort the list ascendingly by the "name" key
        sorted_stations = sorted(extracted_data, key=lambda x: x["name"].lower())

        '''
        # --- 1. Write to the CSV file ---
        with open(OUTPUT_CSV, mode="w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=["name", "station_id"])
            writer.writeheader()
            writer.writerows(sorted_stations)

        print(f"Successfully saved {len(sorted_stations)} stations to '{OUTPUT_CSV}'.")
        '''
        # --- 2. Write to the JavaScript file ---
        # Fixed the key here to use "station_id" to match extracted_data
        js_array = [{station["name"]: station["station_id"]} for station in sorted_stations]

        with open(OUTPUT_JS, mode="w", encoding="utf-8") as js_file:
            # Prepend a variable declaration so it's a valid, instantly readable global JS variable
            js_file.write(f"const stationData = {json.dumps(js_array, ensure_ascii=False)};\n")
            
        print(f"Successfully saved {len(sorted_stations)} stations to '{OUTPUT_JS}'.")

    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    export_stations()