"""Bounded adapter probe — tests each adapter with small bounds.
Run: .venv/bin/python3 -m market_radar.cognition_v2.data_factory.adapters.probe
"""
from __future__ import annotations

import json
import sys
import os
from datetime import datetime, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../../../"))

from market_radar.cognition_v2.data_factory.adapters.registry import ADAPTER_REGISTRY
from market_radar.cognition_v2.data_factory.contracts import AcquisitionRun


def probe_adapter(name: str, adapter, start_year: int = 2024) -> dict:
    """Run a bounded probe and return results."""
    result = {
        "source_id": name,
        "status": "unknown",
        "records_count": 0,
        "has_source_timestamps": False,
        "sample_timestamps": [],
        "error": None,
    }

    try:
        start = datetime(start_year, 1, 1, tzinfo=timezone.utc)
        end = datetime(start_year, 6, 30, tzinfo=timezone.utc)

        records, next_token = adapter.fetch_page(
            source_id=name,
            start_time=start,
            end_time=end,
            page_size=5,
            page_token=None,
        )

        result["status"] = "ok"
        result["records_count"] = len(records)
        result["has_next"] = next_token is not None

        if records:
            result["has_source_timestamps"] = True
            for r in records[:3]:
                result["sample_timestamps"].append({
                    "intake_id": r.intake_id[:20],
                    "retrieved_at": r.retrieved_at.isoformat(),
                    "url": r.source_url[:80],
                })
    except Exception as e:
        result["status"] = "error"
        result["error"] = f"{type(e).__name__}: {str(e)[:120]}"

    return result


def main():
    results = []
    for name, adapter in ADAPTER_REGISTRY.items():
        print(f"Probing {name}...", flush=True)
        r = probe_adapter(name, adapter)
        results.append(r)
        print(f"  -> {r['status']}: {r['records_count']} records", flush=True)

    print("\n=== PROBE RESULTS ===")
    for r in results:
        ts_info = ""
        if r["sample_timestamps"]:
            ts_info = f' ts={r["sample_timestamps"][0]["retrieved_at"][:19]}'
        print(f'{r["source_id"]:30s} {r["status"]:8s} {r["records_count"]:4d} records{ts_info}')
        if r.get("error"):
            print(f'  ERROR: {r["error"][:100]}')


if __name__ == "__main__":
    main()
