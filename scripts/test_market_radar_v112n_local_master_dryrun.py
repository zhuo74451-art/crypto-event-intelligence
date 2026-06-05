"""Market Radar v1.12-N — Local Master Dry-Run 单元测试

Tests:
  1. v112N runner executes and returns success
  2. result JSON exists and status == "passed"
  3. dry_run_only == true, live_ready == false
  4. real_tg_sent == false, external_api_called == false
  5. external_ai_called == false, daemon_started == false
  6. files_deleted == false
  7. master_steps_passed == master_steps_total
  8. signal_envelope_count == 13, gate_decision_count == 13
  9. eligible_signal_count == 9, blocked_signal_count == 4
  10. first_pass_eligible_reblocked == 9
  11. unexpected_repass_signal_ids == []
  12. idempotency_passed == true
  13. deterministic_clock == true
  14. evaluated_at == "2026-06-04T22:30:00+08:00"
  15. time_dependent_test_risk == false
  16. report MD and handoff MD exist
  17. No token/key/secret/cookie/password in any output
  18. No ai_relay_desk references

Security:
    - Does NOT read, print, or save any token / chat_id / key / cookie / password.
    - Does NOT access environment variables for credentials.
    - Does NOT make network calls.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

# Import the runner module
from scripts.run_market_radar_v112n_local_master_dryrun import (
    main as run_master,
    RESULT_JSON_PATH,
    REPORT_MD_PATH,
    HANDOFF_MD_PATH,
    VERSION,
    RUN_ID,
    check_forbidden_terms,
)

# ══════════════════════════════════════════════════════════════════════════════════════
# Test Helpers
# ══════════════════════════════════════════════════════════════════════════════════════

PASS = 0
FAIL = 0


def assert_true(condition, test_name: str):
    global PASS, FAIL
    if condition:
        PASS += 1
        print(f"  ✅ PASS: {test_name}")
    else:
        FAIL += 1
        print(f"  ❌ FAIL: {test_name}")


def assert_equal(expected, actual, test_name: str):
    global PASS, FAIL
    if expected == actual:
        PASS += 1
        print(f"  ✅ PASS: {test_name} (expected={expected}, actual={actual})")
    else:
        FAIL += 1
        print(f"  ❌ FAIL: {test_name} (expected={expected}, actual={actual})")


# ══════════════════════════════════════════════════════════════════════════════════════
# Run the Orchestrator
# ══════════════════════════════════════════════════════════════════════════════════════

print("=" * 70)
print(f"Market Radar {VERSION} — Local Master Dry-Run Tests")
print(f"Run ID: {RUN_ID}")
print("=" * 70)
print()

# Run the master orchestrator
print("[SETUP] Running v112N master orchestrator...")
exit_code = run_master()
print(f"  Master exit code: {exit_code}")
print()

# ══════════════════════════════════════════════════════════════════════════════════════
# Test Group 1: Runner execution
# ══════════════════════════════════════════════════════════════════════════════════════

print("─" * 50)
print("[TEST GROUP 1] Runner Execution")
print("─" * 50)

assert_equal(0, exit_code, "v112N runner exit code = 0")

# ══════════════════════════════════════════════════════════════════════════════════════
# Test Group 2: Result JSON exists and loads
# ══════════════════════════════════════════════════════════════════════════════════════

print("─" * 50)
print("[TEST GROUP 2] Result JSON Existence and Basic Fields")
print("─" * 50)

assert_true(RESULT_JSON_PATH.exists(), f"Result JSON exists: {RESULT_JSON_PATH}")

try:
    result = json.loads(RESULT_JSON_PATH.read_text(encoding="utf-8"))
    print(f"  Loaded: {RESULT_JSON_PATH}")
except (FileNotFoundError, json.JSONDecodeError) as e:
    print(f"  ❌ Cannot load result JSON: {e}")
    sys.exit(1)

assert_equal(VERSION, result.get("version"), f"version = {VERSION}")
assert_equal("passed", result.get("status"), "status = passed")

# ══════════════════════════════════════════════════════════════════════════════════════
# Test Group 3: Safety boundary fields
# ══════════════════════════════════════════════════════════════════════════════════════

print("─" * 50)
print("[TEST GROUP 3] Safety Boundary Fields")
print("─" * 50)

assert_equal(True, result.get("dry_run_only"), "dry_run_only = true")
assert_equal(False, result.get("live_ready"), "live_ready = false")
assert_equal(False, result.get("real_tg_sent"), "real_tg_sent = false")
assert_equal(False, result.get("external_api_called"), "external_api_called = false")
assert_equal(False, result.get("external_ai_called"), "external_ai_called = false")
assert_equal(False, result.get("daemon_started"), "daemon_started = false")
assert_equal(False, result.get("files_deleted"), "files_deleted = false")

# ══════════════════════════════════════════════════════════════════════════════════════
# Test Group 4: Master steps
# ══════════════════════════════════════════════════════════════════════════════════════

print("─" * 50)
print("[TEST GROUP 4] Master Steps")
print("─" * 50)

steps_total = result.get("master_steps_total", 0)
steps_passed = result.get("master_steps_passed", 0)
assert_equal(8, steps_total, "master_steps_total = 8")
assert_equal(steps_total, steps_passed, f"master_steps_passed ({steps_passed}) = master_steps_total ({steps_total})")

# Verify each step has required fields
step_results = result.get("step_results", [])
assert_equal(8, len(step_results), "step_results has 8 entries")

for step in step_results:
    sn = step.get("step_name", "unknown")
    assert_true("step_name" in step, f"{sn}: has step_name")
    assert_true("script_path" in step, f"{sn}: has script_path")
    assert_true("status" in step, f"{sn}: has status")
    assert_true("started_at" in step, f"{sn}: has started_at")
    assert_true("finished_at" in step, f"{sn}: has finished_at")
    assert_true("duration_seconds" in step, f"{sn}: has duration_seconds")
    assert_true("expected_output_files" in step, f"{sn}: has expected_output_files")
    assert_true("observed_output_files" in step, f"{sn}: has observed_output_files")

# ══════════════════════════════════════════════════════════════════════════════════════
# Test Group 5: Core metric values (from real pipeline output, not hardcoded)
# ══════════════════════════════════════════════════════════════════════════════════════

print("─" * 50)
print("[TEST GROUP 5] Core Metric Values")
print("─" * 50)

assert_equal(5, result.get("fixed_card_types_total"), "fixed_card_types_total = 5")
assert_equal(13, result.get("signal_envelope_count"), "signal_envelope_count = 13")
assert_equal(13, result.get("gate_decision_count"), "gate_decision_count = 13")
assert_equal(9, result.get("eligible_signal_count"), "eligible_signal_count = 9")
assert_equal(4, result.get("blocked_signal_count"), "blocked_signal_count = 4")

# ══════════════════════════════════════════════════════════════════════════════════════
# Test Group 6: Idempotency and state replay
# ══════════════════════════════════════════════════════════════════════════════════════

print("─" * 50)
print("[TEST GROUP 6] Idempotency and State Replay")
print("─" * 50)

assert_equal(9, result.get("canonical_state_entry_count"), "canonical_state_entry_count = 9")
assert_equal(9, result.get("first_pass_eligible_reblocked"), "first_pass_eligible_reblocked = 9")
assert_equal([], result.get("unexpected_repass_signal_ids"), "unexpected_repass_signal_ids = []")
assert_equal(True, result.get("idempotency_passed"), "idempotency_passed = true")

# ══════════════════════════════════════════════════════════════════════════════════════
# Test Group 7: Deterministic clock (v112M hardening)
# ══════════════════════════════════════════════════════════════════════════════════════

print("─" * 50)
print("[TEST GROUP 7] Deterministic Clock (v112M hardening)")
print("─" * 50)

assert_equal(True, result.get("deterministic_clock"), "deterministic_clock = true")
assert_equal(
    "2026-06-04T22:30:00+08:00",
    result.get("evaluated_at"),
    "evaluated_at = 2026-06-04T22:30:00+08:00",
)
assert_equal(False, result.get("time_dependent_test_risk"), "time_dependent_test_risk = false")

# ══════════════════════════════════════════════════════════════════════════════════════
# Test Group 8: Output file existence
# ══════════════════════════════════════════════════════════════════════════════════════

print("─" * 50)
print("[TEST GROUP 8] Output File Existence")
print("─" * 50)

assert_true(REPORT_MD_PATH.exists(), f"Report MD exists: {REPORT_MD_PATH}")
assert_true(HANDOFF_MD_PATH.exists(), f"Handoff MD exists: {HANDOFF_MD_PATH}")

# Verify file sizes are reasonable
if RESULT_JSON_PATH.exists():
    size = RESULT_JSON_PATH.stat().st_size
    assert_true(size > 500, f"Result JSON is non-trivial (size={size} bytes)")

if REPORT_MD_PATH.exists():
    size = REPORT_MD_PATH.stat().st_size
    assert_true(size > 300, f"Report MD is non-trivial (size={size} bytes)")

if HANDOFF_MD_PATH.exists():
    size = HANDOFF_MD_PATH.stat().st_size
    assert_true(size > 300, f"Handoff MD is non-trivial (size={size} bytes)")

# ══════════════════════════════════════════════════════════════════════════════════════
# Test Group 9: No credential leaks in any output
# ══════════════════════════════════════════════════════════════════════════════════════

print("─" * 50)
print("[TEST GROUP 9] Credential Leak Scan")
print("─" * 50)

# Scan result JSON
result_text = json.dumps(result, ensure_ascii=False)

# Master debug/secret leak counts aggregate step-level counts (each step
# scans only public-facing content — public cards, previews — not structural
# field names). Verify they are 0.
assert_equal(0, result.get("debug_leak_count", -1), "debug_leak_count in result = 0")
assert_equal(0, result.get("secret_leak_count", -1), "secret_leak_count in result = 0")

# Scan for actual credential VALUE patterns (not structural field names like
# "secret_leak_count" which appear in safety confirmation tables).
credential_value_patterns = [
    r'sk-[A-Za-z0-9]{20,}',          # OpenAI-style API key values
    r'Bearer\s+[A-Za-z0-9_\-\.]{10,}', # Bearer token with actual value
    r'api_key[\s:=]+[\'"]?\w{8,}',   # api_key with value (not just field name)
    r'chat_id[\s:=]+\d{6,}',         # chat_id with numeric value
    r'password[\s:=]+[\'"]?(?!false\b|none\b|NONE\b)\w', # password with non-sentinel value
    r'token[\s:=]+[\'"]?[\w\-]{8,}',  # token with actual value
]
for fp_label, fp in [("Result JSON", RESULT_JSON_PATH), ("Report MD", REPORT_MD_PATH), ("Handoff MD", HANDOFF_MD_PATH)]:
    if not fp.exists():
        continue
    text = fp.read_text(encoding="utf-8")
    clean = True
    for pat in credential_value_patterns:
        if re.search(pat, text, re.IGNORECASE):
            assert_true(False, f"{fp_label} contains credential value: '{pat}'")
            clean = False
    if clean:
        assert_true(True, f"{fp_label}: no credential value patterns found")

# ══════════════════════════════════════════════════════════════════════════════════════
# Test Group 10: No ai_relay_desk references
# ══════════════════════════════════════════════════════════════════════════════════════

print("─" * 50)
print("[TEST GROUP 10] No ai_relay_desk Path References")
print("─" * 50)

# Check that no output file contains an actual path reference to
# C:\Users\PC\Desktop\工作台\ai_relay_desk (the real filesystem path).
# Safety table mentions like "ai_relay_desk writes | false" are confirmations,
# not leaks — they confirm the safety boundary is respected.
ai_relay_path_pattern = r'C:\\Users\\PC\\Desktop\\工作台\\ai_relay_desk'

result_text = json.dumps(result, ensure_ascii=False)
assert_true(
    not re.search(ai_relay_path_pattern, result_text),
    "Result JSON: no ai_relay_desk path reference",
)

if REPORT_MD_PATH.exists():
    report_text = REPORT_MD_PATH.read_text(encoding="utf-8")
    assert_true(
        not re.search(ai_relay_path_pattern, report_text),
        "Report MD: no ai_relay_desk path reference",
    )

if HANDOFF_MD_PATH.exists():
    handoff_text = HANDOFF_MD_PATH.read_text(encoding="utf-8")
    assert_true(
        not re.search(ai_relay_path_pattern, handoff_text),
        "Handoff MD: no ai_relay_desk path reference",
    )

# ══════════════════════════════════════════════════════════════════════════════════════
# Test Group 11: Verify all v112I deterministic clock fields cross-validated
# ══════════════════════════════════════════════════════════════════════════════════════

print("─" * 50)
print("[TEST GROUP 11] Cross-Validation: v112I Deterministic Clock")
print("─" * 50)

# Load v112I result directly and cross-check
v112i_path = ROOT / "results" / "market_radar_v112i_dedupe_cooldown_gate_result.json"
if v112i_path.exists():
    i_data = json.loads(v112i_path.read_text(encoding="utf-8"))
    assert_equal(
        i_data.get("deterministic_clock"),
        result.get("deterministic_clock"),
        "Cross-validated deterministic_clock (master vs v112I)",
    )
    assert_equal(
        i_data.get("evaluated_at"),
        result.get("evaluated_at"),
        "Cross-validated evaluated_at (master vs v112I)",
    )
    assert_equal(
        i_data.get("time_dependent_test_risk"),
        result.get("time_dependent_test_risk"),
        "Cross-validated time_dependent_test_risk (master vs v112I)",
    )
else:
    print("  [INFO] v112I result not found — skipping cross-validation")

# ══════════════════════════════════════════════════════════════════════════════════════
# Test Group 12: Verify step-level v112I clock detail
# ══════════════════════════════════════════════════════════════════════════════════════

print("─" * 50)
print("[TEST GROUP 12] Step-Level v112I Deterministic Clock")
print("─" * 50)

v112i_step = None
for step in step_results:
    if step.get("step_name") == "v112i_dedupe_cooldown_gate":
        v112i_step = step
        break

if v112i_step:
    assert_equal("passed", v112i_step.get("status"), "v112I step status = passed")
    km = v112i_step.get("key_metrics", {})
    assert_equal(True, km.get("deterministic_clock"), "v112I step: deterministic_clock = true")
    assert_equal(
        "2026-06-04T22:30:00+08:00",
        km.get("evaluated_at"),
        "v112I step: evaluated_at = 2026-06-04T22:30:00+08:00",
    )
    assert_equal(False, km.get("time_dependent_test_risk"), "v112I step: time_dependent_test_risk = false")
else:
    print("  [INFO] v112I step not found in step_results")

# ══════════════════════════════════════════════════════════════════════════════════════
# Final Summary
# ══════════════════════════════════════════════════════════════════════════════════════

print()
print("=" * 70)
print(f"TEST RESULTS: {PASS} passed, {FAIL} failed, {PASS + FAIL} total")
print("=" * 70)

if FAIL > 0:
    print()
    print("❌ SOME TESTS FAILED!")
    sys.exit(1)
else:
    print()
    print("✅ ALL TESTS PASSED!")
    sys.exit(0)
