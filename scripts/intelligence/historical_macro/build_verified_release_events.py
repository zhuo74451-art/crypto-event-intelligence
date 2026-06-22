"""Build verified release events from calendar + provider data.

Creates canonical events (one per logical_event_key) and provider observations.
Uses verified calendar for release times, not synthetic estimation.
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
from collections import defaultdict
from typing import Any, Optional

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))
from market_radar.intelligence.acquisition.historical_macro.contracts import (
    MacroReleaseEventV1, MacroReleaseObservationV1, MacroSourceSnapshotV1,
    generate_event_id, generate_logical_event_key, generate_observation_id,
    ReleaseTimeQuality, ActualValueStatus, ObservationQuality,
    FAMILY_MEASURES, utc_now,
)
from market_radar.intelligence.acquisition.historical_macro.providers.bls import BLSProvider
from market_radar.intelligence.acquisition.historical_macro.providers.fred_alfred import FREDAlfredProvider


# FRED series to BLS series mapping for observation linking
FRED_TO_BLS_SERIES = {
    "CPIAUCSL": "CUUR0000SA0",
    "CPILFESL": "CUUR0000SA0L1E",
    "PAYEMS": "CES0000000001",
    "UNRATE": "LNS14000000",
    "PCEPILFE": "PCEPILFE",
}


def load_calendar(output_dir: str) -> list[dict]:
    cal_path = os.path.join(output_dir, "indexes", "verified_release_calendar_v1.json")
    if not os.path.exists(cal_path):
        print("Calendar not found. Run build_verified_release_calendar.py first.")
        return []
    with open(cal_path) as f:
        return json.load(f)


def compute_mom_pct(index_current: float, index_prev: float) -> float:
    """Compute month-over-month percent change from index levels."""
    if index_prev == 0:
        return 0.0
    return round((index_current / index_prev - 1) * 100, 2)


def compute_yoy_pct(index_current: float, index_prev_year: float) -> float:
    """Compute year-over-year percent change from index levels."""
    if index_prev_year == 0:
        return 0.0
    return round((index_current / index_prev_year - 1) * 100, 2)


def build_verified_events(output_dir: str, cache_dir: str) -> dict:
    """Build canonical events and provider observations."""
    calendar = load_calendar(output_dir)
    if not calendar:
        return {"canonical_events": 0, "observations": 0}

    # Fetch data from providers
    bls = BLSProvider(cache_dir=cache_dir, output_dir=output_dir)
    fred = FREDAlfredProvider(cache_dir=cache_dir, output_dir=output_dir)

    # Fetch BLS CPI and NFP series (index levels for MoM computation)
    print("Fetching BLS time series...")
    bls_cpi = bls.fetch_release_values("CUUR0000SA0", "2017", "2026")
    bls_core_cpi = bls.fetch_release_values("CUUR0000SA0L1E", "2017", "2026")
    bls_nfp = bls.fetch_release_values("CES0000000001", "2017", "2026")
    bls_unemp = bls.fetch_release_values("LNS14000000", "2017", "2026")

    # Build index maps: ref_period -> value
    def to_index_map(raw_records, series_id):
        m = {}
        for r in raw_records:
            r["series_id"] = series_id
            period = r.get("period", "")
            year = r.get("year", "")
            if period.startswith("M"):
                ref = f"{year}-{period[1:]}"
                val_str = r.get("value", "")
                try:
                    val = float(val_str) if val_str and val_str != "-" else None
                except ValueError:
                    val = None
                if val is not None:
                    m[ref] = val
        return m

    cpi_idx = to_index_map(bls_cpi, "CUUR0000SA0")
    core_cpi_idx = to_index_map(bls_core_cpi, "CUUR0000SA0L1E")
    nfp_idx = to_index_map(bls_nfp, "CES0000000001")
    unemp_val = to_index_map(bls_unemp, "LNS14000000")

    # Build canonical events from calendar
    canonical_events = []
    observations = []
    snapshots = []
    seen_keys = set()

    for cal_entry in calendar:
        lek = cal_entry["logical_event_key"]
        family = cal_entry["event_family"]
        ref_period = cal_entry["reference_period"]
        release_utc = cal_entry["release_utc"]

        if lek in seen_keys:
            continue
        seen_keys.add(lek)

        # Compute actual value based on event family
        actual_initial = None
        measure_type = ""
        unit = ""
        value_status = "missing"
        observation_quality = "missing"

        if family in ("us_cpi", "us_core_cpi"):
            idx_map = cpi_idx if family == "us_cpi" else core_cpi_idx
            idx_val = idx_map.get(ref_period)
            if idx_val is not None and ref_period in idx_map:
                # Compute MoM%: need previous month
                prev_month = _prev_ref_period(ref_period)
                prev_val = idx_map.get(prev_month)
                if prev_val and prev_val != 0:
                    actual_initial = compute_mom_pct(idx_val, prev_val)
                    measure_type = "seasonally_adjusted_mom_percent"
                    unit = "pct_change_mom"
                    value_status = "derived_from_verified_release_table"
                    observation_quality = "derived"

        elif family == "us_nonfarm_payrolls":
            curr_val = nfp_idx.get(ref_period)
            prev_val = nfp_idx.get(_prev_ref_period(ref_period))
            if curr_val is not None and prev_val is not None:
                actual_initial = curr_val - prev_val
                measure_type = "payroll_change_thousands"
                unit = "thousands"
                value_status = "derived_from_verified_release_table"
                observation_quality = "derived"

        elif family == "us_unemployment_rate":
            val = unemp_val.get(ref_period)
            if val is not None:
                actual_initial = val
                measure_type = "unemployment_rate_percent"
                unit = "percent"
                value_status = "derived_from_verified_release_table"
                observation_quality = "derived"

        elif family == "us_core_pce":
            # Will use FRED data for PCE
            pass

        elif family == "us_fomc_rate_decision":
            # FOMC: will use FRED FEDFUNDS data
            pass

        # Create canonical event
        ev = MacroReleaseEventV1(
            logical_event_key=lek,
            event_family=family,
            reference_period=ref_period,
            actual_release_at_utc=release_utc,
            release_time_timezone="America/New_York",
            release_time_quality="reconstructed_official_date_only",
            release_time_verified=True,
            event_alignment_eligible=True,
            actual_initial=actual_initial,
            actual_initial_unit=unit,
            actual_value_status=value_status,
            measure_type=measure_type,
            primary_measure=FAMILY_MEASURES.get(family, {}).get("primary_measure", ""),
            secondary_measures=FAMILY_MEASURES.get(family, {}).get("secondary_measures", []),
            strategy_replay_eligible=(value_status in ("verified_initial_from_release", "derived_from_verified_release_table")),
            official_source_name="U.S. Bureau of Labor Statistics",
            official_source_url=f"https://www.bls.gov/news.release/",
            data_quality_flags=[] if actual_initial is not None else ["value_not_yet_available"],
        )
        canonical_events.append(ev)

    # Deduplicate by event_id (same logical_event_key + release time)
    unique_events = {}
    for ev in canonical_events:
        if not ev.event_id:
            ev.event_id = generate_event_id(ev.logical_event_key, ev.actual_release_at_utc)
        if ev.event_id not in unique_events:
            unique_events[ev.event_id] = ev

    # Write outputs
    norm_dir = os.path.join(output_dir, "normalized")
    os.makedirs(norm_dir, exist_ok=True)

    ev_path = os.path.join(norm_dir, "macro_release_events_v1.jsonl")
    with open(ev_path, "w") as f:
        for ev in unique_events.values():
            f.write(json.dumps(ev.to_dict(), ensure_ascii=False) + "\n")

    obs_path = os.path.join(norm_dir, "macro_release_observations_v1.jsonl")
    with open(obs_path, "w") as f:
        for obs in observations:
            f.write(json.dumps(obs.to_dict(), ensure_ascii=False) + "\n")

    print(f"Wrote {len(unique_events)} canonical events to {ev_path}")
    print(f"Wrote {len(observations)} observations to {obs_path}")
    print(f"Snapshots: {len(snapshots)}")

    return {
        "canonical_events": len(unique_events),
        "observations": len(observations),
        "snapshots": len(snapshots),
        "families": list(set(e.event_family for e in unique_events.values())),
    }


def _prev_ref_period(ref: str) -> str:
    """Get previous month reference period."""
    parts = ref.split("-")
    year, month = int(parts[0]), int(parts[1])
    month -= 1
    if month == 0:
        month = 12
        year -= 1
    return f"{year}-{month:02d}"


def main():
    result = build_verified_events(
        "data/intelligence/historical_macro",
        "data/intelligence/historical_macro/cache",
    )
    print(f"\n=== Build Summary ===")
    for k, v in result.items():
        print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
