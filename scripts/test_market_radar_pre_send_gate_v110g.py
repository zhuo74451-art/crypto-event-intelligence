"""Market Radar v1.10-G — pre_send_gate 通用发送前安全接口 单元测试

测试覆盖：
  - fresh api signal + valid payload + test → allowed=True
  - fixture + valid payload + test → allowed=True
  - fixture + valid payload + prod → allowed=False
  - unknown source_type → allowed=False
  - expired signal → allowed=False
  - missing payload text → allowed=False
  - empty payload text → allowed=False
  - payload parse_mode=None but text valid → allowed=True
  - blocked result 包含 signal_hash
  - 不包含 token/chat_id/key 敏感字段
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.market_radar_pre_send_gate import pre_send_gate
from scripts.market_radar_signal_trust_gate import GATE_VERSION


CN_TZ = timezone(timedelta(hours=8))


# ── Test helpers ──────────────────────────────────────────────────────────────

def _fresh_signal(**overrides) -> dict:
    """Build a fresh (just now) signal with defaults."""
    now = datetime.now(timezone.utc)
    base = {
        "signal_type": "market_anomaly",
        "asset": "BTC",
        "core_entity": "BTC",
        "source_type": "api",
        "source": "hyperliquid",
        "source_url": "https://app.hyperliquid.xyz/",
        "price_change_pct": 5.0,
        "volume_change_pct": 30.0,
        "generated_at": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "observed_at": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "status": "ok",
    }
    base.update(overrides)
    return base


def _old_signal(minutes_ago: int = 20, **overrides) -> dict:
    """Build an old signal from N minutes ago."""
    then = datetime.now(timezone.utc) - timedelta(minutes=minutes_ago)
    base = _fresh_signal(**overrides)
    base["generated_at"] = then.strftime("%Y-%m-%dT%H:%M:%SZ")
    base["observed_at"] = then.strftime("%Y-%m-%dT%H:%M:%SZ")
    return base


def _valid_payload(**overrides) -> dict:
    """Build a valid payload dict matching render_card_payload output."""
    base = {
        "text": "📊 *BTC 行情异动*\\\n\\\n不构成交易建议。",
        "parse_mode": "MarkdownV2",
        "card_type": "market_anomaly",
        "fallback_used": False,
        "warnings": [],
    }
    base.update(overrides)
    return base


# ── Tests ─────────────────────────────────────────────────────────────────────

def test_fresh_api_signal_valid_payload_test_allowed() -> bool:
    """fresh api signal + valid payload + test → allowed=True"""
    signal = _fresh_signal(source_type="api", signal_type="market_anomaly")
    payload = _valid_payload()
    result = pre_send_gate(signal, payload, target_env="test")

    assert result["allowed"] is True, f"Expected allowed=True, got {result}"
    assert result["target_env"] == "test"
    assert result["payload_ok"] is True
    assert result["blocked_reason"] is None
    assert len(result["signal_hash"]) == 16
    assert result["gate_result"]["allowed"] is True
    assert result["gate_version"] == GATE_VERSION
    print(f"  [PASS] fresh api signal + valid payload + test → allowed=True")
    return True


def test_fixture_valid_payload_test_allowed() -> bool:
    """fixture + valid payload + test → allowed=True"""
    signal = _fresh_signal(source_type="fixture", signal_type="market_anomaly")
    payload = _valid_payload()
    result = pre_send_gate(signal, payload, target_env="test")

    assert result["allowed"] is True, f"Expected allowed=True, got {result}"
    assert result["target_env"] == "test"
    assert result["payload_ok"] is True
    assert result["blocked_reason"] is None
    print(f"  [PASS] fixture + valid payload + test → allowed=True")
    return True


def test_fixture_valid_payload_prod_blocked() -> bool:
    """fixture + valid payload + prod → allowed=False"""
    signal = _fresh_signal(source_type="fixture", signal_type="market_anomaly")
    payload = _valid_payload()
    result = pre_send_gate(signal, payload, target_env="prod")

    assert result["allowed"] is False, f"Expected allowed=False, got {result}"
    assert result["target_env"] == "prod"
    assert "fixture" in result["blocked_reason"].lower()
    assert result["gate_result"]["allowed"] is False
    print(f"  [PASS] fixture + valid payload + prod → allowed=False")
    return True


def test_unknown_source_type_blocked() -> bool:
    """unknown source_type → allowed=False"""
    signal = _fresh_signal(source_type="unknown")
    payload = _valid_payload()
    result = pre_send_gate(signal, payload, target_env="test")

    assert result["allowed"] is False, f"Expected allowed=False, got {result}"
    assert "unknown" in result["blocked_reason"].lower() or "Unrecognized source_type" in str(result.get("blocked_reason", ""))
    print(f"  [PASS] unknown source_type → allowed=False")
    return True


def test_expired_signal_blocked() -> bool:
    """expired signal → allowed=False"""
    signal = _old_signal(minutes_ago=20, source_type="api", signal_type="market_anomaly")
    payload = _valid_payload()
    result = pre_send_gate(signal, payload, target_env="test")

    assert result["allowed"] is False, f"Expected allowed=False, got {result}"
    assert "TTL expired" in result["blocked_reason"]
    assert result["gate_result"]["age_seconds"] > result["gate_result"]["ttl_seconds"]
    print(f"  [PASS] expired signal → allowed=False (age={result['gate_result']['age_seconds']}s)")
    return True


def test_missing_payload_text_blocked() -> bool:
    """missing payload text → allowed=False"""
    signal = _fresh_signal(source_type="api", signal_type="market_anomaly")
    payload = {"parse_mode": "MarkdownV2"}  # no 'text'
    result = pre_send_gate(signal, payload, target_env="test")

    assert result["allowed"] is False, f"Expected allowed=False, got {result}"
    assert result["payload_ok"] is False
    assert "text" in result["blocked_reason"].lower()
    print(f"  [PASS] missing payload text → allowed=False")
    return True


def test_empty_payload_text_blocked() -> bool:
    """empty payload text → allowed=False"""
    signal = _fresh_signal(source_type="api", signal_type="market_anomaly")

    # Empty string
    payload1 = {"text": "", "parse_mode": "MarkdownV2"}
    result1 = pre_send_gate(signal, payload1, target_env="test")
    assert result1["allowed"] is False, f"Expected allowed=False for empty string, got {result1}"
    assert "empty" in result1["blocked_reason"].lower()
    print(f"  [PASS] empty payload text (\"\") → allowed=False")

    # Whitespace-only
    payload2 = {"text": "   \n  \t  ", "parse_mode": "MarkdownV2"}
    result2 = pre_send_gate(signal, payload2, target_env="test")
    assert result2["allowed"] is False, f"Expected allowed=False for whitespace, got {result2}"
    assert "empty" in result2["blocked_reason"].lower()
    print(f"  [PASS] whitespace-only payload text → allowed=False")
    return True


def test_parse_mode_none_text_valid_allowed() -> bool:
    """payload parse_mode=None but text valid → allowed=True (plain text is valid)"""
    signal = _fresh_signal(source_type="api", signal_type="market_anomaly")
    payload = {"text": "📊 BTC 行情异动: +5.00%\n不构成交易建议。", "parse_mode": None}
    result = pre_send_gate(signal, payload, target_env="test")

    assert result["allowed"] is True, f"Expected allowed=True, got {result}"
    assert result["payload_ok"] is True
    assert result["blocked_reason"] is None
    print(f"  [PASS] parse_mode=None but text valid → allowed=True")
    return True


def test_blocked_result_contains_signal_hash() -> bool:
    """blocked result 包含 signal_hash"""
    signal = _fresh_signal(source_type="unknown")
    payload = _valid_payload()
    result = pre_send_gate(signal, payload, target_env="test")

    assert result["allowed"] is False
    assert "signal_hash" in result
    assert len(result["signal_hash"]) == 16
    assert isinstance(result["signal_hash"], str)
    print(f"  [PASS] blocked result contains signal_hash = {result['signal_hash']}")
    return True


def test_no_token_chat_id_key_in_result() -> bool:
    """pre_send_gate 返回结果不包含 token/chat_id/key 敏感字段"""
    signal = _fresh_signal(source_type="api", signal_type="market_anomaly")
    payload = _valid_payload()
    result = pre_send_gate(signal, payload, target_env="test")

    # Serialize entire result to JSON and check for sensitive patterns
    result_str = json.dumps(result, ensure_ascii=False, default=str).lower()
    sensitive_terms = ["token", "chat_id", "key", "cookie", "password", "secret", "bot_token"]
    found = []
    for term in sensitive_terms:
        if term in result_str:
            found.append(term)

    assert len(found) == 0, f"Sensitive terms found in result: {found}"
    print(f"  [PASS] result contains no sensitive fields (token/chat_id/key/cookie/password/secret)")
    return True


def test_allowed_result_structure() -> bool:
    """通过的结果包含所有必需字段"""
    signal = _fresh_signal(source_type="api", signal_type="market_anomaly")
    payload = _valid_payload()
    result = pre_send_gate(signal, payload, target_env="test")

    required_keys = [
        "allowed", "target_env", "gate_result", "payload_ok",
        "blocked_reason", "signal_hash", "gate_version",
    ]
    for key in required_keys:
        assert key in result, f"Missing key '{key}' in result"

    assert result["allowed"] is True
    assert result["payload_ok"] is True
    assert result["blocked_reason"] is None
    assert isinstance(result["gate_result"], dict)
    assert result["gate_version"] == GATE_VERSION
    print(f"  [PASS] allowed result has all required fields")
    return True


def test_blocked_result_structure() -> bool:
    """blocked 结果包含 blocked_reason 且 non-empty"""
    signal = _fresh_signal(source_type="unknown")
    payload = _valid_payload()
    result = pre_send_gate(signal, payload, target_env="test")

    assert result["allowed"] is False
    assert result["blocked_reason"] is not None
    assert len(result["blocked_reason"]) > 0
    assert result["payload_ok"] is True  # payload itself was fine
    print(f"  [PASS] blocked result has non-empty blocked_reason")
    return True


def test_gate_blocked_but_payload_valid() -> bool:
    """Gate blocked 但 payload 本身合法 → allowed=False, payload_ok=True"""
    signal = _old_signal(minutes_ago=20, source_type="api", signal_type="market_anomaly")
    payload = _valid_payload()
    result = pre_send_gate(signal, payload, target_env="test")

    assert result["allowed"] is False  # gate blocked
    assert result["payload_ok"] is True  # payload was fine
    assert "TTL expired" in result["blocked_reason"]
    print(f"  [PASS] gate blocked but payload valid → allowed=False, payload_ok=True")
    return True


def test_both_gate_blocked_and_payload_bad() -> bool:
    """Gate blocked 且 payload 也无效 → allowed=False, payload_ok=False"""
    signal = _old_signal(minutes_ago=20, source_type="unknown")
    payload = {"parse_mode": "MarkdownV2"}  # missing text
    result = pre_send_gate(signal, payload, target_env="test")

    assert result["allowed"] is False
    assert result["payload_ok"] is False
    assert result["blocked_reason"] is not None
    print(f"  [PASS] both gate blocked and payload bad → allowed=False, payload_ok=False")
    return True


def test_signal_hash_deterministic_across_calls() -> bool:
    """同一 signal 多次调用 pre_send_gate 返回相同 signal_hash"""
    signal = _fresh_signal(source_type="api", signal_type="market_anomaly")
    payload = _valid_payload()
    r1 = pre_send_gate(signal, payload, target_env="test")
    r2 = pre_send_gate(signal, payload, target_env="test")
    assert r1["signal_hash"] == r2["signal_hash"], f"Hash differs: {r1['signal_hash']} vs {r2['signal_hash']}"
    print(f"  [PASS] signal_hash is deterministic across calls ({r1['signal_hash']})")
    return True


def test_default_target_env_is_test() -> bool:
    """默认 target_env="test" """
    signal = _fresh_signal(source_type="fixture")
    payload = _valid_payload()
    result = pre_send_gate(signal, payload)  # no target_env arg
    assert result["target_env"] == "test"
    assert result["allowed"] is True  # fixture allowed in test
    print(f"  [PASS] default target_env=test")
    return True


# ── Run all tests ─────────────────────────────────────────────────────────────

def run_all_tests() -> int:
    tests = [
        ("fresh api signal + valid payload + test → allowed=True", test_fresh_api_signal_valid_payload_test_allowed),
        ("fixture + valid payload + test → allowed=True", test_fixture_valid_payload_test_allowed),
        ("fixture + valid payload + prod → allowed=False", test_fixture_valid_payload_prod_blocked),
        ("unknown source_type → allowed=False", test_unknown_source_type_blocked),
        ("expired signal → allowed=False", test_expired_signal_blocked),
        ("missing payload text → allowed=False", test_missing_payload_text_blocked),
        ("empty payload text → allowed=False", test_empty_payload_text_blocked),
        ("parse_mode=None but text valid → allowed=True", test_parse_mode_none_text_valid_allowed),
        ("blocked result 包含 signal_hash", test_blocked_result_contains_signal_hash),
        ("不包含 token/chat_id/key 敏感字段", test_no_token_chat_id_key_in_result),
        ("allowed result structure", test_allowed_result_structure),
        ("blocked result structure", test_blocked_result_structure),
        ("gate blocked but payload valid", test_gate_blocked_but_payload_valid),
        ("both gate blocked and payload bad", test_both_gate_blocked_and_payload_bad),
        ("signal_hash deterministic across calls", test_signal_hash_deterministic_across_calls),
        ("default target_env=test", test_default_target_env_is_test),
    ]

    print("=" * 60)
    print("Market Radar v1.10-G — pre_send_gate 通用发送前安全接口 测试套件")
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
