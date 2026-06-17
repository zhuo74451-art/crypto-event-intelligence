#!/usr/bin/env python3
"""MVP+ Window 2 — Lane 1: Hyperliquid Whale Position Provider.

Uses hardened modules in market_radar/l1_hyperliquid_provider/.
Features:
- 3-tier address universe (whitelist -> leaderboard -> cache)
- Live provenance tracking (live/cached/fixture)
- Correct liquidation distance formulas
- HYPE prices from Hyperliquid only (NOT Binance)
- Raw response archiving for audit
- Bounded concurrency, timeouts, retry
"""

from __future__ import annotations

import json
import os
import sys
import time
from datetime import datetime, timezone

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(_SCRIPT_DIR, *[os.pardir] * 3))
sys.path.insert(0, PROJECT_ROOT)

from market_radar.l1_hyperliquid_provider.address_universe import create_default_universe
from market_radar.l1_hyperliquid_provider.hl_client import HyperliquidClient
from market_radar.l1_hyperliquid_provider.position_mapper import (
    map_raw_position, validate_positions_batch,
)
from market_radar.l1_hyperliquid_provider.provenance import (
    make_source_health, utc_now_str,
)

OUTPUT_DIR = os.path.join(PROJECT_ROOT, "results", "mvpplus")
os.makedirs(OUTPUT_DIR, exist_ok=True)
RAW_ARCHIVE_DIR = os.path.join(PROJECT_ROOT, "artifacts", "evidence", "hl_raw_responses")


def main() -> int:
    start_time = time.time()
    run_id = f"mvpplus_w2_{datetime.now(timezone.utc).strftime('%Y-%m-%d_%H%M%S')}_lane1"
    snapshot_time = utc_now_str()

    print(f"[{run_id}] Window 2 - Lane 1: Hyperliquid Whale Provider", file=sys.stderr)
    print(f"  Snapshot: {snapshot_time}", file=sys.stderr)

    client = HyperliquidClient(raw_archive_dir=RAW_ARCHIVE_DIR)
    universe = create_default_universe()

    # Step 1: Fetch mids
    print("  [1/3] Fetching all mids...", file=sys.stderr)
    mids, mids_error, mids_prov = client.fetch_all_mids()
    if mids is None:
        print(f"  [FATAL] Failed: {mids_error}", file=sys.stderr)
        output = {
            "run_id": run_id, "snapshot_time_utc": snapshot_time,
            "lane": "lane1_hyperliquid_w2", "positions": [],
            "source_health": make_source_health(
                source="hyperliquid_info_public", status="unavailable",
                error_type="api_failure", message_summary=mids_error,
            ),
        }
        with open(os.path.join(OUTPUT_DIR, "lane1_whale_positions.json"), "w") as f:
            json.dump(output, f, indent=2, ensure_ascii=False)
        return 1

    print(f"  Got {len(mids)} mids", file=sys.stderr)

    # Step 2: Build address universe
    print("  [2/3] Building address universe...", file=sys.stderr)
    addresses = universe.refresh()

    # Step 3: Fetch positions
    print("  [3/3] Fetching positions...", file=sys.stderr)
    all_positions: list[dict] = []
    errors: list[dict] = []
    healthy_count = 0

    for entry in addresses:
        addr = entry.address
        label = entry.label or "Unknown"
        short = f"{addr[:6]}...{addr[-4:]}"
        print(f"    {label} ({short})...", file=sys.stderr)

        state, error, prov = client.fetch_clearinghouse_state(addr)
        if state is None:
            errors.append({"address": addr[:10], "label": label,
                           "error_type": "clearinghouse_failed",
                           "message_summary": error or "No response"})
            print(f"      [DEGRADED] {error}", file=sys.stderr)
            continue

        count = 0
        for raw_pos in state.get("assetPositions", []):
            pos = raw_pos.get("position", {}) if isinstance(raw_pos, dict) else raw_pos
            if not pos:
                continue
            mapped = map_raw_position(pos, addr, label, entry.entity_type,
                                      entry.label_confidence, mids, snapshot_time, prov)
            if mapped:
                all_positions.append(mapped)
                count += 1

        healthy_count += 1
        print(f"      {count} positions ({prov.data_mode.value if prov else '?'})", file=sys.stderr)

    # Validate
    validation = validate_positions_batch(all_positions)
    print(f"  Validation: {validation['passed']}/{validation['total']} passed", file=sys.stderr)

    # Strip provenance from output
    clean = []
    provenance_list = []
    for p in all_positions:
        prov = p.pop("_provenance", None)
        if prov:
            provenance_list.append(prov)
        clean.append(p)

    overall = "healthy" if healthy_count > 0 else "degraded"
    data_mode_counts = {
        "live": sum(1 for p in all_positions if p.get("_provenance", {}).get("data_mode") == "live"),
        "cached": 0, "fixture": 0,
    }

    output = {
        "run_id": run_id, "snapshot_time_utc": snapshot_time,
        "lane": "lane1_hyperliquid_w2",
        "positions": clean,
        "address_universe": universe.to_dict(),
        "data_mode_counts": data_mode_counts,
        "validation": validation,
        "provenance_records": provenance_list,
        "source_health": make_source_health(
            source="hyperliquid_info_public", status=overall, occurred_at_utc=snapshot_time,
            message_summary=f"{len(clean)} positions from {healthy_count} addresses",
        ),
    }
    if errors:
        output["errors"] = errors

    op = os.path.join(OUTPUT_DIR, "lane1_whale_positions.json")
    with open(op, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    elapsed = time.time() - start_time
    print(f"\n  Done in {elapsed:.1f}s. {len(clean)} positions.", file=sys.stderr)
    print(f"  Output: {op}", file=sys.stderr)
    return 0 if overall == "healthy" else 1


if __name__ == "__main__":
    sys.exit(main())
