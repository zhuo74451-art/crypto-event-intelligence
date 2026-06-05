"""Market Radar v1.12-C — Liquidation Pipeline Integration 单元测试

Tests:
  1. liquidation_pressure registry readiness 可从 missing 变 partial
  2. v112b 3 条 valid signal 全部能进入 v112c pipeline
  3. 2 条 invalid sample 仍然 block
  4. public card 不含 debug/internal terms
  5. fixture 不得 live_ready
  6. mock_send_ready 可以 true，但 real_tg_sent 必须 false
  7. fixed card matrix 仍保持 5 类
  8. price_oi_volume_anomaly 仍为 ready
  9. liquidation_pressure 更新为 partial
  10. news_event_market_impact 仍为 missing
  11. 不调用网络
  12. 不读取 token/API key
  13. 不发送 TG
  14. 不启动 loop/daemon/cron

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
    normalize_liquidation_snapshot,
    detect_liquidation_pressure,
    render_liquidation_pressure_card,
    validate_liquidation_signal,
    check_public_debug_leak as check_v112b_debug_leak,
    process_raw_snapshot,
    LiquidationPressureSignal,
)

from scripts.market_radar_card_type_registry_v112a import (
    get_all_card_types,
    get_card_type,
    list_card_types,
    get_card_type_count,
    validate_signal_against_card_type,
    render_public_preview,
    assess_readiness,
    check_public_debug_leak,
    update_liquidation_readiness_from_adapter,
    get_fixed_card_matrix_summary,
)


# ══════════════════════════════════════════════════════════════════════════════════════
# Fixture Data (same as v112b fixture + additional test cases)
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
    "liquidation_cluster_below": [],
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
# Helper: full v112c pipeline for a single raw snapshot
# ══════════════════════════════════════════════════════════════════════════════════════

def run_v112c_pipeline(raw: dict) -> dict:
    """Run a single snapshot through the full v112c integration pipeline.

    Steps:
      1. v112b: normalize → detect → validate
      2. v112a: schema check against liquidation_pressure card type
      3. v112a: admission + block check
      4. v112a: public card render
      5. v112a + v112b: debug leak check
      6. mock send readiness

    Returns a result dict matching the specified output format.
    """
    # v112b processing
    v112b_result = process_raw_snapshot(raw)

    if v112b_result["blocked"]:
        return {
            "card_type": "liquidation_pressure",
            "signal_id": raw.get("sample_id", "unknown"),
            "asset": v112b_result.get("asset", ""),
            "pressure_type": "none",
            "data_mode": "fixture",
            "schema_valid": False,
            "admission_passed": False,
            "block_passed": False,
            "public_card_rendered": False,
            "debug_leak_found": False,
            "mock_send_ready": False,
            "live_ready": False,
            "blocked": True,
            "block_reason": v112b_result["block_reason"],
        }

    signal_data = v112b_result.get("signal")
    if signal_data is None:
        return {
            "card_type": "liquidation_pressure",
            "signal_id": raw.get("sample_id", "unknown"),
            "asset": v112b_result.get("asset", ""),
            "pressure_type": "none",
            "data_mode": "fixture",
            "schema_valid": False,
            "admission_passed": False,
            "block_passed": False,
            "public_card_rendered": False,
            "debug_leak_found": False,
            "mock_send_ready": False,
            "live_ready": False,
            "blocked": True,
            "block_reason": "v112b detect returned None",
        }

    # Build v112a-compatible signal
    asset = signal_data.get("asset", "")
    v112a_signal = {
        "signal_type": "liquidation_pressure",
        "asset": asset,
        "core_entity": asset,
        "liquidation_level": signal_data.get("cluster_below_total_usd") or signal_data.get("cluster_above_total_usd"),
        "leverage_zone": f"价格 ${int(signal_data.get('price', 0)):,} 附近",
        "long_liq_total": signal_data.get("long_liquidation_usd_1h", 0),
        "short_liq_total": signal_data.get("short_liquidation_usd_1h", 0),
        "liq_cluster_price": signal_data.get("price"),
        "liq_cluster_size": signal_data.get("total_liquidation_usd_1h", 0),
        "crowded_direction": (
            "long" if "long_liquidation" in signal_data.get("pressure_type", "")
            else "short" if "short_liquidation" in signal_data.get("pressure_type", "")
            else ""
        ),
        "risk_level": (
            "critical" if signal_data.get("total_liquidation_usd_1h", 0) >= 50_000_000
            else "high" if signal_data.get("total_liquidation_usd_1h", 0) >= 20_000_000
            else "medium"
        ),
        "trigger_reason": signal_data.get("trigger_description", ""),
        "source_type": "fixture",
        "is_fixture": True,
        "data_mode": "fixture",
        "source": signal_data.get("source", "local_fixture"),
        "observed_at": signal_data.get("timestamp_utc", ""),
    }

    # v112a: get card type definition
    ct_def = get_card_type("liquidation_pressure")
    if ct_def is None:
        return {
            "card_type": "liquidation_pressure",
            "signal_id": raw.get("sample_id", "unknown"),
            "asset": asset,
            "pressure_type": signal_data.get("pressure_type", "unknown"),
            "data_mode": "fixture",
            "schema_valid": False,
            "admission_passed": False,
            "block_passed": False,
            "public_card_rendered": False,
            "debug_leak_found": False,
            "mock_send_ready": False,
            "live_ready": False,
            "blocked": True,
            "block_reason": "card_type not found in registry",
        }

    # v112a: validate against card type
    validation = validate_signal_against_card_type(v112a_signal, ct_def)
    schema_valid = validation["schema_valid"]
    admission_passed = validation["admission_passed"]
    block_triggered = validation["block_triggered"]

    if block_triggered:
        return {
            "card_type": "liquidation_pressure",
            "signal_id": raw.get("sample_id", "unknown"),
            "asset": asset,
            "pressure_type": signal_data.get("pressure_type", "unknown"),
            "data_mode": "fixture",
            "schema_valid": schema_valid,
            "admission_passed": admission_passed,
            "block_passed": False,
            "public_card_rendered": False,
            "debug_leak_found": False,
            "mock_send_ready": False,
            "live_ready": False,
            "blocked": True,
            "block_reason": validation.get("block_reason", "v112a block"),
        }

    # v112a: render public card
    try:
        public_card = render_public_preview(ct_def, v112a_signal, validation)
    except Exception:
        public_card = ""
    public_card_rendered = len(public_card) > 50

    # Debug leak check (both v112a and v112b)
    leaked_v112a = check_public_debug_leak(public_card, ct_def)
    leaked_v112b = check_v112b_debug_leak(public_card)
    all_leaked = list(set(leaked_v112a + leaked_v112b))
    debug_leak_found = len(all_leaked) > 0

    # Live ready check (fixture must never be live_ready)
    live_ready = signal_data.get("live_ready", False)
    if signal_data.get("data_mode") == "fixture" and live_ready:
        live_ready = False

    mock_send_ready = (
        schema_valid and admission_passed and not block_triggered
        and public_card_rendered and not debug_leak_found
    )

    return {
        "card_type": "liquidation_pressure",
        "signal_id": raw.get("sample_id", "unknown"),
        "asset": asset,
        "pressure_type": signal_data.get("pressure_type", "unknown"),
        "data_mode": "fixture",
        "schema_valid": schema_valid,
        "admission_passed": admission_passed,
        "block_passed": not block_triggered,
        "public_card_rendered": public_card_rendered,
        "debug_leak_found": debug_leak_found,
        "mock_send_ready": mock_send_ready,
        "live_ready": live_ready,
        "blocked": False,
        "block_reason": "",
    }


# ══════════════════════════════════════════════════════════════════════════════════════
# Tests
# ══════════════════════════════════════════════════════════════════════════════════════

def test_1_readiness_missing_to_partial() -> bool:
    """1. liquidation_pressure registry readiness 可从 missing 变 partial。"""
    # Force back to missing first
    update_liquidation_readiness_from_adapter(force_missing=True)

    # Now update with valid signals
    result = update_liquidation_readiness_from_adapter(
        valid_signal_count=3,
        public_card_count=3,
    )
    if result["new_readiness"] != "partial":
        print(f"  [FAIL] Expected partial, got {result['new_readiness']}")
        return False
    if result["previous_readiness"] != "missing":
        print(f"  [FAIL] Expected previous=missing, got {result['previous_readiness']}")
        return False
    print(f"  [PASS] Readiness: {result['previous_readiness']} → {result['new_readiness']}")
    return True


def test_2_three_valid_signals_pass_pipeline() -> bool:
    """2. v112b 3 条 valid signal 全部能进入 v112c pipeline。"""
    valid_samples = [BTC_LONG_PRESSURE, ETH_SHORT_PRESSURE, SOL_TWO_SIDED]
    passed = 0
    for sample in valid_samples:
        result = run_v112c_pipeline(sample)
        if result["mock_send_ready"]:
            passed += 1
        else:
            print(f"  [FAIL] {sample['sample_id']}: mock_send_ready=False, blocked={result.get('blocked')}, reason={result.get('block_reason')}")
    if passed == 3:
        print(f"  [PASS] All 3 valid signals pass pipeline: {passed}/3")
        return True
    print(f"  [FAIL] Only {passed}/3 passed")
    return False


def test_3_two_invalid_samples_blocked() -> bool:
    """3. 2 条 invalid sample 仍然 block。"""
    invalid_samples = [MISSING_ASSET, ZERO_LIQUIDATION]
    blocked = 0
    for sample in invalid_samples:
        result = run_v112c_pipeline(sample)
        if result.get("blocked", False):
            blocked += 1
        else:
            print(f"  [FAIL] {sample['sample_id']}: should be blocked but mock_send_ready={result['mock_send_ready']}")
    if blocked == 2:
        print(f"  [PASS] Both invalid samples blocked: {blocked}/2")
        return True
    print(f"  [FAIL] Only {blocked}/2 blocked")
    return False


def test_4_public_card_no_debug_terms() -> bool:
    """4. public card 不含 debug/internal terms。"""
    ct_def = get_card_type("liquidation_pressure")
    if ct_def is None:
        print(f"  [FAIL] liquidation_pressure not in registry")
        return False

    result = run_v112c_pipeline(BTC_LONG_PRESSURE)
    if result.get("debug_leak_found", True):
        print(f"  [FAIL] Debug leak found in v112c pipeline result")
        return False

    # Also check via v112a registry renderer directly
    signal = {
        "asset": "BTC",
        "liquidation_level": 62800,
        "leverage_zone": "高杠杆区 $62,000 - $63,500",
        "long_liq_total": 18_500_000,
        "short_liq_total": 3_200_000,
        "liq_cluster_price": 62850,
        "liq_cluster_size": 21_700_000,
        "crowded_direction": "long",
        "risk_level": "high",
        "trigger_reason": "BTC 下方多头清算压力升高",
        "source_type": "fixture",
        "is_fixture": True,
        "data_mode": "fixture",
    }
    validation = validate_signal_against_card_type(signal, ct_def)
    preview = render_public_preview(ct_def, signal, validation)
    leaked = check_public_debug_leak(preview, ct_def)
    if len(leaked) > 0:
        print(f"  [FAIL] v112a debug leak: {leaked}")
        return False

    print(f"  [PASS] Public card is clean — no debug/internal terms")
    return True


def test_5_fixture_not_live_ready() -> bool:
    """5. fixture 不得 live_ready。"""
    result = run_v112c_pipeline(BTC_LONG_PRESSURE)
    if result["live_ready"]:
        print(f"  [FAIL] Fixture sample marked as live_ready=True")
        return False

    # Also test all 3 valid samples
    for sample in [BTC_LONG_PRESSURE, ETH_SHORT_PRESSURE, SOL_TWO_SIDED]:
        r = run_v112c_pipeline(sample)
        if r["live_ready"]:
            print(f"  [FAIL] {sample['sample_id']} live_ready=True")
            return False

    print(f"  [PASS] All fixture samples have live_ready=False")
    return True


def test_6_mock_send_ready_true_but_real_tg_false() -> bool:
    """6. mock_send_ready 可以 true，但 real_tg_sent 必须 false。"""
    # The runner's result.json must have real_tg_sent=false
    result_path = ROOT / "results" / "market_radar_v112c_liquidation_pipeline_integration_result.json"
    if result_path.exists():
        with open(result_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if data.get("real_tg_sent", True):
            print(f"  [FAIL] result.json has real_tg_sent=true")
            return False
        print(f"  [PASS] result.json: real_tg_sent={data.get('real_tg_sent')}")
    else:
        print(f"  [INFO] result.json not yet generated — checking pipeline logic")
        # Check pipeline logic: all samples should have mock_send_ready but live_ready=False
        result = run_v112c_pipeline(BTC_LONG_PRESSURE)
        if result["mock_send_ready"] and not result["live_ready"]:
            print(f"  [PASS] mock_send_ready=True, live_ready=False")
        else:
            print(f"  [FAIL] mock_send_ready={result['mock_send_ready']}, live_ready={result['live_ready']}")
            return False
    return True


def test_7_fixed_card_matrix_still_5_types() -> bool:
    """7. fixed card matrix 仍保持 5 类。"""
    count = get_card_type_count()
    types = list_card_types()
    if count != 5:
        print(f"  [FAIL] Expected 5 card types, got {count}: {types}")
        return False
    print(f"  [PASS] Card type count: {count} — {types}")
    return True


def test_8_price_oi_volume_anomaly_still_ready() -> bool:
    """8. price_oi_volume_anomaly 仍为 ready。"""
    ct_def = get_card_type("price_oi_volume_anomaly")
    if ct_def is None:
        print(f"  [FAIL] price_oi_volume_anomaly not found")
        return False
    level = ct_def.get("readiness_level", "")
    if level != "ready":
        print(f"  [FAIL] Expected ready, got {level}")
        return False
    print(f"  [PASS] price_oi_volume_anomaly readiness={level}")
    return True


def test_9_liquidation_pressure_updated_to_partial() -> bool:
    """9. liquidation_pressure 更新为 partial。"""
    # Ensure registry is updated
    update_liquidation_readiness_from_adapter(valid_signal_count=3, public_card_count=3)
    ct_def = get_card_type("liquidation_pressure")
    if ct_def is None:
        print(f"  [FAIL] liquidation_pressure not found")
        return False
    level = ct_def.get("readiness_level", "")
    if level != "partial":
        print(f"  [FAIL] Expected partial, got {level}")
        return False
    print(f"  [PASS] liquidation_pressure readiness={level}")
    return True


def test_10_news_event_still_missing() -> bool:
    """10. news_event_market_impact 仍为 missing。"""
    ct_def = get_card_type("news_event_market_impact")
    if ct_def is None:
        print(f"  [FAIL] news_event_market_impact not found")
        return False
    level = ct_def.get("readiness_level", "")
    if level != "missing":
        print(f"  [FAIL] Expected missing, got {level}")
        return False
    print(f"  [PASS] news_event_market_impact readiness={level}")
    return True


def test_11_no_network_calls() -> bool:
    """11. 不调用网络。"""
    module_path = ROOT / "scripts" / "run_market_radar_v112c_liquidation_pipeline_integration.py"
    with open(module_path, "r", encoding="utf-8") as f:
        source = f.read()

    network_imports = ["import socket", "import requests", "import urllib",
                       "import http.client", "import aiohttp", "import websocket"]
    for ni in network_imports:
        if ni in source:
            print(f"  [FAIL] Network import found: {ni}")
            return False

    print(f"  [PASS] No network imports in module")
    return True


def test_12_no_token_or_key() -> bool:
    """12. 不读取 token/API key。"""
    import re
    module_path = ROOT / "scripts" / "run_market_radar_v112c_liquidation_pipeline_integration.py"
    with open(module_path, "r", encoding="utf-8") as f:
        source = f.read()

    # Only check for actual credential patterns (not safety statements)
    patterns = [
        (r'\d{8,10}:[A-Za-z0-9_-]{30,}', "bot token"),
        (r'sk-[A-Za-z0-9]{20,}', "API key"),
    ]
    for pattern, label in patterns:
        for line in source.split("\n"):
            if re.search(pattern, line, re.IGNORECASE):
                # Skip safety/docstring lines
                if any(kw in line for kw in ["不", "NOT", "未", "false", "禁止", "Security"]):
                    continue
                print(f"  [FAIL] Found {label} pattern: {line.strip()[:80]}")
                return False

    # Check for real credential assignments (not in notes/constraints)
    cred_assign = re.compile(
        r'(api[._-]?key|chat[._-]?id|password|token|secret)\s*[:=]\s*["\']',
        re.IGNORECASE
    )
    for line in source.split("\n"):
        if cred_assign.search(line):
            # Skip notes/constraint lines
            if any(kw in line for kw in ["不", "NOT", "未", "false", "notes", "安全", "constraint"]):
                continue
            print(f"  [FAIL] Credential assignment found: {line.strip()[:80]}")
            return False

    print(f"  [PASS] No token/API key/password/cookie in module")
    return True


def test_13_no_tg_send() -> bool:
    """13. 不发送 TG。"""
    module_path = ROOT / "scripts" / "run_market_radar_v112c_liquidation_pipeline_integration.py"
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


def test_14_no_daemon_or_loop() -> bool:
    """14. 不启动 loop/daemon/cron。"""
    module_path = ROOT / "scripts" / "run_market_radar_v112c_liquidation_pipeline_integration.py"
    with open(module_path, "r", encoding="utf-8") as f:
        source = f.read()

    loop_patterns = ["while True", "schedule.", "setInterval", "setTimeout", "asyncio.run"]
    # Only check non-safety lines for daemon/cron/time.sleep
    lines = source.split("\n")
    for i, line in enumerate(lines):
        stripped = line.strip()
        # Skip safety/constraint/docstring lines
        if any(kw in stripped for kw in ["NONE", "未启动", "Daemon/Loop", "constraint", "执行约束"]):
            continue
        if stripped.startswith("#") or stripped.startswith('"') or stripped.startswith("'"):
            continue
        for pat in loop_patterns:
            if pat in stripped:
                print(f"  [FAIL] Loop/daemon pattern found: {pat}")
                return False
        # Check for daemon/cron/time.sleep only if not in a constraint context
        safety_keywords = ["NONE", "NO ", "未", "不", "NOT", "false", "禁止", "constraint",
                          "disabled", "Security", "无", "❌"]
        for pat in ["daemon", "cron", "time.sleep"]:
            if pat in stripped.lower():
                if not any(kw in stripped or kw.lower() in stripped.lower() for kw in safety_keywords):
                    print(f"  [FAIL] Loop/daemon pattern found: {pat} in: {stripped[:80]}")
                    return False

    print(f"  [PASS] No loop/daemon/cron patterns in module")
    return True


def test_15_matrix_summary_function() -> bool:
    """15. get_fixed_card_matrix_summary 输出正确。"""
    matrix = get_fixed_card_matrix_summary()
    required_keys = ["ready_count", "partial_count", "missing_count", "card_types"]
    for key in required_keys:
        if key not in matrix:
            print(f"  [FAIL] Missing key in matrix summary: {key}")
            return False
    if len(matrix["card_types"]) != 5:
        print(f"  [FAIL] Expected 5 card types, got {len(matrix['card_types'])}")
        return False
    total = matrix["ready_count"] + matrix["partial_count"] + matrix["missing_count"]
    if total != 5:
        print(f"  [FAIL] Readiness counts don't sum to 5: {matrix['ready_count']}+{matrix['partial_count']}+{matrix['missing_count']}={total}")
        return False
    print(f"  [PASS] Matrix summary: ready={matrix['ready_count']} partial={matrix['partial_count']} missing={matrix['missing_count']}")
    return True


def test_16_whale_position_alert_is_partial() -> bool:
    """16. whale_position_alert 仍为 partial。"""
    ct_def = get_card_type("whale_position_alert")
    if ct_def is None:
        print(f"  [FAIL] whale_position_alert not found")
        return False
    level = ct_def.get("readiness_level", "")
    if level != "partial":
        print(f"  [FAIL] Expected partial, got {level}")
        return False
    print(f"  [PASS] whale_position_alert readiness={level}")
    return True


def test_17_multi_asset_market_sync_is_partial() -> bool:
    """17. multi_asset_market_sync 仍为 partial。"""
    ct_def = get_card_type("multi_asset_market_sync")
    if ct_def is None:
        print(f"  [FAIL] multi_asset_market_sync not found")
        return False
    level = ct_def.get("readiness_level", "")
    if level != "partial":
        print(f"  [FAIL] Expected partial, got {level}")
        return False
    print(f"  [PASS] multi_asset_market_sync readiness={level}")
    return True


def test_18_pressure_types_correct() -> bool:
    """18. 3 条 valid signal 的 pressure_type 正确。"""
    expected = {
        "test_btc_long": "long_liquidation_pressure",
        "test_eth_short": "short_liquidation_pressure",
        "test_sol_two_sided": "two_sided_liquidation_pressure",
    }
    samples = {
        "test_btc_long": BTC_LONG_PRESSURE,
        "test_eth_short": ETH_SHORT_PRESSURE,
        "test_sol_two_sided": SOL_TWO_SIDED,
    }
    for sid, sample in samples.items():
        result = run_v112c_pipeline(sample)
        actual = result.get("pressure_type", "")
        expected_type = expected.get(sid, "")
        if actual != expected_type:
            print(f"  [FAIL] {sid}: expected {expected_type}, got {actual}")
            return False
    print(f"  [PASS] All 3 pressure types correct")
    return True


def test_19_readiness_update_no_adapter_returns_missing() -> bool:
    """19. 无 adapter 数据时 readiness 保持/返回 missing。"""
    result = update_liquidation_readiness_from_adapter(
        valid_signal_count=0,
        public_card_count=0,
    )
    if result["new_readiness"] != "missing":
        print(f"  [FAIL] Expected missing with 0 signals, got {result['new_readiness']}")
        return False
    print(f"  [PASS] Zero signals → missing: {result['reason']}")
    return True


def test_20_readiness_update_force_missing() -> bool:
    """20. force_missing=True 强制返回 missing。"""
    # First set to partial
    update_liquidation_readiness_from_adapter(valid_signal_count=3, public_card_count=3)
    # Then force back
    result = update_liquidation_readiness_from_adapter(force_missing=True)
    if result["new_readiness"] != "missing":
        print(f"  [FAIL] force_missing should return missing, got {result['new_readiness']}")
        return False
    print(f"  [PASS] force_missing works: {result['previous_readiness']} → {result['new_readiness']}")
    return True


# ══════════════════════════════════════════════════════════════════════════════════════
# Run All Tests
# ══════════════════════════════════════════════════════════════════════════════════════

def run_all_tests() -> int:
    tests = [
        ("readiness missing → partial", test_1_readiness_missing_to_partial),
        ("3 valid signals pass pipeline", test_2_three_valid_signals_pass_pipeline),
        ("2 invalid samples blocked", test_3_two_invalid_samples_blocked),
        ("public card no debug terms", test_4_public_card_no_debug_terms),
        ("fixture not live_ready", test_5_fixture_not_live_ready),
        ("mock_send_ready true, real_tg false", test_6_mock_send_ready_true_but_real_tg_false),
        ("fixed card matrix 5 types", test_7_fixed_card_matrix_still_5_types),
        ("price_oi_volume_anomaly still ready", test_8_price_oi_volume_anomaly_still_ready),
        ("liquidation_pressure → partial", test_9_liquidation_pressure_updated_to_partial),
        ("news_event still missing", test_10_news_event_still_missing),
        ("no network calls", test_11_no_network_calls),
        ("no token/API key", test_12_no_token_or_key),
        ("no TG send", test_13_no_tg_send),
        ("no daemon/loop/cron", test_14_no_daemon_or_loop),
        ("matrix summary function", test_15_matrix_summary_function),
        ("whale_position_alert partial", test_16_whale_position_alert_is_partial),
        ("multi_asset_market_sync partial", test_17_multi_asset_market_sync_is_partial),
        ("pressure types correct", test_18_pressure_types_correct),
        ("zero signals → missing", test_19_readiness_update_no_adapter_returns_missing),
        ("force_missing works", test_20_readiness_update_force_missing),
    ]

    print("=" * 60)
    print(f"Market Radar Liquidation Pipeline Integration {VERSION} — 测试套件")
    print("=" * 60)

    # Import VERSION from runner
    import importlib
    try:
        runner_mod = importlib.import_module("scripts.run_market_radar_v112c_liquidation_pipeline_integration")
        ver = getattr(runner_mod, "VERSION", VERSION)
    except Exception:
        ver = VERSION

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


# Allow both VERSION as module-level and the imported one
VERSION = "v1.12-C"

if __name__ == "__main__":
    raise SystemExit(run_all_tests())
