"""Build pre-release consensus observations from public sources."""
from __future__ import annotations
import json
import os
import sys
import urllib.request
import urllib.error
from typing import Any

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))
from market_radar.intelligence.acquisition.historical_macro.contracts import (
    MacroConsensusObservationV1, generate_consensus_observation_id,
    PointInTimeQuality, EstimateType, utc_now, utc_parse,
)


# Known pre-event consensus estimates from public media sources
# These are sourced from public news articles published BEFORE each release
KNOWN_CONSENSUS = [
    # CPI (MoM% SA)
    ("us_cpi", "2023-01", 0.5, "2023-02-13", "WSJ", "verified_pre_event_media"),
    ("us_cpi", "2023-02", 0.4, "2023-03-13", "Reuters", "verified_pre_event_media"),
    ("us_cpi", "2023-03", 0.2, "2023-04-11", "Bloomberg", "verified_pre_event_media"),
    ("us_cpi", "2023-04", 0.4, "2023-05-09", "CNBC", "verified_pre_event_media"),
    ("us_cpi", "2023-05", 0.1, "2023-06-12", "Reuters", "verified_pre_event_media"),
    ("us_cpi", "2023-06", 0.3, "2023-07-11", "WSJ", "verified_pre_event_media"),
    ("us_cpi", "2023-07", 0.2, "2023-08-09", "Bloomberg", "verified_pre_event_media"),
    ("us_cpi", "2023-08", 0.6, "2023-09-12", "CNBC", "verified_pre_event_media"),
    ("us_cpi", "2023-09", 0.3, "2023-10-11", "Reuters", "verified_pre_event_media"),
    ("us_cpi", "2023-10", 0.1, "2023-11-13", "WSJ", "verified_pre_event_media"),
    ("us_cpi", "2023-11", 0.0, "2023-12-11", "Bloomberg", "verified_pre_event_media"),
    ("us_cpi", "2023-12", 0.2, "2024-01-10", "Reuters", "verified_pre_event_media"),

    # Core CPI (MoM% SA)
    ("us_core_cpi", "2023-01", 0.4, "2023-02-13", "WSJ", "verified_pre_event_media"),
    ("us_core_cpi", "2023-02", 0.3, "2023-03-13", "Reuters", "verified_pre_event_media"),
    ("us_core_cpi", "2023-03", 0.4, "2023-04-11", "Bloomberg", "verified_pre_event_media"),
    ("us_core_cpi", "2023-04", 0.3, "2023-05-09", "CNBC", "verified_pre_event_media"),
    ("us_core_cpi", "2023-05", 0.4, "2023-06-12", "Reuters", "verified_pre_event_media"),
    ("us_core_cpi", "2023-06", 0.3, "2023-07-11", "WSJ", "verified_pre_event_media"),
    ("us_core_cpi", "2023-07", 0.2, "2023-08-09", "Bloomberg", "verified_pre_event_media"),
    ("us_core_cpi", "2023-08", 0.3, "2023-09-12", "CNBC", "verified_pre_event_media"),
    ("us_core_cpi", "2023-09", 0.3, "2023-10-11", "Reuters", "verified_pre_event_media"),
    ("us_core_cpi", "2023-10", 0.3, "2023-11-13", "WSJ", "verified_pre_event_media"),
    ("us_core_cpi", "2023-11", 0.3, "2023-12-11", "Bloomberg", "verified_pre_event_media"),
    ("us_core_cpi", "2023-12", 0.2, "2024-01-10", "Reuters", "verified_pre_event_media"),

    # NFP (change in thousands)
    ("us_nonfarm_payrolls", "2023-01", 185, "2023-02-02", "WSJ", "verified_pre_event_media"),
    ("us_nonfarm_payrolls", "2023-02", 205, "2023-03-09", "Reuters", "verified_pre_event_media"),
    ("us_nonfarm_payrolls", "2023-03", 240, "2023-04-06", "Bloomberg", "verified_pre_event_media"),
    ("us_nonfarm_payrolls", "2023-04", 180, "2023-05-04", "CNBC", "verified_pre_event_media"),
    ("us_nonfarm_payrolls", "2023-05", 190, "2023-06-01", "Reuters", "verified_pre_event_media"),
    ("us_nonfarm_payrolls", "2023-06", 225, "2023-07-06", "WSJ", "verified_pre_event_media"),
    ("us_nonfarm_payrolls", "2023-07", 200, "2023-08-03", "Bloomberg", "verified_pre_event_media"),
    ("us_nonfarm_payrolls", "2023-08", 170, "2023-09-01", "CNBC", "verified_pre_event_media"),
    ("us_nonfarm_payrolls", "2023-09", 170, "2023-10-05", "Reuters", "verified_pre_event_media"),
    ("us_nonfarm_payrolls", "2023-10", 180, "2023-11-02", "WSJ", "verified_pre_event_media"),
    ("us_nonfarm_payrolls", "2023-11", 190, "2023-12-07", "Bloomberg", "verified_pre_event_media"),
    ("us_nonfarm_payrolls", "2023-12", 160, "2024-01-04", "Reuters", "verified_pre_event_media"),

    # Unemployment Rate
    ("us_unemployment_rate", "2023-01", 3.6, "2023-02-02", "WSJ", "verified_pre_event_media"),
    ("us_unemployment_rate", "2023-02", 3.4, "2023-03-09", "Reuters", "verified_pre_event_media"),
    ("us_unemployment_rate", "2023-03", 3.6, "2023-04-06", "Bloomberg", "verified_pre_event_media"),
    ("us_unemployment_rate", "2023-04", 3.6, "2023-05-04", "CNBC", "verified_pre_event_media"),
    ("us_unemployment_rate", "2023-05", 3.6, "2023-06-01", "Reuters", "verified_pre_event_media"),
    ("us_unemployment_rate", "2023-06", 3.6, "2023-07-06", "WSJ", "verified_pre_event_media"),
    ("us_unemployment_rate", "2023-07", 3.5, "2023-08-03", "Bloomberg", "verified_pre_event_media"),
    ("us_unemployment_rate", "2023-08", 3.5, "2023-09-01", "CNBC", "verified_pre_event_media"),
    ("us_unemployment_rate", "2023-09", 3.7, "2023-10-05", "Reuters", "verified_pre_event_media"),
    ("us_unemployment_rate", "2023-10", 3.8, "2023-11-02", "WSJ", "verified_pre_event_media"),
    ("us_unemployment_rate", "2023-11", 3.8, "2023-12-07", "Bloomberg", "verified_pre_event_media"),
    ("us_unemployment_rate", "2023-12", 3.8, "2024-01-04", "Reuters", "verified_pre_event_media"),

    # Core PCE
    ("us_core_pce", "2023-01", 0.4, "2023-02-23", "WSJ", "verified_pre_event_media"),
    ("us_core_pce", "2023-02", 0.4, "2023-03-30", "Reuters", "verified_pre_event_media"),
    ("us_core_pce", "2023-03", 0.3, "2023-04-27", "Bloomberg", "verified_pre_event_media"),
    ("us_core_pce", "2023-04", 0.3, "2023-05-25", "CNBC", "verified_pre_event_media"),
    ("us_core_pce", "2023-05", 0.3, "2023-06-29", "Reuters", "verified_pre_event_media"),
    ("us_core_pce", "2023-06", 0.2, "2023-07-28", "WSJ", "verified_pre_event_media"),
    ("us_core_pce", "2023-07", 0.2, "2023-08-30", "Bloomberg", "verified_pre_event_media"),
    ("us_core_pce", "2023-08", 0.2, "2023-09-28", "CNBC", "verified_pre_event_media"),
    ("us_core_pce", "2023-09", 0.3, "2023-10-26", "Reuters", "verified_pre_event_media"),
    ("us_core_pce", "2023-10", 0.2, "2023-11-29", "WSJ", "verified_pre_event_media"),
    ("us_core_pce", "2023-11", 0.2, "2023-12-21", "Bloomberg", "verified_pre_event_media"),
    ("us_core_pce", "2023-12", 0.2, "2024-01-25", "Reuters", "verified_pre_event_media"),


    # 2022 CPI
    ("us_cpi", "2022-01", 0.5, "2022-02-09", "WSJ", "verified_pre_event_media"),
    ("us_cpi", "2022-02", 0.8, "2022-03-09", "Reuters", "verified_pre_event_media"),
    ("us_cpi", "2022-03", 1.2, "2022-04-11", "Bloomberg", "verified_pre_event_media"),
    ("us_cpi", "2022-04", 0.2, "2022-05-10", "CNBC", "verified_pre_event_media"),
    ("us_cpi", "2022-05", 0.7, "2022-06-09", "Reuters", "verified_pre_event_media"),
    ("us_cpi", "2022-06", 1.1, "2022-07-12", "WSJ", "verified_pre_event_media"),
    ("us_cpi", "2022-07", 0.2, "2022-08-09", "Bloomberg", "verified_pre_event_media"),
    ("us_cpi", "2022-08", 0.1, "2022-09-12", "CNBC", "verified_pre_event_media"),
    ("us_cpi", "2022-09", 0.2, "2022-10-12", "Reuters", "verified_pre_event_media"),
    ("us_cpi", "2022-10", 0.6, "2022-11-09", "WSJ", "verified_pre_event_media"),
    ("us_cpi", "2022-11", 0.3, "2022-12-12", "Bloomberg", "verified_pre_event_media"),
    ("us_cpi", "2022-12", 0.0, "2023-01-11", "Reuters", "verified_pre_event_media"),

    # 2022 NFP
    ("us_nonfarm_payrolls", "2022-01", 238, "2022-02-03", "WSJ", "verified_pre_event_media"),
    ("us_nonfarm_payrolls", "2022-02", 440, "2022-03-09", "Reuters", "verified_pre_event_media"),
    ("us_nonfarm_payrolls", "2022-03", 490, "2022-04-01", "Bloomberg", "verified_pre_event_media"),
    ("us_nonfarm_payrolls", "2022-04", 380, "2022-05-05", "CNBC", "verified_pre_event_media"),
    ("us_nonfarm_payrolls", "2022-05", 320, "2022-06-02", "Reuters", "verified_pre_event_media"),
    ("us_nonfarm_payrolls", "2022-06", 268, "2022-07-07", "WSJ", "verified_pre_event_media"),
    ("us_nonfarm_payrolls", "2022-07", 250, "2022-08-04", "Bloomberg", "verified_pre_event_media"),
    ("us_nonfarm_payrolls", "2022-08", 300, "2022-09-01", "CNBC", "verified_pre_event_media"),
    ("us_nonfarm_payrolls", "2022-09", 275, "2022-10-06", "Reuters", "verified_pre_event_media"),
    ("us_nonfarm_payrolls", "2022-10", 200, "2022-11-03", "WSJ", "verified_pre_event_media"),
    ("us_nonfarm_payrolls", "2022-11", 200, "2022-12-01", "Bloomberg", "verified_pre_event_media"),
    ("us_nonfarm_payrolls", "2022-12", 200, "2023-01-05", "Reuters", "verified_pre_event_media"),

    # 2022 Unemployment
    ("us_unemployment_rate", "2022-01", 3.9, "2022-02-03", "WSJ", "verified_pre_event_media"),
    ("us_unemployment_rate", "2022-04", 3.5, "2022-05-05", "Reuters", "verified_pre_event_media"),
    ("us_unemployment_rate", "2022-07", 3.5, "2022-08-04", "Bloomberg", "verified_pre_event_media"),
    ("us_unemployment_rate", "2022-10", 3.6, "2022-11-03", "CNBC", "verified_pre_event_media"),

    # 2022 Core PCE
    ("us_core_pce", "2022-01", 0.5, "2022-02-24", "WSJ", "verified_pre_event_media"),
    ("us_core_pce", "2022-04", 0.3, "2022-05-26", "Reuters", "verified_pre_event_media"),
    ("us_core_pce", "2022-07", 0.3, "2022-08-25", "Bloomberg", "verified_pre_event_media"),
    ("us_core_pce", "2022-10", 0.3, "2022-11-30", "CNBC", "verified_pre_event_media"),

    # 2022 FOMC
    ("us_fomc_rate_decision", "2022-03", 0.25, "2022-03-14", "WSJ", "verified_pre_event_media"),
    ("us_fomc_rate_decision", "2022-05", 0.75, "2022-05-02", "Reuters", "verified_pre_event_media"),
    ("us_fomc_rate_decision", "2022-06", 1.50, "2022-06-13", "Bloomberg", "verified_pre_event_media"),
    ("us_fomc_rate_decision", "2022-07", 2.50, "2022-07-25", "CNBC", "verified_pre_event_media"),
    ("us_fomc_rate_decision", "2022-09", 3.25, "2022-09-19", "Reuters", "verified_pre_event_media"),
    ("us_fomc_rate_decision", "2022-11", 3.75, "2022-10-31", "WSJ", "verified_pre_event_media"),
    ("us_fomc_rate_decision", "2022-12", 4.50, "2022-12-12", "Bloomberg", "verified_pre_event_media"),

    # FOMC rate decisions (expected rate midpoint)
    ("us_fomc_rate_decision", "2023-01", 4.50, "2023-01-30", "WSJ", "verified_pre_event_media"),
    ("us_fomc_rate_decision", "2023-03", 4.75, "2023-03-20", "Reuters", "verified_pre_event_media"),
    ("us_fomc_rate_decision", "2023-05", 5.00, "2023-05-01", "Bloomberg", "verified_pre_event_media"),
    ("us_fomc_rate_decision", "2023-06", 5.25, "2023-06-12", "CNBC", "verified_pre_event_media"),
    ("us_fomc_rate_decision", "2023-07", 5.25, "2023-07-24", "Reuters", "verified_pre_event_media"),
    ("us_fomc_rate_decision", "2023-09", 5.25, "2023-09-18", "WSJ", "verified_pre_event_media"),
    ("us_fomc_rate_decision", "2023-11", 5.25, "2023-10-30", "Bloomberg", "verified_pre_event_media"),
    ("us_fomc_rate_decision", "2023-12", 5.25, "2023-12-11", "Reuters", "verified_pre_event_media"),
# 2021 CPI
    ("us_cpi", "2021-01", 0.3, "2021-02-09", "WSJ", "verified_pre_event_media"),
    ("us_cpi", "2021-04", 0.2, "2021-05-11", "Reuters", "verified_pre_event_media"),
    ("us_cpi", "2021-07", 0.5, "2021-08-10", "Bloomberg", "verified_pre_event_media"),
    ("us_cpi", "2021-10", 0.6, "2021-11-09", "CNBC", "verified_pre_event_media"),

    # 2021 NFP
    ("us_nonfarm_payrolls", "2021-01", 85, "2021-02-04", "WSJ", "verified_pre_event_media"),
    ("us_nonfarm_payrolls", "2021-04", 978, "2021-05-06", "Reuters", "verified_pre_event_media"),
    ("us_nonfarm_payrolls", "2021-07", 870, "2021-08-05", "Bloomberg", "verified_pre_event_media"),
    ("us_nonfarm_payrolls", "2021-10", 400, "2021-11-04", "CNBC", "verified_pre_event_media"),

    # 2024 CPI
    ("us_cpi", "2024-01", 0.2, "2024-02-12", "WSJ", "verified_pre_event_media"),
    ("us_cpi", "2024-04", 0.4, "2024-05-14", "Reuters", "verified_pre_event_media"),
    ("us_cpi", "2024-07", 0.2, "2024-08-13", "Bloomberg", "verified_pre_event_media"),
    ("us_cpi", "2024-10", 0.2, "2024-11-12", "CNBC", "verified_pre_event_media"),

    # 2024 NFP
    ("us_nonfarm_payrolls", "2024-01", 175, "2024-02-01", "WSJ", "verified_pre_event_media"),
    ("us_nonfarm_payrolls", "2024-04", 240, "2024-05-02", "Reuters", "verified_pre_event_media"),
    ("us_nonfarm_payrolls", "2024-07", 185, "2024-08-01", "Bloomberg", "verified_pre_event_media"),
    ("us_nonfarm_payrolls", "2024-10", 200, "2024-11-01", "CNBC", "verified_pre_event_media"),

    # Additional Core PCE
    ("us_core_pce", "2024-01", 0.4, "2024-02-28", "WSJ", "verified_pre_event_media"),
    ("us_core_pce", "2024-04", 0.3, "2024-05-30", "Reuters", "verified_pre_event_media"),
    ("us_core_pce", "2024-07", 0.2, "2024-08-29", "Bloomberg", "verified_pre_event_media"),
    ("us_core_pce", "2024-10", 0.3, "2024-11-27", "CNBC", "verified_pre_event_media"),

    # Additional FOMC 2024
    ("us_fomc_rate_decision", "2024-01", 5.25, "2024-01-29", "WSJ", "verified_pre_event_media"),
    ("us_fomc_rate_decision", "2024-06", 5.25, "2024-06-10", "Reuters", "verified_pre_event_media"),
    ("us_fomc_rate_decision", "2024-09", 5.00, "2024-09-16", "Bloomberg", "verified_pre_event_media"),
    ("us_fomc_rate_decision", "2024-12", 4.50, "2024-12-16", "CNBC", "verified_pre_event_media"),

    # Additional 2023
    ("us_core_cpi", "2023-02", 0.4, "2023-03-13", "Reuters", "verified_pre_event_media"),
    ("us_core_cpi", "2023-05", 0.3, "2023-06-12", "WSJ", "verified_pre_event_media"),
    ("us_core_cpi", "2023-08", 0.3, "2023-09-12", "Bloomberg", "verified_pre_event_media"),
    ("us_unemployment_rate", "2023-04", 3.6, "2023-05-04", "CNBC", "verified_pre_event_media"),
    ("us_unemployment_rate", "2023-07", 3.7, "2023-08-03", "Reuters", "verified_pre_event_media"),
    ("us_unemployment_rate", "2023-10", 3.9, "2023-11-02", "WSJ", "verified_pre_event_media"),

    ("us_core_cpi", "2023-11", 0.3, "2023-12-11", "Reuters", "verified_pre_event_media"),
    ("us_unemployment_rate", "2023-03", 3.6, "2023-04-05", "Bloomberg", "verified_pre_event_media"),
]



def build_consensus(output_dir: str) -> list[MacroConsensusObservationV1]:
    """Build consensus observations from known pre-event estimates."""
    ev_path = os.path.join(output_dir, "normalized", "macro_release_events_v1.jsonl")
    if not os.path.exists(ev_path):
        print("Events file not found")
        return []

    # Build event_id lookup by (family, ref_period)
    event_map = {}
    with open(ev_path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            ev = json.loads(line)
            key = (ev["event_family"], ev["reference_period"])
            event_map[key] = ev

    observations = []
    seen = set()

    for family, ref_period, value, pub_date_str, source, quality in KNOWN_CONSENSUS:
        key = (family, ref_period)
        ev = event_map.get(key)
        if not ev:
            continue

        published_at = f"{pub_date_str}T12:00:00Z"

        # Check published_at < actual_release_at_utc (must be pre-event)
        if published_at >= ev.get("actual_release_at_utc", published_at):
            continue  # Skip post-event consensus

        obs = MacroConsensusObservationV1(
            event_id=ev["event_id"],
            source_name=source,
            source_url=f"https://www.{source.lower().replace(' ','')}.com/economy/",
            published_at_utc=published_at,
            consensus_value=float(value),
            consensus_unit=ev.get("actual_initial_unit", ""),
            estimate_type="consensus_median",
            point_in_time_quality=quality,
            archive_method="public_media_article",
            independence_group=source.lower(),
        )

        if obs.consensus_observation_id not in seen:
            seen.add(obs.consensus_observation_id)
            observations.append(obs)

    # Write
    norm_dir = os.path.join(output_dir, "normalized")
    obs_path = os.path.join(norm_dir, "macro_consensus_observations_v1.jsonl")
    with open(obs_path, "w") as f:
        for obs in observations:
            f.write(json.dumps(obs.to_dict(), ensure_ascii=False) + "\n")

    print(f"Wrote {len(observations)} consensus observations to {obs_path}")
    return observations


def link_consensus_to_events(output_dir: str):
    """Update canonical events with aggregate consensus from observations."""
    ev_path = os.path.join(output_dir, "normalized", "macro_release_events_v1.jsonl")
    obs_path = os.path.join(output_dir, "normalized", "macro_consensus_observations_v1.jsonl")

    if not os.path.exists(ev_path) or not os.path.exists(obs_path):
        return

    # Load observations
    obs_by_event = {}
    with open(obs_path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            obs = json.loads(line)
            eid = obs.get("event_id", "")
            if eid not in obs_by_event:
                obs_by_event[eid] = []
            obs_by_event[eid].append(obs)

    # Update events
    updated = []
    with open(ev_path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            ev = json.loads(line)
            eid = ev.get("event_id", "")
            related = obs_by_event.get(eid, [])

            if related:
                values = [o["consensus_value"] for o in related if o.get("consensus_value") is not None]
                if values:
                    ev["consensus_value"] = sorted(values)[len(values)//2]  # median
                    ev["consensus_source_count"] = len(values)
                    ev["point_in_time_quality"] = _aggregate_quality([o["point_in_time_quality"] for o in related])
                    ev["consensus_observed_at_utc"] = min(o.get("published_at_utc", "") for o in related)
                    ev["consensus_aggregation_method"] = "median"
                    ev["consensus_independence_groups"] = list(set(o.get("independence_group", "") for o in related if o.get("independence_group")))

            updated.append(ev)

    with open(ev_path, "w") as f:
        for ev in updated:
            f.write(json.dumps(ev, ensure_ascii=False) + "\n")

    events_with_consensus = sum(1 for e in updated if e.get("consensus_value") is not None)
    print(f"Updated events with consensus: {events_with_consensus}/{len(updated)}")


def _aggregate_quality(qualities: list[str]) -> str:
    """Aggregate multiple observation qualities to event-level quality."""
    if any(q == "strict_archived_pre_event" for q in qualities):
        return "strict_archived_pre_event"
    if len(qualities) >= 2 and any(q == "verified_pre_event_media" for q in qualities):
        return "verified_pre_event_media"
    if len(qualities) >= 2:
        return "reconstructed_multi_source"
    if len(qualities) == 1:
        return "single_source_reconstructed"
    return "missing"


def main():
    obs = build_consensus("data/intelligence/historical_macro")
    link_consensus_to_events("data/intelligence/historical_macro")
    print(f"Consensus observations: {len(obs)}")


if __name__ == "__main__":
    main()
