'''
find interesting videos of manually validated rarer birds on "https://wiediversistmeingarten.org/api/movement/"
using german bird labels from "webserver-main2026-04-18/nginx/data_visualization/src/helpers/labels.js"
'''
import requests
from datetime import datetime
import time
import json
from sharedBird import prev_month

# Global API endpoint and state variables
BASE_URL = "https://wiediversistmeingarten.org/api/movement/"
STATION_ID = ""
STATION_NAME = ""
API_URL = ""
API_URL = f"{BASE_URL}{STATION_ID}"
month_back = 3

# Sets are scanned faster than lists or tuples, and they don't allow duplicates, so a set is appropriate here.
FREQUENT_BIRDS = {"Haussperling", "Feldsperling", "Gimpel", "Blaumeise", "Kohlmeise", "Rotkehlchen", "Buchfink", "Gruenfink", "Kleiber"}

# Create a persistent session object at the top level of your rb script
session = requests.Session()
# Configure the session to close connections cleanly instead of leaving them in TIME_WAIT
session.headers.update({"Connection": "close"}) 

def setStation(station_name, station_id):
    """
    Sets the station name and ID received from the server.
    """
    global STATION_NAME, STATION_ID, API_URL
    # Fallback to empty string if None is passed
    STATION_NAME = station_name if station_name else "Unknown Station"
    STATION_ID = station_id if station_id else "No ID"
    API_URL = f"{BASE_URL}{STATION_ID}"

def get_movements():
    print(f"Sending API request to: {API_URL} ...") # Watch this in your Python terminal
    try:
        response = session.get(API_URL, timeout=30)
        response.raise_for_status()
        movements = response.json()
        if not isinstance(movements, list):
            print("API response format unexpected. Expected a list.")
            return []
        return movements
    except Exception as e:
        print(f"Error fetching data: {e}")
        return []

def get_dated_movements(target_url, earliest_date):
    start_time = time.time()
    print(f"\n[TIMING 1] Entering get_dated_movements. Target URL: {target_url}")
    
    try:
        print("[TIMING 1.1] Initiating stream GET request via session pool...")
        
        # Open the request as a live connection stream
        response = session.get(target_url, timeout=30, stream=True)
        
        network_duration = time.time() - start_time
        print(f"[TIMING 1.2] Connection stream opened in {network_duration:.2f} seconds. Status: {response.status_code}")
        
        response.raise_for_status()
        
        print("[TIMING 1.3] Iterating stream chunks and decoding JSON objects natively...")
        decoder = json.JSONDecoder()
        buffer = ""
        filtered_movements = []
        should_abort = False
        total_objects_scanned = 0
        
        # Read the raw TCP data incrementally in 16KB text blocks
        for chunk in response.iter_content(chunk_size=16384, decode_unicode=True):
            if not chunk:
                continue
                
            buffer += chunk
            buffer = buffer.lstrip(r'[,\s')
            
            while buffer:
                try:
                    # Snip exactly ONE individual JSON object out of the text buffer
                    obj, idx = decoder.raw_decode(buffer)
                    buffer = buffer[idx:].lstrip(r'[,\s')
                    total_objects_scanned += 1
                    
                    start_date_str = obj.get("start_date")
                    if not start_date_str:
                        continue
                        
                    # Evaluate the object's creation date
                    movement_date = datetime.strptime(start_date_str.split(" ")[0], "%Y-%m-%d").date()
                    
                    if movement_date >= earliest_date:
                        filtered_movements.append(obj)
                    else:
                        # Optimization: We hit historical logs older than our threshold!
                        # Break out and cut off the connection immediately.
                        print(f"[TIMING 1.3.5] Reached historical boundary date ({movement_date}). Tripping early abort.")
                        should_abort = True
                        break
                        
                except json.JSONDecodeError:
                    # Buffer cut off mid-object, break while loop to fetch the next chunk from the wire
                    break
            
            if should_abort:
                response.close() # Safely close the remote socket stream immediately
                break
                
        print(f"[TIMING 1.4.5] Streaming process finished. Scanned {total_objects_scanned} total items.")
        print(f"[TIMING 1.6] Kept {len(filtered_movements)} items matching timeframe.")
        return filtered_movements

    except Exception as e:
        print(f"[TIMING 1.ERROR] Failed to fetch data: {e}")
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
    
    # BUILD THE TARGET URL LOCALLY HERE USING THE CURRENT GLOBAL CONFIG
    target_url = f"{BASE_URL}{STATION_ID}"
    
    # Pass the variable explicitly into the worker function
    movements = get_dated_movements(target_url, earliest_date)
    
    print(f"[TIMING 2] Returned from data fetching. Proceeding to HTML serialization...")
    loop_start = time.time()

    frequent_counts = {}  
    rare_birds_links = [] 

    # 3. Time the validation parsing loop
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

    # Instead of building a massive HTML string, return a clean dictionary
    report_data = {
        "station_name": STATION_NAME,
        "station_id": STATION_ID,
        "earliest_date": str(earliest_date),
        "current_day": current_day,
        "frequent_birds": frequent_counts, # e.g., {"Kohlmeise": 12, "Blaumeise": 5}
        "rare_birds": rare_birds_links     # List of pre-formatted <a> tags or raw video URLs
    }
    
    print(f"================== [FINISHED Data Processing in {time.time() - total_start:.2f}s] ==================\n")
    return report_data