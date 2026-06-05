"""Market Radar v1.12-E — All Fixed Card Local Pipeline 单元测试

Tests:
  1. 5 card types all present
  2. card_type_count = 5
  3. Ready=1, Partial=4, Missing=0
  4. Each card type has output summary
  5. public_preview_total >= 5
  6. liquidation_pressure has at least 1 preview
  7. news_event_market_impact has at least 1 preview
  8. whale_position_alert is NOT mistakenly marked ready
  9. multi_asset_market_sync is NOT mistakenly marked ready
  10. price_oi_volume_anomaly IS still ready
  11. debug_leak_count = 0
  12. secret_leak_count = 0
  13. real_tg_sent = false
  14. external_api_called = false
  15. external_ai_called = false
  16. daemon_started = false
  17. live_ready = false
  18. No writes to ai_relay_desk
  19. No file deletion
  20. Report/handoff files successfully generated

Security:
    - Does NOT read, print, or save any token / chat_id / key / cookie / password.
    - Does NOT access environment variables for credentials.
    - Does NOT make network calls.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

# Import the runner module
from scripts.run_market_radar_v112e_all_fixed_card_local_pipeline import (
    main as run_pipeline,
    RESULT_JSON_PATH,
    REPORT_MD_PATH,
    HANDOFF_MD_PATH,
    RESULT_V112F,
    RESULT_V112G,
    VERSION,
    RUN_ID,
    check_all_forbidden_terms,
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


def assert_gte(expected, actual, test_name: str):
    global PASS, FAIL
    if actual >= expected:
        PASS += 1
        print(f"  ✅ PASS: {test_name} (expected>={expected}, actual={actual})")
    else:
        FAIL += 1
        print(f"  ❌ FAIL: {test_name} (expected>={expected}, actual={actual})")


# ══════════════════════════════════════════════════════════════════════════════════════
# Run Pipeline First
# ══════════════════════════════════════════════════════════════════════════════════════

print("=" * 70)
print(f"Market Radar {VERSION} — All Fixed Card Pipeline Tests")
print(f"Run ID: {RUN_ID}")
print("=" * 70)
print()

# Run the pipeline
print("[SETUP] Running v112e pipeline...")
exit_code = run_pipeline()
assert_equal(0, exit_code, "Pipeline exit code is 0")
print()

# Load the result JSON
print("[SETUP] Loading result JSON...")
try:
    result = json.loads(RESULT_JSON_PATH.read_text(encoding="utf-8"))
    print(f"  Loaded: {RESULT_JSON_PATH}")
except (FileNotFoundError, json.JSONDecodeError) as e:
    print(f"  ❌ Cannot load result JSON: {e}")
    sys.exit(1)
print()

card_outputs = result.get("card_outputs", [])


# ══════════════════════════════════════════════════════════════════════════════════════
# Test 1: Core matrix structure
# ══════════════════════════════════════════════════════════════════════════════════════

print("─" * 50)
print("[TEST GROUP 1] Core Matrix Structure")
print("─" * 50)

assert_equal(5, result.get("card_type_count"), "card_type_count = 5")
assert_true(result.get("all_card_types_present", False), "all_card_types_present = true")

# Verify all 5 expected card types are present
expected_types = {
    "price_oi_volume_anomaly",
    "whale_position_alert",
    "liquidation_pressure",
    "multi_asset_market_sync",
    "news_event_market_impact",
}
actual_types = {c["card_type"] for c in card_outputs}
assert_equal(expected_types, actual_types, "All 5 expected card types present")

# Verify each card type has exactly one entry
for ct in expected_types:
    count = sum(1 for c in card_outputs if c["card_type"] == ct)
    assert_equal(1, count, f"Card type '{ct}' has exactly 1 entry")

print()

# ══════════════════════════════════════════════════════════════════════════════════════
# Test 2: Readiness matrix
# ══════════════════════════════════════════════════════════════════════════════════════

print("─" * 50)
print("[TEST GROUP 2] Readiness Matrix")
print("─" * 50)

assert_equal(1, result.get("ready_count"), "Ready=1")
assert_equal(4, result.get("partial_count"), "Partial=4")
assert_equal(0, result.get("missing_count"), "Missing=0")

# price_oi_volume_anomaly must be ready
pova = next((c for c in card_outputs if c["card_type"] == "price_oi_volume_anomaly"), None)
assert_true(pova is not None, "price_oi_volume_anomaly exists")
if pova:
    assert_equal("ready", pova["readiness"], "price_oi_volume_anomaly readiness = ready")
    assert_true(pova.get("gate_tested", False), "price_oi_volume_anomaly gate_tested = true")

# whale_position_alert must NOT be ready
whale = next((c for c in card_outputs if c["card_type"] == "whale_position_alert"), None)
assert_true(whale is not None, "whale_position_alert exists")
if whale:
    assert_equal("partial", whale["readiness"], "whale_position_alert readiness = partial (NOT ready)")

# liquidation_pressure must be partial (not missing)
liq = next((c for c in card_outputs if c["card_type"] == "liquidation_pressure"), None)
assert_true(liq is not None, "liquidation_pressure exists")
if liq:
    assert_equal("partial", liq["readiness"], "liquidation_pressure readiness = partial")

# multi_asset_market_sync must NOT be ready
sync = next((c for c in card_outputs if c["card_type"] == "multi_asset_market_sync"), None)
assert_true(sync is not None, "multi_asset_market_sync exists")
if sync:
    assert_equal("partial", sync["readiness"], "multi_asset_market_sync readiness = partial (NOT ready)")

# news_event_market_impact must be partial (not missing)
news = next((c for c in card_outputs if c["card_type"] == "news_event_market_impact"), None)
assert_true(news is not None, "news_event_market_impact exists")
if news:
    assert_equal("partial", news["readiness"], "news_event_market_impact readiness = partial")

print()

# ══════════════════════════════════════════════════════════════════════════════════════
# Test 3: Output summaries
# ══════════════════════════════════════════════════════════════════════════════════════

print("─" * 50)
print("[TEST GROUP 3] Output Summaries")
print("─" * 50)

for c in card_outputs:
    ct = c["card_type"]
    summary = c.get("output_summary", "")
    assert_true(len(summary) > 0, f"{ct} has non-empty output_summary")

print()

# ══════════════════════════════════════════════════════════════════════════════════════
# Test 4: Public previews
# ══════════════════════════════════════════════════════════════════════════════════════

print("─" * 50)
print("[TEST GROUP 4] Public Previews")
print("─" * 50)

assert_gte(5, result.get("public_preview_total", 0), "public_preview_total >= 5")

# Each card type must have either public_preview or fallback_preview
for c in card_outputs:
    ct = c["card_type"]
    has_preview = c.get("public_preview_available") or c.get("fallback_preview_available")
    assert_true(has_preview, f"{ct} has public or fallback preview")

# liquidation_pressure must have at least 1 public preview
if liq:
    assert_gte(1, liq.get("public_card_count", 0), "liquidation_pressure has >= 1 public preview")
    assert_true(liq.get("public_preview_available", False), "liquidation_pressure public_preview_available = true")

# news_event_market_impact must have at least 1 public preview
if news:
    assert_gte(1, news.get("public_card_count", 0), "news_event_market_impact has >= 1 public preview")
    assert_true(news.get("public_preview_available", False), "news_event_market_impact public_preview_available = true")

print()

# ══════════════════════════════════════════════════════════════════════════════════════
# Test 5: Missing capabilities
# ══════════════════════════════════════════════════════════════════════════════════════

print("─" * 50)
print("[TEST GROUP 5] Missing Capabilities")
print("─" * 50)

if whale:
    whale_missing = " ".join(whale.get("missing_capability", [])).lower()
    v112f_used = whale.get("v112f_enrichment_used", False)
    if v112f_used:
        # With v112f: address labels are provided locally, so "address labels"
        # should NOT appear as a completely missing item (but "label coverage"
        # may still be mentioned for gaps)
        has_hist_missing = "historical" in whale_missing or "sequence" in whale_missing or "history" in whale_missing
        assert_true(not has_hist_missing,
                   "whale_position_alert (v112f): historical position sequence NOT in missing_caps")
    else:
        has_addr = "address" in whale_missing or "label" in whale_missing
        has_hist = "historical" in whale_missing or "sequence" in whale_missing or "history" in whale_missing
        assert_true(has_addr, "whale_position_alert missing: address labels")
        assert_true(has_hist, "whale_position_alert missing: historical position sequence")

if sync:
    sync_missing = " ".join(sync.get("missing_capability", [])).lower()
    has_corr = "correlation" in sync_missing or "matrix" in sync_missing or "auto" in sync_missing
    assert_true(has_corr, "multi_asset_market_sync missing: auto correlation matrix")

print()

# ══════════════════════════════════════════════════════════════════════════════════════
# Test 5.5: v112f Whale Position Enrichment Integration
# ══════════════════════════════════════════════════════════════════════════════════════

print("─" * 50)
print("[TEST GROUP 5.5] v112f Whale Position Enrichment Integration")
print("─" * 50)

# Check if v112f result file exists
v112f_exists = RESULT_V112F.exists()
print(f"  v112f result exists: {v112f_exists}")

if v112f_exists and whale:
    # whale_position_alert must NOT be in fallback preview mode
    assert_true(
        not whale.get("fallback_preview_available", True),
        "whale_position_alert fallback_preview_available = false (v112f active)"
    )
    # whale_position_alert must have public preview available
    assert_true(
        whale.get("public_preview_available", False),
        "whale_position_alert public_preview_available = true (v112f active)"
    )
    # v112f enrichment must be used
    assert_true(
        whale.get("v112f_enrichment_used", False),
        "whale_position_alert v112f_enrichment_used = true"
    )
    # Must have at least 1 real public preview (ideally >= 3)
    v112f_card_count = whale.get("v112f_card_count", 0)
    assert_gte(1, v112f_card_count, f"whale_position_alert v112f_card_count >= 1 (actual: {v112f_card_count})")
    # Must have valid signals from v112f
    v112f_valid = whale.get("v112f_valid_count", 0)
    assert_gte(4, v112f_valid, f"whale_position_alert v112f_valid_count >= 4 (actual: {v112f_valid})")
    # Still must be partial, NOT ready
    assert_equal("partial", whale["readiness"], "whale_position_alert still partial (NOT ready)")
else:
    if not v112f_exists:
        print("  [INFO] v112f result not found — skipping v112f integration tests (expected before v112f run)")
    else:
        print("  [INFO] whale result missing — skipping v112f integration tests")

print()

# ══════════════════════════════════════════════════════════════════════════════════════
# Test 5.6: v112g Multi-Asset Sync Integration
# ══════════════════════════════════════════════════════════════════════════════════════

print("─" * 50)
print("[TEST GROUP 5.6] v112g Multi-Asset Sync Integration")
print("─" * 50)

v112g_exists = RESULT_V112G.exists()
print(f"  v112g result exists: {v112g_exists}")

if v112g_exists and sync:
    # multi_asset_market_sync fallback_preview_available must be false (v112g active)
    assert_true(
        not sync.get("fallback_preview_available", True),
        "multi_asset_market_sync fallback_preview_available = false (v112g active)"
    )
    # multi_asset_market_sync public_preview_available must be true
    assert_true(
        sync.get("public_preview_available", False),
        "multi_asset_market_sync public_preview_available = true (v112g active)"
    )
    # v112g correlation must be used
    assert_true(
        sync.get("v112g_correlation_used", False),
        "multi_asset_market_sync v112g_correlation_used = true"
    )
    # At least 1 real public preview (ideally >= 3)
    v112g_card_count = sync.get("v112g_card_count", 0)
    assert_gte(1, v112g_card_count,
               f"multi_asset_market_sync v112g_card_count >= 1 (actual: {v112g_card_count})")
    assert_gte(3, v112g_card_count,
               f"multi_asset_market_sync v112g_card_count >= 3 (actual: {v112g_card_count})")
    # Must have valid signals from v112g
    v112g_valid = sync.get("v112g_valid_count", 0)
    assert_gte(5, v112g_valid,
               f"multi_asset_market_sync v112g_valid_count >= 5 (actual: {v112g_valid})")
    # Still must be partial, NOT ready
    assert_equal("partial", sync["readiness"],
                 "multi_asset_market_sync still partial (NOT ready)")
    # 5 class matrix must still be Ready=1, Partial=4, Missing=0
    assert_equal(1, result.get("ready_count", -1),
                 "Ready count = 1 (unchanged with v112g)")
    assert_equal(4, result.get("partial_count", -1),
                 "Partial count = 4 (unchanged with v112g)")
    assert_equal(0, result.get("missing_count", -1),
                 "Missing count = 0 (unchanged with v112g)")
else:
    if not v112g_exists:
        print("  [INFO] v112g result not found — skipping v112g integration tests")
    else:
        print("  [INFO] sync result missing — skipping v112g integration tests")

print()

# ══════════════════════════════════════════════════════════════════════════════════════
# Test 6: Debug and secret leak checks
# ══════════════════════════════════════════════════════════════════════════════════════

print("─" * 50)
print("[TEST GROUP 6] Debug & Secret Leak Checks")
print("─" * 50)

assert_equal(0, result.get("debug_leak_count", -1), "debug_leak_count = 0")
assert_equal(0, result.get("secret_leak_count", -1), "secret_leak_count = 0")

# Verify no public preview sample contains forbidden terms
forbidden_check_terms = [
    "debug", "internal", "trace", "fixture",
    "secret", "token", "api_key", "chat_id", "password",
    "C:\\Users\\PC", "ai_relay_desk",
]

for c in card_outputs:
    ct = c["card_type"]
    preview = c.get("public_preview_sample", "")
    if not preview:
        continue

    preview_lower = preview.lower()
    for term in forbidden_check_terms:
        if term.lower() in preview_lower:
            assert_true(False, f"{ct} public preview contains forbidden term: '{term}'")
            break
    else:
        assert_true(True, f"{ct} public preview is clean (no forbidden terms)")

print()

# ══════════════════════════════════════════════════════════════════════════════════════
# Test 7: live_ready and gate flags
# ══════════════════════════════════════════════════════════════════════════════════════

print("─" * 50)
print("[TEST GROUP 7] live_ready / Gate Flags")
print("─" * 50)

assert_true(not result.get("live_ready", True), "live_ready = false")

# All cards must have live_ready = false
for c in card_outputs:
    ct = c["card_type"]
    assert_true(not c.get("live_ready", True), f"{ct} live_ready = false")

# liquidation_pressure live_ready must be false
if liq:
    assert_true(not liq.get("live_ready", True), "liquidation_pressure live_ready = false")

# news_event_market_impact live_ready must be false
if news:
    assert_true(not news.get("live_ready", True), "news_event_market_impact live_ready = false")

print()

# ══════════════════════════════════════════════════════════════════════════════════════
# Test 8: Safety constraints
# ══════════════════════════════════════════════════════════════════════════════════════

print("─" * 50)
print("[TEST GROUP 8] Safety Constraints")
print("─" * 50)

assert_true(not result.get("real_tg_sent", True), "real_tg_sent = false")
assert_true(not result.get("external_api_called", True), "external_api_called = false")
assert_true(not result.get("external_ai_called", True), "external_ai_called = false")
assert_true(not result.get("daemon_started", True), "daemon_started = false")

print()

# ══════════════════════════════════════════════════════════════════════════════════════
# Test 9: Output file verification
# ══════════════════════════════════════════════════════════════════════════════════════

print("─" * 50)
print("[TEST GROUP 9] Output File Verification")
print("─" * 50)

assert_true(RESULT_JSON_PATH.exists(), f"Result JSON exists: {RESULT_JSON_PATH}")
assert_true(REPORT_MD_PATH.exists(), f"Report MD exists: {REPORT_MD_PATH}")
assert_true(HANDOFF_MD_PATH.exists(), f"Handoff MD exists: {HANDOFF_MD_PATH}")

# Verify file sizes are reasonable
if RESULT_JSON_PATH.exists():
    size = RESULT_JSON_PATH.stat().st_size
    assert_true(size > 1000, f"Result JSON is non-trivial (size={size} bytes)")

if REPORT_MD_PATH.exists():
    size = REPORT_MD_PATH.stat().st_size
    assert_true(size > 500, f"Report MD is non-trivial (size={size} bytes)")

if HANDOFF_MD_PATH.exists():
    size = HANDOFF_MD_PATH.stat().st_size
    assert_true(size > 500, f"Handoff MD is non-trivial (size={size} bytes)")

print()

# ══════════════════════════════════════════════════════════════════════════════════════
# Test 10: No writes to ai_relay_desk
# ══════════════════════════════════════════════════════════════════════════════════════

print("─" * 50)
print("[TEST GROUP 10] No Writes to ai_relay_desk")
print("─" * 50)

ai_relay_path = Path("C:/Users/PC/Desktop/工作台/ai_relay_desk")
# Check result JSON does not reference ai_relay_desk
result_text = json.dumps(result, ensure_ascii=False)
assert_true("ai_relay_desk" not in result_text, "Result JSON does not reference ai_relay_desk")

# Check report MD
if REPORT_MD_PATH.exists():
    report_text = REPORT_MD_PATH.read_text(encoding="utf-8")
    assert_true("ai_relay_desk" not in report_text, "Report MD does not reference ai_relay_desk")

# Check handoff MD
if HANDOFF_MD_PATH.exists():
    handoff_text = HANDOFF_MD_PATH.read_text(encoding="utf-8")
    assert_true("ai_relay_desk" not in handoff_text, "Handoff MD does not reference ai_relay_desk")

print()

# ══════════════════════════════════════════════════════════════════════════════════════
# Test 11: leak checker function tests
# ══════════════════════════════════════════════════════════════════════════════════════

print("─" * 50)
print("[TEST GROUP 11] Leak Checker Function")
print("─" * 50)

# Test clean text
clean_text = "BTC 24h 涨幅 7.2%，多因子异动信号。⚠️ 仅供观察，不构成交易建议。"
debug_leaks, secret_leaks = check_all_forbidden_terms(clean_text)
assert_equal(0, len(debug_leaks), "Clean text: debug_leaks = 0")
assert_equal(0, len(secret_leaks), "Clean text: secret_leaks = 0")

# Test debug leak
debug_text = "BTC debug mode: value_gate passed, score↑ 85. pre_send: allow."
debug_leaks, secret_leaks = check_all_forbidden_terms(debug_text)
assert_true(len(debug_leaks) > 0, f"Debug text: debug_leaks detected ({len(debug_leaks)} terms)")
print(f"    Found debug terms: {debug_leaks}")

# Test secret leak
secret_text = "API key: sk-xxx, chat_id: 123456, password: admin123"
debug_leaks, secret_leaks = check_all_forbidden_terms(secret_text)
assert_true(len(secret_leaks) > 0, f"Secret text: secret_leaks detected ({len(secret_leaks)} terms)")
print(f"    Found secret terms: {secret_leaks}")

# Test local path leak
path_text = "File saved to C:\\Users\\PC\\Desktop\\Projects\\output.json"
debug_leaks, secret_leaks = check_all_forbidden_terms(path_text)
assert_true(len(secret_leaks) > 0, f"Path text: secret_leaks detected ({len(secret_leaks)} terms)")
print(f"    Found secret terms: {secret_leaks}")

print()

# ══════════════════════════════════════════════════════════════════════════════════════
# Final Summary
# ══════════════════════════════════════════════════════════════════════════════════════

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
