"""Market Radar v1.12-B — Liquidation Feed Adapter 单元测试

测试覆盖:
  1. valid BTC long liquidation pressure → 可生成 signal
  2. valid ETH short liquidation pressure → 可生成 signal
  3. valid SOL two-sided pressure → 可生成 signal
  4. 缺 asset → block
  5. liquidation 全为 0 → block
  6. public preview 不含 debug/internal terms
  7. data_mode=fixture 不得标记 live_ready
  8. normalize 输出稳定
  9. render 输出稳定
  10. 不读取 token/API key
  11. 不调用网络
  12. 不发送 TG
  13. 不启动 loop/daemon/cron

Security:
    - Does NOT read, print, or save any token / chat_id / key / cookie / password.
    - Does NOT access environment variables for credentials.
    - Does NOT make network calls.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.market_radar_liquidation_feed_v112b import (
    VERSION,
    MODE,
    LiquidationSnapshot,
    LiquidationCluster,
    LiquidationPressureSignal,
    normalize_liquidation_snapshot,
    detect_liquidation_pressure,
    render_liquidation_pressure_card,
    validate_liquidation_signal,
    check_public_debug_leak,
    process_raw_snapshot,
    PUBLIC_FORBIDDEN_TERMS,
)


# ══════════════════════════════════════════════════════════════════════════════════════
# Fixture Data
# ══════════════════════════════════════════════════════════════════════════════════════

BTC_LONG_PRESSURE = {
    "sample_id": "test_btc_long",
    "data_mode": "fixture",
    "source": "local_fixture",
    "asset": "BTC",
    "timestamp_utc": "2026-06-04T12:00:00Z",
    "price": 63500.00,
    "long_liquidation_usd_1h": 18500000,
    "short_liquidation_usd_1h": 3200000,
    "long_liquidation_usd_24h": 125000000,
    "short_liquidation_usd_24h": 28000000,
    "liquidation_cluster_above": [
        {"price_low": 65000, "price_high": 66000, "liquidation_usd": 8000000, "direction": "short"},
    ],
    "liquidation_cluster_below": [
        {"price_low": 62000, "price_high": 63000, "liquidation_usd": 45000000, "direction": "long"},
    ],
    "open_interest_usd": 18500000000,
    "volume_24h_usd": 42000000000,
}

ETH_SHORT_PRESSURE = {
    "sample_id": "test_eth_short",
    "data_mode": "fixture",
    "source": "local_fixture",
    "asset": "ETH",
    "timestamp_utc": "2026-06-04T12:00:00Z",
    "price": 3050.00,
    "long_liquidation_usd_1h": 4200000,
    "short_liquidation_usd_1h": 22000000,
    "long_liquidation_usd_24h": 38000000,
    "short_liquidation_usd_24h": 145000000,
    "liquidation_cluster_above": [
        {"price_low": 3100, "price_high": 3200, "liquidation_usd": 55000000, "direction": "short"},
    ],
    "liquidation_cluster_below": [
        {"price_low": 2900, "price_high": 2980, "liquidation_usd": 12000000, "direction": "long"},
    ],
    "open_interest_usd": 8200000000,
    "volume_24h_usd": 18500000000,
}

SOL_TWO_SIDED = {
    "sample_id": "test_sol_two_sided",
    "data_mode": "fixture",
    "source": "local_fixture",
    "asset": "SOL",
    "timestamp_utc": "2026-06-04T12:00:00Z",
    "price": 142.50,
    "long_liquidation_usd_1h": 28000000,
    "short_liquidation_usd_1h": 31000000,
    "long_liquidation_usd_24h": 185000000,
    "short_liquidation_usd_24h": 210000000,
    "liquidation_cluster_above": [
        {"price_low": 148, "price_high": 155, "liquidation_usd": 65000000, "direction": "short"},
    ],
    "liquidation_cluster_below": [
        {"price_low": 130, "price_high": 138, "liquidation_usd": 72000000, "direction": "long"},
    ],
    "open_interest_usd": 2100000000,
    "volume_24h_usd": 5800000000,
}

MISSING_ASSET = {
    "sample_id": "test_missing_asset",
    "data_mode": "fixture",
    "source": "local_fixture",
    "asset": "",
    "timestamp_utc": "2026-06-04T12:00:00Z",
    "price": 50000.00,
    "long_liquidation_usd_1h": 5000000,
    "short_liquidation_usd_1h": 2000000,
    "long_liquidation_usd_24h": 30000000,
    "short_liquidation_usd_24h": 15000000,
    "liquidation_cluster_above": [],
    "liquidation_cluster_below": [
        {"price_low": 48000, "price_high": 49500, "liquidation_usd": 12000000, "direction": "long"},
    ],
    "open_interest_usd": 0,
    "volume_24h_usd": 0,
}

ZERO_LIQUIDATION = {
    "sample_id": "test_zero_liq",
    "data_mode": "fixture",
    "source": "local_fixture",
    "asset": "DOGE",
    "timestamp_utc": "2026-06-04T12:00:00Z",
    "price": 0.12,
    "long_liquidation_usd_1h": 0,
    "short_liquidation_usd_1h": 0,
    "long_liquidation_usd_24h": 0,
    "short_liquidation_usd_24h": 0,
    "liquidation_cluster_above": [],
    "liquidation_cluster_below": [],
    "open_interest_usd": 0,
    "volume_24h_usd": 0,
}


# ══════════════════════════════════════════════════════════════════════════════════════
# Tests
# ══════════════════════════════════════════════════════════════════════════════════════

def test_1_btc_long_liquidation_pressure_signal() -> bool:
    """1. valid BTC long liquidation pressure 可生成 signal。"""
    result = process_raw_snapshot(BTC_LONG_PRESSURE)
    if result["blocked"]:
        print(f"  [FAIL] BTC signal blocked: {result['block_reason']}")
        return False
    if result["signal"] is None:
        print(f"  [FAIL] BTC signal is None")
        return False
    pressure_type = result["signal"].get("pressure_type", "")
    if pressure_type == "long_liquidation_pressure":
        print(f"  [PASS] BTC → {pressure_type}")
        return True
    print(f"  [FAIL] Expected long_liquidation_pressure, got {pressure_type}")
    return False


def test_2_eth_short_liquidation_pressure_signal() -> bool:
    """2. valid ETH short liquidation pressure 可生成 signal。"""
    result = process_raw_snapshot(ETH_SHORT_PRESSURE)
    if result["blocked"]:
        print(f"  [FAIL] ETH signal blocked: {result['block_reason']}")
        return False
    if result["signal"] is None:
        print(f"  [FAIL] ETH signal is None")
        return False
    pressure_type = result["signal"].get("pressure_type", "")
    if pressure_type == "short_liquidation_pressure":
        print(f"  [PASS] ETH → {pressure_type}")
        return True
    print(f"  [FAIL] Expected short_liquidation_pressure, got {pressure_type}")
    return False


def test_3_sol_two_sided_pressure_signal() -> bool:
    """3. SOL two-sided pressure 可生成 signal。"""
    result = process_raw_snapshot(SOL_TWO_SIDED)
    if result["blocked"]:
        print(f"  [FAIL] SOL signal blocked: {result['block_reason']}")
        return False
    if result["signal"] is None:
        print(f"  [FAIL] SOL signal is None")
        return False
    pressure_type = result["signal"].get("pressure_type", "")
    if pressure_type == "two_sided_liquidation_pressure":
        print(f"  [PASS] SOL → {pressure_type}")
        return True
    print(f"  [FAIL] Expected two_sided_liquidation_pressure, got {pressure_type}")
    return False


def test_4_missing_asset_blocked() -> bool:
    """4. 缺 asset → block。"""
    result = process_raw_snapshot(MISSING_ASSET)
    if not result["blocked"]:
        print(f"  [FAIL] Missing asset sample was NOT blocked")
        return False
    if "asset" in result.get("block_reason", "").lower():
        print(f"  [PASS] Missing asset blocked: {result['block_reason']}")
        return True
    print(f"  [FAIL] Block reason doesn't mention asset: {result['block_reason']}")
    return False


def test_5_zero_liquidation_blocked() -> bool:
    """5. liquidation 全为 0 → block。"""
    result = process_raw_snapshot(ZERO_LIQUIDATION)
    if not result["blocked"]:
        print(f"  [FAIL] Zero liquidation sample was NOT blocked")
        return False
    print(f"  [PASS] Zero liquidation blocked: {result['block_reason']}")
    return True


def test_6_public_preview_no_debug_terms() -> bool:
    """6. public preview 不含 debug/internal terms。"""
    result = process_raw_snapshot(BTC_LONG_PRESSURE)
    public_card = result.get("public_card", "")
    if not public_card:
        print(f"  [FAIL] No public card generated")
        return False

    leaked = check_public_debug_leak(public_card)
    if len(leaked) > 0:
        print(f"  [FAIL] Debug terms leaked: {leaked}")
        return False

    # Also check for forbidden terms manually
    card_lower = public_card.lower()
    extra_checks = ["value_gate", "cooldown_gate", "admission", "block_rules",
                    "fixture", "mock", "debug", "live_ready"]
    extra_leaked = [t for t in extra_checks if t.lower() in card_lower]
    if extra_leaked:
        print(f"  [FAIL] Extra forbidden terms found: {extra_leaked}")
        return False

    print(f"  [PASS] Public preview is clean ({len(public_card)} chars)")
    return True


def test_7_fixture_not_live_ready() -> bool:
    """7. data_mode=fixture 不得标记 live_ready。"""
    result = process_raw_snapshot(BTC_LONG_PRESSURE)
    live_ready = result.get("live_ready", None)
    if live_ready:
        print(f"  [FAIL] Fixture sample marked as live_ready=True")
        return False
    print(f"  [PASS] Fixture sample live_ready=False")
    return True


def test_8_normalize_output_stable() -> bool:
    """8. normalize 输出稳定（同一输入得同一输出）。"""
    snap1 = normalize_liquidation_snapshot(BTC_LONG_PRESSURE)
    snap2 = normalize_liquidation_snapshot(BTC_LONG_PRESSURE)

    d1 = snap1.to_dict()
    d2 = snap2.to_dict()

    if d1 != d2:
        print(f"  [FAIL] normalize output differs between calls")
        return False

    # Check key fields are preserved
    checks = [
        ("asset", "BTC"),
        ("price", 63500.0),
        ("long_liquidation_usd_1h", 18500000.0),
        ("data_mode", "fixture"),
    ]
    for field, expected in checks:
        actual = d1.get(field)
        if actual != expected:
            print(f"  [FAIL] Field {field}: expected {expected}, got {actual}")
            return False

    print(f"  [PASS] normalize output stable and correct")
    return True


def test_9_render_output_stable() -> bool:
    """9. render 输出稳定且包含关键信息。"""
    result1 = process_raw_snapshot(BTC_LONG_PRESSURE)
    result2 = process_raw_snapshot(BTC_LONG_PRESSURE)

    card1 = result1.get("public_card", "")
    card2 = result2.get("public_card", "")

    if card1 != card2:
        print(f"  [FAIL] render output differs between calls")
        return False

    # Check card contains essential info
    checks = [
        "清算压力",
        "BTC",
        "不构成交易建议",
        "当前价格",
    ]
    for check in checks:
        if check not in card1:
            print(f"  [FAIL] Card missing: '{check}'")
            return False

    print(f"  [PASS] render output stable and contains essential info")
    return True


def test_10_no_token_or_key_in_module() -> bool:
    """10. 不读取 token/API key（仅检查非注释/安全声明中的真实凭据）。"""
    import re
    module_path = ROOT / "scripts" / "market_radar_liquidation_feed_v112b.py"
    with open(module_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    # Patterns that indicate actual credential usage (not "don't do X" comments)
    credential_assign_patterns = [
        re.compile(r'^\s*[^#]*\b(api[._-]?key|chat[._-]?id|password|token|secret)\s*[:=]\s*[\'"]', re.IGNORECASE),
    ]
    # Patterns that are always suspicious even in comments
    suspicious_patterns = [
        re.compile(r'\d{8,10}:[A-Za-z0-9_-]{30,}'),  # bot token format
        re.compile(r'sk-[A-Za-z0-9]{20,}'),            # API key format
    ]

    for line in lines:
        # Skip pure comment/docstring lines mentioning security
        stripped = line.strip()
        if stripped.startswith("#") or stripped.startswith('"') or stripped.startswith("'"):
            continue

        for pat in suspicious_patterns:
            if pat.search(line):
                print(f"  [FAIL] Found suspicious credential pattern in code: {line.strip()[:80]}")
                return False

        for pat in credential_assign_patterns:
            if pat.search(line):
                print(f"  [FAIL] Found credential usage in code: {line.strip()[:80]}")
                return False

    print(f"  [PASS] No token/API key/password/cookie in module")
    return True


def test_11_no_network_calls() -> bool:
    """11. 不调用网络。"""
    module_path = ROOT / "scripts" / "market_radar_liquidation_feed_v112b.py"
    with open(module_path, "r", encoding="utf-8") as f:
        source = f.read()

    network_imports = ["import socket", "import requests", "import urllib",
                       "import http.client", "import aiohttp", "import websocket",
                       "import asyncio"]
    for ni in network_imports:
        if ni in source:
            print(f"  [FAIL] Network import found: {ni}")
            return False

    print(f"  [PASS] No network imports in module")
    return True


def test_12_no_tg_send() -> bool:
    """12. 不发送 TG。"""
    module_path = ROOT / "scripts" / "market_radar_liquidation_feed_v112b.py"
    with open(module_path, "r", encoding="utf-8") as f:
        source = f.read()

    tg_patterns = ["telegram", "telebot", "python-telegram-bot", "sendMessage",
                   "send_message", "bot.send"]
    for pat in tg_patterns:
        if pat.lower() in source.lower():
            print(f"  [FAIL] TG-related pattern found: {pat}")
            return False

    print(f"  [PASS] No TG send code in module")
    return True


def test_13_no_daemon_or_loop() -> bool:
    """13. 不启动 loop/daemon/cron。"""
    module_path = ROOT / "scripts" / "market_radar_liquidation_feed_v112b.py"
    with open(module_path, "r", encoding="utf-8") as f:
        source = f.read()

    loop_patterns = ["while True", "schedule.", "cron", "daemon",
                     "setInterval", "setTimeout", "time.sleep", "asyncio.run"]
    for pat in loop_patterns:
        if pat in source:
            print(f"  [FAIL] Loop/daemon pattern found: {pat}")
            return False

    print(f"  [PASS] No loop/daemon/cron patterns in module")
    return True


def test_14_fixture_json_loads_all_snapshots() -> bool:
    """14. Fixture JSON 包含全部 5 条快照且标记正确。"""
    fixture_path = ROOT / "data" / "fixtures" / "market_radar_v112b_liquidation_snapshots.json"
    try:
        with open(fixture_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"  [FAIL] Fixture file not found: {fixture_path}")
        return False

    snapshots = data.get("snapshots", [])
    if len(snapshots) != 5:
        print(f"  [FAIL] Expected 5 snapshots, got {len(snapshots)}")
        return False

    for s in snapshots:
        if s.get("data_mode") != "fixture":
            print(f"  [FAIL] {s.get('sample_id')} data_mode is '{s.get('data_mode')}', expected 'fixture'")
            return False
        if s.get("source") != "local_fixture":
            print(f"  [FAIL] {s.get('sample_id')} source is '{s.get('source')}', expected 'local_fixture'")
            return False

    print(f"  [PASS] All 5 snapshots correctly marked data_mode=fixture")
    return True


def test_15_disclaimer_in_all_cards() -> bool:
    """15. 所有 public card 包含「不构成交易建议」。"""
    valid_samples = [BTC_LONG_PRESSURE, ETH_SHORT_PRESSURE, SOL_TWO_SIDED]
    passed = 0
    for sample in valid_samples:
        result = process_raw_snapshot(sample)
        card = result.get("public_card", "")
        if "不构成交易建议" in card:
            passed += 1
        else:
            print(f"  [FAIL] {sample['sample_id']} missing disclaimer")
    if passed == len(valid_samples):
        print(f"  [PASS] All {passed} cards contain disclaimer")
        return True
    print(f"  [FAIL] Only {passed}/{len(valid_samples)} cards have disclaimer")
    return False


def test_16_card_contains_observation_window() -> bool:
    """16. 卡片包含观察窗口提示。"""
    result = process_raw_snapshot(BTC_LONG_PRESSURE)
    card = result.get("public_card", "")
    if "观察窗口" in card:
        print(f"  [PASS] Card contains observation window")
        return True
    print(f"  [FAIL] Card missing observation window")
    return False


def test_17_card_contains_trigger_reason() -> bool:
    """17. 卡片包含触发原因说明。"""
    result = process_raw_snapshot(BTC_LONG_PRESSURE)
    card = result.get("public_card", "")
    if "触发原因" in card:
        print(f"  [PASS] Card contains trigger reason")
        return True
    print(f"  [FAIL] Card missing trigger reason")
    return False


def test_18_process_all_fixture_snapshots() -> bool:
    """18. 处理 fixture JSON 中全部 5 条快照，统计正确。"""
    fixture_path = ROOT / "data" / "fixtures" / "market_radar_v112b_liquidation_snapshots.json"
    with open(fixture_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    snapshots = data.get("snapshots", [])
    valid_count = 0
    blocked_count = 0

    for raw in snapshots:
        result = process_raw_snapshot(raw)
        if result["blocked"]:
            blocked_count += 1
        else:
            valid_count += 1

    if valid_count == 3 and blocked_count == 2:
        print(f"  [PASS] 3 valid signals + 2 blocked = {valid_count}+{blocked_count}")
        return True
    print(f"  [FAIL] Expected 3+2, got {valid_count}+{blocked_count}")
    return False


def test_19_validate_function_returns_correct_structure() -> bool:
    """19. validate_liquidation_signal 返回结构正确。"""
    snapshot = normalize_liquidation_snapshot(BTC_LONG_PRESSURE)
    signal = detect_liquidation_pressure(snapshot)
    if signal is None:
        print(f"  [FAIL] detect returned None for valid BTC sample")
        return False

    validation = validate_liquidation_signal(signal)
    required_keys = ["valid", "blocked", "block_reason", "warnings", "live_ready", "data_mode_ok"]
    for key in required_keys:
        if key not in validation:
            print(f"  [FAIL] Missing key in validation: {key}")
            return False

    if not validation["valid"]:
        print(f"  [FAIL] Valid signal marked as invalid: {validation['block_reason']}")
        return False

    print(f"  [PASS] Validation structure correct for valid signal")
    return True


def test_20_empty_snapshot_blocked() -> bool:
    """20. 空快照被正确阻止。"""
    empty = {
        "sample_id": "test_empty",
        "data_mode": "fixture",
        "source": "local_fixture",
        "asset": "",
        "price": 0,
        "long_liquidation_usd_1h": 0,
        "short_liquidation_usd_1h": 0,
    }
    result = process_raw_snapshot(empty)
    if not result["blocked"]:
        print(f"  [FAIL] Empty snapshot was NOT blocked")
        return False
    print(f"  [PASS] Empty snapshot blocked: {result['block_reason']}")
    return True


# ══════════════════════════════════════════════════════════════════════════════════════
# Run All Tests
# ══════════════════════════════════════════════════════════════════════════════════════

def run_all_tests() -> int:
    tests = [
        ("BTC long liquidation pressure signal", test_1_btc_long_liquidation_pressure_signal),
        ("ETH short liquidation pressure signal", test_2_eth_short_liquidation_pressure_signal),
        ("SOL two-sided pressure signal", test_3_sol_two_sided_pressure_signal),
        ("缺 asset block", test_4_missing_asset_blocked),
        ("清算全为 0 block", test_5_zero_liquidation_blocked),
        ("public preview 不含 debug terms", test_6_public_preview_no_debug_terms),
        ("fixture 不标记 live_ready", test_7_fixture_not_live_ready),
        ("normalize 输出稳定", test_8_normalize_output_stable),
        ("render 输出稳定", test_9_render_output_stable),
        ("不读取 token/API key", test_10_no_token_or_key_in_module),
        ("不调用网络", test_11_no_network_calls),
        ("不发送 TG", test_12_no_tg_send),
        ("不启动 loop/daemon/cron", test_13_no_daemon_or_loop),
        ("Fixture JSON 所有快照正确标记", test_14_fixture_json_loads_all_snapshots),
        ("所有卡片含 disclaimer", test_15_disclaimer_in_all_cards),
        ("卡片含观察窗口", test_16_card_contains_observation_window),
        ("卡片含触发原因", test_17_card_contains_trigger_reason),
        ("全量 fixture 处理统计正确", test_18_process_all_fixture_snapshots),
        ("validate 返回结构正确", test_19_validate_function_returns_correct_structure),
        ("空快照被正确阻止", test_20_empty_snapshot_blocked),
    ]

    print("=" * 60)
    print(f"Market Radar Liquidation Feed {VERSION} — 测试套件")
    print("=" * 60)

    passed = 0
    failed = 0

    for name, test_fn in tests:
        print(f"\n── {name} ──")
        try:
            ok = test_fn()
            if ok:
                passed += 1
            else:
                failed += 1
        except Exception as exc:
            failed += 1
            import traceback
            print(f"  [EXCEPTION] {exc}")
            traceback.print_exc()

    print(f"\n{'=' * 60}")
    print(f"Results: {passed}/{passed + failed} passed, {failed} failed")
    print(f"{'=' * 60}")

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(run_all_tests())
