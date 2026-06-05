#!/usr/bin/env python3
"""
Test suite for v115E Whale Address Audit Evidence Pack — Local Only
=====================================================================
Validates that the v115E audit evidence pack runner produced correct
outputs with all safety invariants, evidence request requirements,
manual audit form completeness, and blocked upgrade decisions.

This test ONLY verifies generated files — it does NOT make any
external API calls, send TG, or write production state.
"""

import json
import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RESULTS_DIR = os.path.join(BASE_DIR, "results")
CONFIG_DIR = os.path.join(BASE_DIR, "config")
RUNS_DIR = os.path.join(BASE_DIR, "runs", "market_radar")

# v115E outputs
V115E_RESULT = os.path.join(
    RESULTS_DIR, "market_radar_v115e_whale_address_audit_evidence_pack_result.json"
)
V115E_EVIDENCE_REQUESTS = os.path.join(
    RESULTS_DIR, "market_radar_v115e_whale_address_audit_evidence_requests.jsonl"
)
V115E_MANUAL_AUDIT_FORMS = os.path.join(
    RESULTS_DIR, "market_radar_v115e_whale_address_manual_audit_forms.jsonl"
)
V115E_UPGRADE_DECISIONS = os.path.join(
    RESULTS_DIR, "market_radar_v115e_whale_label_upgrade_decisions.jsonl"
)
V115E_REPORT = os.path.join(
    RUNS_DIR, "v115e_whale_address_audit_evidence_pack_local_only.md"
)
V115E_HANDOFF = os.path.join(
    RUNS_DIR, "v115e_whale_address_audit_evidence_pack_local_only_handoff.md"
)

# v115B inputs (must still exist)
V115B_UPGRADE_TARGETS = os.path.join(
    RESULTS_DIR, "market_radar_v115b_whale_label_upgrade_targets.jsonl"
)
V115B_ROUTING = os.path.join(
    CONFIG_DIR, "market_radar_v115b_whale_label_confidence_routing_policy.json"
)
V115B_SEND_GATE = os.path.join(
    CONFIG_DIR, "market_radar_v115b_whale_send_preview_gate_policy.json"
)

# v115D outputs/inputs
V115D_PREVIEW_RECORDS = os.path.join(
    RESULTS_DIR, "market_radar_v115d_whale_one_shot_send_preview_records.jsonl"
)
V115D_GATE_DECISIONS = os.path.join(
    RESULTS_DIR, "market_radar_v115d_whale_one_shot_send_preview_gate_decisions.jsonl"
)
V115D_RESULT = os.path.join(
    RESULTS_DIR, "market_radar_v115d_whale_one_shot_send_preview_gate_result.json"
)

# v115C outputs
V115C_RESULT = os.path.join(
    RESULTS_DIR, "market_radar_v115c_whale_tg_test_copy_template_gate_result.json"
)
V115C_TEMPLATES = os.path.join(
    RESULTS_DIR, "market_radar_v115c_whale_tg_test_copy_templates.jsonl"
)

# v114C inputs
V114C_REVIEW_CARDS = os.path.join(
    RESULTS_DIR, "market_radar_v114c_whale_delta_operator_review_cards.jsonl"
)

REQUIRED_EVIDENCE_TYPES = [
    "trusted_source_label",
    "cross_source_consistency",
    "address_activity_consistency",
    "manual_operator_confirmation",
]

MANUAL_FORM_FIELDS = [
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
    print("v115E Test Suite — Whale Address Audit Evidence Pack")
    print("=" * 70)

    # ==================================================================
    # 1. File Existence — v115E Outputs
    # ==================================================================
    print("\n[1] File Existence — v115E Outputs")
    check("evidence requests JSONL exists", file_exists(V115E_EVIDENCE_REQUESTS))
    check("manual audit forms JSONL exists", file_exists(V115E_MANUAL_AUDIT_FORMS))
    check("upgrade decisions JSONL exists", file_exists(V115E_UPGRADE_DECISIONS))
    check("result JSON exists", file_exists(V115E_RESULT))
    check("markdown report exists", file_exists(V115E_REPORT))
    check("handoff markdown exists", file_exists(V115E_HANDOFF))

    # ==================================================================
    # 2. File Existence — Input files must still exist (not deleted)
    # ==================================================================
    print("\n[2] File Existence — v115B/v115D/v114C Inputs (still intact)")
    check("v115B upgrade targets still exist", file_exists(V115B_UPGRADE_TARGETS))
    check("v115B routing policy still exists", file_exists(V115B_ROUTING))
    check("v115B send preview gate policy still exists", file_exists(V115B_SEND_GATE))
    check("v115D preview records still exist", file_exists(V115D_PREVIEW_RECORDS))
    check("v115D gate decisions still exist", file_exists(V115D_GATE_DECISIONS))
    check("v115D result still exists", file_exists(V115D_RESULT))
    check("v115C templates still exist", file_exists(V115C_TEMPLATES))
    check("v115C result still exists", file_exists(V115C_RESULT))
    check("v114C review cards still exist", file_exists(V114C_REVIEW_CARDS))

    # ==================================================================
    # 3. Data Loading
    # ==================================================================
    print("\n[3] Data Loading")
    evidence_requests = load_jsonl(V115E_EVIDENCE_REQUESTS)
    manual_audit_forms = load_jsonl(V115E_MANUAL_AUDIT_FORMS)
    upgrade_decisions = load_jsonl(V115E_UPGRADE_DECISIONS)
    result = load_json(V115E_RESULT)

    check("evidence requests JSONL parsed", isinstance(evidence_requests, list))
    check("manual audit forms JSONL parsed", isinstance(manual_audit_forms, list))
    check("upgrade decisions JSONL parsed", isinstance(upgrade_decisions, list))
    check("result JSON parsed", isinstance(result, dict))

    # ==================================================================
    # 4. Record Counts = 4
    # ==================================================================
    print("\n[4] Record Counts = 4")
    check(f"evidence requests count = 4 (got {len(evidence_requests)})",
          len(evidence_requests) == 4)
    check(f"manual audit forms count = 4 (got {len(manual_audit_forms)})",
          len(manual_audit_forms) == 4)
    check(f"upgrade decisions count = 4 (got {len(upgrade_decisions)})",
          len(upgrade_decisions) == 4)

    # ==================================================================
    # 5. Each target has corresponding evidence request / audit form / decision
    # ==================================================================
    print("\n[5] Address Matching Across Outputs")
    targets = load_jsonl(V115B_UPGRADE_TARGETS)
    target_addresses = set(t["address"] for t in targets)
    evr_addresses = set(e["address"] for e in evidence_requests)
    maf_addresses = set(m["address"] for m in manual_audit_forms)
    upd_addresses = set(u["address"] for u in upgrade_decisions)

    check("target addresses match evidence request addresses",
          target_addresses == evr_addresses,
          f"targets: {sorted(target_addresses)}, evr: {sorted(evr_addresses)}")
    check("target addresses match audit form addresses",
          target_addresses == maf_addresses)
    check("target addresses match upgrade decision addresses",
          target_addresses == upd_addresses)

    # ==================================================================
    # 6. Required Evidence Types — 4/4 Present
    # ==================================================================
    print("\n[6] Required Evidence Types — 4/4 Present")
    for evr in evidence_requests:
        sa = evr.get("address", "")[:14]
        req = evr.get("required_evidence_types", [])
        check(f"{sa}...: required_evidence_types has 4 entries",
              len(req) == 4,
              f"got {len(req)}: {req}")
        for et in REQUIRED_EVIDENCE_TYPES:
            check(f"{sa}...: required includes '{et}'",
                  et in req,
                  f"missing: {et}")

    # ==================================================================
    # 7. All evidence request fields present
    # ==================================================================
    print("\n[7] Evidence Request Field Completeness")
    required_evr_fields = [
        "address", "current_label", "current_confidence", "target_confidence",
        "priority", "why_this_address_matters", "related_delta_context",
        "required_evidence_types", "missing_evidence_types",
        "operator_action_required", "upgrade_ready",
    ]
    for evr in evidence_requests:
        eid = evr.get("evidence_request_id", "?")
        for field in required_evr_fields:
            check(f"{eid}: has field '{field}'",
                  field in evr,
                  f"missing field: {field}")

    # ==================================================================
    # 8. All manual evidence fields are empty or false
    # ==================================================================
    print("\n[8] All Manual Evidence Fields Default Empty/False")
    for maf in manual_audit_forms:
        fid = maf.get("audit_form_id", "?")
        for field in MANUAL_FORM_FIELDS:
            val = maf.get(field, None)
            is_empty = val in ("", None, False, [])
            check(f"{fid}: '{field}' is empty/false (got: {repr(val)})",
                  is_empty,
                  f"expected empty/false, got: {repr(val)}")

    # ==================================================================
    # 9. All ready_for_upgrade = false
    # ==================================================================
    print("\n[9] All ready_for_upgrade = false")
    for maf in manual_audit_forms:
        fid = maf.get("audit_form_id", "?")
        check(f"{fid}: ready_for_upgrade = false",
              maf.get("ready_for_upgrade") is False,
              f"got: {maf.get('ready_for_upgrade')}")

    # ==================================================================
    # 10. All upgrade_ready = false in evidence requests
    # ==================================================================
    print("\n[10] All evidence request upgrade_ready = false")
    for evr in evidence_requests:
        eid = evr.get("evidence_request_id", "?")
        check(f"{eid}: upgrade_ready = false",
              evr.get("upgrade_ready") is False,
              f"got: {evr.get('upgrade_ready')}")

    # ==================================================================
    # 11. All upgrade_ready = false in upgrade decisions
    # ==================================================================
    print("\n[11] All upgrade decision upgrade_ready = false")
    for upd in upgrade_decisions:
        uid = upd.get("upgrade_decision_id", "?")
        check(f"{uid}: upgrade_ready = false",
              upd.get("upgrade_ready") is False,
              f"got: {upd.get('upgrade_ready')}")

    # ==================================================================
    # 12. All decisions = blocked_missing_evidence
    # ==================================================================
    print("\n[12] All decisions = blocked_missing_evidence")
    for upd in upgrade_decisions:
        uid = upd.get("upgrade_decision_id", "?")
        check(f"{uid}: decision = blocked_missing_evidence",
              upd.get("decision") == "blocked_missing_evidence",
              f"got: {upd.get('decision')}")

    # ==================================================================
    # 13. All send_allowed = false
    # ==================================================================
    print("\n[13] All send_allowed = false")
    for upd in upgrade_decisions:
        uid = upd.get("upgrade_decision_id", "?")
        check(f"{uid}: send_allowed = false",
              upd.get("send_allowed") is False,
              f"got: {upd.get('send_allowed')}")

    # ==================================================================
    # 14. All tg_test_group_allowed = false
    # ==================================================================
    print("\n[14] All tg_test_group_allowed = false")
    for upd in upgrade_decisions:
        uid = upd.get("upgrade_decision_id", "?")
        check(f"{uid}: tg_test_group_allowed = false",
              upd.get("tg_test_group_allowed") is False,
              f"got: {upd.get('tg_test_group_allowed')}")

    # ==================================================================
    # 15. All public_send_allowed = false
    # ==================================================================
    print("\n[15] All public_send_allowed = false")
    for upd in upgrade_decisions:
        uid = upd.get("upgrade_decision_id", "?")
        check(f"{uid}: public_send_allowed = false",
              upd.get("public_send_allowed") is False,
              f"got: {upd.get('public_send_allowed')}")

    # ==================================================================
    # 16. Low/unknown confidence addresses have UNKNOWN_WHALE blocker
    # ==================================================================
    print("\n[16] Low/Unknown Confidence — Exclusive Blockers")
    low_keywords = ["unknown", "low"]
    for evr in evidence_requests:
        eid = evr.get("evidence_request_id", "?")
        confidence = evr.get("current_confidence", "")
        label = evr.get("current_label", "")

        if confidence == "low" or any(kw in label.lower() for kw in low_keywords):
            # Find corresponding upgrade decision
            for upd in upgrade_decisions:
                if upd.get("address") == evr.get("address"):
                    reasons = upd.get("block_reasons", [])
                    conf_blockers = upd.get("confidence_specific_blockers", [])

                    check(f"{eid}: blocked — UNKNOWN_WHALE_REQUIRES_MANUAL_ATTRIBUTION in reasons",
                          "UNKNOWN_WHALE_REQUIRES_MANUAL_ATTRIBUTION" in reasons,
                          f"reasons: {reasons}")
                    check(f"{eid}: blocked — LOW_CONFIDENCE_LABEL_NOT_SENDABLE in reasons",
                          "LOW_CONFIDENCE_LABEL_NOT_SENDABLE" in reasons,
                          f"reasons: {reasons}")
                    check(f"{eid}: confidence_specific_blockers has UNKNOWN_WHALE_REQUIRES_MANUAL_ATTRIBUTION",
                          "UNKNOWN_WHALE_REQUIRES_MANUAL_ATTRIBUTION" in conf_blockers)
                    check(f"{eid}: confidence_specific_blockers has LOW_CONFIDENCE_LABEL_NOT_SENDABLE",
                          "LOW_CONFIDENCE_LABEL_NOT_SENDABLE" in conf_blockers)
                    break

    # ==================================================================
    # 17. Medium confidence addresses have MEDIUM_CONFIDENCE blocker
    # ==================================================================
    print("\n[17] Medium Confidence — Exclusive Blockers")
    for evr in evidence_requests:
        eid = evr.get("evidence_request_id", "?")
        confidence = evr.get("current_confidence", "")

        if confidence == "medium":
            for upd in upgrade_decisions:
                if upd.get("address") == evr.get("address"):
                    reasons = upd.get("block_reasons", [])
                    conf_blockers = upd.get("confidence_specific_blockers", [])

                    check(f"{eid}: blocked — MEDIUM_CONFIDENCE_REQUIRES_CORROBORATION in reasons",
                          "MEDIUM_CONFIDENCE_REQUIRES_CORROBORATION" in reasons,
                          f"reasons: {reasons}")
                    check(f"{eid}: confidence_specific_blockers has MEDIUM_CONFIDENCE_REQUIRES_CORROBORATION",
                          "MEDIUM_CONFIDENCE_REQUIRES_CORROBORATION" in conf_blockers)
                    break

    # ==================================================================
    # 18. Result JSON — Top-Level Fields
    # ==================================================================
    print("\n[18] Result JSON — Top-Level Fields")
    check("stage = v115e_whale_address_audit_evidence_pack_local_only",
          result.get("stage") == "v115e_whale_address_audit_evidence_pack_local_only",
          f"got: {result.get('stage')}")
    check("input_targets = 4",
          result.get("input_targets") == 4,
          f"got: {result.get('input_targets')}")
    check("evidence_requests = 4",
          result.get("evidence_requests") == 4,
          f"got: {result.get('evidence_requests')}")
    check("manual_audit_forms = 4",
          result.get("manual_audit_forms") == 4,
          f"got: {result.get('manual_audit_forms')}")
    check("upgrade_decisions = 4",
          result.get("upgrade_decisions") == 4,
          f"got: {result.get('upgrade_decisions')}")

    # ==================================================================
    # 19. Result JSON — Upgrade/Send Counts
    # ==================================================================
    print("\n[19] Result JSON — Upgrade/Send Counts")
    check("upgrade_ready_count = 0",
          result.get("upgrade_ready_count") == 0,
          f"got: {result.get('upgrade_ready_count')}")
    check("blocked_upgrade_count = 4",
          result.get("blocked_upgrade_count") == 4,
          f"got: {result.get('blocked_upgrade_count')}")
    check("high_confidence_after_upgrade = 0",
          result.get("high_confidence_after_upgrade") == 0,
          f"got: {result.get('high_confidence_after_upgrade')}")

    # ==================================================================
    # 20. Result JSON — Send Readiness
    # ==================================================================
    print("\n[20] Result JSON — Send Readiness")
    check("send_ready = false",
          result.get("send_ready") is False,
          f"got: {result.get('send_ready')}")
    check("tg_test_group_ready = false",
          result.get("tg_test_group_ready") is False,
          f"got: {result.get('tg_test_group_ready')}")
    check("local_review_ready = true",
          result.get("local_review_ready") is True,
          f"got: {result.get('local_review_ready')}")

    # ==================================================================
    # 21. Result JSON — Safety Invariants
    # ==================================================================
    print("\n[21] Result JSON — Safety Invariants")
    check("external_api_called = false",
          result.get("external_api_called") is False)
    check("ai_model_called = false",
          result.get("ai_model_called") is False)
    check("credentials_read = false",
          result.get("credentials_read") is False)
    check("tg_sent = false",
          result.get("tg_sent") is False)
    check("prod_state_write = false",
          result.get("prod_state_write") is False)
    check("daemon_started = false",
          result.get("daemon_started") is False)
    check("watcher_started = false",
          result.get("watcher_started") is False)
    check("files_deleted = false",
          result.get("files_deleted") is False)
    check("real_send_candidate_generated = false",
          result.get("real_send_candidate_generated") is False)

    # ==================================================================
    # 22. No credential references in any output
    # ==================================================================
    print("\n[22] No Credential References in Output Records")
    sensitive_patterns = [
        "env", "token", "cookie", "password", "api key", "API_KEY",
        "OPENAI_API_KEY", "OPENROUTER_API_KEY", "secret", "credential",
        ".env",
    ]
    all_records = evidence_requests + manual_audit_forms + upgrade_decisions
    for rec in all_records:
        rec_id = rec.get(list(rec.keys())[0] if rec else "unknown", "?")
        for key, value in rec.items():
            if isinstance(value, str):
                for pat in sensitive_patterns:
                    hit = pat.lower() in value.lower()
                    rid = rec.get("evidence_request_id",
                           rec.get("audit_form_id",
                           rec.get("upgrade_decision_id", "?")))
                    check(f"{rid}: no '{pat}' in field '{key}'",
                          not hit,
                          f"found '{pat}' in {key}")

    # ==================================================================
    # 23. No External API References
    # ==================================================================
    print("\n[23] No External API References in Output")
    api_patterns = [
        "http://", "https://", "api.", "fetch(", "curl ",
        "requests.", "urllib", "httpx",
    ]
    for rec in all_records:
        for key, value in rec.items():
            if isinstance(value, str):
                for pat in api_patterns:
                    hit = pat in value.lower()
                    rid = rec.get("evidence_request_id",
                           rec.get("audit_form_id",
                           rec.get("upgrade_decision_id", "?")))
                    check(f"{rid}: no '{pat}' in field '{key}'",
                          not hit,
                          f"found '{pat}' in {key}")

    # ==================================================================
    # 24. Evidence request — target_confidence always "high"
    # ==================================================================
    print("\n[24] Evidence Request — target_confidence always 'high'")
    for evr in evidence_requests:
        eid = evr.get("evidence_request_id", "?")
        check(f"{eid}: target_confidence = 'high'",
              evr.get("target_confidence") == "high",
              f"got: {evr.get('target_confidence')}")

    # ==================================================================
    # 25. Upgrade decision — to_confidence_requested always "high"
    # ==================================================================
    print("\n[25] Upgrade Decision — to_confidence_requested always 'high'")
    for upd in upgrade_decisions:
        uid = upd.get("upgrade_decision_id", "?")
        check(f"{uid}: to_confidence_requested = 'high'",
              upd.get("to_confidence_requested") == "high",
              f"got: {upd.get('to_confidence_requested')}")

    # ==================================================================
    # 26. Upgrade decision — from_confidence matches input
    # ==================================================================
    print("\n[26] Upgrade Decision — from_confidence matches input target")
    target_conf_map = {t["address"]: t["current_label_confidence"] for t in targets}
    for upd in upgrade_decisions:
        uid = upd.get("upgrade_decision_id", "?")
        addr = upd.get("address", "")
        expected_conf = target_conf_map.get(addr, "?")
        check(f"{uid}: from_confidence = '{expected_conf}'",
              upd.get("from_confidence") == expected_conf,
              f"expected '{expected_conf}', got '{upd.get('from_confidence')}'")

    # ==================================================================
    # 27. Missing evidence = all 4 types for all addresses
    # ==================================================================
    print("\n[27] Missing Evidence Types = 4/4 for All Addresses")
    for evr in evidence_requests:
        eid = evr.get("evidence_request_id", "?")
        missing = evr.get("missing_evidence_types", [])
        check(f"{eid}: missing_evidence_count = 4",
              evr.get("missing_evidence_count") == 4,
              f"got: {evr.get('missing_evidence_count')}")
        check(f"{eid}: missing_evidence_types = 4 items",
              len(missing) == 4,
              f"got {len(missing)}: {missing}")

    # ==================================================================
    # 28. Negative Assertions — nothing claims success
    # ==================================================================
    print("\n[28] Negative Assertions")
    check("result does NOT claim send_ready=true",
          result.get("send_ready") is not True)
    check("result does NOT claim tg_test_group_ready=true",
          result.get("tg_test_group_ready") is not True)
    check("result does NOT claim tg_sent=true",
          result.get("tg_sent") is not True)
    check("result does NOT claim prod_state_write=true",
          result.get("prod_state_write") is not True)
    check("result does NOT claim real_send_candidate_generated=true",
          result.get("real_send_candidate_generated") is not True)
    check("result does NOT claim upgrade_ready_count > 0",
          result.get("upgrade_ready_count", 0) == 0)
    check("result does NOT claim high_confidence_after_upgrade > 0",
          result.get("high_confidence_after_upgrade", 0) == 0)

    # ==================================================================
    # 29. v114A-v115D old results not modified
    # ==================================================================
    print("\n[29] v114A-v115D Old Results Not Modified")
    protected = [
        (V115B_UPGRADE_TARGETS, "v115B upgrade targets"),
        (V115B_ROUTING, "v115B routing policy"),
        (V115B_SEND_GATE, "v115B send preview gate"),
        (V115D_PREVIEW_RECORDS, "v115D preview records"),
        (V115D_GATE_DECISIONS, "v115D gate decisions"),
        (V115D_RESULT, "v115D result"),
        (V115C_TEMPLATES, "v115C templates"),
        (V115C_RESULT, "v115C result"),
        (V114C_REVIEW_CARDS, "v114C review cards"),
    ]
    for path, name in protected:
        check(f"{name} still exists",
              file_exists(path),
              f"file may have been deleted: {path}")

    # ==================================================================
    # 30. Report Content
    # ==================================================================
    print("\n[30] Markdown Report Content")
    if file_exists(V115E_REPORT):
        with open(V115E_REPORT, "r", encoding="utf-8") as f:
            report_text = f.read()

        check("report mentions v115E", "v115E" in report_text)
        check("report mentions evidence", "evidence" in report_text.lower())
        check("report mentions audit", "audit" in report_text.lower())
        check("report mentions upgrade", "upgrade" in report_text.lower())
        check("report mentions blocked", "blocked" in report_text.lower())
        check("report mentions safety invariants",
              "safety" in report_text.lower() or "invariant" in report_text.lower())
        check("report mentions upgrade_ready_count",
              "upgrade_ready_count" in report_text)
        check("report mentions blocked_upgrade_count",
              "blocked_upgrade_count" in report_text)
    else:
        check("report file exists for content check", False, "file not found")

    # ==================================================================
    # 31. Handoff Content
    # ==================================================================
    print("\n[31] Handoff Markdown Content")
    if file_exists(V115E_HANDOFF):
        with open(V115E_HANDOFF, "r", encoding="utf-8") as f:
            handoff_text = f.read()

        check("handoff mentions v115E", "v115E" in handoff_text)
        check("handoff mentions evidence", "evidence" in handoff_text.lower())
        check("handoff mentions upgrade_ready_count",
              "upgrade_ready_count" in handoff_text)
        check("handoff mentions blocked_upgrade_count",
              "blocked_upgrade_count" in handoff_text)
        check("handoff mentions safety invariants",
              "safety" in handoff_text.lower() or "invariant" in handoff_text.lower())
        check("handoff mentions operator actions",
              "operator" in handoff_text.lower() or "Operator" in handoff_text)
    else:
        check("handoff file exists for content check", False, "file not found")

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
