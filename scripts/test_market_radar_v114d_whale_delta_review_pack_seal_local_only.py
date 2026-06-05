#!/usr/bin/env python3
"""
Test suite for v114D Whale Delta Review Pack Seal — Local Only
================================================================
Validates that the v114D seal runner produced correct outputs with all
safety invariants, proper chain consistency, BTC closed_position sealed,
and all routing guards verified.

This test ONLY verifies generated files — it does NOT make any
external API calls.
"""

import json
import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RESULTS_DIR = os.path.join(BASE_DIR, "results")
RUNS_DIR = os.path.join(BASE_DIR, "runs", "market_radar")

# v114D outputs
V114D_SEAL = os.path.join(RESULTS_DIR, "market_radar_v114d_whale_delta_review_pack_seal_result.json")
V114D_MANIFEST = os.path.join(RESULTS_DIR, "market_radar_v114d_whale_delta_review_pack_manifest.json")
V114D_REPORT = os.path.join(RUNS_DIR, "v114d_whale_delta_review_pack_seal_local_only.md")
V114D_HANDOFF = os.path.join(RUNS_DIR, "v114d_whale_delta_review_pack_seal_local_only_handoff.md")

# Reference files for cross-validation
V114A_RESULT = os.path.join(RESULTS_DIR, "market_radar_v114a_whale_position_baseline_snapshot_result.json")
V114A_POSITIONS = os.path.join(RESULTS_DIR, "market_radar_v114a_whale_position_baseline_positions.jsonl")
V114B_RESULT = os.path.join(RESULTS_DIR, "market_radar_v114b_whale_delta_compare_result.json")
V114B_DELTAS = os.path.join(RESULTS_DIR, "market_radar_v114b_whale_position_deltas.jsonl")
V114C_RESULT = os.path.join(RESULTS_DIR, "market_radar_v114c_whale_delta_operator_review_pack_result.json")
V114C_CARDS = os.path.join(RESULTS_DIR, "market_radar_v114c_whale_delta_operator_review_cards.jsonl")

passed = 0
failed = 0
failures = []


def check(description: str, condition: bool, detail: str = ""):
    global passed, failed, failures
    if condition:
        passed += 1
        print(f"  [PASS] {description}")
    else:
        failed += 1
        msg = f"  [FAIL] {description}"
        if detail:
            msg += f" — {detail}"
        print(msg)
        failures.append(msg)


def file_exists(path: str) -> bool:
    if not os.path.exists(path):
        return False
    try:
        with open(path, "r", encoding="utf-8") as f:
            f.read(1)
        return True
    except Exception:
        return False


def load_json(path: str):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_jsonl(path: str) -> list:
    records = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


def main():
    global passed, failed

    print("=" * 70)
    print("v114D Test Suite — Whale Delta Review Pack Seal Local Only")
    print("=" * 70)

    # ==================================================================
    # 1. File existence
    # ==================================================================
    print("\n[1] File Existence")
    check("seal result JSON exists", file_exists(V114D_SEAL))
    check("manifest JSON exists", file_exists(V114D_MANIFEST))
    check("markdown seal report exists", file_exists(V114D_REPORT))
    check("handoff markdown exists", file_exists(V114D_HANDOFF))

    # ==================================================================
    # 2. Load data
    # ==================================================================
    print("\n[2] Data Loading")
    seal = load_json(V114D_SEAL)
    manifest = load_json(V114D_MANIFEST)

    check("seal result JSON parsed", isinstance(seal, dict))
    check("manifest JSON parsed", isinstance(manifest, dict))

    # Load reference data for cross-validation
    v114a_result = load_json(V114A_RESULT)
    v114a_positions = load_jsonl(V114A_POSITIONS)
    v114b_result = load_json(V114B_RESULT)
    v114b_deltas = load_jsonl(V114B_DELTAS)
    v114c_result = load_json(V114C_RESULT)
    v114c_cards = load_jsonl(V114C_CARDS)

    check("v114A baseline positions loaded", len(v114a_positions) > 0,
          f"got {len(v114a_positions)}")
    check("v114B deltas loaded", len(v114b_deltas) > 0,
          f"got {len(v114b_deltas)}")
    check("v114C review cards loaded", len(v114c_cards) > 0,
          f"got {len(v114c_cards)}")

    # ==================================================================
    # 3. Seal result — top-level fields
    # ==================================================================
    print("\n[3] Seal Result — Top-Level Fields")
    check("version = v114D",
          seal.get("version") == "v114D",
          f"got: {seal.get('version')}")
    check("status = passed",
          seal.get("status") == "passed",
          f"got: {seal.get('status')}")
    check("sealed = true",
          seal.get("sealed") is True,
          f"got: {seal.get('sealed')}")
    check("local_only = true",
          seal.get("local_only") is True,
          f"got: {seal.get('local_only')}")
    check("stage_conclusion = local_delta_review_ready_not_send_ready",
          seal.get("stage_conclusion") == "local_delta_review_ready_not_send_ready",
          f"got: {seal.get('stage_conclusion')}")

    # ==================================================================
    # 4. Required artifacts
    # ==================================================================
    print("\n[4] Required Artifacts")
    check("all_required_artifacts_present = true",
          seal.get("all_required_artifacts_present") is True,
          f"got: {seal.get('all_required_artifacts_present')}")

    required_files = [
        V114A_RESULT, V114A_POSITIONS,
        V114B_RESULT, V114B_DELTAS,
        V114C_RESULT, V114C_CARDS,
        V114D_SEAL, V114D_MANIFEST, V114D_REPORT, V114D_HANDOFF,
    ]
    for f in required_files:
        check(f"artifact exists: {os.path.basename(f)}", file_exists(f))

    # ==================================================================
    # 5. Chain counts
    # ==================================================================
    print("\n[5] Chain Counts")
    check("v114A baseline records = 10",
          len(v114a_positions) == 10,
          f"got: {len(v114a_positions)}")
    check("v114A result baseline_records_written = 10",
          v114a_result.get("baseline_records_written") == 10,
          f"got: {v114a_result.get('baseline_records_written')}")
    check("v114B delta records = 10",
          len(v114b_deltas) == 10,
          f"got: {len(v114b_deltas)}")
    check("v114B result delta_records_written = 10",
          v114b_result.get("delta_records_written") == 10,
          f"got: {v114b_result.get('delta_records_written')}")
    check("v114C operator review cards = 10",
          len(v114c_cards) == 10,
          f"got: {len(v114c_cards)}")
    check("v114C result operator_review_cards_written = 10",
          v114c_result.get("operator_review_cards_written") == 10,
          f"got: {v114c_result.get('operator_review_cards_written')}")
    check("chain_counts_consistent = true",
          seal.get("chain_counts_consistent") is True,
          f"got: {seal.get('chain_counts_consistent')}")

    # ==================================================================
    # 6. Delta summary
    # ==================================================================
    print("\n[6] Delta Summary")
    # From v114B deltas
    b_closed = sum(1 for d in v114b_deltas if d.get("delta_type") == "closed_position")
    b_changed = sum(1 for d in v114b_deltas if d.get("delta_type") == "size_changed")
    b_unchanged = sum(1 for d in v114b_deltas if d.get("delta_type") == "unchanged")
    b_new = sum(1 for d in v114b_deltas if d.get("delta_type") == "new_position")

    check("closed_position_count = 1",
          b_closed == 1, f"got: {b_closed}")
    check("size_changed_count = 5",
          b_changed == 5, f"got: {b_changed}")
    check("unchanged_count = 4",
          b_unchanged == 4, f"got: {b_unchanged}")
    check("new_position_count = 0",
          b_new == 0, f"got: {b_new}")

    # From v114C cards
    c_closed = sum(1 for c in v114c_cards if c.get("delta_type") == "closed_position")
    c_changed = sum(1 for c in v114c_cards if c.get("delta_type") == "size_changed")
    c_unchanged = sum(1 for c in v114c_cards if c.get("delta_type") == "unchanged")
    c_new = sum(1 for c in v114c_cards if c.get("delta_type") == "new_position")

    check("v114B→v114C closed_position consistent", b_closed == c_closed)
    check("v114B→v114C size_changed consistent", b_changed == c_changed)
    check("v114B→v114C unchanged consistent", b_unchanged == c_unchanged)
    check("v114B→v114C new_position consistent", b_new == c_new)

    # From manifest
    manifest_delta = manifest.get("delta_summary", {})
    check("manifest delta_summary.closed_position = 1",
          manifest_delta.get("closed_position") == 1,
          f"got: {manifest_delta.get('closed_position')}")
    check("manifest delta_summary.size_changed = 5",
          manifest_delta.get("size_changed") == 5,
          f"got: {manifest_delta.get('size_changed')}")
    check("manifest delta_summary.unchanged = 4",
          manifest_delta.get("unchanged") == 4,
          f"got: {manifest_delta.get('unchanged')}")
    check("manifest delta_summary.new_position = 0",
          manifest_delta.get("new_position") == 0,
          f"got: {manifest_delta.get('new_position')}")

    # ==================================================================
    # 7. Attention summary
    # ==================================================================
    print("\n[7] Attention Summary")
    c_high = sum(1 for c in v114c_cards if c.get("operator_attention_level") == "high")
    c_medium = sum(1 for c in v114c_cards if c.get("operator_attention_level") == "medium")
    c_low = sum(1 for c in v114c_cards if c.get("operator_attention_level") == "low")

    check("high_attention_count = 1",
          c_high == 1, f"got: {c_high}")
    check("medium_attention_count = 5",
          c_medium == 5, f"got: {c_medium}")
    check("low_attention_count = 4",
          c_low == 4, f"got: {c_low}")

    manifest_attn = manifest.get("attention_summary", {})
    check("manifest attention_summary.high = 1",
          manifest_attn.get("high") == 1,
          f"got: {manifest_attn.get('high')}")
    check("manifest attention_summary.medium = 5",
          manifest_attn.get("medium") == 5,
          f"got: {manifest_attn.get('medium')}")
    check("manifest attention_summary.low = 4",
          manifest_attn.get("low") == 4,
          f"got: {manifest_attn.get('low')}")

    # ==================================================================
    # 8. BTC short closed_position
    # ==================================================================
    print("\n[8] BTC Short Closed Position")
    btc_cards = [
        c for c in v114c_cards
        if c.get("delta_type") == "closed_position"
        and c.get("asset") == "BTC"
        and c.get("side") == "short"
    ]
    check("BTC short closed_position exists",
          len(btc_cards) >= 1, f"found {len(btc_cards)} cards")

    if btc_cards:
        c = btc_cards[0]
        check("BTC closed_position asset = BTC",
              c.get("asset") == "BTC", f"got: {c.get('asset')}")
        check("BTC closed_position side = short",
              c.get("side") == "short", f"got: {c.get('side')}")
        check("BTC closed_position delta_type = closed_position",
              c.get("delta_type") == "closed_position",
              f"got: {c.get('delta_type')}")
        check("BTC closed_position operator_attention_level = high",
              c.get("operator_attention_level") == "high",
              f"got: {c.get('operator_attention_level')}")
        check("BTC closed_position NOT written as error",
              "error" not in c.get("review_summary", "").lower(),
              f"contains 'error': {c.get('review_summary', '')[:80]}")
        check("BTC closed_position NOT written as fault",
              "fault" not in c.get("review_summary", "").lower())
        check("btc_closed_position_verified = true",
              seal.get("btc_closed_position_verified") is True,
              f"got: {seal.get('btc_closed_position_verified')}")

    # Manifest key_event
    key_event = manifest.get("key_event", {})
    check("manifest key_event.asset = BTC",
          key_event.get("asset") == "BTC",
          f"got: {key_event.get('asset')}")
    check("manifest key_event.side = short",
          key_event.get("side") == "short",
          f"got: {key_event.get('side')}")
    check("manifest key_event.delta_type = closed_position",
          key_event.get("delta_type") == "closed_position",
          f"got: {key_event.get('delta_type')}")
    check("manifest key_event.operator_attention_level = high",
          key_event.get("operator_attention_level") == "high",
          f"got: {key_event.get('operator_attention_level')}")
    check("manifest key_event.not_error = true",
          key_event.get("not_error") is True,
          f"got: {key_event.get('not_error')}")

    # ==================================================================
    # 9. Per-card routing guards
    # ==================================================================
    print(f"\n[9] Per-Card Routing Guards ({len(v114c_cards)} cards)")
    for i, c in enumerate(v114c_cards):
        prefix = f"card[{i}] ({c.get('asset','?')} {c.get('delta_type','?')})"

        check(f"{prefix} operator_action = review_only_no_send",
              c.get("operator_action") == "review_only_no_send",
              f"got: {c.get('operator_action')}")
        check(f"{prefix} eligible_for_real_send = false",
              c.get("eligible_for_real_send") is False,
              f"got: {c.get('eligible_for_real_send')}")
        check(f"{prefix} tg_send_allowed = false",
              c.get("tg_send_allowed") is False,
              f"got: {c.get('tg_send_allowed')}")
        check(f"{prefix} local_review_only = true",
              c.get("local_review_only") is True,
              f"got: {c.get('local_review_only')}")
        check(f"{prefix} prod_state_write = false",
              c.get("prod_state_write") is False,
              f"got: {c.get('prod_state_write')}")
        check(f"{prefix} real_send_candidate = false",
              c.get("real_send_candidate") is False,
              f"got: {c.get('real_send_candidate')}")

    check("all_routing_guards_false",
          seal.get("all_routing_guards_false") is True,
          f"got: {seal.get('all_routing_guards_false')}")

    # ==================================================================
    # 10. Routing count checks
    # ==================================================================
    print("\n[10] Routing Count Checks")
    check("eligible_for_real_send_count = 0",
          seal.get("eligible_for_real_send_count") == 0,
          f"got: {seal.get('eligible_for_real_send_count')}")
    check("real_send_candidate_count = 0",
          seal.get("real_send_candidate_count") == 0,
          f"got: {seal.get('real_send_candidate_count')}")
    check("tg_send_allowed_count = 0",
          seal.get("tg_send_allowed_count") == 0,
          f"got: {seal.get('tg_send_allowed_count')}")

    # ==================================================================
    # 11. Safety invariants
    # ==================================================================
    print("\n[11] Safety Invariants")
    check("external_api_called = false",
          seal.get("external_api_called") is False)
    check("prod_state_write = false",
          seal.get("prod_state_write") is False)
    check("credentials_read = false",
          seal.get("credentials_read") is False)
    check("daemon_started = false",
          seal.get("daemon_started") is False)
    check("watcher_started = false",
          seal.get("watcher_started") is False)
    check("files_deleted = false",
          seal.get("files_deleted") is False)

    # Manifest safety
    m_safety = manifest.get("safety", {})
    check("manifest safety.external_api_called_in_this_step = false",
          m_safety.get("external_api_called_in_this_step") is False)
    check("manifest safety.eligible_for_real_send_count = 0",
          m_safety.get("eligible_for_real_send_count") == 0)
    check("manifest safety.real_send_candidate_count = 0",
          m_safety.get("real_send_candidate_count") == 0)
    check("manifest safety.tg_send_allowed_count = 0",
          m_safety.get("tg_send_allowed_count") == 0)
    check("manifest safety.prod_state_write = false",
          m_safety.get("prod_state_write") is False)
    check("manifest safety.credentials_read = false",
          m_safety.get("credentials_read") is False)
    check("manifest safety.daemon_started = false",
          m_safety.get("daemon_started") is False)
    check("manifest safety.watcher_started = false",
          m_safety.get("watcher_started") is False)
    check("manifest safety.files_deleted = false",
          m_safety.get("files_deleted") is False)

    # ==================================================================
    # 12. Manifest structure
    # ==================================================================
    print("\n[12] Manifest Structure")
    check("manifest version = v114D",
          manifest.get("version") == "v114D")
    check("manifest seal_type = whale_delta_review_pack_local_only",
          manifest.get("seal_type") == "whale_delta_review_pack_local_only")
    check("manifest sealed = true",
          manifest.get("sealed") is True)
    check("manifest stage_conclusion = local_delta_review_ready_not_send_ready",
          manifest.get("stage_conclusion") == "local_delta_review_ready_not_send_ready")
    check("manifest input_chain exists",
          isinstance(manifest.get("input_chain"), dict))
    check("manifest input_chain.v114a_baseline_records = 10",
          manifest.get("input_chain", {}).get("v114a_baseline_records") == 10)
    check("manifest input_chain.v114b_delta_records = 10",
          manifest.get("input_chain", {}).get("v114b_delta_records") == 10)
    check("manifest input_chain.v114c_operator_review_cards = 10",
          manifest.get("input_chain", {}).get("v114c_operator_review_cards") == 10)
    check("manifest next_policy = handoff_to_gpt_for_next_stage_decision",
          manifest.get("next_policy") == "handoff_to_gpt_for_next_stage_decision")

    # ==================================================================
    # 13. Known data consistency note
    # ==================================================================
    print("\n[13] Known Data Consistency Note")
    check("known_data_consistency_note_preserved = true",
          seal.get("known_data_consistency_note_preserved") is True,
          f"got: {seal.get('known_data_consistency_note_preserved')}")

    # ==================================================================
    # 14. Markdown report content
    # ==================================================================
    print("\n[14] Markdown Report Content")
    if file_exists(V114D_REPORT):
        with open(V114D_REPORT, "r", encoding="utf-8") as f:
            report_content = f.read()

        check("report mentions v114D",
              "v114D" in report_content)
        check("report mentions v114A baseline",
              "v114A" in report_content)
        check("report mentions v114B delta",
              "v114B" in report_content)
        check("report mentions v114C operator review",
              "v114C" in report_content)
        check("report mentions BTC closed_position",
              "BTC" in report_content and "closed_position" in report_content)
        check("report mentions not_tg_send_ready",
              "not_tg_send_ready" in report_content)
        check("report mentions local_delta_review_ready",
              "local_delta_review_ready" in report_content)
        check("report mentions not_prod_state_ready",
              "not_prod_state_ready" in report_content)
        check("report mentions not_real_send_candidate",
              "not_real_send_candidate" in report_content)
        check("report mentions known data consistency note",
              "v113D" in report_content and "consistency" in report_content.lower())
        check("report mentions closed_position: 1",
              report_content.count("closed_position") >= 2)
        check("report mentions size_changed: 5",
              "size_changed" in report_content)
        check("report mentions unchanged: 4",
              "unchanged" in report_content)
        check("report mentions high: 1",
              "High" in report_content)
        check("report mentions medium: 5",
              "Medium" in report_content)
        check("report mentions low: 4",
              "Low" in report_content)
        check("report mentions label confidence summary",
              "Label Confidence" in report_content)
        check("report mentions safety invariants",
              "Safety Invariant" in report_content)
        check("report mentions next step to GPT",
              "gpt_decide_next_stage" in report_content
              or "GPT" in report_content)

        # Must NOT contain send-ready or live-passed language
        check("report does NOT say 'send ready'",
              "send ready" not in report_content.lower())
        check("report does NOT say 'live passed'",
              "live passed" not in report_content.lower())
        check("report does NOT say 'TG send ready'",
              "TG send ready" not in report_content.lower())
        check("report does NOT say 'ready to send'",
              "ready to send" not in report_content.lower())
    else:
        check("report file exists for content check", False, "file not found")

    # ==================================================================
    # 15. Handoff content
    # ==================================================================
    print("\n[15] Handoff Markdown Content")
    if file_exists(V114D_HANDOFF):
        with open(V114D_HANDOFF, "r", encoding="utf-8") as f:
            handoff_content = f.read()

        check("handoff mentions v114D",
              "v114D" in handoff_content)
        check("handoff mentions local_delta_review_ready_not_send_ready",
              "local_delta_review_ready_not_send_ready" in handoff_content)
        check("handoff mentions BTC closed_position",
              "BTC" in handoff_content and "closed_position" in handoff_content)
        check("handoff mentions known data consistency note",
              "v113D" in handoff_content)
        check("handoff mentions not TG send ready",
              "not_tg_send_ready" in handoff_content.lower()
              or "not TG" in handoff_content
              or "TG-eligible" in handoff_content)
        check("handoff mentions safety invariants",
              "safety" in handoff_content.lower() or "invariant" in handoff_content.lower())
        check("handoff mentions chain counts",
              "10" in handoff_content)
        check("handoff mentions gpt_decide_next_stage",
              "gpt_decide_next_stage" in handoff_content
              or "next stage" in handoff_content.lower())
    else:
        check("handoff file exists for content check", False, "file not found")

    # ==================================================================
    # 16. Not live passed / not send ready
    # ==================================================================
    print("\n[16] Not Live Passed / Not Send Ready")
    # Seal result must NOT claim live passed or send ready
    check("seal stage_conclusion is NOT 'live_passed'",
          seal.get("stage_conclusion") != "live_passed")
    check("seal stage_conclusion is NOT 'send_ready'",
          seal.get("stage_conclusion") != "send_ready")
    check("seal stage_conclusion contains 'not_send_ready'",
          "not_send_ready" in seal.get("stage_conclusion", ""))
    check("seal status is 'passed' not 'live_passed'",
          seal.get("status") == "passed")

    # ==================================================================
    # 17. Label confidence distribution
    # ==================================================================
    print("\n[17] Label Confidence Distribution")
    lc_counts = {"high": 0, "medium": 0, "low": 0}
    for c in v114c_cards:
        lc = c.get("label_confidence", "")
        if lc in lc_counts:
            lc_counts[lc] += 1

    check("label_confidence high = 0",
          lc_counts["high"] == 0, f"got: {lc_counts['high']}")
    check("label_confidence medium = 8",
          lc_counts["medium"] == 8, f"got: {lc_counts['medium']}")
    check("label_confidence low = 2",
          lc_counts["low"] == 2, f"got: {lc_counts['low']}")

    # ==================================================================
    # 18. Next step field
    # ==================================================================
    print("\n[18] Next Step")
    check("seal next_step correct",
          seal.get("next_step") == "gpt_decide_next_stage_after_v114d_seal",
          f"got: {seal.get('next_step')}")

    # ==================================================================
    # Summary
    # ==================================================================
    print("\n" + "=" * 70)
    total = passed + failed
    print(f"Results: {passed} passed, {failed} failed, {total} total")
    print("=" * 70)
    if failed:
        print("\nFAILURES:")
        for f in failures:
            print(f"  {f}")
        return 1
    else:
        print("\nAll tests passed.")
        return 0


if __name__ == "__main__":
    sys.exit(main())
