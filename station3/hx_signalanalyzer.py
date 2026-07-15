#!/usr/bin/env python3

"""
hx_signalanalyzer.py

Analyze SignalLogger output.

todo: maybe add more compact timeline
"""

import sys


CAMERA_MIN_PRESENT = 1.0   # seconds, for contact classification

# --------------------------------------------------------
# read csv
# --------------------------------------------------------

if len(sys.argv) != 2:
    print("usage: hx_signalanalyzer.py signal_xxx.csv")
    sys.exit(1)

rows = []

with open(sys.argv[1]) as f:

    f.readline()

    for line in f:

        (
            t,
            mono,
            raw,
            offset,
            weight,
            state,
            event,
            peak,
            note
        ) = line.strip().split(",")

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
print()

# --------------------------------------------------------
# split into state periods
# --------------------------------------------------------

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

# --------------------------------------------------------
# build visits
# --------------------------------------------------------

visits = []

current = None

for p in periods:

    state = p["state"]
    r = p["rows"]

    if state == "ARRIVAL":

        current = {
            "arrival": r[0]["time"],
            "arrival_weight": r[0]["weight"]
        }

    elif state == "PRESENT" and current is not None:

        current["present"] = r[0]["time"]
        current["duration"] = (
            r[-1]["mono"] - r[0]["mono"]
        )

        weights = [
            x["weight"]
            for x in r
        ]

        current["mean"] = (
            sum(weights) / len(weights)
        )

        current["peak"] = max(weights)

    elif state == "DEPARTURE" and current is not None:

        current["departure"] = r[0]["time"]

    elif state == "IDLE" and current is not None:

        current["idle"] = r[0]["time"]

        visits.append(current)

        current = None

# --------------------------------------------------------
# print visits
# --------------------------------------------------------

print("Bird visits")
print("-----------")

for i, v in enumerate(visits, 1):

    print()

    print(f"Visit {i}")

    print(f"  arrival : {v.get('arrival')}")
    print(f"  present : {v.get('present')}")
    print(f"  leave   : {v.get('departure')}")
    print(f"  idle    : {v.get('idle')}")

    if "duration" in v:
        print(f"  stay    : {v['duration']:.1f} s")

    if "mean" in v:
        print(f"  mean    : {v['mean']:.2f} g")

    if "peak" in v:
        print(f"  peak    : {v['peak']:.2f} g")

# --------------------------------------------------------
# state timeline
# --------------------------------------------------------
print()
print("State periods")
print("-------------")

for i, p in enumerate(periods, 1):

    r = p["rows"]

    print(
        f"{i:3d} "
        f"{p['state']:10s} "
        f"{r[0]['time']} -> "
        f"{r[-1]['time']} "
        f"({p['duration']:.2f} s)"
    )

# --------------------------------------------------------
# contact classification
# --------------------------------------------------------

print()
print("Contact statistics")
print("-------------------")

contacts = []

current_contact = None

for p in periods:

    if p["state"] == "ARRIVAL":

        current_contact = {
            "arrival": p["rows"][0]["time"],
            "arrival_duration": p["duration"],
            "present_duration": 0.0,
            "has_present": False
        }

    elif p["state"] == "PRESENT" and current_contact is not None:

        current_contact["has_present"] = True
        current_contact["present_duration"] = p["duration"]

    elif p["state"] == "IDLE" and current_contact is not None:

        contacts.append(current_contact)
        current_contact = None


# --------------------------------------------------------
# classify contacts
# --------------------------------------------------------
short = [
    c for c in contacts
    if not c["has_present"]
]

brief = [
    c for c in contacts
    if c["has_present"]
    and c["present_duration"] < CAMERA_MIN_PRESENT
]

valid = [
    c for c in contacts
    if c["has_present"]
    and c["present_duration"] >= CAMERA_MIN_PRESENT
]


print(f"total contacts : {len(contacts)}")
print(f"valid visits   : {len(valid)}")
print(f"brief visits   : {len(brief)}")
print(f"short contacts : {len(short)}")


# --------------------------------------------------------
# valid visit statistics
# --------------------------------------------------------

if valid:

    durations = [
        c["present_duration"]
        for c in valid
    ]

    print()
    print("Valid PRESENT durations")
    print("-----------------------")

    print(
        f"minimum : {min(durations):.2f} s"
    )

    print(
        f"maximum : {max(durations):.2f} s"
    )

    print(
        f"mean    : {sum(durations)/len(durations):.2f} s"
    )


# --------------------------------------------------------
# brief visits
# --------------------------------------------------------

if brief:

    print()
    print("Brief visits")
    print("------------")

    for i, c in enumerate(brief, 1):

        print(
            f"{i:2d}: "
            f"{c['arrival']} "
            f"(PRESENT {c['present_duration']:.2f} s)"
        )


# --------------------------------------------------------
# short contacts
# --------------------------------------------------------

if short:

    print()
    print("Short contacts")
    print("--------------")

    for i, c in enumerate(short, 1):

        print(
            f"{i:2d}: "
            f"{c['arrival']} "
            f"(ARRIVAL {c['arrival_duration']:.2f} s)"
        )


# --------------------------------------------------------
# camera trigger simulation
# --------------------------------------------------------

print()
print("Camera trigger simulation")
print("-------------------------")

print(
    f"threshold     : {CAMERA_MIN_PRESENT:.2f} s"
)

print(
    f"would trigger : {len(valid)}"
)
# --------------------------------------------------------
# idle statistics
# --------------------------------------------------------

idle = [
    r
    for r in rows
    if r["state"] == "IDLE"
]

if idle:

    weights = [
        r["weight"]
        for r in idle
    ]

    print()
    print("Idle statistics")
    print("----------------")

    print(
        f"mean weight : {sum(weights)/len(weights):.2f} g"
    )

    print(
        f"minimum     : {min(weights):.2f} g"
    )

    print(
        f"maximum     : {max(weights):.2f} g"
    )

# --------------------------------------------------------
# suspicious situations
# --------------------------------------------------------

print()
print("Warnings")
print("--------")

found = False

for p in periods:

    if p["state"] == "ARRIVAL":

        w = p["rows"][0]["weight"]

        if w < 0:

            print(
                f"negative ARRIVAL at {p['rows'][0]['time']}"
            )

            found = True

for r in idle:

    if abs(r["weight"]) > 5:

        print(
            f"IDLE outside ±5 g at {r['time']} "
            f"({r['weight']:.2f} g)"
        )

        found = True
        break

if not found:

    print("none")

# --------------------------------------------------------
# summary
# --------------------------------------------------------

print()
print("Summary")
print("-------")

print(f"visits : {len(visits)}")

if visits:

    peaks = [
        v["peak"]
        for v in visits
        if "peak" in v
    ]

    stays = [
        v["duration"]
        for v in visits
        if "duration" in v
    ]

    print(
        f"mean stay : "
        f"{sum(stays)/len(stays):.1f} s"
    )

    print(
        f"longest   : "
        f"{max(stays):.1f} s"
    )

    print(
        f"highest   : "
        f"{max(peaks):.2f} g"
    )