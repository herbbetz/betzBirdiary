import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime
from collections import defaultdict
import json

# Load data from file
with open("camdataDev.json", "r") as f:
    data = json.load(f)
# example data: [{"timestamp": "2025:07:28:06:12", "brightness": 90, "metaLux": 1400, "luxcategory": 3}, ...]

# Parse data into day-wise curves
keyParam = 'metaLux'

curves = defaultdict(list)
for entry in data:
    # Parse timestamp: YYYY:MM:DD:HH:MM
    year, month, day, hour, minute = map(int, entry['timestamp'].split(':'))
    dt = datetime(year=year, month=month, day=day, hour=hour, minute=minute)
    # Key: (year, month, day), Value: (datetime, brightness)
    day_key = (year, month, day)
    curves[day_key].append((dt, entry[keyParam]))
# example: curves[(2025, 7, 28)] = [(datetime(2025,7,28,6,12), 90), ...]
# Sort each day's data by time
for day_key in curves:
    curves[day_key].sort(key=lambda x: x[0])

# Plotting
fig, ax = plt.subplots(figsize=(10, 5))

colors = ['tab:blue', 'tab:orange', 'tab:green', 'tab:red']
for idx, (day_key, points) in enumerate(curves.items()):
    times = [dt.time() for dt, _ in points]
    brightness = [b for _, b in points]
    # Convert times to minutes since midnight for x-axis
    x_vals = [t.hour * 60 + t.minute for t in times]
    label = f"{day_key[1]:02d}-{day_key[2]:02d}" # year not needed
    # label = f"{day_key[0]}-{day_key[1]:02d}-{day_key[2]:02d}"  # year-month-day
    ax.plot(x_vals, brightness, label=label, color=colors[idx % len(colors)], marker='o')

# X-axis ticks: hours of the day
ax.set_xticks([i * 60 for i in range(0, 24, 2)])
ax.set_xticklabels([f"{i:02d}:00" for i in range(0, 24, 2)])
ax.set_xlim(0, 1439)
ax.set_xlabel("Time of Day")
ax.set_ylabel(keyParam)
ax.set_title(f"{keyParam} Curves for Each Day")
ax.legend(title="Date")
ax.grid(True)

plt.tight_layout()
plt.savefig("brightness_curves.svg", format="svg")