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

humids = []
counts = []
dates = []
total_counts = 0

for hour_str, stats in hourly_data.items():
    dt = datetime.strptime(hour_str, '%Y%m%d%H')
    dates.append(dt)
    humids.append(stats['humid'])
    counts.append(stats['count'])
    total_counts += stats['count']

# Find date range
if dates:
    oldest = min(dates)
    newest = max(dates)
    date_range_str = f"from {oldest.strftime('%Y-%m-%d')} to {newest.strftime('%Y-%m-%d')}"
else:
    date_range_str = "no data"

# Plot scatter
fig, ax = plt.subplots(figsize=(10, 6))
ax.scatter(humids, counts, color='royalblue', s=50)

ax.set_xlabel('Humidity rel %')
ax.set_ylabel('Videos per hour')
ax.set_title('Hourly videos vs Humidity')

plt.figtext(0.13, 0.86, date_range_str, fontsize=10, ha='left')
plt.figtext(0.13, 0.81, f"Videos total: {total_counts}", fontsize=10, ha='left')
plt.figtext(0.13, 0.76, f"as of: {created}", fontsize=10, ha='left')

plt.tight_layout()
plt.savefig('countsbyhumid.svg', format='svg')
# plt.show()