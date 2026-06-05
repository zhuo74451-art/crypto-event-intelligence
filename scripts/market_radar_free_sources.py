"""Market Radar Free Data Sources v1.10-A — 免费公开数据源适配器。

所有数据源都是免费公开的，不需要任何 API Key。
网络请求带 timeout，失败不崩溃，返回 error_card 或 skipped 状态。

数据源：
1. Hyperliquid 官方公开 Info API — 持仓/市场数据（无需 Key）
2. CoinGecko 免费公开 API — 行情数据（无需 Key）
3. RSS 新闻源 — 公开 RSS Feed（无需 Key）
4. 衍生风险信号 — 从公开数据计算
"""

from __future__ import annotations

import json
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any
from defusedxml import ElementTree

import requests


ROOT = Path(__file__).resolve().parents[1]

# ── 公开 API 端点（免费，无需 Key）───────────────────────────────────────
HYPERLIQUID_INFO_URL = "https://api.hyperliquid.xyz/info"
COINGECKO_API_BASE = "https://api.coingecko.com/api/v3"

# 默认超时
DEFAULT_TIMEOUT = 8

# ── 通用网络请求 ──────────────────────────────────────────────────────────

def _http_get(url: str, timeout: int = DEFAULT_TIMEOUT, **kwargs) -> tuple[dict | None, str | None]:
    """GET 请求，返回 (data_dict, error_string)。"""
    session = requests.Session()
    session.trust_env = False
    try:
        resp = session.get(url, timeout=timeout, **kwargs)
        resp.raise_for_status()
        return resp.json(), None
    except Exception as exc:
        return None, _clean_error(exc)


def _http_post(url: str, payload: dict, timeout: int = DEFAULT_TIMEOUT) -> tuple[dict | None, str | None]:
    """POST 请求，返回 (data_dict, error_string)。"""
    session = requests.Session()
    session.trust_env = False
    try:
        resp = session.post(url, json=payload, timeout=timeout)
        resp.raise_for_status()
        return resp.json(), None
    except Exception as exc:
        return None, _clean_error(exc)


def _http_get_text(url: str, timeout: int = DEFAULT_TIMEOUT) -> tuple[str | None, str | None]:
    """GET 文本（RSS XML），返回 (text, error_string)。"""
    session = requests.Session()
    session.trust_env = False
    try:
        resp = session.get(url, timeout=timeout)
        resp.raise_for_status()
        return resp.text, None
    except Exception as exc:
        return None, _clean_error(exc)


def _clean_error(exc: Exception) -> str:
    msg = str(exc)
    # 去掉 URL 中可能的敏感信息
    if len(msg) > 300:
        msg = msg[:300] + "..."
    return msg


def _safe_float(value: Any) -> float:
    try:
        return float(str(value or "").strip())
    except (ValueError, TypeError):
        return 0.0


# ── 1. Hyperliquid 公开持仓数据 ───────────────────────────────────────────

def fetch_hyperliquid_position_watchlist(
    watchlist: list[dict] | None = None,
    timeout: int = DEFAULT_TIMEOUT,
) -> list[dict]:
    """从 Hyperliquid 公开 API 拉取指定地址的持仓数据。

    Hyperliquid Info API 是公开的，不需要 API Key。
    通过 POST {"type": "clearinghouseState", "user": "<address>"} 获取。

    返回 list of dict，每个 dict 是归一化的 signal。
    """
    signals: list[dict] = []
    if not watchlist:
        return signals

    for entry in watchlist:
        address = str(entry.get("address") or "").strip()
        label = str(entry.get("label") or entry.get("name") or "")
        focus_asset = str(entry.get("asset") or "").strip().upper()

        if not address:
            continue

        # 拉取持仓状态
        state, err = _http_post(
            HYPERLIQUID_INFO_URL,
            {"type": "clearinghouseState", "user": address},
            timeout=timeout,
        )

        if err:
            signals.append({
                "signal_type": "onchain_position",
                "asset": focus_asset or "未知",
                "address": address,
                "label": label,
                "side": "未知",
                "position_value_usd": 0,
                "quantity": 0,
                "entry_price": 0,
                "mark_price": 0,
                "pnl_usd": 0,
                "liquidation_price": 0,
                "note": f"数据拉取失败: {err}",
                "source_url": "https://app.hyperliquid.xyz/",
                "source": "hyperliquid",
                "status": "error",
            })
            continue

        if not isinstance(state, dict):
            continue

        # 解析资产仓位
        asset_positions = state.get("assetPositions", [])
        if not isinstance(asset_positions, list):
            asset_positions = []

        for pos in asset_positions:
            pos_data = pos.get("position", {}) if isinstance(pos, dict) else {}
            coin = str(pos_data.get("coin") or pos.get("coin") or "").upper()
            if not coin:
                continue

            # 如果配置了关注资产过滤
            if focus_asset and coin != focus_asset:
                continue

            side_raw = str(pos_data.get("side") or pos.get("side") or "")
            side = "多头" if "long" in side_raw.lower() else "空头" if "short" in side_raw.lower() else side_raw

            entry_px = _safe_float(pos_data.get("entryPx"))
            size = _safe_float(pos_data.get("szi"))
            liq_px = _safe_float(pos_data.get("liquidationPx"))
            position_value = _safe_float(pos_data.get("positionValue"))
            unrealized_pnl = _safe_float(pos_data.get("unrealizedPnl"))

            # 获取当前价格
            mark_price = 0
            meta, meta_err = _http_post(
                HYPERLIQUID_INFO_URL,
                {"type": "metaAndAssetCtxs"},
                timeout=timeout,
            )
            if not meta_err and isinstance(meta, list) and len(meta) >= 2:
                universe = meta[0].get("universe", []) if isinstance(meta[0], dict) else []
                ctxs = meta[1] if isinstance(meta[1], list) else []
                for i, ctx in enumerate(ctxs):
                    asset_meta = universe[i] if i < len(universe) else {}
                    if str(asset_meta.get("name") or "").upper() == coin:
                        mark_price = _safe_float(ctx.get("markPx"))
                        break

            signals.append({
                "signal_type": "onchain_position",
                "asset": coin,
                "address": address,
                "label": label,
                "side": side,
                "position_value_usd": position_value if position_value > 0 else abs(size) * mark_price,
                "quantity": abs(size),
                "entry_price": entry_px,
                "mark_price": mark_price,
                "pnl_usd": unrealized_pnl,
                "liquidation_price": liq_px,
                "note": f"该地址为 Hyperliquid 上{'大规模' if position_value > 1_000_000 else ''}持仓地址，当前卡片仅展示其 {coin} {'多头' if 'long' in side_raw.lower() else '空头'}。",
                "source_url": "https://app.hyperliquid.xyz/",
                "source": "hyperliquid",
                "status": "ok",
            })

    return signals


# ── 2. 免费行情异动数据 ──────────────────────────────────────────────────

def fetch_market_anomaly_public(
    symbols: list[str] | None = None,
    timeout: int = DEFAULT_TIMEOUT,
) -> list[dict]:
    """从 Hyperliquid 公开 API 拉取行情数据，检测异常波动。

    使用 Hyperliquid 的 metaAndAssetCtxs 端点获取全市场数据，
    不需要 API Key。
    """
    symbols = symbols or ["BTC", "ETH", "HYPE", "SOL"]
    upper_symbols = [s.upper() for s in symbols]

    meta, err = _http_post(
        HYPERLIQUID_INFO_URL,
        {"type": "metaAndAssetCtxs"},
        timeout=timeout,
    )

    if err:
        return [{
            "signal_type": "market_anomaly",
            "asset": "ALL",
            "price_change_pct": 0,
            "volume_change_pct": 0,
            "oi_change_pct": 0,
            "funding_rate": 0,
            "liquidation_status": f"数据拉取失败: {err}",
            "is_crowded": "",
            "note": "Hyperliquid 公开 API 暂不可用",
            "source_url": "https://app.hyperliquid.xyz/",
            "source": "hyperliquid",
            "status": "error",
        }]

    if not isinstance(meta, list) or len(meta) < 2:
        return []

    universe = meta[0].get("universe", []) if isinstance(meta[0], dict) else []
    ctxs = meta[1] if isinstance(meta[1], list) else []

    signals: list[dict] = []
    for i, ctx in enumerate(ctxs):
        asset_meta = universe[i] if i < len(universe) else {}
        coin = str(asset_meta.get("name") or ctx.get("coin") or "").upper()
        if not coin or coin not in upper_symbols:
            continue

        mark = _safe_float(ctx.get("markPx"))
        prev = _safe_float(ctx.get("prevDayPx"))
        oi_native = _safe_float(ctx.get("openInterest"))
        funding_raw = _safe_float(ctx.get("funding"))
        day_volume = _safe_float(ctx.get("dayNtlVlm"))

        price_change = (mark / prev - 1.0) * 100 if mark > 0 and prev > 0 else 0
        oi_usd = oi_native * mark if oi_native > 0 and mark > 0 else 0

        # 只输出有明显异动的标的（涨跌幅 > 3% 或 资金费率 > 0.01%）
        if abs(price_change) < 3 and abs(funding_raw) < 0.0001:
            if abs(price_change) >= 3:
                pass  # 保留
            elif abs(funding_raw) >= 0.0005:
                pass  # 极端费率
            else:
                continue  # 无明显异动，跳过

        signals.append({
            "signal_type": "market_anomaly",
            "asset": coin,
            "price_change_pct": round(price_change, 2),
            "volume_change_pct": 0,  # 需要历史对比，单次无法计算
            "oi_change_pct": 0,  # 同上
            "funding_rate": round(funding_raw, 6),
            "liquidation_status": f"OI: {_money(oi_usd)}，24h成交量: {_money(day_volume)}",
            "is_crowded": "是" if abs(funding_raw) > 0.005 else "否",
            "observation_window": "1-4 小时",
            "source_url": "https://app.hyperliquid.xyz/",
            "source": "hyperliquid",
            "status": "ok",
        })

    return signals


# ── 3. 免费新闻事件数据 ──────────────────────────────────────────────────

def fetch_news_event_public(
    sources: list[dict] | None = None,
    timeout: int = DEFAULT_TIMEOUT,
) -> list[dict]:
    """从免费公开 RSS 拉取加密货币新闻。

    来源：
    - CoinDesk RSS（免费公开）
    - CoinTelegraph RSS（免费公开）
    不需要任何 API Key。

    RSS 解析失败不崩溃，返回 skipped。
    """
    default_sources = [
        {"name": "coindesk_rss", "url": "https://www.coindesk.com/arc/outboundfeeds/rss/", "type": "rss"},
        {"name": "cointelegraph_rss", "url": "https://cointelegraph.com/rss", "type": "rss"},
    ]
    sources = sources or default_sources

    signals: list[dict] = []
    for src in sources:
        if not src.get("enabled", True):
            continue

        name = src.get("name", "unknown")
        url = src.get("url", "")
        src_type = src.get("type", "rss")

        if src_type != "rss":
            continue

        text, err = _http_get_text(url, timeout=timeout)

        if err:
            signals.append({
                "signal_type": "news_event",
                "event_title": f"新闻源不可用: {name}",
                "affected_assets": "N/A",
                "event_type": "系统",
                "trading_relevance": "无",
                "already_priced": "N/A",
                "risk_tags": "",
                "observation_window": "N/A",
                "source": name,
                "source_url": url,
                "summary": f"RSS 拉取失败: {err}",
                "status": "error",
            })
            continue

        # 解析 RSS XML
        try:
            root = ElementTree.fromstring(text)
        except Exception as parse_err:
            signals.append({
                "signal_type": "news_event",
                "event_title": f"新闻源解析失败: {name}",
                "affected_assets": "N/A",
                "event_type": "系统",
                "trading_relevance": "无",
                "already_priced": "N/A",
                "risk_tags": "",
                "observation_window": "N/A",
                "source": name,
                "source_url": url,
                "summary": f"XML 解析失败: {parse_err}",
                "status": "error",
            })
            continue

        # 提取前 3 条新闻
        items = root.findall(".//item")[:3]
        for item in items:
            title_el = item.find("title")
            desc_el = item.find("description")
            link_el = item.find("link")
            pubdate_el = item.find("pubDate")

            title = (title_el.text or "").strip() if title_el is not None else ""
            desc = (desc_el.text or "").strip() if desc_el is not None else ""
            link = (link_el.text or "").strip() if link_el is not None else url
            pubdate = (pubdate_el.text or "").strip() if pubdate_el is not None else ""

            # 清理 HTML 标签
            import re
            desc_clean = re.sub(r"<[^>]+>", "", desc)[:200] if desc else ""

            # 推断影响币种
            crypto_keywords = ["Bitcoin", "BTC", "Ethereum", "ETH", "Solana", "SOL", "HYPE",
                              "Hyperliquid", "ARB", "Arbitrum", "SUI"]

            mentioned = []
            title_lower = title.lower()
            desc_lower = desc.lower()
            for kw in crypto_keywords:
                if kw.lower() in title_lower or kw.lower() in desc_lower:
                    if kw.upper() not in mentioned and kw.strip() not in ["Bitcoin", "Ethereum", "Solana"]:
                        mentioned.append(kw.upper())

            affected = ", ".join(mentioned) if mentioned else "待确认"

            # 事件类型推断
            event_type = "其他"
            title_lower_combined = title.lower() + " " + desc.lower()
            if any(w in title_lower_combined for w in ["sec", "regulation", "cftc", "ban", "监管", "合规"]):
                event_type = "监管"
            elif any(w in title_lower_combined for w in ["hack", "exploit", "security", "攻击", "漏洞"]):
                event_type = "安全"
            elif any(w in title_lower_combined for w in ["upgrade", "fork", "mainnet", "升级", "主网"]):
                event_type = "技术"
            elif any(w in title_lower_combined for w in ["launch", "listing", "airdrop", "上线", "空投"]):
                event_type = "上线"
            elif any(w in title_lower_combined for w in ["price", "rally", "crash", "surge", "涨", "跌"]):
                event_type = "交易"

            signals.append({
                "signal_type": "news_event",
                "event_title": title,
                "affected_assets": affected,
                "event_type": event_type,
                "trading_relevance": "中等" if mentioned else "待评估",
                "already_priced": "未知",
                "risk_tags": event_type if event_type in ["监管", "安全"] else "",
                "observation_window": "2-4 小时",
                "source": name,
                "source_url": link,
                "summary": desc_clean,
                "pub_date": pubdate,
                "status": "ok",
            })

    return signals


# ── 4. 免费风险预警数据 ──────────────────────────────────────────────────

def fetch_risk_alert_public(
    symbols: list[str] | None = None,
    funding_threshold: float = 0.01,
    price_threshold_pct: float = 10.0,
    timeout: int = DEFAULT_TIMEOUT,
) -> list[dict]:
    """从公开行情数据衍生风险预警信号。

    检查：
    1. 极端资金费率（年化 > 100%）- 拥挤交易风险
    2. 极端价格波动（24h > 10%）- 市场风险
    3. 大额清算风险 - OI 异常

    所有数据均来自 Hyperliquid 免费公开 API。
    """
    symbols = symbols or ["BTC", "ETH", "HYPE", "SOL"]
    upper_symbols = [s.upper() for s in symbols]

    meta, err = _http_post(
        HYPERLIQUID_INFO_URL,
        {"type": "metaAndAssetCtxs"},
        timeout=timeout,
    )

    if err:
        return [{
            "signal_type": "risk_alert",
            "risk_type": "系统",
            "affected_asset": "ALL",
            "impact_scope": "N/A",
            "current_status": f"数据源不可用: {err}",
            "is_spreading": "",
            "what_to_watch": "等待数据源恢复",
            "source": "hyperliquid",
            "status": "error",
        }]

    if not isinstance(meta, list) or len(meta) < 2:
        return []

    universe = meta[0].get("universe", []) if isinstance(meta[0], dict) else []
    ctxs = meta[1] if isinstance(meta[1], list) else []

    signals: list[dict] = []
    for i, ctx in enumerate(ctxs):
        asset_meta = universe[i] if i < len(universe) else {}
        coin = str(asset_meta.get("name") or ctx.get("coin") or "").upper()
        if not coin or coin not in upper_symbols:
            continue

        mark = _safe_float(ctx.get("markPx"))
        prev = _safe_float(ctx.get("prevDayPx"))
        funding_raw = _safe_float(ctx.get("funding"))
        oi_native = _safe_float(ctx.get("openInterest"))

        price_change = (mark / prev - 1.0) * 100 if mark > 0 and prev > 0 else 0
        funding_8h_pct = abs(funding_raw)
        funding_annual = funding_raw * 3 * 365 * 100

        # 检查极端资金费率
        if funding_8h_pct >= funding_threshold:
            direction = "多头拥挤" if funding_raw > 0 else "空头拥挤"
            signals.append({
                "signal_type": "risk_alert",
                "risk_type": "资金费率极端",
                "affected_asset": coin,
                "impact_scope": f"{coin} 永续合约交易者",
                "current_status": f"资金费率 {funding_8h_pct*100:.2f}%/8h（年化 {funding_annual:.1f}%），{direction}",
                "is_spreading": "否",
                "what_to_watch": "关注费率回归和潜在的轧空/轧多风险",
                "risk_note": f"极端负费率可能预示轧空，极端正费率可能预示多头拥挤回调",
                "source": "hyperliquid",
                "status": "ok",
            })

        # 检查极端价格波动
        if abs(price_change) >= price_threshold_pct:
            direction = "急涨" if price_change > 0 else "急跌"
            signals.append({
                "signal_type": "risk_alert",
                "risk_type": "市场风险",
                "affected_asset": coin,
                "impact_scope": f"{coin} 及相关交易对",
                "current_status": f"24h {direction} {abs(price_change):.1f}%，当前价 {_format_price(mark)}",
                "is_spreading": "待观察",
                "what_to_watch": "关注成交量放大和清算累积情况",
                "risk_note": "极端波动可能导致连环清算，注意风控",
                "source": "hyperliquid",
                "status": "ok",
            })

    return signals


# ── 信号归一化 ────────────────────────────────────────────────────────────

def normalize_signal(raw: dict) -> dict:
    """将不同来源的原始信号归一化为统一字段结构。

    v1.10-A R2 增强：
    - source_type: 数据源类型（api / rss / fixture / combo）
    - source_name: 数据源名称
    - core_entity: 核心资产（BTC / ETH / HYPE 等）
    - trigger_reason: 触发原因（大白话中文）
    - topic_key: core_entity + signal_type + source_type + 小时桶
    """
    signal_type = raw.get("signal_type") or raw.get("type") or "unknown"
    source = raw.get("source") or raw.get("source_name") or "unknown"

    # 推断 source_type
    source_type = raw.get("source_type") or _infer_source_type(source, signal_type)

    # 推断 core_entity
    core_entity = raw.get("core_entity") or _infer_core_entity(raw)

    # 推断 trigger_reason（如果尚未设置）
    trigger_reason = raw.get("trigger_reason") or _infer_trigger_reason(raw, signal_type)

    # 观察时间
    observed_at = raw.get("observed_at") or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    # topic_key: core_entity + signal_type + source_type + 小时桶
    hour_bucket = _extract_hour_bucket(observed_at)
    topic_key = raw.get("topic_key") or f"{core_entity}:{signal_type}:{source_type}:{hour_bucket}"

    base = {
        "signal_type": signal_type,
        "source": source,
        "source_type": source_type,
        "source_name": source,
        "source_url": raw.get("source_url") or "",
        "core_entity": core_entity,
        "trigger_reason": trigger_reason,
        "topic_key": topic_key,
        "status": raw.get("status") or "ok",
        "observed_at": observed_at,
    }

    # 合并 raw 字段（base 优先，因为字段名是归一化的）
    normalized = dict(raw)
    normalized.update(base)
    return normalized


def _infer_source_type(source: str, signal_type: str) -> str:
    """从 source 名称推断 source_type。"""
    source_lower = source.lower()
    if signal_type == "combo":
        return "combo"
    if "fixture" in source_lower:
        return "fixture"
    if any(k in source_lower for k in ["hyperliquid", "api"]):
        return "api"
    if any(k in source_lower for k in ["rss", "coindesk", "cointelegraph"]):
        return "rss"
    return "other"


def _infer_core_entity(raw: dict) -> str:
    """从 signal 字段推断核心实体（资产）。"""
    # 优先级：core_entity > asset > affected_asset > symbol > coin
    entity = (
        raw.get("core_entity")
        or raw.get("asset")
        or raw.get("affected_asset")
        or raw.get("affected_assets")
        or raw.get("symbol")
        or raw.get("coin")
        or ""
    )
    entity = str(entity).strip().upper()
    # 处理逗号分隔的多实体，取第一个
    if "," in entity:
        entity = entity.split(",")[0].strip()
    return entity or "未知"


def _infer_trigger_reason(raw: dict, signal_type: str) -> str:
    """用大白话推断信号触发原因。"""
    entity = _infer_core_entity(raw)

    if signal_type == "market_anomaly":
        pct = _safe_float(raw.get("price_change_pct") or raw.get("price_change", 0))
        direction = "涨" if pct > 0 else "跌"
        return f"{entity} 24h {direction}幅 {abs(pct):.2f}% 触发行情异动监测"

    if signal_type == "onchain_position":
        side = str(raw.get("side") or "")
        side_label = "多头" if "long" in side.lower() else "空头" if "short" in side.lower() else ""
        value_usd = _safe_float(raw.get("position_value_usd") or raw.get("value_usd", 0))
        label = raw.get("label") or ""
        parts = [entity]
        if side_label:
            parts.append(side_label)
        if value_usd > 1_000_000:
            parts.append("大额持仓")
        if label:
            parts.append(f"({label})")
        return " ".join(parts) + "，Hyperliquid 公开 API 检测到链上仓位"

    if signal_type == "whale_transfer":
        amount = _safe_float(raw.get("transfer_amount") or raw.get("amount", 0))
        asset = raw.get("asset") or raw.get("transfer_asset") or ""
        to_exchange = str(raw.get("to_exchange") or "").lower() in ("true", "yes", "1")
        exch_suffix = "，目标疑似交易所" if to_exchange else ""
        return f"检测到大额 {amount:,.0f} {asset} 转账{exch_suffix}"

    if signal_type == "news_event":
        source_name = raw.get("source") or raw.get("source_name") or "RSS"
        title = raw.get("event_title") or raw.get("title") or ""
        title_short = title[:40] + ("..." if len(title) > 40 else "")
        return f"RSS 源 {source_name} 检测到新闻：{title_short}"

    if signal_type == "risk_alert":
        risk_type = raw.get("risk_type") or "风险"
        status = raw.get("current_status") or raw.get("status") or ""
        return f"{entity} 触发{risk_type}预警：{status}"

    if signal_type == "combo":
        return raw.get("trigger_reason") or f"{entity} 同时触发多类市场信号，已合并为组合卡片"

    source = raw.get("source") or "未知"
    return f"从 {source} 接收到 {signal_type} 信号"


def _extract_hour_bucket(observed_at: str) -> str:
    """从 ISO 时间字符串提取小时桶 YYYY-MM-DD-HH。"""
    try:
        dt = datetime.fromisoformat(observed_at.replace("Z", "+00:00"))
        return dt.strftime("%Y-%m-%d-%H")
    except Exception:
        return "unknown-hour"


# ── 工具函数 ──────────────────────────────────────────────────────────────

def _money(value: float) -> str:
    abs_val = abs(value)
    if abs_val >= 100_000_000:
        return f"{value / 100_000_000:.2f} 亿美元"
    if abs_val >= 10_000:
        return f"{value / 10_000:.2f} 万美元"
    return f"{value:.2f} 美元"


def _format_price(value: float) -> str:
    if value >= 1000:
        return f"{value:,.2f}"
    if value >= 1:
        return f"{value:.2f}"
    return f"{value:.6f}"
