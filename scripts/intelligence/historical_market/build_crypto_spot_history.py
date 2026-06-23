"""Build historical crypto spot market data from Binance archives.

Downloads BTCUSDT and ETHUSDT 1h and 1d data, normalizes it,
and writes to data/intelligence/historical_market/normalized/market_bars_v1.jsonl.gz.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# Ensure project root is on path
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from market_radar.intelligence.acquisition.historical_market.contracts import (
    MarketBarV1,
    DataQuality,
    Interval,
    utc_now,
)
from market_radar.intelligence.acquisition.historical_market.providers.crypto_archive import (
    CryptoArchiveProvider,
)


def build_crypto_spot_history(
    output_dir: str | Path,
    cache_dir: str | Path,
    start_date: str = "2017-01-01",
    end_date: str = "",
    force: bool = False,
    skip_daily: bool = False,
) -> dict[str, Any]:
    """Build BTC and ETH spot history. Returns coverage report."""
    output_dir = Path(output_dir)
    cache_dir = Path(cache_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    provider = CryptoArchiveProvider(cache_dir, output_dir)
    fetched_at = utc_now()

    intervals = ["1h", "1d"] if not skip_daily else ["1h"]
    symbols = ["BTCUSDT", "ETHUSDT"]
    all_bars: list[MarketBarV1] = []

    for symbol in symbols:
        for interval in intervals:
            print(f"[crypto_spot] Fetching {symbol} {interval} from {start_date} to {end_date or 'now'}")
            result = provider.fetch_bars(
                symbol=symbol,
                interval=interval,
                start_date=start_date,
                end_date=end_date or datetime.now(timezone.utc).strftime("%Y-%m-%d"),
                force=force,
            )
            if result.success:
                all_bars.extend(result.bars)
                print(f"  -> {len(result.bars)} bars")
            else:
                print(f"  -> FAILED: {result.error_message}")

    # Write to normalized output
    output_path = output_dir / "normalized" / "market_bars_v1.jsonl.gz"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Deduplicate by bar_id
    seen: set[str] = set()
    unique_bars: list[MarketBarV1] = []
    for bar in all_bars:
        if bar.bar_id not in seen:
            seen.add(bar.bar_id)
            unique_bars.append(bar)

    with gzip.open(output_path, "wt", encoding="utf-8") as f:
        for bar in unique_bars:
            f.write(json.dumps(bar.to_json(), ensure_ascii=False) + "\n")

    # Compute hash
    sha256 = hashlib.sha256()
    with gzip.open(output_path, "rb") as f:
        while True:
            chunk = f.read(65536)
            if not chunk:
                break
            sha256.update(chunk)
    file_hash = sha256.hexdigest()

    report = {
        "provider": "binance_public_archive",
        "fetched_at_utc": fetched_at,
        "total_bars": len(unique_bars),
        "output_path": str(output_path),
        "file_sha256": file_hash,
        "instruments": symbols,
        "intervals": intervals,
        "start_date": start_date,
        "end_date": end_date or "latest",
    }

    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", default="data/intelligence/historical_market")
    parser.add_argument("--cache-dir", default="data/intelligence/historical_market/cache")
    parser.add_argument("--start-date", default="2017-01-01")
    parser.add_argument("--end-date", default="")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--skip-daily", action="store_true")
    args = parser.parse_args()

    report = build_crypto_spot_history(
        output_dir=args.output_dir,
        cache_dir=args.cache_dir,
        start_date=args.start_date,
        end_date=args.end_date,
        force=args.force,
        skip_daily=args.skip_daily,
    )
    print(json.dumps(report, indent=2))
