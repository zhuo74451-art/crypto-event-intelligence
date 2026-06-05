#!/usr/bin/env python3
"""
Test suite for v115L Whale Label Evidence Scoring Gate — Local Only
=====================================================================
Validates that the v115L runner produced correct outputs:

Real workbook path (v115F, empty operator fields):
  - real workbook rows = 4
  - real scoring records = 4
  - real scoring decisions = 4
  - real scoring passed count = 0
  - real scoring blocked count = 4

Fixture path (v115I, all evidence complete):
  - fixture rows = 1
  - fixture scoring passed count = 1
  - fixture high confidence allowed count = 1
  - fixture label upgraded count = 0

Rejected source check:
  - rejected source negative check passed = true
  - rejected source cannot grant high confidence = false

Safety:
  - All HC requirements referenced by scoring gate
  - v115F workbook NOT modified
  - Real label NOT upgraded
  - No real send candidate generated
  - All send guards = false
  - No TG sent
  - No prod state write
  - No external API called
  - No AI/model called
  - No credentials read
  - No daemon/watcher/cron/loop started
  - No files deleted
  - No modification of v114A-v115K old results
"""

import csv
import json
import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RESULTS_DIR = os.path.join(BASE_DIR, "results")
CONFIG_DIR = os.path.join(BASE_DIR, "config")
RUNS_DIR = os.path.join(BASE_DIR, "runs", "market_radar")
FIXTURES_DIR = os.path.join(BASE_DIR, "fixtures", "market_radar")

# ---------------------------------------------------------------------------
# v115L outputs (must exist)
# ---------------------------------------------------------------------------
V115L_REAL_RECORDS = os.path.join(
    RESULTS_DIR, "market_radar_v115l_whale_real_workbook_evidence_scoring_records.jsonl"
)
V115L_REAL_DECISIONS = os.path.join(
    RESULTS_DIR, "market_radar_v115l_whale_real_workbook_evidence_scoring_decisions.jsonl"
)
V115L_FIXTURE_RECORDS = os.path.join(
    RESULTS_DIR, "market_radar_v115l_whale_fixture_evidence_scoring_records.jsonl"
)
V115L_FIXTURE_DECISIONS = os.path.join(
    RESULTS_DIR, "market_radar_v115l_whale_fixture_evidence_scoring_decisions.jsonl"
)
V115L_GATE_RESULT = os.path.join(
    RESULTS_DIR, "market_radar_v115l_whale_label_evidence_scoring_gate_result.json"
)
V115L_MD = os.path.join(
    RUNS_DIR, "v115l_whale_label_evidence_scoring_gate_local_only.md"
)
V115L_HANDOFF = os.path.join(
    RUNS_DIR, "v115l_whale_label_evidence_scoring_gate_local_only_handoff.md"
)

# ---------------------------------------------------------------------------
# Input files (must still exist, unmodified)
# ---------------------------------------------------------------------------
V115K_REGISTRY = os.path.join(
    CONFIG_DIR, "market_radar_v115k_whale_label_evidence_source_registry.json"
)
V115K_SCORING_POLICY = os.path.join(
    CONFIG_DIR, "market_radar_v115k_whale_label_evidence_scoring_policy.json"
)
V115F_WORKBOOK = os.path.join(
    RUNS_DIR, "v115f_whale_address_audit_operator_workbook.csv"
)
V115I_FIXTURE = os.path.join(
    FIXTURES_DIR, "v115i_whale_manual_audit_positive_path_fixture.csv"
)

# ---------------------------------------------------------------------------
# Old results to check still exist
# ---------------------------------------------------------------------------
OLD_RESULTS_TO_CHECK = [
    # v115E
    os.path.join(RESULTS_DIR, "market_radar_v115e_whale_label_upgrade_decisions.jsonl"),
    os.path.join(RESULTS_DIR, "market_radar_v115e_whale_address_audit_evidence_requests.jsonl"),
    os.path.join(RESULTS_DIR, "market_radar_v115e_whale_address_manual_audit_forms.jsonl"),
    os.path.join(RESULTS_DIR, "market_radar_v115e_whale_address_audit_evidence_pack_result.json"),
    # v115F
    os.path.join(RESULTS_DIR, "market_radar_v115f_whale_address_audit_operator_workbook_manifest.json"),
    os.path.join(RESULTS_DIR, "market_radar_v115f_whale_address_audit_operator_workbook_gate_result.json"),
    # v115G
    os.path.join(RESULTS_DIR, "market_radar_v115g_whale_manual_audit_intake_records.jsonl"),
    os.path.join(RESULTS_DIR, "market_radar_v115g_whale_manual_audit_intake_decisions.jsonl"),
    os.path.join(RESULTS_DIR, "market_radar_v115g_whale_manual_audit_workbook_intake_gate_result.json"),
    # v115H
    os.path.join(RESULTS_DIR, "market_radar_v115h_whale_label_upgrade_adjudication_records.jsonl"),
    os.path.join(RESULTS_DIR, "market_radar_v115h_whale_label_upgrade_adjudication_decisions.jsonl"),
    os.path.join(RESULTS_DIR, "market_radar_v115h_whale_label_upgrade_adjudication_gate_result.json"),
    # v115I
    os.path.join(RESULTS_DIR, "market_radar_v115i_whale_manual_audit_positive_path_fixture_gate_result.json"),
    os.path.join(RESULTS_DIR, "market_radar_v115i_whale_manual_audit_positive_path_intake_records.jsonl"),
    os.path.join(RESULTS_DIR, "market_radar_v115i_whale_manual_audit_positive_path_intake_decisions.jsonl"),
    os.path.join(RESULTS_DIR, "market_radar_v115i_whale_manual_audit_positive_path_adjudication_records.jsonl"),
    os.path.join(RESULTS_DIR, "market_radar_v115i_whale_manual_audit_positive_path_adjudication_decisions.jsonl"),
    # v115J
    os.path.join(RESULTS_DIR, "market_radar_v115j_whale_manual_audit_gate_rule_parity_matrix.json"),
    os.path.join(RESULTS_DIR, "market_radar_v115j_whale_manual_audit_gate_rule_parity_findings.jsonl"),
    os.path.join(RESULTS_DIR, "market_radar_v115j_whale_manual_audit_gate_rule_parity_audit_result.json"),
    # v115K
    os.path.join(RESULTS_DIR, "market_radar_v115k_whale_label_evidence_policy_gate_result.json"),
    os.path.join(RESULTS_DIR, "market_radar_v115k_whale_label_evidence_source_registry_result.json"),
    os.path.join(RESULTS_DIR, "market_radar_v115k_whale_label_evidence_scoring_policy_result.json"),
]

# ---------------------------------------------------------------------------
# HC requirement IDs that must be referenced in the gate
# ---------------------------------------------------------------------------
HC_REQUIREMENT_IDS = [
    "HC_REQ_001",
    "HC_REQ_002",
    "HC_REQ_003",
    "HC_REQ_004",
    "HC_REQ_005",
    "HC_REQ_006",
    "HC_REQ_007",
    "HC_REQ_008",
    "HC_REQ_009",
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


def load_csv_dict(path: str) -> list:
    rows = []
    with open(path, "r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)
    return rows


def parse_bool_csv(val):
    if isinstance(val, bool):
        return val
    if isinstance(val, str):
        return val.strip().lower() == "true"
    return False


def main():
    global passed, failed

    print("=" * 70)
    print("v115L Test Suite — Evidence Scoring Gate")
    print("=" * 70)

    # ==================================================================
    # 1. File Existence — v115L Outputs
    # ==================================================================
    print("\n[1] File Existence — v115L Outputs")
    check("Real scoring records .jsonl exists", file_exists(V115L_REAL_RECORDS))
    check("Real scoring decisions .jsonl exists", file_exists(V115L_REAL_DECISIONS))
    check("Fixture scoring records .jsonl exists", file_exists(V115L_FIXTURE_RECORDS))
    check("Fixture scoring decisions .jsonl exists", file_exists(V115L_FIXTURE_DECISIONS))
    check("Gate result .json exists", file_exists(V115L_GATE_RESULT))
    check("Markdown report exists", file_exists(V115L_MD))
    check("Handoff markdown exists", file_exists(V115L_HANDOFF))

    # ==================================================================
    # 2. File Existence — Input Sources Still Intact
    # ==================================================================
    print("\n[2] File Existence — Input Sources Still Intact")
    check("v115K registry config exists", file_exists(V115K_REGISTRY))
    check("v115K scoring policy config exists", file_exists(V115K_SCORING_POLICY))
    check("v115F workbook exists", file_exists(V115F_WORKBOOK))
    check("v115I fixture CSV exists", file_exists(V115I_FIXTURE))

    # ==================================================================
    # 3. Old Results Still Intact (v114A-v115K)
    # ==================================================================
    print("\n[3] Old Results v114A-v115K Still Intact")
    for path in OLD_RESULTS_TO_CHECK:
        fname = os.path.basename(path)
        check(f"{fname} exists", file_exists(path))

    # ==================================================================
    # 4. Data Loading
    # ==================================================================
    print("\n[4] Data Loading")
    real_records = load_jsonl(V115L_REAL_RECORDS)
    check(f"Real scoring records loaded ({len(real_records)} records)", len(real_records) > 0)

    real_decisions = load_jsonl(V115L_REAL_DECISIONS)
    check(f"Real scoring decisions loaded ({len(real_decisions)} decisions)", len(real_decisions) > 0)

    fixture_records = load_jsonl(V115L_FIXTURE_RECORDS)
    check(f"Fixture scoring records loaded ({len(fixture_records)} records)", len(fixture_records) > 0)

    fixture_decisions = load_jsonl(V115L_FIXTURE_DECISIONS)
    check(f"Fixture scoring decisions loaded ({len(fixture_decisions)} decisions)", len(fixture_decisions) > 0)

    gate_result = load_json(V115L_GATE_RESULT)
    check("Gate result JSON parsed", isinstance(gate_result, dict))

    with open(V115L_MD, "r", encoding="utf-8") as f:
        md_text = f.read()
    check("Markdown report loaded", len(md_text) > 0)

    with open(V115L_HANDOFF, "r", encoding="utf-8") as f:
        handoff_text = f.read()
    check("Handoff markdown loaded", len(handoff_text) > 0)

    # ==================================================================
    # 5. registry_loaded = true
    # ==================================================================
    print("\n[5] registry_loaded = true")
    check("registry_loaded = true", gate_result.get("registry_loaded") is True,
          f"got: {gate_result.get('registry_loaded')}")

    # ==================================================================
    # 6. scoring_policy_loaded = true
    # ==================================================================
    print("\n[6] scoring_policy_loaded = true")
    check("scoring_policy_loaded = true", gate_result.get("scoring_policy_loaded") is True,
          f"got: {gate_result.get('scoring_policy_loaded')}")

    # ==================================================================
    # 7. Real Workbook — Row Counts
    # ==================================================================
    print("\n[7] Real Workbook — Row Counts = 4")
    check("real_workbook_rows = 4", gate_result.get("real_workbook_rows") == 4,
          f"got: {gate_result.get('real_workbook_rows')}")
    check("real_scoring_records = 4", gate_result.get("real_scoring_records") == 4,
          f"got: {gate_result.get('real_scoring_records')}")
    check("real_scoring_decisions = 4", gate_result.get("real_scoring_decisions") == 4,
          f"got: {gate_result.get('real_scoring_decisions')}")
    check(f"real_records.jsonl has 4 entries (got {len(real_records)})", len(real_records) == 4)
    check(f"real_decisions.jsonl has 4 entries (got {len(real_decisions)})", len(real_decisions) == 4)

    # ==================================================================
    # 8. Real Workbook — Scoring Results
    # ==================================================================
    print("\n[8] Real Workbook — Scoring Results (0 passed, 4 blocked)")
    check("real_scoring_passed_count = 0", gate_result.get("real_scoring_passed_count") == 0,
          f"got: {gate_result.get('real_scoring_passed_count')}")
    check("real_scoring_blocked_count = 4", gate_result.get("real_scoring_blocked_count") == 4,
          f"got: {gate_result.get('real_scoring_blocked_count')}")

    # Verify each real decision is scoring_blocked
    for i, dec in enumerate(real_decisions):
        check(f"Real decision {i + 1}: decision = 'scoring_blocked'",
              dec.get("decision") == "scoring_blocked",
              f"got: '{dec.get('decision')}'")
        check(f"Real decision {i + 1}: high_confidence_allowed = false",
              dec.get("high_confidence_allowed") is False,
              f"got: {dec.get('high_confidence_allowed')}")
        check(f"Real decision {i + 1}: label_upgrade_allowed = false",
              dec.get("label_upgrade_allowed") is False,
              f"got: {dec.get('label_upgrade_allowed')}")
        check(f"Real decision {i + 1}: send_allowed = false",
              dec.get("send_allowed") is False)
        check(f"Real decision {i + 1}: tg_test_group_allowed = false",
              dec.get("tg_test_group_allowed") is False)
        check(f"Real decision {i + 1}: public_send_allowed = false",
              dec.get("public_send_allowed") is False)

    # ==================================================================
    # 9. Real Workbook — Scoring Records Fields
    # ==================================================================
    print("\n[9] Real Workbook — Scoring Records Required Fields")
    required_record_fields = [
        "address", "current_label", "current_confidence", "target_confidence",
        "trusted_source_present", "trusted_source_category", "trusted_source_accepted",
        "second_source_present", "second_source_category", "second_source_accepted",
        "activity_pattern_present", "activity_source_accepted",
        "operator_confirmation_present", "reviewer_present", "reviewed_at_present",
        "ready_for_upgrade", "rejected_source_detected", "evidence_score",
        "minimum_high_confidence_requirements_met",
    ]
    for i, rec in enumerate(real_records):
        for field in required_record_fields:
            check(f"Real record {i + 1}: field '{field}' present",
                  field in rec, f"missing field: {field}")
        # All of these should show evidence not present (empty workbook)
        check(f"Real record {i + 1}: trusted_source_present = false",
              rec.get("trusted_source_present") is False,
              f"got: {rec.get('trusted_source_present')}")
        check(f"Real record {i + 1}: minimum_high_confidence_requirements_met = false",
              rec.get("minimum_high_confidence_requirements_met") is False,
              f"got: {rec.get('minimum_high_confidence_requirements_met')}")

    # ==================================================================
    # 10. Real Scoring Decisions — Required Fields
    # ==================================================================
    print("\n[10] Real Scoring Decisions — Required Fields")
    required_decision_fields = [
        "address", "decision", "evidence_score", "high_confidence_allowed",
        "label_upgrade_allowed", "block_reasons", "send_allowed",
        "tg_test_group_allowed", "public_send_allowed",
    ]
    for i, dec in enumerate(real_decisions):
        for field in required_decision_fields:
            check(f"Real decision {i + 1}: field '{field}' present",
                  field in dec, f"missing field: {field}")
        check(f"Real decision {i + 1}: block_reasons is non-empty",
              len(dec.get("block_reasons", "")) > 0,
              "block_reasons should list why it's blocked")

    # ==================================================================
    # 11. Fixture — Row Counts = 1
    # ==================================================================
    print("\n[11] Fixture — Row Counts = 1")
    check("fixture_rows = 1", gate_result.get("fixture_rows") == 1,
          f"got: {gate_result.get('fixture_rows')}")
    check("fixture_scoring_records = 1", gate_result.get("fixture_scoring_records") == 1,
          f"got: {gate_result.get('fixture_scoring_records')}")
    check("fixture_scoring_decisions = 1", gate_result.get("fixture_scoring_decisions") == 1,
          f"got: {gate_result.get('fixture_scoring_decisions')}")
    check(f"fixture_records.jsonl has 1 entry (got {len(fixture_records)})", len(fixture_records) == 1)
    check(f"fixture_decisions.jsonl has 1 entry (got {len(fixture_decisions)})", len(fixture_decisions) == 1)

    # ==================================================================
    # 12. Fixture — Scoring Passed
    # ==================================================================
    print("\n[12] Fixture — Scoring Passed Count = 1")
    check("fixture_scoring_passed_count = 1", gate_result.get("fixture_scoring_passed_count") == 1,
          f"got: {gate_result.get('fixture_scoring_passed_count')}")
    check("fixture_high_confidence_allowed_count = 1",
          gate_result.get("fixture_high_confidence_allowed_count") == 1,
          f"got: {gate_result.get('fixture_high_confidence_allowed_count')}")
    check("fixture_label_upgraded_count = 0",
          gate_result.get("fixture_label_upgraded_count") == 0,
          f"got: {gate_result.get('fixture_label_upgraded_count')}")

    # ==================================================================
    # 13. Fixture Decision Content
    # ==================================================================
    print("\n[13] Fixture Decision — scoring_passed_for_fixture_only")
    for i, dec in enumerate(fixture_decisions):
        check(f"Fixture decision {i + 1}: decision starts with 'scoring_passed'",
              dec.get("decision", "").startswith("scoring_passed"),
              f"got: '{dec.get('decision')}'")
        check(f"Fixture decision {i + 1}: high_confidence_allowed = true",
              dec.get("high_confidence_allowed") is True,
              f"got: {dec.get('high_confidence_allowed')}")
        check(f"Fixture decision {i + 1}: label_upgrade_allowed = false (fixture, no real upgrade)",
              dec.get("label_upgrade_allowed") is False,
              f"got: {dec.get('label_upgrade_allowed')}")
        check(f"Fixture decision {i + 1}: block_reasons is empty",
              dec.get("block_reasons", "") == "",
              f"got: '{dec.get('block_reasons')}'")
        check(f"Fixture decision {i + 1}: send_allowed = false",
              dec.get("send_allowed") is False)
        check(f"Fixture decision {i + 1}: tg_test_group_allowed = false",
              dec.get("tg_test_group_allowed") is False)
        check(f"Fixture decision {i + 1}: public_send_allowed = false",
              dec.get("public_send_allowed") is False)

    # ==================================================================
    # 14. Fixture Record Content
    # ==================================================================
    print("\n[14] Fixture Record — Evidence Fields Accepted")
    for i, rec in enumerate(fixture_records):
        check(f"Fixture record {i + 1}: trusted_source_present = true",
              rec.get("trusted_source_present") is True)
        check(f"Fixture record {i + 1}: trusted_source_accepted = true",
              rec.get("trusted_source_accepted") is True)
        check(f"Fixture record {i + 1}: second_source_present = true",
              rec.get("second_source_present") is True)
        check(f"Fixture record {i + 1}: second_source_accepted = true",
              rec.get("second_source_accepted") is True)
        check(f"Fixture record {i + 1}: activity_pattern_present = true",
              rec.get("activity_pattern_present") is True)
        check(f"Fixture record {i + 1}: operator_confirmation_present = true",
              rec.get("operator_confirmation_present") is True)
        check(f"Fixture record {i + 1}: reviewer_present = true",
              rec.get("reviewer_present") is True)
        check(f"Fixture record {i + 1}: reviewed_at_present = true",
              rec.get("reviewed_at_present") is True)
        check(f"Fixture record {i + 1}: ready_for_upgrade = true",
              rec.get("ready_for_upgrade") is True)
        check(f"Fixture record {i + 1}: minimum_high_confidence_requirements_met = true",
              rec.get("minimum_high_confidence_requirements_met") is True,
              f"got: {rec.get('minimum_high_confidence_requirements_met')}")

    # ==================================================================
    # 15. Rejected Source Negative Check
    # ==================================================================
    print("\n[15] Rejected Source Negative Check")
    check("rejected_source_negative_check_passed = true",
          gate_result.get("rejected_source_negative_check_passed") is True,
          f"got: {gate_result.get('rejected_source_negative_check_passed')}")
    check("rejected_source_can_grant_high_confidence = false",
          gate_result.get("rejected_source_can_grant_high_confidence") is False,
          f"got: {gate_result.get('rejected_source_can_grant_high_confidence')}")

    # ==================================================================
    # 16. HC Requirements All Referenced
    # ==================================================================
    print("\n[16] HC Requirements All Referenced by Scoring Gate")
    hc_refs = gate_result.get("hc_requirement_ids_referenced", [])
    for req_id in HC_REQUIREMENT_IDS:
        check(f"HC requirement '{req_id}' referenced in gate result",
              req_id in hc_refs,
              f"missing from hc_requirement_ids_referenced: {req_id}")
    check(f"All 9 HC requirements referenced (got {len(hc_refs)})", len(hc_refs) >= 9)

    # Also verify hc_requirements_detail present in each record
    for i, rec in enumerate(real_records):
        hc_detail = rec.get("hc_requirements_detail", {})
        for req_id in HC_REQUIREMENT_IDS:
            check(f"Real record {i + 1}: hc_requirements_detail has '{req_id}'",
                  req_id in hc_detail,
                  f"missing HC detail: {req_id}")
    for i, rec in enumerate(fixture_records):
        hc_detail = rec.get("hc_requirements_detail", {})
        for req_id in HC_REQUIREMENT_IDS:
            check(f"Fixture record {i + 1}: hc_requirements_detail has '{req_id}'",
                  req_id in hc_detail,
                  f"missing HC detail: {req_id}")

    # ==================================================================
    # 17. Real v115F Workbook NOT Modified
    # ==================================================================
    print("\n[17] Real v115F Workbook NOT Modified")
    check("real_workbook_modified = false", gate_result.get("real_workbook_modified") is False)

    # Verify workbook content
    wb_rows = load_csv_dict(V115F_WORKBOOK)
    check(f"v115F workbook still has 4 rows (got {len(wb_rows)})", len(wb_rows) == 4)

    operator_fields = [
        "trusted_source_label_value",
        "trusted_source_url_or_note",
        "second_source_label_value",
        "second_source_url_or_note",
        "activity_pattern_note",
        "operator_confirmed_label",
        "operator_confidence_assessment",
        "reviewer",
        "reviewed_at",
    ]
    for field in operator_fields:
        if field in wb_rows[0]:
            for i, row in enumerate(wb_rows):
                val = row.get(field, "")
                check(f"v115F row {i + 1}: '{field}' still empty",
                      (val or "").strip() == "",
                      f"got non-empty: '{val}'")

    # ==================================================================
    # 18. Real Label NOT Upgraded
    # ==================================================================
    print("\n[18] Real Label NOT Upgraded")
    check("real_label_upgrade_performed = false",
          gate_result.get("real_label_upgrade_performed") is False)

    # ==================================================================
    # 19. No Real Send Candidate Generated
    # ==================================================================
    print("\n[19] No Real Send Candidate Generated")
    check("real_send_candidate_generated = false",
          gate_result.get("real_send_candidate_generated") is False)

    # ==================================================================
    # 20. All Send Guards = false
    # ==================================================================
    print("\n[20] All Send Guards = false")
    check("send_ready = false", gate_result.get("send_ready") is False)
    check("tg_test_group_ready = false", gate_result.get("tg_test_group_ready") is False)

    # ==================================================================
    # 21. No TG Sent
    # ==================================================================
    print("\n[21] No TG Sent")
    check("tg_sent = false", gate_result.get("tg_sent") is False)

    # ==================================================================
    # 22. No Production State Write
    # ==================================================================
    print("\n[22] No Production State Write")
    check("prod_state_write = false", gate_result.get("prod_state_write") is False)

    # ==================================================================
    # 23. No External API Called
    # ==================================================================
    print("\n[23] No External API Called")
    check("external_api_called = false", gate_result.get("external_api_called") is False)

    # ==================================================================
    # 24. No AI/Model Called
    # ==================================================================
    print("\n[24] No AI/Model Called")
    check("ai_model_called = false", gate_result.get("ai_model_called") is False)

    # ==================================================================
    # 25. No Credentials Read
    # ==================================================================
    print("\n[25] No Credentials Read")
    check("credentials_read = false", gate_result.get("credentials_read") is False)

    # ==================================================================
    # 26. No Daemon/Watcher/Cron/Loop
    # ==================================================================
    print("\n[26] No Daemon/Watcher/Cron/Loop")
    check("daemon_started = false", gate_result.get("daemon_started") is False)
    check("watcher_started = false", gate_result.get("watcher_started") is False)

    # ==================================================================
    # 27. No Files Deleted
    # ==================================================================
    print("\n[27] No Files Deleted")
    check("files_deleted = false", gate_result.get("files_deleted") is False)

    # ==================================================================
    # 28. No Sensitive Data in Outputs
    # ==================================================================
    print("\n[28] No Sensitive Data in Outputs")
    all_output_text = (
        json.dumps(gate_result) +
        json.dumps(real_records) +
        json.dumps(real_decisions) +
        json.dumps(fixture_records) +
        json.dumps(fixture_decisions) +
        md_text +
        handoff_text
    )
    sensitive_patterns = [
        "API_KEY", "api_key", "token", "password", "secret",
        ".env", "OPENAI", "OPENROUTER", "cookie",
    ]
    for pat in sensitive_patterns:
        check(f"No '{pat}' in any v115L output",
              pat.lower() not in all_output_text.lower(),
              f"found '{pat}'")

    # credentials_read is a valid field name — ensure no other credential leak
    cred_count = all_output_text.lower().count("credential")
    cred_read_count = all_output_text.lower().count("credentials_read")
    check("'credential' appears only as 'credentials_read' safety flag",
          cred_count == cred_read_count,
          f"unexpected 'credential' occurrences: {cred_count} total, {cred_read_count} as credentials_read")

    # No API call patterns
    api_patterns = ["http://api.", "https://api.", "fetch(", "curl ",
                    "requests.get", "requests.post", "urllib"]
    for pat in api_patterns:
        check(f"No '{pat}' in any v115L output", pat not in all_output_text.lower(),
              f"found '{pat}'")

    # ==================================================================
    # 29. Gate Result — All Required Fields
    # ==================================================================
    print("\n[29] Gate Result — All Required Fields")
    required_fields = [
        "stage", "registry_loaded", "scoring_policy_loaded",
        "real_workbook_rows", "real_scoring_records", "real_scoring_decisions",
        "real_scoring_passed_count", "real_scoring_blocked_count",
        "fixture_rows", "fixture_scoring_records", "fixture_scoring_decisions",
        "fixture_scoring_passed_count", "fixture_high_confidence_allowed_count",
        "fixture_label_upgraded_count",
        "rejected_source_negative_check_passed",
        "rejected_source_can_grant_high_confidence",
        "real_workbook_modified", "real_label_upgrade_performed",
        "real_send_candidate_generated",
        "send_ready", "tg_test_group_ready", "local_review_ready",
        "external_api_called", "ai_model_called", "credentials_read",
        "tg_sent", "prod_state_write", "daemon_started",
        "watcher_started", "files_deleted",
        "hc_requirement_ids_referenced",
    ]
    for field in required_fields:
        check(f"Gate result has field '{field}'", field in gate_result,
              f"missing field: {field}")

    # ==================================================================
    # 30. Gate Result — Stage Correct
    # ==================================================================
    print("\n[30] Gate Result — Stage Correct")
    check("stage = v115l_whale_label_evidence_scoring_gate_local_only",
          gate_result.get("stage") == "v115l_whale_label_evidence_scoring_gate_local_only",
          f"got: {gate_result.get('stage')}")

    # ==================================================================
    # 31. local_review_ready = true
    # ==================================================================
    print("\n[31] local_review_ready = true")
    check("local_review_ready = true", gate_result.get("local_review_ready") is True)

    # ==================================================================
    # 32. Negative Assertions
    # ==================================================================
    print("\n[32] Negative Assertions — Nothing Claims Success It Shouldn't")
    check("NOT claiming send_ready=true", gate_result.get("send_ready") is not True)
    check("NOT claiming tg_test_group_ready=true", gate_result.get("tg_test_group_ready") is not True)
    check("NOT claiming tg_sent=true", gate_result.get("tg_sent") is not True)
    check("NOT claiming prod_state_write=true", gate_result.get("prod_state_write") is not True)
    check("NOT claiming real_workbook_modified=true", gate_result.get("real_workbook_modified") is not True)
    check("NOT claiming real_label_upgrade_performed=true", gate_result.get("real_label_upgrade_performed") is not True)
    check("NOT claiming real_send_candidate_generated=true", gate_result.get("real_send_candidate_generated") is not True)
    check("NOT claiming external_api_called=true", gate_result.get("external_api_called") is not True)
    check("NOT claiming ai_model_called=true", gate_result.get("ai_model_called") is not True)
    check("NOT claiming credentials_read=true", gate_result.get("credentials_read") is not True)
    check("NOT claiming daemon_started=true", gate_result.get("daemon_started") is not True)
    check("NOT claiming watcher_started=true", gate_result.get("watcher_started") is not True)
    check("NOT claiming files_deleted=true", gate_result.get("files_deleted") is not True)
    check("NOT claiming fixture_label_upgraded_count > 0",
          gate_result.get("fixture_label_upgraded_count", 0) == 0)

    # ==================================================================
    # 33. Markdown Content Check
    # ==================================================================
    print("\n[33] Markdown Report Content")
    check("Markdown mentions v115L", "v115L" in md_text or "v115l" in md_text.lower())
    check("Markdown mentions evidence scoring", "scoring" in md_text.lower())
    check("Markdown mentions registry", "registry" in md_text.lower())
    check("Markdown contains safety invariants", "external_api" in md_text.lower())
    check("Markdown mentions Explicit NOT", "NOT" in md_text)
    check("Markdown mentions rejected source negative check", "Rejected" in md_text)

    # ==================================================================
    # 34. Handoff Content Check
    # ==================================================================
    print("\n[34] Handoff Content")
    check("Handoff mentions v115L", "v115L" in handoff_text or "v115l" in handoff_text.lower())
    check("Handoff mentions scoring", "scoring" in handoff_text.lower())
    check("Handoff mentions safety invariants", "safety" in handoff_text.lower())
    check("Handoff mentions v115K", "v115K" in handoff_text)

    # ==================================================================
    # 35. Fixture CSV Not Modified
    # ==================================================================
    print("\n[35] Fixture CSV Not Modified")
    fixture_rows_check = load_csv_dict(V115I_FIXTURE)
    check(f"Fixture CSV still has 1 row (got {len(fixture_rows_check)})", len(fixture_rows_check) == 1)
    check("Fixture row still has fixture_only=true",
          parse_bool_csv(fixture_rows_check[0].get("fixture_only", "false")) is True)

    # ==================================================================
    # 36. v115K Config Files Not Modified
    # ==================================================================
    print("\n[36] v115K Config Files Not Modified")
    registry_check = load_json(V115K_REGISTRY)
    check("v115K registry version is v115K", registry_check.get("version") == "v115K")
    check("v115K registry has 4 categories", registry_check.get("registry_categories") == 4)

    scoring_check = load_json(V115K_SCORING_POLICY)
    check("v115K scoring policy version is v115K", scoring_check.get("version") == "v115K")
    check("v115K scoring policy has 9 HC requirements",
          scoring_check.get("minimum_for_high_confidence", {}).get("total_requirements") == 9)

    # ==================================================================
    # 37. Count cross-check
    # ==================================================================
    print("\n[37] Count Cross-Checks")
    count_real_passed = sum(1 for dec in real_decisions if dec.get("decision") == "scoring_passed")
    count_real_blocked = sum(1 for dec in real_decisions if dec.get("decision") == "scoring_blocked")
    check(f"Real decisions: passed={count_real_passed}, blocked={count_real_blocked} matches gate result",
          count_real_passed == gate_result.get("real_scoring_passed_count", -1)
          and count_real_blocked == gate_result.get("real_scoring_blocked_count", -1))

    count_fixture_passed = sum(1 for dec in fixture_decisions if dec.get("decision", "").startswith("scoring_passed"))
    check(f"Fixture decisions: passed={count_fixture_passed} matches gate result",
          count_fixture_passed == gate_result.get("fixture_scoring_passed_count", -1))

    count_fixture_hc = sum(1 for dec in fixture_decisions if dec.get("high_confidence_allowed") is True)
    check(f"Fixture high_confidence_allowed={count_fixture_hc} matches gate result",
          count_fixture_hc == gate_result.get("fixture_high_confidence_allowed_count", -1))

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
