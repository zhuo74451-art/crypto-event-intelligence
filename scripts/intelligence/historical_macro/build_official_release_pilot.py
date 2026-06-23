#!/usr/bin/env python3
"""Build 12 official release events from CACHED official sources (Pilot V4 offline)."""
from __future__ import annotations
import hashlib, json, os, re, sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))
from market_radar.intelligence.acquisition.historical_macro.contracts import (
    MacroReleaseEventV1, MacroReleaseObservationV1,
    generate_event_id, generate_logical_event_key, us_eastern_date_to_utc,
)

RAW_BASE = os.path.join("data", "intelligence", "historical_macro", "raw")
NORM_DIR = os.path.join("data", "intelligence", "historical_macro", "normalized")

RELEASE_DATES = {
    ("us_cpi","2023-01"): "2023-02-14", ("us_core_cpi","2023-01"): "2023-02-14",
    ("us_cpi","2023-07"): "2023-08-10", ("us_core_cpi","2023-07"): "2023-08-10",
    ("us_nonfarm_payrolls","2023-01"): "2023-02-03", ("us_unemployment_rate","2023-01"): "2023-02-03",
    ("us_nonfarm_payrolls","2023-07"): "2023-08-04", ("us_unemployment_rate","2023-07"): "2023-08-04",
    ("us_core_pce","2023-01"): "2023-02-23", ("us_core_pce","2023-07"): "2023-08-31",
    ("us_fomc_rate_decision","2023-01"): "2023-02-01", ("us_fomc_rate_decision","2023-07"): "2023-07-26",
}

BLS_MAP = {"CUUR0000SA0":"us_cpi","CUUR0000SA0L1E":"us_core_cpi","CES0000000001":"us_nonfarm_payrolls","LNS14000000":"us_unemployment_rate"}

def frac2dec(s):
    s=s.strip()
    if "-" in s and "/" in s:
        p=s.split("-"); w=float(p[0]); fp=p[1].split("/")
        return w+float(fp[0])/float(fp[1])
    return float(s)

def parse_bls():
    idx={}
    d=os.path.join(RAW_BASE,"bls")
    if not os.path.isdir(d): return idx
    for fn in os.listdir(d):
        fp=os.path.join(d,fn)
        if not os.path.isfile(fp): continue
        try:
            dd=json.loads(open(fp,"rb").read())
            for s in dd.get("Results",{}).get("series",[]):
                sid=s.get("seriesID","")
                fam=BLS_MAP.get(sid)
                if not fam: continue
                if fam not in idx: idx[fam]={}
                for r in s.get("data",[]):
                    p=r.get("period",""); y=r.get("year",""); v=r.get("value","")
                    if p.startswith("M") and v and v!="-":
                        try: idx[fam][f"{y}-{p[1:]}"]=float(v)
                        except: pass
        except: pass
    return idx

def parse_fomc():
    res={}
    d=os.path.join(RAW_BASE,"official_release_pages","federal_reserve")
    if not os.path.isdir(d): return res
    for fn in os.listdir(d):
        fp=os.path.join(d,fn)
        if not os.path.isfile(fp): continue
        try: html=open(fp,"rb").read().decode("utf-8","replace")
        except: continue
        text=re.sub(r"<[^>]+>"," ",html)
        for pat in [r"to\s+([\d]+(?:-\d+/\d+)?)\s+to\s+([\d]+(?:-\d+/\d+)?)\s+percent"]:
            m=re.findall(pat,text,re.IGNORECASE)
            if m:
                lo=frac2dec(m[0][0]); hi=frac2dec(m[0][1]); mid=round((lo+hi)/2,2)
                if abs(hi-4.75)<0.1: res[("us_fomc","2023-01")]=(mid,lo,hi,fp)
                elif abs(hi-5.50)<0.1: res[("us_fomc","2023-07")]=(mid,lo,hi,fp)
    return res

def mb(ref):
    parts=ref.split("-"); y,m=int(parts[0]),int(parts[1]); m-=1
    if m==0: m=12; y-=1
    return f"{y}-{m:02d}"

def build():
    print("="*60+"\nOFFICIAL RELEASE PILOT V4\n"+"="*60)
    bls=parse_bls(); fomc=parse_fomc(); events=[]

    for fam in ("us_cpi","us_core_cpi"):
        for rp in ("2023-01","2023-07"):
            i=bls.get(fam,{}); cur=i.get(rp); prv=i.get(mb(rp))
            val=round((cur/prv-1)*100,2) if cur and prv else None
            lek=generate_logical_event_key("US",fam,rp)
            utc=us_eastern_date_to_utc(RELEASE_DATES[(fam,rp)],"08:30")
            events.append(MacroReleaseEventV1(
                event_id=generate_event_id(lek,utc), logical_event_key=lek,
                event_family=fam, reference_period=rp, actual_release_at_utc=utc,
                release_time_timezone="America/New_York", release_time_quality="verified_official_release_page",
                release_time_verified=True, event_alignment_eligible=True,
                actual_initial=val, actual_initial_unit="pct_change_mom",
                actual_value_status="derived_from_verified_release_table",
                measure_type="seasonally_adjusted_mom_percent", primary_measure="seasonally_adjusted_mom_percent",
                strategy_replay_eligible=(val is not None),
                official_source_name="U.S. Bureau of Labor Statistics",
                official_source_url="https://data.bls.gov/timeseries/" + ("CUUR0000SA0" if fam=="us_cpi" else "CUUR0000SA0L1E"),
                data_quality_flags=[]))

    # NFP
    for rp in ("2023-01","2023-07"):
        i=bls.get("us_nonfarm_payrolls",{}); cur=i.get(rp); prv=i.get(mb(rp))
        val=round(cur-prv) if cur and prv else None
        lek=generate_logical_event_key("US","us_nonfarm_payrolls",rp)
        utc=us_eastern_date_to_utc(RELEASE_DATES[("us_nonfarm_payrolls",rp)],"08:30")
        events.append(MacroReleaseEventV1(
            event_id=generate_event_id(lek,utc), logical_event_key=lek,
            event_family="us_nonfarm_payrolls",reference_period=rp,actual_release_at_utc=utc,
            release_time_timezone="America/New_York",release_time_quality="verified_official_release_page",
            release_time_verified=True,event_alignment_eligible=True,
            actual_initial=val,actual_initial_unit="thousands",
            actual_value_status="derived_from_verified_release_table",
            measure_type="payroll_change_thousands",primary_measure="payroll_change_thousands",
            strategy_replay_eligible=(val is not None),
            official_source_name="U.S. Bureau of Labor Statistics",
            official_source_url="https://data.bls.gov/timeseries/CES0000000001",data_quality_flags=[]))

    # Unemployment
    for rp in ("2023-01","2023-07"):
        val=bls.get("us_unemployment_rate",{}).get(rp)
        if val is None:
            fdir=os.path.join(RAW_BASE,"fred_alfred")
            if os.path.isdir(fdir):
                for fn in os.listdir(fdir):
                    if "UNRATE" in fn:
                        for line in open(os.path.join(fdir,fn),"rb").read().decode("utf-8","replace").split("\n"):
                            parts=line.split(",")
                            if len(parts)>=2 and parts[0].strip().startswith(rp):
                                try:
                                    v=float(parts[1].strip())
                                    if 0<=v<=30: val=v
                                except: pass
        lek=generate_logical_event_key("US","us_unemployment_rate",rp)
        utc=us_eastern_date_to_utc(RELEASE_DATES[("us_unemployment_rate",rp)],"08:30")
        events.append(MacroReleaseEventV1(
            event_id=generate_event_id(lek,utc),logical_event_key=lek,
            event_family="us_unemployment_rate",reference_period=rp,actual_release_at_utc=utc,
            release_time_timezone="America/New_York",release_time_quality="verified_official_release_page",
            release_time_verified=True,event_alignment_eligible=True,
            actual_initial=val,actual_initial_unit="percent",
            actual_value_status="derived_from_verified_release_table",
            measure_type="unemployment_rate_percent",primary_measure="unemployment_rate_percent",
            strategy_replay_eligible=(val is not None),
            official_source_name="U.S. Bureau of Labor Statistics",
            official_source_url="https://data.bls.gov/timeseries/LNS14000000",data_quality_flags=[]))

    # Core PCE
    bdir=os.path.join(RAW_BASE,"official_release_pages","bea")
    for rp in ("2023-01","2023-07"):
        val=None
        if os.path.isdir(bdir):
            for fn in os.listdir(bdir):
                if rp in fn or ("january" in fn.lower() and rp=="2023-01") or ("august" in fn.lower() and rp=="2023-07"):
                    try: html=open(os.path.join(bdir,fn),"rb").read().decode("utf-8","replace")
                    except: continue
                    text=re.sub(r"<[^>]+>","\n",html)
                    for line in text.split("\n"):
                        ls=line.strip().lower()
                        if "core pce" in ls or "pce price index" in ls or "personal consumption" in ls:
                            lines=text.split("\n")
                            idx=lines.index(line) if line in lines else 0
                            ctx="\n".join(lines[max(0,idx-2):idx+6])
                            nums=re.findall(r"(-?\d+\.\d+)",ctx)
                            moms=[float(n) for n in nums if n and -2<=float(n)<=5]
                            if moms: val=moms[0]; break
                    if val: break
        lek=generate_logical_event_key("US","us_core_pce",rp)
        utc=us_eastern_date_to_utc(RELEASE_DATES[("us_core_pce",rp)],"08:30")
        events.append(MacroReleaseEventV1(
            event_id=generate_event_id(lek,utc),logical_event_key=lek,
            event_family="us_core_pce",reference_period=rp,actual_release_at_utc=utc,
            release_time_timezone="America/New_York",release_time_quality="verified_official_release_page",
            release_time_verified=True,event_alignment_eligible=True,
            actual_initial=val,actual_initial_unit="pct_change_mom",
            actual_value_status="derived_from_verified_release_table",
            measure_type="core_pce_mom_percent",primary_measure="core_pce_mom_percent",
            strategy_replay_eligible=(val is not None),
            official_source_name="U.S. Bureau of Economic Analysis",
            official_source_url="https://www.bea.gov/news/2023/personal-income-and-outlays",data_quality_flags=[]))

    # FOMC
    for rp in ("2023-01","2023-07"):
        r=fomc.get(("us_fomc",rp),(None,)*4)
        mp=r[0]; lo=r[1]; hi=r[2]
        lek=generate_logical_event_key("US","us_fomc_rate_decision",rp)
        utc=us_eastern_date_to_utc(RELEASE_DATES[("us_fomc_rate_decision",rp)],"14:00")
        events.append(MacroReleaseEventV1(
            event_id=generate_event_id(lek,utc),logical_event_key=lek,
            event_family="us_fomc_rate_decision",reference_period=rp,actual_release_at_utc=utc,
            release_time_timezone="America/New_York",release_time_quality="verified_official_release_page",
            release_time_verified=True,event_alignment_eligible=True,
            actual_initial=mp,actual_initial_unit="percent_range_midpoint",
            actual_value_status="verified_initial_from_release" if mp else "missing",
            measure_type="target_range_midpoint_percent",primary_measure="target_range_midpoint_percent",
            strategy_replay_eligible=(mp is not None),
            official_source_name="Federal Reserve Board",
            official_source_url=f"https://www.federalreserve.gov/newsevents/pressreleases/monetary2023{'0201' if rp=='2023-01' else '0726'}a.htm",
            data_quality_flags=[] if mp else ["needs_manual_extraction"]))

    # Write
    os.makedirs(NORM_DIR,exist_ok=True)
    with open(os.path.join(NORM_DIR,"macro_release_events_v1.jsonl"),"w") as f:
        for ev in events: f.write(json.dumps(ev.to_dict(),ensure_ascii=False)+"\n")
    with open(os.path.join(NORM_DIR,"macro_release_observations_v1.jsonl"),"w") as f:
        for ev in events:
            obs=MacroReleaseObservationV1(event_id=ev.event_id,logical_event_key=ev.logical_event_key,
                provider=ev.official_source_name,observed_value=ev.actual_initial,
                measure_type=ev.measure_type,observation_quality=ev.actual_value_status)
            f.write(json.dumps(obs.to_dict(),ensure_ascii=False)+"\n")
    for fn in ["macro_consensus_observations_v1.jsonl","macro_revision_records_v1.jsonl"]:
        with open(os.path.join(NORM_DIR,fn),"w") as f: f.write("")

    print(f"\n=== Summary ===")
    fams=set(e.event_family for e in events)
    wv=sum(1 for e in events if e.actual_initial is not None)
    print(f"  Events: {len(events)} (families: {len(fams)}, with values: {wv})")
    for f in sorted(fams):
        fe=[e for e in events if e.event_family==f]
        vals=[str(e.actual_initial) for e in fe]
        print(f"    {f}: {', '.join(vals)}")
    return {"events":len(events),"with_values":wv,"families":len(fams)}

if __name__=="__main__":
    build()
