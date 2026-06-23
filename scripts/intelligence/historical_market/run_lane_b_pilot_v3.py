import argparse
import gzip
import hashlib
import json
import os
import sqlite3
import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

# Constants

H = {"1h": 3600, "4h": 14400, "24h": 86400}
CA = ["BTCUSDT", "ETHUSDT"]
XS = [
    "yahoo_sp500_index",
    "yahoo_nasdaq_composite",
    "yahoo_gold_futures",
    "yahoo_us_dollar_index",
    "yahoo_us10y_yield",
    "yahoo_us5y_yield",
    "yahoo_us30y_yield",
    "yahoo_vix_index",
    "yahoo_silver_futures",
    "yahoo_wti_crude",
]
DE = 0.001
VER = "3.0.0"

SQLITE_TABLE_PILOT = "pilot_v3_alignment"
SQLITE_TABLE_WINDOWS = "pilot_v3_event_asset_windows"
SQLITE_TABLE_LABELS = "pilot_v3_reaction_labels"
SQLITE_TABLE_CROSS_ASSET = "pilot_v3_cross_asset_context"
SQLITE_TABLE_FUNDING = "pilot_v3_funding_context"

def LE(p):
    events = []
    with open(p, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                events.append(json.loads(line))
    return events


def LB(p):
    index = {}
    with gzip.open(p, "rt", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            bar = json.loads(line)
            key = bar.get("instrument_id", "") + "|" + bar.get("interval", "")
            index.setdefault(key, []).append(bar)
    for key in index:
        index[key].sort(key=lambda b: b.get("open_time_utc", ""))
    return index


def LD(p):
    records = []
    with gzip.open(p, "rt", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


def PT(s):
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    return datetime.fromisoformat(s)


def FPB(b, ev):
    et = PT(ev.get("event_time_utc", ev.get("actual_release_at_utc", "")))
    candidate = None
    for bar in b:
        ct = PT(bar["close_time_utc"])
        if ct <= et:
            candidate = bar
        else:
            break
    return candidate


def FEB(b, ev):
    et = PT(ev.get("event_time_utc", ev.get("actual_release_at_utc", "")))
    for bar in b:
        ct = PT(bar["close_time_utc"])
        if ct > et:
            return bar
    return None


def FPOB(b, tv):
    for bar in b:
        ct = PT(bar["close_time_utc"])
        if ct >= tv:
            return bar
    return None


def CR(pre, post):
    if pre == 0.0:
        return 0.0
    return (post / pre - 1.0) * 100.0


def DR(r):
    if r > DE:
        return "positive"
    elif r < -DE:
        return "negative"
    return "neutral"


def MSG(evts):
    ids = sorted(e.get("event_id", "") for e in evts)
    combined = "|".join(ids)
    return hashlib.sha256(combined.encode("utf-8")).hexdigest()

def main(ep, bp, dp, od, sp):
    events = LE(ep)
    bars_index = LB(bp)
    derivatives = LD(dp)

    output_dir = Path(od)
    output_dir.mkdir(parents=True, exist_ok=True)

    sqlite_dir = os.path.dirname(sp)
    if sqlite_dir:
        os.makedirs(sqlite_dir, exist_ok=True)

    group_id = MSG(events)
    group_size = len(events)

    deriv_index = {}
    for snap in derivatives:
        sym = snap.get("symbol", "")
        deriv_index.setdefault(sym, []).append(snap)
    for sym in deriv_index:
        deriv_index[sym].sort(key=lambda s: s.get("observed_at_utc", ""))

    windows = []
    labels = []
    cross_asset = []
    funding = []

    for event in events:
        event_id = event.get("event_id", "")
        event_family = event.get("event_family", "")
        event_time_str = event.get("event_time_utc", event.get("actual_release_at_utc", ""))
        if not event_time_str:
            continue
        event_time = PT(event_time_str)

        for asset in CA:
            instrument_id = "binance_spot_" + asset.lower()
            bar_key = instrument_id + "|1h"
            bars = bars_index.get(bar_key, [])
            if not bars:
                continue

            pre_bar = FPB(bars, event)
            if pre_bar is None:
                continue

            pre_close = pre_bar.get("close", 0.0)
            baseline_time_str = pre_bar.get("close_time_utc", "")
            baseline_time = PT(baseline_time_str)
            baseline_offset_min = (baseline_time - event_time).total_seconds() / 60.0

            for hn, hm in H.items():
                target_time = event_time + timedelta(seconds=hm)
                post_bar = FPOB(bars, target_time)
                if post_bar is None:
                    continue

                post_close = post_bar.get("close", 0.0)
                post_bar_time_str = post_bar.get("close_time_utc", "")
                post_bar_time = PT(post_bar_time_str)
                endpoint_offset_min = (post_bar_time - event_time).total_seconds() / 60.0

                span_min = endpoint_offset_min - baseline_offset_min
                nominal_min = hm / 60.0
                err_min = endpoint_offset_min - nominal_min

                return_pct = CR(pre_close, post_close)
                direction = DR(return_pct)

                before_flag = 1 if baseline_offset_min < 0 else 0

                window_id = hashlib.sha256(
                    (event_id + ":" + instrument_id + ":" + hn).encode("utf-8")
                ).hexdigest()

                eep = (event_time + timedelta(seconds=hm)).isoformat()

                window_record = {
                    "wid": window_id,
                    "eid": event_id,
                    "ef": event_family,
                    "et": event_time_str,
                    "ii": instrument_id,
                    "a": asset,
                    "hn": hn,
                    "hm": hm,
                    "pc": pre_close,
                    "poc": post_close,
                    "rp": round(return_pct, 6),
                    "d": direction,
                    "bt": baseline_time_str,
                    "bo": round(baseline_offset_min, 4),
                    "pot": post_bar_time_str,
                    "eo": round(endpoint_offset_min, 4),
                    "sp": round(span_min, 4),
                    "err": round(err_min, 4),
                    "bf": before_flag,
                    "pc_": "coarse_hourly_alignment",
                    "eep": eep,
                    "gid": group_id,
                    "gsz": group_size,
                }
                windows.append(window_record)

                label_id = hashlib.sha256(
                    ("label:" + event_id + ":" + instrument_id + ":" + hn).encode("utf-8")
                ).hexdigest()
                label_record = {
                    "contract_name": "MarketReactionLabelV3",
                    "schema_version": VER,
                    "label_id": label_id,
                    "window_id": window_id,
                    "event_id": event_id,
                    "instrument_id": instrument_id,
                    "symbol": asset,
                    "event_time_utc": event_time_str,
                    "horizon": hn,
                    "return_pct": round(return_pct, 6),
                    "direction": direction,
                    "label_availability": "full",
                    "data_quality": "computed_from_archived_bars",
                    "quality_flags": [],
                    "calculation_version": VER,
                }
                labels.append(label_record)

    for event in events:
        event_id = event.get("event_id", "")
        event_time_str = event.get("event_time_utc", event.get("actual_release_at_utc", ""))
        if not event_time_str:
            continue
        event_time = PT(event_time_str)

        for series_name in XS:
            bar_key = series_name + "|1h"
            bars = bars_index.get(bar_key, [])

            if not bars:
                ca_record = {
                    "event_id": event_id,
                    "event_time_utc": event_time_str,
                    "series_name": series_name,
                    "pre_bar_close": None,
                    "post_bar_close": None,
                    "pre_bar_close_time_utc": None,
                    "post_bar_close_time_utc": None,
                }
                cross_asset.append(ca_record)
                continue

            pre_bar = FPB(bars, event)
            post_bar = FPOB(bars, event_time)

            ca_record = {
                "event_id": event_id,
                "event_time_utc": event_time_str,
                "series_name": series_name,
                "pre_bar_close": pre_bar.get("close") if pre_bar else None,
                "post_bar_close": post_bar.get("close") if post_bar else None,
                "pre_bar_close_time_utc": (
                    pre_bar.get("close_time_utc") if pre_bar else None
                ),
                "post_bar_close_time_utc": (
                    post_bar.get("close_time_utc") if post_bar else None
                ),
            }
            cross_asset.append(ca_record)

    for event in events:
        event_id = event.get("event_id", "")
        event_time_str = event.get("event_time_utc", event.get("actual_release_at_utc", ""))
        if not event_time_str:
            continue
        event_time = PT(event_time_str)

        for asset in CA:
            instrument_id = "binance_spot_" + asset.lower()
            snaps = deriv_index.get(asset, [])
            funding_rate = None
            for snap in snaps:
                ot = PT(snap["observed_at_utc"])
                if ot <= event_time:
                    fr = snap.get("funding_rate")
                    if fr is not None:
                        funding_rate = fr
                else:
                    break

            funding_record = {
                "event_id": event_id,
                "event_time_utc": event_time_str,
                "instrument_id": instrument_id,
                "symbol": asset,
                "funding_rate": funding_rate,
            }
            funding.append(funding_record)

    windows_path = os.path.join(output_dir, "event_asset_windows_v3.jsonl")
    with open(windows_path, "w", encoding="utf-8") as f:
        for rec in windows:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    labels_path = os.path.join(output_dir, "market_reaction_labels_v3.jsonl")
    with open(labels_path, "w", encoding="utf-8") as f:
        for rec in labels:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    cross_asset_path = os.path.join(output_dir, "cross_asset_context_v3.jsonl")
    with open(cross_asset_path, "w", encoding="utf-8") as f:
        for rec in cross_asset:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    funding_path = os.path.join(output_dir, "funding_context_v3.jsonl")
    with open(funding_path, "w", encoding="utf-8") as f:
        for rec in funding:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    print("Written " + str(len(windows)) + " event windows to " + windows_path)
    print("Written " + str(len(labels)) + " reaction labels to " + labels_path)
    print("Written " + str(len(cross_asset)) + " cross-asset records to " + cross_asset_path)
    print("Written " + str(len(funding)) + " funding records to " + funding_path)

    conn = sqlite3.connect(sp)
    cursor = conn.cursor()

    cursor.execute("DROP TABLE IF EXISTS " + SQLITE_TABLE_PILOT)
    cursor.execute("DROP TABLE IF EXISTS " + SQLITE_TABLE_WINDOWS)
    cursor.execute("DROP TABLE IF EXISTS " + SQLITE_TABLE_LABELS)
    cursor.execute("DROP TABLE IF EXISTS " + SQLITE_TABLE_CROSS_ASSET)
    cursor.execute("DROP TABLE IF EXISTS " + SQLITE_TABLE_FUNDING)

    cursor.execute(
        "CREATE TABLE "
        + SQLITE_TABLE_PILOT
        + " ("
        + "run_id INTEGER PRIMARY KEY AUTOINCREMENT, "
        + "pilot_version TEXT NOT NULL, "
        + "started_at_utc TEXT NOT NULL, "
        + "event_count INTEGER NOT NULL, "
        + "asset_count INTEGER NOT NULL, "
        + "horizon_count INTEGER NOT NULL, "
        + "expected_windows INTEGER NOT NULL, "
        + "actual_windows INTEGER NOT NULL, "
        + "expected_labels INTEGER NOT NULL, "
        + "actual_labels INTEGER NOT NULL, "
        + "report_generated_at_utc TEXT NOT NULL"
        + ")"
    )

    cursor.execute(
        "CREATE TABLE "
        + SQLITE_TABLE_WINDOWS
        + " ("
        + "wid TEXT PRIMARY KEY, "
        + "eid TEXT NOT NULL, "
        + "ef TEXT, "
        + "et TEXT NOT NULL, "
        + "ii TEXT NOT NULL, "
        + "a TEXT NOT NULL, "
        + "hn TEXT NOT NULL, "
        + "hm INTEGER NOT NULL, "
        + "pc REAL, "
        + "poc REAL, "
        + "rp REAL, "
        + "d TEXT, "
        + "bt TEXT, "
        + "bo REAL, "
        + "pot TEXT, "
        + "eo REAL, "
        + "sp REAL, "
        + "err REAL, "
        + "bf INTEGER, "
        + "pc_ TEXT, "
        + "eep TEXT, "
        + "gid TEXT, "
        + "gsz INTEGER"
        + ")"
    )

    cursor.execute(
        "CREATE TABLE "
        + SQLITE_TABLE_LABELS
        + " ("
        + "label_id TEXT PRIMARY KEY, "
        + "window_id TEXT, "
        + "event_id TEXT NOT NULL, "
        + "instrument_id TEXT NOT NULL, "
        + "symbol TEXT NOT NULL, "
        + "event_time_utc TEXT NOT NULL, "
        + "horizon TEXT NOT NULL, "
        + "return_pct REAL, "
        + "direction TEXT, "
        + "label_availability TEXT"
        + ")"
    )

    cursor.execute(
        "CREATE TABLE "
        + SQLITE_TABLE_CROSS_ASSET
        + " ("
        + "id INTEGER PRIMARY KEY AUTOINCREMENT, "
        + "event_id TEXT NOT NULL, "
        + "event_time_utc TEXT NOT NULL, "
        + "series_name TEXT NOT NULL, "
        + "pre_bar_close REAL, "
        + "post_bar_close REAL, "
        + "UNIQUE(event_id, series_name)"
        + ")"
    )

    cursor.execute(
        "CREATE TABLE "
        + SQLITE_TABLE_FUNDING
        + " ("
        + "id INTEGER PRIMARY KEY AUTOINCREMENT, "
        + "event_id TEXT NOT NULL, "
        + "event_time_utc TEXT NOT NULL, "
        + "instrument_id TEXT NOT NULL, "
        + "symbol TEXT NOT NULL, "
        + "funding_rate REAL, "
        + "UNIQUE(event_id, instrument_id)"
        + ")"
    )

    insert_window_sql = (
        "INSERT OR IGNORE INTO "
        + SQLITE_TABLE_WINDOWS
        + " (wid, eid, ef, et, ii, a, hn, hm, pc, poc, rp, d, "
        + "bt, bo, pot, eo, sp, err, bf, pc_, eep, gid, gsz) "
        + "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, "
        + "?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
    )
    for rec in windows:
        cursor.execute(
            insert_window_sql,
            (
                rec["wid"], rec["eid"], rec["ef"], rec["et"], rec["ii"],
                rec["a"], rec["hn"], rec["hm"], rec["pc"], rec["poc"],
                rec["rp"], rec["d"], rec["bt"], rec["bo"], rec["pot"],
                rec["eo"], rec["sp"], rec["err"], rec["bf"], rec["pc_"],
                rec["eep"], rec["gid"], rec["gsz"],
            ),
        )

    insert_label_sql = (
        "INSERT OR IGNORE INTO "
        + SQLITE_TABLE_LABELS
        + " (label_id, window_id, event_id, instrument_id, symbol, "
        + "event_time_utc, horizon, return_pct, direction, label_availability) "
        + "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
    )
    for rec in labels:
        cursor.execute(
            insert_label_sql,
            (
                rec["label_id"], rec.get("window_id", ""), rec["event_id"],
                rec["instrument_id"], rec["symbol"], rec["event_time_utc"],
                rec["horizon"], rec["return_pct"], rec["direction"],
                rec.get("label_availability", "full"),
            ),
        )

    insert_ca_sql = (
        "INSERT OR IGNORE INTO "
        + SQLITE_TABLE_CROSS_ASSET
        + " (event_id, event_time_utc, series_name, pre_bar_close, post_bar_close) "
        + "VALUES (?, ?, ?, ?, ?)"
    )
    for rec in cross_asset:
        cursor.execute(
            insert_ca_sql,
            (rec["event_id"], rec["event_time_utc"], rec["series_name"],
             rec["pre_bar_close"], rec["post_bar_close"]),
        )

    insert_funding_sql = (
        "INSERT OR IGNORE INTO "
        + SQLITE_TABLE_FUNDING
        + " (event_id, event_time_utc, instrument_id, symbol, funding_rate) "
        + "VALUES (?, ?, ?, ?, ?)"
    )
    for rec in funding:
        cursor.execute(
            insert_funding_sql,
            (rec["event_id"], rec["event_time_utc"], rec["instrument_id"],
             rec["symbol"], rec["funding_rate"]),
        )

    cursor.execute("CREATE INDEX IF NOT EXISTS idx_v3_windows_eid ON " + SQLITE_TABLE_WINDOWS + "(eid)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_v3_windows_a ON " + SQLITE_TABLE_WINDOWS + "(a)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_v3_labels_eid ON " + SQLITE_TABLE_LABELS + "(event_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_v3_labels_symbol ON " + SQLITE_TABLE_LABELS + "(symbol)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_v3_ca_eid ON " + SQLITE_TABLE_CROSS_ASSET + "(event_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_v3_funding_eid ON " + SQLITE_TABLE_FUNDING + "(event_id)")

    conn.commit()

    actual_windows = cursor.execute("SELECT COUNT(*) FROM " + SQLITE_TABLE_WINDOWS).fetchone()[0]
    actual_labels = cursor.execute("SELECT COUNT(*) FROM " + SQLITE_TABLE_LABELS).fetchone()[0]
    actual_cross_asset = cursor.execute("SELECT COUNT(*) FROM " + SQLITE_TABLE_CROSS_ASSET).fetchone()[0]
    actual_funding = cursor.execute("SELECT COUNT(*) FROM " + SQLITE_TABLE_FUNDING).fetchone()[0]

    expected_windows = len(windows)
    expected_labels = len(labels)

    assert actual_windows == expected_windows, (
        "Windows count mismatch: expected " + str(expected_windows) + " got " + str(actual_windows)
    )
    assert actual_labels == expected_labels, (
        "Labels count mismatch: expected " + str(expected_labels) + " got " + str(actual_labels)
    )

    integrity_issues = []

    for rec in windows:
        if not rec["wid"] or not rec["eid"] or not rec["ii"]:
            integrity_issues.append("Window " + str(rec.get("wid", "")) + " has missing critical field")

    distinct_pairs = set()
    for w in windows:
        distinct_pairs.add((w["eid"], w["ii"]))
    expected_distinct = len(events) * len(CA)
    if len(distinct_pairs) != expected_distinct:
        integrity_issues.append(
            "Distinct (event, instrument) pairs: expected " + str(expected_distinct) + " got " + str(len(distinct_pairs))
        )

    expected_cross_asset = len(events) * len(XS)
    if len(cross_asset) != expected_cross_asset:
        integrity_issues.append(
            "Cross-asset records: expected " + str(expected_cross_asset) + " got " + str(len(cross_asset))
        )

    expected_funding = len(events) * len(CA)
    if len(funding) != expected_funding:
        integrity_issues.append(
            "Funding records: expected " + str(expected_funding) + " got " + str(len(funding))
        )

    if integrity_issues:
        print("Integrity issues found:")
        for issue in integrity_issues:
            print("  - " + issue)
    else:
        print("All integrity checks passed.")

    started_at = datetime.utcnow().isoformat()
    report_generated_at = started_at

    cursor.execute(
        "INSERT INTO " + SQLITE_TABLE_PILOT + " "
        + "(pilot_version, started_at_utc, event_count, asset_count, "
        + "horizon_count, expected_windows, actual_windows, "
        + "expected_labels, actual_labels, report_generated_at_utc) "
        + "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (VER, started_at, len(events), len(CA), len(H),
         expected_windows, actual_windows, expected_labels, actual_labels,
         report_generated_at),
    )
    conn.commit()
    conn.close()

    print("SQLite database written to " + sp)

    report = {
        "pilot_version": VER,
        "started_at_utc": started_at,
        "report_generated_at_utc": report_generated_at,
        "event_count": len(events),
        "asset_count": len(CA),
        "horizons": list(H.keys()),
        "expected_windows": expected_windows,
        "actual_windows": actual_windows,
        "expected_labels": expected_labels,
        "actual_labels": actual_labels,
        "cross_asset_records": len(cross_asset),
        "funding_records": len(funding),
        "assertions_passed": len(integrity_issues) == 0,
        "integrity_issues": integrity_issues,
        "output_files": {
            "event_windows": str(windows_path),
            "reaction_labels": str(labels_path),
            "cross_asset_context": str(cross_asset_path),
            "funding_context": str(funding_path),
            "sqlite_database": str(sp),
        },
    }

    report_json_path = os.path.join(output_dir, "pilot_alignment_report_v3.json")
    with open(report_json_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    report_md_path = os.path.join(output_dir, "pilot_alignment_report_v3.md")
    with open(report_md_path, "w", encoding="utf-8") as f:
        f.write("# Lane B Pilot v3 Alignment Report" + chr(92) + chr(110))
        f.write(chr(92) + chr(110))
        f.write("**Pilot Version:** " + VER + chr(92) + chr(110))
        f.write(chr(92) + chr(110))
        f.write("## Summary" + chr(92) + chr(110))
        f.write(chr(92) + chr(110))
        f.write("- **Events:** " + str(len(events)) + chr(92) + chr(110))
        f.write("- **Assets:** " + str(len(CA)) + chr(92) + chr(110))
        f.write("- **Horizons:** " + str(list(H.keys())) + chr(92) + chr(110))
        f.write("- **Expected Windows:** " + str(expected_windows) + chr(92) + chr(110))
        f.write("- **Actual Windows:** " + str(actual_windows) + chr(92) + chr(110))
        f.write("- **Expected Labels:** " + str(expected_labels) + chr(92) + chr(110))
        f.write("- **Actual Labels:** " + str(actual_labels) + chr(92) + chr(110))
        f.write("- **Cross-Asset Records:** " + str(len(cross_asset)) + chr(92) + chr(110))
        f.write("- **Funding Records:** " + str(len(funding)) + chr(92) + chr(110))
        f.write("- **Assertions Passed:** " + str(len(integrity_issues) == 0) + chr(92) + chr(110))
        f.write(chr(92) + chr(110))
        if integrity_issues:
            f.write("## Integrity Issues" + chr(92) + chr(110))
            f.write(chr(92) + chr(110))
            for issue in integrity_issues:
                f.write("- " + issue + chr(92) + chr(110))
        f.write(chr(92) + chr(110))
        f.write("## Output Files" + chr(92) + chr(110))
        f.write(chr(92) + chr(110))
        for k, v in report["output_files"].items():
            f.write("- **" + k + ":** " + v + chr(92) + chr(110))
    print("JSON report written to " + report_json_path)
    print("MD report written to " + report_md_path)

    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Lane B Pilot v3")
    parser.add_argument("--ep", help="Events JSONL")
    parser.add_argument("--bp", help="Bars gzipped JSONL")
    parser.add_argument("--dp", help="Derivatives gzipped JSONL")
    parser.add_argument("--od", help="Output directory")
    parser.add_argument("--sp", help="SQLite path")
    args = parser.parse_args()
    report = main(args.ep, args.bp, args.dp, args.od, args.sp)
    print(json.dumps(report, indent=2, ensure_ascii=False))
