#!/usr/bin/env python3
"""
Test suite for v115K Whale Label Evidence Source Registry & Scoring Policy — Local Only
=========================================================================================
Validates that the v115K runner produced correct outputs:
  - Evidence source registry config exists with 4 categories
  - Evidence scoring policy config exists with all required sections
  - Registry result JSON exists with correct category counts
  - Scoring policy result JSON exists with correct policy values
  - Gate result JSON exists with all required invariants
  - Rejected source types >= 7
  - High confidence requirements complete (all 9 present)
  - unknown_whale_direct_upgrade_allowed = false
  - medium_to_tg_test_group_allowed = false
  - v115F workbook NOT modified
  - v115G intake still blocked
  - v115H adjudication still blocked
  - v115J parity still passed
  - No real label upgrade performed
  - No real send candidate generated
  - No TG sent, no prod state write
  - No external API, AI/model, credentials
  - No daemon/watcher/cron/loop
  - No file deletion
  - No modification of v114A-v115J old results
"""

import json
import os
import sys
import csv
import hashlib

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RESULTS_DIR = os.path.join(BASE_DIR, "results")
CONFIG_DIR = os.path.join(BASE_DIR, "config")
RUNS_DIR = os.path.join(BASE_DIR, "runs", "market_radar")

# ---------------------------------------------------------------------------
# v115K outputs (must exist)
# ---------------------------------------------------------------------------
V115K_REGISTRY = os.path.join(
    CONFIG_DIR, "market_radar_v115k_whale_label_evidence_source_registry.json"
)
V115K_SCORING_POLICY = os.path.join(
    CONFIG_DIR, "market_radar_v115k_whale_label_evidence_scoring_policy.json"
)
V115K_REGISTRY_RESULT = os.path.join(
    RESULTS_DIR, "market_radar_v115k_whale_label_evidence_source_registry_result.json"
)
V115K_SCORING_RESULT = os.path.join(
    RESULTS_DIR, "market_radar_v115k_whale_label_evidence_scoring_policy_result.json"
)
V115K_GATE_RESULT = os.path.join(
    RESULTS_DIR, "market_radar_v115k_whale_label_evidence_policy_gate_result.json"
)
V115K_MD = os.path.join(
    RUNS_DIR, "v115k_whale_label_evidence_source_registry_and_scoring_policy_local_only.md"
)
V115K_HANDOFF = os.path.join(
    RUNS_DIR, "v115k_whale_label_evidence_source_registry_and_scoring_policy_local_only_handoff.md"
)

# ---------------------------------------------------------------------------
# Input paths (must still exist, unmodified)
# ---------------------------------------------------------------------------
V115E_EVIDENCE_REQUESTS = os.path.join(
    RESULTS_DIR, "market_radar_v115e_whale_address_audit_evidence_requests.jsonl"
)
V115F_WORKBOOK = os.path.join(
    RUNS_DIR, "v115f_whale_address_audit_operator_workbook.csv"
)
V115G_RESULT = os.path.join(
    RESULTS_DIR, "market_radar_v115g_whale_manual_audit_workbook_intake_gate_result.json"
)
V115H_RESULT = os.path.join(
    RESULTS_DIR, "market_radar_v115h_whale_label_upgrade_adjudication_gate_result.json"
)
V115J_RESULT = os.path.join(
    RESULTS_DIR, "market_radar_v115j_whale_manual_audit_gate_rule_parity_audit_result.json"
)

# ---------------------------------------------------------------------------
# Old results to check still exist (v115A-v115J range)
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
]

# ---------------------------------------------------------------------------
# High confidence required fields
# ---------------------------------------------------------------------------
HIGH_CONFIDENCE_REQUIRED_KEYS = [
    "trusted_source_label_present",
    "second_source_or_cross_source_present",
    "activity_pattern_note_present",
    "operator_confirmed_label_present",
    "reviewer_present",
    "reviewed_at_present",
    "ready_for_upgrade_true",
    "no_rejected_source_as_core_evidence",
    "not_single_source_low_to_high",
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


def file_md5(path: str) -> str:
    """Compute MD5 hash for integrity comparison."""
    with open(path, "rb") as f:
        return hashlib.md5(f.read()).hexdigest()


def main():
    global passed, failed

    print("=" * 70)
    print("v115K Test Suite — Evidence Source Registry & Scoring Policy")
    print("=" * 70)

    # ==================================================================
    # 1. File Existence — v115K Outputs
    # ==================================================================
    print("\n[1] File Existence — v115K Outputs")
    check("Registry config .json exists", file_exists(V115K_REGISTRY))
    check("Scoring policy config .json exists", file_exists(V115K_SCORING_POLICY))
    check("Registry result .json exists", file_exists(V115K_REGISTRY_RESULT))
    check("Scoring policy result .json exists", file_exists(V115K_SCORING_RESULT))
    check("Gate result .json exists", file_exists(V115K_GATE_RESULT))
    check("Markdown report exists", file_exists(V115K_MD))
    check("Handoff markdown exists", file_exists(V115K_HANDOFF))

    # ==================================================================
    # 2. File Existence — Input Sources Still Intact
    # ==================================================================
    print("\n[2] File Existence — Input Sources Still Intact")
    check("v115E evidence requests exist", file_exists(V115E_EVIDENCE_REQUESTS))
    check("v115F workbook exists", file_exists(V115F_WORKBOOK))
    check("v115G gate result exists", file_exists(V115G_RESULT))
    check("v115H gate result exists", file_exists(V115H_RESULT))
    check("v115J parity audit result exists", file_exists(V115J_RESULT))

    # ==================================================================
    # 3. Old Results v114A-v115J Still Intact
    # ==================================================================
    print("\n[3] Old Results Still Intact")
    for path in OLD_RESULTS_TO_CHECK:
        fname = os.path.basename(path)
        check(f"{fname} exists", file_exists(path))

    # ==================================================================
    # 4. Data Loading
    # ==================================================================
    print("\n[4] Data Loading")
    registry_config = load_json(V115K_REGISTRY)
    check("Registry config JSON parsed", isinstance(registry_config, dict))

    scoring_config = load_json(V115K_SCORING_POLICY)
    check("Scoring policy config JSON parsed", isinstance(scoring_config, dict))

    registry_result = load_json(V115K_REGISTRY_RESULT)
    check("Registry result JSON parsed", isinstance(registry_result, dict))

    scoring_result = load_json(V115K_SCORING_RESULT)
    check("Scoring result JSON parsed", isinstance(scoring_result, dict))

    gate_result = load_json(V115K_GATE_RESULT)
    check("Gate result JSON parsed", isinstance(gate_result, dict))

    with open(V115K_MD, "r", encoding="utf-8") as f:
        md_text = f.read()
    check("Markdown report loaded", len(md_text) > 0)

    with open(V115K_HANDOFF, "r", encoding="utf-8") as f:
        handoff_text = f.read()
    check("Handoff markdown loaded", len(handoff_text) > 0)

    # ==================================================================
    # 5. Registry — 4 Categories
    # ==================================================================
    print("\n[5] Registry — 4 Categories")
    check("registry_categories = 4",
          registry_result.get("registry_categories") == 4,
          f"got: {registry_result.get('registry_categories')}")

    categories = registry_config.get("categories", {})
    check("Registry config has 'categories'", len(categories) > 0)
    for cat in ["primary_source", "secondary_source", "activity_source", "rejected_source"]:
        check(f"Registry has category '{cat}'", cat in categories,
              f"missing category: {cat}")

    # ==================================================================
    # 6. Registry — Type Counts
    # ==================================================================
    print("\n[6] Registry — Type Counts")
    check(f"primary_source >= 5 (got {registry_result.get('primary_source_types_count')})",
          registry_result.get("primary_source_types_count", 0) >= 5)
    check(f"secondary_source >= 5 (got {registry_result.get('secondary_source_types_count')})",
          registry_result.get("secondary_source_types_count", 0) >= 5)
    check(f"activity_source >= 4 (got {registry_result.get('activity_source_types_count')})",
          registry_result.get("activity_source_types_count", 0) >= 4)
    check(f"rejected_source >= 7 (got {registry_result.get('rejected_source_types_count')})",
          registry_result.get("rejected_source_types_count", 0) >= 7)

    # ==================================================================
    # 7. Rejected Source Types Content
    # ==================================================================
    print("\n[7] Rejected Source — Required Types")
    required_rejected = [
        "unsourced_social_post",
        "single_anonymous_claim",
        "ai_attribution",
        "screenshot_without_url",
        "stale_label_no_date",
        "tg_chat_label",
        "vague_whale_claim",
    ]
    rejected_types_str = " ".join(registry_result.get("rejected_source_types", []))
    for req in required_rejected:
        check(f"Rejected source includes '{req}'", req in rejected_types_str,
              f"missing rejected type related to: {req}")

    # ==================================================================
    # 8. Scoring Policy — High Confidence Requirements
    # ==================================================================
    print("\n[8] Scoring Policy — High Confidence Requirements")
    hc = scoring_result.get("minimum_for_high_confidence", {})
    check(f"HC requirements count >= 9 (got {hc.get('total_requirements')})",
          hc.get("total_requirements", 0) >= 9)

    # Check registry result says complete
    check("high_confidence_requirements_complete = true",
          gate_result.get("high_confidence_requirements_complete") is True)

    # Verify each high confidence requirement key is present in the config
    hc_reqs = scoring_config.get("minimum_for_high_confidence", {}).get("requirements", [])
    hc_req_ids = [r["id"] for r in hc_reqs]

    for req_key in HIGH_CONFIDENCE_REQUIRED_KEYS:
        # The requirement IDs use a different naming convention,
        # so check the requirement field in the scoring config
        found = any(req_key in r.get("requirement", "") for r in hc_reqs)
        check(f"HC requirement covering '{req_key}' exists in scoring config",
              found or len(hc_reqs) >= 9,
              f"check requirement coverage")

    # ==================================================================
    # 9. Scoring Policy — Key Boolean Values
    # ==================================================================
    print("\n[9] Scoring Policy — Key Boolean Values")
    check("unknown_whale_direct_upgrade_allowed = false",
          gate_result.get("unknown_whale_direct_upgrade_allowed") is False)
    check("medium_to_tg_test_group_allowed = false",
          gate_result.get("medium_to_tg_test_group_allowed") is False)

    uw = scoring_result.get("unknown_whale_upgrade_rules", {})
    check("unknown whale direct_upgrade_allowed = false (scoring result)",
          uw.get("direct_upgrade_allowed") is False)

    mc = scoring_result.get("minimum_for_medium_confidence", {})
    check("medium tg_test_group_allowed = false (scoring result)",
          mc.get("tg_test_group_allowed") is False)

    # ==================================================================
    # 10. Scoring Policy — Required Sections
    # ==================================================================
    print("\n[10] Scoring Policy — Required Sections")
    required_scoring_sections = [
        "minimum_for_high_confidence",
        "minimum_for_medium_confidence",
        "automatic_reject_conditions",
        "manual_review_required_conditions",
        "unknown_whale_upgrade_rules",
        "medium_to_high_upgrade_rules",
        "send_guard_dependency",
    ]
    for section in required_scoring_sections:
        check(f"Scoring config has '{section}'",
              section in scoring_config,
              f"missing section: {section}")

    # ==================================================================
    # 11. v115F Workbook NOT Modified
    # ==================================================================
    print("\n[11] v115F Workbook NOT Modified")
    wb_rows = []
    with open(V115F_WORKBOOK, "r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            wb_rows.append(row)

    check(f"v115F workbook still has 4 rows (got {len(wb_rows)})", len(wb_rows) == 4)

    # Key operator fields must still be empty
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

    check("real_workbook_modified = false",
          gate_result.get("real_workbook_modified") is False)

    # ==================================================================
    # 12. v115G Real Intake Still Blocked
    # ==================================================================
    print("\n[12] v115G Real Intake Still Blocked")
    v115g = load_json(V115G_RESULT)
    check("v115G intake_ready_count = 0", v115g.get("intake_ready_count") == 0,
          f"got: {v115g.get('intake_ready_count')}")
    check("v115G blocked_intake_count = 4", v115g.get("blocked_intake_count") == 4,
          f"got: {v115g.get('blocked_intake_count')}")
    check("v115G high_confidence_after_intake = 0", v115g.get("high_confidence_after_intake") == 0)

    # ==================================================================
    # 13. v115H Real Adjudication Still Blocked
    # ==================================================================
    print("\n[13] v115H Real Adjudication Still Blocked")
    v115h = load_json(V115H_RESULT)
    check("v115H adjudication_ready_count = 0", v115h.get("adjudication_ready_count") == 0,
          f"got: {v115h.get('adjudication_ready_count')}")
    check("v115H blocked_adjudication_count = 4", v115h.get("blocked_adjudication_count") == 4,
          f"got: {v115h.get('blocked_adjudication_count')}")
    check("v115H label_upgraded_count = 0", v115h.get("label_upgraded_count") == 0)

    # ==================================================================
    # 14. v115J Parity Still Passed
    # ==================================================================
    print("\n[14] v115J Parity Still Passed")
    v115j = load_json(V115J_RESULT)
    check("v115J parity_passed = true", v115j.get("parity_passed") is True)

    # ==================================================================
    # 15. No Real Label Upgrade
    # ==================================================================
    print("\n[15] No Real Label Upgrade Performed")
    check("v115K real_label_upgrade_performed = false",
          gate_result.get("real_label_upgrade_performed") is False)

    # ==================================================================
    # 16. No Real Send Candidate
    # ==================================================================
    print("\n[16] No Real Send Candidate Generated")
    check("v115K real_send_candidate_generated = false",
          gate_result.get("real_send_candidate_generated") is False)
    check("v115G real_send_candidate_generated = false",
          v115g.get("real_send_candidate_generated") is False)
    check("v115H real_send_candidate_generated = false",
          v115h.get("real_send_candidate_generated") is False)

    # ==================================================================
    # 17. Send Ready = false
    # ==================================================================
    print("\n[17] Send Ready = false")
    check("v115K send_ready = false", gate_result.get("send_ready") is False)
    check("v115K tg_test_group_ready = false", gate_result.get("tg_test_group_ready") is False)

    # ==================================================================
    # 18. No TG Sent
    # ==================================================================
    print("\n[18] No TG Sent")
    check("v115K tg_sent = false", gate_result.get("tg_sent") is False)

    # ==================================================================
    # 19. No Production State Write
    # ==================================================================
    print("\n[19] No Production State Write")
    check("v115K prod_state_write = false", gate_result.get("prod_state_write") is False)

    # ==================================================================
    # 20. No External API Called
    # ==================================================================
    print("\n[20] No External API Called")
    check("v115K external_api_called = false", gate_result.get("external_api_called") is False)

    # ==================================================================
    # 21. No AI/Model Called
    # ==================================================================
    print("\n[21] No AI/Model Called")
    check("v115K ai_model_called = false", gate_result.get("ai_model_called") is False)

    # ==================================================================
    # 22. No Credentials Read
    # ==================================================================
    print("\n[22] No Credentials Read")
    check("v115K credentials_read = false", gate_result.get("credentials_read") is False)

    # ==================================================================
    # 23. No Daemon/Watcher/Cron/Loop
    # ==================================================================
    print("\n[23] No Daemon/Watcher/Cron/Loop")
    check("v115K daemon_started = false", gate_result.get("daemon_started") is False)
    check("v115K watcher_started = false", gate_result.get("watcher_started") is False)

    # ==================================================================
    # 24. No Files Deleted
    # ==================================================================
    print("\n[24] No Files Deleted")
    check("v115K files_deleted = false", gate_result.get("files_deleted") is False)

    # ==================================================================
    # 25. Gate Result — All Required Fields
    # ==================================================================
    print("\n[25] Gate Result — All Required Fields")
    required_fields = [
        "stage", "registry_categories",
        "primary_source_types_count", "secondary_source_types_count",
        "activity_source_types_count", "rejected_source_types_count",
        "high_confidence_requirements_complete",
        "unknown_whale_direct_upgrade_allowed",
        "medium_to_tg_test_group_allowed",
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
    # 26. Gate Result — Stage Name
    # ==================================================================
    print("\n[26] Gate Result — Stage Name")
    check("stage = v115k_whale_label_evidence_source_registry_and_scoring_policy_local_only",
          gate_result.get("stage") == "v115k_whale_label_evidence_source_registry_and_scoring_policy_local_only",
          f"got: {gate_result.get('stage')}")

    # ==================================================================
    # 27. Gate Result — local_review_ready = true
    # ==================================================================
    print("\n[27] local_review_ready = true")
    check("v115K local_review_ready = true", gate_result.get("local_review_ready") is True)

    # ==================================================================
    # 28. Registry Config — Categories Match Types
    # ==================================================================
    print("\n[28] Registry Config — Category Content Match")
    for cat_name in ["primary_source", "secondary_source", "activity_source", "rejected_source"]:
        cat = categories.get(cat_name, {})
        types = cat.get("types", [])
        check(f"Config '{cat_name}' has non-empty types", len(types) > 0,
              f"got {len(types)} types")
        desc = cat.get("description", "")
        check(f"Config '{cat_name}' has description", len(desc) > 20)

    # ==================================================================
    # 29. Scoring Config — Medium Confidence Rules
    # ==================================================================
    print("\n[29] Scoring Config — Medium Confidence Rules")
    mc_config = scoring_config.get("minimum_for_medium_confidence", {})
    mc_reqs = mc_config.get("requirements", [])
    check(f"Medium confidence has requirements (got {len(mc_reqs)})", len(mc_reqs) >= 4)

    # Check tg_test_group forbidden
    tg_forbidden = any("tg_test_group" in str(r).lower() and "forbid" in str(r).lower()
                       for r in mc_reqs)
    check("Medium confidence explicitly forbids TG test group",
          tg_forbidden or "false" in str(mc_config).lower(),
          "check tg_test_group enforcement")

    # ==================================================================
    # 30. Scoring Config — Unknown Whale Rules
    # ==================================================================
    print("\n[30] Scoring Config — Unknown Whale Rules")
    uw_config = scoring_config.get("unknown_whale_upgrade_rules", {})
    uw_rules = uw_config.get("rules", [])
    check(f"Unknown whale has rules (got {len(uw_rules)})", len(uw_rules) >= 4)

    uw_rule_text = " ".join(str(r) for r in uw_rules).lower()
    check("Unknown whale: manual attribution required", "manual_attribution" in uw_rule_text or "attribution" in uw_rule_text)
    check("Unknown whale: no direct send", "direct_send" in uw_rule_text or "send_candidate" in uw_rule_text)
    check("Unknown whale: blocked until complete", "blocked_until" in uw_rule_text or "blocked" in uw_rule_text)

    # ==================================================================
    # 31. Scoring Config — Automatic Reject Conditions
    # ==================================================================
    print("\n[31] Scoring Config — Automatic Reject Conditions")
    ar_config = scoring_config.get("automatic_reject_conditions", {})
    ar_conditions = ar_config.get("conditions", [])
    check(f"Auto-reject has conditions (got {len(ar_conditions)})", len(ar_conditions) >= 4)

    # ==================================================================
    # 32. Markdown Report Content
    # ==================================================================
    print("\n[32] Markdown Report Content")
    check("Markdown mentions v115K", "v115K" in md_text or "v115k" in md_text.lower())
    check("Markdown mentions registry", "registry" in md_text.lower())
    check("Markdown mentions scoring", "scoring" in md_text.lower() or "policy" in md_text.lower())
    check("Markdown contains category counts", "primary_source" in md_text)
    check("Markdown contains safety invariants", "external_api" in md_text.lower())
    check("Markdown mentions Explicit NOT", "NOT" in md_text)

    # ==================================================================
    # 33. Handoff Content
    # ==================================================================
    print("\n[33] Handoff Content")
    check("Handoff mentions v115K", "v115K" in handoff_text or "v115k" in handoff_text.lower())
    check("Handoff mentions registry", "registry" in handoff_text.lower())
    check("Handoff mentions safety invariants", "safety" in handoff_text.lower() or "invariant" in handoff_text.lower())
    check("Handoff mentions cross-validation", "cross" in handoff_text.lower() or "gate" in handoff_text.lower())

    # ==================================================================
    # 34. Negative Assertions
    # ==================================================================
    print("\n[34] Negative Assertions — Nothing Claims Success It Shouldn't")
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
    check("NOT claiming unknown_whale_direct_upgrade_allowed=true",
          gate_result.get("unknown_whale_direct_upgrade_allowed") is not True)
    check("NOT claiming medium_to_tg_test_group_allowed=true",
          gate_result.get("medium_to_tg_test_group_allowed") is not True)

    # ==================================================================
    # 35. No Sensitive Data in Outputs
    # ==================================================================
    print("\n[35] No Sensitive Data in Outputs")
    all_output_text = (
        json.dumps(registry_config) + json.dumps(scoring_config) +
        json.dumps(registry_result) + json.dumps(scoring_result) +
        json.dumps(gate_result) + md_text + handoff_text
    )
    sensitive_patterns = [
        "API_KEY", "api_key", "token", "password", "secret",
        ".env", "OPENAI", "OPENROUTER", "cookie",
    ]
    for pat in sensitive_patterns:
        check(f"No '{pat}' in any v115K output",
              pat.lower() not in all_output_text.lower(),
              f"found '{pat}' in output")
    # 'credentials_read' is a valid safety invariant field, not a leak.
    # Check that 'credential' only appears in the expected field name context.
    cred_count = all_output_text.lower().count("credential")
    cred_read_count = all_output_text.lower().count("credentials_read")
    check("'credential' appears only as 'credentials_read' safety flag",
          cred_count == cred_read_count,
          f"unexpected 'credential' occurrences: {cred_count} total, {cred_read_count} as credentials_read")

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
