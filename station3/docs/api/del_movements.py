'''
Delete following movements from my API:
- filter my movements by date, using API ?from=2026-06-01
- look for movements with first detection = Aphelocoma_californica (calif. scrub jay, Kalifornienhäher) or Larus_occidentalis (western gull, Westmöwe),
    save movement_id to list for deletion of these bogus KI classifications
- look for movements with first validation = None, save movement_id to list
- print len(movement_ids)/all movements found
- if in deleteMode, delete all movements in list from API, using DELETE method with access token

-- take the first day of 6 months ago, e.g. 2026-01-01
-- from this day (?from=2026-01-01) delete all unvalidated aphelocoma & larus detections and all “None” = no Bird validations
-- take one day before this (?to=2025-12-31) and delete all records with no validation and with validation “None” = no bird
'''

import sys
import requests
from datetime import datetime, timedelta
import time

BASE_URL = "https://wiediversistmeingarten.org/api/movement/"
STATION_ID = "87bab185-7630-461c-85e6-c04cf5bab180"
STATION_NAME = "Betzbirdiary"
API_URL = f"{BASE_URL}{STATION_ID}"
ACCESS_TOKEN = "XXXX" # secret for writing to api, Stationsschlüssel nach Einloggen auf birdiary Plattform, -> D:birdiary\githubMirror\ACCESS_TOKEN.txt
months_back = 6

def prev_month(month_str): # e.g. month_str = '2026-04'
    ### see sharedBird.py
    # Split and convert to integers
    year, month = map(int, month_str.split('-'))
    # Calculate previous month
    if month > 1:
        month -= 1
    else:
        year -= 1
        month = 12
    # Return formatted string with zero-padding (:02d)
    return f"{year}-{month:02d}"

def get_movements(cutoff_date, old=False):
    try:
        # the f-string converts date object to string like 'date_str = date.strftime("%Y-%m-%d")' would do, e.g. '2026-06-01':
        if old:
            response = requests.get(f"{API_URL}?to={cutoff_date}", timeout=30)
        else:
            response = requests.get(f"{API_URL}?from={cutoff_date}", timeout=30)
        response.raise_for_status()
        movements = response.json()
        if not isinstance(movements, list):
            print("API response format unexpected. Expected a list.")
            return []
        return movements
    except Exception as e:
        print(f"Error fetching data: {e}")
        return []

def main():
    global ACCESS_TOKEN
    deleteMode = False
    if len(sys.argv) > 2 and sys.argv[1] == "delete":
        ACCESS_TOKEN = sys.argv[2]
        if ACCESS_TOKEN and not ACCESS_TOKEN.endswith('X'):
            deleteMode = True
        else:
            print(f"ACCESS_TOKEN '{ACCESS_TOKEN}' unvalid, not deleting")    
    
    today = datetime.today()
    current_month = today.strftime("%Y-%m")
    for _ in range(months_back):
        current_month = prev_month(current_month)
    newtime_date = datetime.strptime(f"{current_month}-01", "%Y-%m-%d").date()

    movements = get_movements(newtime_date, old=False)

    cnt_all = len(movements)
    if cnt_all == 0:
        new_movs_exist = False
        print(f"No movements found since {newtime_date}.")
    else:
        new_movs_exist = True
        cnt_detect = 0
        cnt_valid = 0
        movement_ids = []
        for mov in movements:
            take_id = False
            keep = False

            validation_data = mov.get("validation", {})
            validations = validation_data.get("validations", []) if validation_data else []
            if validations and validations[0]:
                val_latin = validations[0].get("latinName", "").strip() if validations[0].get("latinName") else ""
                if val_latin == "None":
                    take_id = True
                    cnt_valid += 1
                else: keep = True

            # step2: detections take_id for delete only, if validations[0] is empty (not None)
            if not keep:
                detections = mov.get("detections", [])
                if detections and detections[0]:
                    det_latin = (detections[0].get("latinName") or "").strip()
                    if det_latin in ("Aphelocoma californica", "Larus occidentalis"):
                        take_id = True
                        cnt_detect += 1
            detections = mov.get("detections", [])
            if detections and detections[0]:
                det_latin = detections[0].get("latinName", "").strip() if detections[0].get("latinName") else ""
                if not keep and det_latin in ("Aphelocoma californica", "Larus occidentalis"):
                    take_id = True
                    cnt_detect += 1

            if take_id:
                movement_ids.append(mov.get("mov_id"))

        # cnt_all > 0 guaranteed here, as we returned early if cnt_all == 0
        id_ratio = len(movement_ids) / cnt_all if cnt_all > 0 else 0
        det_ratio = cnt_detect / cnt_all if cnt_all > 0 else 0
        val_ratio = cnt_valid / cnt_all if cnt_all > 0 else 0
        print(f"Found {len(movement_ids)} movements out of {cnt_all} total ({id_ratio:.2f}) since {newtime_date}.")
        print(f"Aphelocoma: {cnt_detect} ({det_ratio:.2f}), NoBird: {cnt_valid} ({val_ratio:.2f})")
    print("=======================================================================================")

    oldtime_date = newtime_date - timedelta(days=1) # one day before
    old_movements = get_movements(oldtime_date, old=True)
    cnt_old_all = len(old_movements)
    if cnt_old_all == 0:
        old_movs_exist = False
        print(f"No movements found before {oldtime_date}.")
    else:
        old_movs_exist = True
        cnt_no_valid = 0
        cnt_nobird_valid = 0
        oldmovement_ids = []
        for mov in old_movements:
            take_id = False
            #use this to delete unvalidated movements:
            if "validation" not in mov:
                take_id = True
                cnt_no_valid += 1
            else:
                validation_data = mov.get("validation", {})
                validations = validation_data.get("validations", []) if validation_data else []
                if validations and validations[0]:
                    val_latin = validations[0].get("latinName", "").strip() if validations[0].get("latinName") else ""
                    if val_latin == "None":
                        take_id = True
                        cnt_nobird_valid += 1
            
            if take_id:
                oldmovement_ids.append(mov.get("mov_id"))

        old_valid_cnt = cnt_old_all - cnt_no_valid
        old_valid_ratio = old_valid_cnt / cnt_old_all if cnt_old_all > 0 else 0
        nobird_valid_ratio = cnt_nobird_valid / old_valid_cnt if old_valid_cnt > 0 else 0
        print(f"{old_valid_cnt} movements out of {cnt_old_all} ({old_valid_ratio:.2f}) have human validation before incl. {oldtime_date}.")
        print(f"Among these, {cnt_nobird_valid} ({nobird_valid_ratio:.2f}) are validated as 'NoBird'.")
    print("=======================================================================================")

    if not deleteMode:
        print(f"To delete these movements, run 'python {sys.argv[0]} delete ACCESS_TOKEN'.")
        return

    # SPEED OPTIMIZATION: Use a Session block to keep TCP connection alive
    if new_movs_exist:
        print(f"Deleting {len(movement_ids)} movements since {newtime_date}...")
        deleted_count = 0
        with requests.Session() as session:
            for mov_id in movement_ids:
                try:
                    # Per OpenAPI docs: /api/movement/{station_id}/{movement_id}
                    url = f"{API_URL}/{mov_id}?apikey={ACCESS_TOKEN}"
                    response = session.delete(url, timeout=10)
                    response.raise_for_status()
                    # print(f"Deleted movement {mov_id}.")
                    deleted_count += 1
                except Exception as e:
                    print(f"Error deleting movement {mov_id}: {e}")

        all_deleted_count = len(movement_ids)
        del_ratio = deleted_count / all_deleted_count if movement_ids else 0
        print(f"Deleted {deleted_count} out of {all_deleted_count} movements ({del_ratio:.2f}) since {newtime_date}.")
        print("=======================================================================================")

    if old_movs_exist:
        print(f"Deleting {len(oldmovement_ids)} movements before incl. {oldtime_date}...")
        deleted_count = 0
        with requests.Session() as session:
            for mov_id in oldmovement_ids:
                try:
                    # Per OpenAPI docs: /api/movement/{station_id}/{movement_id}
                    url = f"{API_URL}/{mov_id}?apikey={ACCESS_TOKEN}"
                    response = session.delete(url, timeout=10)
                    response.raise_for_status()
                    # print(f"Deleted movement {mov_id}.")
                    deleted_count += 1
                except Exception as e:
                    print(f"Error deleting movement {mov_id}: {e}")

        all_deleted_count = len(oldmovement_ids)
        del_ratio = deleted_count / all_deleted_count if oldmovement_ids else 0
        print(f"Deleted {deleted_count} out of {all_deleted_count} movements ({del_ratio:.2f}) before incl. {oldtime_date}.")
    print("Done.")

if __name__ == "__main__":
    start_time = time.time()  # Record the start time
    
    main()
    
    end_time = time.time()    # Record the end time
    duration = end_time - start_time  # Calculate duration in seconds
    
    print("=======================================================================================")
    print(f"Script finished in {duration:.2f} seconds.")
