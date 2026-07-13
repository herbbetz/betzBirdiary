#!/usr/bin/env python3
"""
signal_analyzer.py

Analyze SignalLogger output.
"""

from datetime import datetime
import sys


if len(sys.argv) != 2:
    print("usage: signal_analyzer.py signal_xxx.csv")
    sys.exit(1)


# --------------------------------------------------------
# read csv
# --------------------------------------------------------

rows = []

with open(sys.argv[1]) as f:

    header = f.readline()

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
            "event": event,
            "peak": float(peak),
            "note": note
        })


print()

print(f"samples : {len(rows)}")
print(f"first   : {rows[0]['time']}")
print(f"last    : {rows[-1]['time']}")

print()

# --------------------------------------------------------
# group into periods
# --------------------------------------------------------

periods = []

start = 0
state = rows[0]["state"]

for i in range(1, len(rows)):

    if rows[i]["state"] != state:

        periods.append(
            (state, start, i - 1)
        )

        start = i
        state = rows[i]["state"]

periods.append(
    (state, start, len(rows) - 1)
)

# --------------------------------------------------------
# print periods
# --------------------------------------------------------

print("State periods")
print("-------------")

for state, first, last in periods:

    segment = rows[first:last + 1]

    weights = [
        r["weight"]
        for r in segment
    ]

    mean = (
        sum(weights)
        / len(weights)
    )

    minimum = min(weights)
    maximum = max(weights)

    peak = max(
        r["peak"]
        for r in segment
    )

    duration = (
        segment[-1]["mono"]
        - segment[0]["mono"]
    )

    print()

    print(
        f"{state}"
    )

    print(
        f"  start    : {segment[0]['time']}"
    )

    print(
        f"  end      : {segment[-1]['time']}"
    )

    print(
        f"  duration : {duration:.1f} s"
    )

    print(
        f"  samples  : {len(segment)}"
    )

    print(
        f"  mean     : {mean:7.2f} g"
    )

    print(
        f"  min/max  : "
        f"{minimum:7.2f} / {maximum:7.2f} g"
    )

    if peak > 0:

        print(
            f"  peak     : {peak:.2f} g"
        )

    events = [
        r["event"]
        for r in segment
        if r["event"]
    ]

    if events:

        print(
            f"  events   : "
            + ", ".join(events)
        )