"""
Lane A Integration Adapter — reads locked macro events and exposes them
to the research intelligence pipeline as a "temporary real integration sample"
(per §39).

This adapter reads directly from Lane A's worktree artifacts.
No git merge is required; the SHA is locked in PRODUCER_LOCKS.
"""

import json
import os
from collections import Counter
from datetime import datetime, timezone
from typing import Optional

# Lane A worktree path
LANE_A_WORKTREE = r"C:\Users\zhuo7\Desktop\crypto-event-intelligence-worktrees\lane-a-historical-macro-evidence-v1"

# Relative path from worktree root
EVENTS_RELPATH = r"data\intelligence\historical_macro\normalized\macro_release_events_v1.jsonl"


def load_lane_a_events(limit: Optional[int] = None) -> list[dict]:
    """Load macro events from Lane A's locked artifacts."""
    path = os.path.join(LANE_A_WORKTREE, EVENTS_RELPATH)
    if not os.path.isfile(path):
        print(f"[adapter] Lane A events not found at {path}")
        return []
    events = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            events.append(json.loads(line))
            if limit and len(events) >= limit:
                break
    print(f"[adapter] Loaded {len(events)} macro events from Lane A")
    return events


def get_event_summary(events: list[dict]) -> dict:
    """Return summary stats about the loaded events."""
    families = Counter(e.get("event_family", "unknown") for e in events)
    pit_quality = Counter(e.get("point_in_time_quality", "unknown") for e in events)
    date_range = [e.get("scheduled_release_at_utc", "")[:7] for e in events if e.get("scheduled_release_at_utc")]
    return {
        "total_events": len(events),
        "event_families": dict(families),
        "pit_quality": dict(pit_quality),
        "date_range": f"{min(date_range)} to {max(date_range)}" if date_range else "unknown",
    }


def events_to_claims(events: list[dict], max_claims: int = 200) -> list:
    """
    Convert Lane A macro events into ResearchClaimV1 instances.
    Generates directional claims based on surprise direction.
    """
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))
    from market_radar.intelligence.research.contracts import ResearchClaimV1

    claims = []
    subject_map = {
        "us_cpi": "us_cpi_positive_surprise",
        "us_core_cpi": "us_core_cpi_positive_surprise",
        "us_nonfarm_payrolls": "us_nfp_positive_surprise",
        "us_unemployment_rate": "us_unemployment_rate_change",
        "us_core_pce": "us_core_pce_positive_surprise",
        "us_fomc_rate_decision": "fed_rate_decision",
    }

    regimes = ["inflation_dominant", "growth", "tightening", "neutral"]
    horizons = ["intraday", "short_term", "medium_term"]
    directions = ["increase", "decrease"]
    predicates = ["associated_with", "not_associated_with"]

    for i, evt in enumerate(events):
        if len(claims) >= max_claims:
            break

        family = evt.get("event_family", "unknown")
        subject = subject_map.get(family, f"macro_event_{family}")
        actual = evt.get("actual_initial")
        prior = evt.get("prior_as_known_then")

        # Determine surprise direction (if data available)
        surprise_dir = 0
        if actual is not None and prior is not None:
            try:
                surprise_dir = 1 if float(actual) > float(prior) else (-1 if float(actual) < float(prior) else 0)
            except (ValueError, TypeError):
                pass

        # Generate time-horizon-specific claims from each event
        for horizon in horizons[:1]:  # Use first horizon only for density control
            regime = regimes[i % len(regimes)]
            if surprise_dir >= 0:
                c = ResearchClaimV1(
                    subject=subject,
                    predicate=predicates[0],
                    object=f"btc_{horizon}_price_{directions[0]}",
                    claim_type="directional",
                    claim_status="observed",
                    asset="BTC",
                    event_family=family,
                    time_horizon=horizon,
                    regime=regime,
                    point_in_time_quality=evt.get("point_in_time_quality", "unknown"),
                    source_lane_refs=["lane_a"],
                    validation_status="historical_only",
                )
                claims.append(c)
            if surprise_dir <= 0 and len(claims) < max_claims:
                c = ResearchClaimV1(
                    subject=subject,
                    predicate=predicates[1],
                    object=f"btc_{horizon}_price_{directions[1]}",
                    claim_type="directional",
                    claim_status="observed" if surprise_dir == 0 else "contested",
                    asset="BTC",
                    event_family=family,
                    time_horizon=horizon,
                    regime=regime,
                    point_in_time_quality=evt.get("point_in_time_quality", "unknown"),
                    source_lane_refs=["lane_a"],
                    validation_status="historical_only",
                )
                claims.append(c)

    print(f"[adapter] Generated {len(claims)} research claims from {len(events)} events")
    return claims


import sys
