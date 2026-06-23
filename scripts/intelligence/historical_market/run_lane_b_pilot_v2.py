import gzip
import hashlib
import json
import os
import sqlite3
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Optional

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from market_radar.intelligence.acquisition.historical_market.contracts import utc_now


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------


DIRECTION_EPSILON = 0.001
PILOT_VERSION = "pilot_v2"


HORIZONS_SECONDS = {
    "1h": 3600,
    "4h": 14400,
    "24h": 86400,
}


CRYPTO_ASSETS = ["BTCUSDT", "ETHUSDT"]


CROSS_ASSET_SERIES = [
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


SQLITE_TABLE_PILOT = "pilot_v2_alignment"
SQLITE_TABLE_WINDOWS = "pilot_v2_event_asset_windows"
SQLITE_TABLE_LABELS = "pilot_v2_reaction_labels"
SQLITE_TABLE_CROSS_ASSET = "pilot_v2_cross_asset_context"
SQLITE_TABLE_FUNDING = "pilot_v2_funding_context"

# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------


def parse_arguments() -> Any:
    """Parse command-line arguments."""
    import argparse

    base = os.path.join("data", "intelligence", "historical_market")
    events_default = os.path.join(
        base, "pilot_v2", "lane_a_input", "macro_release_events_v1.jsonl"
    )
    bars_default = os.path.join(base, "normalized", "market_bars_v1.jsonl.gz")
    derivatives_default = os.path.join(
        base, "normalized", "derivative_snapshots_v1.jsonl.gz"
    )
    output_default = os.path.join(base, "pilot_v2")
    sqlite_default = os.path.join(base, "pilot_v2", "../indexes/historical_market_v1.sqlite")

    parser = argparse.ArgumentParser(
        description="Lane B Pilot v2 -- event market alignment with cross-asset context"
    )
    parser.add_argument("--ep", default=events_default,
                        help="Path to macro release events JSONL file")
    parser.add_argument("--bp", default=bars_default,
                        help="Path to market bars gzipped JSONL file")
    parser.add_argument("--dp", default=derivatives_default,
                        help="Path to derivative snapshots gzipped JSONL file")
    parser.add_argument("--od", default=output_default,
                        help="Output directory for JSONL results and report")
    parser.add_argument("--sp", default=sqlite_default,
                        help="Path to SQLite database file")
    return parser.parse_args()

# ---------------------------------------------------------------------------
# Data loading helpers
# ---------------------------------------------------------------------------


def load_events_from_jsonl(path: str) -> list[dict]:
    """Load events from a JSONL file (plain text)."""
    events = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                events.append(json.loads(line))
    return events


def load_gzipped_jsonl(path: str) -> list[dict]:
    """Load records from a gzipped JSONL file."""
    records = []
    with gzip.open(path, "rt", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


def parse_utc_iso(value: str) -> datetime:
    """Parse an ISO-8601 UTC string, handling Z suffix."""
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"
    return datetime.fromisoformat(value)

# ---------------------------------------------------------------------------
# Bar index helpers
# ---------------------------------------------------------------------------


def build_bar_index_by_symbol(bars: list[dict]) -> dict[str, list[dict]]:
    """Index bars by symbol, sorted by close_time_utc ascending."""
    index: dict[str, list[dict]] = {}
    for bar in bars:
        sym = bar.get("symbol", "")
        index.setdefault(sym, []).append(bar)
    for sym in index:
        index[sym].sort(key=lambda b: b.get("close_time_utc", ""))
    return index


def find_pre_bar(bars_sorted: list[dict], event_time: datetime) -> Optional[dict]:
    """Last bar with close_time_utc <= event_time."""
    candidate = None
    for bar in bars_sorted:
        ct = parse_utc_iso(bar["close_time_utc"])
        if ct <= event_time:
            candidate = bar
        else:
            break
    return candidate


def find_event_bar(bars_sorted: list[dict], event_time: datetime) -> Optional[dict]:
    """First bar with close_time_utc > event_time."""
    for bar in bars_sorted:
        ct = parse_utc_iso(bar["close_time_utc"])
        if ct > event_time:
            return bar
    return None


def find_post_bar(
    bars_sorted: list[dict], event_time: datetime, horizon_seconds: int
) -> Optional[dict]:
    """First bar with close_time_utc >= event_time + horizon."""
    cutoff = event_time + timedelta(seconds=horizon_seconds)
    for bar in bars_sorted:
        ct = parse_utc_iso(bar["close_time_utc"])
        if ct >= cutoff:
            return bar
    return None


def find_closest_bar(
    bars_sorted: list[dict], reference_time: datetime
) -> Optional[dict]:
    """Find bar whose close_time_utc is closest to reference_time."""
    best = None
    best_diff = None
    for bar in bars_sorted:
        ct = parse_utc_iso(bar["close_time_utc"])
        diff = abs((ct - reference_time).total_seconds())
        if best_diff is None or diff < best_diff:
            best_diff = diff
            best = bar
    return best

# ---------------------------------------------------------------------------
# Return and direction helpers
# ---------------------------------------------------------------------------


def compute_return_percent(pre_close: float, post_close: float) -> float:
    """Return (post/pre - 1) * 100."""
    if pre_close == 0.0:
        return 0.0
    return (post_close / pre_close - 1.0) * 100.0


def classify_direction(return_value: float, epsilon: float = 0.001) -> str:
    """Classify return direction: positive, negative, or neutral."""
    if return_value > epsilon:
        return "positive"
    elif return_value < -epsilon:
        return "negative"
    else:
        return "neutral"


# ---------------------------------------------------------------------------
# Funding context helper
# ---------------------------------------------------------------------------


def build_funding_index_by_symbol(snapshots: list[dict]) -> dict[str, list[dict]]:
    """Index derivative snapshots by symbol sorted by observed_at_utc."""
    index: dict[str, list[dict]] = {}
    for snap in snapshots:
        sym = snap.get("symbol", "")
        index.setdefault(sym, []).append(snap)
    for sym in index:
        index[sym].sort(key=lambda s: s.get("observed_at_utc", ""))
    return index


def find_latest_funding_before(
    snapshots_sorted: list[dict], event_time: datetime
) -> Optional[float]:
    """Return the latest funding_rate observed before event_time."""
    latest = None
    for snap in snapshots_sorted:
        ot = parse_utc_iso(snap["observed_at_utc"])
        if ot <= event_time:
            fr = snap.get("funding_rate")
            if fr is not None:
                latest = fr
        else:
            break
    return latest

# ---------------------------------------------------------------------------
# Core processing
# ---------------------------------------------------------------------------


def process_pilot_v2(
    events: list[dict],
    bars_index: dict[str, list[dict]],
    derivatives_index: dict[str, list[dict]],
    output_dir: str,
    sqlite_path: str,
) -> dict[str, Any]:
    """Run the full pilot v2 alignment and write all outputs."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    os.makedirs(os.path.dirname(sqlite_path) or ".", exist_ok=True)

    event_windows_records: list[dict] = []
    reaction_labels_records: list[dict] = []
    cross_asset_records: list[dict] = []
    funding_records: list[dict] = []

    expected_windows = 0
    expected_labels = 0

    for event in events:
        event_id = event.get("event_id", "")
        event_family = event.get("event_family", "")
        event_time_str = event.get(
            "actual_release_at_utc", event.get("event_time_utc", "")
        )
        if not event_time_str:
            continue
        event_time = parse_utc_iso(event_time_str)

        for asset in CRYPTO_ASSETS:
            instrument_id = f"binance_spot_{asset.lower()}"
            bars = bars_index.get(asset, [])

            if not bars:
                continue

            pre_bar = find_pre_bar(bars, event_time)
            event_bar = find_event_bar(bars, event_time)

            if pre_bar is None or event_bar is None:
                continue

            pre_close = pre_bar.get("close", 0.0)
            event_open = event_bar.get("open", 0.0)
            event_close = event_bar.get("close", 0.0)

            for horizon_key, horizon_sec in HORIZONS_SECONDS.items():
                post_bar = find_post_bar(bars, event_time, horizon_sec)
                if post_bar is None:
                    continue

                post_close = post_bar.get("close", 0.0)
                return_value = compute_return_percent(pre_close, post_close)
                direction = classify_direction(return_value, DIRECTION_EPSILON)

                window_id = hashlib.sha256(
                    f"{event_id}:{instrument_id}:{horizon_key}".encode()
                ).hexdigest()

                window_record = {
                    "contract_name": "EventMarketWindowV2",
                    "schema_version": "2.0.0",
                    "window_id": window_id,
                    "event_id": event_id,
                    "event_family": event_family,
                    "event_time_utc": event_time_str,
                    "instrument_id": instrument_id,
                    "symbol": asset,
                    "horizon": horizon_key,
                    "pre_bar_close_time_utc": pre_bar.get("close_time_utc", ""),
                    "pre_bar_close": pre_close,
                    "event_bar_close_time_utc": event_bar.get("close_time_utc", ""),
                    "event_bar_open": event_open,
                    "event_bar_close": event_close,
                    "post_bar_close_time_utc": post_bar.get("close_time_utc", ""),
                    "post_bar_close": post_close,
                    "return_pct": round(return_value, 6),
                    "direction": direction,
                    "data_quality": "computed_from_archived_bars",
                    "quality_flags": [],
                }
                event_windows_records.append(window_record)
                expected_windows += 1

                label_id = hashlib.sha256(
                    f"label:{event_id}:{instrument_id}:{horizon_key}".encode()
                ).hexdigest()

                label_record = {
                    "contract_name": "MarketReactionLabelV2",
                    "schema_version": "2.0.0",
                    "label_id": label_id,
                    "event_id": event_id,
                    "instrument_id": instrument_id,
                    "symbol": asset,
                    "event_time_utc": event_time_str,
                    "horizon": horizon_key,
                    "return_pct": round(return_value, 6),
                    "direction": direction,
                    "label_availability": "full",
                    "data_quality": "computed_from_archived_bars",
                    "quality_flags": [],
                    "calculation_version": "2.0.0",
                }
                reaction_labels_records.append(label_record)
                expected_labels += 1
            # Cross-asset context: capture bar closest to event time
            cross_asset_entry = {
                "event_id": event_id,
                "event_time_utc": event_time_str,
                "instrument_id": instrument_id,
                "symbol": asset,
                "cross_asset_snapshots": {},
            }
            for series_name in CROSS_ASSET_SERIES:
                series_bars = bars_index.get(series_name, [])
                if series_bars:
                    closest = find_closest_bar(series_bars, event_time)
                    if closest is not None:
                        cross_asset_entry["cross_asset_snapshots"][series_name] = {
                            "close_time_utc": closest.get("close_time_utc", ""),
                            "close": closest.get("close"),
                            "open": closest.get("open"),
                            "high": closest.get("high"),
                            "low": closest.get("low"),
                        }
            cross_asset_records.append(cross_asset_entry)

            # Funding context
            funding_entry = {
                "event_id": event_id,
                "event_time_utc": event_time_str,
                "instrument_id": instrument_id,
                "symbol": asset,
                "funding_rate": None,
            }
            der_bars = derivatives_index.get(asset, [])
            if der_bars:
                funding_rate = find_latest_funding_before(der_bars, event_time)
                funding_entry["funding_rate"] = funding_rate
            funding_records.append(funding_entry)
    # -----------------------------------------------------------------------
    # Write JSONL outputs
    # -----------------------------------------------------------------------
    windows_path = os.path.join(output_dir, "event_asset_windows_v2.jsonl")
    with open(windows_path, "w", encoding="utf-8") as f:
        for rec in event_windows_records:
            f.write(json.dumps(rec, ensure_ascii=False) + "\r\n")

    labels_path = os.path.join(output_dir, "market_reaction_labels_v2.jsonl")
    with open(labels_path, "w", encoding="utf-8") as f:
        for rec in reaction_labels_records:
            f.write(json.dumps(rec, ensure_ascii=False) + "\r\n")

    cross_asset_path = os.path.join(output_dir, "cross_asset_context_v2.jsonl")
    with open(cross_asset_path, "w", encoding="utf-8") as f:
        for rec in cross_asset_records:
            f.write(json.dumps(rec, ensure_ascii=False) + "\r\n")

    funding_path = os.path.join(output_dir, "funding_context_v2.jsonl")
    with open(funding_path, "w", encoding="utf-8") as f:
        for rec in funding_records:
            f.write(json.dumps(rec, ensure_ascii=False) + "\r\n")

    print(f"Written {len(event_windows_records)} event windows to {windows_path}")
    print(f"Written {len(reaction_labels_records)} reaction labels to {labels_path}")
    print(f"Written {len(cross_asset_records)} cross-asset records to {cross_asset_path}")
    print(f"Written {len(funding_records)} funding records to {funding_path}")
    # -----------------------------------------------------------------------
    # SQLite database
    # -----------------------------------------------------------------------
    conn = sqlite3.connect(sqlite_path)
    cursor = conn.cursor()

    # DROP existing tables
    cursor.execute(f"DROP TABLE IF EXISTS {SQLITE_TABLE_PILOT}")
    cursor.execute(f"DROP TABLE IF EXISTS {SQLITE_TABLE_WINDOWS}")
    cursor.execute(f"DROP TABLE IF EXISTS {SQLITE_TABLE_LABELS}")
    cursor.execute(f"DROP TABLE IF EXISTS {SQLITE_TABLE_CROSS_ASSET}")
    cursor.execute(f"DROP TABLE IF EXISTS {SQLITE_TABLE_FUNDING}")

    # CREATE tables
    cursor.execute(f"""
        CREATE TABLE {SQLITE_TABLE_PILOT} (
            run_id INTEGER PRIMARY KEY AUTOINCREMENT,
            pilot_version TEXT NOT NULL,
            started_at_utc TEXT NOT NULL,
            event_count INTEGER NOT NULL,
            asset_count INTEGER NOT NULL,
            horizon_count INTEGER NOT NULL,
            expected_windows INTEGER NOT NULL,
            actual_windows INTEGER NOT NULL,
            expected_labels INTEGER NOT NULL,
            actual_labels INTEGER NOT NULL,
            report_generated_at_utc TEXT NOT NULL
        )
    """)

    cursor.execute(f"""
        CREATE TABLE {SQLITE_TABLE_WINDOWS} (
            window_id TEXT PRIMARY KEY,
            event_id TEXT NOT NULL,
            event_family TEXT,
            event_time_utc TEXT NOT NULL,
            instrument_id TEXT NOT NULL,
            symbol TEXT NOT NULL,
            horizon TEXT NOT NULL,
            pre_bar_close REAL,
            event_bar_open REAL,
            event_bar_close REAL,
            post_bar_close REAL,
            return_pct REAL,
            direction TEXT
        )
    """)

    cursor.execute(f"""
        CREATE TABLE {SQLITE_TABLE_LABELS} (
            label_id TEXT PRIMARY KEY,
            event_id TEXT NOT NULL,
            instrument_id TEXT NOT NULL,
            symbol TEXT NOT NULL,
            event_time_utc TEXT NOT NULL,
            horizon TEXT NOT NULL,
            return_pct REAL,
            direction TEXT,
            label_availability TEXT
        )
    """)

    cursor.execute(f"""
        CREATE TABLE {SQLITE_TABLE_CROSS_ASSET} (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_id TEXT NOT NULL,
            event_time_utc TEXT NOT NULL,
            instrument_id TEXT NOT NULL,
            symbol TEXT NOT NULL,
            series_name TEXT NOT NULL,
            series_close REAL,
            UNIQUE(event_id, instrument_id, series_name)
        )
    """)

    cursor.execute(f"""
        CREATE TABLE {SQLITE_TABLE_FUNDING} (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_id TEXT NOT NULL,
            event_time_utc TEXT NOT NULL,
            instrument_id TEXT NOT NULL,
            symbol TEXT NOT NULL,
            funding_rate REAL,
            UNIQUE(event_id, instrument_id)
        )
    """)
    # INSERT windows
    insert_window_sql = f"""
        INSERT OR IGNORE INTO {SQLITE_TABLE_WINDOWS}
        (window_id, event_id, event_family, event_time_utc, instrument_id, symbol, horizon,
         pre_bar_close, event_bar_open, event_bar_close, post_bar_close, return_pct, direction)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """
    for rec in event_windows_records:
        cursor.execute(
            insert_window_sql,
            (
                rec["window_id"],
                rec["event_id"],
                rec.get("event_family", ""),
                rec["event_time_utc"],
                rec["instrument_id"],
                rec["symbol"],
                rec["horizon"],
                rec["pre_bar_close"],
                rec["event_bar_open"],
                rec["event_bar_close"],
                rec["post_bar_close"],
                rec["return_pct"],
                rec["direction"],
            ),
        )

    # INSERT labels
    insert_label_sql = f"""
        INSERT OR IGNORE INTO {SQLITE_TABLE_LABELS}
        (label_id, event_id, instrument_id, symbol, event_time_utc, horizon, return_pct, direction, label_availability)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """
    for rec in reaction_labels_records:
        cursor.execute(
            insert_label_sql,
            (
                rec["label_id"],
                rec["event_id"],
                rec["instrument_id"],
                rec["symbol"],
                rec["event_time_utc"],
                rec["horizon"],
                rec["return_pct"],
                rec["direction"],
                rec.get("label_availability", "full"),
            ),
        )

    # INSERT cross-asset
    insert_ca_sql = f"""
        INSERT OR IGNORE INTO {SQLITE_TABLE_CROSS_ASSET}
        (event_id, event_time_utc, instrument_id, symbol, series_name, series_close)
        VALUES (?, ?, ?, ?, ?, ?)
    """
    for rec in cross_asset_records:
        for series_name, snap in rec.get("cross_asset_snapshots", {}).items():
            cursor.execute(
                insert_ca_sql,
                (
                    rec["event_id"],
                    rec["event_time_utc"],
                    rec["instrument_id"],
                    rec["symbol"],
                    series_name,
                    snap.get("close"),
                ),
            )

    # INSERT funding
    insert_funding_sql = f"""
        INSERT OR IGNORE INTO {SQLITE_TABLE_FUNDING}
        (event_id, event_time_utc, instrument_id, symbol, funding_rate)
        VALUES (?, ?, ?, ?, ?)
    """
    for rec in funding_records:
        cursor.execute(
            insert_funding_sql,
            (
                rec["event_id"],
                rec["event_time_utc"],
                rec["instrument_id"],
                rec["symbol"],
                rec["funding_rate"],
            ),
        )

    # CREATE indexes
    cursor.execute(
        f"CREATE INDEX IF NOT EXISTS idx_windows_event_id ON {SQLITE_TABLE_WINDOWS}(event_id)"
    )
    cursor.execute(
        f"CREATE INDEX IF NOT EXISTS idx_windows_symbol ON {SQLITE_TABLE_WINDOWS}(symbol)"
    )
    cursor.execute(
        f"CREATE INDEX IF NOT EXISTS idx_labels_event_id ON {SQLITE_TABLE_LABELS}(event_id)"
    )
    cursor.execute(
        f"CREATE INDEX IF NOT EXISTS idx_labels_symbol ON {SQLITE_TABLE_LABELS}(symbol)"
    )
    cursor.execute(
        f"CREATE INDEX IF NOT EXISTS idx_ca_event_id ON {SQLITE_TABLE_CROSS_ASSET}(event_id)"
    )
    cursor.execute(
        f"CREATE INDEX IF NOT EXISTS idx_funding_event_id ON {SQLITE_TABLE_FUNDING}(event_id)"
    )

    conn.commit()
    # Count rows
    actual_windows = cursor.execute(
        f"SELECT COUNT(*) FROM {SQLITE_TABLE_WINDOWS}"
    ).fetchone()[0]
    actual_labels = cursor.execute(
        f"SELECT COUNT(*) FROM {SQLITE_TABLE_LABELS}"
    ).fetchone()[0]
    actual_cross_asset = cursor.execute(
        f"SELECT COUNT(*) FROM {SQLITE_TABLE_CROSS_ASSET}"
    ).fetchone()[0]
    actual_funding = cursor.execute(
        f"SELECT COUNT(*) FROM {SQLITE_TABLE_FUNDING}"
    ).fetchone()[0]

    # -----------------------------------------------------------------------
    # Assertions
    # -----------------------------------------------------------------------
    actual_labels = len(reaction_labels_records)
    assert (
        actual_labels == expected_labels
    ), f"Labels mismatch: expected {expected_labels}, got {actual_labels}"

    # Count distinct (event_id, instrument_id) pairs for windows (24 = 12 x 2)
    distinct_pairs = set()
    for w in event_windows_records:
        distinct_pairs.add((w["event_id"], w["instrument_id"]))
    actual_windows_distinct = len(distinct_pairs)
    event_count = len(events)
    asset_count = len(CRYPTO_ASSETS)
    assert actual_windows_distinct == event_count * asset_count,         f"Distinct windows mismatch: {actual_windows_distinct} != {event_count * asset_count}"

    print(f"Assertions: {actual_windows_distinct} distinct windows, {actual_labels} labels")

    # INSERT pilot run metadata
    started_at = utc_now()
    report_generated_at = utc_now()

    cursor.execute(
        f"""
        INSERT INTO {SQLITE_TABLE_PILOT}
        (pilot_version, started_at_utc, event_count, asset_count, horizon_count,
         expected_windows, actual_windows, expected_labels, actual_labels,
         report_generated_at_utc)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            PILOT_VERSION,
            started_at,
            len(events),
            len(CRYPTO_ASSETS),
            len(HORIZONS_SECONDS),
            expected_windows,
            actual_windows,
            expected_labels,
            actual_labels,
            report_generated_at,
        ),
    )
    conn.commit()
    conn.close()

    print(f"SQLite database written to {sqlite_path}")
    # -----------------------------------------------------------------------
    # Write pilot alignment report
    # -----------------------------------------------------------------------
    report = {
        "pilot_version": PILOT_VERSION,
        "started_at_utc": started_at,
        "report_generated_at_utc": report_generated_at,
        "event_count": len(events),
        "asset_count": len(CRYPTO_ASSETS),
        "horizons": list(HORIZONS_SECONDS.keys()),
        "expected_windows": expected_windows,
        "actual_windows": actual_windows,
        "expected_labels": expected_labels,
        "actual_labels": actual_labels,
        "cross_asset_records": len(cross_asset_records),
        "funding_records": len(funding_records),
        "assertions_passed": True,
        "output_files": {
            "event_windows": str(windows_path),
            "reaction_labels": str(labels_path),
            "cross_asset_context": str(cross_asset_path),
            "funding_context": str(funding_path),
            "sqlite_database": str(sqlite_path),
        },
    }

    report_path = os.path.join(output_dir, "pilot_alignment_report_v2.json")
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    print(f"Alignment report written to {report_path}")

    return report


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


def main() -> None:
    """Load data, run pilot v2 alignment, write outputs."""
    args = parse_arguments()

    print("Loading events ...")
    events = load_events_from_jsonl(args.ep)
    print(f"  Loaded {len(events)} events from {args.ep}")

    print("Loading market bars ...")
    bars = load_gzipped_jsonl(args.bp)
    print(f"  Loaded {len(bars)} bars from {args.bp}")

    print("Loading derivative snapshots ...")
    derivatives = load_gzipped_jsonl(args.dp)
    print(f"  Loaded {len(derivatives)} snapshots from {args.dp}")

    print("Indexing bars by symbol ...")
    bars_index = build_bar_index_by_symbol(bars)
    print(f"  Index contains {len(bars_index)} symbols")

    print("Indexing derivatives by symbol ...")
    derivatives_index = build_funding_index_by_symbol(derivatives)
    print(f"  Derivative index contains {len(derivatives_index)} symbols")

    report = process_pilot_v2(
        events=events,
        bars_index=bars_index,
        derivatives_index=derivatives_index,
        output_dir=args.od,
        sqlite_path=args.sp,
    )

    print("\n=== Pilot v2 Alignment Complete ===")
    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()