#!/usr/bin/env python3
"""
hxanalyze4srv.py

Analyze SignalLogger output for the Flask /hxreport endpoint.

This module is independent of hx_signalanalyzer.py.
"""

from datetime import datetime, timedelta
import os

import matplotlib.pyplot as plt


# Threshold for reporting offset jumps in grams.
JUMP_G = 3.0

# Minimum duration for an IDLE warning in seconds.
IDLE_BAD_TIME = 5.0

def read_signal_file(filename: str) -> tuple[dict, list[dict], list[str]]:
    meta = {}
    rows = []

    with open(filename, encoding="utf-8") as file:
        while True:
            line = file.readline()
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
        else:
            return meta, rows, []

        for line in file:
            values = line.strip().split(",")
            if len(values) != len(header):
                continue
            row = dict(zip(header, values))
            row["mono_t"] = float(row["mono_t"])
            row["raw"] = float(row["raw"])
            row["offset"] = float(row["offset"])
            row["weight"] = float(row["weight"])
            row["sigma"] = float(row["sigma"])
            row["threshold"] = float(row["threshold"])
            rows.append(row)

    return meta, rows, header

def split_periods(
    rows: list[dict]
) -> list[tuple[str, int, int]]:
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
                "peak": max(
                    row["weight"]
                    for row in period
                )
            }

        elif state == "PRESENT":
            if current:
                current["present"] = period[0]["time"]
                current["present_i"] = start
                current["stay"] = (
                    period[-1]["mono_t"]
                    - period[0]["mono_t"]
                )

                weights = [
                    row["weight"]
                    for row in period
                ]

                current["mean"] = (
                    sum(weights) / len(weights)
                )
                current["peak"] = max(
                    current["peak"],
                    max(weights)
                )

        elif state == "OVERSIZE":
            over = {
                "arrival": period[0]["time"],
                "duration": (
                    period[-1]["mono_t"]
                    - period[0]["mono_t"]
                ),
                "peak": max(
                    row["weight"]
                    for row in period
                )
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

def get_configuration(meta: dict) -> dict:
    weight_threshold = meta.get("weightThreshold", 0)

    return {
        "weight_threshold": weight_threshold,
        "threshold_off": weight_threshold * 0.7,
        "weightlimit": meta.get("weightlimit", 0),
        "hxScale": meta.get("hxScale", 0),
        "startup_offset": meta.get("startup_offset", 0),
        "startup_note": meta.get("startup_note", ""),
        "CAMERA_DELAY": meta.get("CAMERA_DELAY", 0)
    }

def row_has_event(row: dict, event: str) -> bool:
    return event in row["events"].split("|")


def get_baseline_statistics(rows: list[dict], meta: dict) -> dict:
    idle_offsets = [
        row["offset"] for row in rows
        if row["state"] == "IDLE"
    ]
    baseline_resets = [
        row for row in rows
        if row_has_event(row, "BASELINE_RESET")
    ]

    result = {
        "startup_offset": meta.get("startup_offset", 0),
        "baseline_resets": []
    }

    if idle_offsets:
        result["minimum_offset"] = min(idle_offsets)
        result["maximum_offset"] = max(idle_offsets)
        result["offset_range"] = max(idle_offsets) - min(idle_offsets)
        result["idle_mean"] = sum(idle_offsets) / len(idle_offsets)
    else:
        result["no_idle_offset_samples"] = True

    last_offset = None
    for index, row in enumerate(baseline_resets, 1):
        offset = row["offset"]
        delta = 0.0 if last_offset is None else offset - last_offset
        result["baseline_resets"].append({
            "index": index,
            "time": row["time"],
            "offset": offset,
            "delta": delta
        })
        last_offset = offset

    return result

def get_oversize(oversize: list[dict]) -> list[dict]:
    return [
        {
            "arrival": event["arrival"],
            "leave": event.get("leave"),
            "duration": event["duration"],
            "peak": event["peak"]
        }
        for event in oversize
    ]

def get_visit_statistics(
    visits: list[dict],
    oversize: list[dict],
    rows: list[dict],
    camera_delay: float
) -> dict:
    camera_triggers = sum(
        1 for row in rows
        if row_has_event(row, "CAMERA_TRIGGER")
    )
    departures = sum(
        1 for row in rows
        if row_has_event(row, "DEPARTURE_TRIGGER")
    )

    result = {
        "visits": len(visits),
        "camera_trigger": camera_triggers,
        "departures": departures,
        "oversize": len(oversize),
        "camera_trigger_threshold": camera_delay,
        "triggered": camera_triggers
    }

    if visits:
        durations = [visit["stay"] for visit in visits]
        result["visit_durations"] = {
            "minimum": min(durations),
            "maximum": max(durations),
            "mean": sum(durations) / len(durations)
        }

    return result

def get_idle_statistics(rows: list[dict]) -> dict | None:
    idle = [
        row["weight"]
        for row in rows
        if row["state"] == "IDLE"
    ]

    if not idle:
        return None

    return {
        "mean_weight": sum(idle) / len(idle),
        "minimum": min(idle),
        "maximum": max(idle),
        "peak_to_peak": max(idle) - min(idle)
    }


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
            duration = (
                row["mono_t"]
                - bad_start["mono_t"]
            )

            if duration >= IDLE_BAD_TIME:
                idle_warnings.append(
                    (bad_start, duration, bad_max)
                )

            bad_start = None
            bad_max = 0.0

    if bad_start is not None:
        duration = (
            rows[-1]["mono_t"]
            - bad_start["mono_t"]
        )

        if duration >= IDLE_BAD_TIME:
            idle_warnings.append(
                (bad_start, duration, bad_max)
            )

    return idle_warnings


def get_warnings(
    idle_warnings: list[tuple[dict, float, float]],
    oversize: list[dict]
) -> dict:
    warnings = []

    for row, duration, maximum in idle_warnings:
        warnings.append({
            "type": "IDLE outside threshold_off",
            "time": row["time"],
            "duration": duration,
            "maximum": maximum
        })

    if oversize:
        warnings.append({
            "type": "Oversize events detected",
            "count": len(oversize)
        })

    return {
        "found": bool(warnings),
        "items": warnings
    }


def get_offset_discontinuities(
    rows: list[dict],
    hx_scale: float
) -> list[dict]:
    discontinuities = []

    if not rows or hx_scale == 0:
        return discontinuities

    last = rows[0]["offset"]

    for row in rows[1:]:
        offset = row["offset"]
        delta_g = (
            (last - offset)
            / abs(hx_scale)
        )

        if abs(delta_g) > JUMP_G:
            discontinuities.append({
                "time": row["time"],
                "jump": delta_g,
                "state": row["state"]
            })

        last = offset

    return discontinuities


def get_summary(
    visits: list[dict],
    oversize: list[dict]
) -> dict:
    result = {
        "visits": len(visits)
    }

    if visits:
        result["mean_stay"] = (
            sum(
                visit["stay"]
                for visit in visits
            ) / len(visits)
        )
        result["longest"] = max(
            visit["stay"]
            for visit in visits
        )
        result["highest"] = max(
            visit["peak"]
            for visit in visits
        )

    if oversize:
        result["oversize"] = len(oversize)

    return result

def create_plot(
    rows: list[dict],
    periods: list[tuple[str, int, int]],
    weight_threshold: float,
    startup_offset: float,
    hx_scale: float,
    weightlimit: float,
    output_path: str
) -> None:
    times = [
        datetime.strptime(row["time"], "%Y-%m-%d %H:%M:%S")
        for row in rows
    ]
    weights = [row["weight"] for row in rows]
    thresholds = [row["threshold"] for row in rows]
    sigmas = [row["sigma"] for row in rows]

    offset_g = [
        (startup_offset - row["offset"]) / abs(hx_scale)
        if hx_scale != 0 else 0.0
        for row in rows
    ]

    threshold_off = weight_threshold * 0.7

    fig, ax = plt.subplots(figsize=(11, 4))

    ax.plot(times, weights, label="weight", linewidth=1)
    ax.plot(times, offset_g, label="offset drift (g)", linewidth=1)
    ax.plot(times, thresholds, label="threshold", linewidth=1)
    ax.plot(times, sigmas, label="sigma", linewidth=1)

    ax.axhline(weight_threshold, linestyle="--", alpha=0.7)
    ax.axhline(threshold_off, linestyle="--", alpha=0.7)

    for state, start, end in periods:
        if state != "IDLE":
            ax.axvspan(times[start], times[end], alpha=0.08)

    if hx_scale != 0:
        for index in range(1, len(rows)):
            delta_g = (
                rows[index - 1]["offset"] - rows[index]["offset"]
            ) / abs(hx_scale)

            if abs(delta_g) > JUMP_G:
                ax.axvline(times[index], linestyle=":", alpha=0.8)

    plot_end = max(times[-1], times[0] + timedelta(hours=1))
    ax.set_xlim(times[0], plot_end)
    ax.xaxis.set_major_formatter(
        plt.matplotlib.dates.DateFormatter("%H:%M")
    )
    ax.set_xlabel("time")
    ax.set_ylabel("grams")
    ax.legend(loc="upper left")
    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig(output_path)
    plt.close(fig)


def analyze_csv(filename: str) -> dict:
    if not os.path.isfile(filename):
        return {"signal_csv": False}

    meta, rows, _ = read_signal_file(filename)

    if not rows:
        return {"signal_csv": True, "samples": 0}

    weight_threshold = meta.get("weightThreshold", 0)
    weightlimit = meta.get("weightlimit", 0)
    hx_scale = meta.get("hxScale", 0)
    camera_delay = meta.get("CAMERA_DELAY", 0)
    startup_offset = meta.get("startup_offset", 0)

    periods = split_periods(rows)
    visits, oversize = reconstruct_visits(rows, periods)

    idle_warnings = find_idle_warnings(
        rows,
        weight_threshold * 0.7
    )

    output_path = os.path.join(
        os.path.dirname(filename),
        "signal_timeline.svg"
    )

    create_plot(
        rows,
        periods,
        weight_threshold,
        startup_offset,
        hx_scale,
        weightlimit,
        output_path
    )

    return {
        "signal_csv": True,
        "samples": len(rows),
        "first": rows[0]["time"],
        "last": rows[-1]["time"],
        "configuration": get_configuration(meta),
        "baseline_statistics": get_baseline_statistics(rows, meta),
        "oversize_events": get_oversize(oversize),
        "visit_statistics": get_visit_statistics(
            visits, oversize, rows, camera_delay
        ),
        "idle_statistics": get_idle_statistics(rows),
        "warnings": get_warnings(idle_warnings, oversize),
        "offset_discontinuities": get_offset_discontinuities(
            rows, hx_scale
        ),
        "summary": get_summary(visits, oversize),
        "timeline": "/ramdisk/signal_timeline.svg"
    }