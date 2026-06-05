#!/usr/bin/env python3
"""
Test suite for v115D Whale One-Shot Send Preview Gate — Local Only
===================================================================
Validates that the v115D send preview gate runner produced correct outputs
with all safety invariants, preview record requirements, gate decisions,
payload hashes, no-repeat keys, cooldown keys, and block decisions.

This test ONLY verifies generated files — it does NOT make any
external API calls, send TG, or write production state.
"""

import json
import os
import sys
import re

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RESULTS_DIR = os.path.join(BASE_DIR, "results")
CONFIG_DIR = os.path.join(BASE_DIR, "config")
RUNS_DIR = os.path.join(BASE_DIR, "runs", "market_radar")

# v115D outputs
V115D_RESULT = os.path.join(
    RESULTS_DIR, "market_radar_v115d_whale_one_shot_send_preview_gate_result.json"
)
V115D_PREVIEW_RECORDS = os.path.join(
    RESULTS_DIR, "market_radar_v115d_whale_one_shot_send_preview_records.jsonl"
)
V115D_GATE_DECISIONS = os.path.join(
    RESULTS_DIR, "market_radar_v115d_whale_one_shot_send_preview_gate_decisions.jsonl"
)
V115D_REPORT = os.path.join(
    RUNS_DIR, "v115d_whale_one_shot_send_preview_gate_local_only.md"
)
V115D_HANDOFF = os.path.join(
    RUNS_DIR, "v115d_whale_one_shot_send_preview_gate_local_only_handoff.md"
)

# v115C input (must still exist)
V115C_TEMPLATES = os.path.join(
    RESULTS_DIR, "market_radar_v115c_whale_tg_test_copy_templates.jsonl"
)
V115C_RESULT = os.path.join(
    RESULTS_DIR, "market_radar_v115c_whale_tg_test_copy_template_gate_result.json"
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
V115B_COOLDOWN = os.path.join(
    CONFIG_DIR, "market_radar_v115b_whale_rollback_cooldown_policy.json"
)

# v115A inputs (must still exist)
V115A_RESULT = os.path.join(
    RESULTS_DIR, "market_radar_v115a_whale_delta_send_readiness_gate_result.json"
)

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


# ===========================================================================
# No-repeat key regex: {address}_{asset}_{side}_{delta_type}_{date}
# ===========================================================================
NO_REPEAT_KEY_RE = re.compile(
    r'^0x[0-9a-fA-F]{40}_[A-Z]+_(long|short|unknown)_[a-z_]+_\d{8}$'
)


def validate_no_repeat_key(key: str) -> bool:
    """Validate no-repeat key format: {address}_{asset}_{side}_{delta_type}_{date}"""
    parts = key.rsplit("_", 1)
    if len(parts) != 2:
        return False
    date_part = parts[1]
    if len(date_part) != 8 or not date_part.isdigit():
        return False
    return bool(NO_REPEAT_KEY_RE.match(key))


# ===========================================================================
# Cooldown key regex: {address}_{asset}_{date}
# ===========================================================================
COOLDOWN_KEY_RE = re.compile(
    r'^0x[0-9a-fA-F]{40}_[A-Z]+_\d{8}$'
)


def validate_cooldown_key(key: str) -> bool:
    """Validate cooldown key format: {address}_{asset}_{date}"""
    parts = key.rsplit("_", 1)
    if len(parts) != 2:
        return False
    date_part = parts[1]
    if len(date_part) != 8 or not date_part.isdigit():
        return False
    return bool(COOLDOWN_KEY_RE.match(key))


def main():
    global passed, failed

    print("=" * 70)
    print("v115D Test Suite — Whale One-Shot Send Preview Gate")
    print("=" * 70)

    # ==================================================================
    # 1. File Existence — v115D Outputs
    # ==================================================================
    print("\n[1] File Existence — v115D Outputs")
    check("preview records JSONL exists", file_exists(V115D_PREVIEW_RECORDS))
    check("gate decisions JSONL exists", file_exists(V115D_GATE_DECISIONS))
    check("result JSON exists", file_exists(V115D_RESULT))
    check("markdown report exists", file_exists(V115D_REPORT))
    check("handoff markdown exists", file_exists(V115D_HANDOFF))

    # ==================================================================
    # 2. File Existence — v115C Inputs (must still exist)
    # ==================================================================
    print("\n[2] File Existence — v115C Inputs (still intact)")
    check("v115C templates still exist", file_exists(V115C_TEMPLATES))
    check("v115C result still exists", file_exists(V115C_RESULT))

    # ==================================================================
    # 3. File Existence — v115B Inputs (must still exist)
    # ==================================================================
    print("\n[3] File Existence — v115B Inputs (still intact)")
    check("v115B upgrade targets still exist", file_exists(V115B_UPGRADE_TARGETS))
    check("v115B routing policy still exists", file_exists(V115B_ROUTING))
    check("v115B send preview gate policy still exists", file_exists(V115B_SEND_GATE))
    check("v115B cooldown policy still exists", file_exists(V115B_COOLDOWN))

    # ==================================================================
    # 4. File Existence — v115A Input (must still exist)
    # ==================================================================
    print("\n[4] File Existence — v115A Input (still intact)")
    check("v115A result still exists", file_exists(V115A_RESULT))

    # ==================================================================
    # 5. Data Loading
    # ==================================================================
    print("\n[5] Data Loading")
    preview_records = load_jsonl(V115D_PREVIEW_RECORDS)
    gate_decisions = load_jsonl(V115D_GATE_DECISIONS)
    result = load_json(V115D_RESULT)

    check("preview records JSONL parsed", isinstance(preview_records, list))
    check("gate decisions JSONL parsed", isinstance(gate_decisions, list))
    check("result JSON parsed", isinstance(result, dict))

    # ==================================================================
    # 6. Preview Records Count = 4
    # ==================================================================
    print("\n[6] Preview Records Count")
    check(f"preview records count = 4 (got {len(preview_records)})",
          len(preview_records) == 4)
    check(f"gate decisions count = 4 (got {len(gate_decisions)})",
          len(gate_decisions) == 4)
    check("preview records and gate decisions have same count",
          len(preview_records) == len(gate_decisions))

    # ==================================================================
    # 7. Preview IDs are unique
    # ==================================================================
    print("\n[7] Preview ID Uniqueness")
    preview_ids = [p.get("preview_id") for p in preview_records]
    check("4 unique preview IDs",
          len(set(preview_ids)) == len(preview_ids),
          f"got {len(set(preview_ids))} unique out of {len(preview_ids)}")

    # ==================================================================
    # 8. Payload Hash — Non-Empty and Unique
    # ==================================================================
    print("\n[8] Payload Hash — Non-Empty and Unique")
    payload_hashes = []
    for p in preview_records:
        pid = p.get("preview_id", "?")
        ph = p.get("payload_hash", "")
        check(f"{pid}: payload_hash is non-empty",
              bool(ph) and len(ph) == 64,
              f"got length {len(ph)}")
        # Must be hex string (SHA-256 = 64 hex chars)
        check(f"{pid}: payload_hash is valid hex (64 chars)",
              len(ph) == 64 and all(c in "0123456789abcdef" for c in ph.lower()),
              f"got: {ph[:20]}...")
        payload_hashes.append(ph)

    unique_hashes = len(set(payload_hashes))
    check(f"payload_hashes are unique: {unique_hashes}/4",
          unique_hashes == 4,
          f"got {unique_hashes} unique, {4 - unique_hashes} duplicates")

    # ==================================================================
    # 9. No-Repeat Key — Non-Empty and Valid Format
    # ==================================================================
    print("\n[9] No-Repeat Key — Non-Empty and Valid Format")
    for p in preview_records:
        pid = p.get("preview_id", "?")
        nrk = p.get("no_repeat_key", "")
        check(f"{pid}: no_repeat_key is non-empty",
              bool(nrk),
              f"got empty string")
        if nrk:
            check(f"{pid}: no_repeat_key matches format {{address}}_{{asset}}_{{side}}_{{delta_type}}_{{date}}",
                  validate_no_repeat_key(nrk),
                  f"got: {nrk}")

    # ==================================================================
    # 10. Cooldown Key — Non-Empty and Valid Format
    # ==================================================================
    print("\n[10] Cooldown Key — Non-Empty and Valid Format")
    for p in preview_records:
        pid = p.get("preview_id", "?")
        ck = p.get("cooldown_key", "")
        check(f"{pid}: cooldown_key is non-empty",
              bool(ck),
              f"got empty string")
        if ck:
            check(f"{pid}: cooldown_key matches format {{address}}_{{asset}}_{{date}}",
                  validate_cooldown_key(ck),
                  f"got: {ck}")

    # ==================================================================
    # 11. All Previews Blocked = True
    # ==================================================================
    print("\n[11] All Previews Blocked = True")
    for p in preview_records:
        pid = p.get("preview_id", "?")
        check(f"{pid}: blocked = true",
              p.get("blocked") is True,
              f"got: {p.get('blocked')}")

    # ==================================================================
    # 12. All send_allowed = False
    # ==================================================================
    print("\n[12] All send_allowed = False")
    for p in preview_records:
        pid = p.get("preview_id", "?")
        check(f"{pid}: send_allowed = false",
              p.get("send_allowed") is False,
              f"got: {p.get('send_allowed')}")

    # ==================================================================
    # 13. All operator_approval = False
    # ==================================================================
    print("\n[13] All operator_approval = False")
    for p in preview_records:
        pid = p.get("preview_id", "?")
        check(f"{pid}: operator_approval = false",
              p.get("operator_approval") is False,
              f"got: {p.get('operator_approval')}")

    # ==================================================================
    # 14. All scope = tg_test_group_only
    # ==================================================================
    print("\n[14] All scope = tg_test_group_only")
    for p in preview_records:
        pid = p.get("preview_id", "?")
        check(f"{pid}: scope = tg_test_group_only",
              p.get("scope") == "tg_test_group_only",
              f"got: {p.get('scope')}")

    # ==================================================================
    # 15. Low confidence / Unknown whale must have label upgrade blockers
    # ==================================================================
    print("\n[15] Low Confidence / Unknown Whale — Extra Blockers")
    for p in preview_records:
        pid = p.get("preview_id", "?")
        confidence = p.get("label_confidence", "")
        label = p.get("label", "")
        reasons = p.get("block_reasons", [])

        if confidence == "low" or "unknown" in label.lower():
            check(f"{pid}: blocked — UNKNOWN_WHALE_NOT_SENDABLE in reasons",
                  "UNKNOWN_WHALE_NOT_SENDABLE" in reasons,
                  f"reasons: {reasons}")
            check(f"{pid}: blocked — LABEL_UPGRADE_REQUIRED in reasons",
                  "LABEL_UPGRADE_REQUIRED" in reasons,
                  f"reasons: {reasons}")

    # ==================================================================
    # 16. All previews have required block reasons (minimum set)
    # ==================================================================
    print("\n[16] All Previews Have Required Minimum Block Reasons")
    required_base_reasons = [
        "LABEL_CONFIDENCE_BELOW_HIGH",
        "OPERATOR_APPROVAL_MISSING",
        "TG_SEND_DISABLED_BY_DEFAULT",
        "NOT_SEND_READY",
    ]
    for p in preview_records:
        pid = p.get("preview_id", "?")
        reasons = p.get("block_reasons", [])
        for r in required_base_reasons:
            check(f"{pid}: has block reason '{r}'",
                  r in reasons,
                  f"reasons: {reasons}")

    # ==================================================================
    # 17. Gate decisions — all blocked = True
    # ==================================================================
    print("\n[17] Gate Decisions — All Blocked = True")
    for d in gate_decisions:
        gid = d.get("preview_id", "?")
        check(f"{gid}: gate blocked = true",
              d.get("blocked") is True,
              f"got: {d.get('blocked')}")

    # ==================================================================
    # 18. Gate decisions — all send_allowed = False
    # ==================================================================
    print("\n[18] Gate Decisions — All send_allowed = False")
    for d in gate_decisions:
        gid = d.get("preview_id", "?")
        check(f"{gid}: gate send_allowed = false",
              d.get("send_allowed") is False,
              f"got: {d.get('send_allowed')}")

    # ==================================================================
    # 19. Gate decisions — all operator_approval = False
    # ==================================================================
    print("\n[19] Gate Decisions — All operator_approval = False")
    for d in gate_decisions:
        gid = d.get("preview_id", "?")
        check(f"{gid}: gate operator_approval = false",
              d.get("operator_approval") is False,
              f"got: {d.get('operator_approval')}")

    # ==================================================================
    # 20. Gate decisions — all scope = tg_test_group_only
    # ==================================================================
    print("\n[20] Gate Decisions — All scope = tg_test_group_only")
    for d in gate_decisions:
        gid = d.get("preview_id", "?")
        check(f"{gid}: gate scope = tg_test_group_only",
              d.get("scope") == "tg_test_group_only",
              f"got: {d.get('scope')}")

    # ==================================================================
    # 21. Gate decisions — all send_ready = False
    # ==================================================================
    print("\n[21] Gate Decisions — All send_ready = False")
    for d in gate_decisions:
        gid = d.get("preview_id", "?")
        check(f"{gid}: send_ready = false",
              d.get("send_ready") is False,
              f"got: {d.get('send_ready')}")

    # ==================================================================
    # 22. Gate decisions — all tg_test_group_ready = False
    # ==================================================================
    print("\n[22] Gate Decisions — All tg_test_group_ready = False")
    for d in gate_decisions:
        gid = d.get("preview_id", "?")
        check(f"{gid}: tg_test_group_ready = false",
              d.get("tg_test_group_ready") is False,
              f"got: {d.get('tg_test_group_ready')}")

    # ==================================================================
    # 23. Gate decisions — all local_review_ready = True
    # ==================================================================
    print("\n[23] Gate Decisions — All local_review_ready = True")
    for d in gate_decisions:
        gid = d.get("preview_id", "?")
        check(f"{gid}: local_review_ready = true",
              d.get("local_review_ready") is True,
              f"got: {d.get('local_review_ready')}")

    # ==================================================================
    # 24. Gate decisions — No real send candidate
    # ==================================================================
    print("\n[24] Gate Decisions — No Real Send Candidate")
    for d in gate_decisions:
        gid = d.get("preview_id", "?")
        check(f"{gid}: real_send_candidate_generated = false",
              d.get("real_send_candidate_generated") is False,
              f"got: {d.get('real_send_candidate_generated')}")

    # ==================================================================
    # 25. Gate decisions — No TG sent
    # ==================================================================
    print("\n[25] Gate Decisions — No TG Sent")
    for d in gate_decisions:
        gid = d.get("preview_id", "?")
        check(f"{gid}: tg_sent = false",
              d.get("tg_sent") is False,
              f"got: {d.get('tg_sent')}")

    # ==================================================================
    # 26. Gate decisions — No prod state write
    # ==================================================================
    print("\n[26] Gate Decisions — No Prod State Write")
    for d in gate_decisions:
        gid = d.get("preview_id", "?")
        check(f"{gid}: prod_state_write = false",
              d.get("prod_state_write") is False,
              f"got: {d.get('prod_state_write')}")

    # ==================================================================
    # 27. Result JSON — Top-Level Fields
    # ==================================================================
    print("\n[27] Result JSON — Top-Level Fields")
    check("stage = v115d_whale_one_shot_send_preview_gate_local_only",
          result.get("stage") == "v115d_whale_one_shot_send_preview_gate_local_only",
          f"got: {result.get('stage')}")
    check("input_templates = 4",
          result.get("input_templates") == 4,
          f"got: {result.get('input_templates')}")
    check("preview_records = 4",
          result.get("preview_records") == 4,
          f"got: {result.get('preview_records')}")
    check("gate_decisions = 4",
          result.get("gate_decisions") == 4,
          f"got: {result.get('gate_decisions')}")
    check("sendable_previews = 0",
          result.get("sendable_previews") == 0,
          f"got: {result.get('sendable_previews')}")
    check("blocked_previews = 4",
          result.get("blocked_previews") == 4,
          f"got: {result.get('blocked_previews')}")
    check("unique_payload_hashes = 4",
          result.get("unique_payload_hashes") == 4,
          f"got: {result.get('unique_payload_hashes')}")
    check("duplicate_payload_hashes = 0",
          result.get("duplicate_payload_hashes") == 0,
          f"got: {result.get('duplicate_payload_hashes')}")

    # ==================================================================
    # 28. Result JSON — Send Readiness
    # ==================================================================
    print("\n[28] Result JSON — Send Readiness")
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
    # 29. Result JSON — Safety Invariants
    # ==================================================================
    print("\n[29] Result JSON — Safety Invariants")
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
    # 30. No .env / token / cookie / password / API key references
    # ==================================================================
    print("\n[30] No Credential References in Preview Records")
    sensitive_patterns = [
        "env", "token", "cookie", "password", "api key", "API_KEY",
        "OPENAI_API_KEY", "OPENROUTER_API_KEY", "secret", "credential",
        ".env",
    ]
    for p in preview_records:
        pid = p.get("preview_id", "?")
        # Check all string fields
        for key, value in p.items():
            if isinstance(value, str):
                for pat in sensitive_patterns:
                    hit = pat.lower() in value.lower()
                    check(f"{pid}: no '{pat}' in field '{key}'",
                          not hit,
                          f"found '{pat}' in {key}")

    # ==================================================================
    # 31. No External API References
    # ==================================================================
    print("\n[31] No External API References")
    api_patterns = [
        "http://", "https://", "api.", "fetch(", "curl ",
        "requests.", "urllib", "httpx",
    ]
    for p in preview_records:
        pid = p.get("preview_id", "?")
        copy_text = p.get("copy_text", "")
        copy_lower = copy_text.lower()
        for pat in api_patterns:
            hit = pat in copy_lower
            check(f"{pid}: no '{pat}' in copy text",
                  not hit,
                  f"found '{pat}' in copy text")

    # ==================================================================
    # 32. Preview Record Field Completeness
    # ==================================================================
    print("\n[32] Preview Record Field Completeness")
    required_preview_fields = [
        "preview_id", "template_id", "address", "asset", "side",
        "delta_type", "label", "label_confidence", "copy_text",
        "payload_hash", "no_repeat_key", "cooldown_key", "scope",
        "operator_approval", "user_preauthorization_scope",
        "send_allowed", "blocked", "block_reasons",
    ]
    for p in preview_records:
        pid = p.get("preview_id", "?")
        for field in required_preview_fields:
            check(f"{pid}: has field '{field}'",
                  field in p,
                  f"missing field: {field}")

    # ==================================================================
    # 33. Gate Decision Field Completeness
    # ==================================================================
    print("\n[33] Gate Decision Field Completeness")
    required_gate_fields = [
        "preview_id", "template_id", "address", "label",
        "label_confidence", "asset", "delta_type",
        "payload_hash", "no_repeat_key", "cooldown_key",
        "scope", "operator_approval", "send_allowed",
        "blocked", "block_reasons", "send_ready",
        "tg_test_group_ready", "local_review_ready",
        "tg_sent", "prod_state_write",
        "real_send_candidate_generated", "gate_passed",
    ]
    for d in gate_decisions:
        gid = d.get("preview_id", "?")
        for field in required_gate_fields:
            check(f"{gid}: has field '{field}'",
                  field in d,
                  f"missing field: {field}")

    # ==================================================================
    # 34. No modification of v114A-v115C old results
    # ==================================================================
    print("\n[34] No modification of v114A-v115C old results")
    # Check that v115C files are still valid JSON/JSONL
    try:
        v115c_result = load_json(V115C_RESULT)
        check("v115C result is still valid JSON", isinstance(v115c_result, dict))
    except Exception as e:
        check("v115C result is still valid JSON", False, str(e))

    try:
        v115c_templates = load_jsonl(V115C_TEMPLATES)
        check("v115C templates still have 4 records",
              len(v115c_templates) == 4,
              f"got {len(v115c_templates)}")
    except Exception as e:
        check("v115C templates are still valid JSONL", False, str(e))

    try:
        v115b_targets = load_jsonl(V115B_UPGRADE_TARGETS)
        check("v115B targets still have 4 records",
              len(v115b_targets) == 4,
              f"got {len(v115b_targets)}")
    except Exception as e:
        check("v115B targets are still valid JSONL", False, str(e))

    # ==================================================================
    # 35. Report Content
    # ==================================================================
    print("\n[35] Markdown Report Content")
    if file_exists(V115D_REPORT):
        with open(V115D_REPORT, "r", encoding="utf-8") as f:
            report_text = f.read()

        check("report mentions v115D", "v115D" in report_text)
        check("report mentions preview", "preview" in report_text.lower())
        check("report mentions gate", "gate" in report_text.lower())
        check("report mentions blocked", "blocked" in report_text.lower() or "BLOCKED" in report_text)
        check("report mentions payload hash", "payload" in report_text.lower() or "hash" in report_text.lower())
        check("report mentions no-repeat", "no-repeat" in report_text.lower() or "no_repeat" in report_text.lower())
        check("report mentions cooldown", "cooldown" in report_text.lower())
        check("report mentions sendable_previews",
              "sendable_previews" in report_text.lower())
        check("report mentions safety invariants",
              "safety" in report_text.lower() or "invariant" in report_text.lower())
    else:
        check("report file exists for content check", False, "file not found")

    # ==================================================================
    # 36. Handoff Content
    # ==================================================================
    print("\n[36] Handoff Markdown Content")
    if file_exists(V115D_HANDOFF):
        with open(V115D_HANDOFF, "r", encoding="utf-8") as f:
            handoff_text = f.read()

        check("handoff mentions v115D", "v115D" in handoff_text)
        check("handoff mentions preview records",
              "preview" in handoff_text.lower())
        check("handoff mentions sendable_previews",
              "sendable_previews" in handoff_text.lower())
        check("handoff mentions safety invariants",
              "safety" in handoff_text.lower() or "invariant" in handoff_text.lower())
    else:
        check("handoff file exists for content check", False, "file not found")

    # ==================================================================
    # 37. Negative Assertions
    # ==================================================================
    print("\n[37] Negative Assertions")
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

    # ==================================================================
    # 38. No deletion of v114A-v115C files
    # ==================================================================
    print("\n[38] v114A-v115C Files Not Deleted")
    protected_paths = [
        V115C_TEMPLATES,
        V115C_RESULT,
        V115B_UPGRADE_TARGETS,
        V115B_ROUTING,
        V115B_SEND_GATE,
        V115B_COOLDOWN,
        V115A_RESULT,
    ]
    for path in protected_paths:
        fname = os.path.basename(path)
        check(f"{fname} still exists",
              file_exists(path),
              f"file may have been deleted")

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
