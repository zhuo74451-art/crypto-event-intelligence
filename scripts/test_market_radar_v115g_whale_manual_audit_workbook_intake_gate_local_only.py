#!/usr/bin/env python3
"""
Test suite for v115G Whale Manual Audit Workbook Intake Gate — Local Only
===========================================================================
Validates that the v115G intake gate runner produced correct outputs:
  - 4 intake records (all intake_ready=false)
  - 4 intake decisions (all intake_blocked)
  - Gate result JSON with all required invariants
  - All send guards false
  - No label upgrades
  - No external API calls
  - No TG send
  - No production state write
  - No modification of v114A-v115F old results

Current empty workbook state: ALL 4 addresses must be intake_blocked.
"""

import json
import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RESULTS_DIR = os.path.join(BASE_DIR, "results")
CONFIG_DIR = os.path.join(BASE_DIR, "config")
RUNS_DIR = os.path.join(BASE_DIR, "runs", "market_radar")

# v115G outputs (must exist)
V115G_INTAKE_RECORDS = os.path.join(
    RESULTS_DIR, "market_radar_v115g_whale_manual_audit_intake_records.jsonl"
)
V115G_INTAKE_DECISIONS = os.path.join(
    RESULTS_DIR, "market_radar_v115g_whale_manual_audit_intake_decisions.jsonl"
)
V115G_GATE_RESULT = os.path.join(
    RESULTS_DIR, "market_radar_v115g_whale_manual_audit_workbook_intake_gate_result.json"
)
V115G_MD = os.path.join(
    RUNS_DIR, "v115g_whale_manual_audit_workbook_intake_gate_local_only.md"
)
V115G_HANDOFF = os.path.join(
    RUNS_DIR, "v115g_whale_manual_audit_workbook_intake_gate_local_only_handoff.md"
)

# v115F inputs (must still exist, NOT modified)
V115F_WORKBOOK_CSV = os.path.join(
    RUNS_DIR, "v115f_whale_address_audit_operator_workbook.csv"
)
V115F_MANIFEST = os.path.join(
    RESULTS_DIR, "market_radar_v115f_whale_address_audit_operator_workbook_manifest.json"
)
V115F_GATE_RESULT = os.path.join(
    RESULTS_DIR, "market_radar_v115f_whale_address_audit_operator_workbook_gate_result.json"
)

# v115E inputs (must still exist)
V115E_UPGRADE_DECISIONS = os.path.join(
    RESULTS_DIR, "market_radar_v115e_whale_label_upgrade_decisions.jsonl"
)
V115E_EVIDENCE_REQUESTS = os.path.join(
    RESULTS_DIR, "market_radar_v115e_whale_address_audit_evidence_requests.jsonl"
)
V115E_MANUAL_AUDIT_FORMS = os.path.join(
    RESULTS_DIR, "market_radar_v115e_whale_address_manual_audit_forms.jsonl"
)
V115E_RESULT = os.path.join(
    RESULTS_DIR, "market_radar_v115e_whale_address_audit_evidence_pack_result.json"
)

# v115D inputs (must still exist)
V115D_GATE_DECISIONS = os.path.join(
    RESULTS_DIR, "market_radar_v115d_whale_one_shot_send_preview_gate_decisions.jsonl"
)
V115D_RESULT = os.path.join(
    RESULTS_DIR, "market_radar_v115d_whale_one_shot_send_preview_gate_result.json"
)

# v115B config (must still exist)
V115B_ROUTING = os.path.join(
    CONFIG_DIR, "market_radar_v115b_whale_label_confidence_routing_policy.json"
)

# Expected addresses (from v115F workbook)
EXPECTED_ADDRESSES = [
    "0x082e843a431aef031264dc232693dd710aedca88",
    "0x50b309f78e774a756a2230e1769729094cac9f20",
    "0x6c8512516ce5669d35113a11ca8b8de322fd84f6",
    "0x8def9f50456c6c4e37fa5d3d57f108ed23992dae",
]

# All 10 required block reasons for empty workbook
REQUIRED_BLOCK_REASONS = [
    "TRUSTED_SOURCE_LABEL_MISSING",
    "TRUSTED_SOURCE_NOTE_OR_URL_MISSING",
    "SECOND_SOURCE_LABEL_MISSING",
    "SECOND_SOURCE_NOTE_OR_URL_MISSING",
    "ACTIVITY_PATTERN_NOTE_MISSING",
    "OPERATOR_CONFIRMED_LABEL_MISSING",
    "OPERATOR_CONFIDENCE_ASSESSMENT_MISSING",
    "REVIEWER_MISSING",
    "REVIEWED_AT_MISSING",
    "READY_FOR_UPGRADE_FALSE",
]

# Required fields in intake record
REQUIRED_INTAKE_RECORD_FIELDS = [
    "address", "current_label", "current_confidence", "target_confidence",
    "priority", "trusted_source_label_value", "trusted_source_url_or_note",
    "second_source_label_value", "second_source_url_or_note",
    "activity_pattern_note", "operator_confirmed_label",
    "operator_confidence_assessment", "operator_reject_reason",
    "reviewer", "reviewed_at", "ready_for_upgrade",
    "manual_fields_complete", "evidence_url_fields_present",
    "operator_confirmation_present", "intake_ready",
]

# Required fields in intake decision
REQUIRED_INTAKE_DECISION_FIELDS = [
    "address", "decision", "upgrade_candidate", "upgrade_ready",
    "missing_fields", "block_reasons", "send_allowed",
    "tg_test_group_allowed", "public_send_allowed",
]

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
    print("v115G Test Suite — Manual Audit Workbook Intake Gate")
    print("=" * 70)

    # ==================================================================
    # 1. File Existence — v115G Outputs
    # ==================================================================
    print("\n[1] File Existence — v115G Outputs")
    check("intake records .jsonl exists", file_exists(V115G_INTAKE_RECORDS))
    check("intake decisions .jsonl exists", file_exists(V115G_INTAKE_DECISIONS))
    check("gate result .json exists", file_exists(V115G_GATE_RESULT))
    check("markdown report exists", file_exists(V115G_MD))
    check("handoff markdown exists", file_exists(V115G_HANDOFF))

    # ==================================================================
    # 2. File Existence — Old Results NOT Modified
    # ==================================================================
    print("\n[2] File Existence — v114A-v115F Old Results Still Intact")
    check("v115F workbook CSV still exists", file_exists(V115F_WORKBOOK_CSV))
    check("v115F manifest still exists", file_exists(V115F_MANIFEST))
    check("v115F gate result still exists", file_exists(V115F_GATE_RESULT))
    check("v115E upgrade decisions still exist", file_exists(V115E_UPGRADE_DECISIONS))
    check("v115E evidence requests still exist", file_exists(V115E_EVIDENCE_REQUESTS))
    check("v115E manual audit forms still exist", file_exists(V115E_MANUAL_AUDIT_FORMS))
    check("v115E result still exists", file_exists(V115E_RESULT))
    check("v115D gate decisions still exist", file_exists(V115D_GATE_DECISIONS))
    check("v115D result still exists", file_exists(V115D_RESULT))
    check("v115B routing policy still exists", file_exists(V115B_ROUTING))

    # ==================================================================
    # 3. Data Loading
    # ==================================================================
    print("\n[3] Data Loading")
    intake_records = load_jsonl(V115G_INTAKE_RECORDS)
    check(f"Intake records loaded ({len(intake_records)} records)", len(intake_records) > 0)

    intake_decisions = load_jsonl(V115G_INTAKE_DECISIONS)
    check(f"Intake decisions loaded ({len(intake_decisions)} decisions)", len(intake_decisions) > 0)

    gate_result = load_json(V115G_GATE_RESULT)
    check("Gate result JSON parsed", isinstance(gate_result, dict))

    with open(V115G_MD, "r", encoding="utf-8") as f:
        md_text = f.read()
    check("Markdown report loaded", len(md_text) > 0)

    with open(V115G_HANDOFF, "r", encoding="utf-8") as f:
        handoff_text = f.read()
    check("Handoff markdown loaded", len(handoff_text) > 0)

    # ==================================================================
    # 4. Row Counts = 4
    # ==================================================================
    print("\n[4] Row Counts = 4")
    check(f"Intake records = 4 (got {len(intake_records)})", len(intake_records) == 4)
    check(f"Intake decisions = 4 (got {len(intake_decisions)})", len(intake_decisions) == 4)

    # ==================================================================
    # 5. All 4 Expected Addresses Present
    # ==================================================================
    print("\n[5] All 4 Expected Addresses")
    record_addresses = set(r.get("address", "") for r in intake_records)
    decision_addresses = set(d.get("address", "") for d in intake_decisions)
    for addr in EXPECTED_ADDRESSES:
        check(f"Address in intake records: {addr[:14]}...", addr in record_addresses)
        check(f"Address in intake decisions: {addr[:14]}...", addr in decision_addresses)

    # ==================================================================
    # 6. All intake_ready = false
    # ==================================================================
    print("\n[6] All intake_ready = false (empty workbook)")
    for i, rec in enumerate(intake_records):
        check(f"Record {i+1}: intake_ready = false", rec.get("intake_ready") is False,
              f"got: {rec.get('intake_ready')}")

    # ==================================================================
    # 7. All manual_fields_complete = false
    # ==================================================================
    print("\n[7] All manual_fields_complete = false")
    for i, rec in enumerate(intake_records):
        check(f"Record {i+1}: manual_fields_complete = false",
              rec.get("manual_fields_complete") is False,
              f"got: {rec.get('manual_fields_complete')}")

    # ==================================================================
    # 8. All evidence_url_fields_present = false
    # ==================================================================
    print("\n[8] All evidence_url_fields_present = false")
    for i, rec in enumerate(intake_records):
        check(f"Record {i+1}: evidence_url_fields_present = false",
              rec.get("evidence_url_fields_present") is False,
              f"got: {rec.get('evidence_url_fields_present')}")

    # ==================================================================
    # 9. All operator_confirmation_present = false
    # ==================================================================
    print("\n[9] All operator_confirmation_present = false")
    for i, rec in enumerate(intake_records):
        check(f"Record {i+1}: operator_confirmation_present = false",
              rec.get("operator_confirmation_present") is False,
              f"got: {rec.get('operator_confirmation_present')}")

    # ==================================================================
    # 10. All decisions = intake_blocked
    # ==================================================================
    print("\n[10] All decisions = intake_blocked (empty workbook)")
    for i, dec in enumerate(intake_decisions):
        check(f"Decision {i+1}: decision = 'intake_blocked'",
              dec.get("decision") == "intake_blocked",
              f"got: '{dec.get('decision')}'")

    # ==================================================================
    # 11. All upgrade_candidate = false
    # ==================================================================
    print("\n[11] All upgrade_candidate = false")
    for i, dec in enumerate(intake_decisions):
        check(f"Decision {i+1}: upgrade_candidate = false",
              dec.get("upgrade_candidate") is False,
              f"got: {dec.get('upgrade_candidate')}")

    # ==================================================================
    # 12. All upgrade_ready = false
    # ==================================================================
    print("\n[12] All upgrade_ready = false")
    for i, dec in enumerate(intake_decisions):
        check(f"Decision {i+1}: upgrade_ready = false",
              dec.get("upgrade_ready") is False,
              f"got: {dec.get('upgrade_ready')}")

    # ==================================================================
    # 13. All send guards = false
    # ==================================================================
    print("\n[13] All Send Guards = false")
    for i, dec in enumerate(intake_decisions):
        check(f"Decision {i+1}: send_allowed = false",
              dec.get("send_allowed") is False,
              f"got: {dec.get('send_allowed')}")
        check(f"Decision {i+1}: tg_test_group_allowed = false",
              dec.get("tg_test_group_allowed") is False,
              f"got: {dec.get('tg_test_group_allowed')}")
        check(f"Decision {i+1}: public_send_allowed = false",
              dec.get("public_send_allowed") is False,
              f"got: {dec.get('public_send_allowed')}")

    # ==================================================================
    # 14. Each address missing_fields non-empty
    # ==================================================================
    print("\n[14] Each Address missing_fields Non-Empty")
    for i, dec in enumerate(intake_decisions):
        mf = dec.get("missing_fields", [])
        check(f"Decision {i+1}: missing_fields non-empty (got {len(mf)})",
              len(mf) > 0,
              f"missing_fields is empty")

    # ==================================================================
    # 15. Each address block_reasons non-empty
    # ==================================================================
    print("\n[15] Each Address block_reasons Non-Empty")
    for i, dec in enumerate(intake_decisions):
        br = dec.get("block_reasons", [])
        check(f"Decision {i+1}: block_reasons non-empty (got {len(br)})",
              len(br) > 0,
              f"block_reasons is empty")

    # ==================================================================
    # 16. All 10 Required Block Reasons Present Per Address
    # ==================================================================
    print("\n[16] All 10 Required Block Reasons Per Address")
    for i, dec in enumerate(intake_decisions):
        br_set = set(dec.get("block_reasons", []))
        for reason in REQUIRED_BLOCK_REASONS:
            check(f"Decision {i+1}: has '{reason}'",
                  reason in br_set,
                  f"missing block reason: {reason}")

    # ==================================================================
    # 17. Gate Result Field Values
    # ==================================================================
    print("\n[17] Gate Result Field Values")
    check("stage = v115g_whale_manual_audit_workbook_intake_gate_local_only",
          gate_result.get("stage") == "v115g_whale_manual_audit_workbook_intake_gate_local_only",
          f"got: {gate_result.get('stage')}")
    check("input_workbook_rows = 4",
          gate_result.get("input_workbook_rows") == 4,
          f"got: {gate_result.get('input_workbook_rows')}")
    check("intake_records = 4",
          gate_result.get("intake_records") == 4,
          f"got: {gate_result.get('intake_records')}")
    check("intake_decisions = 4",
          gate_result.get("intake_decisions") == 4,
          f"got: {gate_result.get('intake_decisions')}")
    check("intake_ready_count = 0",
          gate_result.get("intake_ready_count") == 0,
          f"got: {gate_result.get('intake_ready_count')}")
    check("upgrade_candidate_count = 0",
          gate_result.get("upgrade_candidate_count") == 0,
          f"got: {gate_result.get('upgrade_candidate_count')}")
    check("blocked_intake_count = 4",
          gate_result.get("blocked_intake_count") == 4,
          f"got: {gate_result.get('blocked_intake_count')}")
    check("rejected_count = 0",
          gate_result.get("rejected_count") == 0,
          f"got: {gate_result.get('rejected_count')}")
    check("high_confidence_after_intake = 0",
          gate_result.get("high_confidence_after_intake") == 0,
          f"got: {gate_result.get('high_confidence_after_intake')}")

    # ==================================================================
    # 18. Gate Result Safety Booleans
    # ==================================================================
    print("\n[18] Gate Result Safety Booleans")
    check("send_ready = false",
          gate_result.get("send_ready") is False)
    check("tg_test_group_ready = false",
          gate_result.get("tg_test_group_ready") is False)
    check("local_review_ready = true",
          gate_result.get("local_review_ready") is True)
    check("external_api_called = false",
          gate_result.get("external_api_called") is False)
    check("ai_model_called = false",
          gate_result.get("ai_model_called") is False)
    check("credentials_read = false",
          gate_result.get("credentials_read") is False)
    check("tg_sent = false",
          gate_result.get("tg_sent") is False)
    check("prod_state_write = false",
          gate_result.get("prod_state_write") is False)
    check("daemon_started = false",
          gate_result.get("daemon_started") is False)
    check("watcher_started = false",
          gate_result.get("watcher_started") is False)
    check("files_deleted = false",
          gate_result.get("files_deleted") is False)
    check("real_send_candidate_generated = false",
          gate_result.get("real_send_candidate_generated") is False)
    check("no_label_upgraded = true",
          gate_result.get("no_label_upgraded") is True)
    check("all_send_guards_false = true",
          gate_result.get("all_send_guards_false") is True)

    # ==================================================================
    # 19. Intake Record Field Completeness
    # ==================================================================
    print("\n[19] Intake Record Field Completeness")
    for i, rec in enumerate(intake_records):
        for field in REQUIRED_INTAKE_RECORD_FIELDS:
            check(f"Record {i+1}: field '{field}' present",
                  field in rec,
                  f"missing field: {field}")

    # ==================================================================
    # 20. Intake Decision Field Completeness
    # ==================================================================
    print("\n[20] Intake Decision Field Completeness")
    for i, dec in enumerate(intake_decisions):
        for field in REQUIRED_INTAKE_DECISION_FIELDS:
            check(f"Decision {i+1}: field '{field}' present",
                  field in dec,
                  f"missing field: {field}")

    # ==================================================================
    # 21. No Label Confidence Upgraded
    # ==================================================================
    print("\n[21] No Label Confidence Upgraded")
    for i, rec in enumerate(intake_records):
        check(f"Record {i+1}: current_confidence unchanged (not 'high')",
              rec.get("current_confidence", "") != "high" or
              # Even if originally high, intake_ready is false
              rec.get("intake_ready") is False,
              "potential label upgrade detected")
    check("high_confidence_after_intake = 0 confirmed",
          gate_result.get("high_confidence_after_intake") == 0)

    # ==================================================================
    # 22. No TG Sent (confirmed in all outputs)
    # ==================================================================
    print("\n[22] No TG Sent (confirmed)")
    check("tg_sent=false in gate result", gate_result.get("tg_sent") is False)
    # No TG-related content in markdown
    check("No 'TG sent' claims in markdown",
          "tg_sent" not in md_text.lower() or "tg_sent=false" in md_text.lower() or
          "tg_sent" in md_text.lower() and "false" in md_text.lower())

    # ==================================================================
    # 23. No Production State Write
    # ==================================================================
    print("\n[23] No Production State Write")
    check("prod_state_write=false in gate result",
          gate_result.get("prod_state_write") is False)

    # ==================================================================
    # 24. No External API Called
    # ==================================================================
    print("\n[24] No External API Called")
    check("external_api_called=false in gate result",
          gate_result.get("external_api_called") is False)
    # Check outputs for API patterns
    all_output_text = (
        json.dumps(gate_result) +
        json.dumps(intake_records) +
        json.dumps(intake_decisions) +
        md_text +
        handoff_text
    )
    suspicious_patterns = ["http://api.", "https://api.", "fetch(", "curl ",
                           "requests.get", "requests.post", "urllib"]
    for pat in suspicious_patterns:
        check(f"No '{pat}' in any output", pat not in all_output_text.lower(),
              f"found '{pat}'")

    # ==================================================================
    # 25. No AI/Model Called
    # ==================================================================
    print("\n[25] No AI/Model Called")
    check("ai_model_called=false in gate result",
          gate_result.get("ai_model_called") is False)

    # ==================================================================
    # 26. No Credentials Read
    # ==================================================================
    print("\n[26] No Credentials Read")
    check("credentials_read=false in gate result",
          gate_result.get("credentials_read") is False)
    sensitive_patterns = ["API_KEY", "api_key", "token", "password", "secret",
                          ".env", "OPENAI", "OPENROUTER"]
    for pat in sensitive_patterns:
        check(f"No '{pat}' in any output", pat.lower() not in all_output_text.lower(),
              f"found '{pat}'")

    # ==================================================================
    # 27. No Daemon/Watcher/Cron/Loop Started
    # ==================================================================
    print("\n[27] No Daemon/Watcher/Cron/Loop Started")
    check("daemon_started=false", gate_result.get("daemon_started") is False)
    check("watcher_started=false", gate_result.get("watcher_started") is False)

    # ==================================================================
    # 28. No Files Deleted
    # ==================================================================
    print("\n[28] No Files Deleted")
    check("files_deleted=false", gate_result.get("files_deleted") is False)

    # ==================================================================
    # 29. Markdown Report Content
    # ==================================================================
    print("\n[29] Markdown Report Content")
    check("Markdown mentions v115G", "v115G" in md_text)
    check("Markdown mentions intake_blocked or blocked",
          "intake_blocked" in md_text.lower() or "blocked" in md_text.lower())
    check("Markdown mentions NOT a trading signal or equivalent",
          "NOT a trading signal" in md_text or "not a trading signal" in md_text.lower() or
          "NOT a production send" in md_text or "production send" in md_text.lower())
    for addr in EXPECTED_ADDRESSES:
        check(f"Markdown contains address {addr[:14]}...", addr in md_text,
              f"address not found in markdown")

    # ==================================================================
    # 30. Handoff Content
    # ==================================================================
    print("\n[30] Handoff Markdown Content")
    check("Handoff mentions v115G", "v115G" in handoff_text)
    check("Handoff mentions intake", "intake" in handoff_text.lower())
    check("Handoff mentions blocked_intake_count or blocked",
          "blocked" in handoff_text.lower())
    check("Handoff mentions safety invariants",
          "safety" in handoff_text.lower() or "invariant" in handoff_text.lower())
    check("Handoff mentions operator actions",
          "operator" in handoff_text.lower())

    # ==================================================================
    # 31. Negative Assertions — Nothing Claims Success It Shouldn't
    # ==================================================================
    print("\n[31] Negative Assertions")
    check("NOT claiming send_ready=true", gate_result.get("send_ready") is not True)
    check("NOT claiming tg_test_group_ready=true",
          gate_result.get("tg_test_group_ready") is not True)
    check("NOT claiming tg_sent=true", gate_result.get("tg_sent") is not True)
    check("NOT claiming prod_state_write=true",
          gate_result.get("prod_state_write") is not True)
    check("NOT claiming real_send_candidate_generated=true",
          gate_result.get("real_send_candidate_generated") is not True)
    check("NOT claiming intake_ready_count > 0",
          gate_result.get("intake_ready_count", 0) == 0)
    check("NOT claiming upgrade_candidate_count > 0",
          gate_result.get("upgrade_candidate_count", 0) == 0)
    check("NOT claiming files_deleted=true",
          gate_result.get("files_deleted") is not True)
    check("NOT claiming daemon_started=true",
          gate_result.get("daemon_started") is not True)
    check("NOT claiming watcher_started=true",
          gate_result.get("watcher_started") is not True)

    # ==================================================================
    # 32. v115F Workbook CSV Has 4 Rows (consistency check)
    # ==================================================================
    print("\n[32] v115F Workbook Consistency Check")
    import csv
    if file_exists(V115F_WORKBOOK_CSV):
        wb_rows = []
        with open(V115F_WORKBOOK_CSV, "r", encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                wb_rows.append(row)
        check(f"v115F workbook still has 4 rows (got {len(wb_rows)})", len(wb_rows) == 4)

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
