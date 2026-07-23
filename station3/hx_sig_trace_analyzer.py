#!/usr/bin/env python3
"""
hx_sig_trace_analyzer.py

Correlate SignalLogger signal.csv with trace.csv.

Analyzes BASELINE_RESET events:
    - offset change
    - idle weight error before reset
    - idle weight error after reset
"""

import sys
from datetime import datetime, timedelta

RESET_WINDOW = 10.0


if len(sys.argv) != 3:
    print("usage: hx_sig_trace_analyzer.py signal_xxx.csv trace_xxx.csv")
    sys.exit(1)


signal_file = sys.argv[1]
trace_file = sys.argv[2]


def read_signal(filename):

    meta = {}
    rows = []

    with open(filename) as f:

        while True:
            line = f.readline()

            if not line:
                break

            if line.startswith("#"):
                k, v = line[1:].strip().split("=", 1)
                try:
                    meta[k] = float(v)
                except ValueError:
                    meta[k] = v

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

            rows.append(r)

    return meta, rows


def read_trace(filename):

    rows = []

    with open(filename) as f:

        header = f.readline().strip().split(",")

        for line in f:

            x = line.strip().split(",")

            if len(x) != len(header):
                continue

            r = dict(zip(header, x))

            if r["reason"] == "BASELINE_RESET":
                r["dt"] = datetime.strptime(
                    r["time"],
                    "%Y-%m-%d %H:%M:%S"
                )

                r["offset"] = float(r["offset"])
                rows.append(r)

    return rows


meta, signal = read_signal(signal_file)
resets = read_trace(trace_file)


for r in signal:
    r["dt"] = datetime.strptime(
        r["time"],
        "%Y-%m-%d %H:%M:%S"
    )


def idle_window(t0, t1):

    values = [
        r["weight"]
        for r in signal
        if r["state"] == "IDLE"
        and t0 <= r["dt"] <= t1
    ]

    if not values:
        return None

    return {
        "max": max(abs(x) for x in values),
        "mean": sum(values) / len(values),
        "samples": len(values)
    }


print()
print("Configuration")
print("-------------")
print(f"weight threshold : {meta.get('weightThreshold',0):.2f} g")
print(f"threshold off    : {meta.get('threshold_off',0):.2f} g")
print(f"hxScale          : {meta.get('hxScale',0)}")

print()
print("Baseline reset correlation")
print("--------------------------")
print(
    f"{'time':19} "
    f"{'offset':8} "
    f"{'delta':8} "
    f"{'before max':11} "
    f"{'before avg':11} "
    f"{'after max':10} "
    f"{'after avg':10}"
)


if not resets:
    print("no BASELINE_RESET events")

else:

    last_offset = None
    for r in resets:

        before = idle_window(
            r["dt"] - timedelta(seconds=RESET_WINDOW),
            r["dt"]
        )

        after = idle_window(
            r["dt"],
            r["dt"] + timedelta(seconds=RESET_WINDOW)
        )

        if before:
            b = f"{before['max']:.2f}/{before['mean']:.2f}"
        else:
            b = "-"

        if after:
            a = f"{after['max']:.2f}/{after['mean']:.2f}"
        else:
            a = "-"


        if last_offset is None:
            delta = 0.0
        else:
            delta = r["offset"] - last_offset


        print(
            f"{r['time']} "
            f"{r['offset']:8.0f} "
            f"{delta:+8.0f} "
            f"{before['max'] if before else 0:11.2f} "
            f"{before['mean'] if before else 0:11.2f} "
            f"{after['max'] if after else 0:10.2f} "
            f"{after['mean'] if after else 0:10.2f}"
        )        
        last_offset = r["offset"]

print()
print("Summary")
print("-------")
print(f"resets analysed : {len(resets)}")