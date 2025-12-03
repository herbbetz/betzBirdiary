import json
import matplotlib.pyplot as plt
from datetime import datetime
from dateslice import start_date, end_date
apidatafile = "/home/pi/station3/ramdisk/apidata.json"
# Load data
with open(apidatafile) as f:
    data = json.load(f)

unfiltered = data['data']
created = data.get('created', '') # avoids KeyError, if 'created' not exists

### this is only needed for treating a part (slice) of the data:
# filter for range of dates in format yyyymmdd -> 8 digits
# start_date = None #"20250101"
# end_date = None

dateslist = [k[:8] for k in unfiltered]
if not start_date:
    start_date = dateslist[0]
if not end_date:
    end_date = dateslist[-1]

hourly_data = {
    k: v for k, v in unfiltered.items()
    if start_date <= k[:8] <= end_date
}

# Prepare data structures
hour_counts = {h: 0 for h in range(24)} # prepare 24 fields and init them with 0
dates = []
total_counts = 0 # or total_counts = len(hourly_data)

for hour_str, stats in hourly_data.items():
    dt = datetime.strptime(hour_str, '%Y%m%d%H')
    hour = dt.hour
    hour_counts[hour] += stats['count']
    dates.append(dt)
    total_counts += stats['count']

# Find date range
if dates:
    oldest = min(dates)
    newest = max(dates)
    date_range_str = f"from {oldest.strftime('%Y-%m-%d')} to {newest.strftime('%Y-%m-%d')}"
else:
    date_range_str = "no data"
    oldest = newest = None

# Plot
fig, ax = plt.subplots(figsize=(10, 6))
hours = list(range(24))
counts = [hour_counts[h] for h in hours]
bars = ax.bar(hours, counts, color='skyblue')

# Add axis labels and title
ax.set_xlabel('Hour of Day')
ax.set_ylabel('Videos')
ax.set_title('Hourly Bird Videos')

# Annotate date range, total counts, and created date
plt.figtext(0.13, 0.86, date_range_str, fontsize=10, ha='left')
plt.figtext(0.13, 0.81, f"videos total: {total_counts}", fontsize=10, ha='left')
plt.figtext(0.13, 0.76, f"as of: {created}", fontsize=10, ha='left')

ax.set_xticks(hours)
ax.set_xticklabels([str(h) for h in hours])

plt.tight_layout()
plt.savefig('hours_histo.svg', format='svg')
# plt.show() # WSL cannot open a window, as it has no Xserver