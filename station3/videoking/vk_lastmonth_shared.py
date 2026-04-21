# script to show last month's "video king" from exploring api statistics, version integrated into station3 (called on boot by startup2stage.sh, used by flaskBird3, using sharedBird)
# created Apr 2026 with the aid of gemini
# results in "vk2026-03.html" for the videoking of 2026-03 = March of 2026
# may only be run once a month, so when requested, flask looks if previous month's stats.html has already been calculated.
# script takes several minutes, could be shortened by parallel processing requests using "concurrent.futures".
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from datetime import datetime
import time
import os
from pathlib import Path # to delete old reports
from sharedBird import prev_month

# Configuration
STATION_API = "https://wiediversistmeingarten.org/api/station"
MOVEMENT_API_BASE = "https://wiediversistmeingarten.org/api/movement/"

today = datetime.today()
CURRENT_MONTH = today.strftime("%Y-%m")
TARGET_MONTH = prev_month(CURRENT_MONTH)
OUTPUT_FILE = f"vk{TARGET_MONTH}.html"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_PATH = f"{BASE_DIR}/{OUTPUT_FILE}"

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
            response = session.get(STATION_API, timeout=30)
            response.raise_for_status()
            stations = response.json()
            
            results = []

            # 2. Filter stations
            for station in stations:
                last_mov = station.get("lastMovement", {})
                start_date = last_mov.get("start_date", "")
                
                if start_date.startswith(TARGET_MONTH) or start_date.startswith(CURRENT_MONTH):
                    station_id = station.get("station_id")
                    
                    # 3. Fetch movement data with retry logic
                    try:
                        mov_response = session.get(f"{MOVEMENT_API_BASE}{station_id}", timeout=30)
                        if mov_response.status_code == 200:
                            movements = mov_response.json()

                            # 4. Calculate stats
                            cnt_move = 0
                            cnt_validated = 0
                            
                            for m in movements:
                                start_date_m = m.get("start_date", "")
                                current_month = start_date_m[:7]
                                
                                if current_month > TARGET_MONTH:
                                    continue
                                elif current_month == TARGET_MONTH:
                                    cnt_move += 1
                                    if "validation" in m:
                                        cnt_validated += 1
                                else:
                                    break

                            if cnt_move > 0:
                                results.append({
                                    "station_id": station_id,
                                    "lat": station.get("location", {}).get("lat"),
                                    "lng": station.get("location", {}).get("lng"),
                                    "name": station.get("name"),
                                    "cnt_move": cnt_move,
                                    "cnt_validated": cnt_validated
                                })
                    except Exception as e:
                        print(f"Skipping station {station.get('name', 'Unknown')}: {e}")

            results.sort(key=lambda x: x["cnt_move"], reverse=True)
            return results

        except Exception as e:
            print(f"Critical error fetching station list: {e}")
            return []

def generate_html(data):
    # ... (Keep your existing generate_html function exactly as it was) ...
    html_content = f"""<h2>Videoking of last month {TARGET_MONTH}</h2>
<table>
    <tr><th>Rank</th><th>Station</th><th>Videos</th><th>Validated</th></tr>
"""
    rank = 0
    for entry in data:
        rank += 1
        map_link = f"https://www.google.com/maps/place/{entry['lat']},{entry['lng']}/@{entry['lat']},{entry['lng']},7.5z"
        html_content += f"""    <tr>
        <td>{rank}</td><td><a href="{map_link}" target="_blank">{entry['name']}</a></td>
        <td>{entry['cnt_move']}</td>
        <td>{entry['cnt_validated']}</td>
    </tr>
"""
    html_content += "</table>"
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(html_content)
    print(f"Successfully generated {OUTPUT_FILE}")

if __name__ == "__main__":
    if os.path.exists(OUTPUT_PATH):
        print(f"{OUTPUT_FILE} already there")
        exit(0)

    # 1. Clean up old reports first
    for f in Path(BASE_DIR).glob("vk*.html"):
        f.unlink()

    start_time = time.time()
    aggregated_data = get_data()
    if aggregated_data:
        generate_html(aggregated_data)
    print(f"This script took {time.time() - start_time:.2f} seconds to complete.")
