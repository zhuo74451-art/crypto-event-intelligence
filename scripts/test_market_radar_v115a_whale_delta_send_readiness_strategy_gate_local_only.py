#!/usr/bin/env python3
"""
Test suite for v115A Whale Delta Send-Readiness Strategy Gate — Local Only
==========================================================================
Validates that the v115A strategy gate runner produced correct outputs
with all safety invariants, correct send-readiness judgments, and
required blockers.

This test ONLY verifies generated files — it does NOT make any
external API calls, send TG, or write production state.
"""

import json
import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RESULTS_DIR = os.path.join(BASE_DIR, "results")
RUNS_DIR = os.path.join(BASE_DIR, "runs", "market_radar")

# v115A outputs
V115A_RESULT = os.path.join(RESULTS_DIR, "market_radar_v115a_whale_delta_send_readiness_gate_result.json")
V115A_BLOCKERS = os.path.join(RESULTS_DIR, "market_radar_v115a_whale_delta_send_readiness_blockers.jsonl")
V115A_REPORT = os.path.join(RUNS_DIR, "v115a_whale_delta_send_readiness_strategy_gate_local_only.md")
V115A_HANDOFF = os.path.join(RUNS_DIR, "v115a_whale_delta_send_readiness_strategy_gate_local_only_handoff.md")

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
    print("v115A Test Suite — Whale Delta Send-Readiness Strategy Gate")
    print("=" * 70)

    # ==================================================================
    # 1. File existence
    # ==================================================================
    print("\n[1] File Existence")
    check("gate result JSON exists", file_exists(V115A_RESULT))
    check("blockers JSONL exists", file_exists(V115A_BLOCKERS))
    check("markdown report exists", file_exists(V115A_REPORT))
    check("handoff markdown exists", file_exists(V115A_HANDOFF))

    # ==================================================================
    # 2. Load data
    # ==================================================================
    print("\n[2] Data Loading")
    gate = load_json(V115A_RESULT)
    blockers = load_jsonl(V115A_BLOCKERS)

    check("gate result JSON parsed", isinstance(gate, dict))
    check("blockers JSONL parsed", isinstance(blockers, list))

    # ==================================================================
    # 3. Top-level fields
    # ==================================================================
    print("\n[3] Gate Result — Top-Level Fields")
    check("version = v115A",
          gate.get("version") == "v115A",
          f"got: {gate.get('version')}")
    check("status = passed",
          gate.get("status") == "passed",
          f"got: {gate.get('status')}")
    check("strategy_gate = whale_delta_send_readiness",
          gate.get("strategy_gate") == "whale_delta_send_readiness",
          f"got: {gate.get('strategy_gate')}")
    check("input_stage = v114D",
          gate.get("input_stage") == "v114D",
          f"got: {gate.get('input_stage')}")
    check("input_stage_conclusion = local_delta_review_ready_not_send_ready",
          gate.get("input_stage_conclusion") == "local_delta_review_ready_not_send_ready",
          f"got: {gate.get('input_stage_conclusion')}")

    # ==================================================================
    # 4. Send-readiness judgments (MUST all be false/true as specified)
    # ==================================================================
    print("\n[4] Send-Readiness Judgments")
    check("send_ready = false",
          gate.get("send_ready") is False,
          f"got: {gate.get('send_ready')}")
    check("tg_test_group_ready = false",
          gate.get("tg_test_group_ready") is False,
          f"got: {gate.get('tg_test_group_ready')}")
    check("local_review_ready = true",
          gate.get("local_review_ready") is True,
          f"got: {gate.get('local_review_ready')}")

    # ==================================================================
    # 5. Routing counts (MUST all be zero)
    # ==================================================================
    print("\n[5] Routing Counts (must be zero)")
    check("eligible_for_real_send_count = 0",
          gate.get("eligible_for_real_send_count") == 0,
          f"got: {gate.get('eligible_for_real_send_count')}")
    check("real_send_candidate_count = 0",
          gate.get("real_send_candidate_count") == 0,
          f"got: {gate.get('real_send_candidate_count')}")
    check("tg_send_allowed_count = 0",
          gate.get("tg_send_allowed_count") == 0,
          f"got: {gate.get('tg_send_allowed_count')}")

    # ==================================================================
    # 6. Safety invariants (MUST all be false)
    # ==================================================================
    print("\n[6] Safety Invariants")
    check("external_api_called = false",
          gate.get("external_api_called") is False)
    check("prod_state_write = false",
          gate.get("prod_state_write") is False)
    check("tg_sent = false",
          gate.get("tg_sent") is False)
    check("credentials_read = false",
          gate.get("credentials_read") is False)
    check("daemon_started = false",
          gate.get("daemon_started") is False)
    check("watcher_started = false",
          gate.get("watcher_started") is False)
    check("files_deleted = false",
          gate.get("files_deleted") is False)

    # ==================================================================
    # 7. Blocker count (>= 6)
    # ==================================================================
    print("\n[7] Blocker Count")
    check(f"blocker_count >= 6 (got {gate.get('blocker_count', 0)})",
          gate.get("blocker_count", 0) >= 6,
          f"got: {gate.get('blocker_count')}")
    check(f"blockers JSONL length matches (got {len(blockers)})",
          len(blockers) == gate.get("blocker_count", -1),
          f"gate says {gate.get('blocker_count')}, JSONL has {len(blockers)}")

    # ==================================================================
    # 8. Required blockers present
    # ==================================================================
    print("\n[8] Required Blockers Present")

    required_blocker_ids = [
        "LABEL_CONFIDENCE_NO_HIGH",
        "LOW_CONFIDENCE_UNKNOWN_WHALES",
        "REVIEW_ONLY_NO_SEND",
        "TG_COPY_NOT_TESTED",
        "HISTORICAL_COUNT_MISMATCH_NOTE",
        "NO_SEND_TEMPLATE_GATE",
    ]

    blocker_ids = [b.get("blocker_id") for b in blockers]
    for required_id in required_blocker_ids:
        check(f"blocker '{required_id}' present",
              required_id in blocker_ids)

    # Check each blocker has required fields
    print("\n[8b] Blocker Field Completeness")
    for b in blockers:
        bid = b.get("blocker_id", "?")
        check(f"{bid}: has version",
              "version" in b and b["version"] == "v115A")
        check(f"{bid}: has severity",
              "severity" in b and b["severity"] in ("high", "medium", "low"),
              f"got: {b.get('severity')}")
        check(f"{bid}: has blocks_send_ready",
              "blocks_send_ready" in b and isinstance(b["blocks_send_ready"], bool))
        check(f"{bid}: has blocks_tg_test_group_ready",
              "blocks_tg_test_group_ready" in b and isinstance(b["blocks_tg_test_group_ready"], bool))
        check(f"{bid}: has description",
              "description" in b and len(b["description"]) > 10)
        check(f"{bid}: has required_resolution",
              "required_resolution" in b and len(b["required_resolution"]) > 10)

    # ==================================================================
    # 9. Label confidence distribution
    # ==================================================================
    print("\n[9] Label Confidence Distribution")
    lc = gate.get("label_confidence_distribution", {})
    check("label_confidence_distribution exists",
          isinstance(lc, dict), f"got: {type(lc)}")
    check("high = 0",
          lc.get("high") == 0, f"got: {lc.get('high')}")
    check("low >= 2",
          lc.get("low", 0) >= 2, f"got: {lc.get('low')}")

    # ==================================================================
    # 10. Next step field
    # ==================================================================
    print("\n[10] Next Step")
    check("next_step = v115b_whale_label_confidence_upgrade_plan_local_only",
          gate.get("next_step") == "v115b_whale_label_confidence_upgrade_plan_local_only",
          f"got: {gate.get('next_step')}")

    # ==================================================================
    # 11. NOT send ready / NOT TG sent assertions
    # ==================================================================
    print("\n[11] Negative Assertions (MUST NOT be send ready / TG sent)")
    check("gate does NOT claim send_ready=true",
          gate.get("send_ready") is not True)
    check("gate does NOT claim tg_test_group_ready=true",
          gate.get("tg_test_group_ready") is not True)
    check("gate does NOT claim tg_sent=true",
          gate.get("tg_sent") is not True)
    check("gate does NOT contain 'live_passed'",
          "live_passed" not in gate.get("status", ""))
    check("gate does NOT contain 'send ready' in status",
          "send" not in gate.get("status", "").lower()
          or "send_ready" not in gate.get("status", ""))

    # ==================================================================
    # 12. Markdown report content
    # ==================================================================
    print("\n[12] Markdown Report Content")
    if file_exists(V115A_REPORT):
        with open(V115A_REPORT, "r", encoding="utf-8") as f:
            report = f.read()

        check("report mentions v115A",
              "v115A" in report)
        check("report mentions v114D",
              "v114D" in report)
        check("report mentions send_ready=false",
              "send_ready" in report.lower() and "false" in report.lower())
        check("report mentions tg_test_group_ready=false",
              "tg_test_group_ready" in report.lower())
        check("report mentions local_review_ready=true",
              "local_review_ready" in report.lower())
        check("report contains 'Future Readiness Checklist'",
              "Future Readiness Checklist" in report
              or "future readiness" in report.lower())
        check("report mentions label confidence routing policy",
              "label confidence" in report.lower()
              or "Label confidence" in report)
        check("report mentions low-confidence downgrade",
              "downgrade" in report.lower()
              or "low-confidence" in report.lower()
              or "Low confidence" in report
              or "LOW_CONFIDENCE" in report)
        check("report mentions TG test copy",
              "TG test copy" in report or "tg test copy" in report.lower())
        check("report mentions one-shot send preview",
              "one-shot" in report.lower() or "send preview" in report.lower())
        check("report mentions rollback / cooldown",
              "rollback" in report.lower() or "cooldown" in report.lower())
        check("report mentions user pre-authorization",
              "pre-authorization" in report.lower()
              or "authorization" in report.lower())
        check("report mentions test-only",
              "test-only" in report.lower()
              or "test only" in report.lower())

        # Must NOT contain send-ready or live-passed language
        check("report does NOT say 'send ready'",
              "send ready" not in report.lower()
              or "not send ready" in report.lower()
              or "NOT send-ready" in report)
        check("report does NOT say 'live passed'",
              "live passed" not in report.lower())
        check("report does NOT say 'TG sent'",
              "TG sent" not in report or "TG sent" in report and "NOT"
              in report)
    else:
        check("report file exists for content check", False, "file not found")

    # ==================================================================
    # 13. Handoff content
    # ==================================================================
    print("\n[13] Handoff Markdown Content")
    if file_exists(V115A_HANDOFF):
        with open(V115A_HANDOFF, "r", encoding="utf-8") as f:
            handoff = f.read()

        check("handoff mentions v115A",
              "v115A" in handoff)
        check("handoff mentions send_ready=false",
              "send_ready" in handoff.lower() and "false" in handoff.lower())
        check("handoff mentions blockers",
              "blocker" in handoff.lower())
        check("handoff mentions future readiness",
              "future readiness" in handoff.lower()
              or "Future Readiness Checklist" in handoff)
        check("handoff mentions next_step",
              "v115b" in handoff.lower())
        check("handoff mentions safety invariants",
              "safety" in handoff.lower() or "invariant" in handoff.lower())
    else:
        check("handoff file exists for content check", False, "file not found")

    # ==================================================================
    # 14. Label confidence distribution in detail
    # ==================================================================
    print("\n[14] Label Confidence Detailed Check")
    # Verify that the label_confidence_distribution in gate matches v114C data
    lc = gate.get("label_confidence_distribution", {})
    check("high = 0 (explicitly)",
          lc.get("high") == 0)
    check("medium >= 1",
          lc.get("medium", 0) >= 1)
    check("low >= 2",
          lc.get("low", 0) >= 2)

    # ==================================================================
    # 15. review_only_no_send count
    # ==================================================================
    print("\n[15] Review Card Status")
    check("review_only_no_send_count = review_cards_total",
          gate.get("review_only_no_send_count") == gate.get("review_cards_total"),
          f"review_only={gate.get('review_only_no_send_count')}, "
          f"total={gate.get('review_cards_total')}")

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
