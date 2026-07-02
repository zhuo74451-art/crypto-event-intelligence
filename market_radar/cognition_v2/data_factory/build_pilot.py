"""Build real historical pilot — incremental acquisition with small windows."""
import hashlib, json, os, re, sys
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Tuple

sys.path.insert(0, ".")

from market_radar.cognition_v2.data_factory.contracts import (
    RawIntakeRecord, NormalizedEvidenceRecord, QualificationState, SplitLabel,
    OutcomeObservation
)
from market_radar.cognition_v2.data_factory.outcomes import OutcomeBuilder
from market_radar.cognition_v2.data_factory.storage import write_jsonl, write_yaml, file_sha256, build_manifest_hash

ARTIFACT_DIR = "data/historical_v1"

SOURCE_FAMILY = {
    "sec-edgar": "regulatory", "federal-reserve": "macro", "nvd-nist": "technology",
    "cisa-alerts": "security", "kraken-status": "market", 
}
SOURCE_ASSET = {
    "sec-edgar": "ETH", "federal-reserve": "BTC", "nvd-nist": "BTC",
    "cisa-alerts": "BTC", "kraken-status": "BTC",
}
SOURCE_AUTH = {
    "sec-edgar": ("government_official","public_record","OFFICIAL_VERSIONED_FEED"),
    "federal-reserve": ("government_official","public_record","OFFICIAL_VERSIONED_FEED"),
    "nvd-nist": ("government_official","public_record","OFFICIAL_VERSIONED_FEED"),
    "cisa-alerts": ("government_official","public_record","OFFICIAL_IMMUTABLE_ARCHIVE"),
    "kraken-status": ("exchange_official","public_record","OFFICIAL_VERSIONED_FEED"),
}

def _content_hash(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:32]

def _intake_id(src, key, chash):
    return hashlib.sha256(f"{src}:{key}:{chash}".encode()).hexdigest()[:20]

def _fetch(url, ua="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko)"):
    import ssl, urllib.request
    ctx = ssl.create_default_context()
    req = urllib.request.Request(url, headers={"User-Agent": ua, "Accept": "application/json, text/html, application/atom+xml, text/plain"})
    return urllib.request.urlopen(req, timeout=30, context=ctx).read()

def acquire_fed():
    """Acquire Federal Reserve press releases."""
    print("Acquiring federal-reserve...", end=" ", flush=True)
    url = "https://www.federalreserve.gov/feeds/press_all.xml"
    body = _fetch(url).decode("utf-8", errors="replace")
    records = []
    for item in re.findall(r'<item>(.*?)</item>', body, re.DOTALL):
        title = (re.search(r'<title[^>]*>(.*?)</title>', item, re.DOTALL) or [None,""])[1].strip()
        link = (re.search(r'<link[^>]*>(.*?)</link>', item) or [None,""])[1].strip()
        pdate = (re.search(r'<pubDate>(.*?)</pubDate>', item) or [None,""])[1].strip()
        body_text = f"Title: {title}\nDate: {pdate}\nID: fed-{_content_hash(title)[:12]}"
        ch = _content_hash(body_text[:500])
        rec = RawIntakeRecord(intake_id=_intake_id("fed", _content_hash(title)[:16], ch),
                              source_id="federal-reserve", source_url=link,
                              raw_body=body_text[:500], retrieved_at=datetime.now(timezone.utc),
                              parser_version="fed-rss-2.0")
        records.append(rec)
    print(f"{len(records)} records")
    return records

def acquire_nvd(max_records=120):
    """Acquire NVD CVEs in 120-day windows."""
    print("Acquiring nvd-nist...", end=" ", flush=True)
    records = []
    # Query 2021-01 to 2024-06 in 120-day windows
    windows = [
        (datetime(2021,1,1,tzinfo=timezone.utc), datetime(2021,4,30,tzinfo=timezone.utc)),
        (datetime(2021,5,1,tzinfo=timezone.utc), datetime(2021,8,31,tzinfo=timezone.utc)),
        (datetime(2021,9,1,tzinfo=timezone.utc), datetime(2021,12,31,tzinfo=timezone.utc)),
        (datetime(2022,1,1,tzinfo=timezone.utc), datetime(2022,4,30,tzinfo=timezone.utc)),
        (datetime(2022,5,1,tzinfo=timezone.utc), datetime(2022,8,31,tzinfo=timezone.utc)),
        (datetime(2022,9,1,tzinfo=timezone.utc), datetime(2022,12,31,tzinfo=timezone.utc)),
        (datetime(2023,1,1,tzinfo=timezone.utc), datetime(2023,4,30,tzinfo=timezone.utc)),
        (datetime(2023,5,1,tzinfo=timezone.utc), datetime(2023,8,31,tzinfo=timezone.utc)),
        (datetime(2023,9,1,tzinfo=timezone.utc), datetime(2023,12,31,tzinfo=timezone.utc)),
        (datetime(2024,1,1,tzinfo=timezone.utc), datetime(2024,4,30,tzinfo=timezone.utc)),
    ]
    now = datetime.now(timezone.utc)
    for start, end in windows:
        if len(records) >= max_records:
            break
        params = f"pubStartDate={start.strftime('%Y-%m-%dT%H:%M:%S.000')}&pubEndDate={end.strftime('%Y-%m-%dT%H:%M:%S.000')}&resultsPerPage=50&startIndex=0"
        url = f"https://services.nvd.nist.gov/rest/json/cves/2.0?{params}"
        try:
            raw = _fetch(url)
            data = json.loads(raw)
            for vuln in data.get("vulnerabilities", []):
                cve = vuln.get("cve", {})
                cve_id = cve.get("id", "unknown")
                desc = ""
                for d in cve.get("descriptions", []):
                    if d.get("lang") == "en": desc = d.get("value",""); break
                pub = cve.get("published", "")
                body_txt = f"CVE: {cve_id}\nPublished: {pub}\nDescription: {desc[:500]}"
                ch = _content_hash(body_txt[:500])
                rec = RawIntakeRecord(intake_id=_intake_id("nvd", cve_id, ch),
                                      source_id="nvd-nist", source_url=f"https://nvd.nist.gov/vuln/detail/{cve_id}",
                                      raw_body=body_txt[:500], retrieved_at=now,
                                      parser_version="nvd-cve-2.0")
                records.append(rec)
                if len(records) >= max_records:
                    break
        except Exception as e:
            print(f"\n  NVD window {start.date()}..{end.date()}: {e}", end="")
    print(f"{len(records)} records")
    return records

def acquire_cisa():
    """Acquire CISA KEV catalog."""
    print("Acquiring cisa-alerts...", end=" ", flush=True)
    url = "https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json"
    data = json.loads(_fetch(url))
    vulns = data.get("vulnerabilities", [])
    records, now = [], datetime.now(timezone.utc)
    for v in vulns:
        cve_id = v.get("cveID","")
        name = v.get("vulnerabilityName","")
        desc = v.get("shortDescription","")[:300]
        date_added = v.get("dateAdded","")
        vendor = v.get("vendorProject","")
        body_txt = f"CISA KEV: {name}\nCVE: {cve_id}\nVendor: {vendor}\nDateAdded: {date_added}\nDescription: {desc}"
        ch = _content_hash(body_txt[:500])
        rec = RawIntakeRecord(intake_id=_intake_id("cisa", cve_id, ch),
                              source_id="cisa-alerts",
                              source_url=f"https://www.cisa.gov/known-exploited-vulnerabilities/{cve_id}",
                              raw_body=body_txt[:500], retrieved_at=now,
                              parser_version="cisa-kev-1.1")
        records.append(rec)
    print(f"{len(records)} records")
    return records

def acquire_kraken():
    """Acquire Kraken status incidents."""
    print("Acquiring kraken-status...", end=" ", flush=True)
    url = "https://status.kraken.com/api/v2/incidents.json"
    data = json.loads(_fetch(url))
    incidents = data.get("incidents", [])
    records, now = [], datetime.now(timezone.utc)
    for inc in incidents:
        inc_id = inc.get("id","")
        name = inc.get("name","")
        created = inc.get("created_at","")
        body_txt = f"Kraken: {name}\nCreated: {created}"
        ch = _content_hash(body_txt[:500])
        rec = RawIntakeRecord(intake_id=_intake_id("kraken", inc_id, ch),
                              source_id="kraken-status",
                              source_url=f"https://status.kraken.com/incidents/{inc_id}",
                              raw_body=body_txt[:500], retrieved_at=now,
                              parser_version="kraken-status-1.0")
        records.append(rec)
    print(f"{len(records)} records")
    return records

def acquire_sec():
    """Acquire SEC EDGAR current filings."""
    print("Acquiring sec-edgar...", end=" ", flush=True)
    url = "https://www.sec.gov/cgi-bin/browse-edgar?action=getcurrent&output=atom&count=50"
    body = _fetch(url).decode("utf-8", errors="replace")
    records, now = [], datetime.now(timezone.utc)
    for entry in re.findall(r'<entry>(.*?)</entry>', body, re.DOTALL):
        title = (re.search(r'<title[^>]*>(.*?)</title>', entry, re.DOTALL) or [None,""])[1].strip()
        link = (re.search(r'<link[^>]*href="([^"]+)"', entry) or [None,""])[1]
        date = (re.search(r'<updated>(.*?)</updated>', entry) or [None,""])[1].strip()
        body_txt = f"Title: {title}\nDate: {date}\nLink: {link}"
        ch = _content_hash(body_txt[:500])
        rec = RawIntakeRecord(intake_id=_intake_id("sec", _content_hash(title)[:16], ch),
                              source_id="sec-edgar", source_url=link,
                              raw_body=body_txt[:500], retrieved_at=now,
                              parser_version="sec-edgar-1.0")
        records.append(rec)
    print(f"{len(records)} records")
    return records

def acquire_binance_ohlcv(start: datetime, end: datetime):
    """Acquire Binance OHLCV outcome data."""
    print("Acquiring binance outcomes...", end=" ", flush=True)
    start_ms = int(start.timestamp() * 1000)
    end_ms = int(end.timestamp() * 1000)
    url = f"https://api.binance.com/api/v3/klines?symbol=BTCUSDT&interval=1h&startTime={start_ms}&endTime={end_ms}&limit=1000"
    data = json.loads(_fetch(url))
    records, now = [], datetime.now(timezone.utc)
    for k in data:
        ts = int(k[0])
        dt = datetime.fromtimestamp(ts/1000, tz=timezone.utc)
        body_txt = json.dumps({"open":k[1],"high":k[2],"low":k[3],"close":k[4],"volume":k[5],"time":dt.isoformat()}, sort_keys=True)
        ch = _content_hash(body_txt[:500])
        rec = RawIntakeRecord(intake_id=_intake_id("binance", f"btc-{ts//3600000}", ch),
                              source_id="binance-public",
                              source_url=f"https://api.binance.com/api/v3/klines?symbol=BTCUSDT&interval=1h&startTime={ts}",
                              raw_body=body_txt[:500], retrieved_at=now,
                              parser_version="binance-klines-1.0")
        records.append(rec)
    print(f"{len(records)} records")
    return records


def parse_ts(s: str) -> Optional[datetime]:
    if not s: return None
    s = s.replace("<![CDATA[","").replace("]]>","").strip()
    for fmt in ["%Y-%m-%dT%H:%M:%S.%f","%Y-%m-%dT%H:%M:%S","%Y-%m-%d","%a, %d %b %Y %H:%M:%S %z","%a, %d %b %Y %H:%M:%S %Z"]:
        try: return datetime.strptime(s, fmt)
        except: pass
    try: return datetime.fromisoformat(s)
    except: pass
    return None


def build_pilot():
    print("=" * 50)
    print("WP-02 Real Historical Pilot Builder")
    print("=" * 50)

    # Acquire all
    raw: List[RawIntakeRecord] = []
    for acq_name, acq_fn in [("cisa-alerts", acquire_cisa), ("federal-reserve", acquire_fed),
                              ("nvd-nist", lambda: acquire_nvd(120)),
                              ("kraken-status", acquire_kraken), ("sec-edgar", acquire_sec)]:
        try:
            raw += acq_fn()
        except Exception as e:
            print(f"  SKIPPED ({e})")
    print(f"\nTotal raw intake: {len(raw)}")

    # Build cases
    now = datetime.now(timezone.utc)
    cases = []
    evidence = []
    seen_ids = set()

    for rec in raw:
        sid = rec.source_id
        family = SOURCE_FAMILY.get(sid, "unknown")
        asset = SOURCE_ASSET.get(sid, "BTC")
        auth, fp, ha = SOURCE_AUTH.get(sid, ("unknown","unknown","UNKNOWN"))
        
        # Parse source-native timestamp
        raw_body = rec.raw_body
        ts_str = None
        if sid == "nvd-nist":
            m = re.search(r"Published: ([^\n]+)", raw_body)
            ts_str = m.group(1).strip() if m else None
        elif sid == "cisa-alerts":
            m = re.search(r"DateAdded: ([^\n]+)", raw_body)
            ts_str = m.group(1).strip() if m else None
        elif sid in ("federal-reserve", "sec-edgar"):
            m = re.search(r"Date: ([^\n]+)", raw_body)
            ts_str = m.group(1).strip() if m else None
        elif sid == "kraken-status":
            m = re.search(r"Created: ([^\n]+)", raw_body)
            ts_str = m.group(1).strip() if m else None
        
        event_dt = parse_ts(ts_str) if ts_str else rec.retrieved_at
        if event_dt and event_dt.tzinfo is None:
            event_dt = event_dt.replace(tzinfo=timezone.utc)

        # Build evidence
        ev_id = hashlib.sha256(f"{sid}:{rec.intake_id}".encode()).hexdigest()[:20]
        
        ev = NormalizedEvidenceRecord(
            evidence_id=ev_id, source_id=sid, source_url=rec.source_url,
            authority=auth, fact_permission=fp,
            publication_time=event_dt, effective_time=event_dt,
            first_seen_at=rec.retrieved_at, retrieval_time=rec.retrieved_at,
            assessment_time=rec.retrieved_at,
            normalized_fact=rec.raw_body[:1000], short_excerpt=rec.raw_body[:500],
            parser_version=rec.parser_version,
        )
        ev.content_hash = ev.compute_content_hash()
        evidence.append(ev)

        # Build case
        title = raw_body[:80].split('\n')[0] if raw_body else "untitled"
        case_id = f"{sid}-{rec.intake_id[:16]}"
        
        if case_id in seen_ids:
            continue
        seen_ids.add(case_id)
        
        qual = QualificationState.QUALIFIED
        reject_reason = None
        
        if sid in ("sec-edgar", "kraken-status") and ts_str is None:
            qual = QualificationState.INCOMPLETE
            reject_reason = "no_source_native_timestamp"
        
        case = {
            "case_id": case_id, "intake_id": rec.intake_id,
            "qualification": qual.value, "event_family": family,
            "title": title,
            "event_time": event_dt.isoformat() if event_dt else None,
            "asset": asset, "source_id": sid,
            "source_url": rec.source_url, "authority": auth,
            "fact_permission": fp, "historical_authority": ha,
            "collection_retrieved_at": rec.retrieved_at.isoformat(),
            "publication_time": event_dt.isoformat() if event_dt else None,
            "first_seen_at": rec.retrieved_at.isoformat(),
            "retrieval_time": rec.retrieved_at.isoformat(),
            "assessment_time": rec.retrieved_at.isoformat(),
            "evidence_refs": [ev_id],
            "outcome_refs": [],
            "market_regime": "unknown", "regime_rule": "pilot-1.0",
            "split_label": None,
            "rejection_reason": reject_reason,
        }
        cases.append(case)

    # Split allocation
    qualified = [c for c in cases if c.get("qualification") == "QUALIFIED"]
    case_times = []
    for c in qualified:
        et = c.get("event_time")
        if et:
            try: case_times.append((c["case_id"], datetime.fromisoformat(et)))
            except: pass
    case_times.sort(key=lambda x: x[1])
    
    if len(case_times) >= 5:
        n = len(case_times)
        bi = max(1, int(n * 0.6))
        di = max(bi + 1, int(n * 0.8))
        bc = case_times[bi-1][1]
        dc = case_times[di-1][1]
        
        for c in qualified:
            ct = None
            for cid, dt in case_times:
                if cid == c["case_id"]: ct = dt; break
            if ct:
                if ct <= bc: c["split_label"] = "BUILD"
                elif ct <= dc: c["split_label"] = "DEVELOPMENT"
                else: c["split_label"] = "BLIND"
            else:
                c["split_label"] = "BUILD"
    
    # Outcomes
    print("\nAcquiring outcome data...", end=" ", flush=True)
    try:
        # Get OHLCV for a broad range to cover all cases
        all_dates = [datetime.fromisoformat(c["event_time"]) for c in qualified if c.get("event_time")]
        if all_dates:
            min_dt = min(all_dates)
            max_dt = max(all_dates)
            ohlcv = acquire_binance_ohlcv(min_dt - timedelta(days=1), max_dt + timedelta(days=8))
            
            # Build price map
            price_map = {}
            for r in ohlcv:
                try:
                    d = json.loads(r.raw_body)
                    price_map[d["time"]] = {"open": float(d["open"]), "close": float(d["close"]),
                                            "high": float(d["high"]), "low": float(d["low"]),
                                            "volume": float(d["volume"])}
                except: pass
            
            outcomes = []
            for c in qualified:
                et = c.get("event_time")
                if not et: continue
                try:
                    event_dt = datetime.fromisoformat(et)
                except: continue
                
                ob = OutcomeBuilder(provider="binance", instrument="BTCUSDT")
                for interval, dur in [("1h", timedelta(hours=1)), ("6h", timedelta(hours=6)),
                                      ("24h", timedelta(hours=24)), ("3d", timedelta(days=3)),
                                      ("7d", timedelta(days=7))]:
                    ct_et = event_dt + dur
                    # Find closest price
                    close_price = None
                    for ts_key in sorted(price_map.keys()):
                        try:
                            ts_dt = datetime.fromisoformat(ts_key)
                            if ts_dt >= ct_et - timedelta(hours=1) and ts_dt <= ct_et + timedelta(hours=1):
                                close_price = price_map[ts_key]
                                break
                        except: pass
                    
                    oid = f"{c['case_id']}_{interval}"
                    obs = {
                        "outcome_id": oid, "case_id": c["case_id"],
                        "provider": "binance", "instrument": "BTCUSDT",
                        "interval": interval,
                        "open_time": event_dt.isoformat(),
                        "close_time": ct_et.isoformat(),
                        "retrieval_time": now.isoformat(),
                        "open_price": close_price["open"] if close_price else None,
                        "close_price": close_price["close"] if close_price else None,
                        "high_price": close_price["high"] if close_price else None,
                        "low_price": close_price["low"] if close_price else None,
                        "volume": close_price["volume"] if close_price else None,
                        "return_pct": None,
                        "direction": None,
                        "content_hash": hashlib.sha256(f"{oid}:{ct_et.isoformat()}:{close_price}".encode()).hexdigest()[:20] if close_price else "",
                        "missing_data_reason": None if close_price else "price_data_unavailable",
                    }
                    outcomes.append(obs)
                    c.setdefault("outcome_refs", [])
                    c["outcome_refs"].append(oid)
            
            print(f"{len(outcomes)} outcome records")
    except Exception as e:
        print(f"Outcome error: {e}")
        outcomes = []

    # Write artifacts
    print("\n=== Writing artifacts ===")
    os.makedirs(ARTIFACT_DIR, exist_ok=True)
    
    write_jsonl(os.path.join(ARTIFACT_DIR, "cases.jsonl"), cases)
    
    ev_list = [{"evidence_id": e.evidence_id, "source_id": e.source_id,
                "source_url": e.source_url, "authority": e.authority,
                "fact_permission": e.fact_permission,
                "publication_time": e.publication_time.isoformat() if e.publication_time else None,
                "first_seen_at": e.first_seen_at.isoformat() if e.first_seen_at else None,
                "retrieval_time": e.retrieval_time.isoformat() if e.retrieval_time else None,
                "assessment_time": e.assessment_time.isoformat() if e.assessment_time else None,
                "normalized_fact": e.normalized_fact, "content_hash": e.content_hash,
                "parser_version": e.parser_version} for e in evidence]
    write_jsonl(os.path.join(ARTIFACT_DIR, "evidence.jsonl"), ev_list)
    
    _outcomes = outcomes if 'outcomes' in dir() else []
    write_jsonl(os.path.join(ARTIFACT_DIR, "outcome_windows.jsonl"), _outcomes)
    write_jsonl(os.path.join(ARTIFACT_DIR, "correction_chains.jsonl"), [])
    
    # Rejected records
    rejected = [c for c in cases if c.get("qualification") != "QUALIFIED"]
    rej_path = os.path.join(ARTIFACT_DIR, "rejected_records.jsonl")
    existing_rej = []
    if os.path.exists(rej_path):
        with open(rej_path) as f:
            for line in f:
                line = line.strip()
                if line: existing_rej.append(json.loads(line))
    for r in rejected:
        existing_rej.append({"intake_id": r.get("case_id",""), "case_id": r.get("case_id"),
                             "rejection_reason": r.get("rejection_reason",""), "qualification": "QUARANTINED",
                             "source_id": r.get("source_id","")})
    with open(rej_path, "w") as f:
        for r in existing_rej:
            f.write(json.dumps(r, sort_keys=True) + "\n")
    
    # Reports
    family_dist = {}
    reg_dist = {}
    split_dist = {}
    for c in qualified:
        f = c.get("event_family","unknown")
        family_dist[f] = family_dist.get(f, 0) + 1
        r = c.get("market_regime","unknown")
        reg_dist[r] = reg_dist.get(r, 0) + 1
        s = c.get("split_label","UNALLOCATED")
        split_dist[s] = split_dist.get(s, 0) + 1
    
    manifest = {
        "build_id": "pilot-001", "corpus_version": "1.0",
        "total_accepted_cases": len(qualified),
        "total_intake_records": len(cases),
        "rejected_records": len(rejected),
        "family_distribution": family_dist,
        "regime_distribution": reg_dist,
        "split_distribution": split_dist,
        "artifact_hashes": {a: file_sha256(os.path.join(ARTIFACT_DIR, a)) 
                           for a in ["cases.jsonl","evidence.jsonl","outcome_windows.jsonl","correction_chains.jsonl"]
                           if os.path.exists(os.path.join(ARTIFACT_DIR, a))},
        "root_hash": build_manifest_hash(ARTIFACT_DIR),
    }
    write_yaml(os.path.join(ARTIFACT_DIR, "build_manifest.json"), manifest)
    
    split_manifest = {"build_id": "pilot-001", "split_boundary_version": "1.0",
                      "split_distribution": split_dist,
                      "total_cases": len(cases), "total_qualified": len(qualified)}
    write_yaml(os.path.join(ARTIFACT_DIR, "split_manifest.json"), split_manifest)
    
    quality = {"build_type": "pilot", "target_cases": 120, "accepted_cases": len(qualified),
               "schema_version": "1.0", "status": "BUILT"}
    write_yaml(os.path.join(ARTIFACT_DIR, "quality_report.json"), quality)
    
    print(f"\n=== Pilot Summary ===")
    print(f"Qualified: {len(qualified)}")
    for fam in ["regulatory","corporate","macro","technology","market","security"]:
        cnt = family_dist.get(fam, 0)
        print(f"  {fam}: {cnt}")
    print(f"Splits: {split_dist}")
    print(f"Root hash: {manifest['root_hash']}")


if __name__ == "__main__":
    build_pilot()
