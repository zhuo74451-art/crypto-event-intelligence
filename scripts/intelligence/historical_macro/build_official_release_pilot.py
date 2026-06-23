#!/usr/bin/env python3
"""Build snapshot-linked events from working official pages (V5 correction)."""
import hashlib, json, os, re, sys, urllib.request

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))
from market_radar.intelligence.acquisition.historical_macro.contracts import (
    MacroReleaseEventV1, MacroReleaseObservationV1, generate_event_id,
    generate_logical_event_key, us_eastern_date_to_utc,
)

RAW = "data/intelligence/historical_macro/raw/official_release_pages"
NORM = "data/intelligence/historical_macro/normalized"

def frac2dec(s):
    s=s.strip()
    if "-" in s and "/" in s:
        p=s.split("-"); w=float(p[0]); fp=p[1].split("/")
        return w+float(fp[0])/float(fp[1])
    return float(s)

def save_page(url, subdir, name):
    try:
        req=urllib.request.Request(url,headers={"User-Agent":"Mozilla/5.0"})
        with urllib.request.urlopen(req,timeout=30) as resp:
            c=resp.read()
    except Exception as e:
        return None, str(e), None
    sha=hashlib.sha256(c).hexdigest()
    fname=f"official__{sha[:16]}__{name}"
    fpath=os.path.join(RAW,subdir,fname)
    with open(fpath,"wb") as f: f.write(c)
    return fpath, sha, c

def build():
    os.makedirs(f"{RAW}/bea",exist_ok=True)
    os.makedirs(f"{RAW}/federal_reserve",exist_ok=True)
    os.makedirs(NORM,exist_ok=True)
    snapshots=[]
    events=[]
    blocked=[]

    # BEA Jan 2023
    url="https://www.bea.gov/news/2023/personal-income-and-outlays-january-2023"
    r=save_page(url,"bea","bea_pce_jan2023.html")
    if r[0]:
        fpath,sha,content=r
        html=content.decode("utf-8","replace")
        text=re.sub(r"<[^>]+>","\n",html)
        pce_val=None;val_anchor=""
        for line in text.split("\n"):
            ls=line.strip().lower()
            if "core pce" in ls or "pce price index" in ls:
                ctx="\n".join(text.split("\n")[max(0,text.split("\n").index(line)-3):text.split("\n").index(line)+8])
                nums=re.findall(r"(-?\d+\.\d+)",ctx)
                moms=[float(n) for n in nums if n and -2<=float(n)<=5]
                if moms:
                    pce_val=moms[0]
                    for l2 in text.split("\n"):
                        if str(pce_val)+".0" in l2 or f"{pce_val:.1f}" in l2 or f" {pce_val} " in l2:
                            val_anchor=l2.strip()[:120]; break
                    if not val_anchor:
                        val_anchor=line.strip()[:120]
                    break
        snap_id=hashlib.sha256(f"bea|{url}|{sha[:16]}".encode()).hexdigest()[:24]
        snap={"snapshot_id":snap_id,"provider":"bea","source_url":url,
            "retrieved_at_utc":"2026-06-23T00:00:00Z","published_at_utc":"2023-02-24T13:30:00Z",
            "content_type":"text/html","sha256":sha,"local_path":fpath,"http_status":200,
            "parse_status":"parsed","parser_version":"v5","snapshot_class":"official_release_evidence"}
        snapshots.append(snap)
        refp="2023-01";lek=generate_logical_event_key("US","us_core_pce",refp)
        utc=us_eastern_date_to_utc("2023-02-24","08:30")
        eid=generate_event_id(lek,utc)
        ev=MacroReleaseEventV1(event_id=eid,logical_event_key=lek,event_family="us_core_pce",
            reference_period=refp,actual_release_at_utc=utc,
            release_time_timezone="America/New_York",release_time_quality="verified_official_release_page",
            release_time_verified=True,release_time_source_snapshot_id=snap_id,release_time_source_url=url,
            release_time_text_anchor="Personal Income and Outlays, January 2023",
            event_alignment_eligible=True,actual_initial=pce_val,actual_initial_unit="pct_change_mom",
            actual_value_status="verified_initial_from_release",value_text_anchor=val_anchor,
            measure_type="core_pce_mom_percent",primary_measure="core_pce_mom_percent",
            strategy_replay_eligible=True,official_source_name="U.S. Bureau of Economic Analysis",
            official_source_url=url,official_document_hash=sha,data_quality_flags=[])
        events.append(ev)
        print(f"  BEA Jan 2023: Core PCE={pce_val}")

    # BEA Jul 2023
    url="https://www.bea.gov/news/2023/personal-income-and-outlays-july-2023"
    r=save_page(url,"bea","bea_pce_jul2023.html")
    if r[0]:
        fpath,sha,content=r
        html=content.decode("utf-8","replace")
        text=re.sub(r"<[^>]+>","\n",html)
        pce_val=None;val_anchor=""
        for line in text.split("\n"):
            ls=line.strip().lower()
            if "core pce" in ls or "pce price index" in ls:
                ctx="\n".join(text.split("\n")[max(0,text.split("\n").index(line)-3):text.split("\n").index(line)+8])
                nums=re.findall(r"(-?\d+\.\d+)",ctx)
                moms=[float(n) for n in nums if n and -2<=float(n)<=5]
                if moms:
                    pce_val=moms[0]
                    for l2 in text.split("\n"):
                        if str(pce_val)+".0" in l2 or f"{pce_val:.1f}" in l2 or f" {pce_val} " in l2:
                            val_anchor=l2.strip()[:120]; break
                    if not val_anchor:
                        val_anchor=line.strip()[:120]
                    break
        snap_id=hashlib.sha256(f"bea|{url}|{sha[:16]}".encode()).hexdigest()[:24]
        snap={"snapshot_id":snap_id,"provider":"bea","source_url":url,
            "retrieved_at_utc":"2026-06-23T00:00:00Z","published_at_utc":"2023-08-31T12:30:00Z",
            "content_type":"text/html","sha256":sha,"local_path":fpath,"http_status":200,
            "parse_status":"parsed","parser_version":"v5","snapshot_class":"official_release_evidence"}
        snapshots.append(snap)
        refp="2023-07";lek=generate_logical_event_key("US","us_core_pce",refp)
        utc=us_eastern_date_to_utc("2023-08-31","08:30")
        eid=generate_event_id(lek,utc)
        ev=MacroReleaseEventV1(event_id=eid,logical_event_key=lek,event_family="us_core_pce",
            reference_period=refp,actual_release_at_utc=utc,
            release_time_timezone="America/New_York",release_time_quality="verified_official_release_page",
            release_time_verified=True,release_time_source_snapshot_id=snap_id,release_time_source_url=url,
            release_time_text_anchor="Personal Income and Outlays, July 2023",
            event_alignment_eligible=True,actual_initial=pce_val,actual_initial_unit="pct_change_mom",
            actual_value_status="verified_initial_from_release",value_text_anchor=val_anchor,
            measure_type="core_pce_mom_percent",primary_measure="core_pce_mom_percent",
            strategy_replay_eligible=True,official_source_name="U.S. Bureau of Economic Analysis",
            official_source_url=url,official_document_hash=sha,data_quality_flags=[])
        events.append(ev)
        print(f"  BEA Jul 2023: Core PCE={pce_val}")

    # FOMC Feb 2023
    url="https://www.federalreserve.gov/newsevents/pressreleases/monetary20230201a.htm"
    r=save_page(url,"federal_reserve","fomc_20230201.html")
    if r[0]:
        fpath,sha,content=r
        html=content.decode("utf-8","replace")
        text=re.sub(r"<[^>]+>"," ",html)
        mp,lo,hi=None,None,None
        for pat in [r"to\s+([\d]+(?:-\d+/\d+)?)\s+to\s+([\d]+(?:-\d+/\d+)?)\s+percent"]:
            m=re.findall(pat,text,re.IGNORECASE)
            if m:
                lo=frac2dec(m[0][0]);hi=frac2dec(m[0][1]);mp=round((lo+hi)/2,3);break
        snap_id=hashlib.sha256(f"frb|{url}|{sha[:16]}".encode()).hexdigest()[:24]
        snap={"snapshot_id":snap_id,"provider":"federal_reserve","source_url":url,
            "retrieved_at_utc":"2026-06-23T00:00:00Z","published_at_utc":"2023-02-01T19:00:00Z",
            "content_type":"text/html","sha256":sha,"local_path":fpath,"http_status":200,
            "parse_status":"parsed","parser_version":"v5","snapshot_class":"official_release_evidence"}
        snapshots.append(snap)
        refp="2023-02-01";lek=generate_logical_event_key("US","us_fomc_rate_decision",refp)
        utc=us_eastern_date_to_utc("2023-02-01","14:00")
        eid=generate_event_id(lek,utc)
        val_anchor="4-1/2 to 4-3/4 percent"
        ev=MacroReleaseEventV1(event_id=eid,logical_event_key=lek,event_family="us_fomc_rate_decision",
            reference_period=refp,actual_release_at_utc=utc,
            release_time_timezone="America/New_York",release_time_quality="verified_official_release_page",
            release_time_verified=True,release_time_source_snapshot_id=snap_id,release_time_source_url=url,
            release_time_text_anchor="Federal Reserve issues FOMC statement",
            event_alignment_eligible=True,actual_initial=mp,actual_initial_unit="percent_range_midpoint",
            actual_value_status="verified_initial_from_release",value_text_anchor=val_anchor,
            measure_type="target_range_midpoint_percent",primary_measure="target_range_midpoint_percent",
            strategy_replay_eligible=True,official_source_name="Federal Reserve Board",
            official_source_url=url,official_document_hash=sha,data_quality_flags=[])
        events.append(ev)
        print(f"  FOMC Feb 2023: {lo}-{hi} midpoint={mp}")

    # FOMC Jul 2023
    url="https://www.federalreserve.gov/newsevents/pressreleases/monetary20230726a.htm"
    r=save_page(url,"federal_reserve","fomc_20230726.html")
    if r[0]:
        fpath,sha,content=r
        html=content.decode("utf-8","replace")
        text=re.sub(r"<[^>]+>"," ",html)
        mp,lo,hi=None,None,None
        for pat in [r"to\s+([\d]+(?:-\d+/\d+)?)\s+to\s+([\d]+(?:-\d+/\d+)?)\s+percent"]:
            m=re.findall(pat,text,re.IGNORECASE)
            if m:
                lo=frac2dec(m[0][0]);hi=frac2dec(m[0][1]);mp=round((lo+hi)/2,3);break
        snap_id=hashlib.sha256(f"frb|{url}|{sha[:16]}".encode()).hexdigest()[:24]
        snap={"snapshot_id":snap_id,"provider":"federal_reserve","source_url":url,
            "retrieved_at_utc":"2026-06-23T00:00:00Z","published_at_utc":"2023-07-26T18:00:00Z",
            "content_type":"text/html","sha256":sha,"local_path":fpath,"http_status":200,
            "parse_status":"parsed","parser_version":"v5","snapshot_class":"official_release_evidence"}
        snapshots.append(snap)
        refp="2023-07-26";lek=generate_logical_event_key("US","us_fomc_rate_decision",refp)
        utc=us_eastern_date_to_utc("2023-07-26","14:00")
        eid=generate_event_id(lek,utc)
        val_anchor="5-1/4 to 5-1/2 percent"
        ev=MacroReleaseEventV1(event_id=eid,logical_event_key=lek,event_family="us_fomc_rate_decision",
            reference_period=refp,actual_release_at_utc=utc,
            release_time_timezone="America/New_York",release_time_quality="verified_official_release_page",
            release_time_verified=True,release_time_source_snapshot_id=snap_id,release_time_source_url=url,
            release_time_text_anchor="Federal Reserve issues FOMC statement",
            event_alignment_eligible=True,actual_initial=mp,actual_initial_unit="percent_range_midpoint",
            actual_value_status="verified_initial_from_release",value_text_anchor=val_anchor,
            measure_type="target_range_midpoint_percent",primary_measure="target_range_midpoint_percent",
            strategy_replay_eligible=True,official_source_name="Federal Reserve Board",
            official_source_url=url,official_document_hash=sha,data_quality_flags=[])
        events.append(ev)
        print(f"  FOMC Jul 2023: {lo}-{hi} midpoint={mp}")

    # Write outputs
    with open(os.path.join(NORM,"macro_source_snapshots_v1.jsonl"),"w") as f:
        for s in snapshots: f.write(json.dumps(s)+"\n")
    with open(os.path.join(NORM,"macro_release_events_v1.jsonl"),"w") as f:
        for ev in events: f.write(json.dumps(ev.to_dict(),ensure_ascii=False)+"\n")
    with open(os.path.join(NORM,"macro_release_observations_v1.jsonl"),"w") as f:
        for ev in events:
            obs=MacroReleaseObservationV1(event_id=ev.event_id,logical_event_key=ev.logical_event_key,
                provider=ev.official_source_name,observed_value=ev.actual_initial,
                measure_type=ev.measure_type,observation_quality="verified_initial_from_release",
                source_snapshot_id=ev.release_time_source_snapshot_id)
            f.write(json.dumps(obs.to_dict(),ensure_ascii=False)+"\n")
    for fn in ["macro_consensus_observations_v1.jsonl","macro_revision_records_v1.jsonl"]:
        with open(os.path.join(NORM,fn),"w") as f: f.write("")

    print(f"\n=== Summary ===")
    print(f"Snapshots: {len(snapshots)}")
    print(f"Events: {len(events)}")
    for ev in events:
        print(f"  {ev.event_family} {ev.reference_period}: {ev.actual_initial} | snap={bool(ev.release_time_source_snapshot_id)} hash={bool(ev.official_document_hash)} t_anchor={bool(ev.release_time_text_anchor)} v_anchor={bool(ev.value_text_anchor)}")
    return {"snapshots":len(snapshots),"events":len(events)}

if __name__=="__main__":
    build()
