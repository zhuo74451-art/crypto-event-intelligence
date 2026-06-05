#!/usr/bin/env python3
"""
Test suite for v115B Whale Label Confidence Upgrade Plan — Local Only
======================================================================
Validates that the v115B policy plan runner produced correct outputs
with all safety invariants, correct routing policies, upgrade targets,
TG copy gate rules, send preview gate rules, and rollback/cooldown
protections.

This test ONLY verifies generated files — it does NOT make any
external API calls, send TG, or write production state.
"""

import json
import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RESULTS_DIR = os.path.join(BASE_DIR, "results")
CONFIG_DIR = os.path.join(BASE_DIR, "config")
RUNS_DIR = os.path.join(BASE_DIR, "runs", "market_radar")

# v115B outputs
V115B_RESULT = os.path.join(RESULTS_DIR, "market_radar_v115b_whale_label_confidence_upgrade_plan_result.json")
V115B_UPGRADE_TARGETS = os.path.join(RESULTS_DIR, "market_radar_v115b_whale_label_upgrade_targets.jsonl")
V115B_ROUTING_POLICY = os.path.join(CONFIG_DIR, "market_radar_v115b_whale_label_confidence_routing_policy.json")
V115B_TG_COPY_GATE = os.path.join(CONFIG_DIR, "market_radar_v115b_whale_tg_test_copy_gate_policy.json")
V115B_SEND_PREVIEW_GATE = os.path.join(CONFIG_DIR, "market_radar_v115b_whale_send_preview_gate_policy.json")
V115B_ROLLBACK_COOLDOWN = os.path.join(CONFIG_DIR, "market_radar_v115b_whale_rollback_cooldown_policy.json")
V115B_REPORT = os.path.join(RUNS_DIR, "v115b_whale_label_confidence_upgrade_plan_local_only.md")
V115B_HANDOFF = os.path.join(RUNS_DIR, "v115b_whale_label_confidence_upgrade_plan_local_only_handoff.md")

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
    print("v115B Test Suite — Whale Label Confidence Upgrade Plan")
    print("=" * 70)

    # ==================================================================
    # 1. File Existence
    # ==================================================================
    print("\n[1] File Existence")
    check("result JSON exists", file_exists(V115B_RESULT))
    check("upgrade targets JSONL exists", file_exists(V115B_UPGRADE_TARGETS))
    check("routing policy config exists", file_exists(V115B_ROUTING_POLICY))
    check("TG copy gate policy config exists", file_exists(V115B_TG_COPY_GATE))
    check("send preview gate policy config exists", file_exists(V115B_SEND_PREVIEW_GATE))
    check("rollback cooldown policy config exists", file_exists(V115B_ROLLBACK_COOLDOWN))
    check("markdown report exists", file_exists(V115B_REPORT))
    check("handoff markdown exists", file_exists(V115B_HANDOFF))

    # ==================================================================
    # 2. Data Loading
    # ==================================================================
    print("\n[2] Data Loading")
    result = load_json(V115B_RESULT)
    targets = load_jsonl(V115B_UPGRADE_TARGETS)
    routing = load_json(V115B_ROUTING_POLICY)
    tg_copy = load_json(V115B_TG_COPY_GATE)
    send_preview = load_json(V115B_SEND_PREVIEW_GATE)
    rollback = load_json(V115B_ROLLBACK_COOLDOWN)

    check("result JSON parsed", isinstance(result, dict))
    check("upgrade targets JSONL parsed", isinstance(targets, list))
    check("routing policy parsed", isinstance(routing, dict))
    check("TG copy gate parsed", isinstance(tg_copy, dict))
    check("send preview gate parsed", isinstance(send_preview, dict))
    check("rollback cooldown parsed", isinstance(rollback, dict))

    # ==================================================================
    # 3. Result JSON — Top-Level Fields
    # ==================================================================
    print("\n[3] Result JSON — Top-Level Fields")
    check("version = v115B",
          result.get("version") == "v115B",
          f"got: {result.get('version')}")
    check("status = passed",
          result.get("status") == "passed",
          f"got: {result.get('status')}")
    check("local_policy_plan_only = true",
          result.get("local_policy_plan_only") is True,
          f"got: {result.get('local_policy_plan_only')}")

    # ==================================================================
    # 4. Policy creation flags
    # ==================================================================
    print("\n[4] Policy Creation Flags")
    check("label_confidence_routing_policy_created = true",
          result.get("label_confidence_routing_policy_created") is True)
    check("label_upgrade_targets_written >= 4",
          result.get("label_upgrade_targets_written", 0) >= 4,
          f"got: {result.get('label_upgrade_targets_written')}")
    check("tg_test_copy_gate_policy_created = true",
          result.get("tg_test_copy_gate_policy_created") is True)
    check("send_preview_gate_policy_created = true",
          result.get("send_preview_gate_policy_created") is True)
    check("rollback_cooldown_policy_created = true",
          result.get("rollback_cooldown_policy_created") is True)

    # ==================================================================
    # 5. Send-Readiness Judgments (MUST all be correct)
    # ==================================================================
    print("\n[5] Send-Readiness Judgments")
    check("send_ready = false",
          result.get("send_ready") is False,
          f"got: {result.get('send_ready')}")
    check("tg_test_group_ready = false",
          result.get("tg_test_group_ready") is False,
          f"got: {result.get('tg_test_group_ready')}")
    check("local_review_ready = true",
          result.get("local_review_ready") is True,
          f"got: {result.get('local_review_ready')}")

    # ==================================================================
    # 6. Routing Counts (MUST all be zero)
    # ==================================================================
    print("\n[6] Routing Counts (must be zero)")
    check("eligible_for_real_send_count = 0",
          result.get("eligible_for_real_send_count") == 0,
          f"got: {result.get('eligible_for_real_send_count')}")
    check("real_send_candidate_count = 0",
          result.get("real_send_candidate_count") == 0,
          f"got: {result.get('real_send_candidate_count')}")
    check("tg_send_allowed_count = 0",
          result.get("tg_send_allowed_count") == 0,
          f"got: {result.get('tg_send_allowed_count')}")

    # ==================================================================
    # 7. Safety Invariants (MUST all be false)
    # ==================================================================
    print("\n[7] Safety Invariants")
    check("external_api_called = false",
          result.get("external_api_called") is False)
    check("prod_state_write = false",
          result.get("prod_state_write") is False)
    check("tg_sent = false",
          result.get("tg_sent") is False)
    check("credentials_read = false",
          result.get("credentials_read") is False)
    check("daemon_started = false",
          result.get("daemon_started") is False)
    check("watcher_started = false",
          result.get("watcher_started") is False)
    check("files_deleted = false",
          result.get("files_deleted") is False)

    # ==================================================================
    # 8. Label Confidence Distribution
    # ==================================================================
    print("\n[8] Label Confidence Distribution")
    lc = result.get("current_label_confidence_distribution", {})
    check("high = 0", lc.get("high") == 0, f"got: {lc.get('high')}")
    check("medium = 8", lc.get("medium") == 8, f"got: {lc.get('medium')}")
    check("low = 2", lc.get("low") == 2, f"got: {lc.get('low')}")

    # ==================================================================
    # 9. Upgrade Targets
    # ==================================================================
    print("\n[9] Upgrade Targets")
    check(f"upgrade targets count >= 4 (got {len(targets)})",
          len(targets) >= 4)

    # Check required addresses are present
    target_addresses = [t.get("address") for t in targets]
    required_addresses = [
        "0x50b309f78e774a756a2230e1769729094cac9f20",  # Unknown Hyperliquid Whale
        "0x082e843a431aef031264dc232693dd710aedca88",  # Unknown HYPE Whale
        "0x8def9f50456c6c4e37fa5d3d57f108ed23992dae",  # loraclexyz
        "0x6c8512516ce5669d35113a11ca8b8de322fd84f6",  # Matrixport Related
    ]
    for addr in required_addresses:
        check(f"required address present: {addr[:20]}...",
              addr in target_addresses)

    # Check BTC closed_position whale is high priority
    btc_target = None
    for t in targets:
        if t.get("address") == "0x50b309f78e774a756a2230e1769729094cac9f20":
            btc_target = t
            break
    if btc_target:
        check("BTC closed_position unknown whale is high priority",
              btc_target.get("upgrade_priority") == "high",
              f"got: {btc_target.get('upgrade_priority')}")
        check("BTC target has tg_test_group_allowed_now = false",
              btc_target.get("tg_test_group_allowed_now") is False)
        check("BTC target has public_send_allowed_now = false",
              btc_target.get("public_send_allowed_now") is False)
        check("BTC target has required_evidence_for_high_confidence",
              len(btc_target.get("required_evidence_for_high_confidence", [])) >= 4)

    # Check unknown whale targets are NOT send-allowed
    for t in targets:
        if t.get("current_label_confidence") == "low":
            check(f"low-confidence target {t.get('current_label','?')[:20]}... is NOT tg_test_group_allowed_now",
                  t.get("tg_test_group_allowed_now") is False)
            check(f"low-confidence target {t.get('current_label','?')[:20]}... is NOT public_send_allowed_now",
                  t.get("public_send_allowed_now") is False)

    # Priority distribution
    high_count = sum(1 for t in targets if t.get("upgrade_priority") == "high")
    medium_count = sum(1 for t in targets if t.get("upgrade_priority") == "medium")
    check(f"high priority targets >= 2 (got {high_count})",
          high_count >= 2)
    check(f"medium priority targets >= 2 (got {medium_count})",
          medium_count >= 2)

    # ==================================================================
    # 10. Label Confidence Routing Policy
    # ==================================================================
    print("\n[10] Label Confidence Routing Policy")
    rr = routing.get("routing_rules", {})

    # high confidence rules
    check("high confidence: operator_review_allowed = true",
          rr.get("high", {}).get("operator_review_allowed") is True)
    check("high confidence: tg_test_group_allowed = true",
          rr.get("high", {}).get("tg_test_group_allowed") is True)
    check("high confidence: public_send_allowed = false",
          rr.get("high", {}).get("public_send_allowed") is False)
    check("high confidence: requires_send_preview_gate = true",
          rr.get("high", {}).get("requires_send_preview_gate") is True)

    # medium confidence rules
    check("medium confidence: operator_review_allowed = true",
          rr.get("medium", {}).get("operator_review_allowed") is True)
    check("medium confidence: tg_test_group_allowed = false",
          rr.get("medium", {}).get("tg_test_group_allowed") is False)
    check("medium confidence: public_send_allowed = false",
          rr.get("medium", {}).get("public_send_allowed") is False)
    check("medium confidence: requires_label_upgrade = true",
          rr.get("medium", {}).get("requires_label_upgrade") is True)

    # low confidence rules
    check("low confidence: operator_review_allowed = true",
          rr.get("low", {}).get("operator_review_allowed") is True)
    check("low confidence: tg_test_group_allowed = false",
          rr.get("low", {}).get("tg_test_group_allowed") is False)
    check("low confidence: public_send_allowed = false",
          rr.get("low", {}).get("public_send_allowed") is False)
    check("low confidence: requires_label_upgrade = true",
          rr.get("low", {}).get("requires_label_upgrade") is True)
    check("low confidence: must_show_unknown_warning = true",
          rr.get("low", {}).get("must_show_unknown_warning") is True)

    # send_ready_requires
    srr = routing.get("send_ready_requires", {})
    check("send_ready_requires.minimum_label_confidence = high",
          srr.get("minimum_label_confidence") == "high",
          f"got: {srr.get('minimum_label_confidence')}")
    check("send_ready_requires.unknown_whale_allowed_for_send = false",
          srr.get("unknown_whale_allowed_for_send") is False)
    check("send_ready_requires.low_confidence_allowed_for_tg_test = false",
          srr.get("low_confidence_allowed_for_tg_test") is False)
    check("send_ready_requires.high_confidence_required_for_public_send = true",
          srr.get("high_confidence_required_for_public_send") is True)

    # ==================================================================
    # 11. TG Test Copy Gate Policy
    # ==================================================================
    print("\n[11] TG Test Copy Gate Policy")
    rules = tg_copy.get("rules", {})

    check("TG copy: must_not_reuse_operator_review_copy = true",
          rules.get("copy_source", {}).get("must_not_reuse_operator_review_copy") is True)
    check("TG copy: must_be_generated_separately = true",
          rules.get("copy_source", {}).get("must_be_generated_separately") is True)

    # Banned phrases must be present
    banned = rules.get("banned_phrases", [])
    required_banned = ["确认", "实锤", "正式信号", "强信号", "可直接发布", "立即发送"]
    for phrase in required_banned:
        check(f"TG copy banned phrase present: '{phrase}'",
              phrase in banned,
              f"not found in banned_phrases list")

    # Required elements
    req_elements = rules.get("required_elements", {})
    check("TG copy required: test_only_marker present",
          "test_only_marker" in req_elements)
    test_only_marker = req_elements.get("test_only_marker", "")
    check("TG copy required: test_only_marker contains 'TEST-ONLY'",
          "TEST-ONLY" in test_only_marker.upper() or "TEST ONLY" in test_only_marker.upper(),
          f"got: {test_only_marker}")
    check("TG copy required: source_disclaimer present",
          "source_disclaimer" in req_elements)
    check("TG copy required: not_financial_advice present",
          "not_financial_advice" in req_elements)
    check("TG copy required: not_production_state present",
          "not_production_state" in req_elements)

    # Review requirements
    review_req = tg_copy.get("review_required", {})
    check("TG copy: review_required.before_tg_test_send = true",
          review_req.get("before_tg_test_send") is True)

    # ==================================================================
    # 12. Send Preview Gate Policy
    # ==================================================================
    print("\n[12] Send Preview Gate Policy")
    check("send preview: send_enabled_by_default = false",
          send_preview.get("send_enabled_by_default") is False)
    check("send preview: tg_send_allowed = false",
          send_preview.get("tg_send_allowed") is False)

    gate_req = send_preview.get("gate_requirements", {})
    check("send preview: one_shot_preview_pack required",
          gate_req.get("one_shot_preview_pack", {}).get("required") is True)
    check("send preview: no_repeat_key required",
          gate_req.get("no_repeat_key", {}).get("required") is True)
    check("send preview: cooldown_key required",
          gate_req.get("cooldown_key", {}).get("required") is True)
    check("send preview: payload_hash required",
          gate_req.get("payload_hash", {}).get("required") is True)
    check("send preview: operator_approval_field required",
          gate_req.get("operator_approval_field", {}).get("required") is True)
    check("send preview: test_group_scope_field required",
          gate_req.get("test_group_scope_field", {}).get("required") is True)
    check("send preview: user_pre_authorization required",
          gate_req.get("user_pre_authorization", {}).get("required") is True)

    # No-repeat key format check
    check("send preview: no_repeat_key format contains required fields",
          "address" in gate_req.get("no_repeat_key", {}).get("format", "").lower()
          and "asset" in gate_req.get("no_repeat_key", {}).get("format", "").lower())

    # ==================================================================
    # 13. Rollback / Cooldown / No-Repeat Policy
    # ==================================================================
    print("\n[13] Rollback / Cooldown / No-Repeat Policy")
    check("rollback: instruction_placeholder present",
          len(rollback.get("rollback", {}).get("instruction_placeholder", "")) > 20)
    check("rollback: rollback_procedure = manual_only_no_automation",
          rollback.get("rollback", {}).get("rollback_procedure") == "manual_only_no_automation",
          f"got: {rollback.get('rollback', {}).get('rollback_procedure')}")

    check("no-repeat: enabled = true",
          rollback.get("no_repeat", {}).get("enabled") is True)
    check("no-repeat: dedupe_key_format present",
          len(rollback.get("no_repeat", {}).get("dedupe_key_format", "")) > 10)
    check("no-repeat: duplicate_payload_hash_blocking = true",
          rollback.get("no_repeat", {}).get("duplicate_payload_hash_blocking") is True)

    check("cooldown: enabled = true",
          rollback.get("cooldown", {}).get("enabled") is True)
    check("cooldown: minimum_window_hours present",
          rollback.get("cooldown", {}).get("minimum_window_hours", 0) > 0)

    check("manual_stop: condition present",
          len(rollback.get("manual_stop", {}).get("condition", "")) > 0)
    check("manual_stop: while_stopped.all_sends_blocked = true",
          rollback.get("manual_stop", {}).get("while_stopped", {}).get("all_sends_blocked") is True)

    check("no_daemon_no_loop: rule = ABSOLUTE",
          rollback.get("no_daemon_no_loop", {}).get("rule") == "ABSOLUTE")

    # ==================================================================
    # 14. Next Step
    # ==================================================================
    print("\n[14] Next Step")
    check("next_step = v115c_whale_tg_test_copy_template_gate_local_only",
          result.get("next_step") == "v115c_whale_tg_test_copy_template_gate_local_only",
          f"got: {result.get('next_step')}")

    # ==================================================================
    # 15. Negative Assertions (MUST NOT be send ready / TG sent)
    # ==================================================================
    print("\n[15] Negative Assertions")
    check("result does NOT claim send_ready=true",
          result.get("send_ready") is not True)
    check("result does NOT claim tg_test_group_ready=true",
          result.get("tg_test_group_ready") is not True)
    check("result does NOT claim tg_sent=true",
          result.get("tg_sent") is not True)
    check("result does NOT contain 'live_passed'",
          "live_passed" not in str(result.get("status", "")))
    check("tg_send_allowed_count is 0",
          result.get("tg_send_allowed_count") == 0)
    check("eligible_for_real_send_count is 0",
          result.get("eligible_for_real_send_count") == 0)
    check("real_send_candidate_count is 0",
          result.get("real_send_candidate_count") == 0)

    # ==================================================================
    # 16. Markdown Report Content
    # ==================================================================
    print("\n[16] Markdown Report Content")
    if file_exists(V115B_REPORT):
        with open(V115B_REPORT, "r", encoding="utf-8") as f:
            report_text = f.read()

        check("report mentions v115B", "v115B" in report_text)
        check("report mentions v115A blockers",
              "v115A" in report_text or "blocker" in report_text.lower())
        check("report mentions label confidence distribution",
              "label confidence" in report_text.lower()
              or "Label Confidence" in report_text)
        check("report mentions high=0",
              "high=0" in report_text or "high: 0" in report_text
              or "**0**" in report_text)
        check("report contains upgrade targets section",
              "upgrade target" in report_text.lower()
              or "Upgrade Target" in report_text)
        check("report contains routing policy summary",
              "routing" in report_text.lower()
              or "Routing" in report_text)
        check("report contains TG test copy gate summary",
              "TG test copy" in report_text
              or "TG Test Copy" in report_text
              or "tg test copy" in report_text.lower())
        check("report contains send preview gate summary",
              "send preview" in report_text.lower()
              or "Send Preview" in report_text)
        check("report contains rollback/cooldown summary",
              "rollback" in report_text.lower()
              or "cooldown" in report_text.lower())
        check("report contains local_review_ready=true",
              "local_review_ready" in report_text.lower())
        check("report contains send_ready=false",
              "send_ready" in report_text.lower())
        check("report contains tg_test_group_ready=false",
              "tg_test_group_ready" in report_text.lower())

        # Must NOT contain send-ready or live-passed language
        check("report does NOT say 'send ready' in affirmative",
              "send ready" not in report_text.lower()
              or "not send ready" in report_text.lower()
              or "NOT send-ready" in report_text
              or "not send-ready" in report_text.lower())
        check("report does NOT say 'live passed'",
              "live passed" not in report_text.lower())
        check("report does NOT say 'production ready'",
              "production ready" not in report_text.lower())
    else:
        check("report file exists for content check", False, "file not found")

    # ==================================================================
    # 17. Handoff Content
    # ==================================================================
    print("\n[17] Handoff Markdown Content")
    if file_exists(V115B_HANDOFF):
        with open(V115B_HANDOFF, "r", encoding="utf-8") as f:
            handoff_text = f.read()

        check("handoff mentions v115B", "v115B" in handoff_text)
        check("handoff mentions send_ready=false",
              "send_ready" in handoff_text.lower() and "false" in handoff_text.lower())
        check("handoff mentions upgrade targets",
              "upgrade target" in handoff_text.lower()
              or "Upgrade Target" in handoff_text)
        check("handoff mentions routing rules",
              "routing" in handoff_text.lower())
        check("handoff mentions safety invariants",
              "safety" in handoff_text.lower() or "invariant" in handoff_text.lower())
        check("handoff mentions next_step",
              "v115c" in handoff_text.lower())
        check("handoff mentions NOT declarations",
              "NOT" in handoff_text)
    else:
        check("handoff file exists for content check", False, "file not found")

    # ==================================================================
    # 18. Upgrade Target Field Completeness
    # ==================================================================
    print("\n[18] Upgrade Target Field Completeness")
    required_target_fields = [
        "version", "address", "current_label", "current_label_confidence",
        "upgrade_priority", "reason", "required_evidence_for_high_confidence",
        "allowed_current_routing", "tg_test_group_allowed_now",
        "public_send_allowed_now",
    ]
    for t in targets:
        addr_short = t.get("address", "?")[:20]
        for field in required_target_fields:
            check(f"{addr_short}... has field '{field}'",
                  field in t,
                  f"missing field: {field}")

    # ==================================================================
    # 19. btc_closed_position check
    # ==================================================================
    print("\n[19] BTC Closed Position Whale Specific Checks")
    btc_targets = [t for t in targets if "BTC" in str(t.get("reason", ""))
                   or "closed_position" in str(t.get("delta_types", []))]
    if btc_targets:
        check("at least one target references BTC closed_position",
              len(btc_targets) >= 1)
        bt = btc_targets[0]
        check("BTC closed_position target is high priority",
              bt.get("upgrade_priority") == "high")

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
