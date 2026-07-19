import json
import requests
import os
from datetime import datetime
import time
from sharedBird import prev_month

STATION_API_URL = "https://wiediversistmeingarten.org/api/station"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

OUTPUT_JS = os.path.join(BASE_DIR, "stations.js")
OUTPUT_JSON = os.path.join(BASE_DIR, "stations.json")

def export_stations():
    try:
        today = datetime.today()
        current_month = today.strftime("%Y-%m")
        target_month = prev_month(current_month)

        print(f"[EXPORT] Fetching main station roster...")
        
        with requests.Session() as session:
            response = session.get(STATION_API_URL, timeout=30)
            response.raise_for_status()
            stations = response.json()
        
        if not isinstance(stations, list):
            print("Expected a list of stations from the API.")
            return

        vk_backend_data = []  # For lean stations.json
        js_frontend_map = {}  # For stations.js dropdown

        for s in stations:
            name = s.get("name", "").strip()
            station_id = s.get("station_id", "").strip()
            
            if not name or not station_id:
                continue

            # 1. Map for Frontend Dropdown (stations.js)
            js_frontend_map[name] = station_id

            # 2. Extract movement info for filtering
            last_mov = s.get("lastMovement") or {}
            start_date = last_mov.get("start_date", "")
            
            # Validate timeframe exactly like the reporting scripts do
            if start_date and (start_date.startswith(target_month) or start_date.startswith(current_month)):
                # Minimize the dictionary to save ONLY the target keys
                lean_station = {
                    "name": name,
                    "station_id": station_id,
                    "lastMovement": {
                        "start_date": start_date
                    }
                }
                vk_backend_data.append(lean_station)

        # Save Target 1: Minimalist VideoKing Backend Cache JSON
        sorted_vk_backend = sorted(vk_backend_data, key=lambda x: x.get("name", "").lower())
        with open(OUTPUT_JSON, mode="w", encoding="utf-8") as json_file:
            json.dump(sorted_vk_backend, json_file, ensure_ascii=False, indent=2)

        # Save Target 2: Frontend JS Map Object
        sorted_js_map = {k: js_frontend_map[k] for k in sorted(js_frontend_map.keys(), key=lambda s: s.lower())}
        with open(OUTPUT_JS, mode="w", encoding="utf-8") as js_file:
            js_file.write(f"const stationData = {json.dumps(sorted_js_map, ensure_ascii=False)};\n")
            
        print(f"\n[EXPORT COMPLETE]")
        print(f" -> Saved {len(sorted_vk_backend)} slim records to 'stations.json'.")
        print(f" -> Saved {len(sorted_js_map)} stations to 'stations.js'.")

    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    start_time = time.time()
    export_stations()
    print(f"\nScript completed in {time.time() - start_time:.2f} seconds.")