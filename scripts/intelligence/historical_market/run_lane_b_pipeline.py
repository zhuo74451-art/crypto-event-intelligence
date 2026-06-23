"""Unified pipeline runner for Lane B — Historical Market Data Factory.

Usage:
    python scripts/intelligence/historical_market/run_lane_b_pipeline.py \
        --start-date 2010-01-01 --end-date 2026-12-31 \
        --crypto-start-date 2017-01-01 --resume
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from build_crypto_spot_history import build_crypto_spot_history
from build_cross_asset_history import build_cross_asset_history
from build_crypto_derivatives_history import build_crypto_derivatives_history
from build_market_index import build_market_index
from audit_market_data import audit_market_data


def run_pipeline(
    start_date: str = "2010-01-01",
    end_date: str = "",
    crypto_start_date: str = "2017-01-01",
    cache_dir: str = "data/intelligence/historical_market/cache",
    output_dir: str = "data/intelligence/historical_market",
    resume: bool = False,
    force: bool = False,
    stages: list[str] | None = None,
) -> dict:
    """Run the full Lane B pipeline or selected stages."""
    output_dir = Path(output_dir)
    cache_dir = Path(cache_dir)

    all_reports = {}
    start_time = time.time()

    if stages is None or "crypto_spot" in stages:
        print("\n=== Stage: Crypto Spot History ===")
        r = build_crypto_spot_history(
            output_dir=output_dir,
            cache_dir=cache_dir,
            start_date=crypto_start_date,
            end_date=end_date,
            force=force,
        )
        all_reports["crypto_spot"] = r

    if stages is None or "cross_asset" in stages:
        print("\n=== Stage: Cross-Asset History ===")
        r = build_cross_asset_history(
            output_dir=output_dir,
            cache_dir=cache_dir,
            start_date=start_date,
            end_date=end_date,
            force=force,
        )
        all_reports["cross_asset"] = r

    if stages is None or "derivatives" in stages:
        print("\n=== Stage: Crypto Derivatives ===")
        r = build_crypto_derivatives_history(
            output_dir=output_dir,
            cache_dir=cache_dir,
            start_date="2019-01-01",
            end_date=end_date,
            force=force,
        )
        all_reports["derivatives"] = r

    if stages is None or "index" in stages:
        print("\n=== Stage: SQLite Index ===")
        r = build_market_index(
            bars_path=output_dir / "normalized" / "market_bars_v1.jsonl.gz",
            index_path=output_dir / "indexes" / "historical_market_v1.sqlite",
            force=force,
        )
        all_reports["index"] = r

    if stages is None or "audit" in stages:
        print("\n=== Stage: Market Data Audit ===")
        r = audit_market_data(
            bars_path=output_dir / "normalized" / "market_bars_v1.jsonl.gz",
            output_dir=output_dir,
        )
        all_reports["audit"] = r

    elapsed = time.time() - start_time

    summary = {
        "success": True,
        "stages_completed": list(all_reports.keys()),
        "elapsed_seconds": round(elapsed, 1),
        "stage_reports": all_reports,
    }

    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Lane B — Historical Market Data Pipeline")
    parser.add_argument("--start-date", default="2010-01-01")
    parser.add_argument("--end-date", default="")
    parser.add_argument("--crypto-start-date", default="2017-01-01")
    parser.add_argument("--cache-dir", default="data/intelligence/historical_market/cache")
    parser.add_argument("--output-dir", default="data/intelligence/historical_market")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--stages", nargs="+", help="crypto_spot cross_asset derivatives index audit")
    args = parser.parse_args()

    summary = run_pipeline(
        start_date=args.start_date,
        end_date=args.end_date,
        crypto_start_date=args.crypto_start_date,
        cache_dir=args.cache_dir,
        output_dir=args.output_dir,
        resume=args.resume,
        force=args.force,
        stages=args.stages,
    )
    print("\n=== Pipeline Summary ===")
    print(json.dumps(summary, indent=2, default=str))
