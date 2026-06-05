#!/usr/bin/env python3
"""
Test suite for v115M Whale Manual Audit End-to-End Upgrade Workflow Gate — Local Only
=====================================================================================
Validates that the v115M runner produced correct outputs:

Real path (v115F workbook, empty operator fields):
  - real_workbook_rows = 4
  - real_workflow_records = 4
  - real_workflow_decisions = 4
  - real_workflow_ready_count = 0
  - real_workflow_blocked_count = 4
  - real_upgrade_preview_allowed_count = 0

Fixture path (v115I, all evidence complete):
  - fixture_rows = 1
  - fixture_workflow_records = 1
  - fixture_workflow_decisions = 1
  - fixture_workflow_ready_count = 1
  - fixture_upgrade_preview_allowed_count = 1
  - fixture_label_upgraded_count = 0

Workflow:
  - workflow_order correct
  - workflow_order_enforced = true

Safety:
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
  - No modification of v114A-v115L old results
  - Fixture path is fixture-only, no real label contamination
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
# v115M outputs (must exist)
# ---------------------------------------------------------------------------
V115M_REAL_RECORDS = os.path.join(
    RESULTS_DIR, "market_radar_v115m_whale_real_workflow_records.jsonl"
)
V115M_REAL_DECISIONS = os.path.join(
    RESULTS_DIR, "market_radar_v115m_whale_real_workflow_decisions.jsonl"
)
V115M_FIXTURE_RECORDS = os.path.join(
    RESULTS_DIR, "market_radar_v115m_whale_fixture_workflow_records.jsonl"
)
V115M_FIXTURE_DECISIONS = os.path.join(
    RESULTS_DIR, "market_radar_v115m_whale_fixture_workflow_decisions.jsonl"
)
V115M_GATE_RESULT = os.path.join(
    RESULTS_DIR,
    "market_radar_v115m_whale_manual_audit_end_to_end_upgrade_workflow_gate_result.json",
)
V115M_MD = os.path.join(
    RUNS_DIR, "v115m_whale_manual_audit_end_to_end_upgrade_workflow_gate_local_only.md"
)
V115M_HANDOFF = os.path.join(
    RUNS_DIR,
    "v115m_whale_manual_audit_end_to_end_upgrade_workflow_gate_local_only_handoff.md",
)

# ---------------------------------------------------------------------------
# Input files (must still exist, unmodified)
# ---------------------------------------------------------------------------
V115F_WORKBOOK = os.path.join(
    RUNS_DIR, "v115f_whale_address_audit_operator_workbook.csv"
)
V115I_FIXTURE = os.path.join(
    FIXTURES_DIR, "v115i_whale_manual_audit_positive_path_fixture.csv"
)
V115K_SCORING_POLICY = os.path.join(
    CONFIG_DIR, "market_radar_v115k_whale_label_evidence_scoring_policy.json"
)
V115B_ROUTING_POLICY = os.path.join(
    CONFIG_DIR, "market_radar_v115b_whale_label_confidence_routing_policy.json"
)

# ---------------------------------------------------------------------------
# Old results to check still exist (v114A-v115L)
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
    # v115L
    os.path.join(RESULTS_DIR, "market_radar_v115l_whale_real_workbook_evidence_scoring_records.jsonl"),
    os.path.join(RESULTS_DIR, "market_radar_v115l_whale_real_workbook_evidence_scoring_decisions.jsonl"),
    os.path.join(RESULTS_DIR, "market_radar_v115l_whale_fixture_evidence_scoring_records.jsonl"),
    os.path.join(RESULTS_DIR, "market_radar_v115l_whale_fixture_evidence_scoring_decisions.jsonl"),
    os.path.join(RESULTS_DIR, "market_radar_v115l_whale_label_evidence_scoring_gate_result.json"),
]

WORKFLOW_ORDER = [
    "intake_gate",
    "evidence_scoring_gate",
    "adjudication_gate",
    "upgrade_preview_decision",
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
    print("v115M Test Suite — End-to-End Upgrade Workflow Gate")
    print("=" * 70)

    # ==================================================================
    # 1. File Existence — v115M Outputs
    # ==================================================================
    print("\n[1] File Existence — v115M Outputs")
    check("Real workflow records .jsonl exists", file_exists(V115M_REAL_RECORDS))
    check("Real workflow decisions .jsonl exists", file_exists(V115M_REAL_DECISIONS))
    check("Fixture workflow records .jsonl exists", file_exists(V115M_FIXTURE_RECORDS))
    check("Fixture workflow decisions .jsonl exists", file_exists(V115M_FIXTURE_DECISIONS))
    check("Gate result .json exists", file_exists(V115M_GATE_RESULT))
    check("Markdown report exists", file_exists(V115M_MD))
    check("Handoff markdown exists", file_exists(V115M_HANDOFF))

    # ==================================================================
    # 2. File Existence — Input Sources Still Intact
    # ==================================================================
    print("\n[2] File Existence — Input Sources Still Intact")
    check("v115F workbook exists", file_exists(V115F_WORKBOOK))
    check("v115I fixture CSV exists", file_exists(V115I_FIXTURE))
    check("v115K scoring policy config exists", file_exists(V115K_SCORING_POLICY))
    check("v115B routing policy config exists", file_exists(V115B_ROUTING_POLICY))

    # ==================================================================
    # 3. Old Results Still Intact (v114A-v115L)
    # ==================================================================
    print("\n[3] Old Results v114A-v115L Still Intact")
    for path in OLD_RESULTS_TO_CHECK:
        fname = os.path.basename(path)
        check(f"{fname} exists", file_exists(path))

    # ==================================================================
    # 4. Data Loading
    # ==================================================================
    print("\n[4] Data Loading")
    real_records = load_jsonl(V115M_REAL_RECORDS)
    check(f"Real workflow records loaded ({len(real_records)} records)", len(real_records) > 0)

    real_decisions = load_jsonl(V115M_REAL_DECISIONS)
    check(f"Real workflow decisions loaded ({len(real_decisions)} decisions)", len(real_decisions) > 0)

    fixture_records = load_jsonl(V115M_FIXTURE_RECORDS)
    check(f"Fixture workflow records loaded ({len(fixture_records)} records)", len(fixture_records) > 0)

    fixture_decisions = load_jsonl(V115M_FIXTURE_DECISIONS)
    check(f"Fixture workflow decisions loaded ({len(fixture_decisions)} decisions)", len(fixture_decisions) > 0)

    gate_result = load_json(V115M_GATE_RESULT)
    check("Gate result JSON parsed", isinstance(gate_result, dict))

    with open(V115M_MD, "r", encoding="utf-8") as f:
        md_text = f.read()
    check("Markdown report loaded", len(md_text) > 0)

    with open(V115M_HANDOFF, "r", encoding="utf-8") as f:
        handoff_text = f.read()
    check("Handoff markdown loaded", len(handoff_text) > 0)

    # ==================================================================
    # 5. Workflow Order Correct
    # ==================================================================
    print("\n[5] Workflow Order Correct")
    wf_order = gate_result.get("workflow_order", [])
    check("workflow_order has 4 stages", len(wf_order) == 4,
          f"got: {len(wf_order)}")
    check("workflow_order = intake_gate first", wf_order[0] if len(wf_order) > 0 else None == "intake_gate",
          f"got: {wf_order[0] if wf_order else 'empty'}")
    check("workflow_order = evidence_scoring_gate second",
          wf_order[1] if len(wf_order) > 1 else None == "evidence_scoring_gate",
          f"got: {wf_order[1] if len(wf_order) > 1 else 'empty'}")
    check("workflow_order = adjudication_gate third",
          wf_order[2] if len(wf_order) > 2 else None == "adjudication_gate",
          f"got: {wf_order[2] if len(wf_order) > 2 else 'empty'}")
    check("workflow_order = upgrade_preview_decision fourth",
          wf_order[3] if len(wf_order) > 3 else None == "upgrade_preview_decision",
          f"got: {wf_order[3] if len(wf_order) > 3 else 'empty'}")
    for i, expected in enumerate(WORKFLOW_ORDER):
        check(f"workflow_order[{i}] = '{expected}'",
              wf_order[i] == expected if i < len(wf_order) else False,
              f"got: '{wf_order[i] if i < len(wf_order) else 'out of range'}'")

    # ==================================================================
    # 6. Real Workbook — Row Counts = 4
    # ==================================================================
    print("\n[6] Real Workbook — Row Counts = 4")
    check("real_workbook_rows = 4", gate_result.get("real_workbook_rows") == 4,
          f"got: {gate_result.get('real_workbook_rows')}")
    check("real_workflow_records = 4", gate_result.get("real_workflow_records") == 4,
          f"got: {gate_result.get('real_workflow_records')}")
    check("real_workflow_decisions = 4", gate_result.get("real_workflow_decisions") == 4,
          f"got: {gate_result.get('real_workflow_decisions')}")
    check(f"real_records.jsonl has 4 entries (got {len(real_records)})", len(real_records) == 4)
    check(f"real_decisions.jsonl has 4 entries (got {len(real_decisions)})", len(real_decisions) == 4)

    # ==================================================================
    # 7. Real Workbook — Workflow Results
    # ==================================================================
    print("\n[7] Real Workbook — Workflow Results (0 ready, 4 blocked)")
    check("real_workflow_ready_count = 0", gate_result.get("real_workflow_ready_count") == 0,
          f"got: {gate_result.get('real_workflow_ready_count')}")
    check("real_workflow_blocked_count = 4", gate_result.get("real_workflow_blocked_count") == 4,
          f"got: {gate_result.get('real_workflow_blocked_count')}")
    check("real_upgrade_preview_allowed_count = 0",
          gate_result.get("real_upgrade_preview_allowed_count") == 0,
          f"got: {gate_result.get('real_upgrade_preview_allowed_count')}")

    # ==================================================================
    # 8. Real Records — Required Fields
    # ==================================================================
    print("\n[8] Real Records — Required Fields")
    required_record_fields = [
        "address", "current_label", "current_confidence", "target_confidence",
        "intake_ready", "intake_decision",
        "evidence_scoring_passed", "evidence_scoring_decision", "evidence_score",
        "adjudication_ready", "adjudication_decision",
        "workflow_ready", "upgrade_preview_allowed", "new_confidence",
        "workflow_stage_blocked", "workflow_block_reasons",
        "fixture_only", "synthetic_evidence",
    ]
    for i, rec in enumerate(real_records):
        for field in required_record_fields:
            check(f"Real record {i + 1}: field '{field}' present",
                  field in rec, f"missing field: {field}")

    # ==================================================================
    # 9. Real Records — All Blocked
    # ==================================================================
    print("\n[9] Real Records — All Blocked at Intake Gate")
    for i, rec in enumerate(real_records):
        check(f"Real record {i + 1}: intake_ready = false",
              rec.get("intake_ready") is False,
              f"got: {rec.get('intake_ready')}")
        check(f"Real record {i + 1}: evidence_scoring_passed = false",
              rec.get("evidence_scoring_passed") is False,
              f"got: {rec.get('evidence_scoring_passed')}")
        check(f"Real record {i + 1}: adjudication_ready = false",
              rec.get("adjudication_ready") is False,
              f"got: {rec.get('adjudication_ready')}")
        check(f"Real record {i + 1}: workflow_ready = false",
              rec.get("workflow_ready") is False,
              f"got: {rec.get('workflow_ready')}")
        check(f"Real record {i + 1}: upgrade_preview_allowed = false",
              rec.get("upgrade_preview_allowed") is False,
              f"got: {rec.get('upgrade_preview_allowed')}")
        check(f"Real record {i + 1}: new_confidence = current_confidence",
              rec.get("new_confidence") == rec.get("current_confidence"),
              f"new={rec.get('new_confidence')} vs current={rec.get('current_confidence')}")
        check(f"Real record {i + 1}: workflow_stage_blocked is set",
              rec.get("workflow_stage_blocked") is not None)
        check(f"Real record {i + 1}: workflow_block_reasons is non-empty",
              len(rec.get("workflow_block_reasons", [])) > 0)
        check(f"Real record {i + 1}: fixture_only = false",
              rec.get("fixture_only") is False,
              f"got: {rec.get('fixture_only')}")

    # ==================================================================
    # 10. Real Decisions — All Workflow Blocked
    # ==================================================================
    print("\n[10] Real Decisions — All workflow_blocked")
    for i, dec in enumerate(real_decisions):
        check(f"Real decision {i + 1}: decision = 'workflow_blocked'",
              dec.get("decision") == "workflow_blocked",
              f"got: '{dec.get('decision')}'")
        check(f"Real decision {i + 1}: upgrade_preview_allowed = false",
              dec.get("upgrade_preview_allowed") is False)
        check(f"Real decision {i + 1}: real_label_upgrade_allowed = false",
              dec.get("real_label_upgrade_allowed") is False)
        check(f"Real decision {i + 1}: real_label_upgrade_performed = false",
              dec.get("real_label_upgrade_performed") is False)
        check(f"Real decision {i + 1}: send_allowed = false",
              dec.get("send_allowed") is False)
        check(f"Real decision {i + 1}: tg_test_group_allowed = false",
              dec.get("tg_test_group_allowed") is False)
        check(f"Real decision {i + 1}: public_send_allowed = false",
              dec.get("public_send_allowed") is False)
        check(f"Real decision {i + 1}: block_reasons is non-empty",
              len(dec.get("block_reasons", [])) > 0,
              "block_reasons should list why workflow is blocked")

    # ==================================================================
    # 11. Fixture — Row Counts = 1
    # ==================================================================
    print("\n[11] Fixture — Row Counts = 1")
    check("fixture_rows = 1", gate_result.get("fixture_rows") == 1,
          f"got: {gate_result.get('fixture_rows')}")
    check("fixture_workflow_records = 1", gate_result.get("fixture_workflow_records") == 1,
          f"got: {gate_result.get('fixture_workflow_records')}")
    check("fixture_workflow_decisions = 1", gate_result.get("fixture_workflow_decisions") == 1,
          f"got: {gate_result.get('fixture_workflow_decisions')}")
    check(f"fixture_records.jsonl has 1 entry (got {len(fixture_records)})", len(fixture_records) == 1)
    check(f"fixture_decisions.jsonl has 1 entry (got {len(fixture_decisions)})", len(fixture_decisions) == 1)

    # ==================================================================
    # 12. Fixture — Workflow Ready Count = 1
    # ==================================================================
    print("\n[12] Fixture — Workflow Ready Count = 1")
    check("fixture_workflow_ready_count = 1", gate_result.get("fixture_workflow_ready_count") == 1,
          f"got: {gate_result.get('fixture_workflow_ready_count')}")
    check("fixture_upgrade_preview_allowed_count = 1",
          gate_result.get("fixture_upgrade_preview_allowed_count") == 1,
          f"got: {gate_result.get('fixture_upgrade_preview_allowed_count')}")
    check("fixture_label_upgraded_count = 0",
          gate_result.get("fixture_label_upgraded_count") == 0,
          f"got: {gate_result.get('fixture_label_upgraded_count')}")

    # ==================================================================
    # 13. Fixture Record Content
    # ==================================================================
    print("\n[13] Fixture Record — All Gates Passed")
    for i, rec in enumerate(fixture_records):
        check(f"Fixture record {i + 1}: intake_ready = true",
              rec.get("intake_ready") is True,
              f"got: {rec.get('intake_ready')}")
        check(f"Fixture record {i + 1}: evidence_scoring_passed = true",
              rec.get("evidence_scoring_passed") is True,
              f"got: {rec.get('evidence_scoring_passed')}")
        check(f"Fixture record {i + 1}: adjudication_ready = true",
              rec.get("adjudication_ready") is True,
              f"got: {rec.get('adjudication_ready')}")
        check(f"Fixture record {i + 1}: workflow_ready = true",
              rec.get("workflow_ready") is True,
              f"got: {rec.get('workflow_ready')}")
        check(f"Fixture record {i + 1}: upgrade_preview_allowed = true",
              rec.get("upgrade_preview_allowed") is True,
              f"got: {rec.get('upgrade_preview_allowed')}")
        check(f"Fixture record {i + 1}: new_confidence = 'high'",
              rec.get("new_confidence") == "high",
              f"got: '{rec.get('new_confidence')}'")
        check(f"Fixture record {i + 1}: fixture_only = true",
              rec.get("fixture_only") is True,
              f"got: {rec.get('fixture_only')}")
        check(f"Fixture record {i + 1}: synthetic_evidence = true",
              rec.get("synthetic_evidence") is True,
              f"got: {rec.get('synthetic_evidence')}")

    # ==================================================================
    # 14. Fixture Decision Content
    # ==================================================================
    print("\n[14] Fixture Decision — fixture_preview_allowed")
    for i, dec in enumerate(fixture_decisions):
        check(f"Fixture decision {i + 1}: decision = 'fixture_preview_allowed'",
              dec.get("decision") == "fixture_preview_allowed",
              f"got: '{dec.get('decision')}'")
        check(f"Fixture decision {i + 1}: upgrade_preview_allowed = true",
              dec.get("upgrade_preview_allowed") is True)
        check(f"Fixture decision {i + 1}: real_label_upgrade_allowed = false",
              dec.get("real_label_upgrade_allowed") is False)
        check(f"Fixture decision {i + 1}: real_label_upgrade_performed = false",
              dec.get("real_label_upgrade_performed") is False)
        check(f"Fixture decision {i + 1}: send_allowed = false",
              dec.get("send_allowed") is False)
        check(f"Fixture decision {i + 1}: tg_test_group_allowed = false",
              dec.get("tg_test_group_allowed") is False)
        check(f"Fixture decision {i + 1}: public_send_allowed = false",
              dec.get("public_send_allowed") is False)

    # ==================================================================
    # 15. workflow_order_enforced = True
    # ==================================================================
    print("\n[15] workflow_order_enforced = True")
    check("workflow_order_enforced = true", gate_result.get("workflow_order_enforced") is True,
          f"got: {gate_result.get('workflow_order_enforced')}")

    # ==================================================================
    # 16. Real v115F Workbook NOT Modified
    # ==================================================================
    print("\n[16] Real v115F Workbook NOT Modified")
    check("real_workbook_modified = false", gate_result.get("real_workbook_modified") is False)

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
    # 17. Real Label NOT Upgraded
    # ==================================================================
    print("\n[17] Real Label NOT Upgraded")
    check("real_label_upgrade_performed = false",
          gate_result.get("real_label_upgrade_performed") is False)

    # ==================================================================
    # 18. No Real Send Candidate Generated
    # ==================================================================
    print("\n[18] No Real Send Candidate Generated")
    check("real_send_candidate_generated = false",
          gate_result.get("real_send_candidate_generated") is False)

    # ==================================================================
    # 19. All Send Guards = false
    # ==================================================================
    print("\n[19] All Send Guards = false")
    check("send_ready = false", gate_result.get("send_ready") is False)
    check("tg_test_group_ready = false", gate_result.get("tg_test_group_ready") is False)

    # ==================================================================
    # 20. No TG Sent
    # ==================================================================
    print("\n[20] No TG Sent")
    check("tg_sent = false", gate_result.get("tg_sent") is False)

    # ==================================================================
    # 21. No Production State Write
    # ==================================================================
    print("\n[21] No Production State Write")
    check("prod_state_write = false", gate_result.get("prod_state_write") is False)

    # ==================================================================
    # 22. No External API Called
    # ==================================================================
    print("\n[22] No External API Called")
    check("external_api_called = false", gate_result.get("external_api_called") is False)

    # ==================================================================
    # 23. No AI/Model Called
    # ==================================================================
    print("\n[23] No AI/Model Called")
    check("ai_model_called = false", gate_result.get("ai_model_called") is False)

    # ==================================================================
    # 24. No Credentials Read
    # ==================================================================
    print("\n[24] No Credentials Read")
    check("credentials_read = false", gate_result.get("credentials_read") is False)

    # ==================================================================
    # 25. No Daemon/Watcher/Cron/Loop
    # ==================================================================
    print("\n[25] No Daemon/Watcher/Cron/Loop")
    check("daemon_started = false", gate_result.get("daemon_started") is False)
    check("watcher_started = false", gate_result.get("watcher_started") is False)

    # ==================================================================
    # 26. No Files Deleted
    # ==================================================================
    print("\n[26] No Files Deleted")
    check("files_deleted = false", gate_result.get("files_deleted") is False)

    # ==================================================================
    # 27. No Sensitive Data in Outputs
    # ==================================================================
    print("\n[27] No Sensitive Data in Outputs")
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
        check(f"No '{pat}' in any v115M output",
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
        check(f"No '{pat}' in any v115M output", pat not in all_output_text.lower(),
              f"found '{pat}'")

    # ==================================================================
    # 28. Gate Result — All Required Fields
    # ==================================================================
    print("\n[28] Gate Result — All Required Fields")
    required_fields = [
        "stage", "workflow_order",
        "real_workbook_rows", "real_workflow_records", "real_workflow_decisions",
        "real_workflow_ready_count", "real_workflow_blocked_count",
        "real_upgrade_preview_allowed_count",
        "fixture_rows", "fixture_workflow_records", "fixture_workflow_decisions",
        "fixture_workflow_ready_count", "fixture_upgrade_preview_allowed_count",
        "fixture_label_upgraded_count",
        "workflow_order_enforced",
        "real_workbook_modified", "real_label_upgrade_performed",
        "real_send_candidate_generated",
        "send_ready", "tg_test_group_ready", "local_review_ready",
        "external_api_called", "ai_model_called", "credentials_read",
        "tg_sent", "prod_state_write", "daemon_started",
        "watcher_started", "files_deleted",
    ]
    for field in required_fields:
        check(f"Gate result has field '{field}'", field in gate_result,
              f"missing field: {field}")

    # ==================================================================
    # 29. Gate Result — Stage Correct
    # ==================================================================
    print("\n[29] Gate Result — Stage Correct")
    expected_stage = "v115m_whale_manual_audit_end_to_end_upgrade_workflow_gate_local_only"
    check(f"stage = '{expected_stage}'",
          gate_result.get("stage") == expected_stage,
          f"got: {gate_result.get('stage')}")

    # ==================================================================
    # 30. local_review_ready = true
    # ==================================================================
    print("\n[30] local_review_ready = true")
    check("local_review_ready = true", gate_result.get("local_review_ready") is True)

    # ==================================================================
    # 31. Fixture CSV Not Modified
    # ==================================================================
    print("\n[31] Fixture CSV Not Modified")
    fixture_rows_check = load_csv_dict(V115I_FIXTURE)
    check(f"Fixture CSV still has 1 row (got {len(fixture_rows_check)})", len(fixture_rows_check) == 1)
    check("Fixture row still has fixture_only=true",
          parse_bool_csv(fixture_rows_check[0].get("fixture_only", "false")) is True)

    # ==================================================================
    # 32. v115K/v115B Config Files Not Modified
    # ==================================================================
    print("\n[32] Config Files Not Modified")
    scoring_check = load_json(V115K_SCORING_POLICY)
    check("v115K scoring policy version is v115K", scoring_check.get("version") == "v115K")
    check("v115K scoring policy has 9 HC requirements",
          scoring_check.get("minimum_for_high_confidence", {}).get("total_requirements") == 9)

    routing_check = load_json(V115B_ROUTING_POLICY)
    check("v115B routing policy version is v115B", routing_check.get("version") == "v115B")

    # ==================================================================
    # 33. Negative Assertions
    # ==================================================================
    print("\n[33] Negative Assertions — Nothing Claims Success It Shouldn't")
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
    # 34. Count Cross-Checks
    # ==================================================================
    print("\n[34] Count Cross-Checks")
    count_real_ready = sum(1 for rec in real_records if rec.get("workflow_ready") is True)
    count_real_blocked = sum(1 for rec in real_records if rec.get("workflow_ready") is False)
    check(f"Real records: ready={count_real_ready}, blocked={count_real_blocked} matches gate",
          count_real_ready == gate_result.get("real_workflow_ready_count", -1)
          and count_real_blocked == gate_result.get("real_workflow_blocked_count", -1))

    count_fixture_ready = sum(1 for rec in fixture_records if rec.get("workflow_ready") is True)
    check(f"Fixture records: ready={count_fixture_ready} matches gate",
          count_fixture_ready == gate_result.get("fixture_workflow_ready_count", -1))

    count_real_upgrade_preview = sum(1 for rec in real_records if rec.get("upgrade_preview_allowed") is True)
    check(f"Real upgrade_preview_allowed={count_real_upgrade_preview} matches gate",
          count_real_upgrade_preview == gate_result.get("real_upgrade_preview_allowed_count", -1))

    count_fixture_upgrade_preview = sum(1 for rec in fixture_records if rec.get("upgrade_preview_allowed") is True)
    check(f"Fixture upgrade_preview_allowed={count_fixture_upgrade_preview} matches gate",
          count_fixture_upgrade_preview == gate_result.get("fixture_upgrade_preview_allowed_count", -1))

    # ==================================================================
    # 35. Markdown Content Check
    # ==================================================================
    print("\n[35] Markdown Report Content")
    check("Markdown mentions v115M", "v115M" in md_text or "v115m" in md_text.lower())
    check("Markdown mentions workflow gate", "workflow" in md_text.lower())
    check("Markdown mentions gate chain", "intake" in md_text.lower())
    check("Markdown contains safety invariants", "external_api" in md_text.lower())
    check("Markdown mentions Explicit NOT", "NOT" in md_text)

    # ==================================================================
    # 36. Handoff Content Check
    # ==================================================================
    print("\n[36] Handoff Content")
    check("Handoff mentions v115M", "v115M" in handoff_text or "v115m" in handoff_text.lower())
    check("Handoff mentions workflow gate", "workflow" in handoff_text.lower())
    check("Handoff mentions safety invariants", "safety" in handoff_text.lower())
    check("Handoff mentions gate chain", "intake" in handoff_text.lower())

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
