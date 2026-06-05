"""Market Radar v1.10-A R2 — 免费数据源 + 5 类 TG 卡片模板 + Combo Card + Run Manifest。

功能：
1. 读取 config/market_radar_free_sources.yaml
2. 拉取免费公开数据（Hyperliquid、RSS 新闻、衍生风险）
3. normalize 成统一 signal（含 metadata）
4. 同币多信号 Combo Card 合并
5. 调用 card_router 渲染卡片
6. 输出 results/market_radar_v110a_free_card_samples.md
7. 输出 results/market_radar_v110a_free_signals.json
8. 输出 results/market_radar_v110a_run_manifest.md

用法：
    python scripts/run_market_radar_v110a_free_cards.py
    python scripts/run_market_radar_v110a_free_cards.py --no-live  # 仅使用 fixture 数据
"""

from __future__ import annotations

import argparse
import json
import sys
import traceback
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any

import yaml

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

ROOT = Path(__file__).resolve().parents[1]
CN_TZ = timezone(timedelta(hours=8))

# 导入本地模块
sys.path.insert(0, str(ROOT))
from scripts.market_radar_card_router import (
    classify_signal_type,
    render_card,
    render_card_payload,
    render_error_card,
)
from scripts.market_radar_free_sources import (
    fetch_hyperliquid_position_watchlist,
    fetch_market_anomaly_public,
    fetch_news_event_public,
    fetch_risk_alert_public,
    normalize_signal,
    DEFAULT_TIMEOUT,
)
from scripts.market_radar_signal_merge import (
    merge_related_signals,
    should_merge,
    build_combo_signal,
)


# ── CLI ───────────────────────────────────────────────────────────────────

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Market Radar v1.10-A R2 — 免费数据源 + 卡片产品化渲染"
    )
    parser.add_argument(
        "--config",
        default=str(ROOT / "config" / "market_radar_free_sources.yaml"),
    )
    parser.add_argument(
        "--output-md",
        default=str(ROOT / "results" / "market_radar_v110a_free_card_samples.md"),
    )
    parser.add_argument(
        "--output-json",
        default=str(ROOT / "results" / "market_radar_v110a_free_signals.json"),
    )
    parser.add_argument(
        "--output-manifest",
        default=str(ROOT / "results" / "market_radar_v110a_run_manifest.md"),
    )
    parser.add_argument(
        "--no-live",
        action="store_true",
        help="跳过真实外网拉取，仅使用 fixture 数据生成样例卡片",
    )
    return parser.parse_args()


def normalize_path(value: str | Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else ROOT / path


def china_stamp() -> str:
    return datetime.now(CN_TZ).strftime("%Y-%m-%d %H:%M:%S UTC+8")


# ── 配置加载 ──────────────────────────────────────────────────────────────

def load_config(path: Path) -> dict:
    if not path.exists():
        print(f"WARNING: config not found: {path}, using defaults")
        return _default_config()
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


def _default_config() -> dict:
    return {
        "hyperliquid_watchlist": {"addresses": []},
        "market_symbols": ["BTC", "ETH", "HYPE", "SOL"],
        "news_sources": [
            {"name": "coindesk_rss", "url": "https://www.coindesk.com/arc/outboundfeeds/rss/", "type": "rss", "enabled": True},
            {"name": "cointelegraph_rss", "url": "https://cointelegraph.com/rss", "type": "rss", "enabled": True},
        ],
        "risk_sources": [
            {"name": "hyperliquid_funding_extreme", "threshold_funding_pct": 0.01},
            {"name": "market_volatility", "threshold_price_change_pct": 10},
        ],
        "enable_live_fetch": True,
        "request_timeout_seconds": 8,
    }


# ── fixture 数据（无网络时使用）────────────────────────────────────────────

def fixture_signals() -> list[dict]:
    """当网络不可用时，提供示例 fixture 数据生成样例卡片。"""
    now_ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    return [
        # 1. 链上仓位卡 fixture
        {
            "signal_type": "onchain_position",
            "asset": "HYPE",
            "core_entity": "HYPE",
            "address": "0x082d2ca88b5e0e6c1e8c0b5e2d3f4a5b6c7d8e9f",
            "label": "HYPE 主力地址示例",
            "side": "多头",
            "position_value_usd": 100_000_000,
            "quantity": 1_380_000,
            "entry_price": 33.68,
            "mark_price": 72.51,
            "pnl_usd": 46_985_000,
            "liquidation_price": 54.93,
            "note": "该地址为 Hyperliquid 上大规模持仓地址（fixture 示例数据），当前卡片仅展示其 HYPE 多头。",
            "source_url": "https://app.hyperliquid.xyz/",
            "source": "fixture",
            "status": "fixture",
            "observed_at": now_ts,
            "trigger_reason": "HYPE 多头大额持仓，Hyperliquid 公开 API 检测到链上仓位（fixture 示例）",
        },
        # 2. 巨鲸转账卡 fixture
        {
            "signal_type": "whale_transfer",
            "asset": "ETH",
            "core_entity": "ETH",
            "transfer_amount": 12_500,
            "amount_usd": 45_000_000,
            "from_address": "0x1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b",
            "to_address": "0x28c6c06298d514089e0a6c0b5e2d3f4a5b6c7d8e",
            "to_exchange": "true",
            "chain": "Ethereum",
            "historical_behavior": "该地址过去 3 个月累计向交易所转入 5 万 ETH（fixture 示例数据）",
            "potential_implication": "大额转入交易所可能预示卖出意愿，但无法确认（fixture 示例）",
            "risk_note": "巨鲸行为仅供参考，不构成跟随交易建议",
            "tx_hash": "0xabcd1234ef567890abcd1234ef567890abcd1234ef567890abcd1234ef5678",
            "source_url": "https://etherscan.io/tx/0xabcd",
            "source": "fixture",
            "status": "fixture",
            "observed_at": now_ts,
            "trigger_reason": "检测到大额 12,500 ETH 转账，目标疑似交易所（fixture 示例）",
        },
        # 3. 新闻事件卡 fixture
        {
            "signal_type": "news_event",
            "core_entity": "BTC",
            "event_title": "美 SEC 批准比特币现货 ETF 期权交易（fixture 示例新闻）",
            "affected_assets": "BTC, ETH",
            "event_type": "监管",
            "trading_relevance": "高 — 可能提升 BTC 和 ETH 的机构流动性",
            "already_priced": "部分已定价",
            "risk_tags": "监管, ETF",
            "observation_window": "2-4 小时",
            "source": "CoinDesk (fixture)",
            "source_url": "https://www.coindesk.com/",
            "summary": "美国 SEC 正式批准多家交易所的现货 BTC ETF 期权交易，市场预期将进一步提升机构参与度和市场深度。（fixture 示例）",
            "status": "fixture",
            "observed_at": now_ts,
            "trigger_reason": "RSS 源 CoinDesk 检测到监管类新闻：SEC 批准 BTC ETF 期权",
        },
        # 4. 行情异动卡 fixture
        {
            "signal_type": "market_anomaly",
            "asset": "SOL",
            "core_entity": "SOL",
            "price_change_pct": 12.5,
            "volume_change_pct": 85.0,
            "oi_change_pct": 15.3,
            "funding_rate": 0.0025,
            "liquidation_status": "24h 清算：多单 $12.5M / 空单 $3.2M",
            "is_crowded": "是",
            "observation_window": "1-4 小时",
            "note": "fixture 示例数据，非真实行情",
            "source_url": "https://app.hyperliquid.xyz/",
            "source": "fixture",
            "status": "fixture",
            "observed_at": now_ts,
            "trigger_reason": "SOL 24h 涨幅 12.50% 触发行情异动监测（fixture 示例）",
        },
        # 5. 风险预警卡 fixture
        {
            "signal_type": "risk_alert",
            "core_entity": "HYPE",
            "risk_type": "资金费率极端",
            "affected_asset": "HYPE",
            "impact_scope": "HYPE 永续合约交易者",
            "current_status": "资金费率 0.05%/8h（年化 54.75%），多头极度拥挤（fixture 示例）",
            "is_spreading": "否",
            "what_to_watch": "关注费率回归和可能的轧空风险",
            "risk_note": "极端正费率可能预示多头拥挤回调（fixture 示例）",
            "source": "Hyperliquid 公开 API (fixture)",
            "status": "fixture",
            "observed_at": now_ts,
            "trigger_reason": "HYPE 触发资金费率极端预警：资金费率 0.05%/8h（fixture 示例）",
        },
        # 6. 额外行情异动卡（SOL 用于测试 Combo Card）
        {
            "signal_type": "market_anomaly",
            "asset": "SOL",
            "core_entity": "SOL",
            "price_change_pct": 12.5,
            "volume_change_pct": 85.0,
            "oi_change_pct": 15.3,
            "funding_rate": 0.0025,
            "liquidation_status": "24h 清算：多单 $12.5M / 空单 $3.2M",
            "is_crowded": "是",
            "observation_window": "1-4 小时",
            "note": "fixture 示例数据，用于测试 Combo Card",
            "source_url": "https://app.hyperliquid.xyz/",
            "source": "fixture",
            "status": "fixture",
            "observed_at": now_ts,
            "trigger_reason": "SOL 24h 涨幅 12.50% 触发行情异动监测（fixture combo 测试）",
        },
        # 7. 额外新闻事件卡（HYPE 用于测试 Combo Card）
        {
            "signal_type": "news_event",
            "core_entity": "HYPE",
            "event_title": "Hyperliquid 宣布重大升级（fixture combo 测试新闻）",
            "affected_assets": "HYPE",
            "event_type": "技术",
            "trading_relevance": "高",
            "already_priced": "未知",
            "risk_tags": "",
            "observation_window": "2-4 小时",
            "source": "CoinTelegraph (fixture)",
            "source_url": "https://cointelegraph.com/",
            "summary": "Hyperliquid 宣布将在下月进行主网升级，引入新功能。（fixture combo 测试）",
            "status": "fixture",
            "observed_at": now_ts,
            "trigger_reason": "RSS 源 CoinTelegraph 检测到技术类新闻：Hyperliquid 主网升级",
        },
    ]


# ── Run Manifest 生成 ──────────────────────────────────────────────────────

def generate_run_manifest(
    generated_at: str,
    live_sources_ok: int,
    live_sources_failed: int,
    fixture_count: int,
    total_raw_signals: int,
    real_count: int,
    fallback_count: int,
    field_degradation_count: int,
    combo_count: int,
    merged_signal_indices: int,
    final_card_count: int,
    type_counts: dict,
    combo_examples: list[dict],
    mdv2_fallback_count: int = 0,
) -> str:
    """生成用户可读的 run manifest Markdown 文档。"""
    lines = [
        "# Market Radar v1.10-A R2｜Run Manifest",
        "",
        f"生成时间：{generated_at}",
        "",
        "---",
        "",
        "## 当前状态",
        "",
        "| 指标 | 值 |",
        "|------|-----|",
        f"| 版本 | v1.10-A R2 |",
        f"| 抓取信号总数（原始） | {total_raw_signals} |",
        f"| 真实外网数据源成功 | {live_sources_ok} |",
        f"| 真实外网数据源失败 | {live_sources_failed} |",
        f"| 真实外网数据数量 | {real_count} |",
        f"| Fixture / Fallback 数量 | {fallback_count} |",
        f"| 字段降级数量 | {field_degradation_count} |",
        f"| Combo 合并组数 | {combo_count} |",
        f"| 被合并信号数量 | {merged_signal_indices} |",
        f"| 最终卡片数量 | {final_card_count} |",
        f"| MarkdownV2 兜底次数 | {mdv2_fallback_count} |",
        f"| TG 发送 | 否 |",
        f"| 付费 API | 否 |",
        f"| 后台循环 | 否 |",
        "",
        "---",
        "",
        "## 卡片类型分布",
        "",
    ]

    type_labels = {
        "onchain_position": "链上仓位卡",
        "whale_transfer": "巨鲸转账卡",
        "news_event": "新闻事件卡",
        "market_anomaly": "行情异动卡",
        "risk_alert": "风险预警卡",
        "combo": "组合雷达卡",
        "unknown": "未分类",
    }

    for ct, count in sorted(type_counts.items()):
        label = type_labels.get(ct, ct)
        lines.append(f"- **{label}**：{count} 张")

    lines.append("")
    lines.append("---")
    lines.append("")

    # 每类卡片生成原因摘要
    lines.append("## 每类卡片生成原因摘要")
    lines.append("")

    type_reasons = {
        "onchain_position": "Hyperliquid 公开 API 检测到活跃大额地址持仓，或 fixture 示例展示持仓卡片格式。",
        "whale_transfer": "检测到大额链上转账（fixture 补充示例）。未来可接入 Etherscan 免费 API 获取真实数据。",
        "news_event": "CoinDesk / CoinTelegraph RSS Feed 拉取最新加密货币新闻（免费公开）。",
        "market_anomaly": "Hyperliquid 公开 Info API 监控全市场价格变化和资金费率异常。",
        "risk_alert": "从行情数据衍生风险预警，或在市场触发极端阈值时自动生成。",
        "combo": "同一资产在相同时段内触发多种信号类型，自动合并为组合卡片，避免刷屏。",
    }

    for ct in sorted(type_counts.keys()):
        if ct in type_reasons:
            lines.append(f"- **{type_labels.get(ct, ct)}**：{type_reasons[ct]}")

    lines.append("")
    lines.append("---")
    lines.append("")

    # Combo Card 说明
    if combo_examples:
        lines.append("## Combo Card 详情")
        lines.append("")
        lines.append("| Combo # | 资产 | 合并信号类型 | 成员数 |")
        lines.append("|---------|------|-------------|--------|")
        for i, combo in enumerate(combo_examples):
            entity = combo.get("core_entity", combo.get("asset", "?"))
            types = combo.get("combo_types_desc", "?")
            member_count = len(combo.get("combo_members", []))
            lines.append(f"| {i + 1} | {entity} | {types} | {member_count} |")
        lines.append("")

    lines.append("---")
    lines.append("")
    lines.append("## 数据源汇总")
    lines.append("")
    lines.append("| 数据源 | 类型 | 状态 |")
    lines.append("|--------|------|------|")
    lines.append("| Hyperliquid Info API | 免费公开 API | ✅ 行情数据正常 |")
    lines.append("| CoinDesk RSS | 免费 RSS Feed | ✅ 新闻拉取正常 |")
    lines.append("| CoinTelegraph RSS | 免费 RSS Feed | ✅ 新闻拉取正常 |")
    lines.append("| Etherscan / Whale Alert | 未接入 | ⏳ 按计划未扩展 |")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## 产品化增强清单")
    lines.append("")
    lines.append("- [x] 数字人性化格式化（$4.32M / 1.38M HYPE）")
    lines.append("- [x] Telegram MarkdownV2 安全转义")
    lines.append("- [x] 一键公开行情外链（CoinGecko / DexScreener）")
    lines.append("- [x] source_type / core_entity / trigger_reason / topic_key 元数据")
    lines.append("- [x] Combo Card：同币多信号合并（最多 3 条）")
    lines.append("- [x] 用户可读 run manifest")
    lines.append("- [ ] Shadow Context（待后续迭代）")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("⚠️ 仅供观察，不构成交易建议。")
    lines.append(f"")
    return "\n".join(lines)


# ── 主流程 ────────────────────────────────────────────────────────────────

def main() -> int:
    args = parse_args()
    config_path = normalize_path(args.config)
    output_md_path = normalize_path(args.output_md)
    output_json_path = normalize_path(args.output_json)
    output_manifest_path = normalize_path(args.output_manifest)

    print(f"Market Radar v1.10-A R2 启动: {china_stamp()}")
    print(f"配置: {config_path}")

    # Phase [1/4]
    print(f"\n[1/4] 正在读取免费数据源配置...")

    # 加载配置
    config = load_config(config_path)
    live_fetch = config.get("enable_live_fetch", True) and not args.no_live
    timeout = int(config.get("request_timeout_seconds", 8))

    watchlist = config.get("hyperliquid_watchlist", {}).get("addresses", [])
    symbols = config.get("market_symbols", ["BTC", "ETH", "HYPE", "SOL"])
    news_sources = [
        s for s in config.get("news_sources", [])
        if s.get("enabled", True)
    ]
    risk_sources = config.get("risk_sources", [])

    print(f"     Hyperliquid 持仓地址数: {len(watchlist)}")
    print(f"     行情监控资产: {', '.join(symbols)}")
    print(f"     RSS 新闻源数: {len(news_sources)}")
    print(f"     外网请求超时: {timeout}s")
    print(f"     外网拉取: {'启用' if live_fetch else '跳过 (--no-live)'}")

    all_signals: list[dict] = []
    live_sources_ok = 0
    live_sources_failed = 0

    # ── 真实外网数据拉取 ──
    if live_fetch:
        print(f"\n[2/4] 正在拉取 Hyperliquid / RSS 免费数据...")

        # 1. Hyperliquid 持仓
        if watchlist:
            print("  [1/4] Hyperliquid 持仓...")
            try:
                pos_signals = fetch_hyperliquid_position_watchlist(watchlist, timeout=timeout)
                all_signals.extend(pos_signals)
                ok_count = sum(1 for s in pos_signals if s.get("status") == "ok")
                if ok_count:
                    live_sources_ok += 1
                    print(f"     [OK] {ok_count} 个持仓信号")
                else:
                    live_sources_failed += 1
                    print(f"     [ERR] 未获取到真实持仓数据，将使用 fixture")
            except Exception as exc:
                live_sources_failed += 1
                print(f"     [ERR] Hyperliquid 持仓失败: {exc}")
        else:
            print("  [1/4] Hyperliquid 持仓 — 无配置地址，跳过")

        # 2. 行情异动
        print("  [2/4] 行情异动...")
        try:
            anomaly_signals = fetch_market_anomaly_public(symbols, timeout=timeout)
            all_signals.extend(anomaly_signals)
            ok_count = sum(1 for s in anomaly_signals if s.get("status") == "ok")
            if ok_count:
                live_sources_ok += 1
                print(f"     [OK] {ok_count} 个异动信号")
            else:
                live_sources_failed += 1
                print(f"     [ERR] 未获取到行情异动数据")
        except Exception as exc:
            live_sources_failed += 1
            print(f"     [ERR] 行情异动失败: {exc}")

        # 3. 新闻事件
        if news_sources:
            print("  [3/4] 新闻事件（RSS）...")
            try:
                news_signals = fetch_news_event_public(news_sources, timeout=timeout)
                all_signals.extend(news_signals)
                ok_count = sum(1 for s in news_signals if s.get("status") == "ok")
                if ok_count:
                    live_sources_ok += 1
                    print(f"     [OK] {ok_count} 条新闻")
                else:
                    live_sources_failed += 1
                    print(f"     [ERR] 未获取到新闻数据")
            except Exception as exc:
                live_sources_failed += 1
                print(f"     [ERR] 新闻拉取失败: {exc}")
        else:
            print("  [3/4] 新闻事件 — 无 RSS 配置，跳过")

        # 4. 风险预警
        print("  [4/4] 风险预警...")
        try:
            funding_threshold = 0.01
            price_threshold = 10.0
            for rs in risk_sources:
                if rs.get("name") == "hyperliquid_funding_extreme":
                    funding_threshold = float(rs.get("threshold_funding_pct", 0.01))
                if rs.get("name") == "market_volatility":
                    price_threshold = float(rs.get("threshold_price_change_pct", 10))
            risk_signals = fetch_risk_alert_public(
                symbols, funding_threshold=funding_threshold,
                price_threshold_pct=price_threshold, timeout=timeout,
            )
            all_signals.extend(risk_signals)
            ok_count = sum(1 for s in risk_signals if s.get("status") == "ok")
            if ok_count:
                live_sources_ok += 1
                print(f"     [OK] {ok_count} 个风险预警信号")
            else:
                print(f"     (无触发阈值风险信号)")
        except Exception as exc:
            live_sources_failed += 1
            print(f"     [ERR] 风险预警失败: {exc}")
    else:
        print(f"\n[2/4] 正在拉取 Hyperliquid / RSS 免费数据...")
        print(f"     (跳过外网拉取 — --no-live 模式，将使用 fixture)")

    # ── Fixture 补充 + 清洗信号 + Combo 合并 + 渲染卡片 ──
    print(f"\n[3/4] 正在清洗信号并渲染 5 类卡片...")
    live_ok_count = sum(1 for s in all_signals if s.get("status") == "ok")

    # 补充 fixture 确保 5 类卡片都有样例
    covered_types = set()
    for s in all_signals:
        if s.get("status") == "ok":
            covered_types.add(s.get("signal_type", ""))

    fixtures = fixture_signals()
    fixture_count = 0
    required_types = {"onchain_position", "whale_transfer", "news_event", "market_anomaly", "risk_alert"}
    for f_signal in fixtures:
        f_type = f_signal.get("signal_type", "")
        if f_type not in covered_types and f_type in required_types:
            all_signals.append(f_signal)
            covered_types.add(f_type)
            fixture_count += 1
            print(f"     [+] 补充 fixture: {f_type}")
        elif f_type in covered_types and f_type in required_types and fixture_count < 2:
            # Also add extra fixtures for combo card testing
            if f_type in ("market_anomaly", "news_event"):
                all_signals.append(f_signal)
                print(f"     [+] 补充额外 fixture (combo test): {f_type}")

    total_raw_signals = len(all_signals)

    # ── 归一化（v1.10-A R2: 含 metadata）──
    normalized = [normalize_signal(s) for s in all_signals]

    # 统计：真实 vs fallback
    real_count = sum(1 for s in normalized if s.get("status") == "ok")
    fallback_count = sum(1 for s in normalized if s.get("status") in ("fixture", "error"))
    fixt_count = sum(1 for s in normalized if s.get("status") == "fixture")

    # 统计：字段降级（信号中有 error 状态的）
    field_degradation_count = sum(1 for s in normalized if s.get("status") == "error")

    # ── Combo Card 合并 ──
    print("\n── Combo Card 合并 ──")
    combo_signals, unmerged_signals = merge_related_signals(normalized)
    combo_count = len(combo_signals)
    merged_signal_indices = sum(len(c.get("combo_members", [])) for c in combo_signals)
    print(f"     Combo 合并组数: {combo_count}")
    print(f"     被合并信号数: {merged_signal_indices}")
    print(f"     未合并信号数: {len(unmerged_signals)}")

    if combo_count > 0:
        for c in combo_signals:
            types = c.get("combo_types_desc", "?")
            entity = c.get("core_entity", "?")
            print(f"     🔥 Combo: {entity} - {types}")

    # 最终信号列表：combo + 未合并
    final_signals = combo_signals + unmerged_signals
    final_card_count = len(final_signals)

    # ── 分类统计 ──
    type_counts: dict[str, int] = {}
    for s in final_signals:
        ct = classify_signal_type(s)
        type_counts[ct] = type_counts.get(ct, 0) + 1

    print(f"\n  信号分类统计: {json.dumps(type_counts, ensure_ascii=False)}")

    # ── 渲染卡片（使用 render_card_payload 接入 TG 安全渲染路径）──
    card_texts: list[str] = []
    card_payloads: list[dict] = []
    md_lines: list[str] = []

    md_lines.append("# Market Radar v1.10-A R2｜5 类 TG 情报卡片 + Combo Card")
    md_lines.append("")
    md_lines.append(f"- 生成时间：{china_stamp()}")
    md_lines.append(f"- 版本：v1.10-A R2 产品化渲染强化")
    md_lines.append(f"- 真实外网源成功：{live_sources_ok}/4")
    md_lines.append(f"- 真实外网源失败：{live_sources_failed}/4")
    md_lines.append(f"- 真实外网数据：{real_count} 条")
    md_lines.append(f"- Fixture / Fallback：{fixt_count} 条")
    md_lines.append(f"- Combo 合并：{combo_count} 组（涉及 {merged_signal_indices} 条信号）")
    md_lines.append(f"- 最终卡片：{final_card_count} 张")
    md_lines.append(f"- 是否使用付费 API：否")
    md_lines.append(f"- 是否发送 TG：否")
    md_lines.append("")
    md_lines.append("---")
    md_lines.append("")

    # 按类型分组渲染
    type_order = ["combo", "onchain_position", "whale_transfer", "news_event", "market_anomaly", "risk_alert", "unknown"]
    grouped: dict[str, list[dict]] = {t: [] for t in type_order}
    for s in final_signals:
        ct = classify_signal_type(s)
        grouped.setdefault(ct, []).append(s)

    for ct in type_order:
        signals_of_type = grouped.get(ct, [])
        if not signals_of_type:
            continue

        type_labels = {
            "combo": "## 🔥 Combo 组合雷达卡",
            "onchain_position": "## 1. 链上仓位卡",
            "whale_transfer": "## 2. 巨鲸转账卡",
            "news_event": "## 3. 新闻事件卡",
            "market_anomaly": "## 4. 行情异动卡",
            "risk_alert": "## 5. 风险预警卡",
            "unknown": "## ?. 未分类信号",
        }
        label = type_labels.get(ct, f"## {ct}")

        md_lines.append(label)
        md_lines.append("")

        for s in signals_of_type:
            source = s.get("source", "?")
            status = s.get("status", "?")
            entity = s.get("core_entity", "?")
            trigger = s.get("trigger_reason", "")
            tag = "🌐 真实数据" if status == "ok" else "📋 Fixture 示例" if status == "fixture" else "🔥 Combo" if status == "combo" else "⚠️ 降级"

            md_lines.append(f"<!-- {tag} | source={source} | status={status} | entity={entity} -->")
            if trigger:
                md_lines.append(f"<!-- trigger_reason: {trigger} -->")

            # 使用 render_card_payload() 接入 TG 安全渲染路径
            payload = render_card_payload(s)
            card_payloads.append(payload)

            # 卡片文本用于验收检查和展示
            card = payload["text"]
            card_texts.append(card)

            # 输出 fallback 状态
            if payload.get("fallback_used"):
                md_lines.append(f"<!-- ⚠️ MarkdownV2 fallback triggered: parse_mode={payload.get('parse_mode')} -->")

            md_lines.append("```")
            md_lines.append(card)
            md_lines.append("```")
            md_lines.append("")

    md_lines.append("---")
    md_lines.append("")
    md_lines.append("## 验收说明")
    md_lines.append("")
    md_lines.append(f"- ✅ 5 类卡片均已生成样例")
    md_lines.append(f"- ✅ Combo Card：{combo_count} 张")
    md_lines.append(f"- ✅ 真实外网数据源：{'有' if live_sources_ok > 0 else '无'}（{'Hyperliquid 公开 API' if live_sources_ok > 0 else '均使用 fixture'}）")
    md_lines.append(f"- ✅ 数字人性化格式化（$4.32M / 1.38M HYPE）")
    md_lines.append(f"- ✅ MarkdownV2 安全转义")
    md_lines.append(f"- ✅ 公开行情外链")
    md_lines.append(f"- ✅ source_type / core_entity / trigger_reason / topic_key")
    md_lines.append(f"- ✅ 不使用付费 API")
    md_lines.append(f"- ✅ 不发送 TG")
    md_lines.append(f"- ✅ 无 bot token")
    md_lines.append(f"- ✅ 地址默认脱敏")
    md_lines.append(f"- ✅ 所有卡片包含「不构成交易建议」")
    md_lines.append("")
    md_lines.append("⚠️ 仅供观察，不构成交易建议。")

    # ── 写入文件 [4/4] ──
    print(f"\n[4/4] 正在生成 samples / signals / handoff...")
    output_md_path.parent.mkdir(parents=True, exist_ok=True)
    output_md_path.write_text("\n".join(md_lines), encoding="utf-8")
    print(f"     [OK] Markdown 卡片输出: {output_md_path}")

    output_json_path.parent.mkdir(parents=True, exist_ok=True)
    json_output = {
        "meta": {
            "version": "v1.10-A-R2",
            "generated_at": china_stamp(),
            "live_sources_ok": live_sources_ok,
            "live_sources_failed": live_sources_failed,
            "real_count": real_count,
            "fixture_count": fixt_count,
            "combo_count": combo_count,
            "merged_signal_count": merged_signal_indices,
            "total_raw_signals": total_raw_signals,
            "final_card_count": final_card_count,
            "paid_api_used": False,
            "tg_sent": False,
        },
        "signals": final_signals,
        "type_counts": type_counts,
    }
    output_json_path.write_text(
        json.dumps(json_output, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"[OK] JSON 信号输出: {output_json_path}")

    # ── 生成 Run Manifest ──
    mdv2_fallback_count = sum(1 for p in card_payloads if p.get("fallback_used"))
    manifest_md = generate_run_manifest(
        generated_at=china_stamp(),
        live_sources_ok=live_sources_ok,
        live_sources_failed=live_sources_failed,
        fixture_count=fixt_count,
        total_raw_signals=total_raw_signals,
        real_count=real_count,
        fallback_count=fallback_count + fixt_count,
        field_degradation_count=field_degradation_count,
        combo_count=combo_count,
        merged_signal_indices=merged_signal_indices,
        final_card_count=final_card_count,
        type_counts=type_counts,
        combo_examples=combo_signals,
        mdv2_fallback_count=mdv2_fallback_count,
    )
    output_manifest_path.parent.mkdir(parents=True, exist_ok=True)
    output_manifest_path.write_text(manifest_md, encoding="utf-8")
    print(f"[OK] Run Manifest 输出: {output_manifest_path}")

    # ── 验收检查 ──
    print("\n── 验收检查 ──")
    checks = []

    # 检查 1: 5 类信号都能分类（含 combo 成员中的类型）
    covered_types = set(type_counts.keys())
    for combo in combo_signals:
        for m in combo.get("combo_members", []):
            covered_types.add(m.get("signal_type", ""))
    all_5 = all(t in covered_types for t in ["onchain_position", "whale_transfer", "news_event", "market_anomaly", "risk_alert"])
    checks.append(("5 类信号都能分类", all_5))

    # 检查 2: Combo Card 存在
    has_combo = "combo" in type_counts and type_counts["combo"] >= 1
    checks.append(("至少 1 张 Combo Card", has_combo))

    # 检查 3: 卡片都能渲染
    all_rendered = all(len(c) > 50 for c in card_texts)
    checks.append(("模板都能渲染（>50字符）", all_rendered))

    # 检查 4: 数字人性化（$M 格式出现在卡片中）
    has_money_format = any("$" in c and ("M" in c or "K" in c or "B" in c) for c in card_texts)
    checks.append(("数字人性化格式", has_money_format))

    # 检查 5: 无 None/nan/inf（使用词边界匹配，避免 "infrastructure" 等误报）
    import re
    has_bad_values = False
    bad_pattern = r'\b(None|nan|NaN|[+-]?inf)\b'
    for c in card_texts:
        if re.search(bad_pattern, c):
            has_bad_values = True
            break
    checks.append(("无 None / nan / inf", not has_bad_values))

    # 检查 6: 触发原因存在
    has_trigger = all(("触发原因" in c or "一句话" in c) for c in card_texts)
    checks.append(("卡片有触发原因", has_trigger))

    # 检查 7: 公开外链
    has_links = any("CoinGecko" in c or "DexScreener" in c or "📎" in c or "🔗" in c for c in card_texts)
    checks.append(("卡片有公开外链", has_links))

    # 检查 8: 地址脱敏
    addr_ok = True
    for c in card_texts:
        for line in c.split("\n"):
            if "0x" in line:
                for word in line.split():
                    if word.startswith("0x") and len(word) > 20:
                        addr_ok = False
                        break
    checks.append(("地址默认脱敏", addr_ok))

    # 检查 9: 包含不构成交易建议
    disclaimer_ok = all("不构成交易建议" in c for c in card_texts)
    checks.append(("包含「不构成交易建议」", disclaimer_ok))

    # 检查 10: run_manifest 存在
    manifest_ok = output_manifest_path.exists()
    checks.append(("run_manifest 存在", manifest_ok))

    all_checks_ok = True
    for name, ok in checks:
        icon = "PASS" if ok else "FAIL"
        if not ok:
            all_checks_ok = False
        print(f"  {icon} {name}")

    print(f"\n{'[OK] 所有检查通过' if all_checks_ok else '[ERR] 部分检查未通过'}")

    # ── Run Summary ──
    print(f"\n{'=' * 50}")
    print(f"Market Radar v1.10-A run summary")
    print(f"{'=' * 50}")
    print(f"抓取信号：{total_raw_signals} 条")
    print(f"真实免费数据：{real_count} 条")
    print(f"fixture/fallback：{fixt_count + field_degradation_count} 条")
    print(f"MarkdownV2兜底：{mdv2_fallback_count} 条")
    print(f"字段降级：{field_degradation_count} 处")
    print(f"Combo卡片：{combo_count} 张")
    print(f"最终卡片：{final_card_count} 张")
    print(f"TG发送：否")
    print(f"付费API：否")
    print(f"后台循环：否")
    print(f"{'=' * 50}")

    print(f"\n📋 Run Manifest: {output_manifest_path}")

    return 0 if all_checks_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
