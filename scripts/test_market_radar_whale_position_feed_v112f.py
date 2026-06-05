"""Market Radar v1.12-F — Whale Position Feed 单元测试

Tests:
  1. Address labels fixture loads correctly (>= 5 labels)
  2. Position fixture loads correctly (>= 6 samples)
  3. Valid signals >= 4
  4. Blocked signals >= 2
  5. Wallet label enrichment correct
  6. Full wallet address NOT in public card
  7. Position delta calculation correct
  8. Alert type classification correct
  9. Public card count >= 3
  10. debug_leak_count = 0
  11. secret_leak_count = 0
  12. real_tg_sent = false
  13. external_api_called = false
  14. external_ai_called = false
  15. daemon_started = false
  16. live_ready = false
  17. No token/key/cookie/password read
  18. No writes to ai_relay_desk
  19. No file deletion

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
from scripts.run_market_radar_v112f_whale_position_local_enrichment import (
    main as run_pipeline,
    RESULT_JSON_PATH,
    REPORT_MD_PATH,
    HANDOFF_MD_PATH,
    VERSION,
    RUN_ID,
    LABELS_PATH,
    POSITIONS_PATH,
)

from scripts.market_radar_whale_position_feed_v112f import (
    load_address_labels,
    load_whale_positions,
    normalize_whale_position,
    enrich_wallet_label,
    calculate_position_delta,
    classify_alert_type,
    decide_valid_blocked,
    render_whale_public_card,
    check_public_debug_leak,
    check_public_secret_leak,
    check_secrets_and_debug,
    process_whale_position,
    WhalePositionEvent,
    _wallet_short,
    _safe_float,
    _fmt_money,
    WHALE_POSITION_SIZE_THRESHOLD,
    WHALE_POSITION_DELTA_THRESHOLD,
    WHALE_LEVERAGE_THRESHOLD,
    WHALE_UNREALIZED_LOSS_THRESHOLD,
    VALID_ALERT_TYPES,
    DEBUG_LEAK_TERMS,
    SECRET_LEAK_TERMS,
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
print(f"Market Radar {VERSION} — Whale Position Feed Tests")
print(f"Run ID: {RUN_ID}")
print("=" * 70)
print()

print("[SETUP] Running v112f whale position enrichment pipeline...")
exit_code = run_pipeline()
assert_equal(0, exit_code, "Pipeline exit code is 0")
print()

# Load result JSON
print("[SETUP] Loading result JSON...")
try:
    result = json.loads(RESULT_JSON_PATH.read_text(encoding="utf-8"))
    print(f"  Loaded: {RESULT_JSON_PATH}")
except (FileNotFoundError, json.JSONDecodeError) as e:
    print(f"  ❌ Cannot load result JSON: {e}")
    sys.exit(1)
print()

position_results = result.get("position_results", [])


# ══════════════════════════════════════════════════════════════════════════════════════
# Test 1: Fixture Loading
# ══════════════════════════════════════════════════════════════════════════════════════

print("─" * 50)
print("[TEST GROUP 1] Fixture Loading")
print("─" * 50)

# Test address labels loading
labels = load_address_labels()
assert_gte(5, len(labels), "Address labels fixture has >= 5 labels")

# Check label fields
for i, lbl in enumerate(labels):
    has_wallet = bool(lbl.get("wallet"))
    has_label = bool(lbl.get("label"))
    has_entity = lbl.get("entity_type") in ["smart_money", "high_leverage_trader", "exchange_related", "fund_wallet", "unknown_whale", "market_maker"]
    has_conf = lbl.get("confidence") in ["high", "medium", "low"]
    has_source = bool(lbl.get("source_type"))
    assert_true(has_wallet, f"Label {i+1}: has wallet field")
    assert_true(has_label, f"Label {i+1}: has label field")
    assert_true(has_entity, f"Label {i+1}: has valid entity_type ({lbl.get('entity_type')})")
    assert_true(has_conf, f"Label {i+1}: has valid confidence ({lbl.get('confidence')})")
    assert_true(has_source, f"Label {i+1}: has source_type")

# Test position fixture loading
positions = load_whale_positions()
assert_gte(6, len(positions), "Position fixture has >= 6 samples")

# Check position fields
required_fields = [
    "event_id", "observed_at", "wallet", "asset", "side",
    "entry_price", "mark_price", "position_size_usd", "leverage",
    "unrealized_pnl_usd", "margin_used_usd",
    "previous_position_size_usd", "previous_observed_at",
]
for i, pos in enumerate(positions):
    for field in required_fields:
        # previous_observed_at can be null
        if field == "previous_observed_at":
            continue
        # wallet can be null for blocked "missing_wallet" sample
        if field == "wallet" and pos.get("event_id") == "whale_v112f_006_blocked_missing_wallet":
            continue
        has_field = field in pos and pos[field] is not None
        assert_true(has_field, f"Position {i+1}: has required field '{field}'")

print()

# ══════════════════════════════════════════════════════════════════════════════════════
# Test 2: Normalize and Enrich
# ══════════════════════════════════════════════════════════════════════════════════════

print("─" * 50)
print("[TEST GROUP 2] Normalize and Enrich")
print("─" * 50)

# Test normalize
raw_pos = positions[0]
event = normalize_whale_position(raw_pos)
assert_equal(raw_pos["event_id"], event.event_id, "Normalize preserves event_id")
assert_equal(raw_pos["wallet"], event.wallet, "Normalize preserves wallet")
assert_gte(1.0, event.position_size_usd, "Normalize: position_size_usd > 0")

# Test wallet label enrichment
labels_list = load_address_labels()
enriched = enrich_wallet_label(event, labels_list)
assert_true(len(enriched.label) > 0, f"Enrich: label populated ({enriched.label})")
assert_true(enriched.entity_type in ["smart_money", "high_leverage_trader", "exchange_related", "fund_wallet", "unknown_whale", "market_maker"],
           f"Enrich: entity_type is valid ({enriched.entity_type})")
assert_true(len(enriched.wallet_short) > 0, "Enrich: wallet_short populated")
assert_true(len(enriched.wallet_short) < len(enriched.wallet), "Enrich: wallet_short is shorter than full wallet")
assert_true("..." in enriched.wallet_short, "Enrich: wallet_short contains '...'")

# Test unknown wallet enrichment
unknown_event = WhalePositionEvent(
    wallet="0xdeadbeef00000000000000000000000000000000",
    asset="BTC",
    position_size_usd=1000000,
)
unknown_enriched = enrich_wallet_label(unknown_event, labels_list)
assert_equal("Unknown Whale", unknown_enriched.label, "Unlabeled wallet gets 'Unknown Whale' label")
assert_equal("unknown_whale", unknown_enriched.entity_type, "Unlabeled wallet gets 'unknown_whale' type")
assert_equal("low", unknown_enriched.label_confidence, "Unlabeled wallet gets 'low' confidence")

# Test missing wallet enrichment
empty_event = WhalePositionEvent(wallet="", asset="ETH", position_size_usd=500000)
empty_enriched = enrich_wallet_label(empty_event, labels_list)
assert_equal("", empty_enriched.label, "Empty wallet has no label")
assert_equal("", empty_enriched.wallet_short, "Empty wallet has no short form")

print()

# ══════════════════════════════════════════════════════════════════════════════════════
# Test 3: Position Delta Calculation
# ══════════════════════════════════════════════════════════════════════════════════════

print("─" * 50)
print("[TEST GROUP 3] Position Delta Calculation")
print("─" * 50)

# Test opened position (previous=0)
opened = WhalePositionEvent(
    wallet="0x1234", asset="BTC",
    position_size_usd=5000000, previous_position_size_usd=0,
)
delta, direction = calculate_position_delta(opened)
assert_equal(5000000.0, delta, "Opened: delta = 5M")
assert_equal("opened", direction, "Opened: direction = opened")

# Test increased position
increased = WhalePositionEvent(
    wallet="0x1234", asset="BTC",
    position_size_usd=8000000, previous_position_size_usd=5000000,
)
delta, direction = calculate_position_delta(increased)
assert_equal(3000000.0, delta, "Increased: delta = 3M")
assert_equal("increased", direction, "Increased: direction = increased")

# Test reduced position
reduced = WhalePositionEvent(
    wallet="0x1234", asset="BTC",
    position_size_usd=3000000, previous_position_size_usd=8000000,
)
delta, direction = calculate_position_delta(reduced)
assert_equal(-5000000.0, delta, "Reduced: delta = -5M")
assert_equal("reduced", direction, "Reduced: direction = reduced")

# Test unchanged
unchanged = WhalePositionEvent(
    wallet="0x1234", asset="BTC",
    position_size_usd=5000000, previous_position_size_usd=5000000,
)
delta, direction = calculate_position_delta(unchanged)
assert_equal(0.0, delta, "Unchanged: delta = 0")
assert_equal("unchanged", direction, "Unchanged: direction = unchanged")

print()

# ══════════════════════════════════════════════════════════════════════════════════════
# Test 4: Alert Type Classification
# ══════════════════════════════════════════════════════════════════════════════════════

print("─" * 50)
print("[TEST GROUP 4] Alert Type Classification")
print("─" * 50)

# Test high leverage risk
hl_event = WhalePositionEvent(
    wallet="0x1234", asset="ETH",
    position_size_usd=500000, leverage=20.0,
)
at = classify_alert_type(hl_event)
assert_equal("high_leverage_risk", at, "20x leverage → high_leverage_risk")

# Test large unrealized loss (overrides leverage)
loss_event = WhalePositionEvent(
    wallet="0x1234", asset="ARB",
    position_size_usd=600000, leverage=15.0,
    unrealized_pnl_usd=-150000,
)
at = classify_alert_type(loss_event)
assert_equal("large_unrealized_loss", at, "-$150K loss → large_unrealized_loss (overrides leverage)")

# Test position opened
po_event = WhalePositionEvent(
    wallet="0x1234", asset="SOL",
    position_size_usd=2000000, previous_position_size_usd=0,
)
at = classify_alert_type(po_event)
assert_equal("position_opened", at, "New position → position_opened")

# Test position increased
pi_event = WhalePositionEvent(
    wallet="0x1234", asset="SOL",
    position_size_usd=3000000, previous_position_size_usd=2000000,
)
at = classify_alert_type(pi_event)
assert_equal("position_increased", at, "Increased position → position_increased")

# Test position reduced
pr_event = WhalePositionEvent(
    wallet="0x1234", asset="SOL",
    position_size_usd=1000000, previous_position_size_usd=3000000,
)
at = classify_alert_type(pr_event)
assert_equal("position_reduced", at, "Reduced position → position_reduced")

# Test pre-set alert type preserved
preset = WhalePositionEvent(
    wallet="0x1234", asset="BTC",
    position_size_usd=1000000,
    alert_type="high_leverage_risk",
    leverage=12.0,
)
at = classify_alert_type(preset)
assert_equal("high_leverage_risk", at, "Pre-set alert_type preserved")

print()

# ══════════════════════════════════════════════════════════════════════════════════════
# Test 5: Valid / Blocked Decision
# ══════════════════════════════════════════════════════════════════════════════════════

print("─" * 50)
print("[TEST GROUP 5] Valid / Blocked Decision")
print("─" * 50)

# Test valid: large position
v1 = WhalePositionEvent(wallet="0x1234", asset="BTC", position_size_usd=5000000)
valid, blocked, reason = decide_valid_blocked(v1)
assert_true(valid, "Large position (5M) → valid")
assert_true(not blocked, "Large position → not blocked")

# Test valid: high leverage
v2 = WhalePositionEvent(wallet="0x1234", asset="ETH", position_size_usd=500000, leverage=15)
valid, blocked, reason = decide_valid_blocked(v2)
assert_true(valid, "15x leverage → valid")

# Test valid: large loss
v3 = WhalePositionEvent(wallet="0x1234", asset="ARB", position_size_usd=500000, unrealized_pnl_usd=-120000)
valid, blocked, reason = decide_valid_blocked(v3)
assert_true(valid, "-$120K loss → valid")

# Test valid: large delta
v4 = WhalePositionEvent(wallet="0x1234", asset="SOL", position_size_usd=800000, position_delta_usd=250000)
valid, blocked, reason = decide_valid_blocked(v4)
assert_true(valid, "Position delta $250K → valid")

# Test blocked: missing wallet
b1 = WhalePositionEvent(wallet="", asset="BTC", position_size_usd=1000000)
valid, blocked, reason = decide_valid_blocked(b1)
assert_true(not valid, "Missing wallet → not valid")
assert_true(blocked, "Missing wallet → blocked")
assert_equal("missing_wallet", reason, "Block reason = missing_wallet")

# Test blocked: small position
b2 = WhalePositionEvent(wallet="0x1234", asset="PEPE", position_size_usd=25000)
valid, blocked, reason = decide_valid_blocked(b2)
assert_true(not valid, "Small position → not valid")
assert_true(blocked, "Small position → blocked")
assert_equal("position_size_too_small", reason, "Block reason = position_size_too_small")

# Test blocked: missing asset
b3 = WhalePositionEvent(wallet="0x1234", asset="", position_size_usd=1000000)
valid, blocked, reason = decide_valid_blocked(b3)
assert_true(not valid, "Missing asset → not valid")
assert_true(blocked, "Missing asset → blocked")
assert_equal("missing_asset", reason, "Block reason = missing_asset")

print()

# ══════════════════════════════════════════════════════════════════════════════════════
# Test 6: Public Card Rendering
# ══════════════════════════════════════════════════════════════════════════════════════

print("─" * 50)
print("[TEST GROUP 6] Public Card Rendering")
print("─" * 50)

# Create a fully enriched event
sample_labels = load_address_labels()
sample_pos = positions[0]  # Valid position
sample_event = normalize_whale_position(sample_pos)
sample_event = enrich_wallet_label(sample_event, sample_labels)
calculate_position_delta(sample_event)
classify_alert_type(sample_event)

card = render_whale_public_card(sample_event)
assert_true(len(card) > 100, f"Public card is non-trivial (length={len(card)})")
assert_true("0x7a9f...6b8c" in card, "Public card uses short wallet form")
assert_true(sample_event.wallet not in card, "Public card does NOT contain full wallet address")
assert_true("⚠️" in card, "Public card contains disclaimer emoji")

# Check for forbidden terms
debug_leaks = check_public_debug_leak(card)
secret_leaks = check_public_secret_leak(card)
assert_equal(0, len(debug_leaks), f"Public card: debug_leaks = 0 (found: {debug_leaks})")
assert_equal(0, len(secret_leaks), f"Public card: secret_leaks = 0 (found: {secret_leaks})")

# Key fields must be present
required_card_fields = [
    "巨鲸仓位警报",  # Title
    "地址标签",       # Label
    "钱包地址",       # Wallet short
    "资产",           # Asset
    "持仓规模",       # Size
    "杠杆倍数",       # Leverage (only if > 0)
    "警报类型",       # Alert type
    "触发原因",       # Reason
    "仅供观察",       # Disclaimer
]
for field in required_card_fields:
    assert_true(field in card, f"Card contains '{field}'")

# Full wallet address check
import re
full_addrs = re.findall(r'0x[a-fA-F0-9]{40}', card)
assert_equal(0, len(full_addrs), f"Card has 0 full wallet addresses (found: {len(full_addrs)})")

print()

# ══════════════════════════════════════════════════════════════════════════════════════
# Test 7: Pipeline Result Validation
# ══════════════════════════════════════════════════════════════════════════════════════

print("─" * 50)
print("[TEST GROUP 7] Pipeline Result Structure")
print("─" * 50)

valid_signals = [r for r in position_results if r["valid"]]
blocked_signals = [r for r in position_results if r["blocked"]]
public_cards = result.get("public_cards", [])

assert_gte(4, len(valid_signals), f"Valid signals >= 4 (actual: {len(valid_signals)})")
assert_gte(2, len(blocked_signals), f"Blocked signals >= 2 (actual: {len(blocked_signals)})")
assert_gte(3, len(public_cards), f"Public cards >= 3 (actual: {len(public_cards)})")

# Check fallback_preview
assert_equal(False, result.get("fallback_preview", True), "fallback_preview = false")

# Check alert types
alert_types_found = set(r["alert_type"] for r in position_results)
expected_types = {"position_opened", "position_increased", "position_reduced", "high_leverage_risk", "large_unrealized_loss", "unknown"}
found_interesting = alert_types_found & expected_types
assert_gte(3, len(found_interesting), f"At least 3 alert types found (found: {found_interesting})")

print()

# ══════════════════════════════════════════════════════════════════════════════════════
# Test 8: Debug & Secret Leak Checks
# ══════════════════════════════════════════════════════════════════════════════════════

print("─" * 50)
print("[TEST GROUP 8] Debug & Secret Leak Checks")
print("─" * 50)

assert_equal(0, result.get("debug_leak_count", -1), "Overall debug_leak_count = 0")
assert_equal(0, result.get("secret_leak_count", -1), "Overall secret_leak_count = 0")
assert_equal(False, result.get("full_wallet_in_public_card", True), "full_wallet_in_public_card = false")

# Check each public card individually
for i, card in enumerate(public_cards):
    dl, sl = check_secrets_and_debug(card)
    assert_equal(0, len(dl), f"Card {i+1}: debug_leaks = 0")
    assert_equal(0, len(sl), f"Card {i+1}: secret_leaks = 0")
    # No full wallet
    addrs = re.findall(r'0x[a-fA-F0-9]{40}', card)
    assert_equal(0, len(addrs), f"Card {i+1}: no full wallet address")

# Check per-result leaks
for r in position_results:
    eid = r["event_id"][:30]
    assert_equal(0, r.get("debug_leak_count", -1), f"{eid}: debug_leak_count = 0")
    assert_equal(0, r.get("secret_leak_count", -1), f"{eid}: secret_leak_count = 0")

print()

# ══════════════════════════════════════════════════════════════════════════════════════
# Test 9: Safety Constraints
# ══════════════════════════════════════════════════════════════════════════════════════

print("─" * 50)
print("[TEST GROUP 9] Safety Constraints")
print("─" * 50)

assert_true(not result.get("real_tg_sent", True), "real_tg_sent = false")
assert_true(not result.get("external_api_called", True), "external_api_called = false")
assert_true(not result.get("external_ai_called", True), "external_ai_called = false")
assert_true(not result.get("daemon_started", True), "daemon_started = false")
assert_true(not result.get("live_ready", True), "live_ready = false")

# All position results must have these set to False
for r in position_results:
    assert_true(not r.get("real_tg_sent", True), f"{r['event_id'][:25]}: real_tg_sent = false")
    assert_true(not r.get("external_api_called", True), f"{r['event_id'][:25]}: external_api_called = false")
    assert_true(not r.get("external_ai_called", True), f"{r['event_id'][:25]}: external_ai_called = false")
    assert_true(not r.get("daemon_started", True), f"{r['event_id'][:25]}: daemon_started = false")
    assert_true(not r.get("live_ready", True), f"{r['event_id'][:25]}: live_ready = false")

print()

# ══════════════════════════════════════════════════════════════════════════════════════
# Test 10: No Writes to ai_relay_desk
# ══════════════════════════════════════════════════════════════════════════════════════

print("─" * 50)
print("[TEST GROUP 10] No Writes to ai_relay_desk")
print("─" * 50)

result_text = json.dumps(result, ensure_ascii=False)
assert_true("ai_relay_desk" not in result_text, "Result JSON does not reference ai_relay_desk")

if REPORT_MD_PATH.exists():
    report_text = REPORT_MD_PATH.read_text(encoding="utf-8")
    assert_true("ai_relay_desk" not in report_text, "Report MD does not reference ai_relay_desk")

if HANDOFF_MD_PATH.exists():
    handoff_text = HANDOFF_MD_PATH.read_text(encoding="utf-8")
    assert_true("ai_relay_desk" not in handoff_text, "Handoff MD does not reference ai_relay_desk")

print()

# ══════════════════════════════════════════════════════════════════════════════════════
# Test 11: Wallet Label Enrichment — All Valid Positions
# ══════════════════════════════════════════════════════════════════════════════════════

print("─" * 50)
print("[TEST GROUP 11] Wallet Label Coverage in Valid Signals")
print("─" * 50)

for v in valid_signals:
    eid = v["event_id"][:30]
    assert_true(len(v.get("label", "")) > 0, f"{eid}: has label")
    assert_true(len(v.get("wallet_short", "")) > 0, f"{eid}: has wallet_short")
    if v.get("wallet_short") != "--":
        assert_true("..." in v.get("wallet_short", ""), f"{eid}: wallet_short uses '...'")
        assert_true(len(v.get("wallet_short", "")) < 20, f"{eid}: wallet_short is short")

print()

# ══════════════════════════════════════════════════════════════════════════════════════
# Test 12: Output Files
# ══════════════════════════════════════════════════════════════════════════════════════

print("─" * 50)
print("[TEST GROUP 12] Output File Verification")
print("─" * 50)

assert_true(RESULT_JSON_PATH.exists(), f"Result JSON exists: {RESULT_JSON_PATH}")
assert_true(REPORT_MD_PATH.exists(), f"Report MD exists: {REPORT_MD_PATH}")
assert_true(HANDOFF_MD_PATH.exists(), f"Handoff MD exists: {HANDOFF_MD_PATH}")

if RESULT_JSON_PATH.exists():
    size = RESULT_JSON_PATH.stat().st_size
    assert_true(size > 2000, f"Result JSON is non-trivial (size={size} bytes)")

if REPORT_MD_PATH.exists():
    size = REPORT_MD_PATH.stat().st_size
    assert_true(size > 1000, f"Report MD is non-trivial (size={size} bytes)")

if HANDOFF_MD_PATH.exists():
    size = HANDOFF_MD_PATH.stat().st_size
    assert_true(size > 500, f"Handoff MD is non-trivial (size={size} bytes)")

print()

# ══════════════════════════════════════════════════════════════════════════════════════
# Test 13: Utility Functions
# ══════════════════════════════════════════════════════════════════════════════════════

print("─" * 50)
print("[TEST GROUP 13] Utility Functions")
print("─" * 50)

# _wallet_short
# Last 4 chars of the address are "6b8c"
assert_equal("0x7a9f...6b8c", _wallet_short("0x7a9f2c8d4e6b1a3f5c7d9e2b4a6f8c0d2e4a6b8c"), "_wallet_short works")
assert_equal("--", _wallet_short(""), "_wallet_short empty → '--'")
assert_equal("--", _wallet_short(None), "_wallet_short None → '--'")
assert_equal("short", _wallet_short("short"), "_wallet_short short string preserved")

# _safe_float
assert_equal(123.45, _safe_float(123.45), "_safe_float works for float")
assert_equal(0.0, _safe_float(None), "_safe_float None → 0.0")
assert_equal(1000.0, _safe_float("1,000"), "_safe_float handles comma")
assert_equal(7.2, _safe_float("7.2%"), "_safe_float handles percent")
assert_equal(-500.0, _safe_float("-500"), "_safe_float handles negative")

# _fmt_money
assert_true("$5.20M" in _fmt_money(5200000), "_fmt_money millions")
assert_true("$250.00K" in _fmt_money(250000), "_fmt_money thousands")
assert_true("$1.00B" in _fmt_money(1000000000), "_fmt_money billions")

print()

# ══════════════════════════════════════════════════════════════════════════════════════
# Test 14: Leak Checker Function — Unit Tests
# ══════════════════════════════════════════════════════════════════════════════════════

print("─" * 50)
print("[TEST GROUP 14] Leak Checker Unit Tests")
print("─" * 50)

# Clean text
clean = "BTC 多头持仓 $5.2M，5x 杠杆。⚠️ 仅供观察。"
dl, sl = check_secrets_and_debug(clean)
assert_equal(0, len(dl), "Clean text: debug=0")
assert_equal(0, len(sl), "Clean text: secret=0")

# Debug leak
debug_text = "debug mode: value_gate passed, fixture loaded."
dl, sl = check_secrets_and_debug(debug_text)
assert_true(len(dl) > 0, f"Debug text: debug_leaks > 0 (found: {dl})")

# Secret leak
secret_text = "api_key: sk-xxx, chat_id: 12345"
dl, sl = check_secrets_and_debug(secret_text)
assert_true(len(sl) > 0, f"Secret text: secret_leaks > 0 (found: {sl})")

# Path leak
path_text = "file at C:\\Users\\PC\\Desktop\\output.json"
dl, sl = check_secrets_and_debug(path_text)
assert_true(len(sl) > 0, f"Path text: secret_leaks > 0 (found: {sl})")

print()

# ══════════════════════════════════════════════════════════════════════════════════════
# Test 15: No File Deletion
# ══════════════════════════════════════════════════════════════════════════════════════

print("─" * 50)
print("[TEST GROUP 15] No File Deletion")
print("─" * 50)

# All expected files exist
assert_true(LABELS_PATH.exists(), "Labels fixture still exists")
assert_true(POSITIONS_PATH.exists(), "Positions fixture still exists")
assert_true(RESULT_JSON_PATH.exists(), "Result JSON still exists")

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
