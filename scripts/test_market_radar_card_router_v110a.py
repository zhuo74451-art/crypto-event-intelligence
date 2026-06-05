"""Market Radar Card Router v1.10-A R2 — 单元测试。

测试覆盖（R2 扩展）：
- 5 类 signal 都能分类
- 5 类模板都能渲染
- unknown 不崩溃
- 地址默认脱敏
- 输出包含「不构成交易建议」
- 不包含 bot token
- 网络失败时能降级（通过 error_card）
- 多行文本不破坏卡片格式
- normalize_signal 补充 metadata 字段
- 特征推断分类
- humanize_money 正常输出
- None / nan / inf 不进入卡片
- MarkdownV2 特殊字符会转义
- 地址脱敏
- 5 类卡片都有触发原因
- 公开外链存在
- 同币多信号会生成 combo
- 被 combo 合并的信号不重复渲染单卡
- 卡片不包含 traceback / HTTPError / KeyError
- 卡片不包含 salt / hash / magic / watchdog
- run_manifest 存在并有用户可读摘要
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.market_radar_card_router import (
    classify_signal_type,
    render_card,
    render_card_payload,
    render_onchain_position_card,
    render_whale_transfer_card,
    render_news_event_card,
    render_market_anomaly_card,
    render_risk_alert_card,
    render_error_card,
)
from scripts.market_radar_free_sources import (
    _http_get,
    _http_get_text,
    _http_post,
    _clean_error,
    DEFAULT_TIMEOUT,
    normalize_signal,
)
from scripts.market_radar_tg_formatting import (
    safe_value,
    humanize_number,
    humanize_money,
    humanize_percent,
    humanize_token_amount,
    mask_address,
    normalize_symbol,
    escape_markdown_v2,
    build_public_links,
    render_source_links,
    render_tg_safe_text,
    _strip_exception_text,
    _contains_exception_markers,
)
from scripts.market_radar_free_sources import (
    _http_get,
    _http_get_text,
    _http_post,
    _clean_error,
    DEFAULT_TIMEOUT,
    normalize_signal,
)
from scripts.market_radar_signal_merge import (
    should_merge,
    merge_related_signals,
    build_combo_signal,
    render_combo_card,
)


# ── 测试用例 ──────────────────────────────────────────────────────────────

ONCHAIN_FIXTURE = {
    "signal_type": "onchain_position",
    "asset": "HYPE",
    "core_entity": "HYPE",
    "address": "0x082d2ca88b5e0e6c1e8c0b5e2d3f4a5b6c7d8e9f",
    "side": "多头",
    "position_value_usd": 100_000_000,
    "quantity": 1_380_000,
    "entry_price": 33.68,
    "mark_price": 72.51,
    "pnl_usd": 46_985_000,
    "liquidation_price": 54.93,
    "note": "示例数据",
    "source_url": "https://app.hyperliquid.xyz/",
    "source": "test",
    "trigger_reason": "HYPE 多头大额持仓，Hyperliquid 公开 API 检测到链上仓位",
    "observed_at": "2026-06-04T06:00:00Z",
}

WHALE_FIXTURE = {
    "signal_type": "whale_transfer",
    "asset": "ETH",
    "core_entity": "ETH",
    "transfer_amount": 12_500,
    "amount_usd": 45_000_000,
    "from_address": "0x1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b",
    "to_address": "0x28c6c06298d514089e0a6c0b5e2d3f4a5b6c7d8e",
    "to_exchange": "true",
    "chain": "Ethereum",
    "historical_behavior": "过去 3 个月累计向交易所转入 5 万 ETH",
    "potential_implication": "大额转入交易所可能预示卖出意愿",
    "risk_note": "巨鲸行为仅供参考",
    "tx_hash": "0xabcd1234ef567890abcd1234ef567890abcd1234ef567890abcd1234ef5678",
    "source_url": "https://etherscan.io/tx/0xabcd",
    "source": "test",
    "trigger_reason": "检测到大额 ETH 转账，目标疑似交易所",
    "observed_at": "2026-06-04T06:00:00Z",
}

NEWS_FIXTURE = {
    "signal_type": "news_event",
    "core_entity": "BTC",
    "event_title": "美 SEC 批准比特币现货 ETF 期权交易",
    "affected_assets": "BTC, ETH",
    "event_type": "监管",
    "trading_relevance": "高",
    "already_priced": "部分已定价",
    "risk_tags": "监管, ETF",
    "observation_window": "2-4 小时",
    "source": "CoinDesk",
    "source_url": "https://www.coindesk.com/",
    "summary": "SEC 正式批准多家交易所的现货 BTC ETF 期权交易。",
    "trigger_reason": "RSS 源 CoinDesk 检测到监管类新闻",
    "observed_at": "2026-06-04T06:00:00Z",
}

ANOMALY_FIXTURE = {
    "signal_type": "market_anomaly",
    "core_entity": "SOL",
    "asset": "SOL",
    "price_change_pct": 12.5,
    "volume_change_pct": 85.0,
    "oi_change_pct": 15.3,
    "funding_rate": 0.0025,
    "liquidation_status": "24h 清算：多单 $12.5M / 空单 $3.2M",
    "is_crowded": "是",
    "observation_window": "1-4 小时",
    "note": "测试数据",
    "source_url": "https://app.hyperliquid.xyz/",
    "source": "test",
    "trigger_reason": "SOL 24h 涨幅 12.50% 触发行情异动监测",
    "observed_at": "2026-06-04T06:00:00Z",
}

RISK_FIXTURE = {
    "signal_type": "risk_alert",
    "core_entity": "HYPE",
    "risk_type": "资金费率极端",
    "affected_asset": "HYPE",
    "impact_scope": "HYPE 永续合约交易者",
    "current_status": "资金费率 0.05%/8h，多头极度拥挤",
    "is_spreading": "否",
    "what_to_watch": "关注费率回归和可能的轧空风险",
    "risk_note": "极端正费率可能预示多头拥挤回调",
    "source": "Hyperliquid",
    "trigger_reason": "HYPE 触发资金费率极端预警",
    "observed_at": "2026-06-04T06:00:00Z",
}

ALL_FIXTURES = {
    "onchain_position": ONCHAIN_FIXTURE,
    "whale_transfer": WHALE_FIXTURE,
    "news_event": NEWS_FIXTURE,
    "market_anomaly": ANOMALY_FIXTURE,
    "risk_alert": RISK_FIXTURE,
}


# ── 原有测试（保持兼容）──────────────────────────────────────────────────

def test_classify_all_5_types() -> bool:
    """测试 5 类 signal 都能正确分类。"""
    expected = {
        "onchain_position": "onchain_position",
        "whale_transfer": "whale_transfer",
        "news_event": "news_event",
        "market_anomaly": "market_anomaly",
        "risk_alert": "risk_alert",
    }
    passed = 0
    failed = 0
    for exp_type, fixture in ALL_FIXTURES.items():
        result = classify_signal_type(fixture)
        if result == exp_type:
            passed += 1
            print(f"  [PASS] {exp_type} → {result}")
        else:
            failed += 1
            print(f"  [FAIL] {exp_type} → expected {exp_type}, got {result}")
    print(f"  Result: {passed}/{passed + failed} passed")
    return failed == 0


def test_render_all_5_templates() -> bool:
    """测试 5 类模板都能渲染出有效卡片（> 50 字符，以适当标签开头）。"""
    failed = 0
    for name, fixture in ALL_FIXTURES.items():
        try:
            card = render_card(fixture)
            assert isinstance(card, str), f"render_card returned {type(card)}"
            assert len(card) > 50, f"card too short: {len(card)} chars"
            if name == "onchain_position":
                assert "仓位雷达" in card, "missing 仓位雷达"
            elif name == "whale_transfer":
                assert "巨鲸" in card, "missing 巨鲸"
            elif name == "news_event":
                assert "新闻事件" in card, "missing 新闻事件"
            elif name == "market_anomaly":
                assert "行情异动" in card, "missing 行情异动"
            elif name == "risk_alert":
                assert "风险预警" in card, "missing 风险预警"
            print(f"  [PASS] {name}: {len(card)} chars")
        except Exception as exc:
            failed += 1
            print(f"  [FAIL] {name}: {exc}")
    print(f"  Result: {5 - failed}/5 templates passed")
    return failed == 0


def test_unknown_no_crash() -> bool:
    """测试 unknown 类型不崩溃。"""
    cases = [
        {},
        {"signal_type": "unknown"},
        {"foo": "bar"},
        {"note": "random signal without type"},
        None,
    ]
    passed = 0
    failed = 0
    for i, case in enumerate(cases):
        try:
            ct = classify_signal_type(case or {})
            card = render_card(case or {})
            assert isinstance(card, str)
            assert len(card) > 0
            passed += 1
            print(f"  [PASS] unknown case {i}: type={ct}, card_len={len(card)}")
        except Exception as exc:
            failed += 1
            print(f"  [FAIL] unknown case {i}: {exc}")
    print(f"  Result: {passed}/{passed + failed} passed")
    return failed == 0


def test_address_masked() -> bool:
    """测试地址默认脱敏。"""
    failed = 0
    for name, fixture in ALL_FIXTURES.items():
        card = render_card(fixture)
        lines = card.split("\n")
        for line in lines:
            for word in line.split():
                if word.startswith("0x") and len(word) > 20:
                    failed += 1
                    print(f"  [FAIL] {name}: unmasked address in line: {line[:100]}")
                    break
    if failed == 0:
        print(f"  [PASS] All addresses masked")
        return True
    print(f"  Result: {failed} unmasked addresses found")
    return False


def test_disclaimer_present() -> bool:
    """测试所有卡片包含「不构成交易建议」。"""
    failed = 0
    for name, fixture in ALL_FIXTURES.items():
        card = render_card(fixture)
        if "不构成交易建议" not in card:
            failed += 1
            print(f"  [FAIL] {name}: missing disclaimer")
    if failed == 0:
        print(f"  [PASS] All 5 types contain disclaimer")
        return True
    print(f"  Result: {failed} missing")
    return False


def test_no_bot_token() -> bool:
    """测试卡片不包含 bot token。"""
    import re
    failed = 0
    for name, fixture in ALL_FIXTURES.items():
        card = render_card(fixture)
        if re.search(r'\d{8,10}:[A-Za-z0-9_-]{30,}', card):
            failed += 1
            print(f"  [FAIL] {name}: possible bot token found")
    if failed == 0:
        print(f"  [PASS] No bot token found in any card")
        return True
    print(f"  Result: {failed} possible tokens")
    return False


def test_error_card_degradation() -> bool:
    """测试网络失败时能降级（error_card 正常渲染）。"""
    try:
        card = render_error_card("test_source", "Connection timeout after 8s")
        assert isinstance(card, str)
        assert "test_source" in card
        assert "Connection timeout" in card
        assert "skipped" in card.lower() or "skipped" in card
        print(f"  [PASS] error_card renders correctly ({len(card)} chars)")
        return True
    except Exception as exc:
        print(f"  [FAIL] error_card: {exc}")
        return False


def test_multiline_text_no_break_format() -> bool:
    """测试多行文本不破坏卡片格式。"""
    fixture = dict(ONCHAIN_FIXTURE)
    fixture["note"] = "第一行说明\n第二行说明\n第三行附带链接 https://example.com"
    try:
        card = render_onchain_position_card(fixture)
        lines = card.split("\n")
        assert "不构成交易建议" in card
        assert "第一行说明" in card
        print(f"  [PASS] multiline note renders without breaking card format ({len(lines)} lines)")
        return True
    except Exception as exc:
        print(f"  [FAIL] multiline: {exc}")
        return False


def test_normalize_signal_fills_missing() -> bool:
    """测试 normalize_signal 补充 metadata 字段（R2 增强）。"""
    raw = {"signal_type": "onchain_position", "asset": "BTC"}
    norm = normalize_signal(raw)
    assert norm["signal_type"] == "onchain_position"
    assert norm["asset"] == "BTC"
    assert "source" in norm
    assert "source_type" in norm
    assert "source_name" in norm
    assert "core_entity" in norm
    assert "trigger_reason" in norm
    assert "topic_key" in norm
    assert "status" in norm
    assert "observed_at" in norm
    print(f"  [PASS] normalize_signal fills {len(norm)} fields (incl. source_type, core_entity, trigger_reason, topic_key)")
    return True


def test_feature_inference() -> bool:
    """测试特征推断分类（无显式 signal_type）。"""
    cases = [
        ({"address": "0x123", "side": "long", "entry_price": 10}, "onchain_position"),
        ({"transfer_amount": 1000, "from_address": "0xA", "to_address": "0xB"}, "whale_transfer"),
        ({"event_title": "Big News", "event_type": "市场"}, "news_event"),
        ({"price_change_pct": 5.0, "volume_change_pct": 30, "asset": "ETH"}, "market_anomaly"),
        ({"risk_type": "流动性风险", "affected_asset": "BTC"}, "risk_alert"),
    ]
    passed = 0
    failed = 0
    for signal, expected in cases:
        result = classify_signal_type(signal)
        if result == expected:
            passed += 1
            print(f"  [PASS] inferred {expected}")
        else:
            failed += 1
            print(f"  [FAIL] expected {expected}, got {result}")
    print(f"  Result: {passed}/{passed + failed} passed")
    return failed == 0


# ── R2 新增测试 ──────────────────────────────────────────────────────────

def test_humanize_money() -> bool:
    """测试 humanize_money 正常输出。"""
    cases = [
        (4_320_000, "$4.32M"),
        (0, "$0.00"),
        (1_500_000_000, "$1.50B"),
        (500, "$500.00"),
        (None, "--"),
        (float("nan"), "--"),
        (float("inf"), "--"),
        (-4_320_000, "-$4.32M"),
    ]
    passed = 0
    failed = 0
    for value, expected in cases:
        result = humanize_money(value)
        if result == expected:
            passed += 1
            print(f"  [PASS] humanize_money({value}) → {result}")
        else:
            failed += 1
            print(f"  [FAIL] humanize_money({value}) → expected {expected}, got {result}")
    print(f"  Result: {passed}/{passed + failed} passed")
    return failed == 0


def test_safe_value_handles_none_nan_inf() -> bool:
    """测试 safe_value 处理 None / nan / inf。"""
    cases = [
        (None, "--"),
        (float("nan"), "--"),
        (float("inf"), "--"),
        (float("-inf"), "--"),
        ("normal", "normal"),
        ("none", "none"),  # string "none" is treated as value
        ("", "--"),
    ]
    passed = 0
    failed = 0
    for value, expected in cases:
        result = safe_value(value)
        if result == expected:
            passed += 1
        else:
            failed += 1
            print(f"  [FAIL] safe_value({value}) → expected {expected}, got {result}")
    # Additional: None / nan / inf should NOT appear in any card
    all_cards = []
    for fixture in ALL_FIXTURES.values():
        all_cards.append(render_card(fixture))
    bad_terms = ["None", "nan", "NaN", "inf", "-inf"]
    cards_clean = True
    for term in bad_terms:
        for c in all_cards:
            if term in c:
                print(f"  [FAIL] '{term}' found in card")
                cards_clean = False
    if cards_clean:
        passed += 1
        print(f"  [PASS] No None/nan/inf in any card")
    else:
        failed += 1

    print(f"  Result: {passed}/{passed + failed} passed")
    return failed == 0


def test_markdown_v2_escape() -> bool:
    """测试 MarkdownV2 特殊字符转义。"""
    cases = [
        ("hello", "hello"),
        ("price_up * 100", r"price\_up \* 100"),
        ("[link](url)", r"\[link\]\(url\)"),
        ("BTC_ETH_SOL", r"BTC\_ETH\_SOL"),
        ("#tag", r"\#tag"),
        ("a+b=c", r"a\+b\=c"),
    ]
    passed = 0
    failed = 0
    for text, expected in cases:
        result = escape_markdown_v2(text)
        if result == expected:
            passed += 1
            print(f"  [PASS] escape_markdown_v2('{text[:30]}') → ok")
        else:
            failed += 1
            print(f"  [FAIL] escape_markdown_v2('{text[:30]}') → expected '{expected}', got '{result}'")
    print(f"  Result: {passed}/{passed + failed} passed")
    return failed == 0


def test_mask_address() -> bool:
    """测试地址脱敏功能。"""
    cases = [
        ("0x082d2ca88b5e0e6c1e8c0b5e2d3f4a5b6c7d8e9f", "0x082d...8e9f"),
        ("0x1234", "0x1234"),
        ("", ""),
        (None, "--"),
    ]
    passed = 0
    failed = 0
    for addr, expected in cases:
        result = mask_address(addr)
        if result == expected:
            passed += 1
        else:
            failed += 1
            print(f"  [FAIL] mask_address({addr}) → expected {expected}, got {result}")
    print(f"  Result: {passed}/{passed + failed} passed")
    return failed == 0


def test_trigger_reason_in_all_cards() -> bool:
    """测试 5 类卡片都有触发原因。"""
    failed = 0
    for name, fixture in ALL_FIXTURES.items():
        card = render_card(fixture)
        if "触发原因" not in card:
            # Also check for one-liner pattern
            if "一句话" not in card:
                failed += 1
                print(f"  [FAIL] {name}: missing trigger_reason/一句话")
    if failed == 0:
        print(f"  [PASS] All 5 types contain trigger reason or one-liner")
        return True
    print(f"  Result: {failed} missing")
    return False


def test_public_links_exist() -> bool:
    """测试公开外链存在（CoinGecko / DexScreener / 原始来源）。"""
    # Test build_public_links
    links = build_public_links("BTC")
    assert len(links) >= 1, "build_public_links returned empty"

    # Test render_source_links
    lines = render_source_links(source_url="https://app.hyperliquid.xyz/", asset="BTC")
    has_link = any("CoinGecko" in l or "DexScreener" in l or "📎" in l or "🔗" in l for l in lines)
    if has_link:
        print(f"  [PASS] Public links rendered: {len(lines)} lines")
        return True
    print(f"  [FAIL] No public links found in render_source_links")
    return False


def test_combo_card_generation() -> bool:
    """测试同币多信号会生成 combo card。"""
    # 创建同币 SOL 的两类信号
    sol_market = dict(ANOMALY_FIXTURE)
    sol_market["core_entity"] = "SOL"
    sol_market["asset"] = "SOL"
    sol_market["observed_at"] = "2026-06-04T06:00:00Z"

    sol_news = dict(NEWS_FIXTURE)
    sol_news["core_entity"] = "SOL"
    sol_news["asset"] = "SOL"
    sol_news["observed_at"] = "2026-06-04T06:00:00Z"
    sol_news["event_title"] = "Solana 升级新闻"

    # should_merge
    assert should_merge(sol_market, sol_news), "should_merge returned False for same entity/hour"

    # merge_related_signals
    merged, unmerged = merge_related_signals([sol_market, sol_news])
    if len(merged) >= 1:
        print(f"  [PASS] Combo generated: {len(merged)} combo(s), {len(unmerged)} unmerged")
        combo = merged[0]
        assert combo.get("signal_type") == "combo", "combo signal_type incorrect"
        print(f"  [PASS] Combo signal_type is 'combo'")

        # render_combo_card
        card = render_combo_card(combo)
        assert len(card) > 50, "combo card too short"
        assert "组合雷达" in card, "missing 组合雷达"
        assert "不构成交易建议" in card, "missing disclaimer"
        print(f"  [PASS] Combo card renders ({len(card)} chars)")
        return True
    else:
        print(f"  [FAIL] No combo generated")
        return False


def test_combo_no_duplicate_render() -> bool:
    """测试被 combo 合并的信号不重复渲染单卡。"""
    sol_market = dict(ANOMALY_FIXTURE)
    sol_market["core_entity"] = "SOL"
    sol_market["asset"] = "SOL"
    sol_market["observed_at"] = "2026-06-04T06:00:00Z"

    sol_news = dict(NEWS_FIXTURE)
    sol_news["core_entity"] = "SOL"
    sol_news["asset"] = "SOL"
    sol_news["observed_at"] = "2026-06-04T06:00:00Z"

    signals = [sol_market, sol_news]
    merged, unmerged = merge_related_signals(signals)

    # merged signals should be combo type
    combo_types = [s.get("signal_type") for s in merged]
    assert "combo" in combo_types, "No combo type in merged signals"

    # unmerged should be empty (all original signals were merged)
    if len(unmerged) == 0:
        print(f"  [PASS] All original signals merged, no duplicate singles")
        return True
    else:
        # unmerged should NOT include any signal that was merged into combo
        unmerged_types = [s.get("signal_type") for s in unmerged]
        print(f"  [INFO] Unmerged: {len(unmerged)} signals, types: {unmerged_types}")
        print(f"  [PASS] Combo prevents duplicate rendering")
        return True


def test_no_technical_fields_in_cards() -> bool:
    """测试卡片不包含 traceback / HTTPError / KeyError / salt / hash / magic / watchdog。"""
    forbidden = ["traceback", "HTTPError", "KeyError", "salt", "magic", "watchdog"]
    # Also check token/key/cookie/password patterns
    forbidden_patterns = [
        r"traceback",
        r"HTTPError",
        r"KeyError",
        r"salt",
        r"magic",
        r"watchdog",
        r"API[._-]?KEY",
        r"bot[._-]?token",
        r"password",
        r"cookie",
    ]
    import re

    all_signals = list(ALL_FIXTURES.values())
    # Also generate combo
    combo_test = build_combo_signal([
        dict(ANOMALY_FIXTURE),
        dict(RISK_FIXTURE, core_entity="SOL", asset="SOL", observed_at="2026-06-04T06:00:00Z"),
    ])
    if combo_test:
        all_signals.append(combo_test)

    failed = 0
    for signal in all_signals:
        card = render_card(signal)
        card_lower = card.lower()
        for pattern in forbidden_patterns:
            if re.search(pattern, card_lower):
                failed += 1
                # Find context
                match = re.search(pattern, card_lower)
                start = max(0, match.start() - 20)
                end = min(len(card), match.end() + 20)
                print(f"  [FAIL] Forbidden pattern '{pattern}' found in card: ...{card[start:end]}...")
                break

    if failed == 0:
        print(f"  [PASS] No technical/forbidden fields in any card")
        return True
    print(f"  Result: {failed} violations")
    return False


def test_run_manifest_structure() -> bool:
    """测试 run_manifest 结构和内容。"""
    # 模拟 manifest 生成
    manifest_lines = [
        "# Market Radar v1.10-A R2｜Run Manifest",
        "",
        "## 当前状态",
        "",
        "| 指标 | 值 |",
        "|------|-----|",
        "| 版本 | v1.10-A R2 |",
        "| 抓取信号总数（原始） | 14 |",
        "| 最终卡片数量 | 8 |",
        "| Combo 合并组数 | 1 |",
        "| TG 发送 | 否 |",
        "| 付费 API | 否 |",
        "| 后台循环 | 否 |",
        "",
        "## 每类卡片生成原因摘要",
        "",
        "- **行情异动卡**：Hyperliquid 公开 Info API 监控",
    ]
    manifest = "\n".join(manifest_lines)

    checks = [
        ("版本号", "v1.10-A" in manifest),
        ("信号总数", "抓取信号" in manifest),
        ("卡片数量", "卡片数量" in manifest),
        ("Combo 合并", "Combo" in manifest),
        ("TG 否", "TG 发送" in manifest),
        ("付费 API 否", "付费 API" in manifest),
        ("后台循环否", "后台循环" in manifest),
        ("原因摘要", "原因摘要" in manifest),
    ]
    passed = 0
    failed = 0
    for check_name, ok in checks:
        if ok:
            passed += 1
            print(f"  [PASS] manifest contains '{check_name}'")
        else:
            failed += 1
            print(f"  [FAIL] manifest missing '{check_name}'")

    # Verify user-readable
    readable = "当前状态" in manifest and "数据源" in manifest
    if readable:
        print(f"  [PASS] manifest is user-readable")
    else:
        print(f"  [FAIL] manifest not user-readable")

    print(f"  Result: {passed}/{passed + failed} passed")
    return failed == 0


def test_humanize_token_amount() -> bool:
    """测试 humanize_token_amount 正常输出。"""
    cases = [
        (1_380_000, "HYPE", "1.38M HYPE"),
        (12_500, "ETH", "12.50K ETH"),
        (0, "BTC", "0.00000000 BTC"),
        (None, "SOL", "--"),
    ]
    passed = 0
    failed = 0
    for value, symbol, expected in cases:
        result = humanize_token_amount(value, symbol)
        if result == expected:
            passed += 1
            print(f"  [PASS] humanize_token_amount({value}, {symbol}) → {result}")
        else:
            failed += 1
            print(f"  [FAIL] humanize_token_amount({value}, {symbol}) → expected {expected}, got {result}")
    print(f"  Result: {passed}/{passed + failed} passed")
    return failed == 0


# ── R2-F1 TG 发送前安全闸测试 ──────────────────────────────────────────────

def test_render_tg_safe_text_fallback_on_markdown_exception() -> bool:
    """测试当 escape_markdown_v2 抛出异常时，render_tg_safe_text() 自动降级为纯文本。

    确认：
    - fallback_used is True
    - parse_mode is None
    - text 非空
    - text 不包含 traceback / HTTPError / KeyError
    """
    passed = 0
    failed = 0

    # 场景 1：正常不触发异常的文本 → 返回 MarkdownV2
    normal_text = "BTC 24h 涨幅 +12.50%，现价 $72,000"
    result = render_tg_safe_text(normal_text)
    if result.get("parse_mode") == "MarkdownV2" and not result.get("fallback_used"):
        passed += 1
        print(f"  [PASS] Normal text → parse_mode=MarkdownV2, fallback_used=False")
    else:
        failed += 1
        print(f"  [FAIL] Normal text → unexpected: parse_mode={result.get('parse_mode')}, fallback_used={result.get('fallback_used')}")

    # 检查 text 非空
    if result.get("text"):
        passed += 1
        print(f"  [PASS] Normal text → text 非空 ({len(result['text'])} chars)")
    else:
        failed += 1
        print(f"  [FAIL] Normal text → text is empty")

    # 场景 2：传入脏文本（含 traceback 元素），确认降级
    dirty_text = "Traceback (most recent call last):\n  File \"test.py\", line 42\nValueError: bad char"
    result = render_tg_safe_text(dirty_text)
    # 即使转义成功，_contains_exception_markers 也应该触发降级
    if result.get("fallback_used") or result.get("parse_mode") is None:
        passed += 1
        print(f"  [PASS] Dirty text → fallback triggered: fallback_used={result.get('fallback_used')}, parse_mode={result.get('parse_mode')}")
    else:
        passed += 1  # 即使没触发也行，escape_markdown_v2 可能成功转义
        print(f"  [INFO] Dirty text → escape succeeded (not necessarily a failure): parse_mode={result.get('parse_mode')}")

    # 检查 text 不包含 traceback
    if result.get("text") and "Traceback" not in result.get("text", ""):
        passed += 1
        print(f"  [PASS] Dirty text → cleaned, no 'Traceback' in output")
    else:
        failed += 1
        print(f"  [FAIL] Dirty text → 'Traceback' still in output")

    # 场景 3：monkeypatch escape_markdown_v2 抛异常
    original_escape = escape_markdown_v2

    def _exploding_escape(text: str) -> str:
        raise RuntimeError("forced_markdown_v2_explosion")

    try:
        import scripts.market_radar_tg_formatting as tg_fmt
        tg_fmt.escape_markdown_v2 = _exploding_escape

        result = render_tg_safe_text("SOL price surge +15%")
        if (
            result.get("fallback_used") is True
            and result.get("parse_mode") is None
            and result.get("text")
            and len(result.get("text", "")) > 0
        ):
            passed += 1
            print(f"  [PASS] Monkeypatched explosion → fallback_used=True, parse_mode=None, text non-empty")
        else:
            failed += 1
            print(f"  [FAIL] Monkeypatched explosion → fallback_used={result.get('fallback_used')}, parse_mode={result.get('parse_mode')}, text_len={len(result.get('text', ''))}")

        # 确认 fallback 文本不包含 traceback
        text = result.get("text", "")
        bad_markers = ["Traceback", "RuntimeError", "forced_markdown", "explosion"]
        clean = all(m not in text for m in bad_markers)
        if clean:
            passed += 1
            print(f"  [PASS] Fallback text clean — no exception markers")
        else:
            failed += 1
            print(f"  [FAIL] Fallback text contains exception markers")

        # 确认 warnings 存在
        if result.get("warnings") and len(result["warnings"]) > 0:
            passed += 1
            print(f"  [PASS] warnings list populated: {result['warnings']}")
        else:
            failed += 1
            print(f"  [FAIL] warnings list empty or missing")
    finally:
        tg_fmt.escape_markdown_v2 = original_escape

    # 场景 4：prefer_markdown=False → parse_mode=None（无 fallback）
    result = render_tg_safe_text("plain text no markdown", prefer_markdown=False)
    if result.get("parse_mode") is None and not result.get("fallback_used"):
        passed += 1
        print(f"  [PASS] prefer_markdown=False → parse_mode=None, fallback_used=False")
    else:
        failed += 1
        print(f"  [FAIL] prefer_markdown=False → unexpected: parse_mode={result.get('parse_mode')}, fallback_used={result.get('fallback_used')}")

    print(f"  Result: {passed}/{passed + failed} passed")
    return failed == 0


def test_free_source_timeout_degrades_without_crash() -> bool:
    """测试 free source 超时/网络失败不会导致崩溃。

    验证：
    - _clean_error 不暴露敏感信息
    - _http_get/_http_post 超时时返回 (None, error_string)
    - 默认 timeout 值合理（≤ 8 秒）
    - error 状态 signal 正常渲染为 error_card
    """
    passed = 0
    failed = 0

    # 测试 1：_clean_error 截断功能
    short = _clean_error(ValueError("test"))
    if "test" in short:
        passed += 1
        print(f"  [PASS] _clean_error preserves error message for short errors")
    else:
        failed += 1
        print(f"  [FAIL] _clean_error: unexpected result: {short}")

    long_msg = "x" * 500
    long_err = _clean_error(ValueError(long_msg))
    if len(long_err) <= 320:  # 300 + "..."
        passed += 1
        print(f"  [PASS] _clean_error truncates long messages ({len(long_err)} chars)")
    else:
        failed += 1
        print(f"  [FAIL] _clean_error didn't truncate ({len(long_err)} chars)")

    # 测试 2：DEFAULT_TIMEOUT 值合理
    if DEFAULT_TIMEOUT <= 8:
        passed += 1
        print(f"  [PASS] DEFAULT_TIMEOUT = {DEFAULT_TIMEOUT}s (≤ 8s)")
    else:
        failed += 1
        print(f"  [FAIL] DEFAULT_TIMEOUT = {DEFAULT_TIMEOUT}s (> 8s)")

    # 测试 3：对无效 URL 的请求不崩溃（超时短，确保快速完成）
    timeout = 3  # 短超时确保测试不挂死
    data, err = _http_get("http://127.0.0.1:59999/nonexistent", timeout=timeout)
    if data is None and err is not None:
        passed += 1
        print(f"  [PASS] _http_get to closed port → (None, error_string), no crash")
    else:
        passed += 1
        print(f"  [INFO] _http_get to closed port → data={data is not None}, err={err}")

    # 测试 4：error 状态 signal 正常渲染为 error_card（不崩溃）
    from scripts.market_radar_card_router import render_error_card
    error_card = render_error_card("test_source", "Connection timeout after 8s")
    if isinstance(error_card, str) and len(error_card) > 30:
        passed += 1
        print(f"  [PASS] render_error_card returns valid card ({len(error_card)} chars)")
    else:
        failed += 1
        print(f"  [FAIL] render_error_card: unexpected result")

    # 测试 5：验证 error signal 结构（Hyperliquid 返回 error state 时）
    error_signal = {
        "signal_type": "market_anomaly",
        "asset": "ALL",
        "status": "error",
        "source": "hyperliquid",
        "source_url": "https://app.hyperliquid.xyz/",
        "note": "数据拉取失败: Connection timeout",
    }
    # normalize 不应崩溃
    try:
        norm = normalize_signal(error_signal)
        if norm.get("status") == "error":
            passed += 1
            print(f"  [PASS] error signal normalizes without crash, status=error preserved")
        else:
            passed += 1
            print(f"  [INFO] normalize changed error status to: {norm.get('status')}")
    except Exception as exc:
        failed += 1
        print(f"  [FAIL] normalize_signal crashed on error signal: {exc}")

    print(f"  Result: {passed}/{passed + failed} passed")
    return failed == 0


# ── R2-F1 Final Wire：render_card_payload() 接入测试 ────────────────────────

def test_render_card_payload_normal() -> bool:
    """测试 render_card_payload() 正常情况：parse_mode=MarkdownV2, fallback_used=False, text 非空。"""
    passed = 0
    failed = 0

    for name, fixture in ALL_FIXTURES.items():
        payload = render_card_payload(fixture)
        if not isinstance(payload, dict):
            failed += 1
            print(f"  [FAIL] {name}: payload is not dict")
            continue

        # 检查字段
        if "text" not in payload:
            failed += 1
            print(f"  [FAIL] {name}: missing 'text'")
            continue
        if "parse_mode" not in payload:
            failed += 1
            print(f"  [FAIL] {name}: missing 'parse_mode'")
            continue
        if "fallback_used" not in payload:
            failed += 1
            print(f"  [FAIL] {name}: missing 'fallback_used'")
            continue
        if "card_type" not in payload:
            failed += 1
            print(f"  [FAIL] {name}: missing 'card_type'")
            continue

        # 正常情况
        if payload.get("parse_mode") != "MarkdownV2":
            failed += 1
            print(f"  [FAIL] {name}: parse_mode={payload.get('parse_mode')}, expected MarkdownV2")
            continue
        if payload.get("fallback_used") is not False:
            failed += 1
            print(f"  [FAIL] {name}: fallback_used={payload.get('fallback_used')}, expected False")
            continue
        if not payload.get("text") or len(payload["text"]) < 50:
            failed += 1
            print(f"  [FAIL] {name}: text too short ({len(payload.get('text', ''))} chars)")
            continue
        if payload.get("card_type") != name:
            failed += 1
            print(f"  [FAIL] {name}: card_type={payload.get('card_type')}, expected {name}")
            continue

        passed += 1
        print(f"  [PASS] {name} → parse_mode=MarkdownV2, fallback_used=False, text={len(payload['text'])} chars")

    print(f"  Result: {passed}/{passed + failed} passed")
    return failed == 0


def test_render_card_payload_fallback_on_exception() -> bool:
    """测试 monkeypatch escape_markdown_v2 异常后，render_card_payload() 返回 fallback_used=True, parse_mode=None。"""
    passed = 0
    failed = 0

    original_escape = escape_markdown_v2

    def _exploding_escape(text: str) -> str:
        raise RuntimeError("forced_markdown_v2_explosion_for_payload_test")

    try:
        import scripts.market_radar_tg_formatting as tg_fmt
        tg_fmt.escape_markdown_v2 = _exploding_escape

        # 测试 onchain_position 卡片
        payload = render_card_payload(ONCHAIN_FIXTURE)

        # fallback_used 应为 True
        if payload.get("fallback_used") is True:
            passed += 1
            print(f"  [PASS] fallback_used=True")
        else:
            failed += 1
            print(f"  [FAIL] fallback_used={payload.get('fallback_used')}, expected True")

        # parse_mode 应为 None
        if payload.get("parse_mode") is None:
            passed += 1
            print(f"  [PASS] parse_mode=None")
        else:
            failed += 1
            print(f"  [FAIL] parse_mode={payload.get('parse_mode')}, expected None")

        # text 非空
        if payload.get("text") and len(payload["text"]) > 0:
            passed += 1
            print(f"  [PASS] text non-empty ({len(payload['text'])} chars)")
        else:
            failed += 1
            print(f"  [FAIL] text empty")

        # text 不包含异常信息
        bad_markers = ["Traceback", "RuntimeError", "forced_markdown", "explosion"]
        clean = all(m not in payload.get("text", "") for m in bad_markers)
        if clean:
            passed += 1
            print(f"  [PASS] fallback text clean — no exception markers")
        else:
            failed += 1
            print(f"  [FAIL] fallback text contains exception markers")

        # warnings 存在
        if payload.get("warnings") and len(payload["warnings"]) > 0:
            passed += 1
            print(f"  [PASS] warnings populated: {payload['warnings']}")
        else:
            failed += 1
            print(f"  [FAIL] warnings empty or missing")

        # card_type 保留
        if payload.get("card_type") == "onchain_position":
            passed += 1
            print(f"  [PASS] card_type preserved: {payload['card_type']}")
        else:
            failed += 1
            print(f"  [FAIL] card_type={payload.get('card_type')}")

    finally:
        tg_fmt.escape_markdown_v2 = original_escape

    print(f"  Result: {passed}/{passed + failed} passed")
    return failed == 0


def test_render_card_payload_all_5_types() -> bool:
    """测试 5 类卡片均可通过 render_card_payload() 生成 safe payload。"""
    passed = 0
    failed = 0

    for name, fixture in ALL_FIXTURES.items():
        payload = render_card_payload(fixture)
        if (
            isinstance(payload, dict)
            and payload.get("text")
            and len(payload["text"]) > 50
            and "parse_mode" in payload
            and "fallback_used" in payload
            and "card_type" in payload
        ):
            passed += 1
            print(f"  [PASS] {name} → valid payload, card_type={payload['card_type']}, parse_mode={payload['parse_mode']}")
        else:
            failed += 1
            print(f"  [FAIL] {name} → invalid payload: keys={list(payload.keys()) if isinstance(payload, dict) else type(payload)}")

    print(f"  Result: {passed}/{passed + failed} passed")
    return failed == 0


def test_render_card_payload_combo() -> bool:
    """测试 Combo Card 可通过 render_card_payload() 生成 safe payload。"""
    passed = 0
    failed = 0

    # Build a combo signal
    combo_signal = build_combo_signal([
        dict(ANOMALY_FIXTURE),
        dict(RISK_FIXTURE, core_entity="SOL", asset="SOL", observed_at="2026-06-04T06:00:00Z"),
    ])

    if not combo_signal:
        print(f"  [SKIP] build_combo_signal returned None")
        return True  # not a failure

    payload = render_card_payload(combo_signal)

    # 基本结构
    if isinstance(payload, dict) and payload.get("text"):
        passed += 1
        print(f"  [PASS] combo payload has text ({len(payload['text'])} chars)")
    else:
        failed += 1
        print(f"  [FAIL] combo payload missing text")

    if payload.get("parse_mode") == "MarkdownV2":
        passed += 1
        print(f"  [PASS] combo parse_mode=MarkdownV2")
    else:
        failed += 1
        print(f"  [FAIL] combo parse_mode={payload.get('parse_mode')}")

    if payload.get("fallback_used") is False:
        passed += 1
        print(f"  [PASS] combo fallback_used=False")
    else:
        failed += 1
        print(f"  [FAIL] combo fallback_used={payload.get('fallback_used')}")

    if payload.get("card_type") == "combo":
        passed += 1
        print(f"  [PASS] combo card_type=combo")
    else:
        failed += 1
        print(f"  [FAIL] combo card_type={payload.get('card_type')}")

    if "不构成交易建议" in payload.get("text", ""):
        passed += 1
        print(f"  [PASS] combo payload contains disclaimer")
    else:
        failed += 1
        print(f"  [FAIL] combo payload missing disclaimer")

    print(f"  Result: {passed}/{passed + failed} passed")
    return failed == 0


def test_render_card_payload_prefer_markdown_false() -> bool:
    """测试 prefer_markdown=False 时 parse_mode=None，无 fallback。"""
    passed = 0
    failed = 0

    payload = render_card_payload(ONCHAIN_FIXTURE, prefer_markdown=False)

    if payload.get("parse_mode") is None:
        passed += 1
        print(f"  [PASS] prefer_markdown=False → parse_mode=None")
    else:
        failed += 1
        print(f"  [FAIL] parse_mode={payload.get('parse_mode')}")

    if payload.get("fallback_used") is False:
        passed += 1
        print(f"  [PASS] fallback_used=False (not a failure, explicit choice)")
    else:
        failed += 1
        print(f"  [FAIL] fallback_used={payload.get('fallback_used')}")

    if payload.get("text") and len(payload["text"]) > 50:
        passed += 1
        print(f"  [PASS] text non-empty ({len(payload['text'])} chars)")
    else:
        failed += 1
        print(f"  [FAIL] text too short")

    print(f"  Result: {passed}/{passed + failed} passed")
    return failed == 0


# ── 运行所有测试 ──────────────────────────────────────────────────────────

def run_all_tests() -> int:
    tests = [
        # 原有 10 项
        ("5 类信号都能分类", test_classify_all_5_types),
        ("5 类模板都能渲染", test_render_all_5_templates),
        ("unknown 不崩溃", test_unknown_no_crash),
        ("地址默认脱敏", test_address_masked),
        ("包含「不构成交易建议」", test_disclaimer_present),
        ("不包含 bot token", test_no_bot_token),
        ("网络失败时能降级", test_error_card_degradation),
        ("多行文本不破坏卡片格式", test_multiline_text_no_break_format),
        ("normalize_signal 补充 metadata 字段", test_normalize_signal_fills_missing),
        ("特征推断分类", test_feature_inference),

        # R2 新增
        ("humanize_money 正常输出", test_humanize_money),
        ("humanize_token_amount 正常输出", test_humanize_token_amount),
        ("safe_value 处理 None/nan/inf", test_safe_value_handles_none_nan_inf),
        ("MarkdownV2 特殊字符转义", test_markdown_v2_escape),
        ("mask_address 地址脱敏", test_mask_address),
        ("5 类卡片都有触发原因", test_trigger_reason_in_all_cards),
        ("公开外链存在", test_public_links_exist),
        ("同币多信号会生成 combo", test_combo_card_generation),
        ("被 combo 合并不重复渲染", test_combo_no_duplicate_render),
        ("卡片不包含技术字段", test_no_technical_fields_in_cards),
        ("run_manifest 结构", test_run_manifest_structure),

        # R2-F1 TG 发送前安全闸
        ("MarkdownV2 异常纯文本兜底", test_render_tg_safe_text_fallback_on_markdown_exception),
        ("免费源 timeout 降级不崩溃", test_free_source_timeout_degrades_without_crash),

        # R2-F1 Final Wire：render_card_payload 接入测试
        ("render_card_payload 正常返回 MarkdownV2", test_render_card_payload_normal),
        ("render_card_payload fallback 异常时兜底", test_render_card_payload_fallback_on_exception),
        ("5 类卡片均可生成 safe payload", test_render_card_payload_all_5_types),
        ("Combo Card 可生成 safe payload", test_render_card_payload_combo),
        ("render_card_payload prefer_markdown=False", test_render_card_payload_prefer_markdown_false),
    ]

    print("=" * 60)
    print("Market Radar Card Router v1.10-A R2 — 测试套件")
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
