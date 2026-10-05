#!/usr/bin/env python3
"""
hxanalyze4srv.py
Analyze SignalLogger output for the Flask /hxreport endpoint.
This module is independent of hx_signalanalyzer.py.
Definitions:
hx triggers       : all CAMERA_TRIGGER events in signal_hx.csv
completed visits  : visits containing CAMERA_TRIGGER and DEPARTURE_TRIGGER in signal_hx.csv (cancelled arrivals are not counted)
FIFO events       : all cam_FIFO entries in cam_event.csv
matched FIFO      : cam_FIFO within 0..2 s after a CAMERA_TRIGGER (compared signal_hx.csv to cam_event.csv)
unrelated FIFO    : cam_FIFO without such a trigger (e.g. sent by flaskBird as manual snapshot order to mainFoBird3.py)
followed by recording : cam_SND_MV_ok entries from cam_event.csv
all cam_SND_MV_* entries except _ok: remaining sends (noack, upfail, uplimit, keeplocal) from cam_event.csv
blocked by CLR_Q: cam_CLR_Q (queued trigger dropped after a recording, never a FIFO)
blocked by STDBY: cam_STDBY (logged after its FIFO) entries (hx triggers and flaskBird triggers)
Identities: all triggers = FIFO + CLR_Q; FIFO = SND_MV_* + STDBY
"""
from datetime import datetime, timedelta
import os
import matplotlib.pyplot as plt
JUMP_G = 3.0
IDLE_BAD_TIME = 5.0
CAMERA_MATCH_SECONDS = 2.0
THRESHOLD_OFF_FACTOR = 0.7
def get_threshold_off(weight_threshold: float) -> float:
    """The one place where threshold_off is defined."""
    return weight_threshold * THRESHOLD_OFF_FACTOR

def reconstruct_datetimes(rows:list[dict])->None:
    """Assign a full datetime to each row from its %H:%M:%S time string.

    When the clock rolls past midnight (current < previous), increment the day
    so the X-axis stays continuous and flows to the right.
    """
    if not rows:
        return
    base_date=datetime(2026,1,1)
    current_date=base_date
    prev_time=None
    for row in rows:
        t=datetime.strptime(row["time"],"%H:%M:%S")
        row["dt"]=current_date.replace(hour=t.hour,minute=t.minute,second=t.second)
        if prev_time is not None and row["dt"]<prev_time:
            current_date+=timedelta(days=1)
            row["dt"]=current_date.replace(hour=t.hour,minute=t.minute,second=t.second)
        prev_time=row["dt"]

def read_signal_file(filename: str) -> tuple[dict, list[dict], list[str]]:
    meta = {}
    rows = []
    with open(filename, encoding="utf-8") as file:
        while True:
            line = file.readline()
            if not line:
                return meta, rows, []
            if line.startswith("#"):
                key, value = line[1:].strip().split("=", 1)
                try:
                    meta[key] = float(value)
                except ValueError:
                    meta[key] = value
            else:
                header = line.strip().split(",")
                break
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
            row["events"] = row["events"].strip()
            rows.append(row)

    reconstruct_datetimes(rows)
    return meta,rows,header

def read_camera_events(filename:str)->list[dict]:
    events=[]
    with open(filename,encoding="utf-8") as f:
        header=f.readline().strip().split(",")
        for line in f:
            values=line.strip().split(",")
            if len(values)!=len(header):
                continue
            row=dict(zip(header,values))
            try:
                row["weight"]=float(row["weight"])
            except (KeyError,ValueError):
                continue
            events.append(row)
    current_date=datetime(2026,1,1)
    prev_dt=None
    for row in events:
        t=datetime.strptime(row["date"],"%H:%M:%S")
        row["datetime"]=current_date.replace(hour=t.hour,minute=t.minute,second=t.second)
        if prev_dt is not None and row["datetime"]<prev_dt:
            current_date+=timedelta(days=1)
            row["datetime"]=current_date.replace(hour=t.hour,minute=t.minute,second=t.second)
        prev_dt=row["datetime"]
    return events

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

def reconstruct_visits(rows:list[dict],periods:list[tuple[str,int,int]])->tuple[list[dict],list[dict]]:
    visits=[]
    oversize=[]
    current=None
    over=None
    for state,start,end in periods:
        period=rows[start:end+1]
        if state=="ARRIVAL":
            current={"arrival":period[0]["time"],"arrival_i":start,"peak":max(row["weight"] for row in period)}
        elif state=="PRESENT":
            if current:
                current["present"]=period[0]["time"]
                current["present_i"]=start
                current["stay"]=period[-1]["mono_t"]-period[0]["mono_t"]
                weights=[row["weight"] for row in period]
                current["mean"]=sum(weights)/len(weights)
                current["peak"]=max(current["peak"],max(weights))
                current["trigger"]=any(row_has_event(row,"CAMERA_TRIGGER") for row in period)
        elif state=="OVERSIZE":
            over={"arrival":period[0]["time"],"duration":period[-1]["mono_t"]-period[0]["mono_t"],"peak":max(row["weight"] for row in period)}
        elif state=="DEPARTURE":
            if over:
                over["leave"]=period[0]["time"]
                oversize.append(over)
                over=None
            elif current:
                current["leave"]=period[0]["time"]
                current["departure"]=any(row_has_event(row,"DEPARTURE_TRIGGER") for row in period)
        elif state=="IDLE":
            if current and current.get("trigger") and current.get("departure"):
                current["idle"]=period[0]["time"]
                visits.append(current)
            current=None
    if over:
        oversize.append(over)
    return visits,oversize

def get_configuration(meta: dict) -> dict:
    weight_threshold = meta.get("weightThreshold", 0)
    return {
        "weight_threshold": weight_threshold,
        "threshold_off": get_threshold_off(weight_threshold),
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
        row["offset"]
        for row in rows
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
        result["offset_range"] = (
            max(idle_offsets) - min(idle_offsets)
        )
        result["idle_mean"] = (
            sum(idle_offsets) / len(idle_offsets)
        )
    else:
        result["no_idle_offset_samples"] = True
    last_offset = None
    for index, row in enumerate(baseline_resets, 1):
        offset = row["offset"]
        delta = (
            0.0
            if last_offset is None
            else offset - last_offset
        )
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

def get_visit_statistics(visits:list[dict],oversize:list[dict],hx_triggers:int)->dict:
    result={"hx_triggers":hx_triggers,"completed_visits":len(visits),"oversize":len(oversize)}
    if visits:
        durations=[visit["stay"] for visit in visits]
        result["visit_durations"]={"minimum":min(durations),"maximum":max(durations),"mean":sum(durations)/len(durations)}
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

def get_camera_events(rows:list[dict],camera_events:list[dict])->dict:
    triggers=[row["dt"] for row in rows if row_has_event(row,"CAMERA_TRIGGER")]
    fifo=[event for event in camera_events if event["event"]=="cam_FIFO"]
    used=set()
    for trigger in triggers:
        hits=[i for i,event in enumerate(fifo) if i not in used and timedelta(0)<=event["datetime"]-trigger<=timedelta(seconds=CAMERA_MATCH_SECONDS)]
        if hits:
            used.add(min(hits,key=lambda i:fifo[i]["datetime"]))
    count=lambda name:sum(event["event"]==name for event in camera_events)
    sent=sum(event["event"].startswith("cam_SND_MV_") for event in camera_events)
    return {"hx_triggers":len(triggers), "fifo":len(fifo),
            "matched_fifo":len(used), "unrelated_fifo":len(fifo)-len(used),
            "recordings":count("cam_SND_MV_ok"),"other_sent":sent-count("cam_SND_MV_ok"),
            "clr_q":count("cam_CLR_Q"),"stdby":count("cam_STDBY")}

def get_summary(visits:list[dict],oversize:list[dict])->dict:
    result={"completed_visits":len(visits)}
    if visits:
        result["mean_stay"]=sum(visit["stay"] for visit in visits)/len(visits)
        result["longest"]=max(visit["stay"] for visit in visits)
        result["highest"]=max(visit["peak"] for visit in visits)
    if oversize:
        result["oversize"]=len(oversize)
    return result
 
def create_plot(
    rows: list[dict],
    periods: list[tuple[str, int, int]],
    weight_threshold: float,
    startup_offset: float,
    hx_scale: float,
    output_path: str
) -> None:
    times = [row["dt"] for row in rows]
    weights = [row["weight"] for row in rows]
    thresholds = [row["threshold"] for row in rows]
    sigmas = [row["sigma"] for row in rows]
    offset_g = [
        (
            startup_offset - row["offset"]
        ) / abs(hx_scale)
        if hx_scale != 0
        else 0.0
        for row in rows
    ]
    threshold_off = get_threshold_off(weight_threshold)
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
    ax.plot(
        times,
        thresholds,
        label="threshold",
        linewidth=1,
        color="green"
    )
    ax.plot(
        times,
        sigmas,
        label="sigma",
        linewidth=1,
        color="red"
    )
    ax.axhline(
        weight_threshold,
        color="gray",
        linestyle="--",
        alpha=0.7,
        label="weightThreshold"
    )
    ax.axhline(
        threshold_off,
        color="green",
        linestyle="--",
        alpha=0.7,
        label="threshold_off"
    )
    for state, start, end in periods:
        if state != "IDLE":
            ax.axvspan(
                times[start],
                times[end],
                alpha=0.08
            )
    camera_triggers = [
        times[i] for i, row in enumerate(rows)
        if row_has_event(row, "CAMERA_TRIGGER")
    ]
    if camera_triggers:
        ax.vlines(
            camera_triggers,
            ymin=0,
            ymax=max(weights) * 1.1 if max(weights) > 0 else 1,
            color="blue",
            linestyle="-",
            alpha=0.6,
            linewidth=1,
            label="CAMERA_TRIGGER"
        )
    plot_end = max(
        times[-1],
        times[0] + timedelta(hours=1)
    )
    ax.set_xlim(times[0], plot_end)
    ax.xaxis.set_major_formatter(
        plt.matplotlib.dates.DateFormatter("%H:%M")
    )
    ax.set_xlabel("time")
    ax.set_ylabel("grams")
    ax.legend(loc="upper right", framealpha=0.4)
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(output_path)
    plt.close(fig)

def analyze_csv(signal_filename:str,camera_filename:str)->dict:
    if not os.path.isfile(signal_filename):
        return {"signal_csv":False}
    if not os.path.isfile(camera_filename):
        return {"signal_csv":True,"cam_event":False}
    meta,rows,_=read_signal_file(signal_filename)
    camera_events=read_camera_events(camera_filename)
    if not rows:
        return {"signal_csv":True,"cam_event":True,"samples":0}
    weight_threshold=meta.get("weightThreshold",0)
    hx_scale=meta.get("hxScale",0)
    startup_offset=meta.get("startup_offset",0)
    periods=split_periods(rows)
    visits,oversize=reconstruct_visits(rows,periods)
    camera_analysis=get_camera_events(rows,camera_events)
    idle_warnings=find_idle_warnings(rows,get_threshold_off(weight_threshold))
    output_path=os.path.join(os.path.dirname(signal_filename),"signal_timeline.svg")
    create_plot(rows,periods,weight_threshold,startup_offset,hx_scale,output_path)
    return {
        "signal_csv":True,
        "cam_event":True,
        "samples":len(rows),
        "first":rows[0]["time"],
        "last":rows[-1]["time"],
        "configuration":get_configuration(meta),
        "baseline_statistics":get_baseline_statistics(rows,meta),
        "oversize_events":get_oversize(oversize),
        "visit_statistics":get_visit_statistics(visits,oversize,camera_analysis["hx_triggers"]),
        "camera_events":camera_analysis,
        "idle_statistics":get_idle_statistics(rows),
        "warnings":get_warnings(idle_warnings,oversize),
        "offset_discontinuities":get_offset_discontinuities(rows,hx_scale),
        "summary":get_summary(visits,oversize),
        "timeline":"/ramdisk/signal_timeline.svg"
    }
