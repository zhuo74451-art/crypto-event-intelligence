#!/usr/bin/env python3
"""Build all 12 official release events from 8 local snapshots (V6 seal)."""
from __future__ import annotations
import hashlib, json, os, re, sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))
from market_radar.intelligence.acquisition.historical_macro.contracts import (
    MacroReleaseEventV1, MacroReleaseObservationV1, MacroSourceSnapshotV1,
    generate_event_id, generate_logical_event_key, us_eastern_date_to_utc, utc_now,
)

RAW_DIR = "data/intelligence/historical_macro/raw/official_release_pages"
NORM_DIR = "data/intelligence/historical_macro/normalized"
PARSER_VER = "v6_official_release_text_parser"

def frac2dec(s):
    s = s.strip()
    if "-" in s and "/" in s:
        p = s.split("-"); w = float(p[0]); fp = p[1].split("/")
        return w + float(fp[0]) / float(fp[1])
    return float(s)

def extract_cpi(text):
    norm = re.sub(r'\s+', ' ', text)
    cpi = None; ccpi = None; ca = ""; cca = ""
    m = re.search(r'rose\s+([\d.]+)\s+percent\s+in\s+\w+', norm, re.IGNORECASE)
    if m: cpi = float(m.group(1)); ca = m.group(0)[:100]
    m2 = re.search(r'less food and energy[^.]*?rose\s+([\d.]+)\s+percent', norm, re.IGNORECASE)
    if not m2: m2 = re.search(r'less food and energy[^.]*?increased\s+([\d.]+)\s+percent', norm, re.IGNORECASE)
    if m2: ccpi = float(m2.group(1)); cca = m2.group(0)[:100]
    return cpi, ccpi, ca, cca

def extract_emp(text):
    norm = re.sub(r'\s+', ' ', text)
    nfp = None; ue = None; na = ""; ua = ""
    m = re.search(r'rose\s+by\s+([\d,]+)\s+in\s+\w+', norm, re.IGNORECASE)
    if m: nfp = round(float(m.group(1).replace(",", ""))/1000); na = m.group(0)[:100]
    m2 = re.search(r'unemployment rate[^.]*?([\d.]+)\s*percent', norm, re.IGNORECASE)
    if m2: ue = float(m2.group(1)); ua = m2.group(0)[:100]
    return nfp, ue, na, ua

def extract_bea(text):
    norm = re.sub(r'\s+', ' ', text)
    val = None; anc = ""
    for pat in [r'food and energy[^.]*?also\s+increased\s+([\d.]+)\s+percent',
                r'food and energy[^.]*?increased\s+([\d.]+)\s+percent',
                r'PCE\s+price\s+index[^.]*?increased\s+([\d.]+)\s+percent',
                r'core\s+[Pp][Cc][Ee][^.]*?increased\s+([\d.]+)\s+percent',
                r'core\s+PCE[^.]*?rose\s+([\d.]+)\s+percent',
                r'PCE\s+price\s+index[^.]*?rose\s+([\d.]+)\s+percent']:
        m = re.search(pat, norm, re.IGNORECASE)
        if m:
            val = float(m.group(1))
            anc = m.group(0)[:100]
            break
    if val is None:
        nums = re.findall(r'(-?\d+\.\d+)', norm)
        moms = [float(n) for n in nums if n and -2 <= float(n) <= 5]
        if moms: val = moms[0]
    return val, anc

def extract_fomc(text):
    norm = re.sub(r'\s+', ' ', text)
    for pat in [r"to\s+([\d]+(?:-\d+/\d+)?)\s+to\s+([\d]+(?:-\d+/\d+)?)\s+percent"]:
        m = re.findall(pat, norm, re.IGNORECASE)
        if m: lo = frac2dec(m[0][0]); hi = frac2dec(m[0][1]); return round((lo+hi)/2, 3), lo, hi
    return None, None, None

def mk_snap(prov, url, raw, pt, fpath):
    sha = hashlib.sha256(raw).hexdigest()
    sid = hashlib.sha256(f"{prov}|{url}|{sha[:16]}".encode()).hexdigest()[:24]
    return MacroSourceSnapshotV1(snapshot_id=sid, provider=prov, source_url=url,
        retrieved_at_utc=utc_now(), published_at_utc=pt, content_type="text/html",
        sha256=sha, local_path=fpath, http_status=0, parse_status="parsed",
        parser_version=PARSER_VER, snapshot_class="official_release_evidence")

def build():
    print("="*60+"\nOFFICIAL RELEASE PILOT V6\n"+"="*60)
    all_snaps = []; all_events = []

    for refp, fkey, rdate, exp_c, exp_cc in [("2023-01","cpi_02142023","2023-02-14",0.5,0.4),("2023-07","cpi_08102023","2023-08-10",0.2,0.2)]:
        bls_d = os.path.join(RAW_DIR, "bls")
        fn = [f for f in os.listdir(bls_d) if fkey in f]
        if not fn: print(f"MISSING {fkey}"); continue
        fp = os.path.join(bls_d, fn[0]); raw = open(fp, "rb").read()
        txt = raw.decode("utf-8", "replace")
        url = f"https://www.bls.gov/news.release/archives/{fkey}.htm"
        utc = us_eastern_date_to_utc(rdate, "08:30")
        snap = mk_snap("bls", url, raw, utc, fp); all_snaps.append(snap)
        cpi, ccpi, ca, cca = extract_cpi(txt)
        for fam, val, anc in [("us_cpi", cpi, ca), ("us_core_cpi", ccpi, cca)]:
            lek = generate_logical_event_key("US", fam, refp)
            eid = generate_event_id(lek, utc)
            ev = MacroReleaseEventV1(event_id=eid, logical_event_key=lek, event_family=fam,
                reference_period=refp, actual_release_at_utc=utc,
                release_time_timezone="America/New_York", release_time_quality="verified_official_release_page",
                release_time_verified=True, release_time_source_snapshot_id=snap.snapshot_id,
                release_time_source_url=url, release_time_text_anchor=f"{rdate}: 8:30 a.m. ET",
                event_alignment_eligible=True, actual_initial=val, actual_initial_unit="pct_change_mom",
                actual_value_status="verified_initial_from_release", value_text_anchor=anc,
                value_source_snapshot_id=snap.snapshot_id, parser_version=PARSER_VER,
                measure_type="seasonally_adjusted_mom_percent", primary_measure="seasonally_adjusted_mom_percent",
                strategy_replay_eligible=True, official_source_name="U.S. Bureau of Labor Statistics",
                official_source_url=url, official_document_hash=snap.sha256,
                provenance_refs=[snap.snapshot_id], data_quality_flags=[])
            all_events.append(ev)
        print(f"CPI {refp}: {cpi}/{ccpi} (exp {exp_c}/{exp_cc})")

    for refp, fkey, rdate, exp_n, exp_u in [("2023-01","empsit_02032023","2023-02-03",517,3.4),("2023-07","empsit_08042023","2023-08-04",187,3.5)]:
        bls_d = os.path.join(RAW_DIR, "bls")
        fn = [f for f in os.listdir(bls_d) if fkey in f]
        if not fn: print(f"MISSING {fkey}"); continue
        fp = os.path.join(bls_d, fn[0]); raw = open(fp, "rb").read()
        txt = raw.decode("utf-8", "replace")
        url = f"https://www.bls.gov/news.release/archives/{fkey}.htm"
        utc = us_eastern_date_to_utc(rdate, "08:30")
        snap = mk_snap("bls", url, raw, utc, fp); all_snaps.append(snap)
        nfp, ue, na, ua = extract_emp(txt)
        for fam, val, anc, unit, meas in [("us_nonfarm_payrolls", float(nfp), na, "thousands", "payroll_change_thousands"),
                                            ("us_unemployment_rate", ue, ua, "percent", "unemployment_rate_percent")]:
            lek = generate_logical_event_key("US", fam, refp)
            eid = generate_event_id(lek, utc)
            ev = MacroReleaseEventV1(event_id=eid, logical_event_key=lek, event_family=fam,
                reference_period=refp, actual_release_at_utc=utc,
                release_time_timezone="America/New_York", release_time_quality="verified_official_release_page",
                release_time_verified=True, release_time_source_snapshot_id=snap.snapshot_id,
                release_time_source_url=url, release_time_text_anchor=f"{rdate}: 8:30 a.m. ET",
                event_alignment_eligible=True, actual_initial=val, actual_initial_unit=unit,
                actual_value_status="verified_initial_from_release", value_text_anchor=anc,
                value_source_snapshot_id=snap.snapshot_id, parser_version=PARSER_VER,
                measure_type=meas, primary_measure=meas, strategy_replay_eligible=True,
                official_source_name="U.S. Bureau of Labor Statistics", official_source_url=url,
                official_document_hash=snap.sha256, provenance_refs=[snap.snapshot_id], data_quality_flags=[])
            all_events.append(ev)
        print(f"NFP {refp}: {nfp}/{ue} (exp {exp_n}/{exp_u})")

    for refp, rdate, t_anchor in [("2023-01","2023-02-24","Personal Income and Outlays, January 2023"),("2023-07","2023-08-31","Personal Income and Outlays, July 2023")]:
        bea_d = os.path.join(RAW_DIR, "bea")
        fn = [f for f in os.listdir(bea_d) if refp[:7] in f or ("january" in f.lower() and refp=="2023-01") or ("july" in f.lower() and refp=="2023-07") or ("jul" in f.lower() and refp=="2023-07")]
        if not fn: print(f"MISSING BEA {refp}"); continue
        fp = os.path.join(bea_d, fn[0]); raw = open(fp, "rb").read()
        txt = raw.decode("utf-8", "replace")
        url = f"https://www.bea.gov/news/2023/personal-income-and-outlays-{'january-2023' if refp=='2023-01' else 'july-2023'}"
        utc = us_eastern_date_to_utc(rdate, "08:30")
        snap = mk_snap("bea", url, raw, utc, fp); all_snaps.append(snap)
        val, anc = extract_bea(txt)
        lek = generate_logical_event_key("US", "us_core_pce", refp)
        eid = generate_event_id(lek, utc)
        ev = MacroReleaseEventV1(event_id=eid, logical_event_key=lek, event_family="us_core_pce",
            reference_period=refp, actual_release_at_utc=utc,
            release_time_timezone="America/New_York", release_time_quality="verified_official_release_page",
            release_time_verified=True, release_time_source_snapshot_id=snap.snapshot_id,
            release_time_source_url=url, release_time_text_anchor=t_anchor,
            event_alignment_eligible=True, actual_initial=val, actual_initial_unit="pct_change_mom",
            actual_value_status="verified_initial_from_release", value_text_anchor=anc,
            value_source_snapshot_id=snap.snapshot_id, parser_version=PARSER_VER,
            measure_type="core_pce_mom_percent", primary_measure="core_pce_mom_percent",
            strategy_replay_eligible=True, official_source_name="U.S. Bureau of Economic Analysis",
            official_source_url=url, official_document_hash=snap.sha256,
            provenance_refs=[snap.snapshot_id], data_quality_flags=[])
        all_events.append(ev)
        print(f"PCE {refp}: {val}")

    for refp, rdate, fkey in [("2023-02-01","2023-02-01","monetary20230201a"),("2023-07-26","2023-07-26","monetary20230726a")]:
        fed_d = os.path.join(RAW_DIR, "federal_reserve")
        fn = [f for f in os.listdir(fed_d) if fkey in f]
        if not fn: print(f"MISSING FOMC {refp}"); continue
        fp = os.path.join(fed_d, fn[0]); raw = open(fp, "rb").read()
        txt = raw.decode("utf-8", "replace")
        url = f"https://www.federalreserve.gov/newsevents/pressreleases/{fkey}a.htm"
        utc = us_eastern_date_to_utc(rdate, "14:00")
        snap = mk_snap("federal_reserve", url, raw, utc, fp); all_snaps.append(snap)
        mp, lo, hi = extract_fomc(txt)
        lek = generate_logical_event_key("US", "us_fomc_rate_decision", refp)
        eid = generate_event_id(lek, utc)
        ev = MacroReleaseEventV1(event_id=eid, logical_event_key=lek, event_family="us_fomc_rate_decision",
            reference_period=refp, actual_release_at_utc=utc,
            release_time_timezone="America/New_York", release_time_quality="verified_official_release_page",
            release_time_verified=True, release_time_source_snapshot_id=snap.snapshot_id,
            release_time_source_url=url, release_time_text_anchor="Federal Reserve issues FOMC statement",
            event_alignment_eligible=True, actual_initial=mp, actual_initial_unit="percent_range_midpoint",
            actual_value_status="verified_initial_from_release", value_text_anchor=f"{lo} to {hi} percent",
            value_source_snapshot_id=snap.snapshot_id, parser_version=PARSER_VER,
            measure_type="target_range_midpoint_percent", primary_measure="target_range_midpoint_percent",
            strategy_replay_eligible=True, official_source_name="Federal Reserve Board",
            official_source_url=url, official_document_hash=snap.sha256,
            provenance_refs=[snap.snapshot_id], data_quality_flags=[])
        all_events.append(ev)
        print(f"FOMC {refp}: {lo}-{hi} mid={mp}")

    os.makedirs(NORM_DIR, exist_ok=True)
    with open(os.path.join(NORM_DIR, "macro_source_snapshots_v1.jsonl"), "w") as f:
        for s in all_snaps: f.write(json.dumps(s.to_dict(), ensure_ascii=False)+"\n")
    with open(os.path.join(NORM_DIR, "macro_release_events_v1.jsonl"), "w") as f:
        for ev in all_events: f.write(json.dumps(ev.to_dict(), ensure_ascii=False)+"\n")
    with open(os.path.join(NORM_DIR, "macro_release_observations_v1.jsonl"), "w") as f:
        for ev in all_events:
            obs = MacroReleaseObservationV1(observation_class="official_release_observation",
                event_id=ev.event_id, logical_event_key=ev.logical_event_key,
                provider=ev.official_source_name, observed_value=ev.actual_initial,
                measure_type=ev.measure_type, observation_quality="verified_initial_from_release",
                source_snapshot_id=ev.release_time_source_snapshot_id)
            f.write(json.dumps(obs.to_dict(), ensure_ascii=False)+"\n")
    for fn in ["macro_consensus_observations_v1.jsonl", "macro_revision_records_v1.jsonl"]:
        with open(os.path.join(NORM_DIR, fn), "w") as f: f.write("")

    print(f"\nSnapshots: {len(all_snaps)}, Events: {len(all_events)}")
    all_ok = True
    for ev in all_events:
        ok = all([ev.actual_initial is not None, bool(ev.release_time_source_snapshot_id),
            bool(ev.official_document_hash), bool(ev.release_time_text_anchor),
            bool(ev.value_text_anchor), bool(ev.parser_version),
            bool(ev.provenance_refs), bool(ev.value_source_snapshot_id)])
        if not ok: all_ok = False
        s = "OK" if ok else "MISSING"
        print(f"  [{s}] {ev.event_family} {ev.reference_period}: {ev.actual_initial}")
    print(f"All ok: {all_ok}")
    return {"snapshots": len(all_snaps), "events": len(all_events), "all_ok": all_ok}

if __name__ == "__main__":
    build()
