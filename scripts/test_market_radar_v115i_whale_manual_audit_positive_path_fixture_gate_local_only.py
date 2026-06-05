#!/usr/bin/env python3
"""
Test suite for v115I Whale Manual Audit Positive Path Fixture Gate — Local Only
=================================================================================
Validates the v115I fixture gate runner produced correct positive-path outputs:
  - fixture_rows=1, all metadata flags set
  - fixture intake ready count=1, upgrade_candidate_count=1
  - fixture adjudication ready count=1, label_upgrade_allowed_count=1
  - fixture_label_upgraded_count=0 (no actual upgrade)
  - real v115F workbook NOT modified
  - real v115G/v115H results still blocked
  - No old results modified
  - All safety invariants intact
  - No external API, AI, credentials, TG, prod state, daemon, file deletion
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

# v115I outputs (must exist)
V115I_FIXTURE_CSV = os.path.join(
    FIXTURES_DIR, "v115i_whale_manual_audit_positive_path_fixture.csv"
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
V115I_GATE_RESULT = os.path.join(
    RESULTS_DIR, "market_radar_v115i_whale_manual_audit_positive_path_fixture_gate_result.json"
)
V115I_MD = os.path.join(
    RUNS_DIR, "v115i_whale_manual_audit_positive_path_fixture_gate_local_only.md"
)
V115I_HANDOFF = os.path.join(
    RUNS_DIR, "v115i_whale_manual_audit_positive_path_fixture_gate_local_only_handoff.md"
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

# v115G real results (must still exist, intake_ready_count=0)
V115G_INTAKE_RECORDS = os.path.join(
    RESULTS_DIR, "market_radar_v115g_whale_manual_audit_intake_records.jsonl"
)
V115G_INTAKE_DECISIONS = os.path.join(
    RESULTS_DIR, "market_radar_v115g_whale_manual_audit_intake_decisions.jsonl"
)
V115G_GATE_RESULT = os.path.join(
    RESULTS_DIR, "market_radar_v115g_whale_manual_audit_workbook_intake_gate_result.json"
)

# v115H real results (must still exist, label_upgrade_allowed_count=0)
V115H_ADJ_RECORDS = os.path.join(
    RESULTS_DIR, "market_radar_v115h_whale_label_upgrade_adjudication_records.jsonl"
)
V115H_ADJ_DECISIONS = os.path.join(
    RESULTS_DIR, "market_radar_v115h_whale_label_upgrade_adjudication_decisions.jsonl"
)
V115H_GATE_RESULT = os.path.join(
    RESULTS_DIR, "market_radar_v115h_whale_label_upgrade_adjudication_gate_result.json"
)

# Old results that must still exist
OLD_RESULTS = [
    # v115E
    os.path.join(RESULTS_DIR, "market_radar_v115e_whale_label_upgrade_decisions.jsonl"),
    os.path.join(RESULTS_DIR, "market_radar_v115e_whale_address_audit_evidence_requests.jsonl"),
    os.path.join(RESULTS_DIR, "market_radar_v115e_whale_address_manual_audit_forms.jsonl"),
    os.path.join(RESULTS_DIR, "market_radar_v115e_whale_address_audit_evidence_pack_result.json"),
    # v115D
    os.path.join(RESULTS_DIR, "market_radar_v115d_whale_one_shot_send_preview_gate_decisions.jsonl"),
    os.path.join(RESULTS_DIR, "market_radar_v115d_whale_one_shot_send_preview_gate_result.json"),
]

# v115B config (must still exist)
V115B_ROUTING = os.path.join(
    CONFIG_DIR, "market_radar_v115b_whale_label_confidence_routing_policy.json"
)

# v115F expected addresses
V115F_EXPECTED_ADDRESSES = [
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
    print("v115I Test Suite — Positive Path Fixture Gate")
    print("=" * 70)

    # ==================================================================
    # 1. File Existence — v115I Outputs
    # ==================================================================
    print("\n[1] File Existence — v115I Outputs")
    check("fixture CSV exists", file_exists(V115I_FIXTURE_CSV))
    check("intake records .jsonl exists", file_exists(V115I_INTAKE_RECORDS))
    check("intake decisions .jsonl exists", file_exists(V115I_INTAKE_DECISIONS))
    check("adjudication records .jsonl exists", file_exists(V115I_ADJ_RECORDS))
    check("adjudication decisions .jsonl exists", file_exists(V115I_ADJ_DECISIONS))
    check("gate result .json exists", file_exists(V115I_GATE_RESULT))
    check("markdown report exists", file_exists(V115I_MD))
    check("handoff markdown exists", file_exists(V115I_HANDOFF))

    # ==================================================================
    # 2. File Existence — v115F Real Workbook NOT Modified
    # ==================================================================
    print("\n[2] Real v115F Workbook Still Intact")
    check("v115F workbook CSV exists", file_exists(V115F_WORKBOOK_CSV))
    check("v115F manifest exists", file_exists(V115F_MANIFEST))
    check("v115F gate result exists", file_exists(V115F_GATE_RESULT))

    # Verify v115F still has 4 original addresses
    wb_rows = load_csv_dict(V115F_WORKBOOK_CSV)
    check(f"v115F workbook still has 4 rows (got {len(wb_rows)})", len(wb_rows) == 4)

    wb_addresses = [r.get("address", "").strip() for r in wb_rows]
    for addr in V115F_EXPECTED_ADDRESSES:
        check(f"v115F still contains {addr[:14]}...", addr in wb_addresses)

    # ==================================================================
    # 3. File Existence — v115G/v115H Real Results Still Intact
    # ==================================================================
    print("\n[3] Real v115G/v115H Results Still Intact")
    check("v115G intake records exist", file_exists(V115G_INTAKE_RECORDS))
    check("v115G intake decisions exist", file_exists(V115G_INTAKE_DECISIONS))
    check("v115G gate result exists", file_exists(V115G_GATE_RESULT))
    check("v115H adjudication records exist", file_exists(V115H_ADJ_RECORDS))
    check("v115H adjudication decisions exist", file_exists(V115H_ADJ_DECISIONS))
    check("v115H gate result exists", file_exists(V115H_GATE_RESULT))

    # ==================================================================
    # 4. File Existence — v114A-v115E Old Results Still Intact
    # ==================================================================
    print("\n[4] v114A-v115E Old Results Still Intact")
    for path in OLD_RESULTS:
        fname = os.path.basename(path)
        check(f"{fname} exists", file_exists(path))
    check("v115B routing policy exists", file_exists(V115B_ROUTING))

    # ==================================================================
    # 5. Fixture CSV — Row Count = 1
    # ==================================================================
    print("\n[5] Fixture CSV — Row Count = 1")
    fixture_rows = load_csv_dict(V115I_FIXTURE_CSV)
    check(f"Fixture rows = 1 (got {len(fixture_rows)})", len(fixture_rows) == 1)

    # ==================================================================
    # 6. Fixture CSV — Metadata Flags
    # ==================================================================
    print("\n[6] Fixture CSV — Metadata Flags")
    for i, row in enumerate(fixture_rows):
        fo = parse_bool_csv(row.get("fixture_only", "false"))
        se = parse_bool_csv(row.get("synthetic_evidence", "false"))
        nr = parse_bool_csv(row.get("not_real_label_upgrade", "false"))
        ns = parse_bool_csv(row.get("not_send_candidate", "false"))

        check(f"Fixture row {i+1}: fixture_only=true", fo is True, f"got: {row.get('fixture_only')}")
        check(f"Fixture row {i+1}: synthetic_evidence=true", se is True, f"got: {row.get('synthetic_evidence')}")
        check(f"Fixture row {i+1}: not_real_label_upgrade=true", nr is True, f"got: {row.get('not_real_label_upgrade')}")
        check(f"Fixture row {i+1}: not_send_candidate=true", ns is True, f"got: {row.get('not_send_candidate')}")

    # ==================================================================
    # 7. Fixture CSV — Manual Evidence Fields Filled
    # ==================================================================
    print("\n[7] Fixture CSV — Manual Evidence Fields Filled")
    required_evidence_fields = [
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
    for i, row in enumerate(fixture_rows):
        for field in required_evidence_fields:
            val = row.get(field, "")
            check(f"Fixture row {i+1}: '{field}' is non-empty",
                  val is not None and str(val).strip() != "",
                  f"got: empty")

    # ==================================================================
    # 8. Data Loading — v115I Outputs
    # ==================================================================
    print("\n[8] Data Loading — v115I Outputs")
    intake_records = load_jsonl(V115I_INTAKE_RECORDS)
    check(f"Intake records loaded ({len(intake_records)})", len(intake_records) > 0)

    intake_decisions = load_jsonl(V115I_INTAKE_DECISIONS)
    check(f"Intake decisions loaded ({len(intake_decisions)})", len(intake_decisions) > 0)

    adj_records = load_jsonl(V115I_ADJ_RECORDS)
    check(f"Adjudication records loaded ({len(adj_records)})", len(adj_records) > 0)

    adj_decisions = load_jsonl(V115I_ADJ_DECISIONS)
    check(f"Adjudication decisions loaded ({len(adj_decisions)})", len(adj_decisions) > 0)

    gate_result = load_json(V115I_GATE_RESULT)
    check("Gate result JSON parsed", isinstance(gate_result, dict))

    with open(V115I_MD, "r", encoding="utf-8") as f:
        md_text = f.read()
    check("Markdown report loaded", len(md_text) > 0)

    with open(V115I_HANDOFF, "r", encoding="utf-8") as f:
        handoff_text = f.read()
    check("Handoff markdown loaded", len(handoff_text) > 0)

    # ==================================================================
    # 9. Fixture Intake — Row Counts = 1
    # ==================================================================
    print("\n[9] Fixture Intake — Row Counts = 1")
    check(f"fixture_intake_records = 1 (got {len(intake_records)})", len(intake_records) == 1)
    check(f"fixture_intake_decisions = 1 (got {len(intake_decisions)})", len(intake_decisions) == 1)

    # ==================================================================
    # 10. Fixture Intake — Positive Path Results
    # ==================================================================
    print("\n[10] Fixture Intake — Positive Path Results")
    for rec in intake_records:
        check("intake_ready = true", rec.get("intake_ready") is True,
              f"got: {rec.get('intake_ready')}")
        check("manual_fields_complete = true", rec.get("manual_fields_complete") is True,
              f"got: {rec.get('manual_fields_complete')}")

    for dec in intake_decisions:
        check("intake decision = 'intake_passed'", dec.get("decision") == "intake_passed",
              f"got: '{dec.get('decision')}'")
        check("upgrade_candidate = true", dec.get("upgrade_candidate") is True,
              f"got: {dec.get('upgrade_candidate')}")
        check("upgrade_ready = true", dec.get("upgrade_ready") is True,
              f"got: {dec.get('upgrade_ready')}")
        check("block_reasons is empty", len(dec.get("block_reasons", [])) == 0,
              f"got: {dec.get('block_reasons')}")
        check("missing_fields is empty", len(dec.get("missing_fields", [])) == 0,
              f"got: {dec.get('missing_fields')}")
        # Send guards must be false
        check("send_allowed = false", dec.get("send_allowed") is False)
        check("tg_test_group_allowed = false", dec.get("tg_test_group_allowed") is False)
        check("public_send_allowed = false", dec.get("public_send_allowed") is False)

    # ==================================================================
    # 11. Fixture Adjudication — Row Counts = 1
    # ==================================================================
    print("\n[11] Fixture Adjudication — Row Counts = 1")
    check(f"fixture_adjudication_records = 1 (got {len(adj_records)})", len(adj_records) == 1)
    check(f"fixture_adjudication_decisions = 1 (got {len(adj_decisions)})", len(adj_decisions) == 1)

    # ==================================================================
    # 12. Fixture Adjudication — Positive Path Results
    # ==================================================================
    print("\n[12] Fixture Adjudication — Positive Path Results")
    for rec in adj_records:
        check("adjudication_ready = true", rec.get("adjudication_ready") is True,
              f"got: {rec.get('adjudication_ready')}")
        check("label_upgrade_allowed = true (record)", rec.get("label_upgrade_allowed") is True,
              f"got: {rec.get('label_upgrade_allowed')}")
        check("trusted_source_ok = true", rec.get("trusted_source_ok") is True)
        check("second_source_ok = true", rec.get("second_source_ok") is True)
        check("activity_pattern_ok = true", rec.get("activity_pattern_ok") is True)
        check("operator_confirmation_ok = true", rec.get("operator_confirmation_ok") is True)
        check("evidence_requirements_met = true", rec.get("evidence_requirements_met") is True)
        # new_confidence must equal current_confidence (no actual upgrade)
        cur_c = rec.get("current_confidence", "")
        new_c = rec.get("new_confidence", "")
        check(f"new_confidence = current_confidence ({cur_c})", new_c == cur_c,
              f"new={new_c} != current={cur_c}")

    for dec in adj_decisions:
        check("adjudication decision = 'adjudication_passed'",
              dec.get("decision") == "adjudication_passed",
              f"got: '{dec.get('decision')}'")
        check("label_upgrade_allowed = true (decision)", dec.get("label_upgrade_allowed") is True,
              f"got: {dec.get('label_upgrade_allowed')}")
        check("block_reasons is empty", len(dec.get("block_reasons", [])) == 0,
              f"got: {dec.get('block_reasons')}")
        # to_confidence must equal from_confidence (no actual upgrade)
        from_c = dec.get("from_confidence", "")
        to_c = dec.get("to_confidence", "")
        check(f"to_confidence = from_confidence ({from_c})", to_c == from_c,
              f"to={to_c} != from={from_c}")
        # Send guards must be false
        check("send_allowed = false", dec.get("send_allowed") is False)
        check("tg_test_group_allowed = false", dec.get("tg_test_group_allowed") is False)
        check("public_send_allowed = false", dec.get("public_send_allowed") is False)

    # ==================================================================
    # 13. Gate Result — All Required Fields
    # ==================================================================
    print("\n[13] Gate Result — Primary Fields")
    check("stage = v115i_whale_manual_audit_positive_path_fixture_gate_local_only",
          gate_result.get("stage") == "v115i_whale_manual_audit_positive_path_fixture_gate_local_only")
    check("fixture_only = true", gate_result.get("fixture_only") is True)
    check("synthetic_evidence = true", gate_result.get("synthetic_evidence") is True)
    check("fixture_rows = 1", gate_result.get("fixture_rows") == 1,
          f"got: {gate_result.get('fixture_rows')}")
    check("fixture_intake_ready_count = 1",
          gate_result.get("fixture_intake_ready_count") == 1,
          f"got: {gate_result.get('fixture_intake_ready_count')}")
    check("fixture_upgrade_candidate_count = 1",
          gate_result.get("fixture_upgrade_candidate_count") == 1,
          f"got: {gate_result.get('fixture_upgrade_candidate_count')}")
    check("fixture_blocked_intake_count = 0",
          gate_result.get("fixture_blocked_intake_count") == 0,
          f"got: {gate_result.get('fixture_blocked_intake_count')}")
    check("fixture_adjudication_ready_count = 1",
          gate_result.get("fixture_adjudication_ready_count") == 1,
          f"got: {gate_result.get('fixture_adjudication_ready_count')}")
    check("fixture_label_upgrade_allowed_count = 1",
          gate_result.get("fixture_label_upgrade_allowed_count") == 1,
          f"got: {gate_result.get('fixture_label_upgrade_allowed_count')}")
    check("fixture_label_upgraded_count = 0",
          gate_result.get("fixture_label_upgraded_count") == 0,
          f"got: {gate_result.get('fixture_label_upgraded_count')}")
    check("real_v115g_intake_ready_count = 0",
          gate_result.get("real_v115g_intake_ready_count") == 0,
          f"got: {gate_result.get('real_v115g_intake_ready_count')}")
    check("real_v115h_label_upgrade_allowed_count = 0",
          gate_result.get("real_v115h_label_upgrade_allowed_count") == 0,
          f"got: {gate_result.get('real_v115h_label_upgrade_allowed_count')}")
    check("send_ready = false", gate_result.get("send_ready") is False)
    check("tg_test_group_ready = false", gate_result.get("tg_test_group_ready") is False)
    check("local_review_ready = true", gate_result.get("local_review_ready") is True)

    # ==================================================================
    # 14. Gate Result — Safety Invariants
    # ==================================================================
    print("\n[14] Gate Result — Safety Invariants")
    check("real_workbook_modified = false", gate_result.get("real_workbook_modified") is False)
    check("real_label_upgrade_performed = false",
          gate_result.get("real_label_upgrade_performed") is False)
    check("real_send_candidate_generated = false",
          gate_result.get("real_send_candidate_generated") is False)
    check("external_api_called = false", gate_result.get("external_api_called") is False)
    check("ai_model_called = false", gate_result.get("ai_model_called") is False)
    check("credentials_read = false", gate_result.get("credentials_read") is False)
    check("tg_sent = false", gate_result.get("tg_sent") is False)
    check("prod_state_write = false", gate_result.get("prod_state_write") is False)
    check("daemon_started = false", gate_result.get("daemon_started") is False)
    check("watcher_started = false", gate_result.get("watcher_started") is False)
    check("files_deleted = false", gate_result.get("files_deleted") is False)

    # ==================================================================
    # 15. Cross-Check — Real v115G Still Blocked
    # ==================================================================
    print("\n[15] Cross-Check — Real v115G Still Blocked")
    v115g = load_json(V115G_GATE_RESULT)
    check("v115G intake_ready_count = 0",
          v115g.get("intake_ready_count") == 0,
          f"got: {v115g.get('intake_ready_count')}")
    check("v115G blocked_intake_count = 4",
          v115g.get("blocked_intake_count") == 4,
          f"got: {v115g.get('blocked_intake_count')}")
    check("v115G upgrade_candidate_count = 0",
          v115g.get("upgrade_candidate_count") == 0,
          f"got: {v115g.get('upgrade_candidate_count')}")

    v115g_records = load_jsonl(V115G_INTAKE_RECORDS)
    check(f"v115G intake records still 4 (got {len(v115g_records)})", len(v115g_records) == 4)
    for i, rec in enumerate(v115g_records):
        check(f"v115G record {i+1}: intake_ready still false",
              rec.get("intake_ready") is False)

    # ==================================================================
    # 16. Cross-Check — Real v115H Still Blocked
    # ==================================================================
    print("\n[16] Cross-Check — Real v115H Still Blocked")
    v115h = load_json(V115H_GATE_RESULT)
    check("v115H label_upgrade_allowed_count = 0",
          v115h.get("label_upgrade_allowed_count") == 0,
          f"got: {v115h.get('label_upgrade_allowed_count')}")
    check("v115H blocked_adjudication_count = 4",
          v115h.get("blocked_adjudication_count") == 4,
          f"got: {v115h.get('blocked_adjudication_count')}")
    check("v115H label_upgraded_count = 0",
          v115h.get("label_upgraded_count") == 0,
          f"got: {v115h.get('label_upgraded_count')}")

    v115h_records = load_jsonl(V115H_ADJ_RECORDS)
    check(f"v115H adjudication records still 4 (got {len(v115h_records)})", len(v115h_records) == 4)
    for i, rec in enumerate(v115h_records):
        check(f"v115H record {i+1}: adjudication_ready still false",
              rec.get("adjudication_ready") is False)
        check(f"v115H record {i+1}: label_upgrade_allowed still false",
              rec.get("label_upgrade_allowed") is False)

    # ==================================================================
    # 17. No Real Send Candidate Generated
    # ==================================================================
    print("\n[17] No Real Send Candidate Generated")
    check("real_send_candidate_generated=false in v115I gate result",
          gate_result.get("real_send_candidate_generated") is False)
    check("real_send_candidate_generated=false in v115G gate result",
          v115g.get("real_send_candidate_generated") is False)
    check("real_send_candidate_generated=false in v115H gate result",
          v115h.get("real_send_candidate_generated") is False)

    # ==================================================================
    # 18. No TG Sent
    # ==================================================================
    print("\n[18] No TG Sent")
    check("tg_sent=false in v115I", gate_result.get("tg_sent") is False)
    check("tg_sent=false in v115G", v115g.get("tg_sent") is False)
    check("tg_sent=false in v115H", v115h.get("tg_sent") is False)

    # ==================================================================
    # 19. No Production State Write
    # ==================================================================
    print("\n[19] No Production State Write")
    check("prod_state_write=false in v115I", gate_result.get("prod_state_write") is False)
    check("prod_state_write=false in v115G", v115g.get("prod_state_write") is False)
    check("prod_state_write=false in v115H", v115h.get("prod_state_write") is False)

    # ==================================================================
    # 20. No External API / AI / Credentials
    # ==================================================================
    print("\n[20] No External API / AI / Credentials")
    check("external_api_called=false in v115I", gate_result.get("external_api_called") is False)
    check("ai_model_called=false in v115I", gate_result.get("ai_model_called") is False)
    check("credentials_read=false in v115I", gate_result.get("credentials_read") is False)

    # Check outputs for API/credential patterns
    all_output_text = (
        json.dumps(gate_result) +
        json.dumps(intake_records) +
        json.dumps(intake_decisions) +
        json.dumps(adj_records) +
        json.dumps(adj_decisions) +
        md_text +
        handoff_text
    )
    suspicious_patterns = ["http://api.", "https://api.", "fetch(", "curl ",
                           "requests.get", "requests.post", "urllib"]
    for pat in suspicious_patterns:
        check(f"No '{pat}' in any v115I output", pat not in all_output_text.lower(),
              f"found '{pat}'")

    sensitive_patterns = ["API_KEY", "api_key", "token", "password", "secret",
                          ".env", "OPENAI", "OPENROUTER"]
    for pat in sensitive_patterns:
        check(f"No '{pat}' in any v115I output", pat.lower() not in all_output_text.lower(),
              f"found '{pat}'")

    # ==================================================================
    # 21. No Daemon/Watcher/Cron/Loop Started
    # ==================================================================
    print("\n[21] No Daemon/Watcher/Cron/Loop Started")
    check("daemon_started=false", gate_result.get("daemon_started") is False)
    check("watcher_started=false", gate_result.get("watcher_started") is False)

    # ==================================================================
    # 22. No Files Deleted
    # ==================================================================
    print("\n[22] No Files Deleted")
    check("files_deleted=false", gate_result.get("files_deleted") is False)

    # ==================================================================
    # 23. Intake Record Field Completeness
    # ==================================================================
    print("\n[23] Intake Record Field Completeness")
    required_intake_fields = [
        "address", "current_label", "current_confidence", "target_confidence",
        "priority", "trusted_source_label_value", "trusted_source_url_or_note",
        "second_source_label_value", "second_source_url_or_note",
        "activity_pattern_note", "operator_confirmed_label",
        "operator_confidence_assessment", "operator_reject_reason",
        "reviewer", "reviewed_at", "ready_for_upgrade",
        "manual_fields_complete", "evidence_url_fields_present",
        "operator_confirmation_present", "intake_ready",
        "fixture_only", "synthetic_evidence", "not_real_label_upgrade",
        "not_send_candidate",
    ]
    for i, rec in enumerate(intake_records):
        for field in required_intake_fields:
            check(f"Intake record {i+1}: field '{field}' present",
                  field in rec, f"missing field: {field}")

    # ==================================================================
    # 24. Intake Decision Field Completeness
    # ==================================================================
    print("\n[24] Intake Decision Field Completeness")
    required_intake_dec_fields = [
        "address", "decision", "upgrade_candidate", "upgrade_ready",
        "missing_fields", "block_reasons", "send_allowed",
        "tg_test_group_allowed", "public_send_allowed",
    ]
    for i, dec in enumerate(intake_decisions):
        for field in required_intake_dec_fields:
            check(f"Intake decision {i+1}: field '{field}' present",
                  field in dec, f"missing field: {field}")

    # ==================================================================
    # 25. Adjudication Record Field Completeness
    # ==================================================================
    print("\n[25] Adjudication Record Field Completeness")
    required_adj_fields = [
        "address", "current_label", "current_confidence",
        "requested_confidence", "intake_ready", "upgrade_candidate",
        "manual_fields_complete", "evidence_requirements_met",
        "trusted_source_ok", "second_source_ok",
        "activity_pattern_ok", "operator_confirmation_ok",
        "adjudication_ready", "label_upgrade_allowed", "new_confidence",
        "fixture_only", "synthetic_evidence", "not_real_label_upgrade",
        "not_send_candidate",
    ]
    for i, rec in enumerate(adj_records):
        for field in required_adj_fields:
            check(f"Adjudication record {i+1}: field '{field}' present",
                  field in rec, f"missing field: {field}")

    # ==================================================================
    # 26. Adjudication Decision Field Completeness
    # ==================================================================
    print("\n[26] Adjudication Decision Field Completeness")
    required_adj_dec_fields = [
        "address", "decision", "label_upgrade_allowed",
        "from_confidence", "to_confidence", "requested_confidence",
        "block_reasons", "send_allowed", "tg_test_group_allowed",
        "public_send_allowed",
    ]
    for i, dec in enumerate(adj_decisions):
        for field in required_adj_dec_fields:
            check(f"Adjudication decision {i+1}: field '{field}' present",
                  field in dec, f"missing field: {field}")

    # ==================================================================
    # 27. Markdown Report Content
    # ==================================================================
    print("\n[27] Markdown Report Content")
    check("Markdown mentions v115I", "v115I" in md_text)
    check("Markdown mentions fixture", "fixture" in md_text.lower())
    check("Markdown mentions positive path or test-only",
          "positive path" in md_text.lower() or "test-only" in md_text.lower() or
          "test only" in md_text.lower() or "fixture only" in md_text.lower())
    check("Markdown mentions NOT a trading signal or equivalent",
          "NOT a trading signal" in md_text or "not a trading signal" in md_text.lower() or
          "NOT a production send" in md_text or "production send" in md_text.lower())

    # ==================================================================
    # 28. Handoff Content
    # ==================================================================
    print("\n[28] Handoff Markdown Content")
    check("Handoff mentions v115I", "v115I" in handoff_text)
    check("Handoff mentions fixture", "fixture" in handoff_text.lower())
    check("Handoff mentions safety invariants",
          "safety" in handoff_text.lower() or "invariant" in handoff_text.lower())

    # ==================================================================
    # 29. Negative Assertions — Nothing Claims Success It Shouldn't
    # ==================================================================
    print("\n[29] Negative Assertions")
    check("NOT claiming send_ready=true", gate_result.get("send_ready") is not True)
    check("NOT claiming tg_test_group_ready=true",
          gate_result.get("tg_test_group_ready") is not True)
    check("NOT claiming tg_sent=true", gate_result.get("tg_sent") is not True)
    check("NOT claiming prod_state_write=true",
          gate_result.get("prod_state_write") is not True)
    check("NOT claiming real_send_candidate_generated=true",
          gate_result.get("real_send_candidate_generated") is not True)
    check("NOT claiming real_workbook_modified=true",
          gate_result.get("real_workbook_modified") is not True)
    check("NOT claiming real_label_upgrade_performed=true",
          gate_result.get("real_label_upgrade_performed") is not True)
    check("NOT claiming fixture_label_upgraded_count > 0",
          gate_result.get("fixture_label_upgraded_count", 0) == 0)
    check("NOT claiming real_v115g_intake_ready_count > 0",
          gate_result.get("real_v115g_intake_ready_count", 0) == 0)
    check("NOT claiming real_v115h_label_upgrade_allowed_count > 0",
          gate_result.get("real_v115h_label_upgrade_allowed_count", 0) == 0)
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
    # 30. v115F Workbook CSV Has Original Content (NOT modified)
    # ==================================================================
    print("\n[30] v115F Workbook NOT Modified — Content Check")
    # Check that operator evidence fields remain empty in the real workbook
    for i, row in enumerate(wb_rows):
        check(f"v115F row {i+1}: trusted_source_label_value still empty",
              (row.get("trusted_source_label_value") or "").strip() == "",
              f"got: '{row.get('trusted_source_label_value')}'")
        check(f"v115F row {i+1}: ready_for_upgrade still false",
              parse_bool_csv(row.get("ready_for_upgrade", "false")) is False,
              f"got: '{row.get('ready_for_upgrade')}'")

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
