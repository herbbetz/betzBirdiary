# script to show last month's "video king" from exploring api statistics, version integrated into station3 (called on boot by startup2stage.sh, used by flaskBird3, using sharedBird)
# created Apr 2026 with the aid of gemini
# results in "vk2026-03.html" for the videoking of 2026-03 = March of 2026
# may only be run once a month, so when requested, flask looks if previous month's stats.html has already been calculated.
# script may take several minutes.
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from datetime import datetime
import time
import os
import json
from pathlib import Path # to delete old reports
from sharedBird import prev_month

# Configuration
STATION_API = "https://wiediversistmeingarten.org/api/station"
MOVEMENT_API_BASE = "https://wiediversistmeingarten.org/api/movement/"
DEBUG = False  # Set to True to enable verbose step-by-step console outputs

today = datetime.today()
CURRENT_MONTH = today.strftime("%Y-%m")
TARGET_MONTH = prev_month(CURRENT_MONTH)
OUTPUT_FILE = f"vk{TARGET_MONTH}.html"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_PATH = f"{BASE_DIR}/{OUTPUT_FILE}"

def log_debug(msg):
    """Helper function to cleanly handle optional output logs."""
    if DEBUG:
        print(msg)

def load_optimized_stations():
    stations_json_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "stations.json")
    
    # Fallback to web API if local cache doesn't exist yet
    if os.path.exists(stations_json_path):
        log_debug("[DEBUG] Loading pre-filtered stations from local JSON cache...")
        with open(stations_json_path, "r", encoding="utf-8") as f:
            return json.load(f)
    else:
        print("[WARNING] Local cache missing. Falling back to live API download...")
        response = requests.get(STATION_API, timeout=20)
        return response.json()

def get_data():
    # Configure retry strategy: 3 retries, wait 1 second between attempts
    retry_strategy = Retry(
        total=3,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    
    with requests.Session() as session:
        session.mount("https://", adapter)
        session.mount("http://", adapter)
        
        try:
            # 1. Get all stations
            stations = load_optimized_stations()
            
            total_stations = len(stations)
            log_debug(f"[DEBUG] Discovered {total_stations} total stations. Beginning parsing pass...")

            # 2. Filter stations
            results = []
            for idx, station in enumerate(stations, start=1):
                station_name = station.get("name", "Unknown")
                station_id = station.get("station_id")
                last_mov = station.get("lastMovement", {})
                start_date = last_mov.get("start_date", "")
                
                log_debug(f"\n[DEBUG] Processing Station {idx}/{total_stations}: '{station_name}' ({station_id})")
                
                # Performance optimization: If the station hasn't seen activity since before our target month,
                # skip it completely without making a heavy network request.
                if start_date and start_date[:7] < TARGET_MONTH:
                    log_debug(f" -> [SKIP] Last activity date ({start_date}) is older than target month ({TARGET_MONTH}).")
                    continue
                
                if start_date.startswith(TARGET_MONTH) or start_date.startswith(CURRENT_MONTH):
                    
                    # 3. Fetch movement data using server-side pagination parameter filter
                    try:
                        paginated_url = f"{MOVEMENT_API_BASE}{station_id}?from={TARGET_MONTH}-01"
                        log_debug(f" -> [FETCH] Requesting timeline segments via: {paginated_url}")
                        
                        station_fetch_start = time.time()
                        mov_response = session.get(paginated_url, timeout=30)
                        fetch_duration = time.time() - station_fetch_start
                        
                        log_debug(f" -> [RESPONSE] Status {mov_response.status_code} received in {fetch_duration:.2f}s")
                        
                        if mov_response.status_code == 200:
                            movements = mov_response.json()
                            
                            if not isinstance(movements, list):
                                print(f" -> [WARN] Expected array list structure payload for '{station_name}', skipping.")
                                continue
                                
                            cnt_move = 0
                            cnt_validated = 0
                            
                            log_debug(f" -> [PARSING] Scanning {len(movements)} records returned by server...")
                            for obj in movements:
                                start_date_m = obj.get("start_date", "")
                                current_month_check = start_date_m[:7]
                                
                                # Count entries that fall precisely inside the targeted calendar month window
                                if current_month_check == TARGET_MONTH:
                                    cnt_move += 1
                                    if "validation" in obj:
                                        cnt_validated += 1
                                        
                            log_debug(f" -> [DONE STATION] Matched target month videos: {cnt_move} (Validated: {cnt_validated})")
                            
                            if cnt_move > 0:
                                results.append({
                                    "station_id": station_id,
                                    "lat": station.get("location", {}).get("lat") if station.get("location") else None,
                                    "lng": station.get("location", {}).get("lng") if station.get("location") else None,
                                    "name": station_name,
                                    "cnt_move": cnt_move,
                                    "cnt_validated": cnt_validated
                                })
                        else:
                            print(f" -> [ERROR] Non-200 endpoint response received for '{station_name}' (Status: {mov_response.status_code})")
                    except Exception as e:
                        print(f" -> [EXCEPTION] Network layer error handling station '{station_name}': {e}")
                else:
                    log_debug(f" -> [SKIP] Active date signature '{start_date}' outside matching parameters.")

            log_debug(f"\n[DEBUG] Execution processing complete for all stations. Sorting results...")
            results.sort(key=lambda x: x["cnt_move"], reverse=True)
            return results

        except Exception as e:
            print(f"[CRITICAL ERROR] Failed to initialize root compilation routine: {e}")
            return []

def generate_html(data):
    html_content = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{TARGET_MONTH}</title>
<link rel="icon" href="/favicon.svg" type="image/svg+xml">
<link rel="stylesheet" href="/birdmd.css">
</head>
<body>
"""
    html_content += f"""<h2>Videoking of last month {TARGET_MONTH}</h2>
<table>
    <tr><th>Rank</th><th>Station</th><th>Videos</th><th>Validated</th></tr>
"""
    rank = 0
    for entry in data:
        rank += 1
        # Use fallback map logic if locations are missing from lean JSON cache data layouts
        lat, lng = entry.get('lat'), entry.get('lng')
        if lat and lng:
            map_link = f"https://www.google.com/maps/place/{lat},{lng}/@{lat},{lng},7.5z"
        else:
            map_link = "#"
            
        html_content += f"""    <tr>
        <td>{rank}</td><td><a href="{map_link}" target="_blank">{entry['name']}</a></td>
        <td>{entry['cnt_move']}</td>
        <td>{entry['cnt_validated']}</td>
    </tr>
"""
    html_content += "</table></body></html>"
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        f.write(html_content)
    print(f"[STATUS] Successfully wrote report structure to disk output -> {OUTPUT_FILE}")

if __name__ == "__main__":
    if os.path.exists(OUTPUT_PATH):
        print(f"[STATUS] Pre-calculated target path report detected: {OUTPUT_FILE} already exists.")
        exit(0)

    # 1. Clean up old reports first
    log_debug("[DEBUG] Sweeping old report logs out of local workspace directory...")
    for f in Path(BASE_DIR).glob("vk*.html"):
        f.unlink()

    start_time = time.time()
    aggregated_data = get_data()
    if aggregated_data:
        generate_html(aggregated_data)
    else:
        print(f"[STATUS] No video tracking events discovered inside target parameter window for {TARGET_MONTH}.")
        
    print(f"[TIMING SUMMARY] Script completed generation run sequence in {time.time() - start_time:.2f} total seconds.")