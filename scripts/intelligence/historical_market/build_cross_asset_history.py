"""Build cross-asset historical data from FRED and Yahoo Finance."""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from market_radar.intelligence.acquisition.historical_market.contracts import (
    MarketBarV1,
    utc_now,
)
from market_radar.intelligence.acquisition.historical_market.providers.fred_csv import (
    FredCsvProvider,
    FRED_SERIES,
)
from market_radar.intelligence.acquisition.historical_market.providers.public_cross_asset import (
    YahooFinanceProvider,
    YAHOO_INSTRUMENTS,
)


def build_cross_asset_history(
    output_dir: str | Path,
    cache_dir: str | Path,
    start_date: str = "2010-01-01",
    end_date: str = "",
    force: bool = False,
) -> dict[str, Any]:
    """Build cross-asset daily history. Returns coverage report."""
    output_dir = Path(output_dir)
    cache_dir = Path(cache_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    fred_provider = FredCsvProvider(cache_dir, output_dir)
    yahoo_provider = YahooFinanceProvider(cache_dir, output_dir)
    fetched_at = utc_now()

    all_bars: list[MarketBarV1] = []
    instrument_coverage: dict[str, int] = {}

    # FRED series
    for series_id in FRED_SERIES:
        print(f"[cross_asset] FRED {series_id} from {start_date}")
        result = fred_provider.fetch_bars(
            series_id=series_id,
            start_date=start_date,
            end_date=end_date,
            force=force,
        )
        if result.success:
            all_bars.extend(result.bars)
            instrument_coverage[series_id] = len(result.bars)
            print(f"  -> {len(result.bars)} records")
        else:
            print(f"  -> FAILED: {result.error_message}")

    # Yahoo Finance instruments
    for yahoo_symbol in YAHOO_INSTRUMENTS:
        print(f"[cross_asset] Yahoo {yahoo_symbol} from {start_date}")
        result = yahoo_provider.fetch_bars(
            yahoo_symbol=yahoo_symbol,
            start_date=start_date,
            end_date=end_date,
            force=force,
        )
        if result.success:
            all_bars.extend(result.bars)
            instrument_coverage[yahoo_symbol] = len(result.bars)
            print(f"  -> {len(result.bars)} records")
        else:
            print(f"  -> FAILED: {result.error_message}")

    # Deduplicate
    seen: set[str] = set()
    unique_bars: list[MarketBarV1] = []
    for bar in all_bars:
        if bar.bar_id not in seen:
            seen.add(bar.bar_id)
            unique_bars.append(bar)

    # Write normalized
    output_path = output_dir / "normalized" / "market_bars_v1.jsonl.gz"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Read existing bars if appending
    existing_ids: set[str] = set()
    if output_path.exists():
        with gzip.open(output_path, "rt", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    d = json.loads(line)
                    existing_ids.add(d.get("bar_id", ""))

    deduplicated: list[MarketBarV1] = []
    for bar in unique_bars:
        if bar.bar_id not in existing_ids:
            existing_ids.add(bar.bar_id)
            deduplicated.append(bar)

    # Append to existing file
    mode = "ab" if output_path.exists() else "wb"
    with gzip.open(output_path, mode) as f:
        for bar in deduplicated:
            f.write((json.dumps(bar.to_json(), ensure_ascii=False) + "\n").encode("utf-8"))

    # Compute total hash
    sha256 = hashlib.sha256()
    with gzip.open(output_path, "rb") as f:
        while True:
            chunk = f.read(65536)
            if not chunk:
                break
            sha256.update(chunk)
    file_hash = sha256.hexdigest()

    # Count total records
    total_records = 0
    with gzip.open(output_path, "rt", encoding="utf-8") as f:
        total_records = sum(1 for _ in f)

    report = {
        "provider": "fred_csv+yahoo_finance",
        "fetched_at_utc": fetched_at,
        "new_bars_appended": len(deduplicated),
        "total_records": total_records,
        "output_path": str(output_path),
        "file_sha256": file_hash,
        "instrument_coverage": instrument_coverage,
        "start_date": start_date,
        "end_date": end_date or "latest",
    }

    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", default="data/intelligence/historical_market")
    parser.add_argument("--cache-dir", default="data/intelligence/historical_market/cache")
    parser.add_argument("--start-date", default="2010-01-01")
    parser.add_argument("--end-date", default="")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    report = build_cross_asset_history(
        output_dir=args.output_dir,
        cache_dir=args.cache_dir,
        start_date=args.start_date,
        end_date=args.end_date,
        force=args.force,
    )
    print(json.dumps(report, indent=2))
