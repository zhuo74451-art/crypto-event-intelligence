#!/usr/bin/env python3
"""MVP+ Window 2 — Whale Engine: change detection, risk, exposure, extensions.

Reads Lane 1 output, runs change detection, computes risk/exposure,
and generates extension artifacts (watchlist, entity profiles,
behavior summary, alert candidates).
"""

from __future__ import annotations

import json
import os
import sys
import time
from datetime import datetime, timezone

_SCRIPT_DIR_WE = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(_SCRIPT_DIR_WE, *[os.pardir] * 3))
sys.path.insert(0, PROJECT_ROOT)

from market_radar.l2_whale_engine.state_manager import StateManager
from market_radar.l2_whale_engine.change_detector import detect_all_changes
from market_radar.l2_whale_engine.exposure_aggregator import aggregate_exposure
from market_radar.l2_whale_engine.watchlist import apply_watchlist
from market_radar.l2_whale_engine.entity_profile import get_entity_summary
from market_radar.l2_whale_engine.behavior_summary import compute_behavior
from market_radar.l2_whale_engine.alert_candidates import (
    generate_alert_candidates, format_alert_text,
)
from market_radar.l1_hyperliquid_provider.provenance import (
    make_source_health, utc_now_str,
)

OUTPUT_DIR = os.path.join(PROJECT_ROOT, "results", "mvpplus")
STATE_DIR = os.path.join(PROJECT_ROOT, "data", "mvpplus_state")
ARTIFACT_DIR = os.path.join(PROJECT_ROOT, "artifacts", "evidence")
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(STATE_DIR, exist_ok=True)
os.makedirs(ARTIFACT_DIR, exist_ok=True)


def load_lane1_output() -> tuple[list[dict], dict]:
    """Load positions from Lane 1 output."""
    path = os.path.join(OUTPUT_DIR, "lane1_whale_positions.json")
    if not os.path.isfile(path):
        return [], {"error": "lane1 output not found"}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data.get("positions", []), data
    except (IOError, json.JSONDecodeError) as e:
        return [], {"error": str(e)}


def write_artifact(name: str, data: dict):
    path = os.path.join(ARTIFACT_DIR, name)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    return os.path.relpath(path, PROJECT_ROOT)


def main() -> int:
    start_time = time.time()
    run_id = f"mvpplus_w2_{datetime.now(timezone.utc).strftime('%Y-%m-%d_%H%M%S')}_engine"
    snapshot_time = utc_now_str()

    print(f"[{run_id}] Window 2 - Whale Engine", file=sys.stderr)
    print(f"  Started: {snapshot_time}", file=sys.stderr)

    # Load Lane 1 data
    positions, lane1_meta = load_lane1_output()
    if not positions:
        print("  [DEGRADED] No positions from Lane 1", file=sys.stderr)
        empty = {
            "run_id": run_id, "detected_at_utc": snapshot_time,
            "lane": "lane2_whale_engine_w2",
            "changes": [], "exposure": None,
            "source_health": make_source_health(
                source="whale_engine", status="degraded",
                error_type="no_input",
                message_summary="No positions from Lane 1",
            ),
        }
        op = os.path.join(OUTPUT_DIR, "lane2_whale_changes.json")
        with open(op, "w") as f:
            json.dump(empty, f, indent=2)
        return 1

    # Initialize state manager
    state_mgr = StateManager(STATE_DIR)
    previous_state = state_mgr.load_previous()
    is_first_run = state_mgr.is_first_run

    if is_first_run:
        print("  First run - baseline snapshot (no change detection)", file=sys.stderr)
    else:
        print(f"  Previous state: {len(previous_state)} positions", file=sys.stderr)

    # Detect changes
    print("  Detecting position changes...", file=sys.stderr)
    changes = detect_all_changes(positions, previous_state, is_baseline_run=is_first_run)
    print(f"  Changes detected: {len(changes)}", file=sys.stderr)

    for c in changes:
        ct = c["change_type"]
        coin = c.get("coin", "?")
        label = c.get("label", "?")
        risk = c.get("risk_flags", [])
        flag_str = f" [{', '.join(risk)}]" if risk else ""
        print(f"    {ct:35s} {coin:4s} {label}{flag_str}", file=sys.stderr)

    # Save current state for next run (atomic)
    state_mgr.save_current(positions)
    print("  State saved for next run", file=sys.stderr)

    # Exposure aggregation
    print("  Computing exposure...", file=sys.stderr)
    exposure = aggregate_exposure(positions)

    # Watchlist
    print("  Applying watchlist filters...", file=sys.stderr)
    watchlist = apply_watchlist(positions, changes)

    # Entity profiles
    print("  Building entity profiles...", file=sys.stderr)
    entity_profiles = get_entity_summary(positions)

    # Behavior summary
    print("  Computing behavior summary...", file=sys.stderr)
    behavior = compute_behavior(positions, changes)

    # Alert candidates
    print("  Generating alert candidates...", file=sys.stderr)
    alerts = generate_alert_candidates(positions, changes, exposure)
    print(f"  Alerts: {len(alerts)}", file=sys.stderr)
    for a in alerts:
        print(f"    {format_alert_text(a)}", file=sys.stderr)

    # Outputs
    lane2_output = {
        "run_id": run_id,
        "detected_at_utc": snapshot_time,
        "lane": "lane2_whale_engine_w2",
        "is_first_run": is_first_run,
        "previous_state_count": len(previous_state),
        "changes": changes,
        "source_health": make_source_health(
            source="whale_engine", status="healthy",
            occurred_at_utc=snapshot_time,
            message_summary=f"{len(changes)} changes, baseline={is_first_run}",
        ),
    }
    op = os.path.join(OUTPUT_DIR, "lane2_whale_changes.json")
    with open(op, "w", encoding="utf-8") as f:
        json.dump(lane2_output, f, indent=2, ensure_ascii=False)

    # Extension artifacts
    write_artifact("w2_exposure.json", exposure)
    write_artifact("w2_watchlist.json", watchlist)
    write_artifact("w2_entity_profiles.json", entity_profiles)
    write_artifact("w2_behavior_summary.json", behavior)
    write_artifact("w2_alert_candidates.json", {
        "run_id": run_id,
        "generated_at_utc": snapshot_time,
        "total_alerts": len(alerts),
        "alerts": alerts,
    })

    # Live probe report
    probe = {
        "run_id": run_id,
        "generated_at_utc": snapshot_time,
        "addresses_in_universe": lane1_meta.get("address_universe", {}).get("total", 0),
        "positions_fetched": len(positions),
        "changes_detected": len(changes),
        "data_mode": "live",
        "hyperliquid_api": "healthy" if lane1_meta.get("source_health", {}).get("status") == "healthy" else "degraded",
    }
    write_artifact("w2_live_probe_report.json", probe)

    elapsed = time.time() - start_time
    print(f"\n  Done in {elapsed:.1f}s.", file=sys.stderr)
    print(f"  Positions: {len(positions)}, Changes: {len(changes)}, Alerts: {len(alerts)}", file=sys.stderr)
    print(f"  Output: {op}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    sys.exit(main())
