"""Market Radar v1.11-F — Same-Asset Cooldown Gate 单元测试

测试覆盖（18 tests）:
  1. 首次出现 → allow
  2. 同资产在冷却窗口内、分数相同 → cooldown_suppress
  3. 同资产在冷却窗口内、分数显著提升 → upgrade_override
  4. 冷却窗口过期 → allow
  5. 不同资产独立追踪 — 各自 allow
  6. 无 signal_value_result → allow（保守策略）
  7. 多资产交错 → 各自独立状态
  8. 分数小幅提升（未达阈值） → cooldown_suppress
  9. 冷却窗口恰好边界
  10. 空 cooldown_state → 创建新状态
  11. 返回结构包含所有必需字段
  12. 不包含敏感字段
  13. CooldownState 状态管理
  14. evaluate_cooldown_batch 顺序处理
  15. 信号被 block → 不进入冷却状态
  16. 无法提取 asset → allow（无资产可追踪）
  17. upgrade_override 精确在阈值上
  18. 连续多次 suppress → occurrence_count 递增

Security:
    - Does NOT read, print, or save any token / chat_id / key / cookie / password.
    - Does NOT access environment variables for credentials.
    - Does NOT make network calls.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.market_radar_same_asset_cooldown_gate_v111f import (
    evaluate_cooldown,
    evaluate_cooldown_batch,
    CooldownState,
    _extract_asset,
    _now_iso,
    COOLDOWN_GATE_VERSION,
    DEFAULT_COOLDOWN_WINDOW_MINUTES,
    DEFAULT_UPGRADE_OVERRIDE_SCORE_DELTA,
)

CN_TZ = timezone(timedelta(hours=8))


# ── Test helpers ────────────────────────────────────────────────────────────────

def _signal(**overrides) -> dict:
    """Build a signal dict with defaults."""
    base = {
        "signal_type": "market_anomaly",
        "asset": "BTC",
        "core_entity": "BTC",
        "price_change_pct": -6.5,
        "source_type": "api",
    }
    base.update(overrides)
    return base


def _value_result(**overrides) -> dict:
    """Build a SignalValueGate result dict with defaults."""
    base = {
        "allowed": True,
        "decision": "allow",
        "value_score": 75,
        "value_tier": "high",
        "reasons": ["price_move: abs(-6.50%) >= 5%", "oi_confirmation: open_interest=500.0"],
        "warnings": [],
        "factor_hits": {
            "price_move": True,
            "oi_confirmation": True,
            "volume_confirmation": False,
            "funding_extreme": False,
            "multi_asset_sync": False,
        },
        "gate_version": "v1.11-d",
    }
    base.update(overrides)
    return base


def _dt(minutes_offset: int = 0) -> str:
    """Build an ISO 8601 timestamp offset from now by given minutes."""
    dt = datetime.now(CN_TZ) + timedelta(minutes=minutes_offset)
    return dt.isoformat()


def _fresh_state() -> CooldownState:
    """Create a fresh empty CooldownState."""
    return CooldownState()


# ── Tests ───────────────────────────────────────────────────────────────────────

def test_1_first_occurrence_allow() -> bool:
    """1. 首次出现 → allow"""
    signal = _signal(asset="BTC")
    vr = _value_result(value_score=75)
    state = _fresh_state()

    result = evaluate_cooldown(signal, vr, state, current_time=_dt())

    assert result["allowed"] is True, f"Expected allowed=True, got {result}"
    assert result["decision"] == "allow", f"Expected allow, got {result['decision']}"
    assert result["asset"] == "BTC"
    assert result["occurrence_count"] == 1
    assert result["previous_value_score"] is None
    assert "First occurrence" in result["cooldown_reason"]

    # Verify state was updated
    updated = result["cooldown_state"]
    assert "BTC" in updated
    assert updated["BTC"]["occurrence_count"] == 1
    assert updated["BTC"]["last_value_score"] == 75
    assert updated["BTC"]["last_decision"] == "allow"

    print(f"  [PASS] BTC first occurrence → allow, state updated (count=1)")
    return True


def test_2_same_asset_within_window_suppress() -> bool:
    """2. 同资产在冷却窗口内、分数相同 → cooldown_suppress"""
    signal1 = _signal(asset="ARB")
    vr1 = _value_result(value_score=60)
    signal2 = _signal(asset="ARB")
    vr2 = _value_result(value_score=60)  # same score

    state = _fresh_state()
    base = _dt()

    # First: allow
    r1 = evaluate_cooldown(signal1, vr1, state, current_time=base)
    state.apply(r1["cooldown_state"])
    assert r1["allowed"] is True
    assert r1["decision"] == "allow"

    # Second: 5 min later, same score → suppress
    t2 = (datetime.fromisoformat(base) + timedelta(minutes=5)).isoformat()
    r2 = evaluate_cooldown(signal2, vr2, state, current_time=t2)

    assert r2["allowed"] is False, f"Expected allowed=False, got {r2}"
    assert r2["decision"] == "cooldown_suppress", f"Expected cooldown_suppress, got {r2['decision']}"
    assert r2["asset"] == "ARB"
    assert r2["minutes_since_last"] is not None
    assert r2["minutes_since_last"] <= 5.5  # ~5 min
    assert "Suppressing repeat" in r2["cooldown_reason"]

    print(f"  [PASS] ARB repeat within 5 min window → cooldown_suppress")
    return True


def test_3_upgrade_override() -> bool:
    """3. 同资产在冷却窗口内、分数显著提升 → upgrade_override"""
    signal1 = _signal(asset="ETH")
    vr1 = _value_result(value_score=45)
    signal2 = _signal(asset="ETH")
    vr2 = _value_result(value_score=65)  # Δ+20 >= 15

    state = _fresh_state()
    base = _dt()

    # First: allow
    r1 = evaluate_cooldown(signal1, vr1, state, current_time=base)
    state.apply(r1["cooldown_state"])
    assert r1["allowed"] is True

    # Second: 3 min later, significantly better score → upgrade_override
    t2 = (datetime.fromisoformat(base) + timedelta(minutes=3)).isoformat()
    r2 = evaluate_cooldown(signal2, vr2, state, current_time=t2)

    assert r2["allowed"] is True, f"Expected allowed=True for upgrade, got {r2}"
    assert r2["decision"] == "upgrade_override", f"Expected upgrade_override, got {r2['decision']}"
    assert r2["value_score"] == 65
    assert r2["previous_value_score"] == 45
    assert "Upgrade override" in r2["cooldown_reason"]
    assert "Δ+20" in r2["cooldown_reason"] or "+20" in r2["cooldown_reason"]

    print(f"  [PASS] ETH score 45→65 (Δ+20) within 3 min → upgrade_override")
    return True


def test_4_cooldown_window_expired_allow() -> bool:
    """4. 冷却窗口过期 → allow"""
    signal1 = _signal(asset="SOL")
    vr1 = _value_result(value_score=70)
    signal2 = _signal(asset="SOL")
    vr2 = _value_result(value_score=55)  # worse score, but window expired

    state = _fresh_state()
    base = _dt()

    # First: allow
    r1 = evaluate_cooldown(signal1, vr1, state, current_time=base)
    state.apply(r1["cooldown_state"])
    assert r1["allowed"] is True

    # Second: 15 min later (beyond 10 min window) → allow
    t2 = (datetime.fromisoformat(base) + timedelta(minutes=15)).isoformat()
    r2 = evaluate_cooldown(signal2, vr2, state, current_time=t2)

    assert r2["allowed"] is True, f"Expected allowed=True (window expired), got {r2}"
    assert r2["decision"] == "allow", f"Expected allow, got {r2['decision']}"
    assert "Cooldown window expired" in r2["cooldown_reason"]
    assert r2["minutes_since_last"] is not None
    assert r2["minutes_since_last"] >= 14  # ~15 min

    print(f"  [PASS] SOL 15 min later (window=10) → allow (window expired)")
    return True


def test_5_different_assets_independent() -> bool:
    """5. 不同资产独立追踪 — 各自 allow"""
    state = _fresh_state()
    base = _dt()

    # BTC first
    r_btc = evaluate_cooldown(
        _signal(asset="BTC"), _value_result(value_score=80), state, current_time=base
    )
    state.apply(r_btc["cooldown_state"])
    assert r_btc["allowed"] is True
    assert r_btc["decision"] == "allow"

    # ETH 1 min later — different asset, should also allow
    t2 = (datetime.fromisoformat(base) + timedelta(minutes=1)).isoformat()
    r_eth = evaluate_cooldown(
        _signal(asset="ETH"), _value_result(value_score=65), state, current_time=t2
    )
    assert r_eth["allowed"] is True, f"ETH (different asset) should allow, got {r_eth}"
    assert r_eth["decision"] == "allow"
    assert r_eth["occurrence_count"] == 1  # first for ETH

    # BTC again 2 min later → should suppress
    t3 = (datetime.fromisoformat(base) + timedelta(minutes=2)).isoformat()
    r_btc2 = evaluate_cooldown(
        _signal(asset="BTC"), _value_result(value_score=80), state, current_time=t3
    )
    assert r_btc2["allowed"] is False, f"BTC repeat should suppress, got {r_btc2}"
    assert r_btc2["decision"] == "cooldown_suppress"

    # Verify state tracks both independently
    updated = r_btc2["cooldown_state"]
    assert "BTC" in updated
    assert "ETH" in updated
    assert updated["BTC"]["occurrence_count"] >= 1
    assert updated["ETH"]["occurrence_count"] == 1

    print(f"  [PASS] BTC, ETH, BTC → independent per-asset tracking works")
    return True


def test_6_no_value_result_conservative_allow() -> bool:
    """6. 无 signal_value_result → allow（保守策略）

    Without value context, the cooldown gate cannot judge signal quality.
    Conservative: allow it through (don't silently drop signals).
    """
    signal = _signal(asset="BTC")
    state = _fresh_state()

    result = evaluate_cooldown(signal, None, state, current_time=_dt())

    assert result["allowed"] is True, f"Should allow without value result (conservative), got {result}"
    assert result["decision"] == "allow"
    assert result["value_score"] == 0

    print(f"  [PASS] No value_result → allow (conservative fallback)")
    return True


def test_7_interleaved_multi_asset() -> bool:
    """7. 多资产交错 → 各自独立状态"""
    state = _fresh_state()
    base = _dt()

    assets_sequence = ["BTC", "ETH", "BTC", "SOL", "ETH", "BTC"]
    expected_decisions = ["allow", "allow", "cooldown_suppress", "allow", "cooldown_suppress", "cooldown_suppress"]

    decisions: list[str] = []
    for i, asset in enumerate(assets_sequence):
        t = (datetime.fromisoformat(base) + timedelta(minutes=i)).isoformat()
        result = evaluate_cooldown(
            _signal(asset=asset), _value_result(value_score=70), state, current_time=t
        )
        decisions.append(result["decision"])
        state.apply(result["cooldown_state"])

    assert decisions == expected_decisions, \
        f"Expected {expected_decisions}, got {decisions}"

    # Verify state has all 3 unique assets
    updated = result["cooldown_state"]
    assert set(updated.keys()) == {"BTC", "ETH", "SOL"}

    # BTC should have highest occurrence_count
    assert updated["BTC"]["occurrence_count"] >= 2
    assert updated["SOL"]["occurrence_count"] == 1

    print(f"  [PASS] Interleaved {assets_sequence} → decisions={decisions}")
    return True


def test_8_small_score_increase_no_override() -> bool:
    """8. 分数小幅提升（未达阈值） → cooldown_suppress"""
    signal1 = _signal(asset="ARB")
    vr1 = _value_result(value_score=60)
    signal2 = _signal(asset="ARB")
    vr2 = _value_result(value_score=70)  # Δ+10 < 15

    state = _fresh_state()
    base = _dt()

    r1 = evaluate_cooldown(signal1, vr1, state, current_time=base)
    state.apply(r1["cooldown_state"])

    t2 = (datetime.fromisoformat(base) + timedelta(minutes=3)).isoformat()
    r2 = evaluate_cooldown(signal2, vr2, state, current_time=t2)

    assert r2["allowed"] is False, f"Δ+10 < 15 should NOT trigger upgrade, got {r2}"
    assert r2["decision"] == "cooldown_suppress", f"Expected cooldown_suppress, got {r2['decision']}"
    assert "Δ+10" in r2["cooldown_reason"] or "+10" in r2["cooldown_reason"]

    print(f"  [PASS] ARB score 60→70 (Δ+10 < 15) → still cooldown_suppress")
    return True


def test_9_window_exact_boundary() -> bool:
    """9. 冷却窗口恰好边界"""
    signal1 = _signal(asset="SUI")
    vr1 = _value_result(value_score=55)
    signal2 = _signal(asset="SUI")
    vr2 = _value_result(value_score=55)

    state = _fresh_state()
    base = _dt()

    r1 = evaluate_cooldown(signal1, vr1, state, current_time=base)
    state.apply(r1["cooldown_state"])

    # Exactly at 10 minutes (equal to window) — should not have expired
    t2 = (datetime.fromisoformat(base) + timedelta(minutes=10)).isoformat()
    r2 = evaluate_cooldown(signal2, vr2, state, current_time=t2)

    # At exactly 10.0 min, the delta is exactly the window
    # Implementation uses > (strictly greater than), so 10.0 min is NOT expired
    assert r2["decision"] == "cooldown_suppress", \
        f"At exactly 10 min, should suppress (delta <= window), got {r2['decision']}"

    # At just over 10 minutes → should expire
    t3 = (datetime.fromisoformat(base) + timedelta(minutes=10, seconds=1)).isoformat()
    r3 = evaluate_cooldown(signal2, vr2, state, current_time=t3)

    assert r3["allowed"] is True, f"At 10min 1s, window should be expired, got {r3}"
    assert r3["decision"] == "allow"

    print(f"  [PASS] 10 min exactly → suppress; 10 min 1 sec → allow")
    return True


def test_10_empty_state_create_new() -> bool:
    """10. 空 cooldown_state → 创建新状态"""
    signal = _signal(asset="BTC")
    vr = _value_result(value_score=80)

    # None state
    r1 = evaluate_cooldown(signal, vr, None, current_time=_dt())
    assert r1["allowed"] is True
    assert isinstance(r1["cooldown_state"], dict)
    assert "BTC" in r1["cooldown_state"]

    # Empty dict state
    r2 = evaluate_cooldown(signal, vr, {}, current_time=_dt())
    assert r2["allowed"] is True
    assert "BTC" in r2["cooldown_state"]

    print(f"  [PASS] None and empty dict → new state created correctly")
    return True


def test_11_result_structure() -> bool:
    """11. 返回结构包含所有必需字段"""
    signal = _signal(asset="BTC")
    vr = _value_result(value_score=75)
    state = _fresh_state()

    result = evaluate_cooldown(signal, vr, state, current_time=_dt())

    required_keys = [
        "allowed", "decision", "cooldown_reason", "cooldown_state",
        "asset", "value_score", "previous_value_score",
        "minutes_since_last", "occurrence_count",
        "cooldown_config", "gate_version",
    ]
    for key in required_keys:
        assert key in result, f"Missing key '{key}' in result"

    # decision must be one of the valid values
    assert result["decision"] in ("allow", "cooldown_suppress", "upgrade_override"), \
        f"Invalid decision: {result['decision']}"

    # allowed must be consistent with decision
    if result["decision"] == "cooldown_suppress":
        assert result["allowed"] is False
    else:
        assert result["allowed"] is True

    # gate_version must match
    assert result["gate_version"] == COOLDOWN_GATE_VERSION

    # cooldown_config must have expected keys
    assert "cooldown_window_minutes" in result["cooldown_config"]
    assert "upgrade_override_score_delta" in result["cooldown_config"]

    print(f"  [PASS] Result structure complete and valid")
    return True


def test_12_no_sensitive_fields() -> bool:
    """12. 返回结果不包含敏感字段"""
    signal = _signal(asset="BTC")
    vr = _value_result(value_score=75)
    state = _fresh_state()

    result = evaluate_cooldown(signal, vr, state, current_time=_dt())
    result_str = json.dumps(result, ensure_ascii=False, default=str).lower()
    sensitive_terms = ["token", "chat_id", "key", "cookie", "password", "secret", "bot_token", "api_key"]
    found = [term for term in sensitive_terms if term in result_str]
    assert len(found) == 0, f"Sensitive terms found: {found}"

    print(f"  [PASS] Result contains no API keys, tokens, or credentials")
    return True


def test_13_cooldown_state_management() -> bool:
    """13. CooldownState 状态管理"""
    state = CooldownState()

    # Empty initially
    assert state.is_empty() is True
    assert len(state) == 0

    # Record
    state.record("BTC", 75, "allow")
    assert not state.is_empty()
    assert len(state) == 1
    assert state.get("BTC") is not None
    assert state.get("BTC")["occurrence_count"] == 1
    assert state.get("ETH") is None

    # Record again
    state.record("BTC", 80, "upgrade_override")
    assert state.get("BTC")["occurrence_count"] == 2
    assert state.get("BTC")["last_value_score"] == 80

    # Record suppression
    state.record_suppression("BTC", 80)
    assert state.get("BTC")["suppression_count"] == 1
    state.record_suppression("BTC", 80)
    assert state.get("BTC")["suppression_count"] == 2

    # Record new asset
    state.record("ETH", 65, "allow")
    assert len(state) == 2

    # to_dict
    d = state.to_dict()
    assert isinstance(d, dict)
    assert set(d.keys()) == {"BTC", "ETH"}

    # Apply
    state2 = CooldownState()
    state2.apply(d)
    assert len(state2) == 2
    assert state2.get("BTC")["last_value_score"] == 80

    # Reset
    state.reset()
    assert state.is_empty()

    # Init from dict
    state3 = CooldownState({"SOL": {"last_allowed_at": _dt(), "last_value_score": 70, "occurrence_count": 3}})
    assert len(state3) == 1
    assert state3.get("SOL")["occurrence_count"] == 3

    print(f"  [PASS] CooldownState: record, suppress, apply, reset, init from dict")
    return True


def test_14_evaluate_cooldown_batch_sequential() -> bool:
    """14. evaluate_cooldown_batch 顺序处理"""
    signals = [
        (_signal(asset="BTC"), _value_result(value_score=75)),
        (_signal(asset="ETH"), _value_result(value_score=65)),
        (_signal(asset="BTC"), _value_result(value_score=75)),  # repeat
        (_signal(asset="SOL"), _value_result(value_score=80)),
        (_signal(asset="BTC"), _value_result(value_score=95)),  # upgrade!
    ]

    base = _dt()
    results = evaluate_cooldown_batch(
        signals, base_time=base, time_step_minutes=2.0
    )

    assert len(results) == 5

    # First BTC → allow
    assert results[0]["decision"] == "allow"
    assert results[0]["asset"] == "BTC"

    # ETH → allow (different asset)
    assert results[1]["decision"] == "allow"
    assert results[1]["asset"] == "ETH"

    # BTC again at 4 min → suppress
    assert results[2]["decision"] == "cooldown_suppress"
    assert results[2]["asset"] == "BTC"
    assert results[2]["minutes_since_last"] is not None

    # SOL → allow (different asset)
    assert results[3]["decision"] == "allow"
    assert results[3]["asset"] == "SOL"

    # BTC at 8 min with score 75→95 (Δ+20) → upgrade_override
    assert results[4]["decision"] == "upgrade_override"
    assert results[4]["asset"] == "BTC"
    assert results[4]["value_score"] == 95

    print(f"  [PASS] Batch of 5: A, A, S, A, U")
    return True


def test_15_blocked_signal_skips_cooldown() -> bool:
    """15. 信号被 block → 不进入冷却状态"""
    signal_blocked = _signal(asset="DOT")
    vr_blocked = _value_result(value_score=20, decision="block", allowed=False)

    state = _fresh_state()
    result = evaluate_cooldown(signal_blocked, vr_blocked, state, current_time=_dt())

    assert result["allowed"] is False
    assert result["decision"] == "cooldown_suppress"
    assert "blocked by value gate" in result["cooldown_reason"].lower()

    # State should NOT have recorded DOT
    updated = result["cooldown_state"]
    assert "DOT" not in updated or updated.get("DOT", {}).get("occurrence_count", 0) == 0

    print(f"  [PASS] Blocked signal → cooldown skipped, no state recorded")
    return True


def test_16_no_asset_identifier() -> bool:
    """16. 无法提取 asset → allow（无资产可追踪）"""
    signal = {"signal_type": "market_anomaly"}  # no asset field
    vr = _value_result(value_score=50)

    result = evaluate_cooldown(signal, vr, None, current_time=_dt())

    assert result["allowed"] is True
    assert result["decision"] == "allow"
    assert "no asset" in result["cooldown_reason"].lower()

    print(f"  [PASS] No asset field → allow (cannot track cooldown)")
    return True


def test_17_upgrade_override_exact_threshold() -> bool:
    """17. upgrade_override 精确在阈值上"""
    signal1 = _signal(asset="LINK")
    vr1 = _value_result(value_score=50)
    signal2 = _signal(asset="LINK")
    vr2 = _value_result(value_score=65)  # Δ=15 (exactly at threshold)

    state = _fresh_state()
    base = _dt()

    r1 = evaluate_cooldown(signal1, vr1, state, current_time=base)
    state.apply(r1["cooldown_state"])

    t2 = (datetime.fromisoformat(base) + timedelta(minutes=3)).isoformat()
    r2 = evaluate_cooldown(signal2, vr2, state, current_time=t2)

    # Δ=15 should trigger upgrade (>= threshold)
    assert r2["allowed"] is True, f"Δ=15 should trigger upgrade (>=15), got {r2}"
    assert r2["decision"] == "upgrade_override"

    print(f"  [PASS] LINK score 50→65 (Δ=15, exact threshold) → upgrade_override")
    return True


def test_18_multiple_suppressions() -> bool:
    """18. 连续多次 suppress → occurrence_count 递增，suppression_count 记录"""
    signal = _signal(asset="AVAX")
    vr = _value_result(value_score=55)

    state = _fresh_state()
    base = _dt()

    # First: allow
    r1 = evaluate_cooldown(signal, vr, state, current_time=base)
    state.apply(r1["cooldown_state"])
    assert r1["decision"] == "allow"
    assert r1["occurrence_count"] == 1

    # Second: 3 min → suppress
    t2 = (datetime.fromisoformat(base) + timedelta(minutes=3)).isoformat()
    r2 = evaluate_cooldown(signal, vr, state, current_time=t2)
    state.apply(r2["cooldown_state"])
    assert r2["decision"] == "cooldown_suppress"

    # Third: 6 min → suppress again (still within 10 min from FIRST allow)
    t3 = (datetime.fromisoformat(base) + timedelta(minutes=6)).isoformat()
    r3 = evaluate_cooldown(signal, vr, state, current_time=t3)
    state.apply(r3["cooldown_state"])
    assert r3["decision"] == "cooldown_suppress"

    # Fourth: 8 min → still suppress
    t4 = (datetime.fromisoformat(base) + timedelta(minutes=8)).isoformat()
    r4 = evaluate_cooldown(signal, vr, state, current_time=t4)
    assert r4["decision"] == "cooldown_suppress"

    # Check state: suppression_count should be >= 3
    updated = r4["cooldown_state"]
    avax_state = updated.get("AVAX", {})
    # Note: suppression_counter is on the original allow entry, not reset each time
    # Since record_suppression increments a counter on the state entry
    supp_count = avax_state.get("suppression_count", 0)
    assert supp_count >= 3, f"Expected >= 3 suppressions, got {supp_count}"

    print(f"  [PASS] AVAX: allow → suppress × 3, suppression_count={supp_count}")
    return True


# ── Run all tests ───────────────────────────────────────────────────────────────

def run_all_tests() -> int:
    tests = [
        ("1. 首次出现 → allow", test_1_first_occurrence_allow),
        ("2. 同资产冷却窗口内相同分数 → suppress", test_2_same_asset_within_window_suppress),
        ("3. 分数显著提升 → upgrade_override", test_3_upgrade_override),
        ("4. 冷却窗口过期 → allow", test_4_cooldown_window_expired_allow),
        ("5. 不同资产独立追踪", test_5_different_assets_independent),
        ("6. 无 value_result → 保守 allow", test_6_no_value_result_conservative_allow),
        ("7. 多资产交错各自独立", test_7_interleaved_multi_asset),
        ("8. 分数小幅提升不触发 override", test_8_small_score_increase_no_override),
        ("9. 冷却窗口恰好边界", test_9_window_exact_boundary),
        ("10. 空 state 创建新状态", test_10_empty_state_create_new),
        ("11. 返回结构完整", test_11_result_structure),
        ("12. 不包含敏感字段", test_12_no_sensitive_fields),
        ("13. CooldownState 状态管理", test_13_cooldown_state_management),
        ("14. evaluate_cooldown_batch 顺序处理", test_14_evaluate_cooldown_batch_sequential),
        ("15. 信号 blocked 跳过冷却", test_15_blocked_signal_skips_cooldown),
        ("16. 无法提取 asset → allow", test_16_no_asset_identifier),
        ("17. upgrade 精确在阈值", test_17_upgrade_override_exact_threshold),
        ("18. 连续 suppress occurrence 递增", test_18_multiple_suppressions),
    ]

    print("=" * 60)
    print(f"Market Radar {COOLDOWN_GATE_VERSION} — Same-Asset Cooldown Gate 单元测试")
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
