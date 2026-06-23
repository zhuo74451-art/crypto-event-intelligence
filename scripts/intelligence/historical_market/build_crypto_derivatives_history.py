"""Build crypto derivatives history (funding rates)."""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from market_radar.intelligence.acquisition.historical_market.contracts import utc_now
from market_radar.intelligence.acquisition.historical_market.providers.crypto_public_api import (
    CryptoPublicApiProvider,
    FUTURES_INSTRUMENTS,
)


def build_derivatives_history(
    output_dir: str | Path,
    cache_dir: str | Path,
    start_date: str = "2019-01-01",
    end_date: str = "",
    force: bool = False,
) -> dict[str, Any]:
    """Build derivatives history. Returns coverage report."""
    output_dir = Path(output_dir)
    cache_dir = Path(cache_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    provider = CryptoPublicApiProvider(cache_dir, output_dir)
    fetched_at = utc_now()

    all_snapshots: list[Any] = []

    for symbol in FUTURES_INSTRUMENTS:
        print(f"[derivatives] Funding rates for {symbol} from {start_date}")
        result = provider.fetch_derivative_snapshots(
            symbol=symbol,
            start_date=start_date,
            end_date=end_date,
            force=force,
        )
        if result.success:
            all_snapshots.extend(result.derivatives)
            print(f"  -> {len(result.derivatives)} records")
        else:
            print(f"  -> FAILED: {result.error_message}")

    # Deduplicate
    seen: set[str] = set()
    unique: list[Any] = []
    for snap in all_snapshots:
        if snap.snapshot_id not in seen:
            seen.add(snap.snapshot_id)
            unique.append(snap)

    # Write output
    output_path = output_dir / "normalized" / "derivative_snapshots_v1.jsonl.gz"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    mode = "ab" if output_path.exists() else "wb"
    existing_ids: set[str] = set()
    if output_path.exists():
        try:
            with gzip.open(output_path, "rt", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        d = json.loads(line)
                        existing_ids.add(d.get("snapshot_id", ""))
        except Exception:
            existing_ids = set()

    deduplicated = [s for s in unique if s.snapshot_id not in existing_ids]

    if deduplicated:
        with gzip.open(output_path, mode) as f:
            for snap in deduplicated:
                f.write((json.dumps(snap.to_json(), ensure_ascii=False) + "\n").encode("utf-8"))

    # Hash
    sha256 = hashlib.sha256()
    if output_path.exists():
        with gzip.open(output_path, "rb") as f:
            while True:
                chunk = f.read(65536)
                if not chunk:
                    break
                sha256.update(chunk)

    total = 0
    if output_path.exists():
        with gzip.open(output_path, "rt", encoding="utf-8") as f:
            total = sum(1 for _ in f)

    report = {
        "provider": "binance_public_api",
        "fetched_at_utc": fetched_at,
        "new_records": len(deduplicated),
        "total_records": total,
        "output_path": str(output_path),
        "file_sha256": sha256.hexdigest(),
        "instruments": list(FUTURES_INSTRUMENTS.keys()),
        "start_date": start_date,
        "end_date": end_date or "latest",
    }

    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", default="data/intelligence/historical_market")
    parser.add_argument("--cache-dir", default="data/intelligence/historical_market/cache")
    parser.add_argument("--start-date", default="2019-01-01")
    parser.add_argument("--end-date", default="")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    report = build_derivatives_history(
        output_dir=args.output_dir,
        cache_dir=args.cache_dir,
        start_date=args.start_date,
        end_date=args.end_date,
        force=args.force,
    )
    print(json.dumps(report, indent=2))
