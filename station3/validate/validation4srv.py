'''
add todays validation inside endpoint '/daywatch' using birdiary validation api
valid_confirm.html fetching these data from flask endpoint '/api/validation-data'
'''
import time
from datetime import datetime
import requests
from configBird3 import boxId

MOVEMENT_BASE_URL = "https://wiediversistmeingarten.org/api/movement/"
VIDEO_BASE_URL = "https://wiediversistmeingarten.org/api/uploads/videos/"
VALIDATION_BASE_URL = "https://wiediversistmeingarten.org/api/validate/"

def get_today_movements(station_id, log_messages):
    """Fetches movements using the native ?from=YYYY-MM-DD pagination parameter."""
    today_str = datetime.now().date().strftime("%Y-%m-%d")
    paginated_url = f"{MOVEMENT_BASE_URL}{station_id}?from={today_str}"
    
    start_time = time.time()
    try:
        response = requests.get(paginated_url, timeout=30)
        network_duration = time.time() - start_time
        log_messages.append(f"MOV_API: {response.status_code} ({network_duration:.2f} secs)")
        
        response.raise_for_status()
        movements = response.json()
        
        if not isinstance(movements, list):
            log_messages.append("MOV_API_ERR: no JSON list")
            return []

        return movements

    except Exception as e:
        log_messages.append(f"MOV_API_ERR: {e}")
        return []

def find_id_4video(movements, video_url):
    """Searches for a specific video URL in the movements list."""
    for movement in movements:
        if movement.get("video") == video_url:
            return movement.get("mov_id")
    return None

def add_validation(payload, station_id, mov_id, log_messages):
    """Submits species validation data to the API."""
    url = f"{VALIDATION_BASE_URL}{station_id}/{mov_id}"
    try:
        r = requests.put(url, json=payload, timeout=30)
        r.raise_for_status()
        log_messages.append(f"VALID_API: {r.status_code}")
        return True
    except Exception as e:
        log_messages.append(f"VALID_API_ERR: {e}")
        return False

def get_validation_data(video_id, german_name, latin_name):
    """
    Main entry point for Flask. 
    Constructs a request-scoped validation dictionary safely.
    """
    log_messages = []

    # Local result dict for THIS request only
    result = {
        "video_id": video_id or "",
        "german_name": german_name or "",
        "latin_name": latin_name or "",
        "mov_id": None,
        "msg": ""
    }

    # Validation checks (returns structured response instead of exit(1))
    if not video_id:
        log_messages.append("No video ID provided.")
        result["msg"] = " | ".join(log_messages)
        return result

    if not latin_name or not german_name:
        log_messages.append("No latin- or germanName.")
        result["msg"] = " | ".join(log_messages)
        return result

    # Format video target
    video_url = f"{VIDEO_BASE_URL}{video_id}.mp4"

    # Fetch today's movements & locate movement ID
    movements_today = get_today_movements(boxId, log_messages)
    mov_id = find_id_4video(movements_today, video_url)

    if mov_id:
        result["mov_id"] = mov_id
        payload = {
            "validation": {
                "latinName": latin_name,
                "germanName": german_name
            }
        }
        add_validation(payload, boxId, mov_id, log_messages)
    else:
        log_messages.append(f"No movement contains {video_url}")

    result["msg"] = " | ".join(log_messages)
    return result