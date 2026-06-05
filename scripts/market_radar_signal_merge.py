"""Market Radar Signal Merge v1.10-A R2 — 同币多信号 Combo Card 轻量合并。

合并规则：
- 同一个 core_entity
- 同一小时桶（observed_at 的小时）
- 多个不同 signal_type
- 最多合并 3 条信号
- 合并后原信号不再单独渲染
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from scripts.market_radar_tg_formatting import (
    safe_value,
    humanize_money,
    humanize_percent,
    humanize_token_amount,
    mask_address,
    normalize_symbol,
    escape_markdown_v2,
    build_public_links,
    render_source_links,
)


# ── 小时桶提取 ──────────────────────────────────────────────────────────────

def _hour_bucket(observed_at: str) -> str:
    """从 observed_at ISO 字符串提取小时桶 YYYY-MM-DD-HH。"""
    try:
        dt = datetime.fromisoformat(observed_at.replace("Z", "+00:00"))
        return dt.strftime("%Y-%m-%d-%H")
    except Exception:
        return "unknown-hour"


def _extract_core_entity(signal: dict) -> str:
    """从 signal 中提取核心实体（币种/资产）。"""
    entity = normalize_symbol(
        signal.get("core_entity")
        or signal.get("asset")
        or signal.get("affected_asset")
        or signal.get("affected_assets")
        or signal.get("symbol")
        or ""
    )
    # 处理逗号分隔的多实体，取第一个
    if "," in entity:
        entity = entity.split(",")[0].strip()
    return entity


# ── 合并判断 ────────────────────────────────────────────────────────────────

def should_merge(a: dict, b: dict) -> bool:
    """判断两个信号是否应该合并为 Combo Card。

    条件：
    1. 同一 core_entity（非空）
    2. 同一小时桶
    3. 不同 signal_type
    """
    entity_a = _extract_core_entity(a)
    entity_b = _extract_core_entity(b)
    if not entity_a or not entity_b:
        return False
    if entity_a != entity_b:
        return False

    type_a = a.get("signal_type", "")
    type_b = b.get("signal_type", "")
    if type_a == type_b:
        return False

    hour_a = _hour_bucket(a.get("observed_at", ""))
    hour_b = _hour_bucket(b.get("observed_at", ""))
    if hour_a != hour_b:
        return False

    return True


# ── 批量合并 ────────────────────────────────────────────────────────────────

def merge_related_signals(signals: list[dict]) -> tuple[list[dict], list[dict]]:
    """将信号列表中的相关信号合并为 Combo Card。

    返回 (merged_signals, unmerged_signals)。
    - merged_signals: 被合并的信号（不包含原始单独信号）
    - unmerged_signals: 未被合并的单独信号
    - 原始信号中的 combo 会保留在 unmerged 中，被合并信号用 combo_type 标记
    """
    if len(signals) <= 1:
        return [], list(signals)

    # 分组：按 core_entity + hour_bucket
    groups: dict[str, list[tuple[int, dict]]] = {}
    for idx, s in enumerate(signals):
        entity = _extract_core_entity(s)
        if not entity:
            continue
        bucket = _hour_bucket(s.get("observed_at", ""))
        key = f"{entity}:{bucket}"
        groups.setdefault(key, []).append((idx, s))

    merged_indices: set[int] = set()
    merged_signals: list[dict] = []
    unmerged_signals: list[dict] = []

    for key, group in groups.items():
        if len(group) < 2:
            continue

        # 检查是否有不同 signal_type 的信号
        types_in_group = set(s.get("signal_type", "") for _, s in group)
        if len(types_in_group) < 2:
            continue

        # 取最多 3 条不同类型
        seen_types: set[str] = set()
        combo_items: list[dict] = []
        combo_indices: list[int] = []
        for idx, s in group:
            st = s.get("signal_type", "")
            if st not in seen_types and st != "combo":
                seen_types.add(st)
                combo_items.append(s)
                combo_indices.append(idx)
                if len(combo_items) >= 3:
                    break

        if len(combo_items) < 2:
            continue

        # 构建 Combo signal
        entity = _extract_core_entity(combo_items[0])
        types_desc = "/".join(sorted(seen_types))
        combo_signal = build_combo_signal(combo_items)
        if combo_signal:
            merged_signals.append(combo_signal)
            merged_indices.update(combo_indices)

    # 未合并的信号
    for idx, s in enumerate(signals):
        if idx not in merged_indices:
            unmerged_signals.append(s)

    return merged_signals, unmerged_signals


# ── 构建 Combo Signal ──────────────────────────────────────────────────────

def build_combo_signal(members: list[dict]) -> dict | None:
    """从多个信号构建一个 Combo signal。

    要求至少 2 个成员，最多 3 个。
    """
    if len(members) < 2:
        return None

    members = members[:3]
    entity = _extract_core_entity(members[0])
    types = [m.get("signal_type", "unknown") for m in members]
    types_desc = " + ".join(sorted(set(types)))

    # 汇总所有成员的公开链接
    all_urls: list[str] = []
    for m in members:
        url = m.get("source_url", "")
        if url and url not in all_urls:
            all_urls.append(url)

    # 触发原因（组合版）
    reasons = []
    for m in members:
        reason = m.get("trigger_reason", "")
        if not reason:
            st = m.get("signal_type", "")
            reason = f"{st}信号触发"
        reasons.append(reason)
    combined_reason = "；".join(reasons[:3])

    combo = {
        "signal_type": "combo",
        "asset": entity,
        "core_entity": entity,
        "combo_members": members,
        "combo_types": types,
        "combo_types_desc": types_desc,
        "source_url": all_urls[0] if all_urls else "",
        "source_urls": all_urls,
        "source": "combo",
        "source_type": "combo",
        "source_name": "combo",
        "status": "combo",
        "trigger_reason": f"同一资产 {entity} 在短时间内触发多类信号（{types_desc}），合并为组合卡片",
        "topic_key": f"{entity}:combo:combo:{_hour_bucket(members[0].get('observed_at', ''))}",
        "observed_at": members[0].get("observed_at", ""),
    }
    return combo


# ── Combo Card 渲染 ─────────────────────────────────────────────────────────

def render_combo_card(signal: dict) -> str:
    """渲染组合雷达卡片 — 同币多信号合并。

    结构：
    1. 标题：🔥【组合雷达】$ASSET 同时触发 N 类市场信号
    2. 一句话定性
    3. 各子信号摘要（每条 2-3 行）
    4. 触发原因
    5. 来源/公开外链
    6. 风险提示
    """
    entity = normalize_symbol(signal.get("core_entity") or signal.get("asset") or "")
    members = signal.get("combo_members", [])
    if not members:
        # 尝试从子信号中提取，fallback
        return _render_combo_fallback(signal)

    types_desc = signal.get("combo_types_desc", f"{len(members)} 类信号")
    num_types = len(members)

    lines = [f"🔥【组合雷达】${entity} 同时触发 {num_types} 类市场信号", ""]

    # 一句话定性
    one_liner = _build_one_liner(entity, members)
    lines.append(f"一句话：{one_liner}")
    lines.append("")

    # 各子信号摘要
    lines.append("核心信号:")
    type_icons = {
        "market_anomaly": "📈", "onchain_position": "🐋", "whale_transfer": "💸",
        "news_event": "📰", "risk_alert": "🚨",
    }
    type_labels = {
        "market_anomaly": "行情异动", "onchain_position": "链上仓位", "whale_transfer": "巨鲸转账",
        "news_event": "新闻事件", "risk_alert": "风险预警",
    }

    for i, m in enumerate(members[:3]):
        st = m.get("signal_type", "")
        icon = type_icons.get(st, "📌")
        label = type_labels.get(st, st)
        summary = _summarize_signal(m)
        lines.append(f"{i+1}. {icon} {label}：{summary}")

    lines.append("")

    # 触发原因
    trigger_reason = signal.get("trigger_reason", "")
    if trigger_reason:
        lines.append(f"💡 触发原因：{trigger_reason}")
        lines.append("")

    # 来源/公开外链
    source_url = signal.get("source_url", "")
    all_urls = signal.get("source_urls", [])
    link_lines = render_source_links(source_url=source_url, asset=entity)
    if link_lines:
        lines.extend(link_lines)
        lines.append("")

    # 风险提示
    lines.append("⚠️ 仅供观察，不构成交易建议。")
    return "\n".join(lines)


def _build_one_liner(entity: str, members: list[dict]) -> str:
    """根据子信号构建一句话定性。"""
    parts = []
    for m in members:
        st = m.get("signal_type", "")
        if st == "market_anomaly":
            pct = m.get("price_change_pct", 0)
            direction = "上涨" if pct > 0 else "下跌" if pct < 0 else "波动"
            parts.append(f"{'行情' + direction}")
        elif st == "onchain_position":
            side = m.get("side", "")
            parts.append(f"链上{'多头' if 'long' in str(side).lower() else '空头' if 'short' in str(side).lower() else '持仓'}变动")
        elif st == "whale_transfer":
            parts.append("大额转账")
        elif st == "news_event":
            parts.append("新闻事件")
        elif st == "risk_alert":
            parts.append("风险预警")
    if not parts:
        return f"{entity} 同时出现多源信号叠加，短线关注波动放大。"
    combined = "、".join(parts)
    return f"{entity} 同时出现{combined}，短线关注波动放大。"


def _summarize_signal(signal: dict, max_len: int = 60) -> str:
    """单条信号摘要。"""
    st = signal.get("signal_type", "")
    entity = normalize_symbol(signal.get("asset") or signal.get("core_entity") or "")

    if st == "market_anomaly":
        pct = signal.get("price_change_pct", 0)
        return f"1h 涨跌幅 {humanize_percent(pct)}" + (f"，成交放大" if abs(pct) > 8 else "")
    elif st == "onchain_position":
        value = signal.get("position_value_usd", 0)
        side = signal.get("side", "")
        return f"{side} 持仓 {humanize_money(value)}"
    elif st == "whale_transfer":
        amount = signal.get("transfer_amount", 0)
        to_exchange = str(signal.get("to_exchange", "")).lower() in ("true", "yes", "1")
        suffix = "，目标疑似交易所" if to_exchange else ""
        return f"转账 {humanize_token_amount(amount, entity)}{suffix}"
    elif st == "news_event":
        title = signal.get("event_title", "")[:max_len]
        return str(title or "新闻事件")
    elif st == "risk_alert":
        risk_type = signal.get("risk_type", "风险预警")
        status = signal.get("current_status", "")[:max_len]
        return f"{risk_type}：{status}"
    return "信号已触发"


def _render_combo_fallback(signal: dict) -> str:
    """Combo Card fallback 渲染（当 combo_members 为空时）。"""
    entity = normalize_symbol(signal.get("asset") or signal.get("core_entity") or "")
    lines = [
        f"🔥【组合雷达】${entity} 多信号叠加",
        "",
        f"💡 触发原因：同一资产在短时间内出现多源信号叠加，已合并为一张卡。",
        "",
        "⚠️ 仅供观察，不构成交易建议。",
    ]
    return "\n".join(lines)


# ── 工具：检测是否已经是 combo member ──────────────────────────────────────

def is_combo_member(signal: dict) -> bool:
    """检查信号是否已经被合并到 combo 中（用于防止重复渲染）。"""
    return signal.get("_combo_member", False)


def mark_as_combo_member(signal: dict) -> dict:
    """标记信号为已被 combo 合并。"""
    signal["_combo_member"] = True
    return signal
