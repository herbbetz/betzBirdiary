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
import os
from pathlib import Path # to delete old reports
import requests
from datetime import datetime, timedelta
import time
from sharedBird import prev_month
from configBird3 import serverUrl, boxId, boxName, deleteKey

BASE_URL = f"{serverUrl}movement/"
STATION_ID = boxId
STATION_NAME = boxName
API_URL = f"{BASE_URL}{STATION_ID}"
ACCESS_TOKEN = deleteKey # secret for writing to api, Stationsschlüssel nach Einloggen auf birdiary Plattform, -> D:birdiary\githubMirror\ACCESS_TOKEN.txt
today = datetime.today()
CURRENT_MONTH = today.strftime("%Y-%m")
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_PATH = f"{BASE_DIR}/del{CURRENT_MONTH}.html"
months_back = 6
deleteMode = False

# exit if this month's report already exists:
if os.path.exists(OUTPUT_PATH):
    exit(0)
# else remove old reports and build this month's report:
for f in Path(BASE_DIR).glob("del*.html"):
    f.unlink()

start_time = time.time()  # Record the start time

# CSS curley brackets inside f-string would need to be doubled for distinction from f-string brackets, e.g. {{ color: black }}.
html = """<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Delete_movs</title>
<link rel="icon" href="/favicon.svg" type="image/svg+xml">
<link rel="stylesheet" href="/button.css">
<link rel="stylesheet" href="/birdmd.css">
<style>
.new { background-color: pink; }
.old { background-color: gray; }
</style>
</head>
<body>
"""

def add_html(html_str):
    global html # needed for write access
    html += f"{html_str}<br>\n"

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
            add_html("API response format unexpected. Expected a list.")
            return []
        return movements
    except Exception as e:
        add_html(f"Error fetching data: {e}")
        return []

def delete_movements(session, ids, label):
    # Per OpenAPI docs: /api/movement/{station_id}/{movement_id}
    # without deleteData=True videos were kept unreferenced until 08/2026.
    # url = f"{API_URL}/{mov_id}?apikey={ACCESS_TOKEN}&deleteData=True"
    deleted = 0
    for mov_id in ids:
        if mov_id is None:
            add_html(f"Skipping movement with missing id in {label}.")
            continue
        for attempt in range(3):
            try:
                url = f"{API_URL}/{mov_id}?apikey={ACCESS_TOKEN}"
                response = session.delete(url, timeout=10)
                response.raise_for_status()
                deleted += 1
                break
            except Exception as e:
                if attempt < 2:
                    time.sleep(2 ** attempt) # first wait 1 sec (2^0), then 2 secs (so maximum of 3 secs waiting)
                else:
                    add_html(f"Error deleting movement {mov_id} ({label}): {e}")
    total = len(ids)
    ratio = deleted / total if total else 0
    add_html(f"Deleted {deleted}/{total} ({ratio:.2f}) in {label}.")

# main prog part#2:
former_month = CURRENT_MONTH
for _ in range(months_back):
    former_month = prev_month(former_month)
newtime_date = datetime.strptime(f"{former_month}-01", "%Y-%m-%d").date()

add_html(f'<h2>Delete Report of {today.strftime("%Y-%m-%d")}</h2>')
add_html(f'API = {API_URL}')
add_html(f'<p>Der Delete Vorgang wird einmal monatlich für die Zeit von vor {months_back} Monaten durchgeführt.</p>')
add_html(f'<p><b>Alle unvalidierten Movements der Station {STATION_NAME} vor {newtime_date} werden gelöscht, sobald ein gültiger _deleteKey_ in config.json eingetragen ist !!</b></p>')

if ACCESS_TOKEN and not ACCESS_TOKEN.endswith('X'):
    deleteMode = True
else:
    add_html(f"deleteKey '{ACCESS_TOKEN}' invalid, not deleting")

movements = get_movements(newtime_date, old=False)

cnt_all = len(movements)
if cnt_all == 0:
    new_movs_exist = False
    add_html(f"No movements found since {newtime_date}.")
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

        if take_id:
            mid = mov.get("mov_id")
            if mid == None:
                add_html("mov with missing mov_id")
            else: 
                movement_ids.append(mid)

    # cnt_all > 0 guaranteed here, as we returned early if cnt_all == 0
    id_ratio = len(movement_ids) / cnt_all if cnt_all > 0 else 0
    det_ratio = cnt_detect / cnt_all if cnt_all > 0 else 0
    val_ratio = cnt_valid / cnt_all if cnt_all > 0 else 0
    html += '<div class="new">'
    add_html(f'Found {len(movement_ids)} movements for deletion out of {cnt_all} total ({id_ratio:.2f}) since {newtime_date}.')
    add_html(f'Aphelocoma: {cnt_detect} ({det_ratio:.2f}), NoBird: {cnt_valid} ({val_ratio:.2f})')
    html += '</div>'
html += '<hr>'

oldtime_date = newtime_date - timedelta(days=1) # one day before
old_movements = get_movements(oldtime_date, old=True)
cnt_old_all = len(old_movements)
if cnt_old_all == 0:
    old_movs_exist = False
    add_html(f"No movements found before {oldtime_date}.")
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
            mid = mov.get("mov_id")
            if mid == None:
                add_html("mov with missing mov_id")
            else: 
                oldmovement_ids.append(mid)

    old_valid_cnt = cnt_old_all - cnt_no_valid
    old_valid_ratio = old_valid_cnt / cnt_old_all if cnt_old_all > 0 else 0
    nobird_valid_ratio = cnt_nobird_valid / old_valid_cnt if old_valid_cnt > 0 else 0
    html += '<div class="old">'
    add_html(f'{old_valid_cnt} movements out of {cnt_old_all} ({old_valid_ratio:.2f}) have human validation before incl. {oldtime_date}.')
    add_html(f'Among these, {cnt_nobird_valid} ({nobird_valid_ratio:.2f}) are validated as \'NoBird\'.')
    html += '</div>'
html += '<hr>'

if not deleteMode:
    add_html(f"To delete these movements, provide valid deleteKey (Stationsschlüssel) first.")
else:
    # SPEED OPTIMIZATION: Use a Session block to keep TCP connection alive
    if new_movs_exist:
        html += '<div class="new">'
        add_html(f'Deleting {len(movement_ids)} movements since {newtime_date}…')
        with requests.Session() as session:
            delete_movements(session, movement_ids, f"since {newtime_date}")
        html += '</div><hr>'

    if old_movs_exist:
        html += '<div class="old">'
        add_html(f'Deleting {len(oldmovement_ids)} movements before {oldtime_date}…')
        with requests.Session() as session:
            delete_movements(session, oldmovement_ids, f"before {oldtime_date}")
        html += '</div><hr>'

end_time = time.time()    # Record the end time
duration = end_time - start_time  # Calculate duration in seconds
tokenlength = len(ACCESS_TOKEN)
if tokenlength != 32:
    add_html(f"ACCESS_TOKEN {ACCESS_TOKEN} has {tokenlength} digits - normal is 32!")
add_html(f"Script finished in {duration:.2f} seconds.")
html += '<div><a href="/config3.html" class="button">back</a></div></body></html>'
with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
    f.write(html)
 