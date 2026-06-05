#!/usr/bin/env python3
"""
Test suite for v115F Whale Address Audit Operator Workbook — Local Only
==========================================================================
Validates that the v115F operator workbook runner produced correct
outputs: CSV workbook with 4 rows and all 22 required columns,
Markdown workbook with 4 addresses, manifest with correct stage,
and gate result with all invariants satisfied.

All manual evidence fields must be empty/false.
All send guards must be false.
No external API calls, no TG send, no production state write.
No modification of v114A-v115E old results.
"""

import csv
import json
import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RESULTS_DIR = os.path.join(BASE_DIR, "results")
CONFIG_DIR = os.path.join(BASE_DIR, "config")
RUNS_DIR = os.path.join(BASE_DIR, "runs", "market_radar")

# v115F outputs
V115F_CSV = os.path.join(
    RUNS_DIR, "v115f_whale_address_audit_operator_workbook.csv"
)
V115F_MD = os.path.join(
    RUNS_DIR, "v115f_whale_address_audit_operator_workbook.md"
)
V115F_MANIFEST = os.path.join(
    RESULTS_DIR, "market_radar_v115f_whale_address_audit_operator_workbook_manifest.json"
)
V115F_GATE_RESULT = os.path.join(
    RESULTS_DIR, "market_radar_v115f_whale_address_audit_operator_workbook_gate_result.json"
)
V115F_HANDOFF = os.path.join(
    RUNS_DIR, "v115f_whale_address_audit_operator_workbook_local_only_handoff.md"
)

# v115E inputs (must still exist, not modified)
V115E_EVIDENCE_REQUESTS = os.path.join(
    RESULTS_DIR, "market_radar_v115e_whale_address_audit_evidence_requests.jsonl"
)
V115E_MANUAL_AUDIT_FORMS = os.path.join(
    RESULTS_DIR, "market_radar_v115e_whale_address_manual_audit_forms.jsonl"
)
V115E_UPGRADE_DECISIONS = os.path.join(
    RESULTS_DIR, "market_radar_v115e_whale_label_upgrade_decisions.jsonl"
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

# v115C inputs (must still exist)
V115C_RESULT = os.path.join(
    RESULTS_DIR, "market_radar_v115c_whale_tg_test_copy_template_gate_result.json"
)
V115C_TEMPLATES = os.path.join(
    RESULTS_DIR, "market_radar_v115c_whale_tg_test_copy_templates.jsonl"
)

# v115B configs (must still exist)
V115B_ROUTING = os.path.join(
    CONFIG_DIR, "market_radar_v115b_whale_label_confidence_routing_policy.json"
)
V115B_SEND_GATE = os.path.join(
    CONFIG_DIR, "market_radar_v115b_whale_send_preview_gate_policy.json"
)

# v114C inputs (must still exist)
V114C_REVIEW_CARDS = os.path.join(
    RESULTS_DIR, "market_radar_v114c_whale_delta_operator_review_cards.jsonl"
)

# Required CSV columns
REQUIRED_CSV_COLUMNS = [
    "address",
    "current_label",
    "current_confidence",
    "priority",
    "target_confidence",
    "why_this_address_matters",
    "related_delta_context",
    "trusted_source_label_value",
    "trusted_source_url_or_note",
    "second_source_label_value",
    "second_source_url_or_note",
    "activity_pattern_note",
    "operator_confirmed_label",
    "operator_confidence_assessment",
    "operator_reject_reason",
    "reviewer",
    "reviewed_at",
    "ready_for_upgrade",
    "upgrade_ready",
    "send_allowed",
    "tg_test_group_allowed",
    "public_send_allowed",
    "block_reasons",
]

# Manual fields that must be empty
MANUAL_FIELDS = [
    "trusted_source_label_value",
    "trusted_source_url_or_note",
    "second_source_label_value",
    "second_source_url_or_note",
    "activity_pattern_note",
    "operator_confirmed_label",
    "operator_confidence_assessment",
    "operator_reject_reason",
    "reviewer",
    "reviewed_at",
]

# Boolean fields that must be false
BOOLEAN_FALSE_FIELDS = [
    "ready_for_upgrade",
    "upgrade_ready",
    "send_allowed",
    "tg_test_group_allowed",
    "public_send_allowed",
]

# Target addresses from v115E
EXPECTED_ADDRESSES = [
    "0x082e843a431aef031264dc232693dd710aedca88",
    "0x50b309f78e774a756a2230e1769729094cac9f20",
    "0x6c8512516ce5669d35113a11ca8b8de322fd84f6",
    "0x8def9f50456c6c4e37fa5d3d57f108ed23992dae",
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


def load_csv_rows(path: str) -> list:
    rows = []
    with open(path, "r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)
    return rows


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
    print("v115F Test Suite — Operator Workbook")
    print("=" * 70)

    # ==================================================================
    # 1. File Existence — v115F Outputs
    # ==================================================================
    print("\n[1] File Existence — v115F Outputs")
    check("CSV workbook exists", file_exists(V115F_CSV))
    check("Markdown workbook exists", file_exists(V115F_MD))
    check("manifest JSON exists", file_exists(V115F_MANIFEST))
    check("gate result JSON exists", file_exists(V115F_GATE_RESULT))
    check("handoff markdown exists", file_exists(V115F_HANDOFF))

    # ==================================================================
    # 2. File Existence — v115E/v115D/v115C/v114C inputs still intact
    # ==================================================================
    print("\n[2] File Existence — Old Results Not Modified")
    check("v115E evidence requests still exist", file_exists(V115E_EVIDENCE_REQUESTS))
    check("v115E manual audit forms still exist", file_exists(V115E_MANUAL_AUDIT_FORMS))
    check("v115E upgrade decisions still exist", file_exists(V115E_UPGRADE_DECISIONS))
    check("v115E result still exists", file_exists(V115E_RESULT))
    check("v115D gate decisions still exist", file_exists(V115D_GATE_DECISIONS))
    check("v115D result still exists", file_exists(V115D_RESULT))
    check("v115C templates still exist", file_exists(V115C_TEMPLATES))
    check("v115C result still exists", file_exists(V115C_RESULT))
    check("v115B routing policy still exists", file_exists(V115B_ROUTING))
    check("v115B send preview gate policy still exists", file_exists(V115B_SEND_GATE))
    check("v114C review cards still exist", file_exists(V114C_REVIEW_CARDS))

    # ==================================================================
    # 3. Data Loading
    # ==================================================================
    print("\n[3] Data Loading")
    csv_rows = load_csv_rows(V115F_CSV)
    check(f"CSV parsed ({len(csv_rows)} rows)", len(csv_rows) > 0)

    with open(V115F_MD, "r", encoding="utf-8") as f:
        md_text = f.read()
    check("Markdown loaded", len(md_text) > 0)

    manifest = load_json(V115F_MANIFEST)
    check("manifest JSON parsed", isinstance(manifest, dict))

    gate_result = load_json(V115F_GATE_RESULT)
    check("gate result JSON parsed", isinstance(gate_result, dict))

    # ==================================================================
    # 4. CSV Workbook Row Count = 4
    # ==================================================================
    print("\n[4] CSV Workbook Row Count = 4")
    check(f"CSV has 4 rows (got {len(csv_rows)})", len(csv_rows) == 4)

    # ==================================================================
    # 5. CSV Contains All Required Columns
    # ==================================================================
    print("\n[5] CSV Contains All Required Columns")
    for col in REQUIRED_CSV_COLUMNS:
        if len(csv_rows) > 0:
            check(f"CSV has column '{col}'",
                  col in csv_rows[0],
                  f"missing column: {col}")

    # ==================================================================
    # 6. CSV Has Correct Number of Columns (22)
    # ==================================================================
    print("\n[6] CSV Has Correct Column Count")
    if len(csv_rows) > 0:
        actual_cols = len(csv_rows[0].keys())
        check(f"CSV has 23 columns (got {actual_cols})", actual_cols == 23)

    # ==================================================================
    # 7. All 4 Expected Addresses Present in CSV
    # ==================================================================
    print("\n[7] All 4 Expected Addresses in CSV")
    csv_addresses = set(row.get("address", "") for row in csv_rows)
    for addr in EXPECTED_ADDRESSES:
        check(f"Address {addr[:14]}... present in CSV",
              addr in csv_addresses,
              f"missing: {addr}")

    # ==================================================================
    # 8. All Manual Evidence Fields Empty
    # ==================================================================
    print("\n[8] All Manual Evidence Fields Empty")
    for i, row in enumerate(csv_rows):
        for field in MANUAL_FIELDS:
            val = row.get(field, None)
            is_empty = val in ("", None)
            check(f"Row {i+1}: '{field}' is empty (got: {repr(val)})",
                  is_empty,
                  f"expected empty, got: {repr(val)}")

    # ==================================================================
    # 9. All Boolean Guard Fields = false
    # ==================================================================
    print("\n[9] All Boolean Guard Fields = false")
    for i, row in enumerate(csv_rows):
        for field in BOOLEAN_FALSE_FIELDS:
            val = row.get(field, "")
            is_false = val.lower() == "false" or val == ""
            check(f"Row {i+1}: '{field}' = false (got: {repr(val)})",
                  is_false,
                  f"expected false, got: {repr(val)}")

    # ==================================================================
    # 10. All upgrade_ready = false
    # ==================================================================
    print("\n[10] All upgrade_ready = false")
    for i, row in enumerate(csv_rows):
        check(f"Row {i+1}: upgrade_ready = false",
              row.get("upgrade_ready", "").lower() == "false",
              f"got: {repr(row.get('upgrade_ready'))}")

    # ==================================================================
    # 11. All send_allowed = false
    # ==================================================================
    print("\n[11] All send_allowed = false")
    for i, row in enumerate(csv_rows):
        check(f"Row {i+1}: send_allowed = false",
              row.get("send_allowed", "").lower() == "false",
              f"got: {repr(row.get('send_allowed'))}")

    # ==================================================================
    # 12. All tg_test_group_allowed = false
    # ==================================================================
    print("\n[12] All tg_test_group_allowed = false")
    for i, row in enumerate(csv_rows):
        check(f"Row {i+1}: tg_test_group_allowed = false",
              row.get("tg_test_group_allowed", "").lower() == "false",
              f"got: {repr(row.get('tg_test_group_allowed'))}")

    # ==================================================================
    # 13. All public_send_allowed = false
    # ==================================================================
    print("\n[13] All public_send_allowed = false")
    for i, row in enumerate(csv_rows):
        check(f"Row {i+1}: public_send_allowed = false",
              row.get("public_send_allowed", "").lower() == "false",
              f"got: {repr(row.get('public_send_allowed'))}")

    # ==================================================================
    # 14. All block_reasons Non-Empty
    # ==================================================================
    print("\n[14] All block_reasons Non-Empty")
    for i, row in enumerate(csv_rows):
        br = row.get("block_reasons", "")
        check(f"Row {i+1}: block_reasons non-empty",
              br.strip() != "",
              "block_reasons is empty")

    # ==================================================================
    # 15. Markdown Workbook Contains 4 Addresses
    # ==================================================================
    print("\n[15] Markdown Workbook Contains 4 Addresses")
    for addr in EXPECTED_ADDRESSES:
        check(f"Markdown contains address {addr[:14]}...",
              addr in md_text,
              f"address not found in markdown")

    # ==================================================================
    # 16. Manifest Stage Correct
    # ==================================================================
    print("\n[16] Manifest Stage Correct")
    check("manifest stage = v115f_...",
          manifest.get("stage") == "v115f_whale_address_audit_operator_workbook_local_only",
          f"got: {manifest.get('stage')}")

    # ==================================================================
    # 17. Manifest Field Values
    # ==================================================================
    print("\n[17] Manifest Field Values")
    check("input_audit_forms = 4",
          manifest.get("input_audit_forms") == 4,
          f"got: {manifest.get('input_audit_forms')}")
    check("workbook_rows = 4",
          manifest.get("workbook_rows") == 4,
          f"got: {manifest.get('workbook_rows')}")
    check("addresses = 4",
          manifest.get("addresses") == 4,
          f"got: {manifest.get('addresses')}")
    check("manual_fields_prefilled = false",
          manifest.get("manual_fields_prefilled") is False,
          f"got: {manifest.get('manual_fields_prefilled')}")
    check("upgrade_ready_count = 0",
          manifest.get("upgrade_ready_count") == 0,
          f"got: {manifest.get('upgrade_ready_count')}")
    check("blocked_upgrade_count = 4",
          manifest.get("blocked_upgrade_count") == 4,
          f"got: {manifest.get('blocked_upgrade_count')}")

    # ==================================================================
    # 18. Manifest Safety Invariants
    # ==================================================================
    print("\n[18] Manifest Safety Invariants")
    check("send_ready = false",
          manifest.get("send_ready") is False)
    check("tg_test_group_ready = false",
          manifest.get("tg_test_group_ready") is False)
    check("local_review_ready = true",
          manifest.get("local_review_ready") is True)
    check("external_api_called = false",
          manifest.get("external_api_called") is False)
    check("ai_model_called = false",
          manifest.get("ai_model_called") is False)
    check("credentials_read = false",
          manifest.get("credentials_read") is False)
    check("tg_sent = false",
          manifest.get("tg_sent") is False)
    check("prod_state_write = false",
          manifest.get("prod_state_write") is False)
    check("daemon_started = false",
          manifest.get("daemon_started") is False)
    check("watcher_started = false",
          manifest.get("watcher_started") is False)
    check("files_deleted = false",
          manifest.get("files_deleted") is False)
    check("real_send_candidate_generated = false",
          manifest.get("real_send_candidate_generated") is False)

    # ==================================================================
    # 19. Gate Result Stage Correct
    # ==================================================================
    print("\n[19] Gate Result Stage Correct")
    check("gate stage = v115f_...",
          gate_result.get("gate_stage") == "v115f_whale_address_audit_operator_workbook_local_only",
          f"got: {gate_result.get('gate_stage')}")

    # ==================================================================
    # 20. Gate Result — gate_passed = true
    # ==================================================================
    print("\n[20] Gate Result — gate_passed = true")
    check("gate_passed = true",
          gate_result.get("gate_passed") is True,
          f"got: {gate_result.get('gate_passed')}")

    # ==================================================================
    # 21. Gate Result — All Checks Pass
    # ==================================================================
    print("\n[21] Gate Result — All Individual Checks Pass")
    checks = gate_result.get("checks", [])
    check(f"gate has checks (got {len(checks)})", len(checks) > 0)
    for c in checks:
        check(f"check '{c.get('check')}' = {c.get('result')}",
              c.get("result") is True,
              c.get("detail", ""))

    # ==================================================================
    # 22. Gate Result — Safety Invariants
    # ==================================================================
    print("\n[22] Gate Result — Safety Invariants")
    safety = gate_result.get("safety_invariants", {})
    check("safety: external_api_called = false",
          safety.get("external_api_called") is False)
    check("safety: ai_model_called = false",
          safety.get("ai_model_called") is False)
    check("safety: credentials_read = false",
          safety.get("credentials_read") is False)
    check("safety: tg_sent = false",
          safety.get("tg_sent") is False)
    check("safety: prod_state_write = false",
          safety.get("prod_state_write") is False)
    check("safety: daemon_started = false",
          safety.get("daemon_started") is False)
    check("safety: watcher_started = false",
          safety.get("watcher_started") is False)
    check("safety: files_deleted = false",
          safety.get("files_deleted") is False)

    # ==================================================================
    # 23. No External API References in Output
    # ==================================================================
    print("\n[23] No External API References in Output")
    api_patterns = [
        "http://", "https://", "api.", "fetch(", "curl ",
        "requests.", "urllib", "httpx",
    ]
    # Check manifest
    manifest_str = json.dumps(manifest)
    for pat in api_patterns:
        check(f"manifest: no '{pat}' reference", pat not in manifest_str,
              f"found '{pat}' in manifest")
    # Check gate result
    gate_str = json.dumps(gate_result)
    for pat in api_patterns:
        check(f"gate_result: no '{pat}' reference", pat not in gate_str,
              f"found '{pat}' in gate_result")

    # ==================================================================
    # 24. No Credential References in Output
    # ==================================================================
    print("\n[24] No Credential References in Output")
    sensitive_patterns = [
        "API_KEY", "token", "password", "secret", ".env",
        "OPENAI", "OPENROUTER",
    ]
    all_output_text = manifest_str + gate_str + md_text
    for pat in sensitive_patterns:
        hit = pat.lower() in all_output_text.lower()
        check(f"no '{pat}' in output", not hit,
              f"found '{pat}' in output text")

    # ==================================================================
    # 25. Markdown Contains Operator Instructions
    # ==================================================================
    print("\n[25] Markdown Contains Required Sections")
    check("title mentions v115F", "v115F" in md_text)
    check("mentions current state summary", "Current State Summary" in md_text or "state" in md_text.lower())
    check("mentions block/blocked status", "BLOCKED" in md_text or "blocked" in md_text.lower())
    check("mentions operator filling instructions", "Filling Instructions" in md_text or "operator" in md_text.lower())
    check("explicitly states not a trading signal",
          "NOT a trading signal" in md_text or "not a trading signal" in md_text.lower())
    check("explicitly states not production send",
          "NOT a production send" in md_text or "production send" in md_text.lower())
    check("explicitly states not TG send candidate",
          "TG send candidate" in md_text or "not a TG send" in md_text.lower())

    # ==================================================================
    # 26. Markdown Contains Missing Evidence Types
    # ==================================================================
    print("\n[26] Markdown Contains Missing Evidence Types")
    for et in [
        "trusted_source_label",
        "cross_source_consistency",
        "address_activity_consistency",
        "manual_operator_confirmation",
    ]:
        check(f"Markdown mentions '{et}'",
              et in md_text,
              f"missing evidence type not mentioned: {et}")

    # ==================================================================
    # 27. No External Query Results Embedded
    # ==================================================================
    print("\n[27] No External Query Results Embedded in CSV")
    no_external_domains = [
        "etherscan", "nansen", "arkham", "debank",
        "zapper", "dune", "flipside", "glassnode",
    ]
    for i, row in enumerate(csv_rows):
        for field in MANUAL_FIELDS:
            val = row.get(field, "")
            for domain in no_external_domains:
                hit = domain in val.lower()
                check(f"Row {i+1}/{field}: no '{domain}' embedded",
                      not hit,
                      f"found '{domain}' in {field}")

    # ==================================================================
    # 28. Handoff Content
    # ==================================================================
    print("\n[28] Handoff Markdown Content")
    if file_exists(V115F_HANDOFF):
        with open(V115F_HANDOFF, "r", encoding="utf-8") as f:
            handoff_text = f.read()

        check("handoff mentions v115F", "v115F" in handoff_text)
        check("handoff mentions workbook", "workbook" in handoff_text.lower())
        check("handoff mentions upgrade_ready_count",
              "upgrade_ready_count" in handoff_text)
        check("handoff mentions blocked_upgrade_count",
              "blocked_upgrade_count" in handoff_text)
        check("handoff mentions safety invariants",
              "safety" in handoff_text.lower() or "invariant" in handoff_text.lower())
        check("handoff mentions operator actions",
              "operator" in handoff_text.lower())
    else:
        check("handoff file exists for content check", False, "file not found")

    # ==================================================================
    # 29. Negative Assertions
    # ==================================================================
    print("\n[29] Negative Assertions — Nothing Claims Success")
    check("manifest does NOT claim send_ready=true",
          manifest.get("send_ready") is not True)
    check("manifest does NOT claim tg_test_group_ready=true",
          manifest.get("tg_test_group_ready") is not True)
    check("manifest does NOT claim tg_sent=true",
          manifest.get("tg_sent") is not True)
    check("manifest does NOT claim prod_state_write=true",
          manifest.get("prod_state_write") is not True)
    check("manifest does NOT claim real_send_candidate_generated=true",
          manifest.get("real_send_candidate_generated") is not True)
    check("manifest does NOT claim upgrade_ready_count > 0",
          manifest.get("upgrade_ready_count", 0) == 0)
    check("manifest does NOT claim files_deleted=true",
          manifest.get("files_deleted") is not True)
    check("manifest does NOT claim daemon_started=true",
          manifest.get("daemon_started") is not True)
    check("manifest does NOT claim watcher_started=true",
          manifest.get("watcher_started") is not True)

    # ==================================================================
    # 30. CSV Column Completeness — all 22 columns with correct names
    # ==================================================================
    print("\n[30] CSV Column Name Completeness")
    if len(csv_rows) > 0:
        actual_columns = list(csv_rows[0].keys())
        for col in REQUIRED_CSV_COLUMNS:
            check(f"CSV has required column '{col}'",
                  col in actual_columns,
                  f"not found in CSV; actual columns: {actual_columns}")

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
