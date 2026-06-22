"""Build consensus observations from public pre-event sources.

Fetches and normalizes consensus estimates from public providers.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any, Optional

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../..")))

from market_radar.intelligence.acquisition.historical_macro.contracts import (
    MacroConsensusObservationV1,
    MacroSourceSnapshotV1,
    utc_now,
)
from market_radar.intelligence.acquisition.historical_macro.providers.public_consensus import (
    PublicConsensusProvider,
)


def build_consensus_observations(
    event_families: list[str],
    output_dir: str,
    cache_dir: str,
    resume: bool = True,
) -> tuple[list[MacroConsensusObservationV1], list[MacroSourceSnapshotV1]]:
    """Build consensus observations from public sources."""
    all_observations: list[MacroConsensusObservationV1] = []
    all_snapshots: list[MacroSourceSnapshotV1] = []
    seen_ids: set[str] = set()

    obs_path = os.path.join(output_dir, "normalized", "macro_consensus_observations_v1.jsonl")
    if resume and os.path.exists(obs_path):
        with open(obs_path) as f:
            for line in f:
                line = line.strip()
                if line:
                    data = json.loads(line)
                    obs = MacroConsensusObservationV1(**data)
                    if obs.consensus_observation_id:
                        seen_ids.add(obs.consensus_observation_id)
                    all_observations.append(obs)
        print(f"  Resumed with {len(all_observations)} existing observations")

    provider = PublicConsensusProvider(cache_dir=cache_dir, output_dir=output_dir)

    for family in event_families:
        print(f"\n[Consensus] Fetching for {family}...")
        try:
            raw_records = provider.fetch_consensus_observations(family, "")
            print(f"  Got {len(raw_records)} raw records")
        except Exception as e:
            print(f"  Error: {e}")
            continue

        for raw in raw_records:
            raw["event_id"] = raw.get("event_id", "")
            raw["published_at_utc"] = raw.get("published_at_utc", utc_now())

            try:
                obs = provider.normalize_consensus(raw)
            except Exception as e:
                print(f"  Normalize error: {e}")
                continue

            if obs is None:
                continue

            if obs.consensus_observation_id in seen_ids:
                continue
            seen_ids.add(obs.consensus_observation_id)
            all_observations.append(obs)

        all_snapshots.extend(provider.get_snapshots())

    return all_observations, all_snapshots


def write_output(observations: list[MacroConsensusObservationV1],
                  snapshots: list[MacroSourceSnapshotV1],
                  output_dir: str):
    """Write consensus observations to canonical output."""
    norm_dir = os.path.join(output_dir, "normalized")
    os.makedirs(norm_dir, exist_ok=True)

    obs_path = os.path.join(norm_dir, "macro_consensus_observations_v1.jsonl")
    with open(obs_path, "w") as f:
        for obs in observations:
            f.write(json.dumps(obs.to_dict(), ensure_ascii=False) + "\n")
    print(f"Wrote {len(observations)} observations to {obs_path}")


def main():
    parser = argparse.ArgumentParser(description="Build consensus observations")
    parser.add_argument("--event-families", nargs="*", default=[])
    parser.add_argument("--output-dir", default="data/intelligence/historical_macro")
    parser.add_argument("--cache-dir", default="data/intelligence/historical_macro/cache")
    parser.add_argument("--resume", action="store_true", default=True)
    args = parser.parse_args()

    families = args.event_families or [
        "us_cpi", "us_core_cpi", "us_nonfarm_payrolls",
        "us_unemployment_rate", "us_core_pce", "us_fomc_rate_decision",
    ]

    observations, snapshots = build_consensus_observations(
        families, args.output_dir, args.cache_dir, resume=args.resume,
    )
    write_output(observations, snapshots, args.output_dir)

    print(f"\n=== Consensus Build Summary ===")
    print(f"Observations: {len(observations)}")


if __name__ == "__main__":
    main()
