"""Market Radar Card Router v1.10-A R2 — 信号分类 + 5 类 TG 卡片模板渲染 + Combo Card。

用法：
    from scripts.market_radar_card_router import classify_signal_type, render_card, render_card_payload
    card_type = classify_signal_type(signal)
    card_text = render_card(signal)
    payload = render_card_payload(signal)  # {text, parse_mode, fallback_used, warnings}
"""

from __future__ import annotations

from typing import Any


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
)
from scripts.market_radar_signal_merge import render_combo_card


# ── 信号分类 ──────────────────────────────────────────────────────────────

def classify_signal_type(signal: dict) -> str:
    """根据 signal 内容返回 5 类之一、combo 或 unknown。

    优先级：
    1. 显式 signal_type 字段（包括 combo）
    2. 内容特征推断
    """
    explicit = str(signal.get("signal_type") or signal.get("type") or "").strip().lower()
    type_map = {
        "onchain_position": "onchain_position",
        "whale_transfer": "whale_transfer",
        "news_event": "news_event",
        "market_anomaly": "market_anomaly",
        "risk_alert": "risk_alert",
        "combo": "combo",
    }
    if explicit in type_map:
        return type_map[explicit]

    # 特征推断
    if _has_keys(signal, ["address", "side", "entry_price"]):
        return "onchain_position"
    if _has_keys(signal, ["transfer_amount", "from_address", "to_address"]):
        return "whale_transfer"
    if _has_keys(signal, ["event_title", "event_type"]):
        return "news_event"
    if _has_keys(signal, ["price_change_pct", "volume_change_pct", "asset"]):
        return "market_anomaly"
    if _has_keys(signal, ["risk_type", "affected_asset"]):
        return "risk_alert"

    # 宽松匹配
    if signal.get("address") and signal.get("side"):
        return "onchain_position"
    if signal.get("transfer_amount") or signal.get("whale_amount"):
        return "whale_transfer"
    if signal.get("event_title") or signal.get("news_title"):
        return "news_event"
    if signal.get("price_change_pct") and signal.get("asset"):
        return "market_anomaly"
    if signal.get("risk_type"):
        return "risk_alert"

    return "unknown"


def _has_keys(d: dict, keys: list[str]) -> bool:
    return all(k in d for k in keys)


# ── 渲染入口 ──────────────────────────────────────────────────────────────

def render_card(signal: dict) -> str:
    """根据信号类型渲染 TG 可读卡片文本（纯文本，不包含 MarkdownV2 转义）。

    如需安全的 TG 发送 payload（含 parse_mode / fallback_used），请使用 render_card_payload()。
    """
    card_type = signal.get("signal_type") or classify_signal_type(signal)
    renderers = {
        "onchain_position": render_onchain_position_card,
        "whale_transfer": render_whale_transfer_card,
        "news_event": render_news_event_card,
        "market_anomaly": render_market_anomaly_card,
        "risk_alert": render_risk_alert_card,
        "combo": render_combo_card,
    }
    renderer = renderers.get(card_type)
    if renderer:
        return renderer(signal)
    return _render_unknown_card(signal)


def render_card_payload(signal: dict, prefer_markdown: bool = True) -> dict:
    """渲染卡片并返回 TG 安全发送 payload。

    这是 render_card() 的安全包装层，确保真实 TG 发送前经过 render_tg_safe_text() 兜底保护。

    返回格式：
    {
        "text": "...",              # 渲染后的卡片文本（MarkdownV2 已转义或纯文本兜底）
        "parse_mode": "MarkdownV2" | None,  # Telegram parse_mode
        "fallback_used": bool,       # 是否触发 MarkdownV2 → 纯文本降级
        "warnings": [...],           # 警告信息列表
        "card_type": "onchain_position" | ...,
    }

    prefer_markdown=True（默认）：正常情况返回 MarkdownV2 已转义的文本，异常时自动降级为纯文本。
    prefer_markdown=False：返回纯文本，parse_mode=None。
    """
    card_type = signal.get("signal_type") or classify_signal_type(signal)

    # 1. 先渲染卡片纯文本
    try:
        card_text = render_card(signal)
    except Exception:
        card_text = render_error_card(
            source_name=str(signal.get("source", "unknown")),
            error_message="card rendering failed",
        )
        card_type = "error"

    # 2. 通过 render_tg_safe_text() 安全渲染（MarkdownV2 转义 + 异常兜底）
    safe = render_tg_safe_text(card_text, prefer_markdown=prefer_markdown)

    # 3. 附加 card_type 元数据
    safe["card_type"] = card_type
    return safe


# ── 1. 链上仓位卡 ─────────────────────────────────────────────────────────

def render_onchain_position_card(signal: dict) -> str:
    """渲染链上仓位卡片 — 产品化版本 v1.10-A R2。

    增强项：
    - 数字人性化（$4.32M 格式）
    - MarkdownV2 安全转义
    - 公开行情外链
    - source_type / core_entity / trigger_reason / topic_key
    """
    asset = normalize_symbol(signal.get("asset") or signal.get("symbol") or signal.get("coin") or "")
    side_raw = str(signal.get("side") or "")
    side = "多头" if "long" in side_raw.lower() else "空头" if "short" in side_raw.lower() else side_raw or "未知"
    value_usd = signal.get("position_value_usd") or signal.get("value_usd")
    quantity = signal.get("quantity") or signal.get("size")
    entry = signal.get("entry_price") or signal.get("entry")
    mark = signal.get("mark_price") or signal.get("mark") or signal.get("current_price")
    pnl = signal.get("pnl_usd") or signal.get("pnl")
    liq = signal.get("liquidation_price") or signal.get("liquidation")
    address = str(signal.get("address") or "")
    source_url = safe_value(signal.get("source_url") or "https://app.hyperliquid.xyz/")
    note = str(signal.get("note") or "")
    label = str(signal.get("label") or "")
    trigger_reason = signal.get("trigger_reason", "")

    # 数值计算
    v = _safe_float(value_usd or 0)
    q = _safe_float(quantity or 0)
    e = _safe_float(entry or 0)
    m = _safe_float(mark or 0)
    p = _safe_float(pnl or 0)
    l = _safe_float(liq or 0)

    # 盈亏百分比
    cost = e * q if e > 0 and q > 0 else 0
    pnl_pct = (p / cost * 100) if cost > 0 else 0

    # 距清算百分比
    liq_distance = 0.0
    if l > 0 and m > 0:
        if side == "多头":
            liq_distance = (m - l) / m * 100
        elif side == "空头":
            liq_distance = (l - m) / m * 100
        liq_distance = max(liq_distance, 0)

    # 标题
    pnl_desc = "大浮盈" if pnl_pct > 50 else "浮盈" if p > 0 else "浮亏" if p < 0 else ""
    title_emoji = "🚀" if p > 0 else "📉" if p < 0 else "📊"
    title = f"{title_emoji} 主力仓位雷达｜{asset} {side} {pnl_desc}".strip()

    # 一句话定性
    one_liner = _safe_one_liner(trigger_reason, f"{asset} {side} 持仓 {humanize_money(v)}，{'浮盈' if p > 0 else '浮亏' if p < 0 else '开仓中'}。")

    lines = [title, ""]
    lines.append(f"一句话：{one_liner}")
    lines.append("")

    lines.append(f"● 持仓规模：{humanize_money(v)}")
    if q > 0:
        lines.append(f"● 持仓数量：{humanize_token_amount(q, asset)}")
    if e > 0:
        lines.append(f"● 均价：${_fmt_price_usd(e)}")
    if m > 0:
        lines.append(f"● 当前价格：${_fmt_price_usd(m)}")

    pnl_sign = "+" if p >= 0 else ""
    lines.append(f"● 当前盈亏：{pnl_sign}{humanize_money(p)}（{pnl_sign}{pnl_pct:.1f}%）")

    if l > 0:
        lines.append(f"● 清算价：${_fmt_price_usd(l)}（距清算 {liq_distance:.1f}%）")

    if note:
        safe_note = safe_value(note).replace("--", "")
        if safe_note:
            lines.append("")
            lines.append(f"💬 注：{safe_note}")

    if label:
        lines.append(f"🏷️ 标签：{safe_value(label)}")

    if address:
        lines.append(f"📌 地址：`{mask_address(address)}`")

    lines.append("")

    # 公开外链
    link_lines = render_source_links(source_url=source_url if source_url != "--" else "", asset=asset)
    lines.extend(link_lines)
    lines.append("")

    # 触发原因
    if trigger_reason:
        lines.append(f"💡 触发原因：{trigger_reason}")
        lines.append("")

    lines.append("⚠️ 仅供观察，不构成交易建议。")
    return "\n".join(lines)


# ── 2. 巨鲸转账卡 ─────────────────────────────────────────────────────────

def render_whale_transfer_card(signal: dict) -> str:
    """渲染巨鲸转账卡片 — 产品化版本 v1.10-A R2。"""
    asset = normalize_symbol(signal.get("asset") or signal.get("transfer_asset") or "")
    amount = signal.get("transfer_amount") or signal.get("amount")
    amount_usd = signal.get("amount_usd") or signal.get("value_usd")
    from_addr = str(signal.get("from_address") or signal.get("source_address") or "")
    to_addr = str(signal.get("to_address") or signal.get("target_address") or "")
    to_exchange = str(signal.get("to_exchange") or signal.get("target_is_exchange") or "")
    is_exchange = to_exchange.lower() in {"true", "yes", "1", "是"}
    history = str(signal.get("historical_behavior") or signal.get("history") or "暂无历史行为数据")
    implication = str(signal.get("potential_implication") or signal.get("implication") or "")
    risk_note = str(signal.get("risk_note") or "")
    chain = str(signal.get("chain") or signal.get("network") or "")
    tx_hash = str(signal.get("tx_hash") or signal.get("transaction_hash") or "")
    source_url = safe_value(signal.get("source_url") or "")
    trigger_reason = signal.get("trigger_reason", "")

    a = _safe_float(amount or 0)
    au = _safe_float(amount_usd or 0)

    # 标题
    title = "🐋 巨鲸转账警报"
    if au > 10_000_000:
        title = "🐋🐋 超大额转账警报"
    lines = [title, ""]

    # 一句话定性
    amount_str = humanize_token_amount(a, asset)
    usd_str = f"（约 {humanize_money(au)}）" if au > 0 else ""
    one_liner = _safe_one_liner(trigger_reason, f"检测到 {amount_str} {usd_str}转账{'，目标疑似交易所' if is_exchange else ''}。".strip())
    lines.append(f"一句话：{one_liner}")
    lines.append("")

    lines.append(f"● 转账资产：{amount_str} {usd_str}".rstrip())

    if from_addr:
        lines.append(f"● 来源地址：`{mask_address(from_addr)}`")
    if to_addr:
        exchange_tag = " 🏦（疑似交易所）" if is_exchange else ""
        lines.append(f"● 目标地址：`{mask_address(to_addr)}`{exchange_tag}")

    if chain:
        lines.append(f"● 链/网络：{safe_value(chain)}")

    lines.append(f"● 历史行为：{safe_value(history)}")

    if implication:
        lines.append(f"● 潜在含义：{safe_value(implication)}")

    if tx_hash:
        lines.append(f"● 交易哈希：`{tx_hash[:10]}...{tx_hash[-8:]}`")

    lines.append("")

    # 公开外链
    if source_url and source_url != "--":
        link_lines = render_source_links(source_url=source_url, asset=asset)
        lines.extend(link_lines)
        lines.append("")

    # 触发原因 + 风险提示
    if trigger_reason:
        lines.append(f"💡 触发原因：{trigger_reason}")
        lines.append("")

    if risk_note:
        lines.append(f"⚠️ 风险提示：{safe_value(risk_note)}")
    else:
        lines.append("⚠️ 大额转账可能预示市场动向，请结合其他信号综合判断。")
    lines.append("")
    lines.append("⚠️ 仅供观察，不构成交易建议。")
    return "\n".join(lines)


# ── 3. 新闻事件卡 ─────────────────────────────────────────────────────────

def render_news_event_card(signal: dict) -> str:
    """渲染新闻事件卡片 — 产品化版本 v1.10-A R2。"""
    title_text = safe_value(signal.get("event_title") or signal.get("title") or "未命名事件")
    affected_assets = safe_value(signal.get("affected_assets") or signal.get("assets") or signal.get("asset") or "待确认")
    event_type = safe_value(signal.get("event_type") or signal.get("category") or "其他")
    trading_relevance = safe_value(signal.get("trading_relevance") or signal.get("relevance") or "待评估")
    already_priced = safe_value(signal.get("already_priced") or signal.get("priced_in") or "未知")
    risk_tags = safe_value(signal.get("risk_tags") or signal.get("tags") or "")
    observation_window = safe_value(signal.get("observation_window") or signal.get("window") or "2-4 小时")
    source = safe_value(signal.get("source") or signal.get("source_name") or "公开信息")
    source_url = safe_value(signal.get("source_url") or "")
    summary = safe_value(signal.get("summary") or signal.get("description") or "")
    trigger_reason = signal.get("trigger_reason", "")

    # 事件类型图标
    type_icons = {
        "监管": "🏛️", "政策": "📜", "技术": "🔧", "安全": "🔒",
        "交易": "💹", "上线": "🆕", "合作": "🤝", "其他": "📰",
    }
    icon = type_icons.get(event_type, "📰")

    lines = [f"{icon} 新闻事件｜{title_text}", ""]

    # 一句话定性
    one_liner = _safe_one_liner(trigger_reason, f"{event_type}类型事件，影响 {affected_assets}，交易相关性 {trading_relevance}。")
    lines.append(f"一句话：{one_liner}")
    lines.append("")

    lines.append(f"● 影响币种：{affected_assets}")
    lines.append(f"● 事件类型：{event_type}")
    lines.append(f"● 交易相关性：{trading_relevance}")

    if summary and summary != "--":
        lines.append(f"● 摘要：{summary[:200]}")

    lines.append(f"● 是否已提前反应：{already_priced}")

    if risk_tags and risk_tags != "--":
        lines.append(f"● 风险标签：{risk_tags}")

    lines.append(f"● 观察窗口：{observation_window}")
    lines.append(f"● 来源：{source}")

    lines.append("")

    # 公开外链
    if source_url and source_url != "--":
        lines.append(f"📎 链接：{source_url}")
        # Also add public links if we can extract a core asset
        primary_asset = affected_assets.split(",")[0].strip() if affected_assets and affected_assets != "待确认" else ""
        if primary_asset:
            pub = build_public_links(primary_asset)
            if pub:
                lines.append(f"🔗 行情查看：{pub[0]['url']}")

    lines.append("")

    # 触发原因
    if trigger_reason:
        lines.append(f"💡 触发原因：{trigger_reason}")
        lines.append("")

    lines.append("⚠️ 新闻事件可能已被市场定价，请独立判断，不构成交易建议。")
    return "\n".join(lines)


# ── 4. 行情异动卡 ─────────────────────────────────────────────────────────

def render_market_anomaly_card(signal: dict) -> str:
    """渲染行情异动卡片 — 产品化版本 v1.10-A R2。"""
    asset = normalize_symbol(signal.get("asset") or signal.get("symbol") or "")
    price_change = signal.get("price_change_pct") or signal.get("price_change")
    volume_change = signal.get("volume_change_pct") or signal.get("volume_change")
    oi_change = signal.get("oi_change_pct") or signal.get("oi_change")
    funding = signal.get("funding_rate") or signal.get("funding")
    liquidation = safe_value(signal.get("liquidation_status") or signal.get("liquidations") or "")
    is_crowded = safe_value(signal.get("is_crowded") or signal.get("crowded") or "")
    observation_window = safe_value(signal.get("observation_window") or signal.get("window") or "1-4 小时")
    note = safe_value(signal.get("note") or "")
    source_url = safe_value(signal.get("source_url") or "")
    trigger_reason = signal.get("trigger_reason", "")

    pc = _safe_float(price_change or 0)
    vc = _safe_float(volume_change or 0)
    oc = _safe_float(oi_change or 0)
    fr = _safe_float(funding or 0)

    # 方向判断
    direction_icon = "📈" if pc > 0 else "📉" if pc < 0 else "➡️"
    change_desc = "急涨" if pc > 8 else "上涨" if pc > 2 else "急跌" if pc < -8 else "下跌" if pc < -2 else "平稳"

    lines = [f"{direction_icon} 行情异动｜{asset} {change_desc}", ""]

    # 一句话定性
    one_liner = _safe_one_liner(trigger_reason, f"{asset} 24h {'涨' if pc > 0 else '跌'}幅 {humanize_percent(pc)}，{'成交量异常放大' if abs(vc) > 50 else '注意波动'}。")
    lines.append(f"一句话：{one_liner}")
    lines.append("")

    lines.append(f"● 币种：{asset}")
    lines.append(f"● 涨跌幅：{humanize_percent(pc)}")

    if abs(vc) > 0.01:
        lines.append(f"● 成交量变化：{humanize_percent(vc)}")
    if abs(oc) > 0.01:
        lines.append(f"● OI 变化：{humanize_percent(oc)}")
    if abs(fr) > 0:
        funding_annual = fr * 3 * 365 * 100
        lines.append(f"● Funding：{humanize_percent(fr * 100)}（年化 {funding_annual:.1f}%）")

    if liquidation and liquidation != "--":
        lines.append(f"● 清算情况：{liquidation}")

    crowd_status = "是，注意拥挤交易风险" if is_crowded.lower() in {"true", "yes", "1", "是"} else "否" if is_crowded else "待评估"
    lines.append(f"● 是否拥挤：{crowd_status}")
    lines.append(f"● 观察窗口：{observation_window}")

    if note and note != "--":
        lines.append(f"● 备注：{note}")

    lines.append("")

    # 公开外链
    link_lines = render_source_links(source_url=source_url if source_url != "--" else "", asset=asset)
    lines.extend(link_lines)
    lines.append("")

    # 触发原因
    if trigger_reason:
        lines.append(f"💡 触发原因：{trigger_reason}")
        lines.append("")

    lines.append("⚠️ 行情异动不代表交易方向，请结合其他信号判断，不构成交易建议。")
    return "\n".join(lines)


# ── 5. 风险预警卡 ─────────────────────────────────────────────────────────

def render_risk_alert_card(signal: dict) -> str:
    """渲染风险预警卡片 — 产品化版本 v1.10-A R2。"""
    risk_type = safe_value(signal.get("risk_type") or signal.get("type") or "未知风险")
    affected = safe_value(signal.get("affected_asset") or signal.get("affected_assets") or signal.get("asset") or "待确认")
    impact_scope = safe_value(signal.get("impact_scope") or signal.get("scope") or "待评估")
    status = safe_value(signal.get("current_status") or signal.get("status") or "发展中")
    is_spreading_raw = safe_value(signal.get("is_spreading") or signal.get("spreading") or "")
    what_to_watch = safe_value(signal.get("what_to_watch") or signal.get("watch_for") or "关注事态进展")
    source = safe_value(signal.get("source") or signal.get("source_name") or "公开信息")
    risk_note = safe_value(signal.get("risk_note") or signal.get("note") or "")
    source_url = safe_value(signal.get("source_url") or "")
    trigger_reason = signal.get("trigger_reason", "")

    # 风险类型图标
    risk_icons = {
        "合约风险": "⚠️", "资金费率极端": "💸", "清算风险": "🔻",
        "监管风险": "🏛️", "安全事件": "🔒", "流动性风险": "💧",
        "市场风险": "📊", "系统性风险": "🌐",
    }
    icon = risk_icons.get(risk_type, "🚨")

    spreading_label = "是，正在扩散" if is_spreading_raw.lower() in {"true", "yes", "1", "是"} else "暂未扩散" if is_spreading_raw else "待观察"

    lines = [f"{icon} 风险预警｜{risk_type}", ""]

    # 一句话定性
    one_liner = _safe_one_liner(trigger_reason, f"{risk_type}风险，涉及 {affected}，当前状态 {status}。")
    lines.append(f"一句话：{one_liner}")
    lines.append("")

    lines.append(f"● 风险类型：{risk_type}")
    lines.append(f"● 涉及资产：{affected}")
    lines.append(f"● 影响范围：{impact_scope}")
    lines.append(f"● 当前状态：{status}")
    lines.append(f"● 是否扩散：{spreading_label}")
    lines.append(f"● 应观察：{what_to_watch}")
    lines.append(f"● 来源：{source}")

    if risk_note and risk_note != "--":
        lines.append(f"● 风险提示：{risk_note}")

    lines.append("")

    # 公开外链
    asset_primary = affected.split(",")[0].strip() if affected and affected not in ("待确认", "ALL", "--") else ""
    if source_url and source_url != "--":
        link_lines = render_source_links(source_url=source_url, asset=asset_primary)
        lines.extend(link_lines)
        lines.append("")

    # 触发原因
    if trigger_reason:
        lines.append(f"💡 触发原因：{trigger_reason}")
        lines.append("")

    lines.append("⚠️ 风险预警不构成交易建议，请根据自身风险承受能力独立决策。")
    return "\n".join(lines)


# ── Unknown / Error 卡片 ──────────────────────────────────────────────────

def _render_unknown_card(signal: dict) -> str:
    """对无法分类的信号生成通用卡片。"""
    source = safe_value(signal.get("source") or signal.get("source_name") or "未知来源")
    note = safe_value(signal.get("note") or signal.get("description") or "无法分类的信号")
    lines = ["📋 未分类信号", ""]
    if note and note != "--":
        lines.append(f"■ 内容：{note}")
    lines.append(f"■ 来源：{source}")
    lines.append("")
    lines.append("⚠️ 此信号无法归入现有卡片模板，建议人工审查。不构成交易建议。")
    return "\n".join(lines)


def render_error_card(source_name: str, error_message: str) -> str:
    """网络请求失败或数据异常时的降级卡片。"""
    safe_error = safe_value(error_message, "未知错误")
    lines = ["⚠️ 数据源异常", ""]
    lines.append(f"■ 数据源：{safe_value(source_name)}")
    lines.append(f"■ 错误：{safe_error[:200]}")
    lines.append("■ 状态：skipped")
    lines.append("")
    lines.append("⚠️ 该数据源暂不可用，将在下次运行时重试。不构成交易建议。")
    return "\n".join(lines)


# ── 工具函数 ──────────────────────────────────────────────────────────────

def _safe_float(value: Any) -> float:
    """安全转换为 float。"""
    import math
    try:
        v = float(str(value or "").strip())
        if math.isnan(v) or math.isinf(v):
            return 0.0
        return v
    except (ValueError, TypeError):
        return 0.0


def _safe_one_liner(trigger_reason: str, fallback: str) -> str:
    """返回 trigger_reason 或 fallback 一句话。"""
    if trigger_reason:
        return trigger_reason
    return fallback


def _fmt_price_usd(value: float) -> str:
    """格式化 USD 价格。"""
    vals = abs(value)
    if vals >= 1000:
        return f"{value:,.2f}"
    if vals >= 1:
        return f"{value:.2f}"
    return f"{value:.6f}"
