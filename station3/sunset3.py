# call from crontab '*/16 17-22 * * * ...'
from datetime import datetime, timezone
import ephem # pip install ephem is more current than apt install python3-ephem
import subprocess
from configBird3 import birdpath, read_config_json, update_config_json
import msgBird as ms

def minutes_from_string(timestr):
    """
    Calculates the total minutes from the beginning of the day for a given time string.

    Args:
        timestr: A string in 'HH:MM' format.

    Returns:
        The total minutes as an integer.
    """
    try:
        # Parse the time string into a datetime.time object
        time_object = datetime.strptime(timestr, "%H:%M").time()
        
        # Calculate the total minutes
        total_minutes = time_object.hour * 60 + time_object.minute
        return total_minutes
    except ValueError:
        # In case of an invalid format, it's better to return a clear error or a default value
        return -1 # Return -1 as an indicator of an invalid time string

def datetime_to_string(dt_obj):
    """
    Formats a datetime object to a time string 'HH:MM'.
    
    Args:
        dt_obj: A datetime object.
        
    Returns:
        A string in 'HH:MM' format.
    """
    # Use a different variable name to avoid shadowing the imported datetime module
    return dt_obj.strftime("%H:%M")
    
###main:
try:
    config = read_config_json()
    latitude = config['geoloc'][0]
    longitude = config['geoloc'][1]
    date_saved = config['sun'][0]
    sunrise_saved = config['sun'][1]
    sunset_saved = config['sun'][2]

    # Get current local time
    now = datetime.now()
    now_dateStr = now.strftime("%Y%m%d")
    todayminutes = now.hour * 60 + now.minute

    if now_dateStr == date_saved:
        ms.log(f"{date_saved} sun times from config.json")
        sunset_mins = minutes_from_string(sunset_saved)
    else:
        # Set observer's location and time
        observer = ephem.Observer()
        observer.lat = latitude
        observer.lon = longitude
        observer.date = datetime.now(timezone.utc) # Always use UTC for ephem calculations

        # Calculate sunrise and sunset
        sun = ephem.Sun()
        # next_rising and next_setting will return the time in UTC
        sunrise = observer.next_rising(sun)
        sunset = observer.next_setting(sun)

        # Convert the ephem.Date objects (in UTC) to local datetime objects
        sunrisetime_local = ephem.localtime(sunrise)
        sunsettime_local = ephem.localtime(sunset)
        sunset_mins = sunsettime_local.hour * 60 + sunsettime_local.minute

        # Create a Python dictionary for the data to be saved,
        # rather than creating a JSON-formatted string manually.
        sun_data = {
            "sun": [now_dateStr, datetime_to_string(sunrisetime_local), datetime_to_string(sunsettime_local)]
        }
        ms.log(f"reset {now_dateStr} sun times to config.json")
        update_config_json(sun_data)

    if sunset_mins - 30 < todayminutes: # 30 minutes before sunset
        # print("shutdown from sunset")
        # It's safer to pass a list of arguments to subprocess.run and avoid shell=True
        cmd = f"{birdpath['appdir']}/tasmotaDown.sh sunset-30Down"
        subprocess.run(cmd, shell=True)
    # else:
    #     print("next sunset awaited")
        
except Exception as e:
    print(f"An error occurred: {e}")