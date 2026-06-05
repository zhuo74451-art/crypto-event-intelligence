"""Market Radar v1.10-C — Signal Trust Gate 单元测试。

测试覆盖：
  - api + market_anomaly + fresh + test → allowed=True
  - api + market_anomaly + fresh + prod → allowed=True
  - fixture + fresh + test → allowed=True
  - fixture + fresh + prod → allowed=False
  - manual + fresh + test → allowed=True
  - manual + fresh + prod → allowed=False
  - unknown source_type → allowed=False
  - stale source_type → allowed=False
  - market_anomaly 超过 15 分钟 TTL → allowed=False
  - 缺少时间字段 → allowed=False
  - 未识别 signal_type → allowed=False
  - blocked report 包含 gate_version 和 signal_hash
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.market_radar_signal_trust_gate import (
    SignalTrustGate,
    SOURCE_TRUST_MAP,
    SIGNAL_TTL_SECONDS,
    build_signal_hash,
    extract_signal_time,
    write_blocked_report,
    GATE_VERSION,
    classify_signal_type_inline,
)

CN_TZ = timezone(timedelta(hours=8))

# ── Test helpers ────────────────────────────────────────────────────────────

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


# ── Tests ───────────────────────────────────────────────────────────────────

def test_api_market_anomaly_fresh_test_allowed() -> bool:
    """api + market_anomaly + fresh + test → allowed=True"""
    gate = SignalTrustGate()
    signal = _fresh_signal(source_type="api", signal_type="market_anomaly")
    result = gate.check(signal, target_env="test")
    assert result["allowed"] is True, f"Expected allowed=True, got {result}"
    assert result["gate_version"] == GATE_VERSION
    assert result["source_type"] == "api"
    assert result["signal_type"] == "market_anomaly"
    assert result["blocked_reason"] is None
    assert result["ttl_seconds"] == 15 * 60
    print(f"  [PASS] api + market_anomaly + fresh + test → allowed=True")
    return True


def test_api_market_anomaly_fresh_prod_allowed() -> bool:
    """api + market_anomaly + fresh + prod → allowed=True"""
    gate = SignalTrustGate()
    signal = _fresh_signal(source_type="api", signal_type="market_anomaly")
    result = gate.check(signal, target_env="prod")
    assert result["allowed"] is True, f"Expected allowed=True, got {result}"
    print(f"  [PASS] api + market_anomaly + fresh + prod → allowed=True")
    return True


def test_fixture_fresh_test_allowed() -> bool:
    """fixture + fresh + test → allowed=True"""
    gate = SignalTrustGate()
    signal = _fresh_signal(source_type="fixture", signal_type="market_anomaly")
    result = gate.check(signal, target_env="test")
    assert result["allowed"] is True, f"Expected allowed=True, got {result}"
    print(f"  [PASS] fixture + fresh + test → allowed=True")
    return True


def test_fixture_fresh_prod_blocked() -> bool:
    """fixture + fresh + prod → allowed=False"""
    gate = SignalTrustGate()
    signal = _fresh_signal(source_type="fixture", signal_type="market_anomaly")
    result = gate.check(signal, target_env="prod")
    assert result["allowed"] is False, f"Expected allowed=False, got {result}"
    assert "fixture" in result["blocked_reason"].lower()
    print(f"  [PASS] fixture + fresh + prod → allowed=False")
    return True


def test_manual_fresh_test_allowed() -> bool:
    """manual + fresh + test → allowed=True"""
    gate = SignalTrustGate()
    signal = _fresh_signal(source_type="manual", signal_type="market_anomaly")
    result = gate.check(signal, target_env="test")
    assert result["allowed"] is True, f"Expected allowed=True, got {result}"
    print(f"  [PASS] manual + fresh + test → allowed=True")
    return True


def test_manual_fresh_prod_blocked() -> bool:
    """manual + fresh + prod → allowed=False"""
    gate = SignalTrustGate()
    signal = _fresh_signal(source_type="manual", signal_type="market_anomaly")
    result = gate.check(signal, target_env="prod")
    assert result["allowed"] is False, f"Expected allowed=False, got {result}"
    assert "manual" in result["blocked_reason"].lower()
    print(f"  [PASS] manual + fresh + prod → allowed=False")
    return True


def test_unknown_source_type_blocked() -> bool:
    """unknown source_type → allowed=False"""
    gate = SignalTrustGate()
    signal = _fresh_signal(source_type="unknown")
    result = gate.check(signal, target_env="test")
    assert result["allowed"] is False, f"Expected allowed=False, got {result}"
    assert "unknown" in result["blocked_reason"].lower()
    print(f"  [PASS] unknown source_type → allowed=False")
    return True


def test_stale_source_type_blocked() -> bool:
    """stale source_type → allowed=False"""
    gate = SignalTrustGate()
    signal = _fresh_signal(source_type="stale")
    result = gate.check(signal, target_env="test")
    assert result["allowed"] is False, f"Expected allowed=False, got {result}"
    assert "stale" in result["blocked_reason"].lower()
    print(f"  [PASS] stale source_type → allowed=False")
    return True


def test_market_anomaly_ttl_expired_blocked() -> bool:
    """market_anomaly 超过 15 分钟 TTL → allowed=False"""
    gate = SignalTrustGate()
    signal = _old_signal(minutes_ago=20, source_type="api", signal_type="market_anomaly")
    result = gate.check(signal, target_env="test")
    assert result["allowed"] is False, f"Expected allowed=False, got {result}"
    assert "TTL expired" in result["blocked_reason"]
    assert result["age_seconds"] > result["ttl_seconds"]
    print(f"  [PASS] market_anomaly TTL expired → allowed=False (age={result['age_seconds']}s, ttl={result['ttl_seconds']}s)")
    return True


def test_missing_time_field_blocked() -> bool:
    """缺少时间字段 → allowed=False"""
    gate = SignalTrustGate()
    signal = {
        "signal_type": "market_anomaly",
        "asset": "BTC",
        "source_type": "api",
        "source": "test",
    }
    result = gate.check(signal, target_env="test")
    assert result["allowed"] is False, f"Expected allowed=False, got {result}"
    assert "Missing time field" in result["blocked_reason"]
    print(f"  [PASS] missing time field → allowed=False")
    return True


def test_unrecognized_signal_type_blocked() -> bool:
    """未识别 signal_type → allowed=False"""
    gate = SignalTrustGate()
    signal = _fresh_signal(source_type="api", signal_type="")
    # Remove signal_type entirely so it's not recognized
    signal.pop("signal_type", None)
    # Also remove features that would allow inference
    signal.pop("price_change_pct", None)
    signal.pop("asset", None)
    result = gate.check(signal, target_env="test")
    assert result["allowed"] is False, f"Expected allowed=False, got {result}"
    assert "Unrecognized signal_type" in result["blocked_reason"]
    print(f"  [PASS] unrecognized signal_type → allowed=False")
    return True


def test_blocked_report_contains_gate_version_and_signal_hash() -> bool:
    """blocked report 包含 gate_version 和 signal_hash"""
    import tempfile

    gate = SignalTrustGate()
    signal = _fresh_signal(source_type="stale")

    # First check — should block
    result = gate.check(signal, target_env="test")
    assert result["allowed"] is False
    assert result["gate_version"] == GATE_VERSION
    assert len(result["signal_hash"]) == 16

    # Write blocked report to temp file
    with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False, encoding="utf-8") as f:
        tmp_path = f.name

    try:
        written_path = write_blocked_report(result, path=tmp_path)
        with open(written_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
        assert len(lines) == 1, f"Expected 1 line, got {len(lines)}"
        record = json.loads(lines[0])
        assert record["gate_version"] == GATE_VERSION, f"gate_version mismatch: {record['gate_version']}"
        assert record["signal_hash"] == result["signal_hash"], f"signal_hash mismatch"
        assert "gate_version" in record
        assert "signal_hash" in record
        assert "blocked_reason" in record
        # Should NOT contain token/key/cookie/password
        record_str = json.dumps(record)
        for secret in ["token", "key", "cookie", "password"]:
            assert secret not in record_str.lower(), f"'{secret}' found in blocked report"
        print(f"  [PASS] blocked report contains gate_version and signal_hash")
    finally:
        try:
            os.unlink(tmp_path)
        except Exception:
            pass
    return True


def test_build_signal_hash_deterministic() -> bool:
    """build_signal_hash 对相同信号返回相同 hash"""
    signal = _fresh_signal()
    h1 = build_signal_hash(signal)
    h2 = build_signal_hash(signal)
    assert h1 == h2, f"Hash not deterministic: {h1} vs {h2}"
    assert len(h1) == 16
    print(f"  [PASS] build_signal_hash is deterministic ({h1})")
    return True


def test_extract_signal_time_priority() -> bool:
    """extract_signal_time 按优先级提取时间"""
    now = datetime.now(timezone.utc)
    generated = (now - timedelta(minutes=5)).strftime("%Y-%m-%dT%H:%M:%SZ")
    fetched = (now - timedelta(minutes=10)).strftime("%Y-%m-%dT%H:%M:%SZ")
    timestamp = (now - timedelta(minutes=15)).strftime("%Y-%m-%dT%H:%M:%SZ")
    created = (now - timedelta(minutes=20)).strftime("%Y-%m-%dT%H:%M:%SZ")

    signal = {
        "generated_at": generated,
        "fetched_at": fetched,
        "timestamp": timestamp,
        "created_at": created,
    }
    result = extract_signal_time(signal)
    assert result is not None
    assert result.strftime("%Y-%m-%dT%H:%M:%SZ") == generated
    print(f"  [PASS] extract_signal_time uses generated_at (highest priority)")

    # Only fetched_at
    signal2 = {"fetched_at": fetched}
    result2 = extract_signal_time(signal2)
    assert result2 is not None
    assert result2.strftime("%Y-%m-%dT%H:%M:%SZ") == fetched
    print(f"  [PASS] extract_signal_time falls back to fetched_at")

    # observed_at as final fallback
    signal3 = {"observed_at": created}
    result3 = extract_signal_time(signal3)
    assert result3 is not None
    print(f"  [PASS] extract_signal_time uses observed_at as fallback")
    return True


def test_default_target_env_is_test() -> bool:
    """Gate 默认 target_env="test"（不默认 prod）"""
    gate = SignalTrustGate()
    # fixture is allowed in test, blocked in prod
    signal = _fresh_signal(source_type="fixture")
    result = gate.check(signal)  # default
    assert result["target_env"] == "test"
    assert result["allowed"] is True  # fixture allowed in test
    print(f"  [PASS] default target_env=test")
    return True


def test_allowed_result_structure() -> bool:
    """通过的结果包含所有必需字段"""
    gate = SignalTrustGate()
    signal = _fresh_signal(source_type="api", signal_type="market_anomaly")
    result = gate.check(signal, target_env="test")

    required_keys = [
        "allowed", "gate_version", "target_env", "source_type",
        "signal_type", "signal_id", "signal_hash", "generated_at",
        "checked_at", "ttl_seconds", "age_seconds", "blocked_reason",
    ]
    for key in required_keys:
        assert key in result, f"Missing key '{key}' in result"

    assert result["allowed"] is True
    assert result["blocked_reason"] is None
    assert result["gate_version"] == GATE_VERSION
    print(f"  [PASS] allowed result has all required fields")
    return True


def test_blocked_result_structure() -> bool:
    """blocked 结果包含 blocked_reason"""
    gate = SignalTrustGate()
    signal = _fresh_signal(source_type="stale")
    result = gate.check(signal, target_env="test")

    assert result["allowed"] is False
    assert result["blocked_reason"] is not None
    assert len(result["blocked_reason"]) > 0
    print(f"  [PASS] blocked result has non-empty blocked_reason")
    return True


def test_whale_ttl_60min() -> bool:
    """whale_transfer TTL = 60 分钟"""
    gate = SignalTrustGate()
    # Fresh whale signal
    signal = _fresh_signal(source_type="api", signal_type="whale_transfer",
                           transfer_amount=1000, from_address="0xAAA", to_address="0xBBB")
    result = gate.check(signal, target_env="test")
    assert result["allowed"] is True
    assert result["ttl_seconds"] == 60 * 60
    print(f"  [PASS] whale_transfer TTL = 60 min")

    # Old whale signal (70 min ago)
    signal_old = _old_signal(minutes_ago=70, source_type="api", signal_type="whale_transfer",
                             transfer_amount=1000, from_address="0xAAA", to_address="0xBBB")
    result_old = gate.check(signal_old, target_env="test")
    assert result_old["allowed"] is False
    assert "TTL expired" in result_old["blocked_reason"]
    print(f"  [PASS] whale_transfer 70min old → blocked")
    return True


def test_news_ttl_6hours() -> bool:
    """news_event TTL = 6 小时"""
    gate = SignalTrustGate()
    signal = _fresh_signal(source_type="api", signal_type="news_event",
                           event_title="Test News", event_type="市场")
    result = gate.check(signal, target_env="test")
    assert result["allowed"] is True
    assert result["ttl_seconds"] == 6 * 60 * 60
    print(f"  [PASS] news_event TTL = 6 hours")
    return True


def test_onchain_position_ttl_60min() -> bool:
    """onchain_position TTL = 60 分钟"""
    result_ttl = SIGNAL_TTL_SECONDS.get("onchain_position", 0)
    assert result_ttl == 60 * 60, f"Expected 3600, got {result_ttl}"
    print(f"  [PASS] onchain_position TTL = 60 min")
    return True


def test_source_trust_map_coverage() -> bool:
    """SOURCE_TRUST_MAP 覆盖所有要求的类型"""
    required_types = ["api", "real", "external", "fixture", "manual", "unknown", "stale"]
    for t in required_types:
        assert t in SOURCE_TRUST_MAP, f"Missing source_type '{t}' in SOURCE_TRUST_MAP"

    # Verify rules
    assert SOURCE_TRUST_MAP["api"]["allow_test_send"] is True
    assert SOURCE_TRUST_MAP["api"]["allow_prod_send"] is True
    assert SOURCE_TRUST_MAP["fixture"]["allow_test_send"] is True
    assert SOURCE_TRUST_MAP["fixture"]["allow_prod_send"] is False
    assert SOURCE_TRUST_MAP["manual"]["allow_test_send"] is True
    assert SOURCE_TRUST_MAP["manual"]["allow_prod_send"] is False
    assert SOURCE_TRUST_MAP["unknown"]["allow_test_send"] is False
    assert SOURCE_TRUST_MAP["unknown"]["allow_prod_send"] is False
    assert SOURCE_TRUST_MAP["stale"]["allow_test_send"] is False
    assert SOURCE_TRUST_MAP["stale"]["allow_prod_send"] is False
    print(f"  [PASS] SOURCE_TRUST_MAP covers all required types with correct rules")
    return True


def test_signal_ttl_map_coverage() -> bool:
    """SIGNAL_TTL_SECONDS 包含关键信号类型"""
    key_types = [
        "market_anomaly", "whale", "whale_transfer", "onchain", "onchain_position",
        "news", "news_event", "macro", "position", "liquidation", "combo",
        "risk_alert", "unknown",
    ]
    for t in key_types:
        assert t in SIGNAL_TTL_SECONDS, f"Missing signal_type '{t}' in SIGNAL_TTL_SECONDS"

    # Verify specific TTLs
    assert SIGNAL_TTL_SECONDS["market_anomaly"] == 15 * 60
    assert SIGNAL_TTL_SECONDS["whale_transfer"] == 60 * 60
    assert SIGNAL_TTL_SECONDS["news_event"] == 6 * 60 * 60
    assert SIGNAL_TTL_SECONDS["unknown"] == 0
    print(f"  [PASS] SIGNAL_TTL_SECONDS covers all key types")
    return True


def test_no_token_in_blocked_report() -> bool:
    """blocked report 不包含 token/key/cookie/password/chat_id"""
    import tempfile

    gate = SignalTrustGate()
    signal = _fresh_signal(source_type="stale")
    result = gate.check(signal, target_env="test")

    with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False, encoding="utf-8") as f:
        tmp_path = f.name

    try:
        written_path = write_blocked_report(result, path=tmp_path)
        with open(written_path, "r", encoding="utf-8") as f:
            content = f.read()

        sensitive = ["token", "key", "cookie", "password", "secret", "chat_id"]
        content_lower = content.lower()
        for s in sensitive:
            assert s not in content_lower, f"Sensitive term '{s}' found in blocked report"
        print(f"  [PASS] blocked report contains no sensitive terms")
    finally:
        try:
            os.unlink(tmp_path)
        except Exception:
            pass
    return True


def test_write_blocked_report_default_path() -> bool:
    """write_blocked_report 写入默认路径"""
    gate = SignalTrustGate()
    signal = _fresh_signal(source_type="stale")
    result = gate.check(signal, target_env="test")

    default_path = ROOT / "runs" / "market_radar" / "v110c_signal_trust_gate_blocked_report.jsonl"
    # Remove if exists
    if default_path.exists():
        default_path.unlink()

    written = write_blocked_report(result)
    assert written.exists(), f"Report not written to {written}"
    assert default_path.exists(), f"Default path not created"

    # Verify content
    with open(written, "r", encoding="utf-8") as f:
        line = f.readline()
    record = json.loads(line)
    assert record["gate_version"] == GATE_VERSION
    assert record["signal_hash"] == result["signal_hash"]

    # Clean up
    default_path.unlink()
    print(f"  [PASS] write_blocked_report writes to default path")
    return True


def test_signal_id_fallback_to_hash() -> bool:
    """没有 signal_id 时用 signal_hash 兜底"""
    gate = SignalTrustGate()
    signal = _fresh_signal(source_type="stale")
    signal.pop("signal_id", None)
    signal.pop("id", None)

    result = gate.check(signal, target_env="test")
    # signal_id should be populated from signal_hash as fallback
    assert result["signal_id"] == result["signal_hash"]
    print(f"  [PASS] signal_id falls back to signal_hash when missing")
    return True


def test_combo_signal_gate() -> bool:
    """Combo 信号可以通过 Gate"""
    gate = SignalTrustGate()
    signal = _fresh_signal(source_type="api", signal_type="combo",
                           combo_members=[{"signal_type": "market_anomaly"}])
    result = gate.check(signal, target_env="test")
    assert result["allowed"] is True
    assert result["signal_type"] == "combo"
    assert result["ttl_seconds"] == 30 * 60
    print(f"  [PASS] combo signal passes gate")
    return True


# ── Run all tests ───────────────────────────────────────────────────────────

def run_all_tests() -> int:
    tests = [
        ("api + market_anomaly + fresh + test → allowed=True", test_api_market_anomaly_fresh_test_allowed),
        ("api + market_anomaly + fresh + prod → allowed=True", test_api_market_anomaly_fresh_prod_allowed),
        ("fixture + fresh + test → allowed=True", test_fixture_fresh_test_allowed),
        ("fixture + fresh + prod → allowed=False", test_fixture_fresh_prod_blocked),
        ("manual + fresh + test → allowed=True", test_manual_fresh_test_allowed),
        ("manual + fresh + prod → allowed=False", test_manual_fresh_prod_blocked),
        ("unknown source_type → allowed=False", test_unknown_source_type_blocked),
        ("stale source_type → allowed=False", test_stale_source_type_blocked),
        ("market_anomaly TTL expired → allowed=False", test_market_anomaly_ttl_expired_blocked),
        ("missing time field → allowed=False", test_missing_time_field_blocked),
        ("unrecognized signal_type → allowed=False", test_unrecognized_signal_type_blocked),
        ("blocked report 包含 gate_version 和 signal_hash", test_blocked_report_contains_gate_version_and_signal_hash),
        ("build_signal_hash deterministic", test_build_signal_hash_deterministic),
        ("extract_signal_time priority", test_extract_signal_time_priority),
        ("default target_env=test", test_default_target_env_is_test),
        ("allowed result structure", test_allowed_result_structure),
        ("blocked result structure", test_blocked_result_structure),
        ("whale_transfer TTL 60min", test_whale_ttl_60min),
        ("news_event TTL 6 hours", test_news_ttl_6hours),
        ("onchain_position TTL 60min", test_onchain_position_ttl_60min),
        ("SOURCE_TRUST_MAP coverage", test_source_trust_map_coverage),
        ("SIGNAL_TTL_SECONDS coverage", test_signal_ttl_map_coverage),
        ("no token in blocked report", test_no_token_in_blocked_report),
        ("write_blocked_report default path", test_write_blocked_report_default_path),
        ("signal_id fallback to hash", test_signal_id_fallback_to_hash),
        ("combo signal passes gate", test_combo_signal_gate),
    ]

    print("=" * 60)
    print("Market Radar v1.10-C — Signal Trust Gate 测试套件")
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
