"""Build canonical macro release events from provider data.

Fetches data from all registered providers and normalizes into
MacroReleaseEventV1 records, stored as JSONL.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from typing import Any, Optional

# Ensure we can import from the project
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../..")))

from market_radar.intelligence.acquisition.historical_macro.contracts import (
    MacroReleaseEventV1,
    MacroSourceSnapshotV1,
    EventFamily,
    generate_event_id,
    utc_now,
)
from market_radar.intelligence.acquisition.historical_macro.providers.bls import BLSProvider
from market_radar.intelligence.acquisition.historical_macro.providers.bea import BEAProvider
from market_radar.intelligence.acquisition.historical_macro.providers.federal_reserve import FederalReserveProvider
from market_radar.intelligence.acquisition.historical_macro.providers.fred_alfred import FREDAlfredProvider


# Provider registration: (provider_class, series_ids, event_families)
PROVIDER_CONFIGS = [
    (BLSProvider, ["CUUR0000SA0", "CUUR0000SA0L1E", "CES0000000001", "LNS14000000"],
     ["us_cpi", "us_core_cpi", "us_nonfarm_payrolls", "us_unemployment_rate"]),
    (BEAProvider, ["PCEPILFE"],
     ["us_core_pce"]),
    (FederalReserveProvider, ["FEDFUNDS"],
     ["us_fomc_rate_decision"]),
    (FREDAlfredProvider, ["CPIAUCSL", "CPILFESL", "PAYEMS", "UNRATE", "PCEPILFE", "FEDFUNDS"],
     ["us_cpi", "us_core_cpi", "us_nonfarm_payrolls", "us_unemployment_rate", "us_core_pce", "us_fomc_rate_decision"]),
]


def build_release_events(start_year: str, end_year: str,
                          output_dir: str, cache_dir: str,
                          resume: bool = True) -> tuple[list[MacroReleaseEventV1], list[MacroSourceSnapshotV1]]:
    """Fetch and normalize release events from all providers."""
    all_events: list[MacroReleaseEventV1] = []
    all_snapshots: list[MacroSourceSnapshotV1] = []
    seen_ids: set[str] = set()

    # Load existing events if resuming
    release_path = os.path.join(output_dir, "normalized", "macro_release_events_v1.jsonl")
    if resume and os.path.exists(release_path):
        with open(release_path) as f:
            for line in f:
                line = line.strip()
                if line:
                    data = json.loads(line)
                    event = MacroReleaseEventV1(**data)
                    if event.event_id:
                        seen_ids.add(event.event_id)
                    all_events.append(event)
        print(f"  Resumed with {len(all_events)} existing events")

    for provider_cls, series_ids, families in PROVIDER_CONFIGS:
        provider = provider_cls(cache_dir=cache_dir, output_dir=output_dir)
        provider_name = provider.provider_name
        print(f"\n[{provider_name}] Fetching release values...")

        for series_id in series_ids:
            print(f"  Series: {series_id}")
            try:
                raw_records = provider.fetch_release_values(series_id, start_year, end_year)
                print(f"  Got {len(raw_records)} raw records")
            except Exception as e:
                print(f"  Error fetching {series_id}: {e}")
                continue

            for raw in raw_records:
                raw["series_id"] = series_id
                try:
                    event = provider.normalize_release(raw)
                except Exception as e:
                    print(f"  Normalize error: {e}")
                    continue

                if event is None:
                    continue

                if event.event_id in seen_ids:
                    continue

                seen_ids.add(event.event_id)
                all_events.append(event)

        all_snapshots.extend(provider.get_snapshots())

    # Deduplicate by event_id
    unique: dict[str, MacroReleaseEventV1] = {}
    for event in all_events:
        if event.event_id not in unique:
            unique[event.event_id] = event
        elif event.actual_initial is not None and unique[event.event_id].actual_initial is None:
            unique[event.event_id] = event

    return list(unique.values()), all_snapshots


def write_output(events: list[MacroReleaseEventV1],
                  snapshots: list[MacroSourceSnapshotV1],
                  output_dir: str):
    """Write canonical output files."""
    norm_dir = os.path.join(output_dir, "normalized")
    os.makedirs(norm_dir, exist_ok=True)

    # Write events JSONL
    release_path = os.path.join(norm_dir, "macro_release_events_v1.jsonl")
    with open(release_path, "w") as f:
        for event in events:
            f.write(json.dumps(event.to_dict(), ensure_ascii=False) + "\n")
    print(f"\nWrote {len(events)} events to {release_path}")

    # Write snapshots JSONL
    snap_path = os.path.join(norm_dir, "macro_source_snapshots_v1.jsonl")
    with open(snap_path, "w") as f:
        for snap in snapshots:
            f.write(json.dumps(snap.to_dict(), ensure_ascii=False) + "\n")
    print(f"Wrote {len(snapshots)} snapshots to {snap_path}")

    # Write CSV summary
    csv_path = os.path.join(norm_dir, "macro_release_events_v1.csv")
    with open(csv_path, "w") as f:
        f.write("event_id,event_family,reference_period,actual_release_at_utc,actual_initial,consensus_value,point_in_time_quality\n")
        for event in events:
            f.write(f"{event.event_id},{event.event_family},{event.reference_period},{event.actual_release_at_utc},{event.actual_initial or ''},{event.consensus_value or ''},{event.point_in_time_quality}\n")
    print(f"Wrote CSV summary to {csv_path}")


def main():
    parser = argparse.ArgumentParser(description="Build macro release events")
    parser.add_argument("--start-year", default="2010")
    parser.add_argument("--end-year", default="2026")
    parser.add_argument("--output-dir", default="data/intelligence/historical_macro")
    parser.add_argument("--cache-dir", default="data/intelligence/historical_macro/cache")
    parser.add_argument("--resume", action="store_true", default=True)
    args = parser.parse_args()

    events, snapshots = build_release_events(
        args.start_year, args.end_year,
        args.output_dir, args.cache_dir,
        resume=args.resume,
    )
    write_output(events, snapshots, args.output_dir)

    print(f"\n=== Build Summary ===")
    print(f"Events: {len(events)}")
    print(f"Snapshots: {len(snapshots)}")


if __name__ == "__main__":
    main()
