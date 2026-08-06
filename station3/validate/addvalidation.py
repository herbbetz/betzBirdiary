'''
find interesting videos of manually validated rarer birds on "https://wiediversistmeingarten.org/api/movement/"
manually using german bird labels from "webserver-main2026-04-18/nginx/data_visualization/src/helpers/labels.js", see germanLabels.js
'''
import requests
from datetime import datetime
import time
import json
# from configBird3 import (boxId, boxName)
boxId = "87bab185-7630-461c-85e6-c04cf5bab180"  # Replace with actual boxId
boxName = "your_box_name_here"  # Replace with actual boxName

MOVEMENT_BASE_URL = "https://wiediversistmeingarten.org/api/movement/"
VIDEO_BASE_URL = "https://wiediversistmeingarten.org/api/uploads/videos/"
VALIDATION_BASE_URL = "https://wiediversistmeingarten.org/api/validate/"
VIDEO_ID = ""

def set_video_id(video_id):
    """
    Sets the video ID for searching in movements.
    """
    global VIDEO_ID
    VIDEO_ID = f"{video_id}.mp4"

def get_today_movements(station_id):
    """
    Fetches movements using the native ?from=YYYY-MM-DD pagination parameter.
    """
    today = datetime.now().date()
    today_str = today.strftime("%Y-%m-%d")
 
    paginated_url = f"{MOVEMENT_BASE_URL}{station_id}?from={today_str}"
    print(f"[API PAGINATION] Fetching {paginated_url}")
    start_time = time.time()
    try:
        response = requests.get(paginated_url, timeout=30)
        network_duration = time.time() - start_time
        print(f"[API PAGINATION] Response received in {network_duration:.2f} seconds. Status: {response.status_code}")
        
        response.raise_for_status()
        movements = response.json()
        
        if not isinstance(movements, list):
            print("[API PAGINATION.ERROR] Expected JSON payload array list structure. Received incompatible type.")
            return []

        return movements

    except Exception as e:
        print(f"[API PAGINATION.ERROR] retrieval failed: {e}")
        return []

def find_id_4video(movements, video_id):
    """
    Searches for a specific video ID in the movements list.
    """
    for movement in movements:
        if movement.get("video") == video_id:
            mov_id = movement.get("mov_id")
            # validation_status = movement.get("validation", {}).get("val_yes", "val_no")  # Default to "val_no" if not found
            return mov_id
    return None

def addValidation(payload, stationid, movid):
    #payload = {"validation": {"latinName": "test2"}}
    theurl = VALIDATION_BASE_URL + stationid + "/" + movid
    r = requests.put(theurl, json=payload)
    print(r)

if __name__ == "__main__":

    movements_today = get_today_movements(boxId)
    print(f"Movements today for station {boxName}: {len(movements_today)}")

    video_id = "2026-08-05_064245.880350"  # example: "2026-04-20_090658.863742"
    set_video_id(video_id)
    if not VIDEO_ID:
        print("No video ID to search for")
        exit(1)
    video_url = f"{VIDEO_BASE_URL}{VIDEO_ID}"
    mov_id = find_id_4video(movements_today, video_url)
    if mov_id:
        print(f"{video_id} found in {mov_id}")
    else:
        print(f"No movement found for {video_url}")
        exit(0)

    latinName = "None"
    germanName = "KEIN_VOGEL"
    if not latinName or not germanName:
        print("No latinName or germanName provided for validation. Exiting.")
        exit(1)

    payload = {"validation": {"latinName": latinName, "germanName": germanName}}
    print(f"try adding to {mov_id}: {payload}")
    addValidation(payload, boxId, mov_id)

    
