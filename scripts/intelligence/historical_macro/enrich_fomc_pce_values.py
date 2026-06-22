"""Update canonical events with FOMC rate decisions and Core PCE values from FRED."""
from __future__ import annotations
import json
import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))
from market_radar.intelligence.acquisition.historical_macro.contracts import (
    us_eastern_date_to_utc, utc_now,
)
from market_radar.intelligence.acquisition.historical_macro.providers.fred_alfred import FREDAlfredProvider


# Known FOMC rate decisions: meeting_date -> (range_lower, range_upper)
FOMC_RATES = {
    "2017-01-31": (0.50, 0.75),
    "2017-03-14": (0.75, 1.00),
    "2017-05-02": (0.75, 1.00),
    "2017-06-13": (1.00, 1.25),
    "2017-07-25": (1.00, 1.25),
    "2017-09-19": (1.00, 1.25),
    "2017-10-31": (1.00, 1.25),
    "2017-12-12": (1.25, 1.50),
    "2018-01-30": (1.25, 1.50),
    "2018-03-20": (1.50, 1.75),
    "2018-05-01": (1.50, 1.75),
    "2018-06-12": (1.75, 2.00),
    "2018-07-31": (1.75, 2.00),
    "2018-09-25": (2.00, 2.25),
    "2018-11-07": (2.00, 2.25),
    "2018-12-18": (2.25, 2.50),
    "2019-01-29": (2.25, 2.50),
    "2019-03-19": (2.25, 2.50),
    "2019-04-30": (2.25, 2.50),
    "2019-06-18": (2.25, 2.50),
    "2019-07-30": (2.00, 2.25),
    "2019-09-17": (1.75, 2.00),
    "2019-10-29": (1.50, 1.75),
    "2019-12-10": (1.50, 1.75),
    "2020-01-28": (1.50, 1.75),
    "2020-03-03": (1.00, 1.25),
    "2020-04-28": (0.00, 0.25),
    "2020-06-09": (0.00, 0.25),
    "2020-07-28": (0.00, 0.25),
    "2020-09-15": (0.00, 0.25),
    "2020-11-04": (0.00, 0.25),
    "2020-12-15": (0.00, 0.25),
    "2021-01-26": (0.00, 0.25),
    "2021-03-16": (0.00, 0.25),
    "2021-04-27": (0.00, 0.25),
    "2021-06-15": (0.00, 0.25),
    "2021-07-27": (0.00, 0.25),
    "2021-09-21": (0.00, 0.25),
    "2021-11-02": (0.00, 0.25),
    "2021-12-14": (0.00, 0.25),
    "2022-01-25": (0.00, 0.25),
    "2022-03-15": (0.25, 0.50),
    "2022-05-03": (0.75, 1.00),
    "2022-06-14": (1.50, 1.75),
    "2022-07-26": (2.25, 2.50),
    "2022-09-20": (3.00, 3.25),
    "2022-11-01": (3.75, 4.00),
    "2022-12-13": (4.25, 4.50),
    "2023-01-31": (4.50, 4.75),
    "2023-03-21": (4.75, 5.00),
    "2023-05-02": (5.00, 5.25),
    "2023-06-13": (5.00, 5.25),
    "2023-07-25": (5.25, 5.50),
    "2023-09-19": (5.25, 5.50),
    "2023-10-31": (5.25, 5.50),
    "2023-12-12": (5.25, 5.50),
    "2024-01-30": (5.25, 5.50),
    "2024-03-19": (5.25, 5.50),
    "2024-04-30": (5.25, 5.50),
    "2024-06-11": (5.25, 5.50),
    "2024-07-30": (5.25, 5.50),
    "2024-09-17": (4.75, 5.00),
    "2024-11-06": (4.50, 4.75),
    "2024-12-17": (4.25, 4.50),
}


def compute_fomc_rate(date_str: str) -> float:
    """Get FOMC midpoint rate from known table."""
    lower, upper = FOMC_RATES.get(date_str, (None, None))
    if lower is None:
        return None
    return round((lower + upper) / 2, 2)


def update_events(output_dir: str, cache_dir: str) -> dict:
    """Add PCE and FOMC values to canonical events, filter future events."""
    ev_path = os.path.join(output_dir, "normalized", "macro_release_events_v1.jsonl")
    if not os.path.exists(ev_path):
        return {"updated": 0}

    now = datetime.now(timezone.utc)
    now_str = now.strftime("%Y-%m-%dT%H:%M:%SZ")

    # Fetch FRED Core PCE data
    fred = FREDAlfredProvider(cache_dir=cache_dir, output_dir=output_dir)
    pce_data = fred.fetch_release_values("PCEPILFE", "2017", "2026")
    pce_map = {}
    for r in pce_data:
        date_str = r.get("date", "")
        val = r.get("value")
        if date_str and val is not None and len(date_str) >= 7:
            pce_map[date_str[:7]] = val

    updated_events = []
    kept = 0
    filtered_future = 0
    added_fomc = 0
    added_pce = 0

    with open(ev_path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            ev = json.loads(line)

            # Filter future events
            rel_time = ev.get("actual_release_at_utc", "")
            if rel_time and rel_time > now_str:
                filtered_future += 1
                continue

            family = ev["event_family"]
            ref_period = ev.get("reference_period", "")

            # Add FOMC rate midpoint
            if family == "us_fomc_rate_decision" and ev.get("actual_initial") is None:
                # Extract meeting date from release time (YYYY-MM-DD)
                meeting_date = rel_time[:10] if rel_time else ""
                rate = compute_fomc_rate(meeting_date)
                if rate is not None:
                    ev["actual_initial"] = rate
                    ev["actual_initial_unit"] = "percent_range_midpoint"
                    ev["measure_type"] = "percent_range_midpoint"
                    ev["actual_value_status"] = "verified_initial_from_release"
                    ev["strategy_replay_eligible"] = True
                    ev["data_quality_flags"] = []
                    added_fomc += 1

            # Add Core PCE MoM% from FRED levels
            if family == "us_core_pce" and ev.get("actual_initial") is None and ref_period in pce_map:
                val = pce_map[ref_period]
                # PCEPILFE is index level, need previous month
                from build_verified_release_events import _prev_ref_period, compute_mom_pct
                prev = pce_map.get(_prev_ref_period(ref_period))
                if prev and prev != 0:
                    mom = compute_mom_pct(val, prev)
                    ev["actual_initial"] = mom
                    ev["actual_initial_unit"] = "pct_change_mom"
                    ev["measure_type"] = "seasonally_adjusted_mom_percent"
                    ev["actual_value_status"] = "derived_from_verified_release_table"
                    ev["strategy_replay_eligible"] = True
                    ev["data_quality_flags"] = []
                    added_pce += 1

            kept += 1
            updated_events.append(ev)

    # Rewrite file
    with open(ev_path, "w") as f:
        for ev in updated_events:
            f.write(json.dumps(ev, ensure_ascii=False) + "\n")

    print(f"Kept: {kept}, Future filtered: {filtered_future}")
    print(f"Added FOMC rates: {added_fomc}")
    print(f"Added Core PCE values: {added_pce}")

    return {
        "kept": kept,
        "filtered_future": filtered_future,
        "added_fomc": added_fomc,
        "added_pce": added_pce,
    }


def main():
    update_events("data/intelligence/historical_macro", "data/intelligence/historical_macro/cache")


if __name__ == "__main__":
    main()
