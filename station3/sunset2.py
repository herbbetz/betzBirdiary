# call from crontab
from datetime import datetime
import ephem # pip install ephem is more current than apt install python3-ephem
import subprocess
from configBird3 import birdpath

# Get current local time
now = datetime.now()
todayminutes = now.hour * 60 + now.minute

# Convert to PyEphem Date
ephem_date = ephem.Date(now)

# Set observer's location and time
observer = ephem.Observer()
observer.lat = '48.533509'  # Landshut latitude
observer.lon = '12.137590'
observer.date = ephem_date

# Calculate sunrise and sunset
sun = ephem.Sun()
# sunrise = observer.next_rising(sun)
sunset = observer.next_setting(sun) # will always be in the future of now, therefore compare only hours and minutes

# print("Sunrise:", ephem.localtime(sunrise))
sunsettime = ephem.localtime(sunset)
todaySunsetMinutes = sunsettime.hour * 60 + sunsettime.minute
# print("Sunset:", sunsettime)
if (todaySunsetMinutes - 30 < todayminutes): # 30 minutes before sunset
    # print("shutdown from sunset")
    cmd = f"{birdpath['appdir']}/tasmotaDown.sh sunset-30Down"
    subprocess.call(cmd, shell=True)
# else:
#     print("next sunset awaited")