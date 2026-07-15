#!/usr/bin/env python3
"""
hx_signalanalyzer.py

Analyze SignalLogger output.

States:
    IDLE
    ARRIVAL
    PRESENT
    OVERSIZE
    DEPARTURE
"""

import sys

CAMERA_MIN_PRESENT = 1.0

if len(sys.argv) != 2:
    print("usage: hx_signalanalyzer.py signal_xxx.csv")
    sys.exit(1)

rows = []

with open(sys.argv[1]) as f:
    f.readline()
    for line in f:
        t, mono, raw, offset, weight, state, event, peak, note = line.strip().split(",")
        rows.append({
            "time": t,
            "mono": float(mono),
            "raw": int(raw),
            "offset": float(offset),
            "weight": float(weight),
            "state": state,
            "event": None if event == "None" else event,
            "peak": float(peak),
            "note": None if note == "None" else note
        })

print()
print(f"samples : {len(rows)}")
print(f"first   : {rows[0]['time']}")
print(f"last    : {rows[-1]['time']}")

periods = []
start = 0
state = rows[0]["state"]

for i in range(1, len(rows)):
    if rows[i]["state"] != state:
        r = rows[start:i]
        periods.append({
            "state": state,
            "rows": r,
            "duration": r[-1]["mono"] - r[0]["mono"]
        })
        start = i
        state = rows[i]["state"]

r = rows[start:]
periods.append({
    "state": state,
    "rows": r,
    "duration": r[-1]["mono"] - r[0]["mono"]
})

visits = []
oversize = []

current = None
over = None

for p in periods:
    state = p["state"]
    r = p["rows"]

    if state == "ARRIVAL":
        current = {
            "arrival": r[0]["time"],
            "peak": max(x["weight"] for x in r)
        }

    elif state == "PRESENT" and current:
        current["present"] = r[0]["time"]
        current["duration"] = p["duration"]
        w = [x["weight"] for x in r]
        current["mean"] = sum(w) / len(w)
        current["peak"] = max(current["peak"], max(w))

    elif state == "OVERSIZE":
        over = {
            "arrival": r[0]["time"],
            "duration": p["duration"],
            "peak": max(x["weight"] for x in r)
        }

    elif state == "DEPARTURE":
        if over:
            over["leave"] = r[0]["time"]
            oversize.append(over)
            over = None
        elif current:
            current["leave"] = r[0]["time"]

    elif state == "IDLE":
        if current:
            current["idle"] = r[0]["time"]
            visits.append(current)
            current = None

print()
print("Bird visits")
print("-----------")

for i, v in enumerate(visits, 1):
    print()
    print(f"Visit {i}")
    print(f"  arrival : {v.get('arrival')}")
    print(f"  present : {v.get('present')}")
    print(f"  leave   : {v.get('leave')}")
    print(f"  idle    : {v.get('idle')}")
    if "duration" in v:
        print(f"  stay    : {v['duration']:.1f} s")
    if "mean" in v:
        print(f"  mean    : {v['mean']:.2f} g")
    print(f"  peak    : {v['peak']:.2f} g")

print()
print("Oversize events")
print("----------------")

if oversize:
    print(f"total : {len(oversize)}")
    for i, e in enumerate(oversize, 1):
        print()
        print(f"Event {i}")
        print(f"  arrival : {e['arrival']}")
        print(f"  leave   : {e.get('leave')}")
        print(f"  duration: {e['duration']:.1f} s")
        print(f"  peak    : {e['peak']:.2f} g")
else:
    print("none")

print()
print("Contact statistics")
print("-------------------")

valid = [v for v in visits if "duration" in v and v["duration"] >= CAMERA_MIN_PRESENT]
brief = [v for v in visits if "duration" in v and v["duration"] < CAMERA_MIN_PRESENT]
short = [v for v in visits if "duration" not in v]

print(f"total contacts : {len(visits)}")
print(f"valid visits   : {len(valid)}")
print(f"brief visits   : {len(brief)}")
print(f"short contacts : {len(short)}")
print(f"oversize       : {len(oversize)}")

if valid:
    durations = [v["duration"] for v in valid]
    print()
    print("Valid visit durations")
    print("---------------------")
    print(f"minimum : {min(durations):.2f} s")
    print(f"maximum : {max(durations):.2f} s")
    print(f"mean    : {sum(durations)/len(durations):.2f} s")

print()
print("Camera trigger simulation")
print("-------------------------")
print(f"threshold     : {CAMERA_MIN_PRESENT:.2f} s")
print(f"would trigger : {len(valid)}")

idle = [r["weight"] for r in rows if r["state"] == "IDLE"]

if idle:
    print()
    print("Idle statistics")
    print("----------------")
    print(f"mean weight : {sum(idle)/len(idle):.2f} g")
    print(f"minimum     : {min(idle):.2f} g")
    print(f"maximum     : {max(idle):.2f} g")

print()
print("Warnings")
print("--------")

found = False

for r in rows:
    if r["state"] == "IDLE" and abs(r["weight"]) > 5:
        print(f"IDLE outside ±5 g at {r['time']} ({r['weight']:.2f} g)")
        found = True
        break

if oversize:
    print(f"Oversize events detected: {len(oversize)}")
    found = True

if not found:
    print("none")

print()
print("Summary")
print("-------")
print(f"visits   : {len(visits)}")

if visits:
    stays = [v["duration"] for v in visits if "duration" in v]
    peaks = [v["peak"] for v in visits]

    if stays:
        print(f"mean stay: {sum(stays)/len(stays):.1f} s")
        print(f"longest  : {max(stays):.1f} s")

    print(f"highest  : {max(peaks):.2f} g")

if oversize:
    print(f"oversize : {len(oversize)}")
    print(f"max size : {max(x['peak'] for x in oversize):.2f} g")