#!/usr/bin/env python3
"""
Test suite for v115H Whale Label Upgrade Adjudication Gate — Local Only
=========================================================================
Validates that the v115H adjudication gate runner produced correct outputs:
  - 4 adjudication records (all adjudication_ready=false)
  - 4 adjudication decisions (all adjudication_blocked)
  - Gate result JSON with all required invariants
  - All send guards false
  - No label upgrades
  - No external API calls
  - No TG send
  - No production state write
  - No modification of v114A-v115G old results
  - No credentials read
  - No daemon/watcher/cron/loop started
  - No files deleted

Current state: ALL 4 addresses adjudication_blocked because v115G intake blocked all.
"""

import json
import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RESULTS_DIR = os.path.join(BASE_DIR, "results")
CONFIG_DIR = os.path.join(BASE_DIR, "config")
RUNS_DIR = os.path.join(BASE_DIR, "runs", "market_radar")

# v115H outputs (must exist)
V115H_ADJ_RECORDS = os.path.join(
    RESULTS_DIR, "market_radar_v115h_whale_label_upgrade_adjudication_records.jsonl"
)
V115H_ADJ_DECISIONS = os.path.join(
    RESULTS_DIR, "market_radar_v115h_whale_label_upgrade_adjudication_decisions.jsonl"
)
V115H_GATE_RESULT = os.path.join(
    RESULTS_DIR, "market_radar_v115h_whale_label_upgrade_adjudication_gate_result.json"
)
V115H_MD = os.path.join(
    RUNS_DIR, "v115h_whale_label_upgrade_adjudication_gate_local_only.md"
)
V115H_HANDOFF = os.path.join(
    RUNS_DIR, "v115h_whale_label_upgrade_adjudication_gate_local_only_handoff.md"
)

# v115G outputs (must still exist, NOT modified)
V115G_INTAKE_RECORDS = os.path.join(
    RESULTS_DIR, "market_radar_v115g_whale_manual_audit_intake_records.jsonl"
)
V115G_INTAKE_DECISIONS = os.path.join(
    RESULTS_DIR, "market_radar_v115g_whale_manual_audit_intake_decisions.jsonl"
)
V115G_GATE_RESULT = os.path.join(
    RESULTS_DIR, "market_radar_v115g_whale_manual_audit_workbook_intake_gate_result.json"
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

# Expected addresses (from v115F workbook / v115G intake)
EXPECTED_ADDRESSES = [
    "0x082e843a431aef031264dc232693dd710aedca88",
    "0x50b309f78e774a756a2230e1769729094cac9f20",
    "0x6c8512516ce5669d35113a11ca8b8de322fd84f6",
    "0x8def9f50456c6c4e37fa5d3d57f108ed23992dae",
]

# All 5 required block reasons for adjudication_blocked
REQUIRED_BLOCK_REASONS = sorted([
    "INTAKE_NOT_READY",
    "UPGRADE_CANDIDATE_FALSE",
    "MANUAL_EVIDENCE_INCOMPLETE",
    "NO_CONFIDENCE_CHANGE_ALLOWED",
    "SEND_GUARDS_REMAIN_FALSE",
])

# Required fields in adjudication record
REQUIRED_ADJ_RECORD_FIELDS = [
    "address", "current_label", "current_confidence",
    "requested_confidence", "intake_ready", "upgrade_candidate",
    "manual_fields_complete", "evidence_requirements_met",
    "trusted_source_ok", "second_source_ok",
    "activity_pattern_ok", "operator_confirmation_ok",
    "adjudication_ready", "label_upgrade_allowed", "new_confidence",
]

# Required fields in adjudication decision
REQUIRED_ADJ_DECISION_FIELDS = [
    "address", "decision", "label_upgrade_allowed",
    "from_confidence", "to_confidence", "requested_confidence",
    "block_reasons", "send_allowed", "tg_test_group_allowed",
    "public_send_allowed",
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
    print("v115H Test Suite — Whale Label Upgrade Adjudication Gate")
    print("=" * 70)

    # ==================================================================
    # 1. File Existence — v115H Outputs
    # ==================================================================
    print("\n[1] File Existence — v115H Outputs")
    check("adjudication records .jsonl exists", file_exists(V115H_ADJ_RECORDS))
    check("adjudication decisions .jsonl exists", file_exists(V115H_ADJ_DECISIONS))
    check("gate result .json exists", file_exists(V115H_GATE_RESULT))
    check("markdown report exists", file_exists(V115H_MD))
    check("handoff markdown exists", file_exists(V115H_HANDOFF))

    # ==================================================================
    # 2. File Existence — v115G Outputs Still Intact
    # ==================================================================
    print("\n[2] File Existence — v115G Outputs Still Intact")
    check("v115G intake records still exist", file_exists(V115G_INTAKE_RECORDS))
    check("v115G intake decisions still exist", file_exists(V115G_INTAKE_DECISIONS))
    check("v115G gate result still exists", file_exists(V115G_GATE_RESULT))

    # ==================================================================
    # 3. File Existence — v114A-v115F Old Results Still Intact
    # ==================================================================
    print("\n[3] File Existence — v114A-v115F Old Results Still Intact")
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
    # 4. Data Loading
    # ==================================================================
    print("\n[4] Data Loading")
    adj_records = load_jsonl(V115H_ADJ_RECORDS)
    check(f"Adjudication records loaded ({len(adj_records)} records)", len(adj_records) > 0)

    adj_decisions = load_jsonl(V115H_ADJ_DECISIONS)
    check(f"Adjudication decisions loaded ({len(adj_decisions)} decisions)", len(adj_decisions) > 0)

    gate_result = load_json(V115H_GATE_RESULT)
    check("Gate result JSON parsed", isinstance(gate_result, dict))

    with open(V115H_MD, "r", encoding="utf-8") as f:
        md_text = f.read()
    check("Markdown report loaded", len(md_text) > 0)

    with open(V115H_HANDOFF, "r", encoding="utf-8") as f:
        handoff_text = f.read()
    check("Handoff markdown loaded", len(handoff_text) > 0)

    # ==================================================================
    # 5. Row Counts = 4
    # ==================================================================
    print("\n[5] Row Counts = 4")
    check(f"Adjudication records = 4 (got {len(adj_records)})", len(adj_records) == 4)
    check(f"Adjudication decisions = 4 (got {len(adj_decisions)})", len(adj_decisions) == 4)

    # ==================================================================
    # 6. All 4 Expected Addresses Present
    # ==================================================================
    print("\n[6] All 4 Expected Addresses")
    record_addresses = set(r.get("address", "") for r in adj_records)
    decision_addresses = set(d.get("address", "") for d in adj_decisions)
    for addr in EXPECTED_ADDRESSES:
        check(f"Address in adjudication records: {addr[:14]}...", addr in record_addresses)
        check(f"Address in adjudication decisions: {addr[:14]}...", addr in decision_addresses)

    # ==================================================================
    # 7. All adjudication_ready = false
    # ==================================================================
    print("\n[7] All adjudication_ready = false")
    for i, rec in enumerate(adj_records):
        check(f"Record {i+1}: adjudication_ready = false",
              rec.get("adjudication_ready") is False,
              f"got: {rec.get('adjudication_ready')}")

    # ==================================================================
    # 8. All label_upgrade_allowed = false (records)
    # ==================================================================
    print("\n[8] All label_upgrade_allowed = false (records)")
    for i, rec in enumerate(adj_records):
        check(f"Record {i+1}: label_upgrade_allowed = false",
              rec.get("label_upgrade_allowed") is False,
              f"got: {rec.get('label_upgrade_allowed')}")

    # ==================================================================
    # 9. All decisions = adjudication_blocked
    # ==================================================================
    print("\n[9] All decisions = adjudication_blocked")
    for i, dec in enumerate(adj_decisions):
        check(f"Decision {i+1}: decision = 'adjudication_blocked'",
              dec.get("decision") == "adjudication_blocked",
              f"got: '{dec.get('decision')}'")

    # ==================================================================
    # 10. All label_upgrade_allowed = false (decisions)
    # ==================================================================
    print("\n[10] All label_upgrade_allowed = false (decisions)")
    for i, dec in enumerate(adj_decisions):
        check(f"Decision {i+1}: label_upgrade_allowed = false",
              dec.get("label_upgrade_allowed") is False,
              f"got: {dec.get('label_upgrade_allowed')}")

    # ==================================================================
    # 11. All send guards = false
    # ==================================================================
    print("\n[11] All Send Guards = false")
    for i, dec in enumerate(adj_decisions):
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
    # 12. All new_confidence = current_confidence (no upgrade)
    # ==================================================================
    print("\n[12] All new_confidence = current_confidence (no upgrade)")
    for i, rec in enumerate(adj_records):
        new_c = rec.get("new_confidence", "")
        cur_c = rec.get("current_confidence", "")
        check(f"Record {i+1}: new_confidence = current_confidence ({cur_c})",
              new_c == cur_c,
              f"new={new_c} != current={cur_c}")

    # ==================================================================
    # 13. All from_confidence = to_confidence (decisions, no upgrade)
    # ==================================================================
    print("\n[13] All from_confidence = to_confidence (no upgrade in decisions)")
    for i, dec in enumerate(adj_decisions):
        from_c = dec.get("from_confidence", "")
        to_c = dec.get("to_confidence", "")
        check(f"Decision {i+1}: from_confidence = to_confidence ({from_c})",
              from_c == to_c,
              f"from={from_c} != to={to_c}")

    # ==================================================================
    # 14. No to_confidence = "high"
    # ==================================================================
    print("\n[14] No to_confidence = 'high' (no upgrades)")
    for i, dec in enumerate(adj_decisions):
        check(f"Decision {i+1}: to_confidence != 'high'",
              dec.get("to_confidence") != "high",
              f"got: {dec.get('to_confidence')}")

    # ==================================================================
    # 15. All requested_confidence = "high"
    # ==================================================================
    print("\n[15] All requested_confidence = 'high'")
    for i, rec in enumerate(adj_records):
        check(f"Record {i+1}: requested_confidence = 'high'",
              rec.get("requested_confidence") == "high",
              f"got: '{rec.get('requested_confidence')}'")
    for i, dec in enumerate(adj_decisions):
        check(f"Decision {i+1}: requested_confidence = 'high'",
              dec.get("requested_confidence") == "high",
              f"got: '{dec.get('requested_confidence')}'")

    # ==================================================================
    # 16. All block_reasons non-empty
    # ==================================================================
    print("\n[16] All block_reasons non-empty")
    for i, dec in enumerate(adj_decisions):
        br = dec.get("block_reasons", [])
        check(f"Decision {i+1}: block_reasons non-empty (got {len(br)})",
              len(br) > 0,
              f"block_reasons is empty")

    # ==================================================================
    # 17. All 5 Required Block Reasons Present Per Address
    # ==================================================================
    print("\n[17] All 5 Required Block Reasons Per Address")
    for i, dec in enumerate(adj_decisions):
        br_set = set(dec.get("block_reasons", []))
        for reason in REQUIRED_BLOCK_REASONS:
            check(f"Decision {i+1}: has '{reason}'",
                  reason in br_set,
                  f"missing block reason: {reason}")

    # ==================================================================
    # 18. Gate Result Field Values
    # ==================================================================
    print("\n[18] Gate Result Field Values")
    check("stage = v115h_whale_label_upgrade_adjudication_gate_local_only",
          gate_result.get("stage") == "v115h_whale_label_upgrade_adjudication_gate_local_only",
          f"got: {gate_result.get('stage')}")
    check("input_intake_records = 4",
          gate_result.get("input_intake_records") == 4,
          f"got: {gate_result.get('input_intake_records')}")
    check("input_intake_decisions = 4",
          gate_result.get("input_intake_decisions") == 4,
          f"got: {gate_result.get('input_intake_decisions')}")
    check("adjudication_records = 4",
          gate_result.get("adjudication_records") == 4,
          f"got: {gate_result.get('adjudication_records')}")
    check("adjudication_decisions = 4",
          gate_result.get("adjudication_decisions") == 4,
          f"got: {gate_result.get('adjudication_decisions')}")
    check("adjudication_ready_count = 0",
          gate_result.get("adjudication_ready_count") == 0,
          f"got: {gate_result.get('adjudication_ready_count')}")
    check("label_upgrade_allowed_count = 0",
          gate_result.get("label_upgrade_allowed_count") == 0,
          f"got: {gate_result.get('label_upgrade_allowed_count')}")
    check("label_upgraded_count = 0",
          gate_result.get("label_upgraded_count") == 0,
          f"got: {gate_result.get('label_upgraded_count')}")
    check("blocked_adjudication_count = 4",
          gate_result.get("blocked_adjudication_count") == 4,
          f"got: {gate_result.get('blocked_adjudication_count')}")
    check("high_confidence_after_adjudication = 0",
          gate_result.get("high_confidence_after_adjudication") == 0,
          f"got: {gate_result.get('high_confidence_after_adjudication')}")

    # ==================================================================
    # 19. Gate Result Safety Booleans
    # ==================================================================
    print("\n[19] Gate Result Safety Booleans")
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

    # ==================================================================
    # 20. Adjudication Record Field Completeness
    # ==================================================================
    print("\n[20] Adjudication Record Field Completeness")
    for i, rec in enumerate(adj_records):
        for field in REQUIRED_ADJ_RECORD_FIELDS:
            check(f"Record {i+1}: field '{field}' present",
                  field in rec,
                  f"missing field: {field}")

    # ==================================================================
    # 21. Adjudication Decision Field Completeness
    # ==================================================================
    print("\n[21] Adjudication Decision Field Completeness")
    for i, dec in enumerate(adj_decisions):
        for field in REQUIRED_ADJ_DECISION_FIELDS:
            check(f"Decision {i+1}: field '{field}' present",
                  field in dec,
                  f"missing field: {field}")

    # ==================================================================
    # 22. No Label Confidence Upgraded
    # ==================================================================
    print("\n[22] No Label Confidence Upgraded")
    check("label_upgraded_count = 0 confirmed",
          gate_result.get("label_upgraded_count") == 0)
    check("high_confidence_after_adjudication = 0 confirmed",
          gate_result.get("high_confidence_after_adjudication") == 0)

    # ==================================================================
    # 23. Evidence Fields Reflect False (empty workbook)
    # ==================================================================
    print("\n[23] Evidence Fields All False (empty workbook)")
    for i, rec in enumerate(adj_records):
        check(f"Record {i+1}: trusted_source_ok = false",
              rec.get("trusted_source_ok") is False)
        check(f"Record {i+1}: second_source_ok = false",
              rec.get("second_source_ok") is False)
        check(f"Record {i+1}: activity_pattern_ok = false",
              rec.get("activity_pattern_ok") is False)
        check(f"Record {i+1}: operator_confirmation_ok = false",
              rec.get("operator_confirmation_ok") is False)
        check(f"Record {i+1}: evidence_requirements_met = false",
              rec.get("evidence_requirements_met") is False)

    # ==================================================================
    # 24. No TG Sent (confirmed in all outputs)
    # ==================================================================
    print("\n[24] No TG Sent (confirmed)")
    check("tg_sent=false in gate result", gate_result.get("tg_sent") is False)

    # ==================================================================
    # 25. No Production State Write
    # ==================================================================
    print("\n[25] No Production State Write")
    check("prod_state_write=false in gate result",
          gate_result.get("prod_state_write") is False)

    # ==================================================================
    # 26. No External API Called
    # ==================================================================
    print("\n[26] No External API Called")
    check("external_api_called=false in gate result",
          gate_result.get("external_api_called") is False)
    all_output_text = (
        json.dumps(gate_result) +
        json.dumps(adj_records) +
        json.dumps(adj_decisions) +
        md_text +
        handoff_text
    )
    suspicious_patterns = ["http://api.", "https://api.", "fetch(", "curl ",
                           "requests.get", "requests.post", "urllib"]
    for pat in suspicious_patterns:
        check(f"No '{pat}' in any output", pat not in all_output_text.lower(),
              f"found '{pat}'")

    # ==================================================================
    # 27. No AI/Model Called
    # ==================================================================
    print("\n[27] No AI/Model Called")
    check("ai_model_called=false in gate result",
          gate_result.get("ai_model_called") is False)

    # ==================================================================
    # 28. No Credentials Read
    # ==================================================================
    print("\n[28] No Credentials Read")
    check("credentials_read=false in gate result",
          gate_result.get("credentials_read") is False)
    sensitive_patterns = ["API_KEY", "api_key", "token", "password", "secret",
                          ".env", "OPENAI", "OPENROUTER"]
    for pat in sensitive_patterns:
        check(f"No '{pat}' in any output", pat.lower() not in all_output_text.lower(),
              f"found '{pat}'")

    # ==================================================================
    # 29. No Daemon/Watcher/Cron/Loop Started
    # ==================================================================
    print("\n[29] No Daemon/Watcher/Cron/Loop Started")
    check("daemon_started=false", gate_result.get("daemon_started") is False)
    check("watcher_started=false", gate_result.get("watcher_started") is False)

    # ==================================================================
    # 30. No Files Deleted
    # ==================================================================
    print("\n[30] No Files Deleted")
    check("files_deleted=false", gate_result.get("files_deleted") is False)

    # ==================================================================
    # 31. No Real Send Candidate Generated
    # ==================================================================
    print("\n[31] No Real Send Candidate Generated")
    check("real_send_candidate_generated=false",
          gate_result.get("real_send_candidate_generated") is False)

    # ==================================================================
    # 32. Markdown Report Content
    # ==================================================================
    print("\n[32] Markdown Report Content")
    check("Markdown mentions v115H", "v115H" in md_text)
    check("Markdown mentions adjudication_blocked or blocked",
          "adjudication_blocked" in md_text or "blocked" in md_text.lower())
    check("Markdown mentions NOT a trading signal or equivalent",
          "NOT a trading signal" in md_text or "not a trading signal" in md_text.lower() or
          "NOT a production send" in md_text or "production send" in md_text.lower())
    for addr in EXPECTED_ADDRESSES:
        check(f"Markdown contains address {addr[:14]}...", addr in md_text,
              f"address not found in markdown")

    # ==================================================================
    # 33. Handoff Markdown Content
    # ==================================================================
    print("\n[33] Handoff Markdown Content")
    check("Handoff mentions v115H", "v115H" in handoff_text)
    check("Handoff mentions adjudication", "adjudication" in handoff_text.lower())
    check("Handoff mentions blocked or adjudication_blocked",
          "blocked" in handoff_text.lower())
    check("Handoff mentions safety invariants",
          "safety" in handoff_text.lower() or "invariant" in handoff_text.lower())
    check("Handoff mentions operator actions",
          "operator" in handoff_text.lower())

    # ==================================================================
    # 34. Negative Assertions
    # ==================================================================
    print("\n[34] Negative Assertions — Nothing Claims Success It Shouldn't")
    check("NOT claiming send_ready=true", gate_result.get("send_ready") is not True)
    check("NOT claiming tg_test_group_ready=true",
          gate_result.get("tg_test_group_ready") is not True)
    check("NOT claiming tg_sent=true", gate_result.get("tg_sent") is not True)
    check("NOT claiming prod_state_write=true",
          gate_result.get("prod_state_write") is not True)
    check("NOT claiming real_send_candidate_generated=true",
          gate_result.get("real_send_candidate_generated") is not True)
    check("NOT claiming adjudication_ready_count > 0",
          gate_result.get("adjudication_ready_count", 0) == 0)
    check("NOT claiming label_upgrade_allowed_count > 0",
          gate_result.get("label_upgrade_allowed_count", 0) == 0)
    check("NOT claiming files_deleted=true",
          gate_result.get("files_deleted") is not True)
    check("NOT claiming daemon_started=true",
          gate_result.get("daemon_started") is not True)
    check("NOT claiming watcher_started=true",
          gate_result.get("watcher_started") is not True)
    check("NOT claiming external_api_called=true",
          gate_result.get("external_api_called") is not True)
    check("NOT claiming ai_model_called=true",
          gate_result.get("ai_model_called") is not True)
    check("NOT claiming credentials_read=true",
          gate_result.get("credentials_read") is not True)

    # ==================================================================
    # 35. v115G Input Files Still Have 4 Entries (consistency)
    # ==================================================================
    print("\n[35] v115G Input File Consistency Check")
    if file_exists(V115G_INTAKE_RECORDS):
        intake_recs = load_jsonl(V115G_INTAKE_RECORDS)
        check(f"v115G intake records still has 4 entries (got {len(intake_recs)})",
              len(intake_recs) == 4)
    if file_exists(V115G_INTAKE_DECISIONS):
        intake_decs = load_jsonl(V115G_INTAKE_DECISIONS)
        check(f"v115G intake decisions still has 4 entries (got {len(intake_decs)})",
              len(intake_decs) == 4)

    # ==================================================================
    # 36. v115F Workbook CSV Has 4 Rows (consistency check)
    # ==================================================================
    print("\n[36] v115F Workbook Consistency Check")
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
