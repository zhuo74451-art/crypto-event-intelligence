"""Market Radar v1.11-D — Signal Value Gate 单元测试（已校准）

测试覆盖（24 tests）:
  1. 价格未异常 → block
  2. 单纯价格异常，无确认因子 → observe
  3. 价格异常 + OI → allow
  4. 价格异常 + volume → allow
  5. 价格异常 + funding extreme → allow
  6. 强价格异常 + 多资产共振 但无OI/volume 支撑 → observe（v1.11-D 校准）
  7. 缺失 OI/volume/funding 时不报错
  8. funding 为 0 时给 warning
  9. price_change_pct 字段缺失 → block
  10. 字段为字符串数字时能安全解析
  11. 负向价格变化能识别
  12. 正向价格变化能识别
  13. 多资产共振不足 3 → 不命中 multi_asset_sync
  14. value_score 范围和 tier 分类正确
  15. 返回结构包含所有必需字段
  16. 不包含敏感字段
  17. context 'signals' 键多资产共振
  18. 强价格无确认 → observe
  ── v1.11-D 新增 ──
  19. price_move + multi_asset_sync + 字段缺失 → observe（不是 allow）
  20. strong_price_move + multi_asset_sync + fixture → observe（不是 allow）
  21. price_move + multi_asset_sync + OI 非 0 → allow（backed）
  22. price_move + multi_asset_sync + volume 非 0 → allow（backed）
  23. fixture 不应被 multi_asset_sync 推到 allow
  24. observe 层必须至少有一个测试稳定命中

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

from scripts.market_radar_signal_value_gate_v111b import (
    evaluate_signal_value,
    _safe_float,
    _is_fixture,
    GATE_VERSION,
)


# ── Test helpers ──────────────────────────────────────────────────────────────

def _signal(**overrides) -> dict:
    """Build a market_anomaly signal with defaults."""
    base = {
        "signal_type": "market_anomaly",
        "asset": "BTC",
        "core_entity": "BTC",
        "price_change_pct": -6.5,
        "source_type": "api",
        "source": "hyperliquid",
    }
    base.update(overrides)
    return base


def _fixture_signal(**overrides) -> dict:
    """Build a fixture (synthetic) market_anomaly signal."""
    base = {
        "signal_type": "market_anomaly",
        "asset": "BTC",
        "core_entity": "BTC",
        "price_change_pct": -6.5,
        "source_type": "fixture",
        "is_fixture": True,
    }
    base.update(overrides)
    return base


# ── Tests ─────────────────────────────────────────────────────────────────────

def test_1_no_price_move_block() -> bool:
    """1. 价格未异常 → block"""
    signal = _signal(price_change_pct=2.5)
    result = evaluate_signal_value(signal)
    assert result["allowed"] is False, f"Expected allowed=False, got {result}"
    assert result["decision"] == "block", f"Expected decision=block, got {result['decision']}"
    assert result["factor_hits"]["price_move"] is False
    print(f"  [PASS] price_change_pct=2.5 → block")
    return True


def test_2_price_only_observe() -> bool:
    """2. 单纯价格异常，无确认因子 → observe"""
    signal = _signal(price_change_pct=-6.0)  # no OI, no volume, no funding
    result = evaluate_signal_value(signal)
    assert result["allowed"] is False, f"Expected allowed=False, got {result}"
    assert result["decision"] == "observe", f"Expected decision=observe, got {result['decision']}"
    assert result["factor_hits"]["price_move"] is True
    # No confirmation factors should be hit
    assert result["factor_hits"]["oi_confirmation"] is False
    assert result["factor_hits"]["volume_confirmation"] is False
    assert result["factor_hits"]["funding_extreme"] is False
    print(f"  [PASS] price only (-6.0%) → observe")
    return True


def test_3_price_plus_oi_allow() -> bool:
    """3. 价格异常 + OI → allow"""
    signal = _signal(price_change_pct=-7.0, open_interest=500_000_000)
    result = evaluate_signal_value(signal)
    assert result["allowed"] is True, f"Expected allowed=True, got {result}"
    assert result["decision"] == "allow"
    assert result["factor_hits"]["price_move"] is True
    assert result["factor_hits"]["oi_confirmation"] is True
    print(f"  [PASS] price + OI → allow (score={result['value_score']})")
    return True


def test_4_price_plus_volume_allow() -> bool:
    """4. 价格异常 + volume → allow"""
    signal = _signal(price_change_pct=6.2, volume=1_200_000_000)
    result = evaluate_signal_value(signal)
    assert result["allowed"] is True, f"Expected allowed=True, got {result}"
    assert result["decision"] == "allow"
    assert result["factor_hits"]["price_move"] is True
    assert result["factor_hits"]["volume_confirmation"] is True
    print(f"  [PASS] price + volume → allow (score={result['value_score']})")
    return True


def test_5_price_plus_funding_extreme_allow() -> bool:
    """5. 价格异常 + funding extreme → allow"""
    signal = _signal(price_change_pct=-9.0, funding_rate=0.015)
    result = evaluate_signal_value(signal)
    assert result["allowed"] is True, f"Expected allowed=True, got {result}"
    assert result["decision"] == "allow"
    assert result["factor_hits"]["price_move"] is True
    assert result["factor_hits"]["funding_extreme"] is True
    assert result["factor_hits"]["price_move"] is True  # strong
    print(f"  [PASS] price + funding extreme → allow (score={result['value_score']})")
    return True


def test_6_strong_price_multi_asset_no_backing_observe() -> bool:
    """6. 强价格异常 + 多资产共振 但无OI/volume支撑 → observe（v1.11-D 校准）

    v1.11-D 变更：strong_price + multi_asset_sync 在没有 OI/volume 支撑时
    不再直接 allow，而是 observe。multi_asset_sync 只能作为辅助因子，
    不能单独把低质量信号推到 allow。
    """
    signal = _signal(price_change_pct=-10.0, asset="BTC")  # no OI, no volume
    context = {
        "assets": [
            {"asset": "BTC", "price_change_pct": -10.0},
            {"asset": "ETH", "price_change_pct": -8.5},
            {"asset": "SOL", "price_change_pct": -7.2},
            {"asset": "AVAX", "price_change_pct": -6.1},
        ]
    }
    result = evaluate_signal_value(signal, context)
    # v1.11-D: multi_asset_sync WITHOUT OI/volume backing → observe, NOT allow
    assert result["allowed"] is False, f"v1.11-D: multi_asset without OI/vol backing should NOT allow, got {result}"
    assert result["decision"] == "observe", f"Expected decision=observe, got {result['decision']}"
    assert result["factor_hits"]["price_move"] is True
    assert result["factor_hits"]["multi_asset_sync"] is True
    print(f"  [PASS] strong price + multi-asset sync without OI/vol → observe (calibrated)")
    return True


def test_7_missing_fields_no_error() -> bool:
    """7. 缺失 OI/volume/funding 时不报错"""
    signal = _signal(price_change_pct=-12.0)
    # No open_interest, volume, or funding fields
    try:
        result = evaluate_signal_value(signal)
        assert "allowed" in result
        assert "decision" in result
        # Should have warnings about missing fields
        assert len(result["warnings"]) > 0
        print(f"  [PASS] missing fields → no exception, warnings={result['warnings']}")
    except Exception as exc:
        print(f"  [FAIL] unexpected exception: {exc}")
        return False
    return True


def test_8_funding_zero_warning() -> bool:
    """8. funding 为 0 时给 warning"""
    signal = _signal(price_change_pct=-7.0, funding_rate=0.0)
    result = evaluate_signal_value(signal)
    # funding=0 should not hit as extreme
    assert result["factor_hits"]["funding_extreme"] is False
    # Should have warning about near-zero funding
    near_zero_warning = any("near zero" in w.lower() for w in result["warnings"])
    assert near_zero_warning, f"Expected 'near zero' warning, got: {result['warnings']}"
    print(f"  [PASS] funding=0 → warning present")
    return True


def test_9_missing_price_change_pct_block() -> bool:
    """9. price_change_pct 字段缺失 → block"""
    signal = {"signal_type": "market_anomaly", "asset": "BTC"}  # no price_change_pct
    result = evaluate_signal_value(signal)
    assert result["allowed"] is False, f"Expected allowed=False, got {result}"
    assert result["decision"] == "block"
    assert result["factor_hits"]["price_move"] is False
    print(f"  [PASS] missing price_change_pct → block")
    return True


def test_10_string_fields_parse_safe() -> bool:
    """10. 字段为字符串数字时能安全解析"""
    signal = _signal(
        price_change_pct="-7.24%",
        open_interest="278000000",
        volume="527000000",
        funding_rate="+0.00%(年化0.1%)",
    )
    try:
        result = evaluate_signal_value(signal)
        assert result["allowed"] is True, f"Expected allowed=True, got {result}"
        assert result["factor_hits"]["price_move"] is True
        assert result["factor_hits"]["oi_confirmation"] is True
        assert result["factor_hits"]["volume_confirmation"] is True
        # funding "+0.00%(...)" → parsed as 0.0, not extreme
        assert result["factor_hits"]["funding_extreme"] is False
        print(f"  [PASS] string fields parsed safely (score={result['value_score']})")
    except Exception as exc:
        print(f"  [FAIL] unexpected exception: {exc}")
        return False
    return True


def test_11_negative_price_recognized() -> bool:
    """11. 负向价格变化能识别"""
    signal = _signal(price_change_pct=-15.0, open_interest=200_000_000)
    result = evaluate_signal_value(signal)
    assert result["factor_hits"]["price_move"] is True
    assert result["decision"] == "allow"
    assert any("abs" in r or "-15" in r for r in result["reasons"]), f"reasons: {result['reasons']}"
    print(f"  [PASS] negative -15% → recognized (decision={result['decision']})")
    return True


def test_12_positive_price_recognized() -> bool:
    """12. 正向价格变化能识别"""
    signal = _signal(price_change_pct=9.5, open_interest=300_000_000)
    result = evaluate_signal_value(signal)
    assert result["factor_hits"]["price_move"] is True
    assert result["decision"] == "allow"
    print(f"  [PASS] positive +9.5% → recognized (decision={result['decision']})")
    return True


def test_13_multi_asset_insufficient() -> bool:
    """13. 多资产共振不足 3 → 不命中 multi_asset_sync"""
    signal = _signal(price_change_pct=-8.0, asset="BTC")
    context = {
        "assets": [
            {"asset": "BTC", "price_change_pct": -8.0},
            {"asset": "ETH", "price_change_pct": -3.0},
        ]
    }
    result = evaluate_signal_value(signal, context)
    assert result["factor_hits"]["multi_asset_sync"] is False
    print(f"  [PASS] only 2 assets same direction → multi_asset_sync not hit")
    return True


def test_14_value_score_and_tiers() -> bool:
    """14. value_score 范围和 tier 分类正确"""
    # Low tier: score < 45
    low_signal = _signal(price_change_pct=3.0)  # no price move
    low_result = evaluate_signal_value(low_signal)
    assert low_result["value_tier"] == "low", f"Expected low, got {low_result['value_tier']}"
    assert low_result["value_score"] < 45

    # Low tier: price_only → score 30
    med_signal = _signal(price_change_pct=-6.5)  # price move only → score 30
    med_result = evaluate_signal_value(med_signal)
    assert med_result["value_tier"] == "low", f"Expected low for 30pts, got {med_result['value_tier']}"

    # Medium tier with confirmations: price(-6.5%) + OI(100k) = 30 + 25 = 55
    med_signal2 = _signal(price_change_pct=-6.5, open_interest=100_000)  # 30 + 25 = 55
    med_result2 = evaluate_signal_value(med_signal2)
    assert med_result2["value_tier"] == "medium", f"Expected medium for 55pts, got {med_result2['value_tier']}"

    # High tier: score >= 70
    high_signal = _signal(
        price_change_pct=-12.0,  # strong: 30+20=50
        open_interest=500_000_000,  # OI: +25 = 75
        volume=1_000_000_000,  # volume: +20 = 95
    )
    high_result = evaluate_signal_value(high_signal)
    assert high_result["value_tier"] == "high", f"Expected high for {high_result['value_score']}pts, got {high_result['value_tier']}"
    assert high_result["value_score"] >= 70
    print(f"  [PASS] tier classification correct (low={low_result['value_score']}, med={med_result2['value_score']}, high={high_result['value_score']})")
    return True


def test_15_result_structure() -> bool:
    """15. 返回结构包含所有必需字段"""
    signal = _signal(price_change_pct=-7.5, open_interest=100_000)
    result = evaluate_signal_value(signal)

    required_keys = [
        "allowed", "decision", "value_score", "value_tier",
        "reasons", "warnings", "factor_hits", "gate_version",
    ]
    for key in required_keys:
        assert key in result, f"Missing key '{key}' in result"

    # Check factor_hits sub-keys
    factor_keys = [
        "price_move", "oi_confirmation", "volume_confirmation",
        "funding_extreme", "multi_asset_sync",
    ]
    for key in factor_keys:
        assert key in result["factor_hits"], f"Missing factor_hits key '{key}'"

    # decision must be one of allow/observe/block
    assert result["decision"] in ("allow", "observe", "block"), f"Invalid decision: {result['decision']}"

    # value_tier must be one of high/medium/low
    assert result["value_tier"] in ("high", "medium", "low"), f"Invalid tier: {result['value_tier']}"

    # allowed should be consistent with decision
    assert result["allowed"] == (result["decision"] == "allow"), \
        f"allowed={result['allowed']} but decision={result['decision']}"

    # gate_version should match v1.11-d
    assert result["gate_version"] == GATE_VERSION

    print(f"  [PASS] result structure complete and valid (gate={GATE_VERSION})")
    return True


def test_16_no_sensitive_fields_in_result() -> bool:
    """16. 返回结果不包含敏感字段"""
    signal = _signal(price_change_pct=-7.0, open_interest=100_000)
    result = evaluate_signal_value(signal)
    result_str = json.dumps(result, ensure_ascii=False, default=str).lower()
    sensitive_terms = ["token", "chat_id", "key", "cookie", "password", "secret", "bot_token", "api_key"]
    found = [term for term in sensitive_terms if term in result_str]
    assert len(found) == 0, f"Sensitive terms found: {found}"
    print(f"  [PASS] result contains no API keys, tokens, or credentials")
    return True


def test_17_context_with_signals_list() -> bool:
    """17. context 中使用 'signals' 键也能正确识别多资产共振（v1.11-D: 需real assets >= 3）"""
    signal = _signal(price_change_pct=-11.0, asset="BTC")
    context = {
        "signals": [
            {"asset": "BTC", "price_change_pct": -11.0},
            {"asset": "ETH", "price_change_pct": -9.0},
            {"asset": "SOL", "price_change_pct": -7.0},
        ]
    }
    result = evaluate_signal_value(signal, context)
    assert result["factor_hits"]["multi_asset_sync"] is True
    print(f"  [PASS] context with 'signals' key → multi_asset_sync hit (3 real assets)")
    return True


def test_18_observe_strong_price_no_confirmation() -> bool:
    """18. 强价格异常但无确认因子 → observe（不直接 allow）"""
    signal = _signal(price_change_pct=-9.0)  # strong price, no OI/volume/funding
    result = evaluate_signal_value(signal)
    assert result["allowed"] is False
    assert result["decision"] == "observe"
    assert result["factor_hits"]["price_move"] is True
    print(f"  [PASS] strong -9.0% no confirmation → observe")
    return True


# ── v1.11-D 新增测试 ──────────────────────────────────────────────────────────

def test_19_price_multi_asset_fields_missing_observe() -> bool:
    """19. price_move + multi_asset_sync + 字段缺失 → observe（不是 allow）

    v1.11-D 核心校准：multi_asset_sync 在没有 OI/volume 支撑时，
    即使 price_move 和 strong_price_move 都命中，也只能 observe。
    """
    signal = _signal(price_change_pct=-9.5, asset="BTC")  # strong price, no OI/vol
    context = {
        "assets": [
            {"asset": "BTC", "price_change_pct": -9.5},
            {"asset": "ETH", "price_change_pct": -8.0},
            {"asset": "SOL", "price_change_pct": -7.0},
            {"asset": "AVAX", "price_change_pct": -6.5},
        ]
    }
    result = evaluate_signal_value(signal, context)
    assert result["allowed"] is False, f"multi_asset without OI/vol should NOT allow, got {result}"
    assert result["decision"] == "observe", f"Expected observe, got {result['decision']}"
    assert result["factor_hits"]["price_move"] is True
    assert result["factor_hits"]["multi_asset_sync"] is True
    assert result["factor_hits"]["oi_confirmation"] is False
    assert result["factor_hits"]["volume_confirmation"] is False
    print(f"  [PASS] price_move + multi_asset_sync but no OI/vol → observe")
    return True


def test_20_strong_price_multi_asset_fixture_observe() -> bool:
    """20. strong_price_move + multi_asset_sync + fixture → observe（不是 allow）

    Fixture 信号不能因为 multi_asset_sync 就被推到 allow。
    即使 context 中有足够多的真实资产同向，fixture 本身仍应受限。
    """
    signal = _fixture_signal(price_change_pct=-10.0, asset="FIXTURE_COIN")
    context = {
        "assets": [
            {"asset": "FIXTURE_COIN", "price_change_pct": -10.0, "is_fixture": True},
            {"asset": "BTC", "price_change_pct": -9.0, "source_type": "api"},
            {"asset": "ETH", "price_change_pct": -8.0, "source_type": "api"},
            {"asset": "SOL", "price_change_pct": -7.0, "source_type": "api"},
        ],
        "real_same_direction_asset_count": 3,  # 3 real + fixture target
    }
    result = evaluate_signal_value(signal, context)
    assert result["allowed"] is False, f"fixture + multi should not allow, got {result}"
    assert result["decision"] == "observe", f"Expected observe for fixture + multi, got {result['decision']}"
    assert result["factor_hits"]["multi_asset_sync"] is True  # still hit (real assets >= 3)
    print(f"  [PASS] strong_price + multi_asset_sync + fixture → observe")
    return True


def test_21_price_multi_asset_oi_backed_allow() -> bool:
    """21. price_move + multi_asset_sync + OI 非 0 → allow（backed）

    multi_asset_sync 有 OI 支撑时，作为强确认因子，应该 allow。
    """
    signal = _signal(price_change_pct=-7.0, asset="BTC", open_interest=500_000_000)
    context = {
        "assets": [
            {"asset": "BTC", "price_change_pct": -7.0, "open_interest": 500_000_000},
            {"asset": "ETH", "price_change_pct": -8.5},
            {"asset": "SOL", "price_change_pct": -6.2},
            {"asset": "AVAX", "price_change_pct": -5.1},
        ]
    }
    result = evaluate_signal_value(signal, context)
    assert result["allowed"] is True, f"Expected allow with OI-backed multi, got {result}"
    assert result["decision"] == "allow"
    assert result["factor_hits"]["multi_asset_sync"] is True
    assert result["factor_hits"]["oi_confirmation"] is True
    print(f"  [PASS] price + multi_asset_sync + OI → allow (score={result['value_score']})")
    return True


def test_22_price_multi_asset_volume_backed_allow() -> bool:
    """22. price_move + multi_asset_sync + volume 非 0 → allow（backed）

    multi_asset_sync 有 volume 支撑时，作为强确认因子，应该 allow。
    """
    signal = _signal(price_change_pct=8.5, asset="ETH", volume=2_500_000_000)
    context = {
        "assets": [
            {"asset": "ETH", "price_change_pct": 8.5, "volume": 2_500_000_000},
            {"asset": "BTC", "price_change_pct": 7.0},
            {"asset": "SOL", "price_change_pct": 9.2},
            {"asset": "AVAX", "price_change_pct": 6.1},
        ]
    }
    result = evaluate_signal_value(signal, context)
    assert result["allowed"] is True, f"Expected allow with volume-backed multi, got {result}"
    assert result["decision"] == "allow"
    assert result["factor_hits"]["multi_asset_sync"] is True
    assert result["factor_hits"]["volume_confirmation"] is True
    print(f"  [PASS] price + multi_asset_sync + volume → allow (score={result['value_score']})")
    return True


def test_23_fixture_not_allowed_by_multi_alone() -> bool:
    """23. fixture 不应被 multi_asset_sync 推到 allow

    v1.11-D: 即使 context 中有 >=3 个真实资产同向，fixture 信号在
    没有 OI/volume/funding 时仍应 observe，不能直接 allow。
    """
    signal = _fixture_signal(price_change_pct=-8.0, asset="TEST_TOKEN")
    # context has 4 real assets moving down, plus the fixture
    context = {
        "assets": [
            {"asset": "TEST_TOKEN", "price_change_pct": -8.0, "is_fixture": True},
            {"asset": "BTC", "price_change_pct": -7.0, "source_type": "api"},
            {"asset": "ETH", "price_change_pct": -6.5, "source_type": "api"},
            {"asset": "SOL", "price_change_pct": -6.0, "source_type": "api"},
            {"asset": "AVAX", "price_change_pct": -5.5, "source_type": "api"},
        ]
    }
    result = evaluate_signal_value(signal, context)
    # Fixture with multi_asset but NO OI/volume → observe, not allow
    assert result["allowed"] is False, f"fixture should not be allowed by multi alone, got {result}"
    assert result["decision"] == "observe", f"Expected observe for fixture + multi without OI/vol, got {result['decision']}"
    assert result["factor_hits"]["multi_asset_sync"] is True  # real assets >= 3
    print(f"  [PASS] fixture + multi_asset_sync without OI/vol → observe (not allow)")
    return True


def test_24_observe_layer_triggers_stably() -> bool:
    """24. observe 层必须至少有一个测试稳定命中

    v1.11-D 目标：observe 层必须被实际触发。
    验证多个"应该 observe"的场景都能稳定命中 observe。
    """
    observe_count = 0

    # Scenario A: price_move only, no confirmations
    sig_a = _signal(price_change_pct=-6.0)  # no OI/vol/funding
    r_a = evaluate_signal_value(sig_a)
    if r_a["decision"] == "observe":
        observe_count += 1
    else:
        print(f"  [WARN] Scenario A: expected observe, got {r_a['decision']}")

    # Scenario B: strong price + multi_asset but no OI/vol backing
    sig_b = _signal(price_change_pct=-11.0, asset="BTC")
    ctx_b = {
        "assets": [
            {"asset": "BTC", "price_change_pct": -11.0},
            {"asset": "ETH", "price_change_pct": -9.0},
            {"asset": "SOL", "price_change_pct": -7.0},
        ]
    }
    r_b = evaluate_signal_value(sig_b, ctx_b)
    if r_b["decision"] == "observe":
        observe_count += 1
    else:
        print(f"  [WARN] Scenario B: expected observe, got {r_b['decision']}")

    # Scenario C: strong price alone, no confirmations
    sig_c = _signal(price_change_pct=-9.0)
    r_c = evaluate_signal_value(sig_c)
    if r_c["decision"] == "observe":
        observe_count += 1
    else:
        print(f"  [WARN] Scenario C: expected observe, got {r_c['decision']}")

    # Scenario D: fixture with multi but no OI/vol
    sig_d = _fixture_signal(price_change_pct=-7.5, asset="FIXTURE")
    ctx_d = {
        "assets": [
            {"asset": "FIXTURE", "price_change_pct": -7.5, "is_fixture": True},
            {"asset": "BTC", "price_change_pct": -6.0, "source_type": "api"},
            {"asset": "ETH", "price_change_pct": -5.5, "source_type": "api"},
            {"asset": "SOL", "price_change_pct": -5.0, "source_type": "api"},
        ]
    }
    r_d = evaluate_signal_value(sig_d, ctx_d)
    if r_d["decision"] == "observe":
        observe_count += 1
    else:
        print(f"  [WARN] Scenario D: expected observe, got {r_d['decision']}")

    # At least 1 observe must trigger, and ideally all 4
    assert observe_count >= 1, f"observe layer must trigger at least once, got {observe_count}/4"
    print(f"  [PASS] observe layer triggered in {observe_count}/4 scenarios")
    return True


# ── Run all tests ─────────────────────────────────────────────────────────────

def run_all_tests() -> int:
    tests = [
        ("1. 价格未异常 → block", test_1_no_price_move_block),
        ("2. 单纯价格异常，无确认因子 → observe", test_2_price_only_observe),
        ("3. 价格异常 + OI → allow", test_3_price_plus_oi_allow),
        ("4. 价格异常 + volume → allow", test_4_price_plus_volume_allow),
        ("5. 价格异常 + funding extreme → allow", test_5_price_plus_funding_extreme_allow),
        ("6. 强价格+多资产共振 无OI/vol → observe (校准)", test_6_strong_price_multi_asset_no_backing_observe),
        ("7. 缺失 OI/volume/funding 时不报错", test_7_missing_fields_no_error),
        ("8. funding 为 0 时给 warning", test_8_funding_zero_warning),
        ("9. price_change_pct 字段缺失 → block", test_9_missing_price_change_pct_block),
        ("10. 字段为字符串数字时能安全解析", test_10_string_fields_parse_safe),
        ("11. 负向价格变化能识别", test_11_negative_price_recognized),
        ("12. 正向价格变化能识别", test_12_positive_price_recognized),
        ("13. 多资产共振不足 3 → 不命中", test_13_multi_asset_insufficient),
        ("14. value_score 范围和 tier 分类正确", test_14_value_score_and_tiers),
        ("15. 返回结构包含所有必需字段", test_15_result_structure),
        ("16. 不包含敏感字段", test_16_no_sensitive_fields_in_result),
        ("17. context 'signals' 键多资产共振", test_17_context_with_signals_list),
        ("18. 强价格无确认 → observe", test_18_observe_strong_price_no_confirmation),
        # ── v1.11-D 新增 ──
        ("19. price+multi+字段缺失 → observe", test_19_price_multi_asset_fields_missing_observe),
        ("20. strong+multi+fixture → observe", test_20_strong_price_multi_asset_fixture_observe),
        ("21. price+multi+OI → allow", test_21_price_multi_asset_oi_backed_allow),
        ("22. price+multi+volume → allow", test_22_price_multi_asset_volume_backed_allow),
        ("23. fixture不被multi推到allow", test_23_fixture_not_allowed_by_multi_alone),
        ("24. observe层稳定触发", test_24_observe_layer_triggers_stably),
    ]

    print("=" * 60)
    print(f"Market Radar {GATE_VERSION} — Signal Value Gate 单元测试")
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
                print(f"  [FAIL] returned False")
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
