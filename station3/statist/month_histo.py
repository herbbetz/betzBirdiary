import json
import matplotlib.pyplot as plt
from datetime import datetime
from collections import defaultdict
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
month_counts = defaultdict(int)
dates = []
total_counts = 0

for hour_str, stats in hourly_data.items():
    dt = datetime.strptime(hour_str, '%Y%m%d%H')
    month_label = dt.strftime('%Y-%m')
    month_counts[month_label] += stats['count']
    dates.append(dt)
    total_counts += stats['count']

# Sort months chronologically
sorted_months = sorted(month_counts.keys())
counts = [month_counts[m] for m in sorted_months]

# Find date range
if dates:
    oldest = min(dates)
    newest = max(dates)
    date_range_str = f"from {oldest.strftime('%Y-%m-%d')} to {newest.strftime('%Y-%m-%d')}"
else:
    date_range_str = "no data"

# Plot
fig, ax = plt.subplots(figsize=(12, 6))
bars = ax.bar(range(len(sorted_months)), counts, color='mediumseagreen')

ax.set_xlabel('Month')
ax.set_ylabel('Videos')
ax.set_title('Monthly Video Count')

# Set ticks and labels properly
ax.set_xticks(range(len(sorted_months)))
ax.set_xticklabels(sorted_months, rotation=45, ha='right')

plt.figtext(0.13, 0.86, date_range_str, fontsize=10, ha='left')
plt.figtext(0.13, 0.81, f"videos total: {total_counts}", fontsize=10, ha='left')
plt.figtext(0.13, 0.76, f"as of: {created}", fontsize=10, ha='left')

plt.tight_layout()
plt.savefig('month_histo.svg', format='svg')
# plt.show()