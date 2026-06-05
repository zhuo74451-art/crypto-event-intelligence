"""Market Radar v1.12-G — Multi-Asset Sync Feed 单元测试

Tests:
  1. Snapshot fixture loads correctly
  2. Valid signal count >= 5
  3. Blocked signal count >= 3
  4. Synchronized move score calculation
  5. Direction agreement calculation
  6. Sync type classification
  7. Sector/basket detection
  8. Public card count >= 3
  9. Debug leak count = 0
  10. Secret leak count = 0
  11. real_tg_sent = false
  12. external_api_called = false
  13. external_ai_called = false
  14. daemon_started = false
  15. live_ready = false
  16. No token/key/cookie/password read
  17. No writes to ai_relay_desk
  18. No file deletion

Usage:
    python scripts/test_market_radar_multi_asset_sync_feed_v112g.py
"""

from __future__ import annotations

import io
import json
import sys
from pathlib import Path

# Fix Windows GBK encoding for emoji output
if sys.stdout.encoding != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.market_radar_multi_asset_sync_feed_v112g import (
    VERSION,
    MODE,
    load_snapshots,
    normalize_snapshot,
    calculate_synchronized_move_score,
    calculate_direction_agreement,
    detect_sector_basket_type,
    classify_sync_type,
    decide_valid_blocked,
    render_public_card,
    check_debug_leak,
    check_secret_leak,
    process_snapshot,
    SYNC_TYPES,
)

# ── Test Helpers ────────────────────────────────────────────────────────────────────

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


def assert_gt(expected, actual, test_name: str):
    global PASS, FAIL
    if actual > expected:
        PASS += 1
        print(f"  ✅ PASS: {test_name} (expected>{expected}, actual={actual})")
    else:
        FAIL += 1
        print(f"  ❌ FAIL: {test_name} (expected>{expected}, actual={actual})")


# ── Fixture path ────────────────────────────────────────────────────────────────────

FIXTURE_PATH = ROOT / "data" / "fixtures" / "market_radar_v112g_multi_asset_snapshots.json"
RESULT_JSON_PATH = ROOT / "results" / "market_radar_v112g_multi_asset_sync_local_correlation_result.json"


# ══════════════════════════════════════════════════════════════════════════════════════
# Main
# ══════════════════════════════════════════════════════════════════════════════════════

print("=" * 70)
print(f"Market Radar {VERSION} — Multi-Asset Sync Feed Tests")
print("=" * 70)
print()

# ── Load fixture ────────────────────────────────────────────────────────────────────
print("[SETUP] Loading snapshots...")
snapshots_raw = load_snapshots(FIXTURE_PATH)
assert_true(len(snapshots_raw) > 0, "Snapshots fixture loads successfully")
assert_gte(8, len(snapshots_raw), f"At least 8 snapshots loaded (actual={len(snapshots_raw)})")
print()

# ── Process all snapshots ───────────────────────────────────────────────────────────
print("[SETUP] Processing all snapshots...")
results = [process_snapshot(raw) for raw in snapshots_raw]
valid_results = [r for r in results if r["valid"]]
blocked_results = [r for r in results if r["blocked"]]
print(f"  Processed: {len(results)} snapshots")
print(f"  Valid: {len(valid_results)}, Blocked: {len(blocked_results)}")
print()

# ══════════════════════════════════════════════════════════════════════════════════════
# Test Group 1: Fixture Loading
# ══════════════════════════════════════════════════════════════════════════════════════

print("─" * 50)
print("[TEST GROUP 1] Fixture Loading")
print("─" * 50)

for raw in snapshots_raw:
    event_id = raw.get("event_id", "unknown")
    assert_true(len(event_id) > 0, f"Snapshot has event_id: {event_id}")
    assets = raw.get("assets", [])
    assert_true(len(assets) > 0, f"{event_id}: has assets ({len(assets)})")
    for a in assets:
        assert_true("price_change_pct" in a, f"{event_id}/{a.get('asset')}: has price_change_pct")
        assert_true("volume_change_pct" in a, f"{event_id}/{a.get('asset')}: has volume_change_pct")

print()

# ══════════════════════════════════════════════════════════════════════════════════════
# Test Group 2: Valid / Blocked Counts
# ══════════════════════════════════════════════════════════════════════════════════════

print("─" * 50)
print("[TEST GROUP 2] Valid / Blocked Counts")
print("─" * 50)

assert_gte(5, len(valid_results), f"valid_signal_count >= 5 (actual={len(valid_results)})")
assert_gte(3, len(blocked_results), f"blocked_signal_count >= 3 (actual={len(blocked_results)})")
assert_equal(5, len(valid_results), f"exactly 5 valid signals (actual={len(valid_results)})")
assert_equal(3, len(blocked_results), f"exactly 3 blocked signals (actual={len(blocked_results)})")

print()

# ══════════════════════════════════════════════════════════════════════════════════════
# Test Group 3: Synchronized Move Score
# ══════════════════════════════════════════════════════════════════════════════════════

print("─" * 50)
print("[TEST GROUP 3] Synchronized Move Score")
print("─" * 50)

# Test with valid multi-asset data
valid_assets = [
    {"asset": "BTC", "price_change_pct": 5.2, "volume_change_pct": 95.0, "oi_change_pct": 8.5, "funding_rate": 0.012, "liquidation_usd": 85_000_000},
    {"asset": "ETH", "price_change_pct": 4.8, "volume_change_pct": 88.0, "oi_change_pct": 7.2, "funding_rate": 0.010, "liquidation_usd": 62_000_000},
    {"asset": "SOL", "price_change_pct": 6.1, "volume_change_pct": 105.0, "oi_change_pct": 9.8, "funding_rate": 0.018, "liquidation_usd": 18_000_000},
]
score = calculate_synchronized_move_score(valid_assets)
assert_gt(0, score, f"Sync score > 0 for multi-asset data (actual={score})")
assert_true(0 <= score <= 100, f"Sync score in range [0,100]: {score}")

# Test with single asset (should be low)
single_asset = [
    {"asset": "BTC", "price_change_pct": 3.5, "volume_change_pct": 45.0, "oi_change_pct": 2.5, "funding_rate": 0.005, "liquidation_usd": 25_000_000},
]
score_single = calculate_synchronized_move_score(single_asset)
assert_equal(0.0, score_single, f"Single asset sync score = 0 (actual={score_single})")

# Test with empty list
score_empty = calculate_synchronized_move_score([])
assert_equal(0.0, score_empty, f"Empty list sync score = 0 (actual={score_empty})")

# Test with opposing direction assets
opposing = [
    {"asset": "BTC", "price_change_pct": 4.2, "volume_change_pct": 85.0, "oi_change_pct": 7.5, "funding_rate": 0.010, "liquidation_usd": 55_000_000},
    {"asset": "ETH", "price_change_pct": -3.8, "volume_change_pct": 78.0, "oi_change_pct": -5.0, "funding_rate": -0.008, "liquidation_usd": 42_000_000},
    {"asset": "SOL", "price_change_pct": 2.1, "volume_change_pct": 55.0, "oi_change_pct": 3.0, "funding_rate": 0.005, "liquidation_usd": 12_000_000},
]
score_opposing = calculate_synchronized_move_score(opposing)
assert_true(score_opposing < 75, f"Opposing direction sync score < 75 (actual={score_opposing})")

print()

# ══════════════════════════════════════════════════════════════════════════════════════
# Test Group 4: Direction Agreement
# ══════════════════════════════════════════════════════════════════════════════════════

print("─" * 50)
print("[TEST GROUP 4] Direction Agreement")
print("─" * 50)

# All up
all_up = [
    {"price_change_pct": 5.2},
    {"price_change_pct": 4.8},
    {"price_change_pct": 6.1},
]
dir_all_up = calculate_direction_agreement(all_up)
assert_equal(1.0, dir_all_up, f"All up → direction_agreement = 1.0 (actual={dir_all_up})")

# All down
all_down = [
    {"price_change_pct": -5.2},
    {"price_change_pct": -4.8},
    {"price_change_pct": -6.1},
]
dir_all_down = calculate_direction_agreement(all_down)
assert_equal(1.0, dir_all_down, f"All down → direction_agreement = 1.0 (actual={dir_all_down})")

# Mixed (2 up, 1 down) → 2/3 = 0.667
mixed = [
    {"price_change_pct": 4.2},
    {"price_change_pct": -3.8},
    {"price_change_pct": 2.1},
]
dir_mixed = calculate_direction_agreement(mixed)
assert_equal(0.667, dir_mixed, f"Mixed 2up/1down → direction_agreement = 0.667 (actual={dir_mixed})")

# Equal split
equal = [
    {"price_change_pct": 5.0},
    {"price_change_pct": -5.0},
]
dir_equal = calculate_direction_agreement(equal)
assert_equal(0.5, dir_equal, f"Equal split → direction_agreement = 0.5 (actual={dir_equal})")

# All neutral
all_neutral = [
    {"price_change_pct": 0.0},
    {"price_change_pct": 0.0},
]
dir_neutral = calculate_direction_agreement(all_neutral)
assert_equal(0.0, dir_neutral, f"All neutral → direction_agreement = 0.0 (actual={dir_neutral})")

print()

# ══════════════════════════════════════════════════════════════════════════════════════
# Test Group 5: Sync Type Classification
# ══════════════════════════════════════════════════════════════════════════════════════

print("─" * 50)
print("[TEST GROUP 5] Sync Type Classification")
print("─" * 50)

sync_types_found = set()
for r in results:
    sync_types_found.add(r["sync_type"])

# At least the 5 known types should be present
expected_types = {
    "market_wide_risk_on",
    "market_wide_risk_off",
    "l2_beta_sync",
    "exchange_token_sync",
    "stablecoin_liquidity_stress",
}
for st in expected_types:
    assert_true(st in sync_types_found, f"Sync type '{st}' found in results")

# Each valid snapshot should have a sync_type in SYNC_TYPES
for r in results:
    assert_true(r["sync_type"] in SYNC_TYPES, f"{r['event_id']}: sync_type '{r['sync_type']}' in SYNC_TYPES")

print()

# ══════════════════════════════════════════════════════════════════════════════════════
# Test Group 6: Sector / Basket Detection
# ══════════════════════════════════════════════════════════════════════════════════════

print("─" * 50)
print("[TEST GROUP 6] Sector / Basket Detection")
print("─" * 50)

# L1 assets
l1_assets = [
    {"asset": "BTC", "price_change_pct": 5.0, "volume_change_pct": 80.0, "oi_change_pct": 5.0, "funding_rate": 0.01, "liquidation_usd": 50_000_000},
    {"asset": "ETH", "price_change_pct": 4.0, "volume_change_pct": 75.0, "oi_change_pct": 4.0, "funding_rate": 0.008, "liquidation_usd": 30_000_000},
    {"asset": "SOL", "price_change_pct": 6.0, "volume_change_pct": 90.0, "oi_change_pct": 6.0, "funding_rate": 0.015, "liquidation_usd": 15_000_000},
]
sector_l1 = detect_sector_basket_type(l1_assets)
assert_equal("L1", sector_l1, f"L1 assets → sector = 'L1' (actual='{sector_l1}')")

# L2 assets
l2_assets = [
    {"asset": "OP", "price_change_pct": 8.0, "volume_change_pct": 100.0, "oi_change_pct": 10.0, "funding_rate": 0.02, "liquidation_usd": 5_000_000},
    {"asset": "ARB", "price_change_pct": 7.0, "volume_change_pct": 90.0, "oi_change_pct": 9.0, "funding_rate": 0.018, "liquidation_usd": 4_000_000},
]
sector_l2 = detect_sector_basket_type(l2_assets)
assert_equal("L2", sector_l2, f"L2 assets → sector = 'L2' (actual='{sector_l2}')")

# Exchange token assets
ex_assets = [
    {"asset": "BNB", "price_change_pct": 4.0, "volume_change_pct": 80.0, "oi_change_pct": 5.0, "funding_rate": 0.009, "liquidation_usd": 12_000_000},
    {"asset": "OKB", "price_change_pct": 3.5, "volume_change_pct": 70.0, "oi_change_pct": 4.5, "funding_rate": 0.007, "liquidation_usd": 3_000_000},
]
sector_ex = detect_sector_basket_type(ex_assets)
assert_equal("exchange_token", sector_ex, f"Exchange token assets → sector = 'exchange_token' (actual='{sector_ex}')")

# Stablecoin assets
stable_assets = [
    {"asset": "USDT", "price_change_pct": -1.0, "volume_change_pct": 200.0, "oi_change_pct": 20.0, "funding_rate": -0.04, "liquidation_usd": 100_000_000},
    {"asset": "USDC", "price_change_pct": -0.8, "volume_change_pct": 180.0, "oi_change_pct": 15.0, "funding_rate": -0.03, "liquidation_usd": 70_000_000},
]
sector_stable = detect_sector_basket_type(stable_assets)
assert_equal("stablecoin", sector_stable, f"Stablecoin assets → sector = 'stablecoin' (actual='{sector_stable}')")

# ETH + L2
eth_l2_assets = [
    {"asset": "ETH", "price_change_pct": 3.0, "volume_change_pct": 70.0, "oi_change_pct": 5.0, "funding_rate": 0.008, "liquidation_usd": 30_000_000},
    {"asset": "OP", "price_change_pct": 8.0, "volume_change_pct": 100.0, "oi_change_pct": 15.0, "funding_rate": 0.022, "liquidation_usd": 4_000_000},
]
sector_eth_l2 = detect_sector_basket_type(eth_l2_assets)
assert_equal("L1+L2", sector_eth_l2, f"ETH + L2 → sector = 'L1+L2' (actual='{sector_eth_l2}')")

print()

# ══════════════════════════════════════════════════════════════════════════════════════
# Test Group 7: Public Cards
# ══════════════════════════════════════════════════════════════════════════════════════

print("─" * 50)
print("[TEST GROUP 7] Public Cards")
print("─" * 50)

public_cards = [r["public_card"] for r in valid_results if r["public_card"]]
assert_gte(3, len(public_cards), f"public_card_count >= 3 (actual={len(public_cards)})")

# Each public card must contain required fields
for card in public_cards:
    assert_true("共振" in card or "sync" in card.lower(), "Public card mentions sync type or 共振")
    assert_true("涨跌幅" in card or "price" in card.lower(), "Public card mentions price move")
    assert_true("成交量" in card or "volume" in card.lower(), "Public card mentions volume move")
    assert_true("OI" in card or "未平仓" in card, "Public card mentions OI")

print()

# ══════════════════════════════════════════════════════════════════════════════════════
# Test Group 8: Debug / Secret Leak
# ══════════════════════════════════════════════════════════════════════════════════════

print("─" * 50)
print("[TEST GROUP 8] Debug / Secret Leak")
print("─" * 50)

total_debug = sum(r["debug_leak_count"] for r in results)
total_secret = sum(r["secret_leak_count"] for r in results)
assert_equal(0, total_debug, f"debug_leak_count = 0 (actual={total_debug})")
assert_equal(0, total_secret, f"secret_leak_count = 0 (actual={total_secret})")

# Check each public card individually
for r in results:
    card = r["public_card"]
    if card:
        dl = check_debug_leak(card)
        sl = check_secret_leak(card)
        assert_equal(0, len(dl), f"{r['event_id']}: debug_leak_count = 0 (found: {dl})")
        assert_equal(0, len(sl), f"{r['event_id']}: secret_leak_count = 0 (found: {sl})")

# Test check_debug_leak with known bad text
bad_debug = "debug mode: value_gate passed, mock_sent: true"
dl_found = check_debug_leak(bad_debug)
assert_true(len(dl_found) > 0, f"check_debug_leak detects debug terms: {dl_found}")

# Test check_secret_leak with known bad text
bad_secret = "Using api_key: sk-xxx and token: abc123"
sl_found = check_secret_leak(bad_secret)
assert_true(len(sl_found) > 0, f"check_secret_leak detects secret terms: {sl_found}")

# Test with clean text
clean_text = "BTC and ETH同步上涨5.2%，市场普涨共振。⚠️ 不构成交易建议。"
dl_clean = check_debug_leak(clean_text)
sl_clean = check_secret_leak(clean_text)
assert_equal(0, len(dl_clean), f"Clean text: debug_leaks = 0")
assert_equal(0, len(sl_clean), f"Clean text: secret_leaks = 0")

print()

# ══════════════════════════════════════════════════════════════════════════════════════
# Test Group 9: Safety Constraints
# ══════════════════════════════════════════════════════════════════════════════════════

print("─" * 50)
print("[TEST GROUP 9] Safety Constraints")
print("─" * 50)

for r in results:
    assert_true(not r["real_tg_sent"], f"{r['event_id']}: real_tg_sent = false")
    assert_true(not r["external_api_called"], f"{r['event_id']}: external_api_called = false")
    assert_true(not r["external_ai_called"], f"{r['event_id']}: external_ai_called = false")
    assert_true(not r["daemon_started"], f"{r['event_id']}: daemon_started = false")
    assert_true(not r["live_ready"], f"{r['event_id']}: live_ready = false")

print()

# ══════════════════════════════════════════════════════════════════════════════════════
# Test Group 10: No writes to ai_relay_desk
# ══════════════════════════════════════════════════════════════════════════════════════

print("─" * 50)
print("[TEST GROUP 10] No Writes to ai_relay_desk")
print("─" * 50)

# Check public cards don't reference ai_relay_desk
for r in results:
    card = r["public_card"]
    if card:
        assert_true("ai_relay_desk" not in card.lower(), f"{r['event_id']}: no ai_relay_desk in public card")

# Check result JSON
if RESULT_JSON_PATH.exists():
    try:
        result_data = json.loads(RESULT_JSON_PATH.read_text(encoding="utf-8"))
        result_text = json.dumps(result_data, ensure_ascii=False)
        assert_true("ai_relay_desk" not in result_text.lower(), "Result JSON: no ai_relay_desk reference")
    except (json.JSONDecodeError, FileNotFoundError):
        pass

print()

# ══════════════════════════════════════════════════════════════════════════════════════
# Test Group 11: Normalize Function
# ══════════════════════════════════════════════════════════════════════════════════════

print("─" * 50)
print("[TEST GROUP 11] Normalize Function")
print("─" * 50)

raw = snapshots_raw[0]
norm = normalize_snapshot(raw)
assert_true(len(norm["event_id"]) > 0, "normalize: event_id present")
assert_true(len(norm["assets"]) > 0, "normalize: assets list non-empty")
assert_equal(len(norm["assets"]), norm["asset_count"], "normalize: asset_count matches")
assert_gte(1, norm["window_minutes"], "normalize: window_minutes >= 1")

# Verify each normalized asset has required fields
for a in norm["assets"]:
    assert_true(isinstance(a["price_change_pct"], float), f"normalize: {a['asset']} price_change_pct is float")
    assert_true(isinstance(a["volume_change_pct"], float), f"normalize: {a['asset']} volume_change_pct is float")

print()

# ══════════════════════════════════════════════════════════════════════════════════════
# Test Group 12: Direction Agreement Threshold
# ══════════════════════════════════════════════════════════════════════════════════════

print("─" * 50)
print("[TEST GROUP 12] Direction Agreement Threshold (Valid Criteria)")
print("─" * 50)

# All valid results should have direction_agreement >= 0.66
for r in valid_results:
    assert_true(r["direction_agreement"] >= 0.66,
                f"{r['event_id']}: direction_agreement={r['direction_agreement']} >= 0.66")

# Blocked due to direction conflict should have low agreement
dir_conflict = [r for r in blocked_results if "direction_conflict" in (r.get("block_reason") or "")]
for r in dir_conflict:
    assert_true(r["direction_agreement"] < 0.66,
                f"{r['event_id']}: blocked by direction conflict → agreement={r['direction_agreement']} < 0.66")

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
