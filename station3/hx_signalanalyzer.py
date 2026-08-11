#!/usr/bin/env python3
"""
hx_signalanalyzer.py

Analyze SignalLogger output.

Reads metadata from SignalLogger header:
weightThreshold
threshold_off
weightlimit
hxScale
CAMERA_DELAY

FSM states:
IDLE ARRIVAL PRESENT OVERSIZE DEPARTURE
"""

from datetime import datetime, timedelta
import sys

import matplotlib.pyplot as plt


# Threshold for reporting offset jumps in grams.
JUMP_G = 3.0

# Minimum duration for an IDLE warning in seconds.
IDLE_BAD_TIME = 5.0


def read_signal_file(filename: str) -> tuple[dict, list[dict], list[str]]:
    meta = {}
    rows = []

    with open(filename) as f:
        while True:
            line = f.readline()
            if not line:
                break

            if line.startswith("#"):
                key, value = line[1:].strip().split("=", 1)
                try:
                    meta[key] = float(value)
                except ValueError:
                    meta[key] = value
            else:
                header = line.strip().split(",")
                break

        for line in f:
            values = line.strip().split(",")
            if len(values) != len(header):
                continue

            row = dict(zip(header, values))
            row["mono_t"] = float(row["mono_t"])
            row["weight"] = float(row["weight"])
            row["offset"] = float(row["offset"])
            rows.append(row)

    return meta, rows, header


def split_periods(rows: list[dict]) -> list[tuple[str, int, int]]:
    periods = []
    start = 0
    state = rows[0]["state"]

    for index, row in enumerate(rows[1:], 1):
        if row["state"] != state:
            periods.append((state, start, index - 1))
            start = index
            state = row["state"]

    periods.append((state, start, len(rows) - 1))
    return periods


def reconstruct_visits(
    rows: list[dict],
    periods: list[tuple[str, int, int]]
) -> tuple[list[dict], list[dict]]:
    visits = []
    oversize = []

    current = None
    over = None

    for state, start, end in periods:
        period = rows[start:end + 1]

        if state == "ARRIVAL":
            current = {
                "arrival": period[0]["time"],
                "arrival_i": start,
                "peak": max(row["weight"] for row in period)
            }

        elif state == "PRESENT":
            if current:
                current["present"] = period[0]["time"]
                current["present_i"] = start
                current["stay"] = (
                    period[-1]["mono_t"] - period[0]["mono_t"]
                )
                weights = [row["weight"] for row in period]
                current["mean"] = sum(weights) / len(weights)
                current["peak"] = max(
                    current["peak"],
                    max(weights)
                )

        elif state == "OVERSIZE":
            over = {
                "arrival": period[0]["time"],
                "duration": (
                    period[-1]["mono_t"] - period[0]["mono_t"]
                ),
                "peak": max(row["weight"] for row in period)
            }

        elif state == "DEPARTURE":
            if over:
                over["leave"] = period[0]["time"]
                oversize.append(over)
                over = None
            elif current:
                current["leave"] = period[0]["time"]

        elif state == "IDLE":
            if current:
                current["idle"] = period[0]["time"]

                if "stay" not in current:
                    current["stay"] = 0.0
                    current["mean"] = 0.0

                visits.append(current)
                current = None

    return visits, oversize


def print_configuration(meta: dict) -> None:
    weight_threshold = meta.get("weightThreshold", 0)
    threshold_off = meta.get(
        "threshold_off",
        weight_threshold * 0.7
    )
    hx_scale = meta.get("hxScale", 0)

    print()
    print("Configuration")
    print("-------------")
    print(f"weight threshold : {weight_threshold:.2f} g")
    print(f"threshold off    : {threshold_off:.2f} g")
    print(f"weight limit     : {meta.get('weightlimit', 0):.0f} g")
    print(f"hxScale          : {hx_scale}")
    print(
        f"startup offset   : "
        f"{meta.get('startup_offset', 0):.0f}"
    )
    print(f"startup note     : {meta.get('startup_note', '')}")
    print(
        f"CAMERA_DELAY     : "
        f"{meta.get('CAMERA_DELAY', 0):.2f} s"
    )


def print_baseline_statistics(
    rows: list[dict],
    meta: dict
) -> None:
    idle_offsets = [
        row["offset"]
        for row in rows
        if row["state"] == "IDLE"
    ]

    # These events explicitly change the baseline.
    baseline_resets = [
        row for row in rows
        if row["note"] in (
            "IDLE_BASELINE_TIMEOUT",
            "STATE_TIMEOUT"
        )
    ]

    print()
    print("Baseline statistics")
    print("-------------------")

    print(
        f"startup offset : "
        f"{meta.get('startup_offset', 0):.0f}"
    )

    if idle_offsets:
        print(f"minimum offset : {min(idle_offsets):.0f}")
        print(f"maximum offset : {max(idle_offsets):.0f}")
        print(
            f"offset range   : "
            f"{max(idle_offsets) - min(idle_offsets):.0f}"
        )
        print(
            f"idle mean      : "
            f"{sum(idle_offsets) / len(idle_offsets):.0f}"
        )
    else:
        print("no IDLE offset samples")

    print()
    print("Baseline maintenance")
    print("--------------------")

    if baseline_resets:
        print(f"baseline resets : {len(baseline_resets)}")

        last_offset = None

        for index, row in enumerate(baseline_resets, 1):
            offset = row["offset"]

            if last_offset is None:
                delta = 0.0
            else:
                delta = offset - last_offset

            print(
                f"  {index}. {row['time']} "
                f"offset={offset:.0f} "
                f"delta={delta:+.0f}"
            )

            last_offset = offset
    else:
        print("baseline resets : none")


def print_visits(visits: list[dict]) -> None:
    print()
    print("Bird visits")
    print("-----------")

    for index, visit in enumerate(visits, 1):
        print()
        print(f"Visit {index}")
        print(f"  arrival : {visit['arrival']}")
        print(f"  present : {visit.get('present')}")
        print(f"  leave   : {visit.get('leave')}")
        print(f"  idle    : {visit.get('idle')}")
        print(f"  stay    : {visit['stay']:.1f} s")
        print(f"  mean    : {visit['mean']:.2f} g")
        print(f"  peak    : {visit['peak']:.2f} g")


def print_oversize(oversize: list[dict]) -> None:
    print()
    print("Oversize events")
    print("----------------")

    if oversize:
        for index, event in enumerate(oversize, 1):
            print()
            print(f"Event {index}")
            print(f"  arrival : {event['arrival']}")
            print(f"  leave   : {event.get('leave')}")
            print(f"  peak    : {event['peak']:.2f} g")
    else:
        print("none")


def print_visit_statistics(
    visits: list[dict],
    oversize: list[dict],
    camera_delay: float
) -> None:
    triggered = [
        visit for visit in visits
        if visit["stay"] >= camera_delay
    ]

    print()
    print("Visit statistics")
    print("----------------")
    print(f"visits         : {len(visits)}")
    print(f"camera trigger : {len(triggered)}")
    print(f"oversize       : {len(oversize)}")

    if visits:
        durations = [visit["stay"] for visit in visits]

        print()
        print("Visit durations")
        print("----------------")
        print(f"minimum : {min(durations):.2f} s")
        print(f"maximum : {max(durations):.2f} s")
        print(f"mean    : {sum(durations) / len(durations):.2f} s")

    print()
    print("Camera trigger simulation")
    print("-------------------------")
    print(f"threshold : {camera_delay:.2f} s")
    print(f"triggered : {len(triggered)}")


def print_idle_statistics(rows: list[dict]) -> None:
    idle = [
        row["weight"]
        for row in rows
        if row["state"] == "IDLE"
    ]

    if idle:
        print()
        print("Idle statistics")
        print("----------------")
        print(f"mean weight   : {sum(idle) / len(idle):.2f} g")
        print(f"minimum       : {min(idle):.2f} g")
        print(f"maximum       : {max(idle):.2f} g")
        print(f"peak-to-peak   : {max(idle) - min(idle):.2f} g")


def find_idle_warnings(
    rows: list[dict],
    threshold_off: float
) -> list[tuple[dict, float, float]]:
    idle_warnings = []

    bad_start = None
    bad_max = 0.0

    for row in rows:
        outside = (
            row["state"] == "IDLE"
            and abs(row["weight"]) > threshold_off
        )

        if outside:
            if bad_start is None:
                bad_start = row
                bad_max = abs(row["weight"])
            else:
                bad_max = max(
                    bad_max,
                    abs(row["weight"])
                )

        elif bad_start is not None:
            duration = row["mono_t"] - bad_start["mono_t"]

            if duration >= IDLE_BAD_TIME:
                idle_warnings.append(
                    (bad_start, duration, bad_max)
                )

            bad_start = None
            bad_max = 0.0

    if bad_start is not None:
        duration = rows[-1]["mono_t"] - bad_start["mono_t"]

        if duration >= IDLE_BAD_TIME:
            idle_warnings.append(
                (bad_start, duration, bad_max)
            )

    return idle_warnings


def print_warnings(
    idle_warnings: list[tuple[dict, float, float]],
    oversize: list[dict]
) -> None:
    print()
    print("Warnings")
    print("--------")

    found = False

    for row, duration, maximum in idle_warnings:
        print(
            f"IDLE outside threshold_off "
            f"started at {row['time']} "
            f"duration={duration:.1f}s "
            f"max={maximum:.2f} g."
        )
        found = True

    if oversize:
        print(f"Oversize events detected: {len(oversize)}")
        found = True

    if not found:
        print("none")


def print_offset_discontinuities(
    rows: list[dict],
    hx_scale: float
) -> None:
    print()
    print(
        f"Offset discontinuities "
        f"(threshold: {JUMP_G} g)"
    )
    print("--------------------")

    last = rows[0]["offset"]

    for row in rows[1:]:
        offset = row["offset"]
        delta_g = (last - offset) / abs(hx_scale)

        if abs(delta_g) > JUMP_G:
            print(
                f"{row['time']} "
                f"jump={delta_g:+.2f} g "
                f"state={row['state']}"
            )

        last = offset


def print_summary(
    visits: list[dict],
    oversize: list[dict]
) -> None:
    print()
    print("Summary")
    print("-------")
    print(f"visits   : {len(visits)}")

    if visits:
        print(
            f"mean stay: "
            f"{sum(v['stay'] for v in visits) / len(visits):.1f} s"
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


def create_plot(
    rows: list[dict],
    periods: list[tuple[str, int, int]],
    weight_threshold: float,
    threshold_off: float,
    startup_offset: float,
    hx_scale: float,
    weightlimit: float
) -> None:
    times = [
        datetime.strptime(
            row["time"],
            "%Y-%m-%d %H:%M:%S"
        )
        for row in rows
    ]

    weights = [row["weight"] for row in rows]

    offset_g = [
        (startup_offset - row["offset"]) / abs(hx_scale)
        for row in rows
    ]

    fig, ax = plt.subplots(figsize=(11, 4))

    ax.plot(
        times,
        weights,
        label="weight",
        linewidth=1
    )
    ax.plot(
        times,
        offset_g,
        label="offset drift (g)",
        linewidth=1
    )

    ax.axhline(
        weight_threshold,
        color="r",
        linestyle="--",
        alpha=0.7
    )
    ax.axhline(
        threshold_off,
        color="g",
        linestyle="--",
        alpha=0.7
    )

    for state, start, end in periods:
        if state != "IDLE":
            ax.axvspan(
                times[start],
                times[end],
                alpha=0.08
            )

    for index in range(1, len(rows)):
        delta_g = (
            rows[index - 1]["offset"] - rows[index]["offset"]
        ) / abs(hx_scale)

        if abs(delta_g) > JUMP_G:
            ax.axvline(
                times[index],
                linestyle=":",
                alpha=0.8
            )

    # Show at least one hour on the time axis.
    plot_end = max(
        times[-1],
        times[0] + timedelta(hours=1)
    )

    ax.set_xlim(times[0], plot_end)
    ax.set_ylim(top=weightlimit)
    ax.xaxis.set_major_formatter(
        plt.matplotlib.dates.DateFormatter("%H:%M")
    )

    ax.set_xlabel("time")
    ax.set_ylabel("grams")
    ax.legend(loc="upper left")
    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig("signal_timeline.svg")
    print("timeline plot written to signal_timeline.svg")


def main() -> None:
    if len(sys.argv) != 2:
        print("usage: hx_signalanalyzer.py signal_xxx.csv")
        sys.exit(1)

    meta, rows, _ = read_signal_file(sys.argv[1])

    if not rows:
        print("no samples found")
        sys.exit(1)

    weight_threshold = meta.get("weightThreshold", 0)
    threshold_off = meta.get(
        "threshold_off",
        weight_threshold * 0.7
    )
    weightlimit = meta.get("weightlimit", 0)
    hx_scale = meta.get("hxScale", 0)
    camera_delay = meta.get("CAMERA_DELAY", 0)

    print()
    print(f"samples : {len(rows)}")
    print(f"first   : {rows[0]['time']}")
    print(f"last    : {rows[-1]['time']}")

    print_configuration(meta)

    periods = split_periods(rows)
    visits, oversize = reconstruct_visits(rows, periods)

    print_baseline_statistics(rows, meta)
    print_visits(visits)
    print_oversize(oversize)
    print_visit_statistics(
        visits,
        oversize,
        camera_delay
    )
    print_idle_statistics(rows)

    idle_warnings = find_idle_warnings(
        rows,
        threshold_off
    )
    print_warnings(idle_warnings, oversize)

    print_offset_discontinuities(
        rows,
        hx_scale
    )

    print_summary(visits, oversize)

    create_plot(
        rows,
        periods,
        weight_threshold,
        threshold_off,
        meta.get("startup_offset", 0),
        hx_scale,
        weightlimit
    )


if __name__ == "__main__":
    main()