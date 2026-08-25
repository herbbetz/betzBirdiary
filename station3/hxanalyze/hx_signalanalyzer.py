#!/usr/bin/env python3
"""
hx_signalanalyzer.py
Analyze SignalLogger output and camera recorder events.
Reads metadata from SignalLogger header:
weightThreshold
threshold_off
weightlimit
hxScale
CAMERA_DELAY
FSM states:
IDLE ARRIVAL PRESENT OVERSIZE DEPARTURE
"""
from datetime import datetime,timedelta
import csv
import sys
import matplotlib.pyplot as plt
JUMP_G=3.0
IDLE_BAD_TIME=5.0
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
    return meta,rows,header
def read_camera_events(filename:str)->list[dict]:
    events=[]
    with open(filename,encoding="utf-8",newline="") as f:
        reader=csv.DictReader(f)
        for row in reader:
            try:
                row["datetime"]=datetime.strptime(
                    row["date"],
                    "%Y-%m-%d %H:%M:%S"
                )
                row["weight"]=float(row["weight"])
            except (KeyError,ValueError):
                continue
            events.append(row)
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
        elif state=="OVERSIZE":
            over={"arrival":period[0]["time"],"duration":period[-1]["mono_t"]-period[0]["mono_t"],"peak":max(row["weight"] for row in period)}
        elif state=="DEPARTURE":
            if over:
                over["leave"]=period[0]["time"]
                oversize.append(over)
                over=None
            elif current:
                current["leave"]=period[0]["time"]
        elif state=="IDLE":
            if current:
                current["idle"]=period[0]["time"]
                if "stay" not in current:
                    current["stay"]=0.0
                    current["mean"]=0.0
                visits.append(current)
                current=None
    return visits,oversize
def print_configuration(meta:dict)->None:
    weight_threshold=meta.get("weightThreshold",0)
    threshold_off=meta.get("threshold_off",weight_threshold*0.7)
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
    baseline_resets=[row for row in rows if "BASELINE_RESET" in row["events"].split()]
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
def analyze_camera_events(rows:list[dict],camera_events:list[dict])->dict:
    camera_triggers=[]
    for row in rows:
        if "CAMERA_TRIGGER" in row["events"].split("|"):
            try:
                timestamp=datetime.strptime(
                    row["time"],
                    "%Y-%m-%d %H:%M:%S"
                )
            except ValueError:
                continue
            camera_triggers.append({
                "row":row,
                "datetime":timestamp
            })
    fifo_events=[
        event for event in camera_events
        if event["event"]=="cam_FIFO"
    ]
    matched_fifo=[]
    unrelated_fifo=[]
    used_fifo=set()
    for trigger in camera_triggers:
        trigger_time=trigger["datetime"]
        candidates=[
            (index,event)
            for index,event in enumerate(fifo_events)
            if index not in used_fifo
            and timedelta(0)<=event["datetime"]-trigger_time<=timedelta(seconds=2)
        ]
        if candidates:
            index,event=min(
                candidates,
                key=lambda item:item[1]["datetime"]
            )
            used_fifo.add(index)
            matched_fifo.append({
                "trigger":trigger,
                "fifo":event,
                "recording":False,
                "blocked":None
            })
    for index,event in enumerate(fifo_events):
        if index not in used_fifo:
            unrelated_fifo.append(event)
    for match in matched_fifo:
        fifo_time=match["fifo"]["datetime"]
        following=[
            event for event in camera_events
            if event["datetime"]>=fifo_time
        ]
        for event in following:
            if event["event"]=="cam_SND_MVMNT_FNSHD":
                match["recording"]=True
                break
            if event["event"] in ("cam_CLR_Q","cam_STDBY"):
                match["blocked"]=event["event"]
                break
    return {
        "hx_triggers":len(camera_triggers),
        "matched_fifo":matched_fifo,
        "unrelated_fifo":unrelated_fifo,
        "recordings":sum(match["recording"] for match in matched_fifo),
        "clr_q":sum(match["blocked"]=="cam_CLR_Q" for match in matched_fifo),
        "stdby":sum(match["blocked"]=="cam_STDBY" for match in matched_fifo)
    }
def print_camera_events(camera_analysis:dict)->None:
    print()
    print("Camera events")
    print("-------------")
    print(f"hx triggers             : {camera_analysis['hx_triggers']}")
    print(f"FIFO triggers           : {len(camera_analysis['matched_fifo'])}")
    print(f"followed by recording   : {camera_analysis['recordings']}")
    print(f"blocked by CLR_Q        : {camera_analysis['clr_q']}")
    print(f"blocked by STDBY        : {camera_analysis['stdby']}")
    print(f"unrelated FIFO events   : {len(camera_analysis['unrelated_fifo'])}")
def print_visit_statistics(visits:list[dict],oversize:list[dict])->None:
    print()
    print("Visit statistics")
    print("----------------")
    print(f"visits   : {len(visits)}")
    print(f"oversize : {len(oversize)}")
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
    print(f"visits   : {len(visits)}")
    if visits:
        print(f"mean stay: {sum(v['stay'] for v in visits)/len(visits):.1f} s")
        print(f"longest  : {max(v['stay'] for v in visits):.1f} s")
        print(f"highest  : {max(v['peak'] for v in visits):.2f} g")
    if oversize:
        print(f"oversize : {len(oversize)}")
def create_plot(rows:list[dict],periods:list[tuple[str,int,int]],weight_threshold:float,startup_offset:float,hx_scale:float,weightlimit:float)->None:
    times=[datetime.strptime(row["time"],"%Y-%m-%d %H:%M:%S") for row in rows]
    weights=[row["weight"] for row in rows]
    sigmas=[row["sigma"] for row in rows]
    thresholds=[row["threshold"] for row in rows]
    offset_g=[(startup_offset-row["offset"])/abs(hx_scale) if hx_scale!=0 else 0.0 for row in rows]
    threshold_off=weight_threshold*0.7
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
    if hx_scale!=0:
        for index in range(1,len(rows)):
            delta_g=(rows[index-1]["offset"]-rows[index]["offset"])/abs(hx_scale)
            if abs(delta_g)>JUMP_G:
                ax.axvline(times[index],linestyle=":",alpha=0.8)
    plot_end=max(times[-1],times[0]+timedelta(hours=1))
    ax.set_xlim(times[0],plot_end)
    ax.xaxis.set_major_formatter(plt.matplotlib.dates.DateFormatter("%H:%M"))
    ax.set_xlabel("time")
    ax.set_ylabel("grams")
    ax.legend(loc="upper left")
    ax.grid(True,alpha=0.3)
    plt.tight_layout()
    plt.savefig("signal_timeline.svg")
    print("timeline plot written to signal_timeline.svg")
def main()->None:
    if len(sys.argv)!=3:
        print("usage: hx_signalanalyzer.py signal_xxx.csv cam_event.csv")
        sys.exit(1)
    meta,rows,_=read_signal_file(sys.argv[1])
    camera_events=read_camera_events(sys.argv[2])
    if not rows:
        print("no samples found")
        sys.exit(1)
    weight_threshold=meta.get("weightThreshold",0)
    weightlimit=meta.get("weightlimit",0)
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
    print_visit_statistics(visits,oversize)
    camera_analysis=analyze_camera_events(rows,camera_events)
    print_camera_events(camera_analysis)
    print_idle_statistics(rows)
    threshold_off=weight_threshold*0.7
    idle_warnings=find_idle_warnings(rows,threshold_off)
    print_warnings(idle_warnings,oversize)
    print_offset_discontinuities(rows,hx_scale)
    print_summary(visits,oversize)
    create_plot(rows,periods,weight_threshold,meta.get("startup_offset",0),hx_scale,weightlimit)
if __name__=="__main__":
    main()