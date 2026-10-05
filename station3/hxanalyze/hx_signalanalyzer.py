#!/usr/bin/env python3
"""
hx_signalanalyzer.py
Analyze SignalLogger output and camera recorder events.
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
from datetime import datetime,timedelta
import csv
import os
import sys
import matplotlib.pyplot as plt
JUMP_G=3.0
IDLE_BAD_TIME=5.0
THRESHOLD_OFF_FACTOR=0.7
CAMERA_MATCH_SECONDS=2.0

def get_threshold_off(weight_threshold:float)->float:
    """The one place where threshold_off is defined."""
    return weight_threshold*THRESHOLD_OFF_FACTOR

def row_has_event(row:dict,event:str)->bool:
    """Events are separated by '|' only."""
    return event in row["events"].split("|")

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

def read_signal_file(filename:str)->tuple[dict,list[dict],list[str]]:
    meta={}
    rows=[]
    with open(filename,encoding="utf-8") as f:
        while True:
            line=f.readline()
            if not line:
                return meta,rows,[]
            if line.startswith("#"):
                key,value=line[1:].strip().split("=",1)
                try:
                    meta[key]=float(value)
                except ValueError:
                    meta[key]=value
            else:
                header=line.strip().split(",")
                break
        for line in f:
            values=line.strip().split(",")
            if len(values)!=len(header):
                continue
            row=dict(zip(header,values))
            row["mono_t"]=float(row["mono_t"])
            row["raw"]=float(row["raw"])
            row["weight"]=float(row["weight"])
            row["offset"]=float(row["offset"])
            row["sigma"]=float(row["sigma"])
            row["threshold"]=float(row["threshold"])
            row["events"]=row["events"].strip()
            rows.append(row)
    reconstruct_datetimes(rows)
    return meta,rows,header

def read_camera_events(filename:str)->list[dict]:
    events=[]
    with open(filename,encoding="utf-8",newline="") as f:
        reader=csv.DictReader(f)
        for row in reader:
            try:
                row["weight"]=float(row["weight"])
            except (KeyError,ValueError):
                continue
            events.append(row)

    # Same anchor + midnight-rollover as signal rows.
    base_date=datetime(2026,1,1)
    current_date=base_date
    prev_dt=None
    for row in events:
        t=datetime.strptime(row["date"],"%H:%M:%S")
        row["datetime"]=current_date.replace(
            hour=t.hour,minute=t.minute,second=t.second
        )
        if prev_dt is not None and row["datetime"]<prev_dt:
            current_date+=timedelta(days=1)
            row["datetime"]=current_date.replace(
                hour=t.hour,minute=t.minute,second=t.second
            )
        prev_dt=row["datetime"]

    return events

def split_periods(rows:list[dict])->list[tuple[str,int,int]]:
    periods=[]
    start=0
    state=rows[0]["state"]
    for index,row in enumerate(rows[1:],1):
        if row["state"]!=state:
            periods.append((state,start,index-1))
            start=index
            state=row["state"]
    periods.append((state,start,len(rows)-1))
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

def print_configuration(meta:dict)->None:
    weight_threshold=meta.get("weightThreshold",0)
    threshold_off=get_threshold_off(weight_threshold)
    hx_scale=meta.get("hxScale",0)
    print()
    print("Configuration")
    print("-------------")
    print(f"weight threshold : {weight_threshold:.2f} g")
    print(f"threshold off    : {threshold_off:.2f} g")
    print(f"weight limit     : {meta.get('weightlimit',0):.0f} g")
    print(f"hxScale          : {hx_scale}")
    print(f"startup offset   : {meta.get('startup_offset',0):.0f}")
    print(f"startup note     : {meta.get('startup_note','')}")
    print(f"CAMERA_DELAY     : {meta.get('CAMERA_DELAY',0):.2f} s")

def print_baseline_statistics(rows:list[dict],meta:dict)->None:
    idle_offsets=[row["offset"] for row in rows if row["state"]=="IDLE"]
    baseline_resets=[row for row in rows if row_has_event(row,"BASELINE_RESET")]
    print()
    print("Baseline statistics")
    print("-------------------")
    print(f"startup offset : {meta.get('startup_offset',0):.0f}")
    if idle_offsets:
        print(f"minimum offset : {min(idle_offsets):.0f}")
        print(f"maximum offset : {max(idle_offsets):.0f}")
        print(f"offset range   : {max(idle_offsets)-min(idle_offsets):.0f}")
        print(f"idle mean      : {sum(idle_offsets)/len(idle_offsets):.0f}")
    else:
        print("no IDLE offset samples")
    print()
    print("Baseline maintenance")
    print("--------------------")
    if not baseline_resets:
        print("baseline resets : none")
        return
    print(f"baseline resets : {len(baseline_resets)}")
    last_offset=None
    for index,row in enumerate(baseline_resets,1):
        offset=row["offset"]
        delta=0.0 if last_offset is None else offset-last_offset
        print(f"  {index}. {row['time']} offset={offset:.0f} delta={delta:+.0f}")
        last_offset=offset

def print_visits(visits:list[dict])->None:
    print()
    print("Bird visits")
    print("-----------")
    for index,visit in enumerate(visits,1):
        print()
        print(f"Visit {index}")
        print(f"  arrival : {visit['arrival']}")
        print(f"  present : {visit.get('present')}")
        print(f"  leave   : {visit.get('leave')}")
        print(f"  idle    : {visit.get('idle')}")
        print(f"  stay    : {visit['stay']:.1f} s")
        print(f"  mean    : {visit['mean']:.2f} g")
        print(f"  peak    : {visit['peak']:.2f} g")

def print_oversize(oversize:list[dict])->None:
    print()
    print("Oversize events")
    print("----------------")
    if oversize:
        for index,event in enumerate(oversize,1):
            print()
            print(f"Event {index}")
            print(f"  arrival : {event['arrival']}")
            print(f"  leave   : {event.get('leave')}")
            print(f"  peak    : {event['peak']:.2f} g")
    else:
        print("none")

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

def print_camera_events(camera_analysis:dict)->None:
    print()
    print("Camera events")
    print("-------------")
    print(f"FIFO events (all)       : {camera_analysis['fifo']}")
    print(f"matched FIFO events     : {camera_analysis['matched_fifo']}")
    print(f"unrelated FIFO events   : {camera_analysis['unrelated_fifo']}")
    print(f"followed by recording   : {camera_analysis['recordings']}")
    print(f"other cam_SND_MV_*      : {camera_analysis['other_sent']}")
    print(f"blocked by CLR_Q        : {camera_analysis['clr_q']}")
    print(f"blocked by STDBY        : {camera_analysis['stdby']}")

def print_visit_statistics(visits:list[dict],oversize:list[dict],hx_triggers:int)->None:
    print()
    print("Visit statistics")
    print("----------------")
    print(f"hx triggers      : {hx_triggers}")
    print(f"completed visits : {len(visits)}")
    print(f"oversize         : {len(oversize)}")
    if visits:
        durations=[visit["stay"] for visit in visits]
        print()
        print("Visit durations")
        print("----------------")
        print(f"minimum : {min(durations):.2f} s")
        print(f"maximum : {max(durations):.2f} s")
        print(f"mean    : {sum(durations)/len(durations):.2f} s")

def print_idle_statistics(rows:list[dict])->None:
    idle=[row["weight"] for row in rows if row["state"]=="IDLE"]
    if idle:
        print()
        print("Idle statistics")
        print("----------------")
        print(f"mean weight   : {sum(idle)/len(idle):.2f} g")
        print(f"minimum       : {min(idle):.2f} g")
        print(f"maximum       : {max(idle):.2f} g")
        print(f"peak-to-peak   : {max(idle)-min(idle):.2f} g")

def find_idle_warnings(rows:list[dict],threshold_off:float)->list[tuple[dict,float,float]]:
    idle_warnings=[]
    bad_start=None
    bad_max=0.0
    for row in rows:
        outside=row["state"]=="IDLE" and abs(row["weight"])>threshold_off
        if outside:
            if bad_start is None:
                bad_start=row
                bad_max=abs(row["weight"])
            else:
                bad_max=max(bad_max,abs(row["weight"]))
        elif bad_start is not None:
            duration=row["mono_t"]-bad_start["mono_t"]
            if duration>=IDLE_BAD_TIME:
                idle_warnings.append((bad_start,duration,bad_max))
            bad_start=None
            bad_max=0.0
    if bad_start is not None:
        duration=rows[-1]["mono_t"]-bad_start["mono_t"]
        if duration>=IDLE_BAD_TIME:
            idle_warnings.append((bad_start,duration,bad_max))
    return idle_warnings

def print_warnings(idle_warnings:list[tuple[dict,float,float]],oversize:list[dict])->None:
    print()
    print("Warnings")
    print("--------")
    found=False
    for row,duration,maximum in idle_warnings:
        print(f"IDLE outside threshold_off started at {row['time']} duration={duration:.1f}s max={maximum:.2f} g.")
        found=True
    if oversize:
        print(f"Oversize events detected: {len(oversize)}")
        found=True
    if not found:
        print("none")

def print_offset_discontinuities(rows:list[dict],hx_scale:float)->None:
    print()
    print(f"Offset discontinuities (threshold: {JUMP_G} g)")
    print("--------------------")
    if hx_scale==0:
        return
    last=rows[0]["offset"]
    for row in rows[1:]:
        offset=row["offset"]
        delta_g=(last-offset)/abs(hx_scale)
        if abs(delta_g)>JUMP_G:
            print(f"{row['time']} jump={delta_g:+.2f} g state={row['state']}")
        last=offset

def print_summary(visits:list[dict],oversize:list[dict])->None:
    print()
    print("Summary")
    print("-------")
    print(f"completed visits : {len(visits)}")
    if visits:
        print(f"mean stay: {sum(v['stay'] for v in visits)/len(visits):.1f} s")
        print(f"longest  : {max(v['stay'] for v in visits):.1f} s")
        print(f"highest  : {max(v['peak'] for v in visits):.2f} g")
    if oversize:
        print(f"oversize : {len(oversize)}")

def create_plot(rows:list[dict],periods:list[tuple[str,int,int]],weight_threshold:float,startup_offset:float,hx_scale:float)->None:
    times=[row["dt"] for row in rows]
    weights=[row["weight"] for row in rows]
    sigmas=[row["sigma"] for row in rows]
    thresholds=[row["threshold"] for row in rows]
    offset_g=[(startup_offset-row["offset"])/abs(hx_scale) if hx_scale!=0 else 0.0 for row in rows]
    threshold_off=get_threshold_off(weight_threshold)
    fig,ax=plt.subplots(figsize=(11,4))
    ax.plot(times,weights,label="weight",linewidth=1)
    ax.plot(times,offset_g,label="offset drift (g)",linewidth=1)
    ax.plot(times,sigmas,label="sigma",linewidth=1,color="red")
    ax.plot(times,thresholds,label="threshold",linewidth=1,color="green")
    ax.axhline(weight_threshold,label="weightThreshold",color="gray",linestyle="--",alpha=0.7)
    ax.axhline(threshold_off,label="threshold_off",color="green",linestyle="--",alpha=0.7)
    for state,start,end in periods:
        if state!="IDLE":
            ax.axvspan(times[start],times[end],alpha=0.08)
    camera_triggers=[
        times[i] for i,row in enumerate(rows)
        if row_has_event(row,"CAMERA_TRIGGER")
    ]
    if camera_triggers:
        ax.vlines(
            camera_triggers,
            ymin=0,
            ymax=max(weights)*1.1 if max(weights)>0 else 1,
            color="blue",
            linestyle="-",
            alpha=0.6,
            linewidth=1,
            label="CAMERA_TRIGGER"
        )
    plot_end=max(times[-1],times[0]+timedelta(hours=1))
    ax.set_xlim(times[0],plot_end)
    ax.xaxis.set_major_formatter(plt.matplotlib.dates.DateFormatter("%H:%M"))
    ax.set_xlabel("time")
    ax.set_ylabel("grams")
    ax.legend(loc="upper right",framealpha=0.4)
    ax.grid(True,alpha=0.3)
    plt.tight_layout()
    plt.savefig("signal_timeline.svg")
    print("timeline plot written to signal_timeline.svg")

def fail(message:str)->None:
    print(f"error: {message}",file=sys.stderr)
    sys.exit(1)

def check_input_files(signal_filename:str,camera_filename:str)->None:
    """Report every missing input file with its absolute path, then exit."""
    missing=[
        (label,name)
        for label,name in (("signal file",signal_filename),("camera event file",camera_filename))
        if not os.path.isfile(name)
    ]
    if not missing:
        return
    for label,name in missing:
        print(f"error: {label} not found: {os.path.abspath(name)}",file=sys.stderr)
    print(f"current directory: {os.getcwd()}",file=sys.stderr)
    sys.exit(1)

def main()->None:
    if len(sys.argv)!=3:
        print("usage: hx_signalanalyzer.py signal_xxx.csv cam_event.csv")
        sys.exit(1)
    check_input_files(sys.argv[1],sys.argv[2])
    try:
        meta,rows,_=read_signal_file(sys.argv[1])
        camera_events=read_camera_events(sys.argv[2])
    except OSError as error:
        fail(f"cannot read input file: {error}")
    if not rows:
        print("no samples found")
        sys.exit(1)
    weight_threshold=meta.get("weightThreshold",0)
    # weightlimit=meta.get("weightlimit",0)
    hx_scale=meta.get("hxScale",0)
    print()
    print(f"samples : {len(rows)}")
    print(f"first   : {rows[0]['time']}")
    print(f"last    : {rows[-1]['time']}")
    print_configuration(meta)
    periods=split_periods(rows)
    visits,oversize=reconstruct_visits(rows,periods)
    print_baseline_statistics(rows,meta)
    print_oversize(oversize)
    camera_analysis=get_camera_events(rows,camera_events)
    print_visit_statistics(visits,oversize,camera_analysis["hx_triggers"])
    print_camera_events(camera_analysis)
    print_idle_statistics(rows)
    threshold_off=get_threshold_off(weight_threshold)
    idle_warnings=find_idle_warnings(rows,threshold_off)
    print_warnings(idle_warnings,oversize)
    print_offset_discontinuities(rows,hx_scale)
    print_summary(visits,oversize)
    create_plot(rows,periods,weight_threshold,meta.get("startup_offset",0),hx_scale)

if __name__=="__main__":
    main()