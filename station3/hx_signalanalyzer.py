#!/usr/bin/env python3
"""
hx_signalanalyzer.py

Analyze SignalLogger output.

Reads metadata from SignalLogger header:
    weightThreshold
    threshold_off
    hxScale

FSM states:
    IDLE ARRIVAL PRESENT OVERSIZE DEPARTURE
"""

import sys

if len(sys.argv) != 2:
    print("usage: hx_signalanalyzer.py signal_xxx.csv")
    sys.exit(1)

meta = {}
rows = []

with open(sys.argv[1]) as f:
    while True:
        line = f.readline()
        if not line:
            break
        if line.startswith("#"):
            k, v = line[1:].strip().split("=")
            meta[k] = float(v)
        else:
            header = line.strip().split(",")
            break

    for line in f:
        x = line.strip().split(",")
        if len(x) != len(header):
            continue

        r = dict(zip(header, x))
        r["mono_t"] = float(r["mono_t"])
        r["weight"] = float(r["weight"])
        r["peak"] = float(r["peak"])
        rows.append(r)

weightThreshold = meta.get("weightThreshold", 0)
threshold_off = meta.get("threshold_off", weightThreshold * 0.7)
hxScale = meta.get("hxScale", 0)

CAMERA_MIN_PRESENT = 1.0

print()
print(f"samples : {len(rows)}")
print(f"first   : {rows[0]['time']}")
print(f"last    : {rows[-1]['time']}")

print()
print("Configuration")
print("-------------")
print(f"weight threshold : {weightThreshold:.2f} g")
print(f"threshold off    : {threshold_off:.2f} g")
print(f"hxScale          : {hxScale}")
print(f"startup offset   : {meta.get('startup_offset',0):.1f}")
print(f"startup note     : {meta.get('startup_note','')}")

# ------------------------------------------------------------
# split continuous FSM periods
# ------------------------------------------------------------

periods = []
start = 0
state = rows[0]["state"]

for i,r in enumerate(rows[1:],1):
    if r["state"] != state:
        periods.append((state,start,i-1))
        start = i
        state = r["state"]

periods.append((state,start,len(rows)-1))

# ------------------------------------------------------------
# reconstruct visits from transitions
# ------------------------------------------------------------

visits = []
oversize = []

current = None
over = None

for state,a,b in periods:
    r = rows[a:b+1]

    if state == "ARRIVAL":
        current = {
            "arrival": r[0]["time"],
            "arrival_i": a,
            "peak": max(x["weight"] for x in r)
        }

    elif state == "PRESENT":
        if current:
            current["present"] = r[0]["time"]
            current["present_i"] = a
            current["stay"] = r[-1]["mono_t"] - r[0]["mono_t"]
            w = [x["weight"] for x in r]
            current["mean"] = sum(w)/len(w)
            current["peak"] = max(current["peak"],max(w))

    elif state == "OVERSIZE":
        over = {
            "arrival": r[0]["time"],
            "duration": r[-1]["mono_t"]-r[0]["mono_t"],
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

            if "stay" not in current:
                current["stay"] = 0.0
                current["mean"] = 0.0

            visits.append(current)
            current = None

# ------------------------------------------------------------
# baseline
# ------------------------------------------------------------
idle_offsets = [
    float(r["offset"])
    for r in rows
    if r["state"] == "IDLE"
]

if idle_offsets:
    print()
    print("Baseline statistics")
    print("-------------------")
    print(
        f"idle offset change : "
        f"{max(idle_offsets)-min(idle_offsets):.1f}"
    )
# ------------------------------------------------------------
# visits
# ------------------------------------------------------------

print()
print("Bird visits")
print("-----------")

for i,v in enumerate(visits,1):
    print()
    print(f"Visit {i}")
    print(f"  arrival : {v['arrival']}")
    print(f"  present : {v.get('present')}")
    print(f"  leave   : {v.get('leave')}")
    print(f"  idle    : {v.get('idle')}")
    print(f"  stay    : {v['stay']:.1f} s")
    print(f"  mean    : {v['mean']:.2f} g")
    print(f"  peak    : {v['peak']:.2f} g")

# ------------------------------------------------------------
# oversize
# ------------------------------------------------------------

print()
print("Oversize events")
print("----------------")

if oversize:
    for i,v in enumerate(oversize,1):
        print()
        print(f"Event {i}")
        print(f"  arrival : {v['arrival']}")
        print(f"  leave   : {v.get('leave')}")
        print(f"  peak    : {v['peak']:.2f} g")
else:
    print("none")

# ------------------------------------------------------------
# statistics
# ------------------------------------------------------------

triggered = [
    v for v in visits
    if v["stay"] >= CAMERA_MIN_PRESENT
]

print()
print("Visit statistics")
print("----------------")
print(f"visits         : {len(visits)}")
print(f"camera trigger : {len(triggered)}")
print(f"oversize       : {len(oversize)}")

if visits:
    d = [v["stay"] for v in visits]
    print()
    print("Visit durations")
    print("----------------")
    print(f"minimum : {min(d):.2f} s")
    print(f"maximum : {max(d):.2f} s")
    print(f"mean    : {sum(d)/len(d):.2f} s")

print()
print("Camera trigger simulation")
print("-------------------------")
print(f"threshold : {CAMERA_MIN_PRESENT:.2f} s")
print(f"triggered : {len(triggered)}")

# ------------------------------------------------------------
# idle
# ------------------------------------------------------------

idle = [
    r["weight"] for r in rows
    if r["state"] == "IDLE"
]

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
    if (
        r["state"] == "IDLE"
        and abs(r["weight"]) > threshold_off
    ):
        print(
            f"IDLE outside threshold_off "
            f"({threshold_off:.2f} g) "
            f"at {r['time']} "
            f"({r['weight']:.2f} g)"
        )
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
    print(
        f"mean stay: "
        f"{sum(v['stay'] for v in visits)/len(visits):.1f} s"
    )
    print(
        f"longest  : "
        f"{max(v['stay'] for v in visits):.1f} s"
    )
    print(
        f"highest  : "
        f"{max(v['peak'] for v in visits):.2f} g"
    )

if oversize:
    print(f"oversize : {len(oversize)}")