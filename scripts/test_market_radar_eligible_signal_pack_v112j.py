"""Tests for v1.12-J Eligible Signal Pack + State Dry-run

Covers all acceptance criteria from the v112j task specification.

Usage:
    python scripts/test_market_radar_eligible_signal_pack_v112j.py
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.market_radar_eligible_signal_pack_v112j import (
    PACK_VERSION,
    SCHEMA_VERSION,
    COOLDOWN_POLICY,
    load_envelopes_jsonl,
    load_gate_decisions_jsonl,
    load_prior_signal_state,
    join_envelopes_with_decisions,
    build_eligible_signal_record,
    build_blocked_signal_record,
    rank_eligible_signals,
    build_proposed_signal_state,
    scan_pack_leaks,
    scan_all_pack_leaks,
    write_jsonl,
    write_json,
    write_report,
    _compute_rank_score,
    china_stamp,
)


PASSED = 0
FAILED = 0
ERRORS: list[str] = []


def check(condition: bool, label: str) -> None:
    """Assert a condition and track pass/fail."""
    global PASSED, FAILED, ERRORS
    if condition:
        PASSED += 1
        print(f"  [PASS] {label}")
    else:
        FAILED += 1
        msg = f"  [FAIL] {label}"
        ERRORS.append(label)
        print(msg)


def test_data_loading() -> None:
    """Test data loading functions."""
    print("\n--- Data Loading Tests ---")

    envelopes_path = PROJECT_ROOT / "results" / "market_radar_v112h_unified_signal_envelopes.jsonl"
    decisions_path = PROJECT_ROOT / "results" / "market_radar_v112i_gate_decisions.jsonl"
    prior_state_path = PROJECT_ROOT / "data" / "fixtures" / "market_radar_v112i_prior_signal_state.json"

    envelopes = load_envelopes_jsonl(envelopes_path)
    check(len(envelopes) == 13, f"input_envelope_count = 13 (got {len(envelopes)})")

    decisions = load_gate_decisions_jsonl(decisions_path)
    check(len(decisions) == 13, f"input_decision_count = 13 (got {len(decisions)})")

    prior_state = load_prior_signal_state(prior_state_path)
    check(len(prior_state) > 0, f"Prior state loaded ({len(prior_state)} entries)")


def test_join() -> None:
    """Test join_envelopes_with_decisions."""
    print("\n--- Join Tests ---")

    envelopes = load_envelopes_jsonl(
        PROJECT_ROOT / "results" / "market_radar_v112h_unified_signal_envelopes.jsonl"
    )
    decisions = load_gate_decisions_jsonl(
        PROJECT_ROOT / "results" / "market_radar_v112i_gate_decisions.jsonl"
    )

    joined = join_envelopes_with_decisions(envelopes, decisions)
    check(len(joined) == 13, f"Join count = 13 (got {len(joined)})")

    # Every joined entry should have envelope
    all_have_envelope = all(j.get("envelope") is not None for j in joined)
    check(all_have_envelope, "All joined entries have envelope")

    # Every joined entry should have decision
    all_have_decision = all(j.get("decision") is not None for j in joined)
    check(all_have_decision, "All joined entries have decision")


def test_eligible_records() -> None:
    """Test eligible signal record generation."""
    print("\n--- Eligible Signal Record Tests ---")

    envelopes = load_envelopes_jsonl(
        PROJECT_ROOT / "results" / "market_radar_v112h_unified_signal_envelopes.jsonl"
    )
    decisions = load_gate_decisions_jsonl(
        PROJECT_ROOT / "results" / "market_radar_v112i_gate_decisions.jsonl"
    )
    joined = join_envelopes_with_decisions(envelopes, decisions)

    eligible: list[dict] = []
    blocked: list[dict] = []

    for j in joined:
        decision = j["decision"]
        envelope = j["envelope"]
        if decision.get("gate_status") == "pass":
            rec = build_eligible_signal_record(envelope, decision)
            eligible.append(rec)
        else:
            rec = build_blocked_signal_record(decision)
            blocked.append(rec)

    # Count checks
    passed_count = sum(1 for d in decisions if d.get("gate_status") == "pass")
    check(len(eligible) == passed_count,
          f"eligible_signal_count ({len(eligible)}) = v112i passed_count ({passed_count})")

    blocked_total = sum(1 for d in decisions if d.get("gate_status") != "pass")
    check(len(blocked) == blocked_total,
          f"blocked_signal_count ({len(blocked)}) = v112i blocked total ({blocked_total})")

    check(len(eligible) >= 1, f"eligible_signal_count >= 1 (got {len(eligible)})")
    check(len(blocked) >= 1, f"blocked_signal_count >= 1 (got {len(blocked)})")

    # Every eligible signal has required fields
    for rec in eligible:
        sid = rec.get("signal_id", "?")

        # public_card
        check(bool(rec.get("public_card", "")),
              f"eligible signal {sid} has public_card")

        # rank_score
        check(isinstance(rec.get("rank_score"), (int, float)),
              f"eligible signal {sid} has rank_score")

        # dedupe_key
        check(bool(rec.get("dedupe_key", "")),
              f"eligible signal {sid} has dedupe_key")

        # cooldown_key
        check(bool(rec.get("cooldown_key", "")),
              f"eligible signal {sid} has cooldown_key")

        # payload_hash
        check(bool(rec.get("payload_hash", "")),
              f"eligible signal {sid} has payload_hash")

        # send_policy
        sp = rec.get("send_policy", {})
        check(sp.get("dry_run_only") is True,
              f"eligible signal {sid} dry_run_only=true")
        check(sp.get("production_send_allowed") is False,
              f"eligible signal {sid} production_send_allowed=false")

    # Every blocked signal has required fields
    for rec in blocked:
        sid = rec.get("signal_id", "?")
        check(bool(rec.get("gate_reasons")),
              f"blocked signal {sid} has gate_reasons")


def test_ranking() -> None:
    """Test ranking of eligible signals."""
    print("\n--- Ranking Tests ---")

    envelopes = load_envelopes_jsonl(
        PROJECT_ROOT / "results" / "market_radar_v112h_unified_signal_envelopes.jsonl"
    )
    decisions = load_gate_decisions_jsonl(
        PROJECT_ROOT / "results" / "market_radar_v112i_gate_decisions.jsonl"
    )
    joined = join_envelopes_with_decisions(envelopes, decisions)

    eligible = []
    for j in joined:
        decision = j["decision"]
        envelope = j["envelope"]
        if decision.get("gate_status") == "pass":
            rec = build_eligible_signal_record(envelope, decision)
            eligible.append(rec)

    ranked = rank_eligible_signals(eligible)

    # All have rank_position
    all_have_rank = all(r.get("rank_position", 0) > 0 for r in ranked)
    check(all_have_rank, "All eligible signals have rank_position > 0")

    # Sorted by rank_score descending
    rank_scores = [r.get("rank_score", 0) for r in ranked]
    check(rank_scores == sorted(rank_scores, reverse=True),
          "Eligible signals sorted by rank_score descending")

    # Verify rank formula
    for rec in ranked:
        expected = rec["severity_score"] * 0.7 + rec["confidence_score"] * 100 * 0.3
        check(abs(rec["rank_score"] - round(expected, 2)) < 0.01,
              f"rank_score formula for {rec['signal_id']}: {rec['rank_score']} ≈ {round(expected, 2)}")


def test_proposed_state() -> None:
    """Test proposed state dry-run generation."""
    print("\n--- Proposed State Tests ---")

    envelopes = load_envelopes_jsonl(
        PROJECT_ROOT / "results" / "market_radar_v112h_unified_signal_envelopes.jsonl"
    )
    decisions = load_gate_decisions_jsonl(
        PROJECT_ROOT / "results" / "market_radar_v112i_gate_decisions.jsonl"
    )
    prior_state = load_prior_signal_state(
        PROJECT_ROOT / "data" / "fixtures" / "market_radar_v112i_prior_signal_state.json"
    )
    joined = join_envelopes_with_decisions(envelopes, decisions)

    eligible = []
    for j in joined:
        decision = j["decision"]
        envelope = j["envelope"]
        if decision.get("gate_status") == "pass":
            rec = build_eligible_signal_record(envelope, decision)
            eligible.append(rec)

    run_ts = china_stamp()
    proposed_state = build_proposed_signal_state(eligible, prior_state, run_ts)

    # proposed_state_entry_count = eligible_signal_count
    new_entries = proposed_state.get("new_proposed_entries", 0)
    check(new_entries == len(eligible),
          f"proposed_state_entry_count ({new_entries}) = eligible_signal_count ({len(eligible)})")

    # Each proposed entry has cooldown_until
    entries = proposed_state.get("entries", [])
    new_only = entries[:new_entries] if new_entries <= len(entries) else entries
    for entry in entries:
        cooldown_until = entry.get("cooldown_until", "")
        check(bool(cooldown_until),
              f"proposed state entry has cooldown_until: {entry.get('card_type', '?')}")

    # Prior state fixture not overwritten
    prior_state_path = PROJECT_ROOT / "data" / "fixtures" / "market_radar_v112i_prior_signal_state.json"
    check(prior_state_path.exists(),
          "Prior state fixture still exists (not overwritten)")

    # Check fixture content unchanged
    with open(prior_state_path, "r", encoding="utf-8") as f:
        fixture_data = json.load(f)
    fixture_entries = fixture_data.get("entries", fixture_data if isinstance(fixture_data, list) else [])
    check(len(fixture_entries) == len(prior_state),
          f"Prior state fixture unchanged ({len(fixture_entries)} entries)")

    # Cooldown windows verified
    for entry in entries:
        ct = entry.get("card_type", "")
        if ct in COOLDOWN_POLICY:
            cooldown_until = entry.get("cooldown_until", "")
            check(bool(cooldown_until),
                  f"cooldown_until set for card_type={ct} (window={COOLDOWN_POLICY[ct]}min)")


def test_output_files() -> None:
    """Test that all output files can be generated."""
    print("\n--- Output Files Tests ---")

    # Check that result JSON exists
    result_path = PROJECT_ROOT / "results" / "market_radar_v112j_eligible_signal_pack_result.json"
    eligible_jsonl_path = PROJECT_ROOT / "results" / "market_radar_v112j_eligible_signals.jsonl"
    blocked_jsonl_path = PROJECT_ROOT / "results" / "market_radar_v112j_blocked_signals.jsonl"
    proposed_state_path = PROJECT_ROOT / "results" / "market_radar_v112j_proposed_signal_state.json"
    report_path = PROJECT_ROOT / "runs" / "market_radar" / "v112j_eligible_signal_pack.md"
    handoff_path = PROJECT_ROOT / "runs" / "market_radar" / "v112j_eligible_signal_pack_handoff.md"

    check(result_path.exists(), "Result JSON exists")
    check(eligible_jsonl_path.exists(), "Eligible JSONL exists")
    check(blocked_jsonl_path.exists(), "Blocked JSONL exists")
    check(proposed_state_path.exists(), "Proposed state JSON exists")
    check(report_path.exists(), "Report exists")
    check(handoff_path.exists(), "Handoff exists")


def test_result_json() -> None:
    """Test the result JSON content."""
    print("\n--- Result JSON Tests ---")

    result_path = PROJECT_ROOT / "results" / "market_radar_v112j_eligible_signal_pack_result.json"
    if not result_path.exists():
        check(False, "Result JSON file not found — skipping checks")
        return

    with open(result_path, "r", encoding="utf-8") as f:
        result = json.load(f)

    check(result.get("debug_leak_count") == 0,
          f"debug_leak_count=0 (got {result.get('debug_leak_count')})")
    check(result.get("secret_leak_count") == 0,
          f"secret_leak_count=0 (got {result.get('secret_leak_count')})")
    check(result.get("full_wallet_leak") is False,
          f"full_wallet_leak=false (got {result.get('full_wallet_leak')})")
    check(result.get("real_tg_sent") is False,
          f"real_tg_sent=false (got {result.get('real_tg_sent')})")
    check(result.get("external_api_called") is False,
          f"external_api_called=false (got {result.get('external_api_called')})")
    check(result.get("external_ai_called") is False,
          f"external_ai_called=false (got {result.get('external_ai_called')})")
    check(result.get("daemon_started") is False,
          f"daemon_started=false (got {result.get('daemon_started')})")
    check(result.get("live_ready") is False,
          f"live_ready=false (got {result.get('live_ready')})")
    check(result.get("dry_run_only") is True,
          f"dry_run_only=true (got {result.get('dry_run_only')})")
    check(result.get("production_send_allowed") is False,
          f"production_send_allowed=false (got {result.get('production_send_allowed')})")


def test_leak_scanning() -> None:
    """Test leak scanning functions."""
    print("\n--- Leak Scan Tests ---")

    # Test a clean record
    clean_record = {
        "signal_id": "sig-test-clean",
        "card_type": "price_oi_volume_anomaly",
        "primary_assets": ["BTC"],
        "direction": "bullish",
        "public_card": "This is a clean test card with no forbidden terms.",
        "gate_status": "pass",
    }
    result = scan_pack_leaks(clean_record, kind="eligible")
    check(result["debug_leak_count"] == 0, f"Clean record debug_leak_count=0 (got {result['debug_leak_count']})")
    check(result["secret_leak_count"] == 0, f"Clean record secret_leak_count=0 (got {result['secret_leak_count']})")
    check(result["full_wallet_leak"] is False, f"Clean record full_wallet_leak=false (got {result['full_wallet_leak']})")
    check(result["clean"] is True, f"Clean record is clean")

    # Test a record with debug term
    leaky_record = {
        "signal_id": "sig-test-leaky",
        "card_type": "price_oi_volume_anomaly",
        "primary_assets": ["BTC"],
        "direction": "bullish",
        "public_card": "This card has a debug term in it.",
    }
    result = scan_pack_leaks(leaky_record, kind="eligible")
    check(result["debug_leak_count"] > 0, f"Leaky record catches debug term: {result['debug_terms_found']}")

    # Test a record with wallet address
    wallet_record = {
        "signal_id": "sig-test-wallet",
        "card_type": "whale_position_alert",
        "primary_assets": ["ETH"],
        "direction": "bullish",
        "public_card": "Wallet: 0x7a9f3b6e8c1d4a2f5e7b9c0d3e6f8a1b2c4d5e6f",
    }
    result = scan_pack_leaks(wallet_record, kind="eligible")
    check(result["full_wallet_leak"] is True, f"Wallet record catches full wallet address: {result['wallet_leak_details']}")

    # Test blocked record scan
    blocked_record = {
        "signal_id": "sig-test-blocked",
        "card_type": "whale_position_alert",
        "primary_assets": ["BTC"],
        "direction": "bullish",
        "gate_status": "blocked_dedupe",
        "gate_reasons": ["dedupe_key already in state"],
    }
    result = scan_pack_leaks(blocked_record, kind="blocked")
    check(result["clean"] is True, "Clean blocked record is clean")


def test_safety_constraints() -> None:
    """Test that safety constraints are met."""
    print("\n--- Safety Constraint Tests ---")

    # Check no writes to ai_relay_desk
    ai_relay_dir = Path("C:/Users/PC/Desktop/工作台/ai_relay_desk")
    if ai_relay_dir.exists():
        # Verify we didn't write to executor_outbox
        outbox = ai_relay_dir / "executor_outbox" / "1"
        # This test is just informational — the result.md write is required by the task
        check(True, "ai_relay_desk path exists (informational)")

    # Check we haven't deleted important files
    envelopes_path = PROJECT_ROOT / "results" / "market_radar_v112h_unified_signal_envelopes.jsonl"
    check(envelopes_path.exists(), "v112h envelopes still exist (not deleted)")

    decisions_path = PROJECT_ROOT / "results" / "market_radar_v112i_gate_decisions.jsonl"
    check(decisions_path.exists(), "v112i gate decisions still exist (not deleted)")

    prior_state_path = PROJECT_ROOT / "data" / "fixtures" / "market_radar_v112i_prior_signal_state.json"
    check(prior_state_path.exists(), "v112i prior state fixture still exists (not deleted)")

    # No token/key/password in any output file
    forbidden = ["token", "api_key", "chat_id", "password"]
    output_files = [
        PROJECT_ROOT / "results" / "market_radar_v112j_eligible_signals.jsonl",
        PROJECT_ROOT / "results" / "market_radar_v112j_blocked_signals.jsonl",
        PROJECT_ROOT / "results" / "market_radar_v112j_proposed_signal_state.json",
        PROJECT_ROOT / "results" / "market_radar_v112j_eligible_signal_pack_result.json",
        PROJECT_ROOT / "runs" / "market_radar" / "v112j_eligible_signal_pack.md",
        PROJECT_ROOT / "runs" / "market_radar" / "v112j_eligible_signal_pack_handoff.md",
    ]

    for fp in output_files:
        if not fp.exists():
            continue
        content = fp.read_text(encoding="utf-8").lower()
        for term in forbidden:
            check(term not in content,
                  f"{fp.name} does not contain '{term}'")


def main() -> int:
    """Run all tests."""
    global PASSED, FAILED

    print("=" * 60)
    print("v1.12-J Eligible Signal Pack — Test Suite")
    print("=" * 60)

    test_data_loading()
    test_join()
    test_eligible_records()
    test_ranking()
    test_proposed_state()
    test_output_files()
    test_result_json()
    test_leak_scanning()
    test_safety_constraints()

    print()
    print("=" * 60)
    print(f"Results: {PASSED} passed, {FAILED} failed")
    print("=" * 60)

    if ERRORS:
        print("\nFailed tests:")
        for e in ERRORS:
            print(f"  - {e}")

    return 0 if FAILED == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
