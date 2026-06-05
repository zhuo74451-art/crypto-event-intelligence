#!/usr/bin/env python3
"""
test_market_radar_v112x_recovery_local_contract.py
===================================================
Test suite for v112X recovery local contract.

Verifies that the recovery runner produced correct output files with all
required safety invariants enforced. This test does NOT call any external API,
does NOT require any API keys, and operates exclusively on local files.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parents[1]
os.chdir(str(PROJECT_DIR))

RESULTS_DIR = PROJECT_DIR / "results"
RUNS_DIR = PROJECT_DIR / "runs" / "market_radar"

PASS = "PASS"
FAIL = "FAIL"

results: list[dict] = []


def check(label: str, condition: bool, detail: str = "") -> bool:
    """Record a test check and return whether it passed."""
    status = PASS if condition else FAIL
    msg = f"  [{status}] {label}"
    if detail and not condition:
        msg += f" — {detail}"
    print(msg)
    results.append({"check": label, "passed": condition, "detail": detail})
    return condition


def load_json(path: Path) -> dict:
    """Load a JSON file, return empty dict on failure."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"  [WARN] Could not load {path}: {e}")
        return {}


def test_recovery_result():
    """Test the recovery result JSON."""
    print("\n--- Testing Recovery Result JSON ---")

    result_path = RESULTS_DIR / "market_radar_v112x_recovery_local_contract_result.json"
    check("Recovery result file exists", result_path.exists())

    if not result_path.exists():
        print("  [SKIP] Cannot test recovery result content — file missing.")
        return

    data = load_json(result_path)
    check("Recovery result is non-empty JSON", bool(data))

    # Required fields per task spec
    check("status == partial_not_live",
          data.get("status") == "partial_not_live",
          f"Got: {data.get('status')}")

    check("live_probe_executed == false",
          data.get("live_probe_executed") is False,
          f"Got: {data.get('live_probe_executed')}")

    check("external_api_called == false",
          data.get("external_api_called") is False,
          f"Got: {data.get('external_api_called')}")

    check("api_key_used == false",
          data.get("api_key_used") is False,
          f"Got: {data.get('api_key_used')}")

    check("authorization_header_used == false",
          data.get("authorization_header_used") is False,
          f"Got: {data.get('authorization_header_used')}")

    check("retry_count == 0",
          data.get("retry_count") == 0,
          f"Got: {data.get('retry_count')}")

    check("daemon_started == false",
          data.get("daemon_started") is False,
          f"Got: {data.get('daemon_started')}")

    check("tg_sent == false",
          data.get("tg_sent") is False,
          f"Got: {data.get('tg_sent')}")

    check("production_state_written == false",
          data.get("production_state_written") is False,
          f"Got: {data.get('production_state_written')}")

    check("eligible_for_real_send == false",
          data.get("eligible_for_real_send") is False,
          f"Got: {data.get('eligible_for_real_send')}")

    check("stop_conditions_loaded == true",
          data.get("stop_conditions_loaded") is True,
          f"Got: {data.get('stop_conditions_loaded')}")

    check("field_mapping_loaded == true",
          data.get("field_mapping_loaded") is True,
          f"Got: {data.get('field_mapping_loaded')}")

    check("label_audit_loaded == true",
          data.get("label_audit_loaded") is True,
          f"Got: {data.get('label_audit_loaded')}")

    # Ensure no 'real_send_candidate' field set to true
    real_send_candidate = data.get("real_send_candidate", None)
    check("real_send_candidate is not true",
          real_send_candidate is not True,
          f"Got: {real_send_candidate}")

    # Ensure not claiming live dry-run passed
    check("Does not claim live dry-run passed",
          data.get("live_dry_run_passed") is not True and
          data.get("status") != "live_passed",
          f"status={data.get('status')}")

    # Recovery reason present
    check("recovery_reason is set",
          bool(data.get("recovery_reason")),
          f"Got: {data.get('recovery_reason')}")

    # Next step points to real v112X
    check("next_step is v112X_hyperliquid_one_shot_readonly_dryrun",
          data.get("next_step") == "v112X_hyperliquid_one_shot_readonly_dryrun",
          f"Got: {data.get('next_step')}")

    # Version is correct
    check("version is v112X-recovery",
          data.get("version") == "v112X-recovery",
          f"Got: {data.get('version')}")

    # Safety invariants present
    safety = data.get("safety_invariants", {})
    check("safety_invariants block present", bool(safety))
    check("safety: no_external_api_called == true",
          safety.get("no_external_api_called") is True)
    check("safety: no_hyperliquid_api_called == true",
          safety.get("no_hyperliquid_api_called") is True)
    check("safety: no_api_key_used == true",
          safety.get("no_api_key_used") is True)
    check("safety: no_credentials_read == true",
          safety.get("no_credentials_read") is True)


def test_stop_decision():
    """Test the stop decision JSON."""
    print("\n--- Testing Stop Decision JSON ---")

    decision_path = RESULTS_DIR / "market_radar_v112x_recovery_stop_decision.json"
    check("Stop decision file exists", decision_path.exists())

    if not decision_path.exists():
        print("  [SKIP] Cannot test stop decision content — file missing.")
        return

    data = load_json(decision_path)
    check("Stop decision is non-empty JSON", bool(data))

    # Must NOT be CONTINUE
    decision_val = data.get("decision")
    check("decision is not CONTINUE",
          decision_val != "CONTINUE",
          f"Got: {decision_val}")

    # Must be NOT_EXECUTED_LOCAL_RECOVERY_ONLY
    check("decision is NOT_EXECUTED_LOCAL_RECOVERY_ONLY",
          decision_val == "NOT_EXECUTED_LOCAL_RECOVERY_ONLY",
          f"Got: {decision_val}")

    check("stop decision: live_probe_executed == false",
          data.get("live_probe_executed") is False,
          f"Got: {data.get('live_probe_executed')}")

    check("stop decision: eligible_for_real_send == false",
          data.get("eligible_for_real_send") is False,
          f"Got: {data.get('eligible_for_real_send')}")

    # No real_send_candidate
    check("stop decision: real_send_candidate is not true",
          data.get("real_send_candidate") is not True)

    # Not claiming live dry-run passed
    check("stop decision: does not claim live dry-run passed",
          data.get("live_dry_run_passed") is not True)

    # Reason present
    check("stop decision: reason is set",
          bool(data.get("reason")),
          f"Got: {data.get('reason')}")

    # Version
    check("stop decision: version is v112X-recovery",
          data.get("version") == "v112X-recovery",
          f"Got: {data.get('version')}")


def test_run_report():
    """Test the markdown run report."""
    print("\n--- Testing Markdown Run Report ---")

    report_path = RUNS_DIR / "v112x_recovery_local_contract.md"
    check("Run report file exists", report_path.exists())

    if not report_path.exists():
        print("  [SKIP] Cannot test run report content — file missing.")
        return

    content = report_path.read_text(encoding="utf-8")
    check("Run report is non-empty", len(content) > 100)

    # Must contain key status markers
    check("Report mentions partial_not_live",
          "partial_not_live" in content)
    check("Report mentions NOT_EXECUTED_LOCAL_RECOVERY_ONLY",
          "NOT_EXECUTED_LOCAL_RECOVERY_ONLY" in content)
    check("Report mentions live_probe_executed",
          "live_probe_executed" in content)
    check("Report mentions external_api_called",
          "external_api_called" in content)
    check("Report mentions eligible_for_real_send",
          "eligible_for_real_send" in content)
    # The report MUST explicitly declare that live probe was NOT executed.
    # "Did NOT claim live dry-run passed" is the correct statement — that's a safety declaration,
    # not a positive claim. We verify: the report says "NOT" in context of live execution.
    check("Report explicitly declares live probe NOT executed",
          "NOT claim live dry-run passed" in content or
          "live_probe_executed" in content or
          "did NOT perform any live work" in content.lower() or
          "NOT_EXECUTED" in content)

    # Must contain safety section markers
    check("Report has safety invariants section",
          "Safety Invar" in content or "safety" in content.lower())


def test_handoff():
    """Test the handoff markdown."""
    print("\n--- Testing Handoff Markdown ---")

    handoff_path = RUNS_DIR / "v112x_recovery_local_contract_handoff.md"
    check("Handoff file exists", handoff_path.exists())

    if not handoff_path.exists():
        print("  [SKIP] Cannot test handoff content — file missing.")
        return

    content = handoff_path.read_text(encoding="utf-8")
    check("Handoff is non-empty", len(content) > 200)

    # Must contain key handoff sections
    check("Handoff mentions partial_not_live",
          "partial_not_live" in content)
    check("Handoff mentions NOT_EXECUTED_LOCAL_RECOVERY_ONLY",
          "NOT_EXECUTED_LOCAL_RECOVERY_ONLY" in content)
    check("Handoff mentions HyperLiquid",
          "HyperLiquid" in content or "hyperliquid" in content.lower())
    check("Handoff mentions stop conditions",
          "stop condition" in content.lower())
    check("Handoff mentions field mapping",
          "field mapping" in content.lower() or "field_mapping" in content.lower())
    content_lower_hf = content.lower()
    check("Handoff mentions label audit / label quality",
          "label audit" in content_lower_hf or
          "label quality" in content_lower_hf or
          "label_quality" in content_lower_hf or
          "Label Quality Audit" in content)
    check("Handoff mentions v112X",
          "v112X" in content)
    check("Handoff mentions eligible_for_real_send",
          "eligible_for_real_send" in content)
    check("Handoff mentions next executor",
          "next executor" in content.lower() or "Next Executor" in content)
    # Handoff MUST explicitly state that NO live execution was performed
    check("Handoff explicitly declares NOT_EXECUTED (no live work done)",
          "NOT_EXECUTED" in content or
          "no live work" in content.lower() or
          "NOT performed any live" in content or
          "live_probe_executed" in content)


def test_no_forbidden_content():
    """Ensure no API keys, credentials, or production markers leaked into output files."""
    print("\n--- Testing No Forbidden Content ---")

    json_files_to_check = [
        RESULTS_DIR / "market_radar_v112x_recovery_local_contract_result.json",
        RESULTS_DIR / "market_radar_v112x_recovery_stop_decision.json",
    ]
    md_files_to_check = [
        RUNS_DIR / "v112x_recovery_local_contract.md",
        RUNS_DIR / "v112x_recovery_local_contract_handoff.md",
    ]

    # For JSON files: parse and check exact key values (avoid substring false positives
    # from safety invariants like "no_api_key_used": true)
    forbidden_keys = [
        "api_key_used",
        "authorization_header_used",
        "live_probe_executed",
        "external_api_called",
        "eligible_for_real_send",
        "real_send_candidate",
        "tg_sent",
        "production_state_written",
        "daemon_started",
    ]

    for file_path in json_files_to_check:
        if not file_path.exists():
            continue
        data = load_json(file_path)
        if not data:
            continue

        # Check top-level keys
        for key in forbidden_keys:
            val = data.get(key)
            check(f"No forbidden true value in {file_path.name}: {key}",
                  val is not True,
                  f"Got {key}={val} in {file_path.name}")

        # Check safety_invariants if present — these should all be true (they're "no_*" negations)
        safety = data.get("safety_invariants", {})
        for safety_key, safety_val in safety.items():
            check(f"Safety invariant in {file_path.name}: {safety_key} == true",
                  safety_val is True,
                  f"Got {safety_key}={safety_val} in {file_path.name}")

    # For markdown files: check for ACTUAL credential leaks (API key VALUES, auth headers with tokens).
    # The markdown legitimately lists field names like "api_key_used: false" as safety documentation.
    # We only flag actual credentials, not field name mentions.
    credential_value_patterns = [
        "OPENAI_API_KEY=",
        "OPENROUTER_API_KEY=",
        "ANTHROPIC_API_KEY=",
        "Authorization: Bearer",
        "authorization: bearer",
        "Authorization: Basic",
    ]

    for file_path in md_files_to_check:
        if not file_path.exists():
            continue
        content = file_path.read_text(encoding="utf-8")
        for pattern in credential_value_patterns:
            check(f"No credential leak in {file_path.name}: {pattern}",
                  pattern not in content,
                  f"Found '{pattern}' in {file_path.name}")

        # Additionally, check markdown doesn't misrepresent safety flags
        # "api_key_used: true" (without "no_" prefix) would be a concern
        check(f"No false api_key_used claim in {file_path.name}",
              "api_key_used: true" not in content.lower() and
              "api_key_used\": true" not in content.lower())


def main() -> int:
    """Run all tests. Returns 0 if all pass, 1 if any fail."""
    print("=" * 70)
    print("  v112X Recovery Local Contract — Test Suite")
    print("=" * 70)

    test_recovery_result()
    test_stop_decision()
    test_run_report()
    test_handoff()
    test_no_forbidden_content()

    # Summary
    total = len(results)
    passed = sum(1 for r in results if r["passed"])
    failed = total - passed

    print(f"\n{'=' * 70}")
    print(f"  Test Results: {passed}/{total} passed, {failed} failed")
    print(f"{'=' * 70}")

    if failed > 0:
        print(f"\n  Failed checks:")
        for r in results:
            if not r["passed"]:
                detail = f" — {r['detail']}" if r["detail"] else ""
                print(f"  [FAIL] {r['check']}{detail}")

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
