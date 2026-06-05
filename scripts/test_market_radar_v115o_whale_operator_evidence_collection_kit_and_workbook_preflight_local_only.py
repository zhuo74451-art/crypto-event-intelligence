#!/usr/bin/env python3
"""
Test suite for v115O Whale Operator Evidence Collection Kit & Workbook Preflight
================================================================================
Validates that the v115O runner produced correct outputs:

  - evidence_collection_items == 4
  - high_priority_items == 2
  - medium_priority_items == 2
  - manual_attribution_required_count == 2
  - corroboration_required_count == 2
  - preflight_records == 4
  - preflight_ready_count == 0
  - preflight_blocked_count == 4
  - ready_for_gate_rerun_count == 0
  - JSONL evidence collection lines == 4
  - JSONL preflight records lines == 4
  - JSONL preflight decisions lines == 4
  - CSV data rows == 4
  - Markdown mentions all 4 addresses
  - Markdown mentions "High priority manual attribution"
  - Markdown mentions "Medium priority corroboration"
  - low/unknown addresses require trusted_primary_source + second source + activity + operator confirmation
  - medium addresses require corroboration, NOT direct TG test group access
  - next_gate_command_order_enforced == true
  - gate order must be v115G → v115L → v115H → v115M
  - workbook_modified == false
  - real_label_upgrade_performed == false
  - real_send_candidate_generated == false
  - send_ready == false
  - tg_test_group_ready == false
  - tg_sent == false
  - prod_state_write == false
  - external_api_called == false
  - credentials_read == false
  - No fake pass / synthetic passed language

Safety:
  - v115F workbook NOT modified by this run
  - v115A-v115N historical products NOT modified
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
# v115O outputs (must exist)
# ---------------------------------------------------------------------------
V115O_ITEMS_JSONL = os.path.join(RESULTS_DIR, "market_radar_v115o_whale_operator_evidence_collection_items.jsonl")
V115O_PREFLIGHT_RECORDS_JSONL = os.path.join(RESULTS_DIR, "market_radar_v115o_whale_operator_workbook_preflight_records.jsonl")
V115O_PREFLIGHT_DECISIONS_JSONL = os.path.join(RESULTS_DIR, "market_radar_v115o_whale_operator_workbook_preflight_decisions.jsonl")
V115O_RESULT_JSON = os.path.join(RESULTS_DIR, "market_radar_v115o_whale_operator_evidence_collection_kit_result.json")
V115O_KIT_MD = os.path.join(RUNS_DIR, "v115o_whale_operator_evidence_collection_kit.md")
V115O_KIT_CSV = os.path.join(RUNS_DIR, "v115o_whale_operator_evidence_collection_kit.csv")
V115O_PREFLIGHT_REPORT_MD = os.path.join(RUNS_DIR, "v115o_whale_operator_workbook_preflight_report.md")
V115O_HANDOFF_MD = os.path.join(RUNS_DIR, "v115o_whale_operator_evidence_collection_kit_local_only_handoff.md")

# ---------------------------------------------------------------------------
# Input files that must still exist and be unmodified
# ---------------------------------------------------------------------------
V115F_WORKBOOK = os.path.join(RUNS_DIR, "v115f_whale_address_audit_operator_workbook.csv")
V115K_REGISTRY = os.path.join(CONFIG_DIR, "market_radar_v115k_whale_label_evidence_source_registry.json")
V115K_SCORING_POLICY = os.path.join(CONFIG_DIR, "market_radar_v115k_whale_label_evidence_scoring_policy.json")

# ---------------------------------------------------------------------------
# v115N outputs that must still exist (regression)
# ---------------------------------------------------------------------------
V115N_JSONL = os.path.join(RESULTS_DIR, "market_radar_v115n_whale_manual_audit_operator_actions.jsonl")
V115N_JSON = os.path.join(RESULTS_DIR, "market_radar_v115n_whale_manual_audit_operator_action_queue_result.json")
V115N_CSV = os.path.join(RUNS_DIR, "v115n_whale_manual_audit_operator_action_queue.csv")
V115N_MD = os.path.join(RUNS_DIR, "v115n_whale_manual_audit_operator_action_queue.md")

# ---------------------------------------------------------------------------
# v115M & v115L outputs that must still exist (regression)
# ---------------------------------------------------------------------------
V115M_DECISIONS = os.path.join(RESULTS_DIR, "market_radar_v115m_whale_real_workflow_decisions.jsonl")
V115M_GATE = os.path.join(RESULTS_DIR, "market_radar_v115m_whale_manual_audit_end_to_end_upgrade_workflow_gate_result.json")
V115L_SCORING = os.path.join(RESULTS_DIR, "market_radar_v115l_whale_real_workbook_evidence_scoring_decisions.jsonl")
V115L_GATE = os.path.join(RESULTS_DIR, "market_radar_v115l_whale_label_evidence_scoring_gate_result.json")

# ---------------------------------------------------------------------------
# Expected gate order keywords
# ---------------------------------------------------------------------------
EXPECTED_GATE_ORDER_KEYWORDS = ["v115g", "v115l", "v115h", "v115m"]

# ---------------------------------------------------------------------------
# The 4 real addresses
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

# Required fields per evidence collection item
REQUIRED_ITEM_FIELDS = [
    "address",
    "display_label",
    "current_confidence",
    "priority",
    "action_type",
    "research_goal",
    "required_evidence_bundle",
    "primary_source_checklist",
    "secondary_source_checklist",
    "activity_pattern_checklist",
    "operator_confirmation_fields",
    "reviewer_fields",
    "rejected_source_types",
    "do_not_use_evidence_warning",
    "workbook_fields_to_fill",
    "minimum_pass_condition",
    "next_local_preflight_command",
    "next_gate_commands_after_preflight_pass",
    "safety_status",
]

# Required fields per preflight decision
REQUIRED_PREFLIGHT_FIELDS = [
    "address",
    "display_label",
    "current_confidence",
    "action_type",
    "preflight_ready",
    "missing_required_fields",
    "present_fields",
    "rejected_source_hits",
    "ready_for_gate_rerun",
    "recommended_next_step",
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
    print("v115O Test Suite — Evidence Collection Kit & Workbook Preflight")
    print("=" * 70)

    # ==================================================================
    # 1. File Existence — v115O Outputs
    # ==================================================================
    print("\n[1] File Existence — v115O Outputs")
    check("Evidence collection items .jsonl exists", file_exists(V115O_ITEMS_JSONL))
    check("Preflight records .jsonl exists", file_exists(V115O_PREFLIGHT_RECORDS_JSONL))
    check("Preflight decisions .jsonl exists", file_exists(V115O_PREFLIGHT_DECISIONS_JSONL))
    check("Result .json exists", file_exists(V115O_RESULT_JSON))
    check("Evidence collection kit .md exists", file_exists(V115O_KIT_MD))
    check("Evidence collection kit .csv exists", file_exists(V115O_KIT_CSV))
    check("Preflight report .md exists", file_exists(V115O_PREFLIGHT_REPORT_MD))
    check("Handoff .md exists", file_exists(V115O_HANDOFF_MD))

    # ==================================================================
    # 2. File Existence — Input Sources Still Intact
    # ==================================================================
    print("\n[2] File Existence — Input Sources Still Intact")
    check("v115F workbook still exists", file_exists(V115F_WORKBOOK))
    check("v115K registry still exists", file_exists(V115K_REGISTRY))
    check("v115K scoring policy still exists", file_exists(V115K_SCORING_POLICY))

    # ==================================================================
    # 3. File Existence — v115N Historical Products Still Intact
    # ==================================================================
    print("\n[3] File Existence — v115N Historical Products Still Intact")
    check("v115N actions .jsonl still exists", file_exists(V115N_JSONL))
    check("v115N result .json still exists", file_exists(V115N_JSON))
    check("v115N CSV still exists", file_exists(V115N_CSV))
    check("v115N MD still exists", file_exists(V115N_MD))

    # ==================================================================
    # 4. File Existence — v115M & v115L Historical Products Still Intact
    # ==================================================================
    print("\n[4] File Existence — v115M & v115L Historical Products Still Intact")
    check("v115M decisions still exists", file_exists(V115M_DECISIONS))
    check("v115M gate result still exists", file_exists(V115M_GATE))
    check("v115L scoring decisions still exists", file_exists(V115L_SCORING))
    check("v115L gate result still exists", file_exists(V115L_GATE))

    # ==================================================================
    # 5. Data Loading
    # ==================================================================
    print("\n[5] Data Loading")
    items = load_jsonl(V115O_ITEMS_JSONL)
    check(f"Items JSONL loaded: {len(items)} items", len(items) > 0)

    preflight_records = load_jsonl(V115O_PREFLIGHT_RECORDS_JSONL)
    check(f"Preflight records JSONL loaded: {len(preflight_records)} records", len(preflight_records) > 0)

    preflight_decisions = load_jsonl(V115O_PREFLIGHT_DECISIONS_JSONL)
    check(f"Preflight decisions JSONL loaded: {len(preflight_decisions)} decisions", len(preflight_decisions) > 0)

    result = load_json(V115O_RESULT_JSON)
    check("Result JSON parsed", isinstance(result, dict))

    csv_rows = load_csv_dict(V115O_KIT_CSV)
    check(f"CSV loaded: {len(csv_rows)} rows", len(csv_rows) > 0)

    with open(V115O_KIT_MD, "r", encoding="utf-8") as f:
        kit_md = f.read()
    check("Kit markdown loaded", len(kit_md) > 0)

    with open(V115O_PREFLIGHT_REPORT_MD, "r", encoding="utf-8") as f:
        preflight_md = f.read()
    check("Preflight report markdown loaded", len(preflight_md) > 0)

    with open(V115O_HANDOFF_MD, "r", encoding="utf-8") as f:
        handoff_md = f.read()
    check("Handoff markdown loaded", len(handoff_md) > 0)

    # ==================================================================
    # 6. Core Counts — Evidence Collection
    # ==================================================================
    print("\n[6] Core Counts — Evidence Collection")
    check("evidence_collection_items == 4",
          result.get("evidence_collection_items") == 4,
          f"got: {result.get('evidence_collection_items')}")
    check("high_priority_items == 2",
          result.get("high_priority_items") == 2,
          f"got: {result.get('high_priority_items')}")
    check("medium_priority_items == 2",
          result.get("medium_priority_items") == 2,
          f"got: {result.get('medium_priority_items')}")
    check("manual_attribution_required_count == 2",
          result.get("manual_attribution_required_count") == 2,
          f"got: {result.get('manual_attribution_required_count')}")
    check("corroboration_required_count == 2",
          result.get("corroboration_required_count") == 2,
          f"got: {result.get('corroboration_required_count')}")

    # ==================================================================
    # 7. Core Counts — Preflight
    # ==================================================================
    print("\n[7] Core Counts — Preflight")
    check("preflight_records == 4",
          result.get("preflight_records") == 4,
          f"got: {result.get('preflight_records')}")
    check("preflight_ready_count == 0",
          result.get("preflight_ready_count") == 0,
          f"got: {result.get('preflight_ready_count')}")
    check("preflight_blocked_count == 4",
          result.get("preflight_blocked_count") == 4,
          f"got: {result.get('preflight_blocked_count')}")
    check("ready_for_gate_rerun_count == 0",
          result.get("ready_for_gate_rerun_count") == 0,
          f"got: {result.get('ready_for_gate_rerun_count')}")

    # ==================================================================
    # 8. JSONL Counts
    # ==================================================================
    print("\n[8] JSONL Counts")
    check(f"Evidence collection items JSONL has 4 lines (got {len(items)})",
          len(items) == 4)
    check(f"Preflight records JSONL has 4 lines (got {len(preflight_records)})",
          len(preflight_records) == 4)
    check(f"Preflight decisions JSONL has 4 lines (got {len(preflight_decisions)})",
          len(preflight_decisions) == 4)

    # ==================================================================
    # 9. CSV Counts
    # ==================================================================
    print("\n[9] CSV Counts")
    check(f"CSV has 4 data rows (got {len(csv_rows)})", len(csv_rows) == 4)

    # ==================================================================
    # 10. Markdown Mentions All 4 Addresses
    # ==================================================================
    print("\n[10] Kit Markdown Contains All 4 Addresses")
    for addr in EXPECTED_ADDRESSES:
        check(f"Kit MD mentions {addr[:10]}...",
              addr[:10] in kit_md,
              f"address not found in kit markdown")

    # ==================================================================
    # 11. Markdown Section Headers
    # ==================================================================
    print("\n[11] Kit Markdown Section Headers")
    check("Kit MD contains 'High Priority Manual Attribution'",
          "high priority manual attribution" in kit_md.lower(),
          "section header not found")
    check("Kit MD contains 'Medium Priority Corroboration'",
          "medium priority corroboration" in kit_md.lower(),
          "section header not found")

    # ==================================================================
    # 12. Low/Unknown Address Evidence Requirements
    # ==================================================================
    print("\n[12] Low/Unknown Address Evidence Requirements")
    for item in items:
        addr = item["address"]
        bundle = item["required_evidence_bundle"]
        bundle_str = " ".join(bundle).lower()

        if addr in EXPECTED_LOW_ADDRESSES:
            check(f"Low addr {addr[:10]}... requires trusted_primary_source",
                  "trusted_primary_source" in bundle_str,
                  "missing required evidence")
            check(f"Low addr {addr[:10]}... requires second_source",
                  "second_source" in bundle_str,
                  "missing required evidence")
            check(f"Low addr {addr[:10]}... requires activity_pattern",
                  "activity_pattern" in bundle_str,
                  "missing required evidence")
            check(f"Low addr {addr[:10]}... requires operator_confirmation",
                  "operator_confirmation" in bundle_str,
                  "missing required evidence")
            check(f"Low addr {addr[:10]}... requires reviewer",
                  "reviewer" in bundle_str,
                  "missing required evidence")
            check(f"Low addr {addr[:10]}... requires reviewed_at",
                  "reviewed_at" in bundle_str,
                  "missing required evidence")
            check(f"Low addr {addr[:10]}... requires ready_for_upgrade",
                  "ready_for_upgrade" in bundle_str,
                  "missing required evidence")
            check(f"Low addr {addr[:10]}... has action_type=manual_attribution_required",
                  item["action_type"] == "manual_attribution_required",
                  f"got: {item['action_type']}")
            check(f"Low addr {addr[:10]}... has priority=high",
                  item["priority"] == "high",
                  f"got: {item['priority']}")

    # ==================================================================
    # 13. Medium Address Evidence Requirements
    # ==================================================================
    print("\n[13] Medium Address Evidence Requirements")
    for item in items:
        addr = item["address"]
        bundle = item["required_evidence_bundle"]
        bundle_str = " ".join(bundle).lower()

        if addr in EXPECTED_MEDIUM_ADDRESSES:
            check(f"Medium addr {addr[:10]}... requires primary_source_or_existing",
                  "primary_source" in bundle_str or "existing_label" in bundle_str,
                  "missing required evidence")
            check(f"Medium addr {addr[:10]}... requires second_source",
                  "second_source" in bundle_str,
                  "missing required evidence")
            check(f"Medium addr {addr[:10]}... requires activity_pattern",
                  "activity_pattern" in bundle_str,
                  "missing required evidence")
            check(f"Medium addr {addr[:10]}... requires operator_confirmation",
                  "operator_confirmation" in bundle_str,
                  "missing required evidence")
            check(f"Medium addr {addr[:10]}... has action_type=corroboration_required",
                  item["action_type"] == "corroboration_required",
                  f"got: {item['action_type']}")
            check(f"Medium addr {addr[:10]}... has priority=medium",
                  item["priority"] == "medium",
                  f"got: {item['priority']}")
            # Medium must NOT claim direct TG test group access
            min_pass = item.get("minimum_pass_condition", "").lower()
            check(f"Medium addr {addr[:10]}... minimum_pass blocks direct TG",
                  "cannot" in min_pass or "can not" in min_pass or "must" in min_pass,
                  "minimum_pass_condition does not block direct TG")

    # ==================================================================
    # 14. next_gate_command_order_enforced
    # ==================================================================
    print("\n[14] next_gate_command_order_enforced")
    check("next_gate_command_order_enforced == true",
          result.get("next_gate_command_order_enforced") is True,
          f"got: {result.get('next_gate_command_order_enforced')}")

    gate_commands = result.get("next_gate_commands", [])
    check(f"next_gate_commands has 4 entries", len(gate_commands) == 4,
          f"got: {len(gate_commands)}")

    for i, keyword in enumerate(EXPECTED_GATE_ORDER_KEYWORDS):
        check(f"gate command [{i}] contains '{keyword}'",
              keyword in gate_commands[i].lower() if i < len(gate_commands) else False,
              f"got: '{gate_commands[i] if i < len(gate_commands) else 'out of range'}'")

    # Verify gate order in each evidence collection item
    for i, item in enumerate(items):
        ngc = item.get("next_gate_commands_after_preflight_pass", [])
        check(f"Item {i+1}: next_gate_commands has 4 entries", len(ngc) == 4,
              f"got: {len(ngc)}")
        for j, keyword in enumerate(EXPECTED_GATE_ORDER_KEYWORDS):
            check(f"Item {i+1}: gate command [{j}] contains '{keyword}'",
                  keyword in ngc[j].lower() if j < len(ngc) else False,
                  f"got: '{ngc[j] if j < len(ngc) else 'out of range'}'")

    # ==================================================================
    # 15. Safety Flags — All Must Be false
    # ==================================================================
    print("\n[15] Safety Flags — All Must Be false")
    safety_checks = [
        ("workbook_modified", result.get("workbook_modified")),
        ("real_label_upgrade_performed", result.get("real_label_upgrade_performed")),
        ("real_send_candidate_generated", result.get("real_send_candidate_generated")),
        ("send_ready", result.get("send_ready")),
        ("tg_test_group_ready", result.get("tg_test_group_ready")),
        ("tg_sent", result.get("tg_sent")),
        ("prod_state_write", result.get("prod_state_write")),
        ("external_api_called", result.get("external_api_called")),
        ("credentials_read", result.get("credentials_read")),
    ]
    for name, val in safety_checks:
        check(f"{name} == false", val is False,
              f"got: {val}")

    # ==================================================================
    # 16. Required Item Fields
    # ==================================================================
    print("\n[16] Required Evidence Collection Item Fields")
    for i, item in enumerate(items):
        for field in REQUIRED_ITEM_FIELDS:
            check(f"Item {i+1}: field '{field}' present",
                  field in item,
                  f"missing field: {field}")

    # ==================================================================
    # 17. Required Preflight Decision Fields
    # ==================================================================
    print("\n[17] Required Preflight Decision Fields")
    for i, decision in enumerate(preflight_decisions):
        for field in REQUIRED_PREFLIGHT_FIELDS:
            check(f"Decision {i+1}: field '{field}' present",
                  field in decision,
                  f"missing field: {field}")

    # ==================================================================
    # 18. All Preflight Decisions Are Blocked
    # ==================================================================
    print("\n[18] All Preflight Decisions Are Blocked")
    for i, decision in enumerate(preflight_decisions):
        check(f"Decision {i+1}: preflight_ready = false",
              decision["preflight_ready"] is False,
              f"got: {decision['preflight_ready']}")
        check(f"Decision {i+1}: ready_for_gate_rerun = false",
              decision["ready_for_gate_rerun"] is False,
              f"got: {decision['ready_for_gate_rerun']}")
        check(f"Decision {i+1}: has missing_required_fields",
              len(decision.get("missing_required_fields", [])) > 0,
              f"no missing fields listed")

    # ==================================================================
    # 19. Negative Assertions — No Fake Pass Claims
    # ==================================================================
    print("\n[19] Negative Assertions — No Fake Pass Claims")
    check("NOT claiming workbook_modified=true", result.get("workbook_modified") is not True)
    check("NOT claiming send_ready=true", result.get("send_ready") is not True)
    check("NOT claiming tg_test_group_ready=true", result.get("tg_test_group_ready") is not True)
    check("NOT claiming tg_sent=true", result.get("tg_sent") is not True)
    check("NOT claiming prod_state_write=true", result.get("prod_state_write") is not True)
    check("NOT claiming real_label_upgrade_performed=true", result.get("real_label_upgrade_performed") is not True)
    check("NOT claiming real_send_candidate_generated=true", result.get("real_send_candidate_generated") is not True)
    check("NOT claiming external_api_called=true", result.get("external_api_called") is not True)
    check("NOT claiming credentials_read=true", result.get("credentials_read") is not True)

    # ==================================================================
    # 20. No 'synthetic passed' or 'fake pass' Language
    # ==================================================================
    print("\n[20] No 'synthetic passed' or 'fake pass' Language")
    all_output_text = json.dumps(result) + json.dumps(items) + json.dumps(preflight_decisions)
    all_output_text += kit_md + preflight_md + handoff_md
    fake_pass_phrases = [
        "synthetic passed",
        "synthetic_passed",
        "fake pass",
        "fake_pass",
        "synthetically passed",
    ]
    for phrase in fake_pass_phrases:
        check(f"No '{phrase}' in outputs",
              phrase.lower() not in all_output_text.lower(),
              f"found '{phrase}'")

    # ==================================================================
    # 21. No Sensitive Data
    # ==================================================================
    print("\n[21] No Sensitive Data in Outputs")
    sensitive_patterns = [
        "API_KEY", "api_key", "token", "password", "secret",
        ".env", "OPENAI", "OPENROUTER", "cookie",
    ]
    for pat in sensitive_patterns:
        check(f"No '{pat}' in any v115O output",
              pat.lower() not in all_output_text.lower(),
              f"found '{pat}'")

    # ==================================================================
    # 22. No API Call Patterns
    # ==================================================================
    print("\n[22] No API Call Patterns")
    api_patterns = ["http://api.", "https://api.", "fetch(", "curl ",
                    "requests.get", "requests.post", "urllib"]
    for pat in api_patterns:
        check(f"No '{pat}' in any v115O output", pat not in all_output_text.lower(),
              f"found '{pat}'")

    # ==================================================================
    # 23. v115F Workbook NOT Modified
    # ==================================================================
    print("\n[23] v115F Workbook NOT Modified")
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
                      f"got non-empty: '{val}'")

    # ==================================================================
    # 24. v115K Configs Not Modified
    # ==================================================================
    print("\n[24] v115K Configs Not Modified")
    registry = load_json(V115K_REGISTRY)
    check("v115K registry version is v115K", registry.get("version") == "v115K")
    check("v115K registry has 4 categories", registry.get("registry_categories") == 4)

    scoring = load_json(V115K_SCORING_POLICY)
    check("v115K scoring policy version is v115K", scoring.get("version") == "v115K")
    check("v115K scoring policy has 9 HC requirements",
          scoring.get("minimum_for_high_confidence", {}).get("total_requirements") == 9)

    # ==================================================================
    # 25. Result JSON — All Required Fields
    # ==================================================================
    print("\n[25] Result JSON — All Required Fields")
    required_result_fields = [
        "stage", "version",
        "evidence_collection_items", "high_priority_items", "medium_priority_items",
        "manual_attribution_required_count", "corroboration_required_count",
        "preflight_records", "preflight_ready_count", "preflight_blocked_count",
        "ready_for_gate_rerun_count", "rejected_source_hits_count",
        "workbook_modified", "real_label_upgrade_performed",
        "real_send_candidate_generated",
        "send_ready", "tg_test_group_ready", "tg_sent",
        "prod_state_write", "external_api_called",
        "credentials_read", "next_gate_command_order_enforced",
    ]
    for field in required_result_fields:
        check(f"Result has field '{field}'", field in result,
              f"missing field: {field}")

    # ==================================================================
    # 26. Stage Correct
    # ==================================================================
    print("\n[26] Stage Correct")
    check("stage matches v115o...",
          "v115o_whale_operator_evidence_collection_kit" in result.get("stage", ""),
          f"got: {result.get('stage')}")

    # ==================================================================
    # 27. High Priority Items — Correct Addresses
    # ==================================================================
    print("\n[27] High Priority Items — Correct Addresses")
    high_items = [i for i in items if i["priority"] == "high"]
    check(f"High priority has 2 items", len(high_items) == 2,
          f"got: {len(high_items)}")
    high_addrs = [i["address"] for i in high_items]
    for addr in EXPECTED_LOW_ADDRESSES:
        check(f"Low confidence addr {addr[:10]}... is in high priority",
              addr in high_addrs,
              f"address not found in high priority")

    # ==================================================================
    # 28. Medium Priority Items — Correct Addresses
    # ==================================================================
    print("\n[28] Medium Priority Items — Correct Addresses")
    medium_items = [i for i in items if i["priority"] == "medium"]
    check(f"Medium priority has 2 items", len(medium_items) == 2,
          f"got: {len(medium_items)}")
    medium_addrs = [i["address"] for i in medium_items]
    for addr in EXPECTED_MEDIUM_ADDRESSES:
        check(f"Medium confidence addr {addr[:10]}... is in medium priority",
              addr in medium_addrs,
              f"address not found in medium priority")

    # ==================================================================
    # 29. Preflight Report Critical Finding
    # ==================================================================
    print("\n[29] Preflight Report Content")
    check("Preflight report mentions all addresses blocked",
          "all 4 addresses" in preflight_md.lower() or "4 addresses" in preflight_md.lower(),
          "critical finding not in preflight report")
    check("Preflight report says gate rerun not permitted",
          "gate rerun" in preflight_md.lower() and "NOT" in preflight_md,
          "gate rerun warning not found")
    check("Preflight report says TG test group not accessible",
          "TG" in preflight_md and "NOT" in preflight_md,
          "TG warning not found")
    check("Preflight report says label upgrade not possible",
          "label upgrade" in preflight_md.lower() or "upgrade" in preflight_md.lower(),
          "upgrade warning not found")
    check("Preflight report says fill v115F workbook first",
          "v115f" in preflight_md.lower(),
          "workbook instruction not found")

    # ==================================================================
    # 30. Handoff Content
    # ==================================================================
    print("\n[30] Handoff Content")
    check("Handoff mentions v115O", "v115O" in handoff_md or "v115o" in handoff_md.lower())
    check("Handoff mentions evidence collection kit", "evidence" in handoff_md.lower())
    check("Handoff mentions preflight", "preflight" in handoff_md.lower())
    check("Handoff mentions TG not allowed", "TG" in handoff_md)
    check("Handoff mentions safety", "safety" in handoff_md.lower())
    check("Handoff mentions v115G gate", "v115g" in handoff_md.lower())
    check("Handoff mentions v115L gate", "v115l" in handoff_md.lower())
    check("Handoff mentions v115H gate", "v115h" in handoff_md.lower())
    check("Handoff mentions v115M gate", "v115m" in handoff_md.lower())

    # ==================================================================
    # 31. Count Cross-Check: Result matches Items
    # ==================================================================
    print("\n[31] Count Cross-Check: Result matches Items")
    check(f"result.evidence_collection_items ({result.get('evidence_collection_items')}) matches len(items) ({len(items)})",
          result.get("evidence_collection_items") == len(items))
    check(f"result.preflight_records ({result.get('preflight_records')}) matches len(preflight_decisions) ({len(preflight_decisions)})",
          result.get("preflight_records") == len(preflight_decisions))

    count_high = sum(1 for i in items if i["priority"] == "high")
    check(f"result.high_priority_items ({result.get('high_priority_items')}) matches items ({count_high})",
          result.get("high_priority_items") == count_high)

    count_medium = sum(1 for i in items if i["priority"] == "medium")
    check(f"result.medium_priority_items ({result.get('medium_priority_items')}) matches items ({count_medium})",
          result.get("medium_priority_items") == count_medium)

    count_manual = sum(1 for i in items if i["action_type"] == "manual_attribution_required")
    check(f"result.manual_attribution_required_count ({result.get('manual_attribution_required_count')}) matches items ({count_manual})",
          result.get("manual_attribution_required_count") == count_manual)

    count_corr = sum(1 for i in items if i["action_type"] == "corroboration_required")
    check(f"result.corroboration_required_count ({result.get('corroboration_required_count')}) matches items ({count_corr})",
          result.get("corroboration_required_count") == count_corr)

    count_blocked = sum(1 for d in preflight_decisions if not d["preflight_ready"])
    check(f"result.preflight_blocked_count ({result.get('preflight_blocked_count')}) matches decisions ({count_blocked})",
          result.get("preflight_blocked_count") == count_blocked)

    # ==================================================================
    # 32. CSV Has Required Columns
    # ==================================================================
    print("\n[32] CSV Has Required Columns")
    csv_required_cols = [
        "address", "display_label", "current_confidence", "priority",
        "action_type", "research_goal", "required_evidence_bundle",
        "primary_source_checklist", "secondary_source_checklist",
        "activity_pattern_checklist", "workbook_fields_to_fill",
        "minimum_pass_condition", "next_local_preflight_command",
        "next_gate_commands_after_preflight_pass",
    ]
    for col in csv_required_cols:
        check(f"CSV has column '{col}'",
              col in csv_rows[0] if csv_rows else False,
              f"missing column: {col}")

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
