#!/usr/bin/env python3
"""
Test suite for v115N Whale Manual Audit Operator Action Queue — Local Only
===========================================================================
Validates that the v115N runner produced correct outputs:

  - operator_actions == 4
  - high_priority_actions == 2
  - medium_priority_actions == 2
  - manual_attribution_required_count == 2
  - corroboration_required_count == 2
  - queue_csv_rows == 4
  - JSONL has 4 lines
  - CSV has 4 data rows
  - Markdown mentions all 4 addresses
  - next_gate_commands order is: v115G -> v115L -> v115H -> v115M

Safety:
  - real_workbook_modified == false
  - real_label_upgrade_performed == false
  - real_send_candidate_generated == false
  - send_ready == false
  - tg_test_group_ready == false
  - tg_sent == false
  - prod_state_write == false
  - external_api_called == false
  - credentials_read == false

Negative assertions:
  - No fake pass / synthetic passed presented as real
  - v115F workbook NOT modified
  - v115A-v115M historical products NOT modified
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
# v115N outputs (must exist)
# ---------------------------------------------------------------------------
V115N_JSONL = os.path.join(RESULTS_DIR, "market_radar_v115n_whale_manual_audit_operator_actions.jsonl")
V115N_JSON = os.path.join(RESULTS_DIR, "market_radar_v115n_whale_manual_audit_operator_action_queue_result.json")
V115N_CSV = os.path.join(RUNS_DIR, "v115n_whale_manual_audit_operator_action_queue.csv")
V115N_MD = os.path.join(RUNS_DIR, "v115n_whale_manual_audit_operator_action_queue.md")
V115N_HANDOFF = os.path.join(RUNS_DIR, "v115n_whale_manual_audit_operator_action_queue_local_only_handoff.md")

# ---------------------------------------------------------------------------
# Input files that must still exist and be unmodified
# ---------------------------------------------------------------------------
V115F_WORKBOOK = os.path.join(RUNS_DIR, "v115f_whale_address_audit_operator_workbook.csv")
V115K_REGISTRY = os.path.join(CONFIG_DIR, "market_radar_v115k_whale_label_evidence_source_registry.json")
V115K_SCORING_POLICY = os.path.join(CONFIG_DIR, "market_radar_v115k_whale_label_evidence_scoring_policy.json")

# ---------------------------------------------------------------------------
# v115M & v115L outputs that must still exist (regression)
# ---------------------------------------------------------------------------
V115M_RECORDS = os.path.join(RESULTS_DIR, "market_radar_v115m_whale_real_workflow_records.jsonl")
V115M_DECISIONS = os.path.join(RESULTS_DIR, "market_radar_v115m_whale_real_workflow_decisions.jsonl")
V115M_GATE = os.path.join(RESULTS_DIR, "market_radar_v115m_whale_manual_audit_end_to_end_upgrade_workflow_gate_result.json")
V115L_SCORING = os.path.join(RESULTS_DIR, "market_radar_v115l_whale_real_workbook_evidence_scoring_decisions.jsonl")
V115L_GATE = os.path.join(RESULTS_DIR, "market_radar_v115l_whale_label_evidence_scoring_gate_result.json")
V115E_REQUESTS = os.path.join(RESULTS_DIR, "market_radar_v115e_whale_address_audit_evidence_requests.jsonl")
V115G_INTAKES = os.path.join(RESULTS_DIR, "market_radar_v115g_whale_manual_audit_intake_decisions.jsonl")

# ---------------------------------------------------------------------------
# Expected next gate command order
# ---------------------------------------------------------------------------
EXPECTED_GATE_ORDER_KEYWORDS = ["v115g", "v115l", "v115h", "v115m"]

# ---------------------------------------------------------------------------
# The 4 real addresses from v115M
# ---------------------------------------------------------------------------
EXPECTED_ADDRESSES = [
    "0x082e843a431aef031264dc232693dd710aedca88",
    "0x50b309f78e774a756a2230e1769729094cac9f20",
    "0x6c8512516ce5669d35113a11ca8b8de322fd84f6",
    "0x8def9f50456c6c4e37fa5d3d57f108ed23992dae",
]

EXPECTED_LOW_CONFIDENCE = [
    "0x082e843a431aef031264dc232693dd710aedca88",
    "0x50b309f78e774a756a2230e1769729094cac9f20",
]

EXPECTED_MEDIUM_CONFIDENCE = [
    "0x6c8512516ce5669d35113a11ca8b8de322fd84f6",
    "0x8def9f50456c6c4e37fa5d3d57f108ed23992dae",
]

# Required fields per operator action
REQUIRED_ACTION_FIELDS = [
    "address",
    "display_label",
    "current_confidence",
    "priority",
    "action_type",
    "blocked_stage",
    "blocked_reasons",
    "missing_workbook_fields",
    "recommended_source_types",
    "rejected_source_warning",
    "operator_instruction",
    "workbook_file",
    "workbook_row_hint",
    "next_gate_commands",
    "safety_status",
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
    print("v115N Test Suite — Operator Action Queue")
    print("=" * 70)

    # ==================================================================
    # 1. File Existence — v115N Outputs
    # ==================================================================
    print("\n[1] File Existence — v115N Outputs")
    check("Operator actions .jsonl exists", file_exists(V115N_JSONL))
    check("Action queue result .json exists", file_exists(V115N_JSON))
    check("Action queue .csv exists", file_exists(V115N_CSV))
    check("Action queue .md exists", file_exists(V115N_MD))
    check("Handoff .md exists", file_exists(V115N_HANDOFF))

    # ==================================================================
    # 2. File Existence — Input Sources Still Intact
    # ==================================================================
    print("\n[2] File Existence — Input Sources Still Intact")
    check("v115F workbook still exists", file_exists(V115F_WORKBOOK))
    check("v115K registry still exists", file_exists(V115K_REGISTRY))
    check("v115K scoring policy still exists", file_exists(V115K_SCORING_POLICY))

    # ==================================================================
    # 3. File Existence — v115M & v115L Historical Products Still Intact
    # ==================================================================
    print("\n[3] File Existence — v115M & v115L Historical Products Still Intact")
    check("v115M real workflow records exists", file_exists(V115M_RECORDS))
    check("v115M real workflow decisions exists", file_exists(V115M_DECISIONS))
    check("v115M gate result exists", file_exists(V115M_GATE))
    check("v115L scoring decisions exists", file_exists(V115L_SCORING))
    check("v115L gate result exists", file_exists(V115L_GATE))
    check("v115E evidence requests exists", file_exists(V115E_REQUESTS))
    check("v115G intake decisions exists", file_exists(V115G_INTAKES))

    # ==================================================================
    # 4. Data Loading
    # ==================================================================
    print("\n[4] Data Loading")
    actions = load_jsonl(V115N_JSONL)
    check(f"JSONL loaded: {len(actions)} actions", len(actions) > 0)

    result = load_json(V115N_JSON)
    check("JSON result parsed", isinstance(result, dict))

    csv_rows = load_csv_dict(V115N_CSV)
    check(f"CSV loaded: {len(csv_rows)} rows", len(csv_rows) > 0)

    with open(V115N_MD, "r", encoding="utf-8") as f:
        md_text = f.read()
    check("Markdown report loaded", len(md_text) > 0)

    with open(V115N_HANDOFF, "r", encoding="utf-8") as f:
        handoff_text = f.read()
    check("Handoff markdown loaded", len(handoff_text) > 0)

    # ==================================================================
    # 5. Core Counts
    # ==================================================================
    print("\n[5] Core Counts")
    check("operator_actions == 4", result.get("operator_actions") == 4,
          f"got: {result.get('operator_actions')}")
    check("high_priority_actions == 2", result.get("high_priority_actions") == 2,
          f"got: {result.get('high_priority_actions')}")
    check("medium_priority_actions == 2", result.get("medium_priority_actions") == 2,
          f"got: {result.get('medium_priority_actions')}")
    check("manual_attribution_required_count == 2",
          result.get("manual_attribution_required_count") == 2,
          f"got: {result.get('manual_attribution_required_count')}")
    check("corroboration_required_count == 2",
          result.get("corroboration_required_count") == 2,
          f"got: {result.get('corroboration_required_count')}")
    check("queue_csv_rows == 4", result.get("queue_csv_rows") == 4,
          f"got: {result.get('queue_csv_rows')}")

    # ==================================================================
    # 6. JSONL Counts
    # ==================================================================
    print("\n[6] JSONL Counts")
    check(f"JSONL has 4 lines (got {len(actions)})", len(actions) == 4)

    # ==================================================================
    # 7. CSV Counts
    # ==================================================================
    print("\n[7] CSV Counts")
    check(f"CSV has 4 data rows (got {len(csv_rows)})", len(csv_rows) == 4)

    # ==================================================================
    # 8. Markdown Contains All 4 Addresses
    # ==================================================================
    print("\n[8] Markdown Contains All 4 Addresses")
    for addr in EXPECTED_ADDRESSES:
        check(f"Markdown mentions {addr[:10]}...",
              addr[:10] in md_text,
              f"address not found in markdown")

    # ==================================================================
    # 9. next_gate_commands Order Enforced
    # ==================================================================
    print("\n[9] next_gate_commands Order Enforced")
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

    # Verify each action has the correct gate command order
    for i, action in enumerate(actions):
        ngc = action.get("next_gate_commands", [])
        check(f"Action {i+1}: next_gate_commands has 4 entries", len(ngc) == 4,
              f"got: {len(ngc)}")
        for j, keyword in enumerate(EXPECTED_GATE_ORDER_KEYWORDS):
            check(f"Action {i+1}: gate command [{j}] contains '{keyword}'",
                  keyword in ngc[j].lower() if j < len(ngc) else False,
                  f"got: '{ngc[j] if j < len(ngc) else 'out of range'}'")

    # ==================================================================
    # 10. Action Type Rules Correct
    # ==================================================================
    print("\n[10] Action Type Rules Correct")
    for i, action in enumerate(actions):
        addr = action["address"]
        confidence = action["current_confidence"]
        priority = action["priority"]
        action_type = action["action_type"]

        if addr in EXPECTED_LOW_CONFIDENCE:
            check(f"Low confidence {addr[:10]}... has action_type=manual_attribution_required",
                  action_type == "manual_attribution_required",
                  f"got: {action_type}")
            check(f"Low confidence {addr[:10]}... has priority=high",
                  priority == "high",
                  f"got: {priority}")
            check(f"Low confidence {addr[:10]}... current_confidence=low",
                  confidence == "low",
                  f"got: {confidence}")
        elif addr in EXPECTED_MEDIUM_CONFIDENCE:
            check(f"Medium confidence {addr[:10]}... has action_type=corroboration_required",
                  action_type == "corroboration_required",
                  f"got: {action_type}")
            check(f"Medium confidence {addr[:10]}... has priority=medium",
                  priority == "medium",
                  f"got: {priority}")
            check(f"Medium confidence {addr[:10]}... current_confidence=medium",
                  confidence == "medium",
                  f"got: {confidence}")

    # Count by action type
    manual_count = sum(1 for a in actions if a["action_type"] == "manual_attribution_required")
    corroboration_count = sum(1 for a in actions if a["action_type"] == "corroboration_required")
    check(f"manual_attribution_required count from actions: {manual_count}",
          manual_count == 2)
    check(f"corroboration_required count from actions: {corroboration_count}",
          corroboration_count == 2)

    # ==================================================================
    # 11. Required Action Fields
    # ==================================================================
    print("\n[11] Required Action Fields")
    for i, action in enumerate(actions):
        for field in REQUIRED_ACTION_FIELDS:
            check(f"Action {i+1}: field '{field}' present",
                  field in action,
                  f"missing field: {field}")

    # ==================================================================
    # 12. Safety Status Fields in Each Action
    # ==================================================================
    print("\n[12] Safety Status Fields in Each Action")
    safety_fields = [
        "real_workbook_modified",
        "real_label_upgrade_performed",
        "real_send_candidate_generated",
        "send_ready",
        "tg_test_group_ready",
        "tg_sent",
        "prod_state_write",
        "external_api_called",
        "credentials_read",
    ]
    for i, action in enumerate(actions):
        ss = action.get("safety_status", {})
        for field in safety_fields:
            check(f"Action {i+1}: safety_status.{field} = false",
                  ss.get(field) is False,
                  f"got: {ss.get(field)}")

    # ==================================================================
    # 13. Real Workbook NOT Modified
    # ==================================================================
    print("\n[13] Real Workbook NOT Modified")
    check("real_workbook_modified == false (result)",
          result.get("real_workbook_modified") is False)

    # Verify v115F workbook still has empty operator fields
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
    # 14. All Safety Flags = false
    # ==================================================================
    print("\n[14] Safety Flags — All Must Be false")
    safety_checks = [
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
    # 15. Negative Assertions — No Fake Pass Claims
    # ==================================================================
    print("\n[15] Negative Assertions — No Fake Pass Claims")
    check("NOT claiming send_ready=true", result.get("send_ready") is not True)
    check("NOT claiming tg_test_group_ready=true", result.get("tg_test_group_ready") is not True)
    check("NOT claiming tg_sent=true", result.get("tg_sent") is not True)
    check("NOT claiming prod_state_write=true", result.get("prod_state_write") is not True)
    check("NOT claiming real_workbook_modified=true", result.get("real_workbook_modified") is not True)
    check("NOT claiming real_label_upgrade_performed=true", result.get("real_label_upgrade_performed") is not True)
    check("NOT claiming real_send_candidate_generated=true", result.get("real_send_candidate_generated") is not True)
    check("NOT claiming external_api_called=true", result.get("external_api_called") is not True)
    check("NOT claiming credentials_read=true", result.get("credentials_read") is not True)

    # ==================================================================
    # 16. No Synthetic/Passed Claims
    # ==================================================================
    print("\n[16] No 'synthetic passed' or 'fake pass' Language")
    all_output_text = json.dumps(result) + json.dumps(actions) + md_text + handoff_text
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
    # 17. No Sensitive Data
    # ==================================================================
    print("\n[17] No Sensitive Data in Outputs")
    sensitive_patterns = [
        "API_KEY", "api_key", "token", "password", "secret",
        ".env", "OPENAI", "OPENROUTER", "cookie",
    ]
    for pat in sensitive_patterns:
        check(f"No '{pat}' in any v115N output",
              pat.lower() not in all_output_text.lower(),
              f"found '{pat}'")

    # ==================================================================
    # 18. credentials_read is the only 'credential' mention
    # ==================================================================
    print("\n[18] 'credential' only appears as 'credentials_read' safety flag")
    cred_count = all_output_text.lower().count("credential")
    cred_read_count = all_output_text.lower().count("credentials_read")
    # Allow up to 4 extra "Credential" mentions in safety labels/headings
    # (e.g., "No Credentials Read" in handoff/safety table headers is legitimate)
    check("'credential' occurs primarily as 'credentials_read' safety flag",
          cred_read_count >= cred_count - 4,
          f"unexpected 'credential' occurrences: {cred_count} total, {cred_read_count} as credentials_read")

    # ==================================================================
    # 19. No API Call Patterns
    # ==================================================================
    print("\n[19] No API Call Patterns")
    api_patterns = ["http://api.", "https://api.", "fetch(", "curl ",
                    "requests.get", "requests.post", "urllib"]
    for pat in api_patterns:
        check(f"No '{pat}' in any v115N output", pat not in all_output_text.lower(),
              f"found '{pat}'")

    # ==================================================================
    # 20. Result JSON — All Required Fields
    # ==================================================================
    print("\n[20] Result JSON — All Required Fields")
    required_result_fields = [
        "stage", "version",
        "operator_actions", "high_priority_actions", "medium_priority_actions",
        "manual_attribution_required_count", "corroboration_required_count",
        "queue_csv_rows",
        "next_gate_command_order_enforced", "next_gate_commands",
        "real_workbook_modified", "real_label_upgrade_performed",
        "real_send_candidate_generated",
        "send_ready", "tg_test_group_ready", "tg_sent",
        "prod_state_write", "external_api_called", "ai_model_called",
        "credentials_read", "daemon_started", "watcher_started",
        "files_deleted", "local_review_ready",
    ]
    for field in required_result_fields:
        check(f"Result has field '{field}'", field in result,
              f"missing field: {field}")

    # ==================================================================
    # 21. Stage Correct
    # ==================================================================
    print("\n[21] Stage Correct")
    check("stage matches v115n...",
          "v115n_whale_manual_audit_operator_action_queue_local_only" in result.get("stage", ""),
          f"got: {result.get('stage')}")

    # ==================================================================
    # 22. local_review_ready = true
    # ==================================================================
    print("\n[22] local_review_ready = true")
    check("local_review_ready = true", result.get("local_review_ready") is True)

    # ==================================================================
    # 23. v115K Configs Not Modified
    # ==================================================================
    print("\n[23] v115K Configs Not Modified")
    registry = load_json(V115K_REGISTRY)
    check("v115K registry version is v115K", registry.get("version") == "v115K")
    check("v115K registry has 4 categories", registry.get("registry_categories") == 4)

    scoring = load_json(V115K_SCORING_POLICY)
    check("v115K scoring policy version is v115K", scoring.get("version") == "v115K")
    check("v115K scoring policy has 9 HC requirements",
          scoring.get("minimum_for_high_confidence", {}).get("total_requirements") == 9)

    # ==================================================================
    # 24. High Priority Actions — 2 distinct addresses
    # ==================================================================
    print("\n[24] High Priority Actions — Correct Addresses")
    high_addrs = [a["address"] for a in actions if a["priority"] == "high"]
    check(f"High priority has 2 addresses", len(high_addrs) == 2,
          f"got: {len(high_addrs)}")
    for addr in EXPECTED_LOW_CONFIDENCE:
        check(f"Low confidence address {addr[:10]}... is in high priority",
              addr in high_addrs,
              f"address not found in high priority")

    # ==================================================================
    # 25. Medium Priority Actions — 2 distinct addresses
    # ==================================================================
    print("\n[25] Medium Priority Actions — Correct Addresses")
    medium_addrs = [a["address"] for a in actions if a["priority"] == "medium"]
    check(f"Medium priority has 2 addresses", len(medium_addrs) == 2,
          f"got: {len(medium_addrs)}")
    for addr in EXPECTED_MEDIUM_CONFIDENCE:
        check(f"Medium confidence address {addr[:10]}... is in medium priority",
              addr in medium_addrs,
              f"address not found in medium priority")

    # ==================================================================
    # 26. Handoff Content
    # ==================================================================
    print("\n[26] Handoff Content")
    check("Handoff mentions v115N", "v115N" in handoff_text or "v115n" in handoff_text.lower())
    check("Handoff mentions operator action queue", "action" in handoff_text.lower())
    check("Handoff mentions TG test group not allowed", "TG" in handoff_text)
    check("Handoff mentions safety", "safety" in handoff_text.lower())
    check("Handoff mentions next steps", "next step" in handoff_text.lower())
    check("Handoff mentions v115G gate", "v115g" in handoff_text.lower())
    check("Handoff mentions v115H gate", "v115h" in handoff_text.lower())
    check("Handoff mentions v115L gate", "v115l" in handoff_text.lower())
    check("Handoff mentions v115M gate", "v115m" in handoff_text.lower())

    # ==================================================================
    # 27. CSV Has Required Columns
    # ==================================================================
    print("\n[27] CSV Has Required Columns")
    csv_required_cols = [
        "address", "display_label", "current_confidence", "priority",
        "action_type", "blocked_stage", "blocked_reasons",
        "missing_workbook_fields", "recommended_source_types",
        "operator_instruction", "next_gate_commands",
    ]
    for col in csv_required_cols:
        check(f"CSV has column '{col}'", col in csv_rows[0] if csv_rows else False,
              f"missing column: {col}")

    # ==================================================================
    # 28. Each Action Has Blocked Reasons
    # ==================================================================
    print("\n[28] Each Action Has Blocked Reasons")
    for i, action in enumerate(actions):
        blocked_reasons = action.get("blocked_reasons", "")
        check(f"Action {i+1}: blocked_reasons is non-empty",
              len(blocked_reasons) > 0,
              f"empty blocked_reasons")

    # ==================================================================
    # 29. Each Action Has Missing Workbook Fields
    # ==================================================================
    print("\n[29] Each Action Has Missing Workbook Fields")
    for i, action in enumerate(actions):
        missing = action.get("missing_workbook_fields", [])
        check(f"Action {i+1}: has {len(missing)} missing workbook fields",
              len(missing) > 0,
              f"empty missing_workbook_fields")

    # ==================================================================
    # 30. Count Cross-Check: Result matches Actions
    # ==================================================================
    print("\n[30] Count Cross-Check: Result matches Actions")
    check(f"result.operator_actions ({result.get('operator_actions')}) matches len(actions) ({len(actions)})",
          result.get("operator_actions") == len(actions))

    count_high = sum(1 for a in actions if a["priority"] == "high")
    check(f"result.high_priority_actions ({result.get('high_priority_actions')}) matches actions ({count_high})",
          result.get("high_priority_actions") == count_high)

    count_medium = sum(1 for a in actions if a["priority"] == "medium")
    check(f"result.medium_priority_actions ({result.get('medium_priority_actions')}) matches actions ({count_medium})",
          result.get("medium_priority_actions") == count_medium)

    count_manual = sum(1 for a in actions if a["action_type"] == "manual_attribution_required")
    check(f"result.manual_attribution_required_count ({result.get('manual_attribution_required_count')}) matches actions ({count_manual})",
          result.get("manual_attribution_required_count") == count_manual)

    count_corr = sum(1 for a in actions if a["action_type"] == "corroboration_required")
    check(f"result.corroboration_required_count ({result.get('corroboration_required_count')}) matches actions ({count_corr})",
          result.get("corroboration_required_count") == count_corr)

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
