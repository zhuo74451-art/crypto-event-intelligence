#!/usr/bin/env python3
"""
Test suite for v115R Whale Operator Real Workbook Submission Validator & Safe Rerun Plan
========================================================================================
Validates that the v115R runner produced correct outputs:

  - real_workbook_rows == 4
  - validation_records == 4
  - validation_decisions == 4
  - submission_ready_count == 0
  - submission_blocked_count == 4
  - ready_for_v115o_preflight_count == 0
  - ready_for_gate_rerun_count == 0
  - manual_attribution_submission_ready_count == 0
  - corroboration_submission_ready_count == 0
  - safe_rerun_allowed == false
  - safe_rerun_blocked_count == 4
  - commands_allowed_to_run_now_count == 0
  - next_gate_command_order_enforced == true
  - JSONL validation records lines == 4
  - JSONL validation decisions lines == 4
  - CSV data rows == 4
  - Markdown contains 4 addresses
  - Checklist contains TEST_ONLY warning
  - Checklist contains rejected source warning
  - Checklist contains v115O preflight before v115G/L/H/M
  - real_workbook_sha256_before == real_workbook_sha256_after
  - ALL safety flags must be false
  - validator must detect TEST_ONLY contamination terms
  - validator must detect fixture contamination terms
  - validator must not allow medium labels to claim direct TG readiness
  - No fake pass / synthetic passed language
  - No fixture pass claimed as real pass

Safety:
  - v115F workbook NOT modified by this run
  - v115P fixture workbook NOT modified by this run
  - v115A-v115Q historical products NOT modified
"""

import csv
import json
import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RESULTS_DIR = os.path.join(BASE_DIR, "results")
CONFIG_DIR = os.path.join(BASE_DIR, "config")
RUNS_DIR = os.path.join(BASE_DIR, "runs", "market_radar")

# ---------------------------------------------------------------------------
# v115R outputs (must exist)
# ---------------------------------------------------------------------------
V115R_VALIDATION_RECORDS_JSONL = os.path.join(RESULTS_DIR, "market_radar_v115r_whale_real_workbook_submission_validation_records.jsonl")
V115R_VALIDATION_DECISIONS_JSONL = os.path.join(RESULTS_DIR, "market_radar_v115r_whale_real_workbook_submission_validation_decisions.jsonl")
V115R_SAFE_RERUN_PLAN_JSON = os.path.join(RESULTS_DIR, "market_radar_v115r_whale_real_workbook_safe_rerun_plan.json")
V115R_RESULT_JSON = os.path.join(RESULTS_DIR, "market_radar_v115r_whale_operator_real_workbook_submission_validator_result.json")
V115R_REPORT_MD = os.path.join(RUNS_DIR, "v115r_whale_operator_real_workbook_submission_validation_report.md")
V115R_REPORT_CSV = os.path.join(RUNS_DIR, "v115r_whale_operator_real_workbook_submission_validation_report.csv")
V115R_CHECKLIST_MD = os.path.join(RUNS_DIR, "v115r_whale_operator_real_submission_checklist.md")
V115R_HANDOFF_MD = os.path.join(RUNS_DIR, "v115r_whale_operator_real_workbook_submission_validator_local_only_handoff.md")

# ---------------------------------------------------------------------------
# Input files that must still exist and be unmodified
# ---------------------------------------------------------------------------
V115F_WORKBOOK = os.path.join(RUNS_DIR, "v115f_whale_address_audit_operator_workbook.csv")
V115P_FIXTURE_WORKBOOK = os.path.join(RUNS_DIR, "v115p_whale_operator_fixture_filled_workbook.csv")
V115K_REGISTRY = os.path.join(CONFIG_DIR, "market_radar_v115k_whale_label_evidence_source_registry.json")
V115K_SCORING_POLICY = os.path.join(CONFIG_DIR, "market_radar_v115k_whale_label_evidence_scoring_policy.json")

# ---------------------------------------------------------------------------
# Regression — v115Q, v115O, v115M outputs that must still exist
# ---------------------------------------------------------------------------
V115Q_DECISIONS = os.path.join(RESULTS_DIR, "market_radar_v115q_whale_fixture_workflow_replay_decisions.jsonl")
V115Q_GATE = os.path.join(RESULTS_DIR, "market_radar_v115q_whale_fixture_end_to_end_gate_replay_result.json")
V115O_ITEMS = os.path.join(RESULTS_DIR, "market_radar_v115o_whale_operator_evidence_collection_items.jsonl")
V115O_RESULT = os.path.join(RESULTS_DIR, "market_radar_v115o_whale_operator_evidence_collection_kit_result.json")
V115M_DECISIONS = os.path.join(RESULTS_DIR, "market_radar_v115m_whale_real_workflow_decisions.jsonl")
V115M_GATE = os.path.join(RESULTS_DIR, "market_radar_v115m_whale_manual_audit_end_to_end_upgrade_workflow_gate_result.json")

# ---------------------------------------------------------------------------
# Expected addresses
# ---------------------------------------------------------------------------
EXPECTED_ADDRESSES = [
    "0x082e843a431aef031264dc232693dd710aedca88",
    "0x50b309f78e774a756a2230e1769729094cac9f20",
    "0x6c8512516ce5669d35113a11ca8b8de322fd84f6",
    "0x8def9f50456c6c4e37fa5d3d57f108ed23992dae",
]

EXPECTED_LOW_ADDRESSES = [
    "0x082e843a431aef031264dc232693dd710aedca88",
    "0x50b309f78e774a756a2230e1769729094cac9f20",
]

EXPECTED_MEDIUM_ADDRESSES = [
    "0x6c8512516ce5669d35113a11ca8b8de322fd84f6",
    "0x8def9f50456c6c4e37fa5d3d57f108ed23992dae",
]

# Required fields per validation record
REQUIRED_RECORD_FIELDS = [
    "version", "address", "display_label", "current_confidence",
    "operator_fields_status", "present_fields", "missing_required_fields",
    "test_only_contamination_hits", "fixture_value_contamination_hits",
    "rejected_source_hits", "checked_at",
]

# Required fields per validation decision (from task spec)
REQUIRED_DECISION_FIELDS = [
    "address", "display_label", "current_confidence", "priority",
    "action_type", "submission_ready", "ready_for_v115o_preflight",
    "ready_for_gate_rerun", "missing_required_fields", "present_fields",
    "source_type_validation", "rejected_source_hits",
    "test_only_contamination_hits", "fixture_value_contamination_hits",
    "reviewer_validation", "reviewed_at_validation",
    "operator_confirmation_validation", "activity_pattern_validation",
    "recommended_next_step", "blocking_reasons", "safety_status",
]

# Required fields in summary JSON
REQUIRED_SUMMARY_FIELDS = [
    "real_workbook_rows", "validation_records", "validation_decisions",
    "submission_ready_count", "submission_blocked_count",
    "ready_for_v115o_preflight_count", "ready_for_gate_rerun_count",
    "manual_attribution_submission_ready_count",
    "corroboration_submission_ready_count",
    "test_only_contamination_hits_count",
    "fixture_value_contamination_hits_count",
    "rejected_source_hits_count",
    "safe_rerun_allowed", "safe_rerun_blocked_count",
    "commands_allowed_to_run_now_count",
    "next_gate_command_order_enforced",
    "real_workbook_sha256_before", "real_workbook_sha256_after",
    "real_workbook_modified", "real_label_upgrade_performed",
    "real_send_candidate_generated",
    "send_ready", "tg_test_group_ready", "tg_sent",
    "prod_state_write", "external_api_called", "credentials_read",
]

# TEST_ONLY contamination terms that validator must detect
TEST_ONLY_TERMS = [
    "TEST_ONLY_PRIMARY_SOURCE_DO_NOT_USE_AS_REAL_EVIDENCE",
    "TEST_ONLY_SECOND_SOURCE_DO_NOT_USE_AS_REAL_EVIDENCE",
    "TEST_ONLY_ACTIVITY_PATTERN_DO_NOT_USE_AS_REAL_EVIDENCE",
    "TEST_ONLY_OPERATOR_CONFIRMATION_DO_NOT_USE_AS_REAL_EVIDENCE",
    "TEST_ONLY_REVIEWER",
    "TEST_ONLY_REVIEWED_AT_2026-06-05",
]

FIXTURE_TERMS = [
    "fixture_only",
    "synthetic",
    "mock evidence",
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


def main():
    global passed, failed

    print("=" * 70)
    print("v115R Test Suite — Real Workbook Submission Validator & Safe Rerun Plan")
    print("=" * 70)

    # ==================================================================
    # 1. File Existence — v115R Outputs
    # ==================================================================
    print("\n[1] File Existence — v115R Outputs")
    check("Validation records .jsonl exists", file_exists(V115R_VALIDATION_RECORDS_JSONL))
    check("Validation decisions .jsonl exists", file_exists(V115R_VALIDATION_DECISIONS_JSONL))
    check("Safe rerun plan .json exists", file_exists(V115R_SAFE_RERUN_PLAN_JSON))
    check("Result .json exists", file_exists(V115R_RESULT_JSON))
    check("Validation report .md exists", file_exists(V115R_REPORT_MD))
    check("Validation report .csv exists", file_exists(V115R_REPORT_CSV))
    check("Real submission checklist .md exists", file_exists(V115R_CHECKLIST_MD))
    check("Handoff .md exists", file_exists(V115R_HANDOFF_MD))

    # ==================================================================
    # 2. File Existence — Input Sources Still Intact
    # ==================================================================
    print("\n[2] File Existence — Input Sources Still Intact")
    check("v115F workbook still exists", file_exists(V115F_WORKBOOK))
    check("v115P fixture workbook still exists", file_exists(V115P_FIXTURE_WORKBOOK))
    check("v115K registry still exists", file_exists(V115K_REGISTRY))
    check("v115K scoring policy still exists", file_exists(V115K_SCORING_POLICY))

    # ==================================================================
    # 3. File Existence — Regression: v115Q, v115O, v115M Products Intact
    # ==================================================================
    print("\n[3] File Existence — Regression: v115Q, v115O, v115M Products Intact")
    check("v115Q decisions still exists", file_exists(V115Q_DECISIONS))
    check("v115Q gate result still exists", file_exists(V115Q_GATE))
    check("v115O items still exists", file_exists(V115O_ITEMS))
    check("v115O result still exists", file_exists(V115O_RESULT))
    check("v115M decisions still exists", file_exists(V115M_DECISIONS))
    check("v115M gate result still exists", file_exists(V115M_GATE))

    # ==================================================================
    # 4. Data Loading
    # ==================================================================
    print("\n[4] Data Loading")
    validation_records = load_jsonl(V115R_VALIDATION_RECORDS_JSONL)
    check(f"Validation records JSONL loaded: {len(validation_records)} records",
          len(validation_records) > 0)

    validation_decisions = load_jsonl(V115R_VALIDATION_DECISIONS_JSONL)
    check(f"Validation decisions JSONL loaded: {len(validation_decisions)} decisions",
          len(validation_decisions) > 0)

    safe_rerun_plan = load_json(V115R_SAFE_RERUN_PLAN_JSON)
    check("Safe rerun plan JSON parsed", isinstance(safe_rerun_plan, dict))

    summary = load_json(V115R_RESULT_JSON)
    check("Result JSON parsed", isinstance(summary, dict))

    csv_rows = load_csv_dict(V115R_REPORT_CSV)
    check(f"CSV loaded: {len(csv_rows)} rows", len(csv_rows) > 0)

    with open(V115R_REPORT_MD, "r", encoding="utf-8") as f:
        report_md = f.read()
    check("Report markdown loaded", len(report_md) > 0)

    with open(V115R_CHECKLIST_MD, "r", encoding="utf-8") as f:
        checklist_md = f.read()
    check("Checklist markdown loaded", len(checklist_md) > 0)

    with open(V115R_HANDOFF_MD, "r", encoding="utf-8") as f:
        handoff_md = f.read()
    check("Handoff markdown loaded", len(handoff_md) > 0)

    # ==================================================================
    # 5. Core Counts — Row Counts
    # ==================================================================
    print("\n[5] Core Counts — Row Counts")
    check("real_workbook_rows == 4",
          summary.get("real_workbook_rows") == 4,
          f"got: {summary.get('real_workbook_rows')}")
    check("validation_records == 4",
          summary.get("validation_records") == 4,
          f"got: {summary.get('validation_records')}")
    check("validation_decisions == 4",
          summary.get("validation_decisions") == 4,
          f"got: {summary.get('validation_decisions')}")

    # ==================================================================
    # 6. Core Counts — Submission Status
    # ==================================================================
    print("\n[6] Core Counts — Submission Status")
    check("submission_ready_count == 0",
          summary.get("submission_ready_count") == 0,
          f"got: {summary.get('submission_ready_count')}")
    check("submission_blocked_count == 4",
          summary.get("submission_blocked_count") == 4,
          f"got: {summary.get('submission_blocked_count')}")

    # ==================================================================
    # 7. Core Counts — Preflight & Gate Readiness
    # ==================================================================
    print("\n[7] Core Counts — Preflight & Gate Readiness")
    check("ready_for_v115o_preflight_count == 0",
          summary.get("ready_for_v115o_preflight_count") == 0,
          f"got: {summary.get('ready_for_v115o_preflight_count')}")
    check("ready_for_gate_rerun_count == 0",
          summary.get("ready_for_gate_rerun_count") == 0,
          f"got: {summary.get('ready_for_gate_rerun_count')}")
    check("manual_attribution_submission_ready_count == 0",
          summary.get("manual_attribution_submission_ready_count") == 0,
          f"got: {summary.get('manual_attribution_submission_ready_count')}")
    check("corroboration_submission_ready_count == 0",
          summary.get("corroboration_submission_ready_count") == 0,
          f"got: {summary.get('corroboration_submission_ready_count')}")

    # ==================================================================
    # 8. Core Counts — Safe Rerun
    # ==================================================================
    print("\n[8] Core Counts — Safe Rerun")
    check("safe_rerun_allowed == false",
          summary.get("safe_rerun_allowed") is False,
          f"got: {summary.get('safe_rerun_allowed')}")
    check("safe_rerun_blocked_count == 4",
          summary.get("safe_rerun_blocked_count") == 4,
          f"got: {summary.get('safe_rerun_blocked_count')}")
    check("commands_allowed_to_run_now_count == 0",
          summary.get("commands_allowed_to_run_now_count") == 0,
          f"got: {summary.get('commands_allowed_to_run_now_count')}")
    check("next_gate_command_order_enforced == true",
          summary.get("next_gate_command_order_enforced") is True,
          f"got: {summary.get('next_gate_command_order_enforced')}")

    # Also verify in safe_rerun_plan
    check("Safe rerun plan: safe_rerun_allowed == false",
          safe_rerun_plan.get("safe_rerun_allowed") is False,
          f"got: {safe_rerun_plan.get('safe_rerun_allowed')}")
    check("Safe rerun plan: safe_rerun_blocked_count == 4",
          safe_rerun_plan.get("safe_rerun_blocked_count") == 4,
          f"got: {safe_rerun_plan.get('safe_rerun_blocked_count')}")
    check("Safe rerun plan: commands_allowed_to_run_now is empty",
          len(safe_rerun_plan.get("commands_allowed_to_run_now", [1])) == 0,
          f"got: {len(safe_rerun_plan.get('commands_allowed_to_run_now', []))}")
    check("Safe rerun plan: gate_order_enforced == true",
          safe_rerun_plan.get("gate_order_enforced") is True,
          f"got: {safe_rerun_plan.get('gate_order_enforced')}")
    check("Safe rerun plan: must_run_v115o_preflight_before_gates == true",
          safe_rerun_plan.get("must_run_v115o_preflight_before_gates") is True,
          f"got: {safe_rerun_plan.get('must_run_v115o_preflight_before_gates')}")

    # ==================================================================
    # 9. Contamination Counts
    # ==================================================================
    print("\n[9] Contamination Counts")
    check("test_only_contamination_hits_count defined",
          "test_only_contamination_hits_count" in summary)
    check("fixture_value_contamination_hits_count defined",
          "fixture_value_contamination_hits_count" in summary)
    check("rejected_source_hits_count defined",
          "rejected_source_hits_count" in summary)
    # Empty workbook should have 0 contamination hits (nothing to check)
    check("test_only_contamination_hits_count >= 0 (empty workbook)",
          summary.get("test_only_contamination_hits_count", -1) >= 0)
    check("fixture_value_contamination_hits_count >= 0 (empty workbook)",
          summary.get("fixture_value_contamination_hits_count", -1) >= 0)
    check("rejected_source_hits_count >= 0 (empty workbook)",
          summary.get("rejected_source_hits_count", -1) >= 0)

    # ==================================================================
    # 10. JSONL Counts
    # ==================================================================
    print("\n[10] JSONL Counts")
    check(f"Validation records JSONL has 4 lines (got {len(validation_records)})",
          len(validation_records) == 4)
    check(f"Validation decisions JSONL has 4 lines (got {len(validation_decisions)})",
          len(validation_decisions) == 4)

    # ==================================================================
    # 11. CSV Counts
    # ==================================================================
    print("\n[11] CSV Counts")
    check(f"CSV has 4 data rows (got {len(csv_rows)})", len(csv_rows) == 4)

    # ==================================================================
    # 12. Markdown Contains All 4 Addresses
    # ==================================================================
    print("\n[12] Report Markdown Contains All 4 Addresses")
    for addr in EXPECTED_ADDRESSES:
        check(f"Report MD mentions {addr[:10]}...",
              addr[:10] in report_md,
              f"address not found in report markdown")

    # ==================================================================
    # 13. Checklist Content
    # ==================================================================
    print("\n[13] Checklist Content — Required Warnings")
    check("Checklist contains TEST_ONLY warning",
          "TEST_ONLY" in checklist_md,
          "TEST_ONLY warning not found in checklist")
    check("Checklist contains rejected source warning",
          "rejected" in checklist_md.lower() and "source" in checklist_md.lower(),
          "rejected source warning not found in checklist")
    check("Checklist contains v115O preflight before v115G/L/H/M",
          ("v115o" in checklist_md.lower() and "v115g" in checklist_md.lower()),
          "v115O preflight before gates not found in checklist")
    check("Checklist mentions safe rerun order",
          "rerun" in checklist_md.lower() or "order" in checklist_md.lower(),
          "safe rerun order not found in checklist")
    check("Checklist mentions medium cannot direct TG",
          "medium" in checklist_md.lower() and "tg" in checklist_md.lower(),
          "medium TG restriction not found in checklist")
    check("Checklist mentions v115O preflight command",
          "run_market_radar_v115o" in checklist_md,
          "v115O preflight command not in checklist")

    # ==================================================================
    # 14. SHA-256 Integrity
    # ==================================================================
    print("\n[14] SHA-256 Integrity")
    sha_before = summary.get("real_workbook_sha256_before", "")
    sha_after = summary.get("real_workbook_sha256_after", "")
    check("real_workbook_sha256_before is non-empty",
          len(sha_before) == 64,
          f"got: '{sha_before}'")
    check("real_workbook_sha256_after is non-empty",
          len(sha_after) == 64,
          f"got: '{sha_after}'")
    check("real_workbook_sha256_before == real_workbook_sha256_after",
          sha_before == sha_after,
          f"before: {sha_before[:16]}..., after: {sha_after[:16]}...")

    # ==================================================================
    # 15. Safety Flags — All Must Be false
    # ==================================================================
    print("\n[15] Safety Flags — All Must Be false")
    safety_checks = [
        ("real_workbook_modified", summary.get("real_workbook_modified")),
        ("real_label_upgrade_performed", summary.get("real_label_upgrade_performed")),
        ("real_send_candidate_generated", summary.get("real_send_candidate_generated")),
        ("send_ready", summary.get("send_ready")),
        ("tg_test_group_ready", summary.get("tg_test_group_ready")),
        ("tg_sent", summary.get("tg_sent")),
        ("prod_state_write", summary.get("prod_state_write")),
        ("external_api_called", summary.get("external_api_called")),
        ("credentials_read", summary.get("credentials_read")),
    ]
    for name, val in safety_checks:
        check(f"{name} == false", val is False,
              f"got: {val}")

    # ==================================================================
    # 16. Required Record Fields
    # ==================================================================
    print("\n[16] Required Validation Record Fields")
    for i, rec in enumerate(validation_records):
        for field in REQUIRED_RECORD_FIELDS:
            check(f"Record {i+1}: field '{field}' present",
                  field in rec,
                  f"missing field: {field}")

    # ==================================================================
    # 17. Required Decision Fields (Full Task Spec)
    # ==================================================================
    print("\n[17] Required Validation Decision Fields (Full Task Spec)")
    for i, dec in enumerate(validation_decisions):
        for field in REQUIRED_DECISION_FIELDS:
            check(f"Decision {i+1}: field '{field}' present",
                  field in dec,
                  f"missing field: {field}")

    # ==================================================================
    # 18. All Decisions Are Blocked
    # ==================================================================
    print("\n[18] All Decisions Are submission_ready=false")
    for i, dec in enumerate(validation_decisions):
        check(f"Decision {i+1}: submission_ready = false",
              dec.get("submission_ready") is False,
              f"got: {dec.get('submission_ready')}")
        check(f"Decision {i+1}: ready_for_gate_rerun = false",
              dec.get("ready_for_gate_rerun") is False,
              f"got: {dec.get('ready_for_gate_rerun')}")
        check(f"Decision {i+1}: has blocking_reasons",
              len(dec.get("blocking_reasons", [])) > 0,
              f"no blocking reasons listed")
        check(f"Decision {i+1}: has missing_required_fields",
              len(dec.get("missing_required_fields", [])) > 0,
              f"no missing fields listed")

    # ==================================================================
    # 19. Action Types
    # ==================================================================
    print("\n[19] Action Types")
    low_decisions = [d for d in validation_decisions if d["address"] in EXPECTED_LOW_ADDRESSES]
    medium_decisions = [d for d in validation_decisions if d["address"] in EXPECTED_MEDIUM_ADDRESSES]

    for d in low_decisions:
        check(f"Low addr {d['address'][:10]}... has action_type=manual_attribution_required",
              d.get("action_type") == "manual_attribution_required",
              f"got: {d.get('action_type')}")
        check(f"Low addr {d['address'][:10]}... has priority=high",
              d.get("priority") == "high",
              f"got: {d.get('priority')}")

    for d in medium_decisions:
        check(f"Medium addr {d['address'][:10]}... has action_type=corroboration_required",
              d.get("action_type") == "corroboration_required",
              f"got: {d.get('action_type')}")
        check(f"Medium addr {d['address'][:10]}... has priority=medium",
              d.get("priority") == "medium",
              f"got: {d.get('priority')}")

    # ==================================================================
    # 20. Medium Labels Must NOT Claim Direct TG Readiness
    # ==================================================================
    print("\n[20] Medium Labels Must NOT Claim Direct TG Readiness")
    for d in medium_decisions:
        blocking_reasons = [br.lower() for br in d.get("blocking_reasons", [])]
        check(f"Medium addr {d['address'][:10]}... blocks direct TG readiness",
              "tg" in " ".join(blocking_reasons) or "send" in " ".join(blocking_reasons),
              f"no TG/send block in blocking reasons")
        # Check that recommended_next_step does NOT say "go to TG directly"
        next_step = d.get("recommended_next_step", "").lower()
        check(f"Medium addr {d['address'][:10]}... next_step does NOT claim TG readiness",
              "tg test group ready" not in next_step and "tg ready" not in next_step,
              f"next_step claims TG readiness: {d.get('recommended_next_step', '')[:80]}")

    # ==================================================================
    # 21. TEST_ONLY Contamination Detection (validator must have the terms)
    # ==================================================================
    print("\n[21] TEST_ONLY Contamination Detection — Validator Has Terms")
    # The runner source must contain the TEST_ONLY detection terms
    runner_path = os.path.join(BASE_DIR, "scripts",
        "run_market_radar_v115r_whale_operator_real_workbook_submission_validator_and_rerun_plan_local_only.py")
    with open(runner_path, "r", encoding="utf-8") as f:
        runner_src = f.read()

    for term in TEST_ONLY_TERMS:
        check(f"Runner source contains TEST_ONLY term: '{term[:50]}...'",
              term in runner_src,
              f"term not found in runner source")

    # ==================================================================
    # 22. Fixture Contamination Detection — Validator Has Terms
    # ==================================================================
    print("\n[22] Fixture Contamination Detection — Validator Has Terms")
    for term in FIXTURE_TERMS:
        check(f"Runner source contains fixture term: '{term}'",
              term in runner_src,
              f"term not found in runner source")

    # ==================================================================
    # 23. No 'fake pass' / 'synthetic passed' Language
    # ==================================================================
    print("\n[23] No 'fake pass' or 'synthetic passed' Language")
    all_output_text = (
        json.dumps(summary) + json.dumps(validation_records) +
        json.dumps(validation_decisions) + json.dumps(safe_rerun_plan) +
        report_md + checklist_md + handoff_md
    )
    fake_pass_phrases = [
        "synthetic passed",
        "synthetic_passed",
        "fake pass",
        "fake_pass",
        "synthetically passed",
        "fixture pass",
        "fixture_passed as real",
    ]
    for phrase in fake_pass_phrases:
        check(f"No '{phrase}' in outputs",
              phrase.lower() not in all_output_text.lower(),
              f"found '{phrase}'")

    # ==================================================================
    # 24. No Fixture Pass Claimed as Real Pass
    # ==================================================================
    print("\n[24] No Fixture Pass Claimed as Real Pass")
    # Should not say "fixture passed" then follow with "real passed" equivalently
    misleading_phrases = [
        "fixture only pass",
        "fixture-only passed and real passed",
        "fixture through as real",
    ]
    for phrase in misleading_phrases:
        check(f"No '{phrase}' in outputs",
              phrase.lower() not in all_output_text.lower(),
              f"found '{phrase}'")

    # ==================================================================
    # 25. No Sensitive Data in Outputs
    # ==================================================================
    print("\n[25] No Sensitive Data in Outputs")
    sensitive_patterns = [
        "API_KEY", "api_key", "token", "password", "secret",
        ".env", "OPENAI", "OPENROUTER", "cookie",
    ]
    for pat in sensitive_patterns:
        check(f"No '{pat}' in any v115R output",
              pat.lower() not in all_output_text.lower(),
              f"found '{pat}'")

    # ==================================================================
    # 26. No API Call Patterns
    # ==================================================================
    print("\n[26] No API Call Patterns")
    api_patterns = [
        "http://api.", "https://api.", "fetch(", "curl ",
        "requests.get", "requests.post", "urllib",
    ]
    for pat in api_patterns:
        check(f"No '{pat}' in any v115R output",
              pat not in all_output_text.lower(),
              f"found '{pat}'")

    # ==================================================================
    # 27. Required Summary Fields
    # ==================================================================
    print("\n[27] Result JSON — All Required Fields Present")
    for field in REQUIRED_SUMMARY_FIELDS:
        check(f"Result has field '{field}'",
              field in summary,
              f"missing field: {field}")

    # ==================================================================
    # 28. Stage Correct
    # ==================================================================
    print("\n[28] Stage Correct")
    check("stage matches v115r submission validator",
          "v115r_whale_operator_real_workbook_submission_validator" in summary.get("stage", ""),
          f"got: {summary.get('stage')}")

    # ==================================================================
    # 29. v115F Workbook NOT Modified
    # ==================================================================
    print("\n[29] v115F Workbook NOT Modified")
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
                check(f"v115F row {i+1}: '{field}' still empty",
                      (val or "").strip() == "",
                      f"got non-empty: '{val[:50]}'")

    # ==================================================================
    # 30. v115P Fixture Workbook NOT Modified
    # ==================================================================
    print("\n[30] v115P Fixture Workbook NOT Modified")
    fixture_rows = load_csv_dict(V115P_FIXTURE_WORKBOOK)
    check(f"v115P fixture workbook still has 4 rows (got {len(fixture_rows)})", len(fixture_rows) == 4)

    # v115P fixture should still contain TEST_ONLY values
    fixture_all_text = " ".join(
        v for row in fixture_rows for v in row.values()
    )
    check("v115P fixture still contains TEST_ONLY values",
          "TEST_ONLY" in fixture_all_text,
          "v115P fixture may have been modified — TEST_ONLY values missing")

    # ==================================================================
    # 31. v115K Configs Not Modified
    # ==================================================================
    print("\n[31] v115K Configs Not Modified")
    registry = load_json(V115K_REGISTRY)
    check("v115K registry version is v115K", registry.get("version") == "v115K")
    check("v115K registry has 4 categories", registry.get("registry_categories") == 4)

    scoring = load_json(V115K_SCORING_POLICY)
    check("v115K scoring policy version is v115K", scoring.get("version") == "v115K")
    check("v115K scoring policy has 9 HC requirements",
          scoring.get("minimum_for_high_confidence", {}).get("total_requirements") == 9)

    # ==================================================================
    # 32. Safe Rerun Plan — Commands After All Ready
    # ==================================================================
    print("\n[32] Safe Rerun Plan — commands_after_all_submissions_ready")
    commands_after = safe_rerun_plan.get("commands_after_all_submissions_ready", [])
    check(f"commands_after_all_submissions_ready has 5 entries (got {len(commands_after)})",
          len(commands_after) == 5,
          f"got: {len(commands_after)}")
    expected_keywords = ["v115o", "v115g", "v115l", "v115h", "v115m"]
    for i, keyword in enumerate(expected_keywords):
        check(f"commands_after[{i}] contains '{keyword}'",
              keyword in commands_after[i].lower() if i < len(commands_after) else False,
              f"got: '{commands_after[i] if i < len(commands_after) else 'out of range'}'")

    # ==================================================================
    # 33. Report Markdown Has Key Sections
    # ==================================================================
    print("\n[33] Report Markdown Has Key Sections")
    check("Report mentions all addresses blocked",
          "blocked" in report_md.lower(),
          "blocked mention not in report")
    check("Report says gate rerun not permitted",
          ("gate" in report_md.lower() and "not" in report_md.lower()),
          "gate rerun warning not found")
    check("Report says must fill workbook first",
          "fill" in report_md.lower() and "workbook" in report_md.lower(),
          "workbook fill instruction not found")
    check("Report says v115O preflight must run first",
          "v115o" in report_md.lower() or "preflight" in report_md.lower(),
          "preflight mention not found")
    check("Report says medium cannot direct TG",
          "medium" in report_md.lower() and "tg" in report_md.lower(),
          "medium TG restriction not found")
    check("Report has per-address validation",
          "Per-Address" in report_md or "per-address" in report_md.lower(),
          "per-address section not found")

    # ==================================================================
    # 34. Handoff Content
    # ==================================================================
    print("\n[34] Handoff Content")
    check("Handoff mentions v115R", "v115R" in handoff_md or "v115r" in handoff_md.lower())
    check("Handoff mentions validation", "validation" in handoff_md.lower())
    check("Handoff mentions safe rerun", "safe" in handoff_md.lower() and "rerun" in handoff_md.lower())
    check("Handoff mentions TG not allowed", "TG" in handoff_md)
    check("Handoff mentions v115G gate", "v115g" in handoff_md.lower())
    check("Handoff mentions v115H gate", "v115h" in handoff_md.lower())
    check("Handoff mentions v115M gate", "v115m" in handoff_md.lower())

    # ==================================================================
    # 35. Count Cross-Check: Summary matches Records/Decisions
    # ==================================================================
    print("\n[35] Count Cross-Check: Summary Matches Records/Decisions")
    check(f"summary.real_workbook_rows ({summary.get('real_workbook_rows')}) matches records ({len(validation_records)})",
          summary.get("real_workbook_rows") == len(validation_records))
    check(f"summary.validation_records ({summary.get('validation_records')}) matches records ({len(validation_records)})",
          summary.get("validation_records") == len(validation_records))
    check(f"summary.validation_decisions ({summary.get('validation_decisions')}) matches decisions ({len(validation_decisions)})",
          summary.get("validation_decisions") == len(validation_decisions))

    count_blocked = sum(1 for d in validation_decisions if not d["submission_ready"])
    check(f"summary.submission_blocked_count ({summary.get('submission_blocked_count')}) matches decisions ({count_blocked})",
          summary.get("submission_blocked_count") == count_blocked)

    count_sr_ready = sum(1 for d in validation_decisions if d["submission_ready"])
    check(f"summary.submission_ready_count ({summary.get('submission_ready_count')}) matches decisions ({count_sr_ready})",
          summary.get("submission_ready_count") == count_sr_ready)

    # ==================================================================
    # 36. CSV Has Required Columns
    # ==================================================================
    print("\n[36] CSV Has Required Columns")
    csv_required_cols = [
        "address", "display_label", "current_confidence", "priority",
        "action_type", "submission_ready", "ready_for_v115o_preflight",
        "ready_for_gate_rerun", "missing_required_fields",
        "test_only_contamination_hits", "fixture_value_contamination_hits",
        "rejected_source_hits", "reviewer_validation",
        "reviewed_at_validation", "operator_confirmation_validation",
        "activity_pattern_validation", "recommended_next_step",
        "blocking_reasons", "safety_status",
    ]
    for col in csv_required_cols:
        check(f"CSV has column '{col}'",
              col in csv_rows[0] if csv_rows else False,
              f"missing column: {col}")

    # ==================================================================
    # 37. Negative Assertions — Not Claiming Real Upgrades
    # ==================================================================
    print("\n[37] Negative Assertions — Not Claiming Real Upgrades")
    check("NOT claiming real_label_upgrade_performed=true",
          summary.get("real_label_upgrade_performed") is not True)
    check("NOT claiming real_send_candidate_generated=true",
          summary.get("real_send_candidate_generated") is not True)
    check("NOT claiming send_ready=true",
          summary.get("send_ready") is not True)
    check("NOT claiming tg_test_group_ready=true",
          summary.get("tg_test_group_ready") is not True)
    check("NOT claiming tg_sent=true",
          summary.get("tg_sent") is not True)
    check("NOT claiming prod_state_write=true",
          summary.get("prod_state_write") is not True)
    check("NOT claiming external_api_called=true",
          summary.get("external_api_called") is not True)
    check("NOT claiming credentials_read=true",
          summary.get("credentials_read") is not True)
    check("NOT claiming real_workbook_modified=true",
          summary.get("real_workbook_modified") is not True)

    # ==================================================================
    # 38. Safe Rerun Plan Has Required Fields
    # ==================================================================
    print("\n[38] Safe Rerun Plan Has Required Fields")
    rerun_required_fields = [
        "safe_rerun_allowed", "safe_rerun_blocked_count",
        "commands_allowed_to_run_now", "commands_after_all_submissions_ready",
        "gate_order_enforced", "must_run_v115o_preflight_before_gates",
        "medium_cannot_direct_tg_even_after_gate_pass",
    ]
    for field in rerun_required_fields:
        check(f"Safe rerun plan has field '{field}'",
              field in safe_rerun_plan,
              f"missing field: {field}")

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
