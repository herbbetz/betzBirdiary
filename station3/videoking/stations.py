import csv
import requests

STATION_API_URL = "https://wiediversistmeingarten.org/api/station"
OUTPUT_FILE = "stations.csv"

def export_stations_to_csv():
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
            if name or station_id:
                extracted_data.append({"name": name, "station_id": station_id})

        # Sort the list ascendingly by the "name" key
        # .lower() ensures a proper alphabetical sort (case-insensitive)
        sorted_stations = sorted(extracted_data, key=lambda x: x["name"].lower())

        # Write to the CSV file
        with open(OUTPUT_FILE, mode="w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=["name", "station_id"])
            
            # Write the header row
            writer.writeheader()
            # Write data rows
            writer.writerows(sorted_stations)

        print(f"Successfully saved {len(sorted_stations)} stations to '{OUTPUT_FILE}'.")

    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    export_stations_to_csv()