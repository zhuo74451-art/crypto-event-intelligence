"""Build SQLite index for historical market data."""

from __future__ import annotations

import argparse
import gzip
import json
import sqlite3
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))


def build_market_index(
    bars_path: str | Path,
    index_path: str | Path,
    force: bool = False,
) -> dict[str, Any]:
    """Build or update SQLite index from market_bars_v1.jsonl.gz."""
    bars_path = Path(bars_path)
    index_path = Path(index_path)
    index_path.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(str(index_path))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=OFF")

    # Create tables
    conn.execute("""
        CREATE TABLE IF NOT EXISTS market_bars (
            bar_id TEXT PRIMARY KEY,
            instrument_id TEXT NOT NULL,
            symbol TEXT,
            venue TEXT,
            asset_class TEXT,
            instrument_type TEXT,
            interval TEXT NOT NULL,
            open_time_utc TEXT NOT NULL,
            close_time_utc TEXT,
            open REAL,
            high REAL,
            low REAL,
            close REAL,
            volume REAL,
            quote_volume REAL,
            trade_count INTEGER,
            is_proxy INTEGER DEFAULT 0,
            proxy_for TEXT,
            source_provider TEXT,
            data_quality TEXT,
            retrieved_at_utc TEXT
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS market_index (
            instrument_id TEXT,
            interval TEXT,
            min_open_time TEXT,
            max_open_time TEXT,
            bar_count INTEGER,
            PRIMARY KEY (instrument_id, interval)
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS derivatives (
            snapshot_id TEXT PRIMARY KEY,
            instrument_id TEXT NOT NULL,
            symbol TEXT,
            venue TEXT,
            observed_at_utc TEXT NOT NULL,
            interval TEXT,
            funding_rate REAL,
            open_interest REAL,
            open_interest_value REAL,
            basis REAL,
            source_provider TEXT,
            data_quality TEXT
        )
    """)

    if not bars_path.exists():
        return {"success": False, "error": f"Bars file not found: {bars_path}"}

    # Count existing
    existing = conn.execute("SELECT COUNT(*) FROM market_bars").fetchone()[0]
    print(f"Existing bars in index: {existing}")

    # Insert new bars
    inserted = 0
    with gzip.open(bars_path, "rt", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            d = json.loads(line)
            bar_id = d.get("bar_id", "")
            if not bar_id:
                continue

            try:
                conn.execute("""
                    INSERT OR IGNORE INTO market_bars
                    (bar_id, instrument_id, symbol, venue, asset_class, instrument_type,
                     interval, open_time_utc, close_time_utc,
                     open, high, low, close, volume, quote_volume, trade_count,
                     is_proxy, proxy_for, source_provider, data_quality, retrieved_at_utc)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """, (
                    bar_id,
                    d.get("instrument_id", ""),
                    d.get("symbol", ""),
                    d.get("venue", ""),
                    d.get("asset_class", ""),
                    d.get("instrument_type", ""),
                    d.get("interval", ""),
                    d.get("open_time_utc", ""),
                    d.get("close_time_utc", ""),
                    d.get("open"),
                    d.get("high"),
                    d.get("low"),
                    d.get("close"),
                    d.get("volume", 0),
                    d.get("quote_volume", 0),
                    d.get("trade_count", 0),
                    1 if d.get("is_proxy") else 0,
                    d.get("proxy_for", ""),
                    d.get("source_provider", ""),
                    d.get("data_quality", ""),
                    d.get("retrieved_at_utc", ""),
                ))
                if conn.total_changes > 0:
                    inserted += 1
            except sqlite3.IntegrityError:
                pass

    conn.commit()

    # Build/update index summary
    conn.execute("DELETE FROM market_index")
    conn.execute("""
        INSERT INTO market_index (instrument_id, interval, min_open_time, max_open_time, bar_count)
        SELECT instrument_id, interval,
               MIN(open_time_utc), MAX(open_time_utc), COUNT(*)
        FROM market_bars
        GROUP BY instrument_id, interval
    """)
    conn.commit()

    # Read coverage
    conn.row_factory = sqlite3.Row
    coverage = [dict(r) for r in conn.execute("SELECT * FROM market_index ORDER BY instrument_id, interval").fetchall()]

    conn.close()

    return {
        "success": True,
        "index_path": str(index_path),
        "existing_bars": existing,
        "new_bars_inserted": inserted,
        "total_bars": existing + inserted,
        "coverage": coverage,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--bars-path", default="data/intelligence/historical_market/normalized/market_bars_v1.jsonl.gz")
    parser.add_argument("--index-path", default="data/intelligence/historical_market/indexes/historical_market_v1.sqlite")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    report = build_market_index(
        bars_path=args.bars_path,
        index_path=args.index_path,
        force=args.force,
    )
    print(json.dumps(report, indent=2, default=str))
