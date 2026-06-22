"""Build provider observations linking provider data to canonical events."""
from __future__ import annotations
import hashlib
import json
import os
import sys
from typing import Any, Optional

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))
from market_radar.intelligence.acquisition.historical_macro.contracts import (
    MacroReleaseObservationV1, MacroSourceSnapshotV1,
    generate_observation_id, generate_logical_event_key,
    ObservationQuality, utc_now,
)
from market_radar.intelligence.acquisition.historical_macro.providers.bls import BLSProvider
from market_radar.intelligence.acquisition.historical_macro.providers.fred_alfred import FREDAlfredProvider


def build_observations(output_dir: str, cache_dir: str) -> dict:
    """Build provider observations for all canonical events."""
    events_path = os.path.join(output_dir, "normalized", "macro_release_events_v1.jsonl")
    if not os.path.exists(events_path):
        return {"observations": 0}

    with open(events_path) as f:
        events = [json.loads(line) for line in f if line.strip()]

    # Fetch BLS and FRED data
    bls = BLSProvider(cache_dir=cache_dir, output_dir=output_dir)
    fred = FREDAlfredProvider(cache_dir=cache_dir, output_dir=output_dir)

    observations = []
    snapshots = []

    for ev in events:
        family = ev["event_family"]
        ref = ev["reference_period"]
        lek = ev.get("logical_event_key", "")

        # BLS observations for CPI/Core CPI/NFP/Unemployment
        if family in ("us_cpi", "us_core_cpi", "us_nonfarm_payrolls", "us_unemployment_rate"):
            obs = MacroReleaseObservationV1(
                event_id=ev["event_id"],
                logical_event_key=lek,
                provider="bls",
                series_id=ev.get("series_id", ""),
                observed_value=ev.get("actual_initial"),
                measure_type=ev.get("measure_type", ""),
                observation_quality=ev.get("actual_value_status", "missing"),
            )
            observations.append(obs)

        # FRED observations for all families
        fred_series_map = {
            "us_cpi": "CPIAUCSL",
            "us_core_cpi": "CPILFESL",
            "us_nonfarm_payrolls": "PAYEMS",
            "us_unemployment_rate": "UNRATE",
            "us_core_pce": "PCEPILFE",
            "us_fomc_rate_decision": "FEDFUNDS",
        }
        fs = fred_series_map.get(family)
        if fs:
            obs = MacroReleaseObservationV1(
                event_id=ev["event_id"],
                logical_event_key=lek,
                provider="fred_alfred",
                series_id=fs,
                observed_value=ev.get("actual_initial"),
                measure_type=ev.get("measure_type", ""),
                observation_quality=ev.get("actual_value_status", "missing"),
            )
            observations.append(obs)

    # Write
    norm_dir = os.path.join(output_dir, "normalized")
    obs_path = os.path.join(norm_dir, "macro_release_observations_v1.jsonl")
    with open(obs_path, "w") as f:
        for obs in observations:
            if not obs.observation_id:
                obs.observation_id = generate_observation_id(
                    obs.event_id, obs.provider, obs.series_id,
                    "", obs.measure_type,
                )
            f.write(json.dumps(obs.to_dict(), ensure_ascii=False) + "\n")

    print(f"Wrote {len(observations)} observations to {obs_path}")
    return {"observations": len(observations)}


def main():
    build_observations("data/intelligence/historical_macro", "data/intelligence/historical_macro/cache")


if __name__ == "__main__":
    main()
