'''
find interesting videos of manually validated rarer birds on "https://wiediversistmeingarten.org/api/movement/"
manually using german bird labels from "webserver-main2026-04-18/nginx/data_visualization/src/helpers/labels.js", see germanLabels.js
'''
import requests
from datetime import datetime
import time
# import json
from sharedBird import prev_month

# Global API endpoint and state variables
BASE_URL = "https://wiediversistmeingarten.org/api/movement/"
STATION_ID = ""
STATION_NAME = ""
API_URL = ""
month_back = 3

# Frequent bird labels filter
FREQUENT_BIRDS = {"Haussperling", "Feldsperling", "Gimpel", "Blaumeise", "Kohlmeise", "Rotkehlchen", "Buchfink", "Gruenfink", "Kleiber"}

# Persistent session pool configuration
session = requests.Session()
session.headers.update({"Connection": "close"}) 

def setStation(station_name, station_id):
    """
    Sets the station name and ID received from the server.
    """
    global STATION_NAME, STATION_ID, API_URL
    STATION_NAME = station_name if station_name else "Unknown Station"
    STATION_ID = station_id if station_id else "No ID"
    API_URL = f"{BASE_URL}{STATION_ID}"

def get_dated_movements_paginated(target_url, earliest_date):
    """
    Fetches movements using the native ?from=YYYY-MM-DD pagination parameter.
    """
    start_time = time.time()
    print(f"\n[API PAGINATION] Entering data retrieval. Earliest Date Target: {earliest_date}")
    
    filtered_movements = []
    # Format our starting parameter for the API call
    from_date_str = earliest_date.strftime("%Y-%m-%d")
    
    # Target URL constructed with parameter flag
    paginated_url = f"{target_url}?from={from_date_str}"
    print(f"[API PAGINATION] Fetching targeted timeline window via: {paginated_url}")
    
    try:
        # Request the entire filtered subset natively parsed by the server side
        response = session.get(paginated_url, timeout=30)
        network_duration = time.time() - start_time
        print(f"[API PAGINATION] Response received in {network_duration:.2f} seconds. Status: {response.status_code}")
        
        response.raise_for_status()
        movements = response.json()
        
        if not isinstance(movements, list):
            print("[API PAGINATION.ERROR] Expected JSON payload array list structure. Received incompatible type.")
            return []
            
        print(f"[API PAGINATION] Server returned {len(movements)} records within timeline filter constraint boundaries.")
        
        # Double check date bounds inside the payload just in case server parameters fluctuate
        for mov in movements:
            start_date_str = mov.get("start_date")
            if not start_date_str:
                continue
            
            movement_date = datetime.strptime(start_date_str.split(" ")[0], "%Y-%m-%d").date()
            if movement_date >= earliest_date:
                filtered_movements.append(mov)
                
        return filtered_movements

    except Exception as e:
        print(f"[API PAGINATION.ERROR] Target sequence retrieval execution failed: {e}")
        return []
    
def getReport():
    total_start = time.time()
    print("\n================== [STARTING getReport LOGGING] ==================")
    
    today = datetime.today()
    current_day = today.strftime("%Y-%m-%d")

    current_month = today.strftime("%Y-%m")
    for _ in range(month_back):
        current_month = prev_month(current_month)
    earliest_date = datetime.strptime(f"{current_month}-01", "%Y-%m-%d").date()
    
    # Build the base target path explicitly
    target_url = f"{BASE_URL}{STATION_ID}"
    
    # Execute the updated native paginated filter function
    movements = get_dated_movements_paginated(target_url, earliest_date)
    
    print(f"[TIMING 2] Returned from data fetching. Proceeding to HTML serialization...")
    loop_start = time.time()

    frequent_counts = {}  
    rare_birds_links = [] 

    # Process validation loops exactly as before
    for mov in movements:
        validation_data = mov.get("validation", {})
        validations = validation_data.get("validations", []) if validation_data else []
        
        for v in validations:
            german_name = v.get("germanName")
            if not german_name:
                continue

            if german_name in FREQUENT_BIRDS:
                frequent_counts[german_name] = frequent_counts.get(german_name, 0) + 1
            else:
                video_url = mov.get("video")
                start_date_str = mov.get("start_date", "")
                
                if video_url and start_date_str:
                    date_clean = start_date_str.split(".")[0].replace(" ", "_").replace(":", "")
                    link_text = f"{german_name}_{date_clean}"
                    html_link = f'<a href="{video_url}" target="_blank">{link_text}</a>'
                    rare_birds_links.append(html_link)

    print(f"[TIMING 3] Validation loops finished processing in {time.time() - loop_start:.4f} seconds.")

    report_data = {
        "station_name": STATION_NAME,
        "station_id": STATION_ID,
        "earliest_date": str(earliest_date),
        "current_day": current_day,
        "frequent_birds": frequent_counts, 
        "rare_birds": rare_birds_links     
    }
    
    print(f"================== [FINISHED Data Processing in {time.time() - total_start:.2f}s] ==================\n")
    return report_data