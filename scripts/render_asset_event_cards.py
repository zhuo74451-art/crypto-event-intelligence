"""
Render v16 asset event cards from aggregated_events.

Input:  data/aggregated_events.csv
Output: results/v16_asset_event_cards.md

Rules:
  - Chinese output, China time UTC+8
  - Group by asset, NOT by source
  - Max 1 main card per asset
  - Priority: BTC, ETH, HYPE, SOL, BNB, MARKET
  - Cards are few and high-quality
  - Never use "清算墙" in user-visible text
  - Always use "监控地址清算风险"
  - No buy/sell/long/short advice
"""

import csv
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CN_TZ = timezone(timedelta(hours=8))
NOW_UTC = datetime.now(timezone.utc).replace(microsecond=0)
NOW_CHINA = (NOW_UTC.astimezone(CN_TZ)).strftime("%Y-%m-%d %H:%M:%S UTC+8")


def read_rows(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        fh.write(content)


def safe_float(value: Any) -> float:
    try:
        return float(str(value or "").replace(",", "").strip())
    except Exception:
        return 0.0


def asset_label(asset: str) -> str:
    return str(asset).upper()


def event_lines(event: dict) -> list[str]:
    """Generate the markdown lines for one asset event card."""
    lines = []
    asset = asset_label(event.get("asset", ""))
    event_type = str(event.get("event_type", ""))
    title = str(event.get("title", f"{asset} 资产动态"))
    summary = str(event.get("summary", ""))
    obs = str(event.get("observation_points", ""))
    strength = safe_float(event.get("overall_strength", 50))
    urgency = str(event.get("urgency", "review"))
    first_hand = int(safe_float(event.get("first_hand_count", 0)))
    sig_count = int(safe_float(event.get("signal_count", 0)))
    start_ts = str(event.get("event_start_time", ""))
    end_ts = str(event.get("event_end_time", ""))

    # Card header
    has_fh = str(event.get("has_first_hand_signal", "")) in ("True", "true", "1", True)
    if not has_fh and first_hand == 0:
        # Auto-detect from first_hand_count as fallback
        has_fh = first_hand > 0

    fh_badge = ""
    if has_fh and urgency == "high":
        fh_badge = " [👁 一手监控]"
    elif has_fh:
        fh_badge = " [👁 一手监控]"

    strength_tag = ""
    if urgency == "high":
        strength_tag = " ⚡ 高优先级"
    elif strength >= 60:
        strength_tag = " 🔶 值得关注"

    lines.append(f"## {asset} 资产动态｜多信号共振{strength_tag}{fh_badge}")
    lines.append("")
    lines.append(f"时间窗口：{start_ts} 至 {end_ts} UTC")
    lines.append(f"信号数量：{sig_count}（一手信号 {first_hand} 条）")
    lines.append(f"综合强度：{strength:.0f}/100")
    lines.append("")

    # What happened
    lines.append("### 发生了什么")
    lines.append("")

    event_specifics = _derive_event_description(event)
    lines.extend(event_specifics)
    lines.append("")

    # Why important
    lines.append("### 为什么重要")
    lines.append("")

    reasons = _derive_importance(event)
    lines.extend(reasons)
    lines.append("")

    # Observation points
    lines.append("### 观察点")
    lines.append("")

    obs_list = [o.strip() for o in obs.replace("；", ";").split(";") if o.strip()]
    if not obs_list:
        obs_list = ["是否继续接近监控地址清算风险区", "是否有新的信息源交叉验证"]
    for o in obs_list:
        lines.append(f"- {o}")

    lines.append("")
    lines.append("> ⚠️ 仅作市场结构与链上情报观察，不构成任何交易建议。")
    lines.append("")

    return lines


def _derive_event_description(event: dict) -> list[str]:
    """Generate plain-language bullet points describing what happened."""
    event_type = str(event.get("event_type", ""))
    lines = []

    if event_type == "monitored_liquidation_risk":
        lines.append("- 监控地址存在接近清算价的仓位")
        lines.append("- 当前数据仅代表 watchlist 监控地址的清算风险，不代表全市场清算密集区")
    elif event_type == "whale_position_change":
        lines.append("- 监控大户仓位出现变化")
        lines.append("- 需要结合价格和持仓量确认市场方向")
    elif event_type == "market_state_change":
        lines.append("- 市场价格、持仓量或成交量在同一时间窗口内出现变化")
        lines.append("- 多个结构信号在短时间内集中出现，说明当前市场拥挤度或风险暴露正在变化")
    elif event_type == "onchain_flow":
        lines.append("- 链上大额资金出现流动")
        lines.append("- 需结合交易所流入流出数据交叉验证")
    elif event_type == "asset_multi_signal":
        lines.append("- 同一资产在短时间内出现多个独立信号")
        lines.append("- 信号来源多样，涵盖价格、持仓、快讯等多个维度")
    elif event_type == "news_context":
        lines.append("- 相关资产出现多条新闻快讯")
        lines.append("- 快讯作为背景信息，需等待一手数据确认")
    else:
        lines.append("- 多个维度信号在短时间内集中出现")

    # Add asset-specific context
    asset = str(event.get("asset", ""))
    title = str(event.get("title", ""))
    if "资金费率" in title:
        lines.append("- 资金费率处于极端分位数，多头持仓成本偏高")
    if "价格" in title and ("涨" in title or "跌" in title or "%" in title):
        lines.append("- 价格出现明显变动，需关注后续持续性")

    return lines if lines else ["- 多个维度信号在短时间内集中出现"]


def _derive_importance(event: dict) -> list[str]:
    """Explain why this event matters structurally."""
    event_type = str(event.get("event_type", ""))
    strength = safe_float(event.get("overall_strength", 50))
    first_hand = int(safe_float(event.get("first_hand_count", 0)))
    sig_count = int(safe_float(event.get("signal_count", 0)))

    lines = []

    if event_type == "monitored_liquidation_risk":
        lines.append("- 监控地址的清算风险代表大资金持仓的安全边际")
        lines.append("- 若价格持续逼近清算价，可能引发连锁平仓反应")
    elif event_type == "market_state_change":
        lines.append("- 市场结构变化往往是趋势转变的前置信号")
        lines.append("- 持仓量、成交量、资金费率的组合变化比单一指标更有参考价值")
    elif first_hand >= 2:
        lines.append("- 多个一手信号交叉验证，可信度显著高于单一二手信源")
        lines.append("- 一手信号的时效性和准确性远优于转载快讯")
    elif sig_count >= 3:
        lines.append("- 多个信号短时间内共振，反映了市场参与者的集体行为变化")
        lines.append("- 信号密度本身就是一个有价值的情报维度")
    else:
        lines.append("- 当前信号数量较少，建议结合其他数据源综合判断")
        lines.append("- 单一信号不宜作为决策依据")

    return lines


def build_summary_csv(events: list[dict], raw_signal_count: int, output_dir: Path) -> None:
    """Build v16_signal_aggregation_summary.csv."""
    import csv

    from collections import Counter

    first_hand = sum(1 for e in events if int(safe_float(e.get("first_hand_count", 0))) > 0)
    news_count = len([e for e in events if e.get("event_type") == "news_context"])
    liq_count = len([e for e in events if e.get("event_type") == "monitored_liquidation_risk"])
    market_count = len([e for e in events if e.get("event_type") == "market_state_change"])
    onchain_count = len([e for e in events if e.get("event_type") == "onchain_flow"])
    card_ready = len([e for e in events if e.get("card_type") != "review_only"])
    review_only = len([e for e in events if e.get("card_type") == "review_only"])
    asset_count = len(set(e.get("asset") for e in events))

    # Calculate number of signals that were merged (duplicates)
    total_signals_in_events = sum(int(safe_float(e.get("signal_count", 0))) for e in events)
    events_count = len(events)

    rows = [
        {"metric": "raw_signal_count", "value": str(raw_signal_count), "note": "输入原始信号总数"},
        {"metric": "aggregated_event_count", "value": str(events_count), "note": "聚合后事件数"},
        {"metric": "asset_count", "value": str(asset_count), "note": "覆盖资产数"},
        {"metric": "first_hand_signal_count", "value": str(first_hand), "note": "含一手信号的事件数"},
        {"metric": "news_signal_count", "value": str(news_count), "note": "纯快讯上下文事件数"},
        {"metric": "monitored_liquidation_risk_count", "value": str(liq_count), "note": "监控地址清算风险事件数"},
        {"metric": "market_state_signal_count", "value": str(market_count), "note": "市场状态变化事件数"},
        {"metric": "onchain_flow_signal_count", "value": str(onchain_count), "note": "链上资金流事件数"},
        {"metric": "duplicate_or_merged_signal_count", "value": str(max(0, total_signals_in_events - events_count)), "note": "因聚合而合并的信号数（去重合并估算）"},
        {"metric": "events_ready_for_card_count", "value": str(card_ready), "note": "可输出为资产卡的事件数"},
        {"metric": "events_review_only_count", "value": str(review_only), "note": "仅审阅不输出卡的事件数"},
        {"metric": "missing_source_count", "value": "0", "note": "本轮未接入coinglass/glassnode等外部源，按要求不使用"},
        {"metric": "warnings_count", "value": "1", "note": "监控地址清算风险仅代表watchlist地址，不代表全市场清算密集区"},
    ]

    path = output_dir / "v16_signal_aggregation_summary.csv"
    with path.open("w", encoding="utf-8-sig", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["metric", "value", "note"])
        w.writeheader()
        w.writerows(rows)
    print(f"  Summary CSV: {path}")


def main() -> None:
    input_path = ROOT / "data" / "aggregated_events.csv"
    output_path = ROOT / "results" / "v16_asset_event_cards.md"
    raw_path = ROOT / "data" / "raw_signals.csv"

    raw_signals = read_rows(raw_path)
    raw_count = len(raw_signals)
    events = read_rows(input_path)
    print(f"Loaded {len(events)} aggregated events from {raw_count} raw signals")

    if not events:
        md = f"""# 加密资产动态卡 v16

生成时间：{NOW_CHINA}

当前无聚合事件数据，请先运行：
```bash
python scripts/build_raw_signals.py
python scripts/aggregate_signals_to_events.py
```

> ⚠️ 仅作市场结构与链上情报观察，不构成任何交易建议。
"""
        write_text(output_path, md)
        print("No events — wrote empty template.")
        build_summary_csv([], raw_count, ROOT / "results")
        return

    # Group events by asset
    proxy = {"BTC": 0, "ETH": 1, "HYPE": 2, "SOL": 3, "BNB": 4}
    asset_events: dict[str, list[dict]] = defaultdict(list)
    for ev in events:
        asset = str(ev.get("asset", "UNKNOWN")).upper()
        asset_events[asset].append(ev)

    # Sort assets: priority first, then by strongest event
    sorted_assets = sorted(asset_events.keys(), key=lambda a: (
        proxy.get(a, 99),
        -max(safe_float(e["overall_strength"]) for e in asset_events[a]),
    ))

    # Build markdown
    md_lines = [
        f"# 加密资产动态卡 v16",
        "",
        f"生成时间：{NOW_CHINA}",
        f"覆盖资产：{len(sorted_assets)} 个",
        f"聚合事件：{len(events)} 个",
        "",
        "---",
        "",
    ]

    # Treat MARKET / macro signals as a special section
    macro_events = asset_events.pop("MARKET", [])
    unknown_events = asset_events.pop("UNKNOWN", [])

    for asset in sorted_assets:
        if asset not in asset_events:
            continue
        asset_list = sorted(asset_events[asset], key=lambda e: -safe_float(e["overall_strength"]))
        # Take top 1 event per asset
        top = asset_list[0]
        lines = event_lines(top)
        md_lines.extend(lines)
        md_lines.append("---")
        md_lines.append("")

    # Macro section
    if macro_events:
        md_lines.append("## MARKET 宏观背景")
        md_lines.append("")
        macro = macro_events[0]
        md_lines.extend([
            f"- 信号数量：{int(safe_float(macro.get('signal_count', 0)))}",
            f"- 综合强度：{safe_float(macro.get('overall_strength', 50)):.0f}/100",
            f"- 摘要：{macro.get('summary', '')}",
            "",
        ])

    # Footer
    md_lines.append("---")
    md_lines.append("")
    md_lines.append("## 说明")
    md_lines.append("")
    md_lines.append("- 本报告按资产维度生成，仅作市场结构与链上情报观察，不构成任何交易建议。")
    md_lines.append("- \"监控地址清算风险\"仅代表 watchlist 监控地址的清算风险，不代表全市场清算密集区。")
    md_lines.append("- 不包含任何买入、卖出、做多、做空建议。")
    md_lines.append("- 卡片仅保留高优先级事件，静态背景信息不重复推送。")
    md_lines.append(f"- 原始数据来源：data/raw_signals.csv（{raw_count} 条原始信号）")

    write_text(output_path, "\n".join(md_lines))
    print(f"  Cards: {output_path}")

    # Build summary csv
    build_summary_csv(events, raw_count, ROOT / "results")

    # Build asset cards summary (standard filename)
    build_asset_cards_summary(events, raw_count, ROOT / "results")


def build_asset_cards_summary(events: list[dict], raw_signal_count: int, output_dir: Path) -> None:
    """Build v16_asset_event_cards_summary.csv — standard asset-level cards summary."""
    import csv

    asset_events: dict[str, list[dict]] = defaultdict(list)
    for ev in events:
        asset = str(ev.get("asset", "UNKNOWN")).upper()
        asset_events[asset].append(ev)

    card_count = len(asset_events)
    first_hand_events = sum(1 for e in events if int(safe_float(e.get("first_hand_count", 0))) > 0)
    radar_count = sum(1 for e in events if str(e.get("card_type", "")) == "intraday_radar")
    digest_count = sum(1 for e in events if str(e.get("card_type", "")) == "evening_digest")

    rows = [{
        "generated_at": NOW_CHINA,
        "asset_count": str(card_count),
        "event_count": str(len(events)),
        "card_count": str(card_count),
        "raw_signal_count": str(raw_signal_count),
        "first_hand_event_count": str(first_hand_events),
        "radar_card_count": str(radar_count),
        "digest_card_count": str(digest_count),
        "source_file": "data/aggregated_events.csv",
        "output_markdown": "results/v16_asset_event_cards.md",
    }]

    path = output_dir / "v16_asset_event_cards_summary.csv"
    with path.open("w", encoding="utf-8-sig", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print(f"  Asset cards summary: {path}")


if __name__ == "__main__":
    main()
