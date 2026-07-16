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

visit = None
over = None

for p in periods:

    state = p["state"]
    r = p["rows"]

    if state == "ARRIVAL":
        visit = {
            "arrival": r[0]["time"],
            "peak": max(x["weight"] for x in r)
        }

    elif state == "PRESENT" and visit:
        w = [x["weight"] for x in r]
        visit["present"] = r[0]["time"]
        visit["duration"] = p["duration"]
        visit["mean"] = sum(w) / len(w)
        visit["peak"] = max(visit["peak"], max(w))

    elif state == "OVERSIZE":
        over = {
            "arrival": r[0]["time"],
            "duration": p["duration"],
            "peak": max(x["weight"] for x in r)
        }

    elif state == "DEPARTURE":
        if visit:
            visit["leave"] = r[0]["time"]
        if over:
            over["leave"] = r[0]["time"]
            oversize.append(over)
            over = None

    elif state == "IDLE":
        if visit:
            visit["idle"] = r[0]["time"]
            visits.append(visit)
            visit = None

print()
print("Bird visits")
print("-----------")

for i, v in enumerate(visits, 1):
    print()
    print(f"Visit {i}")
    print(f"  arrival : {v['arrival']}")
    print(f"  present : {v['present']}")
    print(f"  leave   : {v['leave']}")
    print(f"  idle    : {v['idle']}")
    print(f"  stay    : {v['duration']:.1f} s")
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

triggered = [v for v in visits if v["duration"] >= CAMERA_MIN_PRESENT]

print()
print("Visit statistics")
print("----------------")
print(f"visits         : {len(visits)}")
print(f"camera trigger : {len(triggered)}")
print(f"oversize       : {len(oversize)}")

if visits:
    durations = [v["duration"] for v in visits]
    print()
    print("Visit durations")
    print("----------------")
    print(f"minimum : {min(durations):.2f} s")
    print(f"maximum : {max(durations):.2f} s")
    print(f"mean    : {sum(durations)/len(durations):.2f} s")

print()
print("Camera trigger simulation")
print("-------------------------")
print(f"threshold : {CAMERA_MIN_PRESENT:.2f} s")
print(f"triggered : {len(triggered)}")

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
    peaks = [v["peak"] for v in visits]
    durations = [v["duration"] for v in visits]
    print(f"mean stay: {sum(durations)/len(durations):.1f} s")
    print(f"longest  : {max(durations):.1f} s")
    print(f"highest  : {max(peaks):.2f} g")

if oversize:
    print(f"oversize : {len(oversize)}")
    print(f"max size : {max(x['peak'] for x in oversize):.2f} g")