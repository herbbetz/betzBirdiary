# gemini 23.4.26
# "Rheingarten KI-Match: Analyze movement data for March 2026 to find matches between detections (birdiary platform KI) and validations (human validators)."
#  
import requests

# The specific station URL
BASE_URL = "https://wiediversistmeingarten.org/api/movement/" # station_id of Rheingarten
TARGET_MONTH = "2026-03"
STATION_NAME = "Rheingarten"
STATION_ID = "f4f61b9b-4390-4de1-987d-bf72220158e4"
API_URL = f"{BASE_URL}{STATION_ID}"

def analyze_movements():
    try:
        response = requests.get(API_URL, timeout=30)
        response.raise_for_status()
        movements = response.json()
    except Exception as e:
        print(f"Error fetching data: {e}")
        return

    total_march_movements = 0
    validations_found = 0
    matches_found = 0

    for m in movements:
        # Filter for TARGET_MONTH
        if m.get("start_date", "").startswith(TARGET_MONTH):
            total_march_movements += 1
            
            # 1. Check if validations exist
            vals = m.get("validation", {}).get("validations", [])
            
            if vals:
                validations_found += 1
                
                # 2. If validations exist, check for a match with detection
                dets = m.get("detections", [])
                
                # Only compare if we have both detection and validation data
                if dets:
                    # Using index [0] safely
                    det_name = dets[0].get("germanName")
                    val_name = vals[0].get("germanName")
                    
                    if det_name == val_name:
                        matches_found += 1

    # Output results per your requirements
    print(f"Station: {STATION_NAME} ({STATION_ID})")
    print(f"Total videos in {TARGET_MONTH}: {total_march_movements}")
    print(f"Human Validations found: {validations_found}")
    print(f"Validations with KI matches found: {matches_found}")
    
    if validations_found > 0:
        match_rate = (matches_found / validations_found) * 100
        print(f"Match rate: {match_rate:.2f}%")
    else:
        print("Match rate: N/A (No validations found)")

if __name__ == "__main__":
    analyze_movements()