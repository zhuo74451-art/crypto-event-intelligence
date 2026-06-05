#!/usr/bin/env python3
"""
Test suite for v115C Whale TG Test Copy Template Gate — Local Only
===================================================================
Validates that the v115C template gate runner produced correct outputs
with all safety invariants, template requirements, gate decisions,
banned phrase checks, confidence disclosures, and send guards.

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

# v115C outputs
V115C_RESULT = os.path.join(
    RESULTS_DIR, "market_radar_v115c_whale_tg_test_copy_template_gate_result.json"
)
V115C_TEMPLATES = os.path.join(
    RESULTS_DIR, "market_radar_v115c_whale_tg_test_copy_templates.jsonl"
)
V115C_GATE_DECISIONS = os.path.join(
    RESULTS_DIR, "market_radar_v115c_whale_tg_test_copy_gate_decisions.jsonl"
)
V115C_REPORT = os.path.join(
    RUNS_DIR, "v115c_whale_tg_test_copy_template_gate_local_only.md"
)
V115C_HANDOFF = os.path.join(
    RUNS_DIR, "v115c_whale_tg_test_copy_template_gate_local_only_handoff.md"
)

# v115B inputs (must still exist and be unchanged)
V115B_UPGRADE_TARGETS = os.path.join(
    RESULTS_DIR, "market_radar_v115b_whale_label_upgrade_targets.jsonl"
)
V115B_TG_COPY_GATE = os.path.join(
    CONFIG_DIR, "market_radar_v115b_whale_tg_test_copy_gate_policy.json"
)

# v114C input (must still exist)
V114C_CARDS = os.path.join(
    RESULTS_DIR, "market_radar_v114c_whale_delta_operator_review_cards.jsonl"
)

# Banned phrases
BANNED_PHRASES = [
    "确认", "实锤", "正式信号", "强信号",
    "可直接发布", "立即发送",
    "confirmed", "verified", "certain", "guaranteed",
    "正式", "production signal", "send immediately",
    "publish now", "strong signal",
]

# Required template elements
REQUIRED_ELEMENTS = [
    "TEST-ONLY",
    "Source: HyperLiquid",
    "Not financial advice",
    "Not production state",
    "label_confidence",
    "Address:",
    "Delta:",
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
    print("v115C Test Suite — Whale TG Test Copy Template Gate")
    print("=" * 70)

    # ==================================================================
    # 1. File Existence — v115C Outputs
    # ==================================================================
    print("\n[1] File Existence — v115C Outputs")
    check("templates JSONL exists", file_exists(V115C_TEMPLATES))
    check("gate decisions JSONL exists", file_exists(V115C_GATE_DECISIONS))
    check("result JSON exists", file_exists(V115C_RESULT))
    check("markdown report exists", file_exists(V115C_REPORT))
    check("handoff markdown exists", file_exists(V115C_HANDOFF))

    # ==================================================================
    # 2. File Existence — v115B Inputs (must still exist)
    # ==================================================================
    print("\n[2] File Existence — v115B Inputs (still intact)")
    check("v115B upgrade targets still exist", file_exists(V115B_UPGRADE_TARGETS))
    check("v115B TG copy gate policy still exists", file_exists(V115B_TG_COPY_GATE))
    check("v114C review cards still exist", file_exists(V114C_CARDS))

    # ==================================================================
    # 3. Data Loading
    # ==================================================================
    print("\n[3] Data Loading")
    templates = load_jsonl(V115C_TEMPLATES)
    gate_decisions = load_jsonl(V115C_GATE_DECISIONS)
    result = load_json(V115C_RESULT)

    check("templates JSONL parsed", isinstance(templates, list))
    check("gate decisions JSONL parsed", isinstance(gate_decisions, list))
    check("result JSON parsed", isinstance(result, dict))

    # ==================================================================
    # 4. Template Count
    # ==================================================================
    print("\n[4] Template Count")
    check(f"templates count = 4 (got {len(templates)})",
          len(templates) == 4)
    check(f"gate decisions count = 4 (got {len(gate_decisions)})",
          len(gate_decisions) == 4)
    check("templates and gate decisions have same count",
          len(templates) == len(gate_decisions))

    # ==================================================================
    # 5. Template IDs are unique
    # ==================================================================
    print("\n[5] Template ID Uniqueness")
    template_ids = [t.get("template_id") for t in templates]
    check("4 unique template IDs",
          len(set(template_ids)) == len(template_ids),
          f"got {len(set(template_ids))} unique out of {len(template_ids)}")

    # ==================================================================
    # 6. Required Elements — Every Template
    # ==================================================================
    print("\n[6] Required Elements — Every Template")
    for t in templates:
        tid = t.get("template_id", "?")
        copy_text = t.get("copy_text", "")

        check(f"{tid}: [TEST-ONLY — NOT PRODUCTION] present",
              "[TEST-ONLY — NOT PRODUCTION]" in copy_text)
        check(f"{tid}: source_disclaimer present",
              "Source: HyperLiquid" in copy_text)
        check(f"{tid}: not_financial_advice present",
              "not financial advice" in copy_text.lower())
        check(f"{tid}: not_production_state present",
              "not production state" in copy_text.lower())
        check(f"{tid}: label_confidence tag present",
              "[label_confidence:" in copy_text)
        check(f"{tid}: address tag present",
              "Address:" in copy_text)
        check(f"{tid}: delta_summary present",
              "Delta:" in copy_text)
        check(f"{tid}: operator_review present",
              "operator review" in copy_text.lower()
              or "Operator review" in copy_text)

    # ==================================================================
    # 7. Banned Phrases — Must Be 0 Hits
    # ==================================================================
    print("\n[7] Banned Phrases — Must Be 0 Hits")
    for t in templates:
        tid = t.get("template_id", "?")
        copy_text = t.get("copy_text", "")
        copy_lower = copy_text.lower()

        for phrase in BANNED_PHRASES:
            hit = phrase.lower() in copy_lower
            check(f"{tid}: banned phrase '{phrase}' NOT in copy",
                  not hit,
                  f"FOUND banned phrase '{phrase}' in template")

    # ==================================================================
    # 8. Gate Decisions — All Banned Phrase Hits = 0
    # ==================================================================
    print("\n[8] Gate Decisions — Banned Phrase Hits = 0")
    for d in gate_decisions:
        gid = d.get("template_id", "?")
        check(f"{gid}: banned_phrase_hits is empty",
              d.get("banned_phrase_hits") == [],
              f"got: {d.get('banned_phrase_hits')}")

    # ==================================================================
    # 9. Gate Decisions — All Required Elements Missing = 0
    # ==================================================================
    print("\n[9] Gate Decisions — Required Elements Missing = 0")
    for d in gate_decisions:
        gid = d.get("template_id", "?")
        check(f"{gid}: required_elements_missing is empty",
              d.get("required_elements_missing") == [],
              f"got: {d.get('required_elements_missing')}")

    # ==================================================================
    # 10. Gate Decisions — All Passed
    # ==================================================================
    print("\n[10] Gate Decisions — All Passed")
    for d in gate_decisions:
        gid = d.get("template_id", "?")
        check(f"{gid}: passed = true",
              d.get("passed") is True,
              f"got: {d.get('passed')}, failed_reasons={d.get('failed_reasons')}")

    # ==================================================================
    # 11. Unknown Whale Downgrade — Low Confidence
    # ==================================================================
    print("\n[11] Unknown Whale Downgrade — Low Confidence Targets")
    low_templates = [t for t in templates if t.get("label_confidence") == "low"]
    check(f"low confidence templates exist ({len(low_templates)})",
          len(low_templates) >= 2,
          f"got {len(low_templates)}")

    for t in low_templates:
        tid = t.get("template_id", "?")
        copy_lower = t.get("copy_text", "").lower()

        # Must contain downgrade language
        has_downgrade = any(term in copy_lower for term in [
            "unknown whale", "unverified label",
            "low confidence", "not been verified"
        ])
        check(f"{tid}: low confidence has downgrade language",
              has_downgrade,
              "missing required downgrade terms for low confidence")

        # Must NOT contain confirmed/verified/certain
        # NOTE: "known whale" check must avoid false positive on "unknown whale"
        has_confirmed = any(term in copy_lower for term in [
            "confirmed entity", "verified whale",
            "certain entity"
        ])
        if "known whale" in copy_lower and "unknown whale" not in copy_lower:
            has_confirmed = True
        check(f"{tid}: low confidence does NOT present as confirmed",
              not has_confirmed,
              "unknown whale incorrectly presented as confirmed entity")

    # ==================================================================
    # 12. Unknown Whale Downgrade — Gate Decisions
    # ==================================================================
    print("\n[12] Unknown Whale Downgrade — Gate Decisions")
    low_decisions = [d for d in gate_decisions if d.get("label_confidence") == "low"]
    for d in low_decisions:
        gid = d.get("template_id", "?")
        check(f"{gid}: unknown_whale_downgrade_ok = true",
              d.get("unknown_whale_downgrade_ok") is True,
              f"got: {d.get('unknown_whale_downgrade_ok')}")

    # ==================================================================
    # 13. Medium Confidence Disclosure
    # ==================================================================
    print("\n[13] Medium Confidence Disclosure")
    medium_templates = [t for t in templates if t.get("label_confidence") == "medium"]
    check(f"medium confidence templates exist ({len(medium_templates)})",
          len(medium_templates) >= 2,
          f"got {len(medium_templates)}")

    for t in medium_templates:
        tid = t.get("template_id", "?")
        copy_lower = t.get("copy_text", "").lower()
        has_medium = any(term in copy_lower for term in [
            "medium confidence", "needs additional verification",
            "needs further verification"
        ])
        check(f"{tid}: medium confidence disclosure present",
              has_medium,
              "missing medium confidence disclosure")

    # ==================================================================
    # 14. Confidence Disclosure — Gate Decisions
    # ==================================================================
    print("\n[14] Confidence Disclosure — Gate Decisions")
    for d in gate_decisions:
        gid = d.get("template_id", "?")
        check(f"{gid}: confidence_disclosure_ok = true",
              d.get("confidence_disclosure_ok") is True,
              f"got: {d.get('confidence_disclosure_ok')}")

    # ==================================================================
    # 15. All Send Guards = False
    # ==================================================================
    print("\n[15] All Send Guards = False")
    for t in templates:
        tid = t.get("template_id", "?")
        check(f"{tid}: send_allowed = false",
              t.get("send_allowed") is False,
              f"got: {t.get('send_allowed')}")
        check(f"{tid}: tg_sent = false",
              t.get("tg_sent") is False,
              f"got: {t.get('tg_sent')}")
        check(f"{tid}: prod_state_write = false",
              t.get("prod_state_write") is False,
              f"got: {t.get('prod_state_write')}")

    # ==================================================================
    # 16. Gate Decisions — All Send Guards = False
    # ==================================================================
    print("\n[16] Gate Decisions — Send Guards = False")
    for d in gate_decisions:
        gid = d.get("template_id", "?")
        check(f"{gid}: gate send_allowed = false",
              d.get("send_allowed") is False)
        check(f"{gid}: gate tg_sent = false",
              d.get("tg_sent") is False)
        check(f"{gid}: gate prod_state_write = false",
              d.get("prod_state_write") is False)

    # ==================================================================
    # 17. Result JSON — Top-Level Fields
    # ==================================================================
    print("\n[17] Result JSON — Top-Level Fields")
    check("stage = v115c_whale_tg_test_copy_template_gate_local_only",
          result.get("stage") == "v115c_whale_tg_test_copy_template_gate_local_only",
          f"got: {result.get('stage')}")
    check("version = v115C",
          result.get("version") == "v115C",
          f"got: {result.get('version')}")
    check("input_targets = 4",
          result.get("input_targets") == 4,
          f"got: {result.get('input_targets')}")
    check("templates_generated = 4",
          result.get("templates_generated") == 4,
          f"got: {result.get('templates_generated')}")
    check("gate_decisions = 4",
          result.get("gate_decisions") == 4,
          f"got: {result.get('gate_decisions')}")
    check("templates_passed = 4",
          result.get("templates_passed") == 4,
          f"got: {result.get('templates_passed')}")
    check("templates_failed = 0",
          result.get("templates_failed") == 0,
          f"got: {result.get('templates_failed')}")

    # ==================================================================
    # 18. Result JSON — Send Readiness
    # ==================================================================
    print("\n[18] Result JSON — Send Readiness")
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
    # 19. Result JSON — Safety Invariants
    # ==================================================================
    print("\n[19] Result JSON — Safety Invariants")
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
    # 20. No .env / token / cookie / password / API key references
    # ==================================================================
    print("\n[20] No Credential References in Templates")
    sensitive_patterns = [
        "env", "token", "cookie", "password", "api key", "API_KEY",
        "OPENAI_API_KEY", "OPENROUTER_API_KEY", "secret", "credential",
    ]
    for t in templates:
        tid = t.get("template_id", "?")
        copy_text = t.get("copy_text", "")
        copy_lower = copy_text.lower()
        for pat in sensitive_patterns:
            hit = pat.lower() in copy_lower
            check(f"{tid}: no '{pat}' in copy text",
                  not hit,
                  f"found '{pat}' in template copy")

    # ==================================================================
    # 21. No External API References in Templates
    # ==================================================================
    print("\n[21] No External API References in Templates")
    api_patterns = [
        "http://", "https://", "api.", "fetch(", "curl ",
        "requests.", "urllib", "httpx",
    ]
    for t in templates:
        tid = t.get("template_id", "?")
        copy_text = t.get("copy_text", "")
        copy_lower = copy_text.lower()
        for pat in api_patterns:
            hit = pat in copy_lower
            check(f"{tid}: no '{pat}' in copy text",
                  not hit,
                  f"found '{pat}' in template copy")

    # ==================================================================
    # 22. Template Structure Verification
    # ==================================================================
    print("\n[22] Template Structure Verification")
    for t in templates:
        tid = t.get("template_id", "?")
        copy_text = t.get("copy_text", "")

        # First line must be test-only marker
        lines = copy_text.strip().split("\n")
        check(f"{tid}: first line is TEST-ONLY marker",
              "[TEST-ONLY" in lines[0] if lines else False,
              f"first line: {lines[0] if lines else 'EMPTY'}")

        # Must have at least 7 lines
        check(f"{tid}: at least 7 lines in copy",
              len(lines) >= 7,
              f"got {len(lines)} lines")

    # ==================================================================
    # 23. Address Coverage — All 4 Required Addresses
    # ==================================================================
    print("\n[23] Address Coverage — All 4 Required Addresses")
    required_addresses = [
        "0x50b309f78e774a756a2230e1769729094cac9f20",
        "0x082e843a431aef031264dc232693dd710aedca88",
        "0x8def9f50456c6c4e37fa5d3d57f108ed23992dae",
        "0x6c8512516ce5669d35113a11ca8b8de322fd84f6",
    ]
    template_addresses = [t.get("address") for t in templates]
    for addr in required_addresses:
        check(f"required address present: {addr[:14]}...",
              addr in template_addresses)

    gate_addresses = [d.get("address") for d in gate_decisions]
    for addr in required_addresses:
        check(f"gate decision for address: {addr[:14]}...",
              addr in gate_addresses)

    # ==================================================================
    # 24. Template Field Completeness
    # ==================================================================
    print("\n[24] Template Field Completeness")
    required_template_fields = [
        "template_id", "version", "address", "label",
        "label_confidence", "asset", "delta_type",
        "operator_review_required", "send_allowed",
        "tg_sent", "prod_state_write", "copy_text",
        "test_only_marker", "source_disclaimer",
        "not_financial_advice", "not_production_state",
    ]
    for t in templates:
        tid = t.get("template_id", "?")
        for field in required_template_fields:
            check(f"{tid}: has field '{field}'",
                  field in t,
                  f"missing field: {field}")

    # ==================================================================
    # 25. Gate Decision Field Completeness
    # ==================================================================
    print("\n[25] Gate Decision Field Completeness")
    required_gate_fields = [
        "address", "label", "label_confidence", "template_id",
        "passed", "failed_reasons", "banned_phrase_hits",
        "required_elements_missing", "unknown_whale_downgrade_ok",
        "confidence_disclosure_ok", "send_allowed",
        "tg_sent", "prod_state_write",
    ]
    for d in gate_decisions:
        gid = d.get("template_id", "?")
        for field in required_gate_fields:
            check(f"{gid}: has field '{field}'",
                  field in d,
                  f"missing field: {field}")

    # ==================================================================
    # 26. Report Content
    # ==================================================================
    print("\n[26] Markdown Report Content")
    if file_exists(V115C_REPORT):
        with open(V115C_REPORT, "r", encoding="utf-8") as f:
            report_text = f.read()

        check("report mentions v115C", "v115C" in report_text)
        check("report mentions template", "template" in report_text.lower())
        check("report mentions gate", "gate" in report_text.lower())
        check("report mentions v115B", "v115B" in report_text)
        check("report mentions send_ready=false",
              "send_ready" in report_text.lower() and "false" in report_text.lower())
        check("report mentions safety invariants",
              "safety" in report_text.lower() or "invariant" in report_text.lower())
        check("report mentions NOT declarations",
              "NOT" in report_text)
    else:
        check("report file exists for content check", False, "file not found")

    # ==================================================================
    # 27. Handoff Content
    # ==================================================================
    print("\n[27] Handoff Markdown Content")
    if file_exists(V115C_HANDOFF):
        with open(V115C_HANDOFF, "r", encoding="utf-8") as f:
            handoff_text = f.read()

        check("handoff mentions v115C", "v115C" in handoff_text)
        check("handoff mentions templates generated",
              "template" in handoff_text.lower())
        check("handoff mentions send_ready=false",
              "send_ready" in handoff_text.lower())
        check("handoff mentions safety invariants",
              "safety" in handoff_text.lower() or "invariant" in handoff_text.lower())
    else:
        check("handoff file exists for content check", False, "file not found")

    # ==================================================================
    # 28. Negative Assertions
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
