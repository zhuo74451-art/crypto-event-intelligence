#!/usr/bin/env python3
"""
Test suite for v115J Whale Manual Audit Gate Rule Parity Audit — Local Only
=============================================================================
Validates the v115J parity audit runner produced correct outputs:
  - parity_matrix.json exists with required categories
  - findings JSONL non-empty
  - parity_passed=true
  - rule_drift_detected=false
  - fixture_bypass_detected=false
  - 8 required PASS findings all present
  - v115I fixture pass conditions include all 10 manual evidence/confirmation fields
  - v115I fixture does NOT modify real v115F workbook
  - v115I fixture does NOT perform real label upgrade
  - v115I fixture does NOT generate real send candidate
  - All send guards are false
  - No TG send, no prod state write
  - No external API, AI/model, credentials
  - No daemon/watcher/cron/loop
  - No file deletion
  - No modification of v114A-v115I old results
"""

import json
import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RESULTS_DIR = os.path.join(BASE_DIR, "results")
CONFIG_DIR = os.path.join(BASE_DIR, "config")
RUNS_DIR = os.path.join(BASE_DIR, "runs", "market_radar")
FIXTURES_DIR = os.path.join(BASE_DIR, "fixtures", "market_radar")

# v115J outputs (must exist)
V115J_PARITY_MATRIX = os.path.join(
    RESULTS_DIR, "market_radar_v115j_whale_manual_audit_gate_rule_parity_matrix.json"
)
V115J_PARITY_FINDINGS = os.path.join(
    RESULTS_DIR, "market_radar_v115j_whale_manual_audit_gate_rule_parity_findings.jsonl"
)
V115J_AUDIT_RESULT = os.path.join(
    RESULTS_DIR, "market_radar_v115j_whale_manual_audit_gate_rule_parity_audit_result.json"
)
V115J_MD = os.path.join(
    RUNS_DIR, "v115j_whale_manual_audit_gate_rule_parity_audit_local_only.md"
)
V115J_HANDOFF = os.path.join(
    RUNS_DIR, "v115j_whale_manual_audit_gate_rule_parity_audit_local_only_handoff.md"
)

# v115G sources (must still exist, unmodified)
V115G_RESULT = os.path.join(
    RESULTS_DIR, "market_radar_v115g_whale_manual_audit_workbook_intake_gate_result.json"
)
V115G_INTAKE_RECORDS = os.path.join(
    RESULTS_DIR, "market_radar_v115g_whale_manual_audit_intake_records.jsonl"
)
V115G_INTAKE_DECISIONS = os.path.join(
    RESULTS_DIR, "market_radar_v115g_whale_manual_audit_intake_decisions.jsonl"
)

# v115H sources (must still exist, unmodified)
V115H_RESULT = os.path.join(
    RESULTS_DIR, "market_radar_v115h_whale_label_upgrade_adjudication_gate_result.json"
)
V115H_ADJ_RECORDS = os.path.join(
    RESULTS_DIR, "market_radar_v115h_whale_label_upgrade_adjudication_records.jsonl"
)
V115H_ADJ_DECISIONS = os.path.join(
    RESULTS_DIR, "market_radar_v115h_whale_label_upgrade_adjudication_decisions.jsonl"
)

# v115I sources (must still exist, unmodified)
V115I_RESULT = os.path.join(
    RESULTS_DIR, "market_radar_v115i_whale_manual_audit_positive_path_fixture_gate_result.json"
)
V115I_INTAKE_RECORDS = os.path.join(
    RESULTS_DIR, "market_radar_v115i_whale_manual_audit_positive_path_intake_records.jsonl"
)
V115I_INTAKE_DECISIONS = os.path.join(
    RESULTS_DIR, "market_radar_v115i_whale_manual_audit_positive_path_intake_decisions.jsonl"
)
V115I_ADJ_RECORDS = os.path.join(
    RESULTS_DIR, "market_radar_v115i_whale_manual_audit_positive_path_adjudication_records.jsonl"
)
V115I_ADJ_DECISIONS = os.path.join(
    RESULTS_DIR, "market_radar_v115i_whale_manual_audit_positive_path_adjudication_decisions.jsonl"
)

# v115F workbook (must still exist, unmodified)
V115F_WORKBOOK_CSV = os.path.join(
    RUNS_DIR, "v115f_whale_address_audit_operator_workbook.csv"
)

# Old results that must still exist (v115A-v115I range)
OLD_RESULTS_TO_CHECK = [
    # v115E
    os.path.join(RESULTS_DIR, "market_radar_v115e_whale_label_upgrade_decisions.jsonl"),
    os.path.join(RESULTS_DIR, "market_radar_v115e_whale_address_audit_evidence_requests.jsonl"),
    os.path.join(RESULTS_DIR, "market_radar_v115e_whale_address_manual_audit_forms.jsonl"),
    os.path.join(RESULTS_DIR, "market_radar_v115e_whale_address_audit_evidence_pack_result.json"),
    # v115D
    os.path.join(RESULTS_DIR, "market_radar_v115d_whale_one_shot_send_preview_gate_decisions.jsonl"),
    os.path.join(RESULTS_DIR, "market_radar_v115d_whale_one_shot_send_preview_gate_result.json"),
    # v115F
    os.path.join(RESULTS_DIR, "market_radar_v115f_whale_address_audit_operator_workbook_manifest.json"),
    os.path.join(RESULTS_DIR, "market_radar_v115f_whale_address_audit_operator_workbook_gate_result.json"),
]

# v115B routing policy
V115B_ROUTING = os.path.join(
    CONFIG_DIR, "market_radar_v115b_whale_label_confidence_routing_policy.json"
)

# The 8 required PASS finding categories
REQUIRED_PASS_CATEGORIES = [
    "INTAKE_REQUIRED_FIELDS_PARITY",
    "ADJUDICATION_REQUIRED_FIELDS_PARITY",
    "FIXTURE_DOES_NOT_BYPASS_MANUAL_EVIDENCE",
    "FIXTURE_MEDIUM_ONLY_POSITIVE_PATH",
    "REAL_WORKBOOK_NOT_MODIFIED",
    "NO_REAL_LABEL_UPGRADE",
    "NO_SEND_CANDIDATE",
    "SAFETY_INVARIANTS",
]

# The 10 required manual evidence/confirmation fields
TEN_REQUIRED_FIELDS = [
    "trusted_source_label_value",
    "trusted_source_url_or_note",
    "second_source_label_value",
    "second_source_url_or_note",
    "activity_pattern_note",
    "operator_confirmed_label",
    "operator_confidence_assessment",
    "reviewer",
    "reviewed_at",
    "ready_for_upgrade",
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
    print("v115J Test Suite — Gate Rule Parity Audit")
    print("=" * 70)

    # ==================================================================
    # 1. File Existence — v115J Outputs
    # ==================================================================
    print("\n[1] File Existence — v115J Outputs")
    check("parity matrix .json exists", file_exists(V115J_PARITY_MATRIX))
    check("parity findings .jsonl exists", file_exists(V115J_PARITY_FINDINGS))
    check("audit result .json exists", file_exists(V115J_AUDIT_RESULT))
    check("markdown report exists", file_exists(V115J_MD))
    check("handoff markdown exists", file_exists(V115J_HANDOFF))

    # ==================================================================
    # 2. File Existence — Input Sources (v115G, v115H, v115I) Still Intact
    # ==================================================================
    print("\n[2] File Existence — v115G/v115H/v115I Sources Still Intact")
    check("v115G gate result exists", file_exists(V115G_RESULT))
    check("v115G intake records exist", file_exists(V115G_INTAKE_RECORDS))
    check("v115G intake decisions exist", file_exists(V115G_INTAKE_DECISIONS))
    check("v115H gate result exists", file_exists(V115H_RESULT))
    check("v115H adj records exist", file_exists(V115H_ADJ_RECORDS))
    check("v115H adj decisions exist", file_exists(V115H_ADJ_DECISIONS))
    check("v115I gate result exists", file_exists(V115I_RESULT))
    check("v115I intake records exist", file_exists(V115I_INTAKE_RECORDS))
    check("v115I intake decisions exist", file_exists(V115I_INTAKE_DECISIONS))
    check("v115I adj records exist", file_exists(V115I_ADJ_RECORDS))
    check("v115I adj decisions exist", file_exists(V115I_ADJ_DECISIONS))
    check("v115F workbook exists", file_exists(V115F_WORKBOOK_CSV))
    check("v115B routing policy exists", file_exists(V115B_ROUTING))

    # ==================================================================
    # 3. File Existence — Old Results NOT Modified
    # ==================================================================
    print("\n[3] Old Results v114A-v115I Still Intact")
    for path in OLD_RESULTS_TO_CHECK:
        fname = os.path.basename(path)
        check(f"{fname} exists", file_exists(path))

    # ==================================================================
    # 4. Data Loading
    # ==================================================================
    print("\n[4] Data Loading")
    parity_matrix = load_json(V115J_PARITY_MATRIX)
    check("Parity matrix JSON parsed", isinstance(parity_matrix, dict))

    findings = load_jsonl(V115J_PARITY_FINDINGS)
    check(f"Findings loaded ({len(findings)} findings)", len(findings) > 0)

    audit_result = load_json(V115J_AUDIT_RESULT)
    check("Audit result JSON parsed", isinstance(audit_result, dict))

    with open(V115J_MD, "r", encoding="utf-8") as f:
        md_text = f.read()
    check("Markdown report loaded", len(md_text) > 0)

    with open(V115J_HANDOFF, "r", encoding="utf-8") as f:
        handoff_text = f.read()
    check("Handoff markdown loaded", len(handoff_text) > 0)

    # ==================================================================
    # 5. Parity Matrix Has Required Categories
    # ==================================================================
    print("\n[5] Parity Matrix — Required Categories")
    required_categories = [
        "required_manual_fields",
        "required_evidence_fields",
        "required_boolean_flags",
        "intake_block_reasons",
        "adjudication_block_reasons",
        "fixture_pass_conditions",
        "send_guard_fields",
        "safety_invariants",
    ]
    for cat in required_categories:
        check(f"Parity matrix has '{cat}'", cat in parity_matrix)

    # ==================================================================
    # 6. Findings JSONL Non-Empty
    # ==================================================================
    print("\n[6] Findings JSONL Non-Empty")
    check(f"Findings JSONL has {len(findings)} entries (> 0)", len(findings) > 0)

    # ==================================================================
    # 7. Findings Have Required Fields
    # ==================================================================
    print("\n[7] Findings — Required Fields Per Entry")
    required_finding_fields = ["finding_id", "category", "severity", "status", "description", "evidence", "recommended_action"]
    for i, f in enumerate(findings):
        for field in required_finding_fields:
            check(f"Finding {i+1} '{f.get('finding_id', '?')}': field '{field}' present",
                  field in f, f"missing field: {field}")

    # ==================================================================
    # 8. parity_passed = true
    # ==================================================================
    print("\n[8] Audit Result — parity_passed = true")
    check("parity_passed = true", audit_result.get("parity_passed") is True,
          f"got: {audit_result.get('parity_passed')}")

    # ==================================================================
    # 9. rule_drift_detected = false
    # ==================================================================
    print("\n[9] Audit Result — rule_drift_detected = false")
    check("rule_drift_detected = false", audit_result.get("rule_drift_detected") is False,
          f"got: {audit_result.get('rule_drift_detected')}")

    # ==================================================================
    # 10. fixture_bypass_detected = false
    # ==================================================================
    print("\n[10] Audit Result — fixture_bypass_detected = false")
    check("fixture_bypass_detected = false", audit_result.get("fixture_bypass_detected") is False,
          f"got: {audit_result.get('fixture_bypass_detected')}")

    # ==================================================================
    # 11. 8 Required PASS Findings All Present
    # ==================================================================
    print("\n[11] 8 Required PASS Findings")
    pass_findings = [f for f in findings if f["status"] == "PASS"]
    found_pass_categories = set(f["category"] for f in pass_findings)
    for cat in REQUIRED_PASS_CATEGORIES:
        check(f"Required PASS finding '{cat}' present", cat in found_pass_categories,
              f"missing required PASS category")

    # ==================================================================
    # 12. v115I Fixture Pass Conditions Include All 10 Manual Fields
    # ==================================================================
    print("\n[12] Fixture Pass Conditions — 10 Manual Evidence/Confirmation Fields")
    # Check that v115I fixture intake requires all 10 fields
    v115i_intake_records = load_jsonl(V115I_INTAKE_RECORDS)
    for i, rec in enumerate(v115i_intake_records):
        for field in TEN_REQUIRED_FIELDS:
            if field == "ready_for_upgrade":
                check(f"v115I intake record {i+1}: ready_for_upgrade = true",
                      rec.get("ready_for_upgrade") is True,
                      f"got: {rec.get('ready_for_upgrade')}")
            else:
                val = rec.get(field, "")
                check(f"v115I intake record {i+1}: '{field}' is non-empty",
                      val is not None and str(val).strip() != "",
                      f"got: empty")

    # ==================================================================
    # 13. v115I Fixture Does NOT Modify Real v115F Workbook
    # ==================================================================
    print("\n[13] v115I Fixture Does NOT Modify Real v115F Workbook")
    v115i_result = load_json(V115I_RESULT)
    v115g_result = load_json(V115G_RESULT)
    v115h_result = load_json(V115H_RESULT)

    check("v115I real_workbook_modified = false",
          v115i_result.get("real_workbook_modified") is False)
    check("v115I real_v115g_intake_ready_count = 0",
          v115i_result.get("real_v115g_intake_ready_count") == 0)
    check("v115G intake_ready_count still 0",
          v115g_result.get("intake_ready_count") == 0)
    check("v115H label_upgrade_allowed_count still 0",
          v115h_result.get("label_upgrade_allowed_count") == 0)

    # ==================================================================
    # 14. v115I Fixture Does NOT Perform Real Label Upgrade
    # ==================================================================
    print("\n[14] v115I Fixture Does NOT Perform Real Label Upgrade")
    check("v115I real_label_upgrade_performed = false",
          v115i_result.get("real_label_upgrade_performed") is False)
    check("v115I fixture_label_upgraded_count = 0",
          v115i_result.get("fixture_label_upgraded_count") == 0)
    check("v115H label_upgraded_count still 0",
          v115h_result.get("label_upgraded_count") == 0)

    # Check fixture adjudication decision: to_confidence equals from_confidence
    v115i_adj_decisions = load_jsonl(V115I_ADJ_DECISIONS)
    for i, dec in enumerate(v115i_adj_decisions):
        from_c = dec.get("from_confidence", "")
        to_c = dec.get("to_confidence", "")
        check(f"v115I adj decision {i+1}: to_confidence ({to_c}) = from_confidence ({from_c})",
              to_c == from_c, f"to={to_c} != from={from_c}")

    # ==================================================================
    # 15. v115I Fixture Does NOT Generate Real Send Candidate
    # ==================================================================
    print("\n[15] No Real Send Candidate Generated")
    check("v115I real_send_candidate_generated = false",
          v115i_result.get("real_send_candidate_generated") is False)
    check("v115G real_send_candidate_generated = false",
          v115g_result.get("real_send_candidate_generated") is False)
    check("v115H real_send_candidate_generated = false",
          v115h_result.get("real_send_candidate_generated") is False)

    # ==================================================================
    # 16. All Send Guards = false
    # ==================================================================
    print("\n[16] All Send Guards = false")
    # Check v115J audit result
    check("v115J send_ready = false", audit_result.get("send_ready") is False)
    check("v115J tg_test_group_ready = false", audit_result.get("tg_test_group_ready") is False)
    # Check v115I decisions
    for i, dec in enumerate(v115i_adj_decisions):
        check(f"v115I adj decision {i+1}: send_allowed = false", dec.get("send_allowed") is False)
        check(f"v115I adj decision {i+1}: tg_test_group_allowed = false", dec.get("tg_test_group_allowed") is False)
        check(f"v115I adj decision {i+1}: public_send_allowed = false", dec.get("public_send_allowed") is False)

    v115i_intake_decisions = load_jsonl(V115I_INTAKE_DECISIONS)
    for i, dec in enumerate(v115i_intake_decisions):
        check(f"v115I intake decision {i+1}: send_allowed = false", dec.get("send_allowed") is False)
        check(f"v115I intake decision {i+1}: tg_test_group_allowed = false", dec.get("tg_test_group_allowed") is False)
        check(f"v115I intake decision {i+1}: public_send_allowed = false", dec.get("public_send_allowed") is False)

    # ==================================================================
    # 17. No TG Sent
    # ==================================================================
    print("\n[17] No TG Sent")
    check("v115J tg_sent = false", audit_result.get("tg_sent") is False)
    check("v115I tg_sent = false", v115i_result.get("tg_sent") is False)
    check("v115G tg_sent = false", v115g_result.get("tg_sent") is False)
    check("v115H tg_sent = false", v115h_result.get("tg_sent") is False)

    # ==================================================================
    # 18. No Production State Write
    # ==================================================================
    print("\n[18] No Production State Write")
    check("v115J prod_state_write = false", audit_result.get("prod_state_write") is False)
    check("v115I prod_state_write = false", v115i_result.get("prod_state_write") is False)
    check("v115G prod_state_write = false", v115g_result.get("prod_state_write") is False)
    check("v115H prod_state_write = false", v115h_result.get("prod_state_write") is False)

    # ==================================================================
    # 19. No External API Called
    # ==================================================================
    print("\n[19] No External API Called")
    check("v115J external_api_called = false", audit_result.get("external_api_called") is False)
    check("v115I external_api_called = false", v115i_result.get("external_api_called") is False)
    check("v115G external_api_called = false", v115g_result.get("external_api_called") is False)
    check("v115H external_api_called = false", v115h_result.get("external_api_called") is False)

    # Check all v115J outputs for API patterns
    all_j_output = json.dumps(audit_result) + json.dumps(parity_matrix) + json.dumps(findings) + md_text + handoff_text
    api_patterns = ["http://api.", "https://api.", "fetch(", "curl ", "requests.get", "requests.post", "urllib"]
    for pat in api_patterns:
        check(f"No '{pat}' in any v115J output", pat not in all_j_output.lower(),
              f"found '{pat}'")

    # ==================================================================
    # 20. No AI/Model Called
    # ==================================================================
    print("\n[20] No AI/Model Called")
    check("v115J ai_model_called = false", audit_result.get("ai_model_called") is False)
    check("v115I ai_model_called = false", v115i_result.get("ai_model_called") is False)

    # ==================================================================
    # 21. No Credentials Read
    # ==================================================================
    print("\n[21] No Credentials Read")
    check("v115J credentials_read = false", audit_result.get("credentials_read") is False)
    check("v115I credentials_read = false", v115i_result.get("credentials_read") is False)

    sensitive_patterns = ["API_KEY", "api_key", "token", "password", "secret",
                          ".env", "OPENAI", "OPENROUTER"]
    for pat in sensitive_patterns:
        check(f"No '{pat}' in any v115J output", pat.lower() not in all_j_output.lower(),
              f"found '{pat}'")

    # ==================================================================
    # 22. No Daemon/Watcher/Cron/Loop Started
    # ==================================================================
    print("\n[22] No Daemon/Watcher/Cron/Loop Started")
    check("v115J daemon_started = false", audit_result.get("daemon_started") is False)
    check("v115J watcher_started = false", audit_result.get("watcher_started") is False)
    check("v115I daemon_started = false", v115i_result.get("daemon_started") is False)
    check("v115I watcher_started = false", v115i_result.get("watcher_started") is False)

    # ==================================================================
    # 23. No Files Deleted
    # ==================================================================
    print("\n[23] No Files Deleted")
    check("v115J files_deleted = false", audit_result.get("files_deleted") is False)
    check("v115I files_deleted = false", v115i_result.get("files_deleted") is False)
    check("v115G files_deleted = false", v115g_result.get("files_deleted") is False)
    check("v115H files_deleted = false", v115h_result.get("files_deleted") is False)

    # ==================================================================
    # 24. No Modification of v114A-v115I Old Results
    # ==================================================================
    print("\n[24] v114A-v115I Old Results NOT Modified — Content Verification")
    # Cross-check v115G still blocked
    v115g_intake_records = load_jsonl(V115G_INTAKE_RECORDS)
    check(f"v115G intake records still 4 (got {len(v115g_intake_records)})", len(v115g_intake_records) == 4)
    for i, rec in enumerate(v115g_intake_records):
        check(f"v115G record {i+1}: intake_ready still false", rec.get("intake_ready") is False)

    # Cross-check v115H still blocked
    v115h_adj_records = load_jsonl(V115H_ADJ_RECORDS)
    check(f"v115H adj records still 4 (got {len(v115h_adj_records)})", len(v115h_adj_records) == 4)
    for i, rec in enumerate(v115h_adj_records):
        check(f"v115H record {i+1}: adjudication_ready still false", rec.get("adjudication_ready") is False)

    # ==================================================================
    # 25. Audit Result — All Required Fields
    # ==================================================================
    print("\n[25] Audit Result — All Required Fields")
    required_result_fields = [
        "stage", "parity_passed", "findings_total", "pass_findings",
        "warning_findings", "fail_findings", "rule_drift_detected",
        "fixture_bypass_detected", "real_workbook_modified",
        "real_label_upgrade_performed", "real_send_candidate_generated",
        "send_ready", "tg_test_group_ready", "local_review_ready",
        "external_api_called", "ai_model_called", "credentials_read",
        "tg_sent", "prod_state_write", "daemon_started", "watcher_started",
        "files_deleted",
    ]
    for field in required_result_fields:
        check(f"Audit result has field '{field}'", field in audit_result,
              f"missing field: {field}")

    # ==================================================================
    # 26. Audit Result Stage Correct
    # ==================================================================
    print("\n[26] Audit Result — Stage Correct")
    check("stage = v115j_whale_manual_audit_gate_rule_parity_audit_local_only",
          audit_result.get("stage") == "v115j_whale_manual_audit_gate_rule_parity_audit_local_only",
          f"got: {audit_result.get('stage')}")

    # ==================================================================
    # 27. Findings Count Consistency
    # ==================================================================
    print("\n[27] Findings Count Consistency")
    pass_count = audit_result.get("pass_findings", 0)
    warn_count = audit_result.get("warning_findings", 0)
    fail_count = audit_result.get("fail_findings", 0)
    total = audit_result.get("findings_total", 0)
    check(f"findings_total ({total}) = pass ({pass_count}) + warning ({warn_count}) + fail ({fail_count})",
          total == pass_count + warn_count + fail_count,
          f"sum={pass_count + warn_count + fail_count} != total={total}")

    # ==================================================================
    # 28. local_review_ready = true
    # ==================================================================
    print("\n[28] local_review_ready = true")
    check("v115J local_review_ready = true", audit_result.get("local_review_ready") is True)

    # ==================================================================
    # 29. Markdown Report Content
    # ==================================================================
    print("\n[29] Markdown Report Content")
    check("Markdown mentions v115J", "v115J" in md_text)
    check("Markdown mentions parity", "parity" in md_text.lower())
    check("Markdown mentions audit", "audit" in md_text.lower())
    check("Markdown contains findings entries",
          "Findings" in md_text or "findings" in md_text.lower())

    # ==================================================================
    # 30. Handoff Content
    # ==================================================================
    print("\n[30] Handoff Markdown Content")
    check("Handoff mentions v115J", "v115J" in handoff_text)
    check("Handoff mentions parity", "parity" in handoff_text.lower())
    check("Handoff mentions safety invariants",
          "safety" in handoff_text.lower() or "invariant" in handoff_text.lower())
    check("Handoff mentions findings",
          "finding" in handoff_text.lower())

    # ==================================================================
    # 31. Negative Assertions — Nothing Claims Success It Shouldn't
    # ==================================================================
    print("\n[31] Negative Assertions")
    check("NOT claiming send_ready=true", audit_result.get("send_ready") is not True)
    check("NOT claiming tg_test_group_ready=true",
          audit_result.get("tg_test_group_ready") is not True)
    check("NOT claiming tg_sent=true", audit_result.get("tg_sent") is not True)
    check("NOT claiming prod_state_write=true",
          audit_result.get("prod_state_write") is not True)
    check("NOT claiming real_workbook_modified=true",
          audit_result.get("real_workbook_modified") is not True)
    check("NOT claiming real_label_upgrade_performed=true",
          audit_result.get("real_label_upgrade_performed") is not True)
    check("NOT claiming real_send_candidate_generated=true",
          audit_result.get("real_send_candidate_generated") is not True)
    check("NOT claiming rule_drift_detected=true",
          audit_result.get("rule_drift_detected") is not True)
    check("NOT claiming fixture_bypass_detected=true",
          audit_result.get("fixture_bypass_detected") is not True)
    check("NOT claiming external_api_called=true",
          audit_result.get("external_api_called") is not True)
    check("NOT claiming ai_model_called=true",
          audit_result.get("ai_model_called") is not True)
    check("NOT claiming credentials_read=true",
          audit_result.get("credentials_read") is not True)
    check("NOT claiming daemon_started=true",
          audit_result.get("daemon_started") is not True)
    check("NOT claiming watcher_started=true",
          audit_result.get("watcher_started") is not True)
    check("NOT claiming files_deleted=true",
          audit_result.get("files_deleted") is not True)

    # ==================================================================
    # 32. v115F Workbook Content Unchanged
    # ==================================================================
    print("\n[32] v115F Workbook Content Unchanged")
    import csv
    wb_rows = []
    with open(V115F_WORKBOOK_CSV, "r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            wb_rows.append(row)
    check(f"v115F workbook still has 4 rows (got {len(wb_rows)})", len(wb_rows) == 4)
    # Check key operator fields still empty
    for i, row in enumerate(wb_rows):
        check(f"v115F row {i+1}: trusted_source_label_value still empty",
              (row.get("trusted_source_label_value") or "").strip() == "")

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
