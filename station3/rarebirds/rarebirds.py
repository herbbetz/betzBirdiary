'''
interesting.py for finding interesting videos of manually validated rarer birds on "https://wiediversistmeingarten.org/api/movement/"
using german bird labels from "webserver-main2026-04-18/nginx/data_visualization/src/helpers/labels.js"
'''
import requests
from datetime import datetime
from sharedBird import prev_month

BASE_URL = "https://wiediversistmeingarten.org/api/movement/"
STATION_ID = "87bab185-7630-461c-85e6-c04cf5bab180"
API_URL = f"{BASE_URL}{STATION_ID}"
month_back = 3
FREQUENT_BIRDS = {"Haussperling", "Feldsperling", "Gimpel", "Blaumeise",  "Kohlmeise", "Rotkehlchen", "Buchfink", "Gruenfink", "Kleiber"} # sets are scanned faster than lists or tuples, and they don't allow duplicates, so a set is appropriate here.

def get_movements():
    try:
        response = requests.get(API_URL, timeout=30)
        response.raise_for_status()
        movements = response.json()
        if not isinstance(movements, list):
            print("API response format unexpected. Expected a list.")
            return []
        return movements
    except Exception as e:
        print(f"Error fetching data: {e}")
        return []

def get_dated_movements(earliest_date):
    try:
        response = requests.get(API_URL, timeout=30)
        response.raise_for_status()
        movements = response.json()
        if not isinstance(movements, list):
            print("API response format unexpected. Expected a list.")
            return []
        
        filtered_movements = []
        for movement in movements:
            # Extract the start_date string (e.g., "2025-04-29 11:07:16.129554")
            start_date_str = movement.get("start_date")
            if not start_date_str:
                continue
                
            # Parse only the date portion (YYYY-MM-DD) to compare with earliest_date
            # Splitting by space isolates '2025-04-29'
            movement_date = datetime.strptime(start_date_str.split(" ")[0], "%Y-%m-%d").date()
            
            # Keep the element if it falls within your timeframe
            if movement_date >= earliest_date:
                filtered_movements.append(movement)
                
        return filtered_movements

    except Exception as e:
        print(f"Error fetching data: {e}")
        return []

def write_html_file(filename, html_content):
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(html_content)
        print(f"HTML output written to {filename}")
    except Exception as e:
        print(f"Error writing HTML file: {e}")

if __name__ == "__main__":
    today = datetime.today()
    current_day = today.strftime("%Y-%m-%d")

    '''
    ### option1: Get all movements
    movements = get_movements()
    last_movement = movements[-1]
    last_date_str = last_movement.get("start_date")
    earliest_date = datetime.strptime(last_date_str.split(" ")[0], "%Y-%m-%d").date()
    ### end option1
    '''

    ### option2: Only movements since 3 months back
    current_month = today.strftime("%Y-%m")
    for _ in range(month_back):
        current_month = prev_month(current_month)
    earliest_date = datetime.strptime(f"{current_month}-01", "%Y-%m-%d").date()
    movements = get_dated_movements(earliest_date)
    ### end option2

    # Dictionaries to hold our sorted results
    frequent_counts = {}  # e.g., {"Gruenfink": 5}
    rare_birds_links = [] # e.g., ["<a href=...>...</a>"]

    for mov in movements:
        # Check if the movement has a validation object and a list of validations
        validation_data = mov.get("validation", {})
        validations = validation_data.get("validations", []) if validation_data else []
        
        for v in validations:
            german_name = v.get("germanName")
            
            # Skip if there's no valid German name recorded yet
            if not german_name:
                continue
                
            if german_name in FREQUENT_BIRDS:
                # Increment count for frequent birds
                frequent_counts[german_name] = frequent_counts.get(german_name, 0) + 1
            else:
                # Process rare bird video link
                video_url = mov.get("video")
                start_date_str = mov.get("start_date", "")
                
                if video_url and start_date_str:
                    # Clean up the date string for the link text (e.g., "2025-04-29_110716")
                    # Replaces spaces with underscores and removes microseconds/seconds formatting details if desired
                    date_clean = start_date_str.split(".")[0].replace(" ", "_").replace(":", "")
                    link_text = f"{german_name}_{date_clean}"
                    
                    html_link = f'<a href="{video_url}" target="_blank">{link_text}</a>'
                    rare_birds_links.append(html_link)

    # --- Generate Simple HTML Output ---
    html_head = '''
    <!DOCTYPE html>
    <html lang="de">
    <head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>RareBirds</title>
    </head>
    <body>
    '''
    html_output = [html_head]
    html_output.append("<h1>Rare Bird Video Report</h1>")
    html_output.append(f"<p>Human validations<br>of station <b>{STATION_ID}</b><br>from {earliest_date} to {current_day}</p>")
    html_output.append("<h3>Frequent Birds</h3>")
    html_output.append("<ul>")
    for bird, count in frequent_counts.items():
        html_output.append(f"  <li>{bird}: {count}</li>")
    html_output.append("</ul>")

    html_output.append("<h3>Rare Bird Videos</h3>")
    html_output.append("<ul>")
    for link in rare_birds_links:
        html_output.append(f"  <li>{link}</li>")
    html_output.append("</ul>")
    html_output.append("</body></html>")
    # Join everything into a single HTML block string
    final_html = "\n".join(html_output)
    
    # Write the HTML output to a file
    write_html_file("rarebirds.html", final_html)