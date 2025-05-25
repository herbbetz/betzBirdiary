'''
Copy the data from your https://wiediversistmeingarten.org/api/movement/<stationID> (e.g. mine is https://wiediversistmeingarten.org/api/movement/87bab185-7630-461c-85e6-c04cf5bab180 )
and save it as a JSON file, e.g. "data.json".
Then type "python show_hours.py data.json" .
videos[0] is the count of all videos from 0:00 to 0:59 (start_date), etc.
People running their station 24/7 will see, at what hours they have the most videos.
script from 25-5-2025 with the aid of github-copilot.
'''
import sys
import json
from collections import defaultdict

def extract_hour(start_date_str):
    """
    Extracts the hour as an integer from a start_date string of format "YYYY-MM-DD HH:MM:SS.ssssss".
    Returns the hour (0-23) or None if parsing fails.
    """
    try:
        time_part = start_date_str.split()[1]
        hour_str = time_part.split(":")[0]
        return int(hour_str)
    except (IndexError, AttributeError, ValueError):
        return None

def extract_date(start_date_str):
    """
    Extracts the date part ("YYYY-MM-DD") from a start_date string.
    """
    try:
        return start_date_str.split()[0]
    except (IndexError, AttributeError):
        return ""

def main():
    if len(sys.argv) < 2:
        print("Usage: python count_by_hour_and_print_extremes.py <input.json>")
        sys.exit(1)

    filename = sys.argv[1]
    with open(filename, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Extract all start_date entries
    start_dates = [item["start_date"] for item in data if "start_date" in item]

    # Initialize counts for each hour (0-23)
    hour_counts = defaultdict(int)

    # For finding earliest and latest date
    dates = []

    for sd in start_dates:
        hour = extract_hour(sd)
        if hour is not None:
            hour_counts[hour] += 1
        date = extract_date(sd)
        if date:
            dates.append(date)

    # Print counts for each hour (0-23)
    total = 0
    for hour in range(24):
        print(f"videos[{hour}] = {hour_counts[hour]}")
        total += hour_counts[hour]
    print(f"sum of all videos = {total}")

    if dates:
        earliest = min(dates)
        latest = max(dates)
        print(f"Earliest date in data: {earliest}")
        print(f"Latest date in data: {latest}")

if __name__ == "__main__":
    main()