import argparse
import csv
import html
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


FIELDNAMES = [
    "draft_id",
    "candidate_id",
    "published_at_china",
    "asset_symbol",
    "event_type",
    "event_type_label",
    "event_scope",
    "channel_route",
    "confidence_label",
    "strength_stars",
    "amount_usd",
    "severity_tier",
    "alert_priority_score",
    "throttle_key",
    "raw_signal_type",
    "risk_category",
    "needs_model_review",
    "model_review_reason",
    "source",
    "title",
    "url",
    "why_this_matters",
    "watch_next",
    "context_summary",
    "draft_text",
    "draft_status",
    "reviewer_decision",
    "reviewer_usefulness",
    "reviewer_issue_type",
    "reviewer_notes",
    "approved_text",
    "draft_mode",
    "auto_send_enabled",
]


EVENT_TYPE_LABELS = {
    "onchain_transfer": "链上异动",
    "stablecoin_flow": "稳定币流动",
    "whale_position": "巨鲸仓位",
    "cex_netflow": "交易所净流",
    "funding_rate": "资金费率",
    "liquidation": "链上清算",
    "exchange_listing": "交易所上新",
    "token_unlock": "代币解锁",
}

SIGNAL_LABELS = {
    "stablecoin_treasury_in": "金库转入",
    "stablecoin_treasury_out": "金库转出",
    "stablecoin_mint": "增发铸币",
    "stablecoin_burn": "销毁回收",
    "transfer_out": "地址转出",
    "transfer_in": "地址转入",
    "treasury_transfer_out": "项目金库转出",
    "cex_transfer_in": "交易所钱包转入",
    "cex_transfer_out": "交易所钱包转出",
    "hyperliquid_position_long": "Hyperliquid 多头仓位",
    "hyperliquid_position_short": "Hyperliquid 空头仓位",
    "cex_netflow_in": "交易所钱包净流入",
    "cex_netflow_out": "交易所钱包净流出",
    "funding_rate_high_positive": "资金费率明显偏正",
    "funding_rate_high_negative": "资金费率明显偏负",
    "lending_liquidation": "借贷协议清算",
    "cex_listing_announcement": "交易所上新公告",
    "token_unlock_upcoming": "即将解锁",
}

CONFIDENCE_LABELS = {
    "high": "高",
    "medium": "中",
    "low": "低",
    "sample": "样例",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate clean Chinese Telegram drafts from first-hand watcher events.")
    parser.add_argument("--input", default=str(ROOT / "data" / "watcher_events_raw.csv"))
    parser.add_argument("--output", default=str(ROOT / "data" / "tg_drafts_v07_watcher_private_pilot.csv"))
    parser.add_argument("--markdown-output", default=str(ROOT / "results" / "tg_drafts_v07_watcher_private_pilot.md"))
    parser.add_argument("--limit", type=int, default=30)
    return parser.parse_args()


def normalize_path(value: str | Path) -> Path:
    path = Path(value)
    if not path.is_absolute():
        path = ROOT / path
    return path


def read_rows(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_rows(path: Path, rows: list[dict], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def value(row: dict, *names: str) -> str:
    for name in names:
        item = str(row.get(name, "") or "").strip()
        if item:
            return item
    return ""


def amount_float(row: dict) -> float:
    try:
        return float(value(row, "amount_usd") or "0")
    except ValueError:
        return 0.0


def format_usd(amount: float) -> str:
    if amount >= 100_000_000:
        return f"{amount / 100_000_000:.2f} 亿美元"
    if amount >= 10_000:
        return f"{amount / 10_000:.2f} 万美元"
    if amount > 0:
        return f"{amount:,.2f} 美元"
    return "未披露"


def format_usd_short(amount: float) -> str:
    sign = "-" if amount < 0 else ""
    number = abs(amount)
    if number >= 100_000_000:
        return f"{sign}{number / 100_000_000:.2f}亿美元"
    if number >= 10_000:
        return f"{sign}{number / 10_000:.1f}万美元"
    if number > 0:
        return f"{sign}{number:,.0f}美元"
    return "未披露"


def confidence(row: dict) -> str:
    raw = value(row, "confidence").lower()
    return CONFIDENCE_LABELS.get(raw, "中")


def severity_tier(row: dict) -> str:
    event_type = value(row, "event_type")
    amount = amount_float(row)
    if event_type == "exchange_listing":
        return "critical"
    if event_type == "token_unlock":
        return "high" if amount >= 50_000_000 else "watch"
    if event_type == "stablecoin_flow":
        if amount >= 250_000_000:
            return "critical"
        if amount >= 100_000_000:
            return "high"
        return "watch"
    if event_type == "cex_netflow":
        if amount >= 500_000_000:
            return "critical"
        if amount >= 100_000_000:
            return "high"
        return "watch"
    if event_type in {"whale_position", "liquidation"}:
        if amount >= 50_000_000:
            return "critical"
        if amount >= 10_000_000:
            return "high"
    return "watch"


def priority_score(row: dict, severity: str) -> int:
    base = {"critical": 90, "high": 75, "watch": 60, "fyi": 40}.get(severity, 55)
    amount = amount_float(row)
    if amount >= 100_000_000:
        base += 8
    elif amount >= 10_000_000:
        base += 5
    if value(row, "needs_model_review").lower() == "true":
        base -= 8
    return max(1, min(100, base))


def stars(row: dict) -> str:
    amount = amount_float(row)
    event_type = value(row, "event_type")
    score = 3
    if event_type == "exchange_listing":
        score = 5
    elif amount >= 100_000_000:
        score = 5
    elif amount >= 10_000_000:
        score = 4
    elif amount < 1_000_000 and amount > 0:
        score = 2
    return "★" * score + "☆" * (5 - score)


def event_type_label(row: dict) -> str:
    return EVENT_TYPE_LABELS.get(value(row, "event_type"), value(row, "event_type") or "事件")


def signal_label(row: dict) -> str:
    return SIGNAL_LABELS.get(value(row, "raw_signal_type"), value(row, "raw_signal_type") or "监控信号")


def headline(row: dict) -> str:
    asset = value(row, "signal_asset_symbol", "asset_symbol").upper()
    label = event_type_label(row)
    signal = signal_label(row)
    if value(row, "event_type") == "exchange_listing":
        return f"【{label}】{value(row, 'entity_label') or '交易所'} 发布 {asset} 相关上新公告"
    if value(row, "event_type") == "token_unlock":
        return f"【{label}】{asset} 即将发生计划解锁"
    amount = format_usd(amount_float(row))
    return f"【{label}】{asset} {signal}：{amount}"


def why_this_matters(row: dict) -> str:
    event_type = value(row, "event_type")
    signal = value(row, "raw_signal_type")
    if event_type == "exchange_listing":
        return "交易所上新公告通常会带来短时关注度和流动性变化，需要关注公告真实性、上线时间和是否为现货或合约。"
    if event_type == "token_unlock":
        return "解锁属于已知供应事件，重点看规模、流通占比、解锁时间和市场是否提前反应。"
    if event_type == "stablecoin_flow":
        return "稳定币大额流动代表资金供给或金库调拨变化，需要结合后续链上流向、交易所净流和市场风险偏好观察。"
    if event_type == "cex_netflow":
        return "交易所净流入/流出可反映短期资金迁移，需要结合历史基线判断是否异常。"
    if event_type == "whale_position":
        return "大额仓位变化会影响市场结构，重点看仓位增减、强平距离和是否与资金流同向。"
    if event_type == "liquidation":
        return "大额清算说明杠杆结构出现压力，重点看是否引发连续清算或波动放大。"
    if signal == "treasury_transfer_out":
        return "项目金库转出需要确认用途和去向，重点看是否进入交易所、做市地址或合约交互。"
    return "该事件来自结构化监控源，重点看金额、时间、实体和后续是否出现价格或成交量异动。"


def watch_next(row: dict) -> str:
    event_type = value(row, "event_type")
    if event_type == "exchange_listing":
        return "关注公告链接、上线交易对、开盘时间、是否触发同类资产跟随。"
    if event_type == "token_unlock":
        return "关注解锁前后 4h/24h 价格、成交量、交易所流入和持仓变化。"
    if event_type == "stablecoin_flow":
        return "关注后续是否进入交易所、CEX 净流是否同步放大。"
    if event_type == "cex_netflow":
        return "关注同一交易所后续 1h/4h 净流是否继续扩大。"
    if event_type == "whale_position":
        return "关注仓位是否继续增加、是否接近强平价、其他大户是否同步。"
    return "关注后续 4h/24h 是否出现价格、成交量或链上流向变化。"


def raw_payload(row: dict) -> dict:
    text = value(row, "raw_json")
    if not text:
        return {}
    try:
        payload = json.loads(text)
        return payload if isinstance(payload, dict) else {}
    except Exception:
        return {}


def utc_iso_to_china_text(value: str) -> str:
    raw = str(value or "").strip()
    if not raw:
        return ""
    if raw.endswith("Z"):
        raw = raw[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(raw)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone(timedelta(hours=8))).strftime("%Y-%m-%d %H:%M:%S UTC+8")
    except Exception:
        return ""


def token_unlock_time_china(row: dict) -> str:
    payload = raw_payload(row)
    return utc_iso_to_china_text(str(payload.get("unlock_time_utc", "") or ""))


def hours_until_utc(value: str) -> float | None:
    raw = str(value or "").strip()
    if not raw:
        return None
    if raw.endswith("Z"):
        raw = raw[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(raw)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return (dt.astimezone(timezone.utc) - datetime.now(timezone.utc)).total_seconds() / 3600
    except Exception:
        return None


def format_hours_until(hours: float | None) -> str:
    if hours is None:
        return ""
    if hours < 0:
        return "已发生"
    if hours < 1:
        return f"{int(max(1, hours * 60))} 分钟内"
    if hours < 48:
        return f"约 {hours:.1f} 小时后"
    return f"约 {hours / 24:.1f} 天后"


def format_pct(value: str) -> str:
    try:
        number = float(str(value or "").strip())
    except Exception:
        return ""
    return f"{number:.2f}%"


def clean_entity(value_: str) -> str:
    raw = str(value_ or "").strip()
    if not raw:
        return ""
    if "unknown" in raw.lower():
        return ""
    if raw.startswith("first_hand:"):
        return ""
    if raw in {"coinmarketcap_token_unlocks", "scheduled_unlock"}:
        return ""
    if raw.startswith("0x") and len(raw) > 12:
        return ""
    return raw


def display_entity(row: dict) -> str:
    entity = clean_entity(value(row, "entity_label"))
    if entity:
        return entity
    source = value(row, "watcher_source", "source")
    mapping = {
        "hyperliquid_clearinghouse_state": "Hyperliquid",
        "token_unlock_calendar": "Token Unlocks",
        "first_hand:hyperliquid_clearinghouse_state": "Hyperliquid",
        "first_hand:token_unlock_calendar": "Token Unlocks",
    }
    return mapping.get(source, source or "监控源")


def display_china_time(value_: str) -> str:
    return str(value_ or "").replace("UTC+8", "北京时间").strip()


def position_side(row: dict) -> str:
    signal = value(row, "raw_signal_type").lower()
    if "short" in signal:
        return "空头"
    if "long" in signal:
        return "多头"
    payload = raw_payload(row)
    current = payload.get("current", {}) if isinstance(payload, dict) else {}
    position = current.get("position", {}) if isinstance(current, dict) else {}
    try:
        size = float(str(position.get("szi") or "0"))
    except Exception:
        size = 0.0
    if size < 0:
        return "空头"
    if size > 0:
        return "多头"
    return "仓位"


def position_current_price(position: dict) -> float:
    try:
        amount = float(str(position.get("positionValue") or "0"))
        size = abs(float(str(position.get("szi") or "0")))
    except Exception:
        return 0.0
    if amount and size:
        return amount / size
    return 0.0


def position_liq_distance_pct(row: dict) -> float:
    payload = raw_payload(row)
    current = payload.get("current", {}) if isinstance(payload, dict) else {}
    position = current.get("position", {}) if isinstance(current, dict) else {}
    current_px = position_current_price(position)
    try:
        liq_px = float(str(position.get("liquidationPx") or "0"))
    except Exception:
        liq_px = 0.0
    if not current_px or not liq_px:
        return 0.0
    side = position_side(row)
    if side == "多头":
        return (current_px - liq_px) / current_px * 100
    if side == "空头":
        return (liq_px - current_px) / current_px * 100
    return abs(current_px - liq_px) / current_px * 100


def position_pnl(row: dict) -> float:
    payload = raw_payload(row)
    current = payload.get("current", {}) if isinstance(payload, dict) else {}
    position = current.get("position", {}) if isinstance(current, dict) else {}
    try:
        return float(str(position.get("unrealizedPnl") or "0"))
    except Exception:
        return 0.0


def allocation_name_cn(value_: str) -> str:
    raw = str(value_ or "").lower()
    if "core" in raw or "team" in raw or "advisor" in raw or "contractor" in raw:
        return "团队/贡献者"
    if "backer" in raw or "investor" in raw or "private" in raw or "strategic" in raw:
        return "早期投资人"
    if "community" in raw or "airdrop" in raw:
        return "社区"
    if "ecosystem" in raw:
        return "生态激励"
    return str(value_ or "").strip()


def top_allocation_line(row: dict) -> str:
    payload = raw_payload(row)
    notes = str(payload.get("notes", "") or "")
    if "allocations=" not in notes:
        return ""
    raw = notes.split("allocations=", 1)[1].split("; ", 1)[0]
    parts = []
    for chunk in raw.split(";"):
        if ":" not in chunk:
            continue
        name, amount = chunk.split(":", 1)
        try:
            amount_value = float(amount.replace("$", "").replace(",", "").strip())
        except Exception:
            amount_value = 0.0
        parts.append((amount_value, allocation_name_cn(name.strip())))
    if not parts:
        return ""
    parts.sort(reverse=True, key=lambda item: item[0])
    return f"主要释放给{parts[0][1]}"


def extra_detail_lines(row: dict) -> list[str]:
    event_type = value(row, "event_type")
    payload = raw_payload(row)
    lines: list[str] = []
    if event_type == "token_unlock":
        unlock_time = str(payload.get("unlock_time_utc", "") or "")
        eta = format_hours_until(hours_until_utc(unlock_time))
        pct = format_pct(value(row, "amount_native"))
        if eta:
            lines.append(f"⏳ <b>距离：</b>{html_text(eta)}")
        if pct:
            lines.append(f"📊 <b>流通占比：</b>{html_text(pct)}")
        notes = str(payload.get("notes", "") or "")
        if "allocations=" in notes:
            alloc = notes.split("allocations=", 1)[1].split("; ", 1)[0]
            if alloc:
                lines.append(f"🧾 <b>释放对象：</b>{html_text(alloc[:120])}")
    elif event_type == "cex_netflow":
        net = payload.get("net_usd")
        inflow = payload.get("inflow_usd")
        outflow = payload.get("outflow_usd")
        samples = payload.get("baseline_samples")
        multiple = payload.get("abnormal_multiple")
        gate = payload.get("alert_gate")
        if net is not None:
            direction = "净流入" if float(net) > 0 else "净流出"
            lines.append(f"🧭 <b>方向：</b>{direction}")
        if inflow is not None and outflow is not None:
            lines.append(f"📥 <b>流入/流出：</b>{html_text(format_usd(float(inflow)))} / {html_text(format_usd(float(outflow)))}")
        if samples:
            multiple_text = f"{float(multiple):.2f}x" if multiple not in {None, ""} else "暂无"
            lines.append(f"📈 <b>历史基线：</b>{samples} 个样本，当前约 {multiple_text}")
        if gate:
            lines.append(f"🧪 <b>触发：</b>{html_text(str(gate))}")
    elif event_type == "whale_position":
        change_type = str(payload.get("change_type", "") or "")
        delta = payload.get("delta_usd")
        change_pct = payload.get("change_pct")
        current = payload.get("current", {}) if isinstance(payload, dict) else {}
        position = current.get("position", {}) if isinstance(current, dict) else {}
        side = value(row, "raw_signal_type").replace("hyperliquid_position_", "")
        if side:
            lines.append(f"🧭 <b>方向：</b>{'多头' if side == 'long' else '空头' if side == 'short' else html_text(side)}")
        if change_type:
            label = {
                "position_snapshot": "当前大仓位快照",
                "first_seen": "首次发现",
                "position_increased": "仓位增加",
                "position_decreased": "仓位减少",
                "near_liquidation": "接近强平",
                "direction_changed": "方向切换",
                "crossed_threshold": "超过监控阈值",
            }.get(change_type, change_type)
            lines.append(f"📍 <b>变化：</b>{html_text(label)}")
        if delta not in {None, ""} and abs(float(delta)) > 0:
            lines.append(f"📐 <b>变化额：</b>{html_text(format_usd(float(delta)))}")
        if change_pct not in {None, ""} and abs(float(change_pct)) > 0:
            lines.append(f"📊 <b>变化比例：</b>{float(change_pct) * 100:.2f}%")
        liq = current.get("liquidation_distance_pct") if isinstance(current, dict) else ""
        if liq:
            lines.append(f"🧯 <b>强平距离：</b>{float(liq) * 100:.2f}%")
        entry_px = position.get("entryPx") if isinstance(position, dict) else ""
        liq_px = position.get("liquidationPx") if isinstance(position, dict) else ""
        if entry_px or liq_px:
            lines.append(f"🎯 <b>入场/强平：</b>{html_text(str(entry_px or ''))} / {html_text(str(liq_px or ''))}")
    return lines


def concise_headline(row: dict) -> str:
    event_type = value(row, "event_type")
    asset = value(row, "signal_asset_symbol", "asset_symbol").upper()
    amount = amount_float(row)
    entity = clean_entity(value(row, "entity_label"))
    if event_type == "whale_position":
        actor = entity or "链上大户"
        return f"{actor} {asset}{position_side(row)}仓位异动"
    if event_type == "token_unlock":
        return f"{asset}解锁预警"
    if event_type == "stablecoin_flow":
        actor = entity or "稳定币发行方"
        return f"{actor}{asset}大额流动"
    if event_type == "cex_netflow":
        actor = entity or "交易所"
        return f"{asset}大额流入{actor}" if "in" in value(row, "raw_signal_type") else f"{asset}交易所资金异动"
    if event_type == "exchange_listing":
        return f"{asset}交易所公告"
    label = event_type_label(row)
    return f"{asset}{label}｜{format_usd_short(amount)}"


def key_fact_lines(row: dict) -> list[str]:
    event_type = value(row, "event_type")
    asset = value(row, "signal_asset_symbol", "asset_symbol").upper()
    amount = amount_float(row)
    entity = display_entity(row)
    lines: list[str] = []
    if event_type == "whale_position":
        side = position_side(row)
        pnl = position_pnl(row)
        liq_dist = position_liq_distance_pct(row)
        if clean_entity(value(row, "entity_label")):
            lines.append(f"{entity}持有{asset}{side}{format_usd_short(amount)}。")
        else:
            lines.append(f"某地址在{entity}持有{asset}{side}{format_usd_short(amount)}。")
        if pnl:
            pnl_label = "浮盈" if pnl > 0 else "浮亏"
            lines.append(f"当前{pnl_label}{format_usd_short(abs(pnl))}。")
        if liq_dist:
            lines.append(f"距离爆仓约{liq_dist:.1f}%。")
        return lines
    if event_type == "token_unlock":
        unlock_china = display_china_time(token_unlock_time_china(row))
        pct = format_pct(value(row, "amount_native"))
        eta = format_hours_until(hours_until_utc(str(raw_payload(row).get("unlock_time_utc", "") or "")))
        lines.append(f"{asset}将在{unlock_china or '计划时间'}解锁{format_usd_short(amount)}。")
        if pct:
            lines.append(f"规模约占当前流通{pct}。")
        if eta:
            lines.append(f"距离发生：{eta}。")
        allocation = top_allocation_line(row)
        if allocation:
            lines.append(f"{allocation}。")
        return lines
    if event_type == "stablecoin_flow":
        signal = signal_label(row)
        lines.append(f"{entity}出现{asset}{signal}，规模{format_usd_short(amount)}。")
        return lines
    if event_type == "cex_netflow":
        direction = "净流入" if "in" in value(row, "raw_signal_type") else "净流出" if "out" in value(row, "raw_signal_type") else "净流变化"
        lines.append(f"{asset}在{entity}出现{direction}，规模{format_usd_short(amount)}。")
        return lines
    lines.append(f"{event_type_label(row)}：{asset}，规模{format_usd_short(amount)}。")
    return lines


def focus_line(row: dict) -> str:
    event_type = value(row, "event_type")
    if event_type == "whale_position":
        liq_dist = position_liq_distance_pct(row)
        if 0 < liq_dist <= 5:
            return f"爆仓距离很近，后续重点看是否触发连锁清算。"
        payload = raw_payload(row)
        change_type = str(payload.get("change_type", "") or "")
        if change_type and change_type != "position_snapshot":
            return "这是仓位变化，不是普通快照；后续看是否继续加减仓。"
        return "这是静态大仓位快照，只有继续变化或接近爆仓时才值得升级提醒。"
    if event_type == "token_unlock":
        return "重点看解锁前后交易所流入、成交量和价格是否已提前反应。"
    if event_type == "stablecoin_flow":
        return "单笔稳定币流动不等于方向判断，重点看后续是否进入交易所或持续放大。"
    if event_type == "cex_netflow":
        return "只有持续高于历史基线时才更值得关注，单次流入/流出不直接代表方向。"
    if event_type == "exchange_listing":
        return "重点核对公告交易对、上线时间和是否已被市场提前消化。"
    return ""


def source_url(row: dict) -> str:
    payload = raw_payload(row)
    article = payload.get("article", {}) if isinstance(payload, dict) else {}
    if isinstance(article, dict) and article.get("code"):
        return f"https://www.binance.com/en/support/announcement/{article.get('code')}"
    return ""


def html_text(text: str) -> str:
    return html.escape(str(text or ""), quote=False)


def draft_text(row: dict) -> tuple[str, str, str]:
    title = concise_headline(row)
    label = event_type_label(row)
    asset = value(row, "signal_asset_symbol", "asset_symbol").upper()
    entity = display_entity(row)
    amount = format_usd(amount_float(row))
    event_type = value(row, "event_type")
    observed_china = value(row, "event_time_china", "published_at_china")
    unlock_china = token_unlock_time_china(row) if event_type == "token_unlock" else ""
    time_label = "预计解锁" if event_type == "token_unlock" and unlock_china else "时间"
    time_china = display_china_time(unlock_china or observed_china)
    reason = focus_line(row)
    next_text = watch_next(row)
    url = source_url(row)
    tx = value(row, "tx_hash")
    lines = [
        f"<b>⚡ {html_text(title)}</b>",
        "",
        f"<b>时间：</b>{html_text(time_china)}",
        f"<b>主体：</b>{html_text(entity)}",
        f"<b>类型：</b>{html_text(label)}",
        f"<b>规模：</b>{html_text(amount)}",
        "",
        "<b>关键事实：</b>",
    ]
    lines.extend(f"• {html_text(item)}" for item in key_fact_lines(row))
    if event_type == "token_unlock" and observed_china and unlock_china:
        lines.append(f"• 发现时间：{html_text(display_china_time(observed_china))}")
    if reason:
        lines.extend(["", f"<b>关注点：</b>{html_text(reason)}"])
    if tx:
        lines.append(f"🔗 <b>Tx：</b>{html_text(tx[:18])}...")
    if url:
        lines.append(f"🔗 <b>来源：</b>{html_text(url)}")
    lines.extend(["", "仅供市场观察，不构成交易建议。"])
    return "\n".join(lines), reason, next_text


def build_row(index: int, row: dict) -> dict:
    severity = severity_tier(row)
    score = priority_score(row, severity)
    text, reason, next_text = draft_text(row)
    candidate_id = value(row, "event_id") or f"watcher_event_{index:04d}"
    asset = value(row, "asset_symbol").upper()
    event_type = value(row, "event_type")
    return {
        "draft_id": f"tg_watcher_{index:04d}",
        "candidate_id": candidate_id,
        "published_at_china": value(row, "event_time_china"),
        "asset_symbol": asset,
        "event_type": event_type,
        "event_type_label": event_type_label(row),
        "event_scope": "single_asset" if asset else "unknown",
        "channel_route": "realtime" if severity in {"critical", "high"} else "digest_or_realtime",
        "confidence_label": confidence(row),
        "strength_stars": stars(row),
        "amount_usd": value(row, "amount_usd"),
        "severity_tier": severity,
        "alert_priority_score": score,
        "throttle_key": f"{event_type}:{asset}",
        "raw_signal_type": value(row, "raw_signal_type"),
        "risk_category": value(row, "risk_category"),
        "needs_model_review": value(row, "needs_model_review"),
        "model_review_reason": value(row, "model_review_reason"),
        "source": value(row, "source"),
        "title": headline(row),
        "url": source_url(row),
        "why_this_matters": reason,
        "watch_next": next_text,
        "context_summary": reason,
        "draft_text": text,
        "draft_status": "ready",
        "reviewer_decision": "",
        "reviewer_usefulness": "",
        "reviewer_issue_type": "",
        "reviewer_notes": "",
        "approved_text": "",
        "draft_mode": "watcher_realtime_preview",
        "auto_send_enabled": "false",
    }


def render_markdown(rows: list[dict]) -> str:
    lines = [
        "# v0.7 Watcher TG Draft Preview",
        "",
        "Local preview only. It does not send Telegram messages.",
        "",
    ]
    for row in rows:
        lines.extend([f"## {row['draft_id']}", "", row["draft_text"], ""])
    return "\n".join(lines)


def main() -> int:
    args = parse_args()
    events = read_rows(normalize_path(args.input))[: args.limit]
    rows = [build_row(index, row) for index, row in enumerate(events, start=1)]
    output_path = normalize_path(args.output)
    write_rows(output_path, rows, FIELDNAMES)
    markdown_path = normalize_path(args.markdown_output)
    markdown_path.parent.mkdir(parents=True, exist_ok=True)
    markdown_path.write_text(render_markdown(rows), encoding="utf-8")
    print(f"draft_count={len(rows)}")
    print(f"wrote_output={output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
