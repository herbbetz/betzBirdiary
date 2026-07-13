"""
signal_analyzer.py

Analyze signalLogger CSV output.

Only physical quantities:
    raw
    offset
    weight

No signal processing.
"""

import csv
import sys
from collections import defaultdict


def read_csv(filename):

    with open(filename) as f:
        return list(csv.DictReader(f))


def state_summary(rows):

    data = defaultdict(list)

    for r in rows:
        data[r["state"]].append(
            float(r["weight"])
        )

    print("\nWeight by state")

    for state, values in data.items():

        print(
            f"{state:10s} "
            f"n={len(values):5d} "
            f"mean={sum(values)/len(values):7.2f} g "
            f"min={min(values):7.2f} g "
            f"max={max(values):7.2f} g"
        )


def transitions(rows):

    print("\nState changes")

    old = None

    for r in rows:

        state = r["state"]

        if state != old:

            print(
                r["time"],
                old,
                "->",
                state,
                f"weight={float(r['weight']):.2f}"
            )

            old = state


def check_arrival_weight(rows):

    print("\nARRIVAL with negative weight")

    for r in rows:

        if (
            r["state"] == "ARRIVAL"
            and float(r["weight"]) < 0
        ):
            print(
                r["time"],
                r["weight"]
            )


def check_idle_zero(rows, limit=5):

    print(
        f"\nIDLE outside +/-{limit} g"
    )

    for r in rows:

        if (
            r["state"] == "IDLE"
            and abs(float(r["weight"])) > limit
        ):
            print(
                r["time"],
                r["weight"]
            )


def main():

    filename = sys.argv[1]

    rows = read_csv(filename)

    print(
        f"samples: {len(rows)}"
    )

    print(
        "first:",
        rows[0]["time"]
    )

    print(
        "last :",
        rows[-1]["time"]
    )

    state_summary(rows)
    transitions(rows)
    check_arrival_weight(rows)
    check_idle_zero(rows)


if __name__ == "__main__":
    main()