"""Runner — v1.12-J Eligible Signal Pack + State Dry-run

Reads v112h envelopes and v112i gate decisions, produces:
  - Eligible signals JSONL
  - Blocked signals JSONL
  - Proposed state dry-run JSON
  - Summary result JSON
  - Markdown report + handoff

Usage:
    python scripts/run_market_radar_v112j_eligible_signal_pack_and_state_dryrun.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# Ensure project root is on path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.market_radar_eligible_signal_pack_v112j import (
    PACK_VERSION,
    SCHEMA_VERSION,
    load_envelopes_jsonl,
    load_gate_decisions_jsonl,
    load_prior_signal_state,
    join_envelopes_with_decisions,
    build_eligible_signal_record,
    build_blocked_signal_record,
    rank_eligible_signals,
    build_proposed_signal_state,
    scan_all_pack_leaks,
    write_jsonl,
    write_json,
    write_report,
    china_stamp,
)


def main() -> int:
    run_ts = china_stamp()
    print(f"=== Market Radar v1.12-J Eligible Signal Pack + State Dry-run ===")
    print(f"Run timestamp: {run_ts}")
    print()

    # ── Paths ───────────────────────────────────────────────────────────────────
    envelopes_path = PROJECT_ROOT / "results" / "market_radar_v112h_unified_signal_envelopes.jsonl"
    decisions_path = PROJECT_ROOT / "results" / "market_radar_v112i_gate_decisions.jsonl"
    prior_state_path = PROJECT_ROOT / "data" / "fixtures" / "market_radar_v112i_prior_signal_state.json"

    eligible_jsonl_path = PROJECT_ROOT / "results" / "market_radar_v112j_eligible_signals.jsonl"
    blocked_jsonl_path = PROJECT_ROOT / "results" / "market_radar_v112j_blocked_signals.jsonl"
    proposed_state_path = PROJECT_ROOT / "results" / "market_radar_v112j_proposed_signal_state.json"
    result_json_path = PROJECT_ROOT / "results" / "market_radar_v112j_eligible_signal_pack_result.json"
    report_path = PROJECT_ROOT / "runs" / "market_radar" / "v112j_eligible_signal_pack.md"
    handoff_path = PROJECT_ROOT / "runs" / "market_radar" / "v112j_eligible_signal_pack_handoff.md"

    # ── Step 1: Load inputs ─────────────────────────────────────────────────────
    print("[1/7] Loading v112h envelopes...")
    envelopes = load_envelopes_jsonl(envelopes_path)
    print(f"  Loaded {len(envelopes)} envelopes")

    print("[2/7] Loading v112i gate decisions...")
    decisions = load_gate_decisions_jsonl(decisions_path)
    print(f"  Loaded {len(decisions)} gate decisions")

    print("[3/7] Loading prior signal state...")
    prior_state = load_prior_signal_state(prior_state_path)
    print(f"  Loaded {len(prior_state)} prior state entries")

    # ── Step 2: Join envelopes with decisions ────────────────────────────────────
    print("[4/7] Joining envelopes with decisions...")
    joined = join_envelopes_with_decisions(envelopes, decisions)
    print(f"  Joined {len(joined)} records")

    # ── Step 3: Build eligible and blocked records ───────────────────────────────
    print("[5/7] Building eligible and blocked signal records...")
    eligible_records: list[dict] = []
    blocked_records: list[dict] = []

    for j in joined:
        decision = j.get("decision")
        envelope = j.get("envelope")

        if decision is None:
            # No decision — treat as blocked (no gate evaluation)
            # Skip, as per task spec we only process envelopes with decisions
            continue

        gate_status = decision.get("gate_status", "")
        if gate_status == "pass":
            rec = build_eligible_signal_record(envelope, decision)
            eligible_records.append(rec)
        else:
            rec = build_blocked_signal_record(decision)
            blocked_records.append(rec)

    # ── Step 4: Rank eligible signals ───────────────────────────────────────────
    eligible_records = rank_eligible_signals(eligible_records)
    print(f"  Eligible: {len(eligible_records)}, Blocked: {len(blocked_records)}")

    # ── Step 5: Build proposed state dry-run ────────────────────────────────────
    print("[6/7] Building proposed state dry-run...")
    proposed_state = build_proposed_signal_state(eligible_records, prior_state, run_ts)
    print(f"  Proposed state entries: {len(proposed_state.get('entries', []))}")

    # ── Step 6: Leak scan ────────────────────────────────────────────────────────
    print("[7/7] Running leak scan...")
    leak_result = scan_all_pack_leaks(eligible_records, blocked_records, proposed_state)
    print(f"  Debug leaks: {leak_result['debug_leak_count']}")
    print(f"  Secret leaks: {leak_result['secret_leak_count']}")
    print(f"  Full wallet leak: {leak_result['full_wallet_leak']}")

    # ── Build card type summary ──────────────────────────────────────────────────
    card_types: dict[str, dict[str, int]] = {}
    all_card_types = set()

    for rec in eligible_records:
        ct = rec.get("card_type", "unknown")
        all_card_types.add(ct)
        if ct not in card_types:
            card_types[ct] = {"total": 0, "eligible": 0, "blocked": 0}
        card_types[ct]["total"] += 1
        card_types[ct]["eligible"] += 1

    for rec in blocked_records:
        ct = rec.get("card_type", "unknown")
        all_card_types.add(ct)
        if ct not in card_types:
            card_types[ct] = {"total": 0, "eligible": 0, "blocked": 0}
        card_types[ct]["total"] += 1
        card_types[ct]["blocked"] += 1

    # ── Build result JSON ───────────────────────────────────────────────────────
    top_ranked = eligible_records[0] if eligible_records else {}
    new_proposed_entries = proposed_state.get("new_proposed_entries", 0)

    result = {
        "version": PACK_VERSION,
        "schema_version": SCHEMA_VERSION,
        "run_id": "20260604_202718",
        "generated_at": run_ts,
        "input_envelope_count": len(envelopes),
        "input_decision_count": len(decisions),
        "eligible_signal_count": len(eligible_records),
        "blocked_signal_count": len(blocked_records),
        "proposed_state_entry_count": new_proposed_entries,
        "top_ranked_signal_id": top_ranked.get("signal_id", ""),
        "top_ranked_card_type": top_ranked.get("card_type", ""),
        "card_type_summary": card_types,
        "debug_leak_count": leak_result["debug_leak_count"],
        "secret_leak_count": leak_result["secret_leak_count"],
        "full_wallet_leak": leak_result["full_wallet_leak"],
        "real_tg_sent": False,
        "external_api_called": False,
        "external_ai_called": False,
        "daemon_started": False,
        "live_ready": False,
        "dry_run_only": True,
        "production_send_allowed": False,
    }

    # ── Write outputs ────────────────────────────────────────────────────────────
    print()
    print("Writing output files...")

    write_jsonl(eligible_records, eligible_jsonl_path)
    print(f"  -> {eligible_jsonl_path}")

    write_jsonl(blocked_records, blocked_jsonl_path)
    print(f"  -> {blocked_jsonl_path}")

    write_json(proposed_state, proposed_state_path)
    print(f"  -> {proposed_state_path}")

    write_json(result, result_json_path)
    print(f"  -> {result_json_path}")

    write_report(result, eligible_records, blocked_records, proposed_state,
                 report_path, handoff_path, run_ts)
    print(f"  -> {report_path}")
    print(f"  -> {handoff_path}")

    print()
    print("=== Done — v1.12-J eligible signal pack + state dry-run complete ===")
    print(f"Eligible signals: {len(eligible_records)}")
    print(f"Blocked signals: {len(blocked_records)}")
    print(f"Proposed state entries: {new_proposed_entries}")
    print(f"Leaks: debug={leak_result['debug_leak_count']}, secret={leak_result['secret_leak_count']}")
    print(f"Top signal: {top_ranked.get('signal_id', 'N/A')} ({top_ranked.get('card_type', 'N/A')})")

    return 0


if __name__ == "__main__":
    sys.exit(main())
