import argparse
import csv
import html
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests


ROOT = Path(__file__).resolve().parents[1]


try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass


BOARD_COLUMNS = [
    "board_id",
    "generated_at_china",
    "board_label",
    "source_rows",
    "section_count",
    "item_count",
    "top_section",
    "board_text",
]


SUMMARY_COLUMNS = [
    "status",
    "generated_at_china",
    "board_id",
    "board_label",
    "source_rows",
    "section_count",
    "item_count",
    "hyperliquid_rows",
    "token_unlock_rows",
    "long_short_rows",
    "flow_rows",
    "price_context_rows",
    "repeat_suppressed_rows",
    "policy_boosted_rows",
    "policy_review_rows",
    "policy_collect_more_rows",
    "policy_digest_only_rows",
    "policy_digest_filtered_rows",
    "policy_downranked_rows",
    "dynamic_boosted_rows",
    "decision_log_rows",
    "readability_status",
    "readability_flags",
    "output",
    "markdown_output",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a compact Telegram market-radar board from watcher outputs.")
    parser.add_argument("--watcher-events", default=str(ROOT / "data" / "watcher_events_raw.csv"))
    parser.add_argument("--hyperliquid-alerts", default=str(ROOT / "data" / "watcher_alerts_hyperliquid_positions.csv"))
    parser.add_argument("--token-unlock-alerts", default=str(ROOT / "data" / "watcher_alerts_token_unlocks.csv"))
    parser.add_argument("--long-short-snapshot", default=str(ROOT / "data" / "binance_long_short_snapshot.csv"))
    parser.add_argument("--output", default=str(ROOT / "data" / "tg_market_radar_boards.csv"))
    parser.add_argument("--markdown-output", default=str(ROOT / "results" / "v09_tg_market_radar_board.md"))
    parser.add_argument("--summary", default=str(ROOT / "results" / "v09_tg_market_radar_board_summary.csv"))
    parser.add_argument("--history-state", default=str(ROOT / "data" / "tg_radar_item_state.csv"))
    parser.add_argument("--decision-log", default=str(ROOT / "data" / "tg_radar_decision_log.csv"))
    parser.add_argument("--board-label", default="auto")
    parser.add_argument("--max-items", type=int, default=5)
    parser.add_argument("--max-priority-items", type=int, default=2)
    parser.add_argument("--max-context-items", type=int, default=3)
    parser.add_argument("--max-hyperliquid", type=int, default=3)
    parser.add_argument("--max-unlocks", type=int, default=1)
    parser.add_argument("--max-long-short", type=int, default=2)
    parser.add_argument("--max-flows", type=int, default=2)
    parser.add_argument("--min-hyperliquid-usd", type=float, default=10_000_000)
    parser.add_argument("--min-unlock-usd", type=float, default=10_000_000)
    parser.add_argument("--min-unlock-pct", type=float, default=5.0)
    parser.add_argument("--min-unlock-usd-if-pct", type=float, default=1_000_000)
    parser.add_argument("--min-flow-usd", type=float, default=500_000_000)
    parser.add_argument("--min-stablecoin-flow-usd", type=float, default=500_000_000)
    parser.add_argument("--min-crowding-score", type=float, default=60.0)
    parser.add_argument("--max-line-chars", type=int, default=52)
    parser.add_argument("--repeat-hours-static-position", type=float, default=4.0)
    parser.add_argument("--repeat-hours-token-unlock", type=float, default=8.0)
    parser.add_argument("--repeat-hours-indicator", type=float, default=2.0)
    parser.add_argument("--repeat-hours-flow", type=float, default=1.0)
    parser.add_argument("--include-price-context", default="true")
    parser.add_argument("--signal-policy", default=str(ROOT / "data" / "tg_signal_policy_from_history.csv"))
    parser.add_argument("--live-signal-policy", default=str(ROOT / "data" / "tg_signal_policy_live.csv"))
    parser.add_argument("--v11-signal-policy", default=str(ROOT / "data" / "tg_signal_policy_v11.csv"))
    parser.add_argument("--v12-signal-policy", default=str(ROOT / "data" / "tg_signal_policy_v12.csv"))
    return parser.parse_args()


def normalize_path(value: str | Path) -> Path:
    path = Path(value)
    if not path.is_absolute():
        path = ROOT / path
    return path


def china_now() -> datetime:
    return datetime.now(timezone(timedelta(hours=8))).replace(microsecond=0)


def china_stamp(dt: datetime | None = None) -> str:
    return (dt or china_now()).strftime("%Y-%m-%d %H:%M:%S UTC+8")


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


def append_rows(path: Path, rows: list[dict], fieldnames: list[str]) -> None:
    existing = read_rows(path)
    existing.extend(rows)
    merged_fields = list(fieldnames)
    for row in existing:
        for key in row.keys():
            if key not in merged_fields:
                merged_fields.append(key)
    write_rows(path, existing, merged_fields)


def ensure_columns(path: Path, fieldnames: list[str]) -> None:
    if not path.exists():
        return
    existing = read_rows(path)
    merged_fields = list(fieldnames)
    for row in existing:
        for key in row.keys():
            if key not in merged_fields:
                merged_fields.append(key)
    write_rows(path, existing, merged_fields)


def safe_float(value) -> float:
    try:
        return float(str(value or "").strip())
    except Exception:
        return 0.0


def safe_json(value: str) -> dict:
    raw = str(value or "").strip()
    if not raw:
        return {}
    try:
        obj = json.loads(raw)
        return obj if isinstance(obj, dict) else {}
    except Exception:
        return {}


def load_signal_policy(path: Path) -> dict[str, dict[str, dict]]:
    policies = {
        "source": {},
        "event_type": {},
        "event_subtype": {},
        "source_type": {},
        "repeat_group": {},
    }
    source_policy: dict[str, dict] = {}
    event_policy: dict[str, dict] = {}
    for row in read_rows(path):
        scope = str(row.get("policy_scope") or "").strip()
        name = str(row.get("name") or "").strip()
        if not scope or not name:
            continue
        if scope in policies:
            policies[scope][name.lower()] = row
    return policies


def merge_policy_sets(*sets: dict[str, dict[str, dict]]) -> dict[str, dict[str, dict]]:
    merged = {
        "source": {},
        "event_type": {},
        "event_subtype": {},
        "source_type": {},
        "repeat_group": {},
    }
    for policy_set in sets:
        for scope, rows in policy_set.items():
            if scope in merged:
                merged[scope].update(rows)
    return merged


def policy_event_type(source_type: str) -> str:
    mapping = {
        "hyperliquid": "whale_position",
        "token_unlock": "token_unlock",
        "long_short": "market_structure",
        "cex_netflow": "cex_netflow",
        "stablecoin_flow": "stablecoin_flow",
    }
    return mapping.get(str(source_type or "").strip(), "")


def item_event_subtype(item: dict) -> str:
    source = str(item.get("source_type") or "")
    group = str(item.get("repeat_group") or "")
    if source == "token_unlock":
        return "token_unlock_team_large"
    if source == "long_short":
        return "long_short_crowding_extreme"
    if group == "static_position":
        return "whale_position_static_large"
    if group == "position_change":
        return "whale_position_size_change"
    if source == "cex_netflow":
        return "cex_netflow_inflow_spike"
    if source == "stablecoin_flow":
        return "stablecoin_cex_inflow"
    return ""


def policy_for_item(item: dict, policies: dict[str, dict[str, dict]]) -> dict:
    source_key = str(item.get("source_type") or "").lower()
    repeat_key = str(item.get("repeat_group") or "").lower()
    subtype_key = item_event_subtype(item).lower()
    event_key = policy_event_type(source_key).lower()
    for scope, key in [
        ("event_subtype", subtype_key),
        ("repeat_group", repeat_key),
        ("source_type", source_key),
        ("source", source_key),
        ("event_type", event_key),
    ]:
        if key and policies.get(scope, {}).get(key):
            return policies[scope][key]
    return {}


def apply_signal_policy(items: list[dict], policies: dict[str, dict[str, dict]]) -> dict[str, int]:
    counts = {"boost": 0, "review": 0, "collect_more": 0, "digest_only": 0, "downrank": 0}
    for item in items:
        policy = policy_for_item(item, policies)
        if not policy:
            item["policy_action"] = ""
            item["policy_reason_cn"] = ""
            continue
        action = str(policy.get("tg_action") or "").strip()
        item["policy_action"] = action
        item["policy_reason_cn"] = str(policy.get("reason_cn") or "").strip()
        priority_delta_raw = str(policy.get("priority_delta") or "").strip()
        if priority_delta_raw:
            item["priority"] = float(item.get("priority") or 0) + safe_float(priority_delta_raw)
        cooldown_multiplier_raw = str(policy.get("cooldown_multiplier") or "").strip()
        if cooldown_multiplier_raw:
            item["cooldown_multiplier"] = cooldown_multiplier_raw
        if action == "boost":
            if not priority_delta_raw:
                item["priority"] = float(item.get("priority") or 0) + 12
            item["text"] = f"{item.get('text', '')}\n  历史回测：同类来源优先扩样本"
            counts["boost"] += 1
        elif action == "digest_only":
            if not priority_delta_raw:
                item["priority"] = float(item.get("priority") or 0) - 35
            item["section"] = "context"
            counts["digest_only"] += 1
        elif action == "downrank":
            if not priority_delta_raw:
                item["priority"] = float(item.get("priority") or 0) - 20
            counts["downrank"] += 1
        elif action == "review_benchmark":
            if not priority_delta_raw:
                item["priority"] = float(item.get("priority") or 0) - 5
            counts["review"] += 1
        elif action == "collect_more":
            item["text"] = f"{item.get('text', '')}\n  样本状态：继续收集，不做强结论"
            counts["collect_more"] += 1
    return counts


def allow_digest_only_now(now: datetime) -> bool:
    hour = now.hour
    return hour < 10 or hour >= 18


def filter_digest_only_items(items: list[dict], now: datetime) -> tuple[list[dict], int, list[dict]]:
    if allow_digest_only_now(now):
        return items, 0, []
    kept = []
    filtered_items = []
    filtered = 0
    for item in items:
        action = str(item.get("policy_action") or "")
        priority = float(item.get("priority") or 0)
        if action == "digest_only" and priority < 130:
            filtered += 1
            filtered_items.append(item)
            continue
        kept.append(item)
    return kept, filtered, filtered_items


def dynamic_boost_for_item(item: dict) -> tuple[float, str]:
    source = str(item.get("source_type") or "")
    group = str(item.get("repeat_group") or "")
    text = str(item.get("text") or "")
    priority = float(item.get("priority") or 0)
    if group == "position_change":
        return 25.0, "动仓优先"
    if "爆仓" in text or "清算" in text or "距爆仓" in text:
        return 30.0, "接近清算"
    if source in {"cex_netflow", "stablecoin_flow"}:
        if priority >= 110:
            return 22.0, "资金流突变"
        return 12.0, "资金流观察"
    if source == "long_short":
        if priority >= 130:
            return 18.0, "极端拥挤"
        return 8.0, "拥挤变化"
    return 0.0, ""


def apply_dynamic_boost(items: list[dict]) -> int:
    boosted = 0
    for item in items:
        boost, reason = dynamic_boost_for_item(item)
        if boost <= 0:
            continue
        item["priority"] = float(item.get("priority") or 0) + boost
        item["dynamic_boost_reason"] = reason
        if reason and reason not in str(item.get("text") or ""):
            item["text"] = f"{item.get('text', '')}\n  动态提权：{reason}"
        boosted += 1
    return boosted


def truthy(value: str) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "y"}


def h(value) -> str:
    return html.escape(str(value or ""), quote=False)


def usd_short(value) -> str:
    number = safe_float(value)
    sign = "-" if number < 0 else ""
    number = abs(number)
    if number >= 1_000_000_000:
        return f"{sign}${number / 1_000_000_000:.2f}B"
    if number >= 1_000_000:
        return f"{sign}${number / 1_000_000:.1f}M"
    if number >= 1_000:
        return f"{sign}${number / 1_000:.1f}K"
    if number:
        return f"{sign}${number:.0f}"
    return "-"


def pct_short(value, suffix: str = "%") -> str:
    number = safe_float(value)
    if not number:
        return "-"
    return f"{number:.2f}{suffix}"


def utc_to_china_label(value: str) -> str:
    raw = str(value or "").strip()
    if not raw:
        return "-"
    try:
        if raw.endswith("Z"):
            dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        else:
            dt = datetime.fromisoformat(raw)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone(timedelta(hours=8))).strftime("%m-%d %H:%M UTC+8")
    except Exception:
        return raw.replace("T", " ").replace("Z", " UTC")


def utc_to_china_short(value: str, now: datetime | None = None) -> str:
    raw = str(value or "").strip()
    if not raw:
        return ""
    try:
        if raw.endswith("Z"):
            dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        else:
            dt = datetime.fromisoformat(raw)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
        china_dt = dt.astimezone(timezone(timedelta(hours=8)))
        base = (now or china_now()).date()
        if china_dt.date() == base:
            prefix = "今日"
        elif china_dt.date() == base + timedelta(days=1):
            prefix = "明日"
        else:
            prefix = china_dt.strftime("%m-%d")
        return f"{prefix}{china_dt.strftime('%H:%M')}"
    except Exception:
        return utc_to_china_label(value)


def board_label(value: str) -> str:
    if value and value != "auto":
        return value
    hour = china_now().hour
    if 7 <= hour < 10:
        return "早间雷达"
    if 10 <= hour < 14:
        return "午间雷达"
    if 14 <= hour < 18:
        return "盘中雷达"
    if 18 <= hour < 24:
        return "晚间雷达"
    return "夜间雷达"


def side_label(metric_type: str, raw: dict) -> str:
    metric = str(metric_type or "").lower()
    if "short" in metric:
        return "空头"
    if "long" in metric:
        return "多头"
    pos = raw.get("current", {}).get("position", {}) if isinstance(raw.get("current"), dict) else {}
    size = safe_float(pos.get("szi"))
    if size < 0:
        return "空头"
    if size > 0:
        return "多头"
    return "仓位"


def short_address(value: str) -> str:
    raw = str(value or "").strip()
    if len(raw) <= 12:
        return raw or "-"
    return f"{raw[:6]}...{raw[-4:]}"


def clean_entity(value: str) -> str:
    raw = str(value or "").strip()
    if not raw or "unknown" in raw.lower():
        return ""
    return raw


def price_from_position(pos: dict) -> float:
    amount = safe_float(pos.get("positionValue"))
    size = abs(safe_float(pos.get("szi")))
    if amount and size:
        return amount / size
    return 0.0


def liquidation_distance_pct(pos: dict, side: str) -> float:
    current = price_from_position(pos)
    liq = safe_float(pos.get("liquidationPx"))
    if not current or not liq:
        return 0.0
    if side == "多头":
        return (current - liq) / current * 100
    if side == "空头":
        return (liq - current) / current * 100
    return abs(current - liq) / current * 100


def pnl_phrase(value) -> str:
    pnl = safe_float(value)
    if not pnl:
        return ""
    label = "浮盈" if pnl > 0 else "浮亏"
    return f"{label}{usd_short(abs(pnl))}"


def top_allocation_cn(notes: str) -> str:
    text = str(notes or "")
    if "allocations=" not in text:
        return ""
    raw = text.split("allocations=", 1)[1].split("; ", 1)[0].strip()
    parts = []
    for chunk in raw.split(";"):
        chunk = chunk.strip()
        if not chunk or ":" not in chunk:
            continue
        name, amount = chunk.split(":", 1)
        cn_name = allocation_name_cn(name.strip())
        parts.append((safe_float(amount.replace("$", "").replace(",", "")), cn_name))
    if not parts:
        return ""
    parts.sort(reverse=True, key=lambda item: item[0])
    top = parts[0][1]
    return f"主要释放给{top}" if top else ""


def allocation_name_cn(value: str) -> str:
    raw = value.lower()
    if "core" in raw or "team" in raw or "advisor" in raw or "contractor" in raw:
        return "团队/贡献者"
    if "backer" in raw or "investor" in raw or "private" in raw or "strategic" in raw:
        return "早期投资人"
    if "community" in raw or "airdrop" in raw:
        return "社区"
    if "ecosystem" in raw:
        return "生态激励"
    return value


def signal_item(
    section: str,
    priority: float,
    text: str,
    source_type: str,
    item_key: str,
    asset: str = "",
    repeat_group: str = "",
) -> dict:
    return {
        "section": section,
        "priority": priority,
        "text": text,
        "source_type": source_type,
        "item_key": item_key,
        "asset": asset,
        "repeat_group": repeat_group or source_type,
    }


def hyperliquid_items(rows: list[dict], limit: int, min_usd: float) -> list[dict]:
    candidates = []
    for row in rows:
        amount = safe_float(row.get("amount_usd"))
        if amount < min_usd:
            continue
        raw = safe_json(row.get("raw_json", ""))
        pos = raw.get("current", {}).get("position", {}) if isinstance(raw.get("current"), dict) else {}
        asset = str(row.get("asset_symbol") or "-").upper()
        side = side_label(row.get("metric_type", ""), raw)
        entity = clean_entity(row.get("primary_entity", ""))
        change_type = str(raw.get("change_type") or "")
        change_pct = abs(safe_float(raw.get("change_pct")))
        delta_usd = abs(safe_float(raw.get("delta_usd")))
        liq_dist = liquidation_distance_pct(pos, side)
        pnl = pnl_phrase(pos.get("unrealizedPnl"))

        is_notable_change = change_type not in {"", "position_snapshot"} and (change_pct >= 0.5 or delta_usd >= 10_000_000)
        is_near_liq = 0 < liq_dist <= 5
        known_large_unusual = bool(entity) and amount >= 75_000_000 and asset not in {"BTC", "ETH"}
        if not (is_near_liq or is_notable_change or known_large_unusual):
            continue

        actor = f"{entity}" if entity else "监控大户"
        claim_bits = [f"{asset}{side}{usd_short(amount)}"]
        if pnl:
            claim_bits.append(pnl)
        if is_near_liq:
            claim_bits.append(f"距清算价{liq_dist:.1f}%")
            section = "priority"
            priority = 100 + amount / 1_000_000
        elif is_notable_change:
            verb = "仓位变化"
            if "increase" in change_type:
                verb = "加仓"
            elif "decrease" in change_type:
                verb = "减仓"
            claim_bits.append(verb)
            section = "priority" if amount >= 50_000_000 else "context"
            priority = 85 + amount / 2_000_000
        else:
            claim_bits.append("已知实体大仓位")
            section = "context"
            priority = 65 + amount / 3_000_000
        if is_near_liq:
            text = f"{actor} {asset}{side} {usd_short(amount)}\n  {pnl or '有清算风险'}，距清算价{liq_dist:.1f}%"
        elif is_notable_change:
            text = f"{actor} {asset}{side}仓位变化 {usd_short(amount)}\n  {pnl or '变化较大'}，需看是否连续调整"
        else:
            text = f"{actor} {asset}{side} {usd_short(amount)}\n  {pnl or '大额敞口'}，静态大仓位"
        address = str(row.get("primary_address") or "").strip()
        key_entity = entity or address or "unknown"
        repeat_group = "static_position" if not is_near_liq and not is_notable_change else "position_change"
        item_key = f"hyper:{key_entity}:{asset}:{side}:{change_type or 'snapshot'}"
        candidates.append(signal_item(section, priority, text, "hyperliquid", item_key, asset, repeat_group))
    candidates.sort(key=lambda item: item["priority"], reverse=True)
    return candidates[:limit]


def token_unlock_items(rows: list[dict], limit: int, min_usd: float, min_pct: float, min_usd_if_pct: float) -> list[dict]:
    usable = []
    for row in rows:
        raw = safe_json(row.get("raw_json", ""))
        amount = safe_float(row.get("amount_usd") or raw.get("unlock_amount_usd"))
        pct = safe_float(row.get("metric_value") or raw.get("unlock_pct_circulating"))
        if amount >= min_usd and pct >= min_pct:
            usable.append((amount, pct, row, raw))
    usable.sort(key=lambda item: (item[0], item[1]), reverse=True)
    items = []
    for amount, pct, row, raw in usable[:limit]:
        asset = str(row.get("asset_symbol") or raw.get("asset_symbol") or "-").upper()
        unlock_time = utc_to_china_short(raw.get("unlock_time_utc") or "")
        notes = str(raw.get("notes", "") or "")
        allocation = top_allocation_cn(notes)
        parts = [f"{asset}{unlock_time}解锁{usd_short(amount)}", f"占流通{pct:.1f}%"]
        if allocation:
            parts.append(allocation)
        text = f"{parts[0]}\n  " + "，".join(parts[1:])
        priority = 75 + amount / 1_000_000 + pct
        unlock_id = str(raw.get("unlock_id") or raw.get("unlock_time_utc") or asset)
        items.append(
            signal_item(
                "priority" if pct >= 7 or amount >= 50_000_000 else "context",
                priority,
                text,
                "token_unlock",
                f"unlock:{asset}:{unlock_id}",
                asset,
                "token_unlock",
            )
        )
    return items


def crowding_text(row: dict) -> str:
    asset = str(row.get("asset_symbol") or "-").upper()
    bias = row.get("crowding_bias") or "仓位拥挤"
    pos_ratio = safe_float(row.get("top_position_long_short_ratio"))
    taker = safe_float(row.get("taker_buy_sell_ratio"))
    parts = [f"{asset}{bias}"]
    if pos_ratio:
        parts.append(f"大户持仓约为散户{pos_ratio:.1f}倍")
    if taker:
        if taker >= 1.15:
            parts.append("主动买入偏强")
        elif taker <= 0.9:
            parts.append("主动卖出偏强")
    return "，".join(parts)


def long_short_items(rows: list[dict], limit: int, min_score: float) -> list[dict]:
    usable = [row for row in rows if str(row.get("quality_status", "")).lower() in {"ok", "partial", ""}]
    usable = [row for row in usable if safe_float(row.get("crowding_score")) >= min_score]
    usable = sorted(usable, key=lambda row: safe_float(row.get("crowding_score")), reverse=True)[:limit]
    return [
        signal_item(
            "context",
            55 + safe_float(row.get("crowding_score")),
            crowding_text(row),
            "long_short",
            f"long_short:{row.get('asset_symbol')}:{row.get('crowding_bias')}",
            str(row.get("asset_symbol") or "").upper(),
            "indicator",
        )
        for row in usable
    ]


def flow_items(rows: list[dict], limit: int, min_flow_usd: float, min_stablecoin_usd: float) -> list[dict]:
    usable = [
        row
        for row in rows
        if str(row.get("event_type", "")).strip() in {"stablecoin_flow", "cex_netflow"}
        and safe_float(row.get("amount_usd")) > 0
    ]
    items = []
    for row in usable:
        amount_value = safe_float(row.get("amount_usd"))
        event_type = row.get("event_type") or ""
        if event_type == "cex_netflow" and amount_value < min_flow_usd:
            continue
        if event_type == "stablecoin_flow" and amount_value < min_stablecoin_usd:
            continue
        asset = str(row.get("asset_symbol") or row.get("signal_asset_symbol") or "-").upper()
        metric = row.get("raw_signal_type") or row.get("event_type_l2") or ""
        entity = row.get("entity_label") or row.get("source") or "-"
        amount = usd_short(amount_value)
        if event_type == "cex_netflow":
            direction = "流入" if "in" in metric else "流出" if "out" in metric else "净流变化"
            text = f"{asset}大额{direction}{entity}，规模{amount}"
        else:
            if "mint" in metric:
                action = "增发"
            elif "burn" in metric:
                action = "销毁"
            elif "out" in metric:
                action = "转出"
            else:
                action = "大额转入"
            text = f"{entity}{action}{amount} {asset}"
        items.append(
            signal_item(
                "context",
                60 + amount_value / 10_000_000,
                text,
                event_type,
                f"flow:{event_type}:{asset}:{entity}:{metric}",
                asset,
                "flow",
            )
        )
    items.sort(key=lambda item: item["priority"], reverse=True)
    return items[:limit]


def parse_china_stamp(value: str) -> datetime | None:
    raw = str(value or "").replace("UTC+8", "").strip()
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M"):
        try:
            return datetime.strptime(raw, fmt).replace(tzinfo=timezone(timedelta(hours=8)))
        except ValueError:
            continue
    return None


def cooldown_hours(item: dict, args: argparse.Namespace, label: str) -> float:
    group = item.get("repeat_group", "")
    if group == "token_unlock":
        if "??" in label or "??" in label:
            base = 2.0
        else:
            base = args.repeat_hours_token_unlock
    elif group == "static_position":
        base = args.repeat_hours_static_position
    elif group == "indicator":
        base = args.repeat_hours_indicator
    elif group == "flow":
        base = args.repeat_hours_flow
    else:
        base = 1.0
    multiplier = safe_float(item.get("cooldown_multiplier") or 1.0)
    if multiplier <= 0:
        multiplier = 1.0
    return base * multiplier


def suppress_recent_repeats(
    items: list[dict],
    state_rows: list[dict],
    now: datetime,
    label: str,
    args: argparse.Namespace,
) -> tuple[list[dict], int, list[dict]]:
    latest: dict[str, datetime] = {}
    for row in state_rows:
        key = str(row.get("item_key") or "").strip()
        dt = parse_china_stamp(row.get("last_included_china", ""))
        if key and dt and (key not in latest or dt > latest[key]):
            latest[key] = dt
    kept = []
    suppressed_items = []
    suppressed = 0
    for item in items:
        key = str(item.get("item_key") or "")
        last_dt = latest.get(key)
        if last_dt:
            age_hours = (now - last_dt).total_seconds() / 3600
            if age_hours < cooldown_hours(item, args, label):
                suppressed += 1
                item["decision_reason"] = f"冷却期未到：{age_hours:.2f}h < {cooldown_hours(item, args, label):.2f}h"
                suppressed_items.append(item)
                continue
        kept.append(item)
    return kept, suppressed, suppressed_items


def fetch_price_context(assets: set[str]) -> dict[str, dict]:
    result: dict[str, dict] = {}
    for asset in sorted(assets):
        if not asset or asset in {"USDT", "USDC", "DAI"}:
            continue
        symbol = f"{asset}USDT"
        try:
            payload = requests.get(
                "https://fapi.binance.com/fapi/v1/ticker/24hr",
                params={"symbol": symbol},
                timeout=8,
            ).json()
        except Exception:
            continue
        if isinstance(payload, dict) and payload.get("lastPrice"):
            result[asset] = {
                "price": safe_float(payload.get("lastPrice")),
                "change_pct": safe_float(payload.get("priceChangePercent")),
            }
    return result


def price_phrase(asset: str, context: dict[str, dict]) -> str:
    data = context.get(asset)
    if not data:
        return ""
    price = data.get("price", 0.0)
    change = data.get("change_pct", 0.0)
    if not price:
        return ""
    price_text = f"${price:,.2f}" if price >= 1 else f"${price:.4f}"
    sign = "+" if change > 0 else ""
    return f"{asset} {price_text}，24h {sign}{change:.1f}%"


def enrich_with_prices(items: list[dict], context: dict[str, dict]) -> None:
    for item in items:
        asset = str(item.get("asset") or "").upper()
        phrase = price_phrase(asset, context)
        if not phrase or item.get("source_type") == "token_unlock":
            continue
        text = item.get("text", "")
        if "\n  " in text:
            head, tail = text.split("\n  ", 1)
            item["text"] = f"{head}\n  {phrase}；{tail}"
        else:
            item["text"] = f"{text}\n  {phrase}"


STATE_COLUMNS = [
    "included_at_china",
    "board_id",
    "item_key",
    "source_type",
    "asset",
    "repeat_group",
    "final_priority",
    "policy_action",
    "policy_reason_cn",
    "dynamic_boost_reason",
    "last_included_china",
    "text",
]


DECISION_COLUMNS = [
    "decided_at_china",
    "board_id",
    "board_label",
    "decision",
    "decision_reason",
    "item_key",
    "source_type",
    "asset",
    "repeat_group",
    "section",
    "final_priority",
    "policy_action",
    "policy_reason_cn",
    "dynamic_boost_reason",
    "text",
]


def item_identity(item: dict) -> str:
    return str(item.get("item_key") or item.get("text") or "")


def decision_row(now: datetime, board_id: str, label: str, item: dict, decision: str, reason: str = "") -> dict:
    return {
        "decided_at_china": china_stamp(now),
        "board_id": board_id,
        "board_label": label,
        "decision": decision,
        "decision_reason": reason or item.get("decision_reason", ""),
        "item_key": item.get("item_key", ""),
        "source_type": item.get("source_type", ""),
        "asset": item.get("asset", ""),
        "repeat_group": item.get("repeat_group", ""),
        "section": item.get("section", ""),
        "final_priority": f"{float(item.get('priority') or 0):.4f}",
        "policy_action": item.get("policy_action", ""),
        "policy_reason_cn": item.get("policy_reason_cn", ""),
        "dynamic_boost_reason": item.get("dynamic_boost_reason", ""),
        "text": item.get("text", ""),
    }


def build_decision_rows(
    now: datetime,
    board_id: str,
    label: str,
    candidates: list[dict],
    digest_filtered: list[dict],
    cooldown_filtered: list[dict],
    selected: list[dict],
) -> list[dict]:
    selected_ids = {item_identity(item) for item in selected}
    digest_ids = {item_identity(item) for item in digest_filtered}
    cooldown_ids = {item_identity(item) for item in cooldown_filtered}
    digest_reason = {item_identity(item): item.get("decision_reason", "盘中静态背景转早晚报") for item in digest_filtered}
    cooldown_reason = {item_identity(item): item.get("decision_reason", "") for item in cooldown_filtered}
    rows = []
    seen = set()
    for item in candidates:
        ident = item_identity(item)
        if ident in seen:
            continue
        seen.add(ident)
        if ident in selected_ids:
            rows.append(decision_row(now, board_id, label, item, "selected", "进入本轮雷达板"))
        elif ident in digest_ids:
            rows.append(decision_row(now, board_id, label, item, "filtered_digest_only", digest_reason.get(ident, "盘中静态背景转早晚报")))
        elif ident in cooldown_ids:
            rows.append(decision_row(now, board_id, label, item, "suppressed_cooldown", cooldown_reason.get(ident, "")))
        else:
            rows.append(decision_row(now, board_id, label, item, "not_selected_capacity", "优先级未进入本轮展示名额"))
    return rows


def select_board_items(items: list[dict], max_total: int, max_priority: int, max_context: int) -> tuple[list[dict], list[dict]]:
    seen = set()
    deduped = []
    for item in sorted(items, key=lambda row: row["priority"], reverse=True):
        key = item["text"]
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)
    priority = [item for item in deduped if item["section"] == "priority"][:max_priority]
    remaining_slots = max(0, max_total - len(priority))
    context_limit = min(max_context, remaining_slots)
    context = [item for item in deduped if item["section"] != "priority"][:context_limit]
    if len(priority) < max_priority and len(priority) + len(context) < max_total:
        extra_slots = max_total - len(priority) - len(context)
        context.extend([item for item in deduped if item not in priority and item not in context][:extra_slots])
    return priority, context


def lint_board_text(text: str, max_line_chars: int, item_count: int) -> tuple[str, str]:
    flags = []
    forbidden = [
        "cex_netflow_in",
        "cex_netflow_out",
        "stablecoin_treasury_in",
        "分数",
        "均价",
        "强平 ",
        "0x",
        "Unknown Whale",
        "Unknown Hyperliquid",
        "阅读方式",
    ]
    for token in forbidden:
        if token in text:
            flags.append(f"backend_leak:{token}")
    if item_count > 5:
        flags.append("too_many_items")
    for line in text.splitlines():
        clean = line.replace("<b>", "").replace("</b>", "")
        if len(clean) > max_line_chars:
            flags.append("long_line")
            break
    status = "pass" if not flags else "warning"
    return status, ",".join(flags)


def compact_for_card(value: str, limit: int = 120) -> str:
    text = " ".join(str(value or "").replace("\r", "\n").split())
    if len(text) <= limit:
        return text
    return text[: limit - 1] + "…"


def format_board_item(item: dict) -> str:
    raw_lines = [line.strip() for line in str(item.get("text") or "").splitlines() if line.strip()]
    if not raw_lines:
        return "• 未命名信号"
    title = compact_for_card(raw_lines[0], 76)
    details = compact_for_card("；".join(raw_lines[1:]), 120) if len(raw_lines) > 1 else ""
    if details:
        return f"• <b>{h(title)}</b>\n  {h(details)}"
    return f"• <b>{h(title)}</b>"


def build_card_footer(repeat_suppressed: int, policy_digest_filtered: int) -> list[str]:
    parts = []
    if repeat_suppressed:
        parts.append(f"冷却过滤 {repeat_suppressed} 条")
    if policy_digest_filtered:
        parts.append(f"转早晚报 {policy_digest_filtered} 条")
    lines = []
    if parts:
        lines.append("本轮降噪：" + "｜".join(parts))
    lines.append("仅供市场结构与链上情报观察，不构成任何交易建议。")
    return lines


def compact_for_card(value: str, limit: int = 120) -> str:
    text = " ".join(str(value or "").replace("\r", "\n").split())
    if len(text) <= limit:
        return text
    return text[: limit - 1] + "…"


def readable_source_label(source_type: str) -> str:
    labels = {
        "hyperliquid": "合约仓位",
        "token_unlock": "代币解锁",
        "long_short": "多空拥挤",
        "cex_netflow": "交易所资金流",
        "stablecoin_flow": "稳定币流动",
    }
    return labels.get(str(source_type or ""), "市场异动")


def source_observation_note(item: dict) -> str:
    source = str(item.get("source_type") or "")
    group = str(item.get("repeat_group") or "")
    if source == "hyperliquid":
        if group == "position_change":
            return "仓位是否继续变化、是否接近清算区，资金费率是否同步异常"
        return "静态大仓位只作背景，优先等待仓位变化、清算距离或资金费率共振"
    if source == "token_unlock":
        return "供给侧日历事件，盘中只保留临近或异常放大的项目"
    if source == "long_short":
        return "多空比只说明拥挤结构，需结合价格、成交量判断，不单独解释方向"
    if source in {"cex_netflow", "stablecoin_flow"}:
        return "资金流需和滚动基线比较，单笔大额不等于异常"
    return "该来源样本仍少，先作为观察项，不做强结论"


# ── v1 admission rules (hardened per Claude/Gemini direction) ──

# jin10 MUST hit one of these crypto risk factors to enter Market Radar
JIN10_CRYPTO_RISK_FACTORS = [
    "美联储", "CPI", "PCE", "非农", "降息", "加息",
    "SEC", "CFTC", "ETF",
    "比特币", "以太坊", "BTC", "ETH",
    "币安", "Binance", "Coinbase",
    "稳定币", "USDT", "USDC",
    "交易所", "黑客", "攻击", "漏洞",
    "监管", "执法", "冻结", "提现", "充值",
]

# Items that are always filtered (non-crypto-noise)
NON_CRYPTO_NOISE_KEYWORDS = [
    "航空燃油", "民航", "机票", "航运", "传统企业",
    "餐饮", "零售", "房地产", "汽车销售", "保险",
    "旅游", "酒店", "教育", "医疗", "天气",
    "福利", "邀请码", "广告", "营销", "抽奖",
    "印度", "伊朗", "地缘", "油价", "成品油",
    "关税", "贸易战", "制造业", "供应链", "物流",
    "策略公司", "宣布新比特币收购", "比特币收购",
    "公司宣布", "收购计划", "企业收购",
]


def classify_admission(item: dict) -> tuple[str, str]:
    """Classify item into: allow / digest / filter, with a reason."""
    source = str(item.get("source_type") or item.get("source") or "").lower()
    title = str(item.get("title") or item.get("text") or "").lower()
    text = str(item.get("text") or "").lower()
    combined = f"{title} {text}"
    asset = str(item.get("asset") or "").upper()

    # ── explicit noise → filter ──
    for kw in NON_CRYPTO_NOISE_KEYWORDS:
        if kw in combined:
            return ("filter", f"非crypto行业/地区噪声: {kw}")

    # ── jin10 special path ──
    if "jin10" in source:
        for kw in JIN10_CRYPTO_RISK_FACTORS:
            if kw.lower() in combined:
                return ("allow", f"jin10命中crypto风险因子: {kw}")
        return ("filter", "jin10未命中crypto风险因子")

    # ── core asset → allow ──
    if asset in {"BTC", "ETH", "SOL", "BNB", "HYPE", "DOGE", "XRP", "LINK", "AVAX"}:
        return ("allow", f"核心资产: {asset}")

    # ── crypto structural keyword → allow ──
    for kw in JIN10_CRYPTO_RISK_FACTORS:
        if kw.lower() in combined:
            return ("allow", f"命中crypto结构关键词: {kw}")

    # ── no match → digest or filter based on event type ──
    if source in {"hyperliquid", "token_unlock", "long_short", "cex_netflow", "stablecoin_flow"}:
        return ("allow", "已知crypto数据源类型")
    return ("filter", "无crypto资产/结构/数据源映射")


def is_crypto_relevant(item: dict) -> bool:
    return classify_admission(item)[0] == "allow"


# ── v1 card template (hardened) ──────────────────────────────

STRENGTH_LABELS = {1: "低", 2: "低", 3: "中", 4: "中", 5: "高"}


def impact_reason(item: dict, label: str) -> str:
    """Return a factual trigger reason — no prediction, no recommendation."""
    source = str(item.get("source_type") or "")
    dynamic = str(item.get("dynamic_boost_reason") or "")
    policy = str(item.get("policy_reason_cn") or "")
    priority = safe_float(item.get("priority") or 50)
    asset = str(item.get("asset") or "").upper()

    # Look up percentile data for this asset
    pctl = _lookup_percentile_data()

    if "hyperliquid" in source:
        # v1.3b: try to show OI ratio + liq distance as impact evidence
        text_str = str(item.get("text") or "")
        liq_match2 = re.search(r"距清算价(\d+\.?\d*)%", text_str)
        liq_dist = float(liq_match2.group(1)) if liq_match2 else 99.0
        pv_match = re.search(r"\$([\d.]+)([MBK])", text_str)
        pos_v = 0.0
        if pv_match:
            amt = float(pv_match.group(1)); unit = pv_match.group(2)
            if unit == "B": pos_v = amt * 1e9
            elif unit == "M": pos_v = amt * 1e6
            elif unit == "K": pos_v = amt * 1e3
            else: pos_v = amt
        hl_oi2 = _get_hl_total_oi(asset)
        if hl_oi2 > 0 and pos_v > 0:
            ratio = pos_v / hl_oi2 * 100
            return f"HL OI 占比 [{ratio:.1f}%] / 强平边际 {liq_dist:.1f}%"
        return f"仓位规模巨大 / 强平边际 {liq_dist:.1f}%"

    if "long_short" in source:
        # Check if we have OI percentile as supplementary evidence
        if asset in pctl and pctl[asset].get("oi_pctl", 0) >= 80:
            return f"多空比极端分位 / OI {pctl[asset]['oi_pctl']:.0f}%分位"
        return "多空比极端分位"

    if source in {"cex_netflow", "stablecoin_flow"}:
        if asset in pctl and pctl[asset].get("oi_pctl", 0) >= 80:
            return "链上资金流异动 / OI高水位"
        return "链上资金流异动"

    if "token_unlock" in source:
        return "供给侧解锁"

    # Generic rules with percentile enrichment
    if asset in pctl:
        fp = pctl[asset].get("funding_pctl", 0)
        op = pctl[asset].get("oi_pctl", 0)
        max_p = max(fp, op)
        if max_p >= 95:
            return f"多信号共振（funding/OI 90d {max_p:.0f}%分位）"
        if max_p >= 80:
            return f"结构信号偏离（funding/OI 高于常态）"

    if dynamic:
        return dynamic[:30]
    if policy:
        return policy[:30]
    if label == "高":
        return "多信号共振 / 一手数据确认"
    if label == "中":
        return "单一结构信号 / 传导待确认"
    return "弱结构信号"


def format_board_item(item: dict) -> str:
    raw_lines = [line.strip() for line in str(item.get("text") or "").splitlines() if line.strip()]
    source_label = readable_source_label(str(item.get("source_type") or ""))
    asset_label = str(item.get("asset") or "").upper()
    title = compact_for_card(raw_lines[0] if raw_lines else "未命名信号", 80)
    priority = safe_float(item.get("priority") or 50)
    impact_label = STRENGTH_LABELS.get(int(priority / 20) + 1, "低")
    trigger = impact_reason(item, impact_label)

    # v1.2a compact card (target ≤280 chars)
    card_title = f"⚡️ [Market Radar] {h(source_label)} · {h(asset_label if asset_label != '-' else '全市场')}"
    if len(card_title) > 60:
        card_title = card_title[:57] + "..."

    lines = [f"<b>{card_title}</b>"]
    lines.append("━━━━━━━━━━━━━━━━━━━━")

    time_str = item.get("observed_at_china") or item.get("published_at_china") or ""
    time_short = _short_timestamp(time_str) if time_str else ""
    src_name = str(item.get("source_name", "") or item.get("source", "") or "-")
    lines.append(f"⏱ {h(time_short)}｜来源：{h(src_name[:30])}")
    impact_display = {"低": "低度", "中": "中度", "高": "高度"}.get(impact_label, impact_label)
    lines.append(f"🚨 冲击度：{h(impact_display)}（{h(trigger)}）")

    lines.append("")
    lines.append("📊 结构冲击事实：")
    lines.append(h(title))
    details = compact_for_card("；".join(raw_lines[1:]), 100) if len(raw_lines) > 1 else ""
    if details and details != title:
        lines.append(h(details[:100]))

    # Quantitative anchor — only if we have real data
    anchor = _quantitative_anchor(item)
    if anchor:
        lines.append("")
        lines.append(f"📈 定量锚定：")
        lines.append(h(anchor))

    lines.append("")
    lines.append("⚠️ 仅供市场结构观察；数据仅代表监控地址，不构成交易建议。")
    return "\n".join(lines)


def _short_timestamp(ts: str) -> str:
    """Convert timestamps to 'MM-DD HH:MM (SGT)' format."""
    raw = str(ts).replace("UTC+8", "").replace("T", " ").replace("Z", "").strip()
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%m-%d %H:%M"):
        try:
            from datetime import datetime
            dt = datetime.strptime(raw[:19], fmt)
            return dt.strftime("%m-%d %H:%M") + " (SGT)"
        except ValueError:
            continue
    return raw[:16]


def _quantitative_anchor(item: dict) -> str:
    """Build a factual quantitative anchor line — no prediction."""
    source = str(item.get("source_type") or "")
    text = str(item.get("text") or "")
    asset = str(item.get("asset") or "").upper()
    import re

    # Extract position value from text for ratio calculation
    pos_match = re.search(r"\$([\d.]+[MBK]?)", text)
    pos_val = 0.0
    if pos_match:
        pv = pos_match.group(1)
        if "B" in pv: pos_val = float(pv.replace("B","")) * 1e9
        elif "M" in pv: pos_val = float(pv.replace("M","")) * 1e6
        elif "K" in pv: pos_val = float(pv.replace("K","")) * 1e3
        else: pos_val = float(pv)

    # Hyperliquid position: liquidation distance + HL OI ratio
    liq_match = re.search(r"距清算价(\d+\.?\d*)%", text)
    if liq_match and "hyperliquid" in source:
        dist = float(liq_match.group(1))
        hl_oi = _get_hl_total_oi(asset)
        parts = [f"强平安全边际 {dist:.1f}%"]
        if hl_oi > 0 and pos_val > 0:
            ratio = pos_val / hl_oi * 100
            parts.append(f"约占 HL {asset} 总 OI [{ratio:.1f}%]")
        return "；".join(parts) + "。"

    # Percentile context for non-HL items
    pctl = _lookup_percentile_data()
    if asset in pctl:
        parts = []
        fp = pctl[asset].get("funding_pctl", 0)
        op = pctl[asset].get("oi_pctl", 0)
        if fp >= 95:
            parts.append(f"funding 90d {fp:.1f}%分位")
        if op >= 95:
            parts.append(f"OI 90d {op:.1f}%分位")
        if fp >= 80:
            parts.append(f"funding 高于常态（{fp:.0f}%分位）")
        if op >= 80:
            parts.append(f"OI 高于常态（{op:.0f}%分位）")
        if parts:
            return "；".join(parts[:2]) + "。"
    return ""
    lines.append("⚠️ 仅作市场结构与链上情报观察，不构成任何交易建议。")
    return "\n".join(lines)


def build_card_footer(repeat_suppressed: int, policy_digest_filtered: int) -> list[str]:
    parts = []
    if repeat_suppressed:
        parts.append(f"冷却过滤 {repeat_suppressed} 条")
    if policy_digest_filtered:
        parts.append(f"转早午晚报 {policy_digest_filtered} 条")
    lines = []
    if parts:
        lines.append("本轮降噪：" + "｜".join(parts))
    lines.append("仅供市场结构与链上情报观察，不构成任何交易建议。")
    return lines


def build_board(args: argparse.Namespace) -> tuple[dict, dict, str, list[dict]]:
    now = china_now()
    label = board_label(args.board_label)
    board_id = f"tg_board_{now.strftime('%Y%m%d_%H%M%S')}"

    watcher_events = read_rows(normalize_path(args.watcher_events))
    hyper_rows = read_rows(normalize_path(args.hyperliquid_alerts))
    unlock_rows = read_rows(normalize_path(args.token_unlock_alerts))
    long_short_rows = read_rows(normalize_path(args.long_short_snapshot))
    policies = merge_policy_sets(
        load_signal_policy(normalize_path(args.signal_policy)),
        load_signal_policy(normalize_path(args.live_signal_policy)),
        load_signal_policy(normalize_path(args.v11_signal_policy)),
        load_signal_policy(normalize_path(args.v12_signal_policy)),
    )

    hyper_items_rows = hyperliquid_items(hyper_rows, args.max_hyperliquid, args.min_hyperliquid_usd)
    unlock_items_rows = token_unlock_items(
        unlock_rows,
        args.max_unlocks,
        args.min_unlock_usd,
        args.min_unlock_pct,
        args.min_unlock_usd_if_pct,
    )
    long_short_items_rows = long_short_items(long_short_rows, args.max_long_short, args.min_crowding_score)
    flow_items_rows = flow_items(watcher_events, args.max_flows, args.min_flow_usd, args.min_stablecoin_flow_usd)
    all_candidate_items = [*hyper_items_rows, *unlock_items_rows, *long_short_items_rows, *flow_items_rows]
    # v1 admission filter: remove non-crypto noise before policy processing
    filtered_out = len(all_candidate_items)
    all_candidate_items = [it for it in all_candidate_items if is_crypto_relevant(it)]
    filtered_out -= len(all_candidate_items)
    if filtered_out > 0:
        print(f"  v1 admission filter: removed {filtered_out} non-crypto item(s)")
    policy_counts = apply_signal_policy(all_candidate_items, policies)
    dynamic_boosted = apply_dynamic_boost(all_candidate_items)
    decision_candidates = [dict(item) for item in all_candidate_items]
    all_candidate_items, policy_digest_filtered, digest_filtered_items = filter_digest_only_items(all_candidate_items, now)
    all_candidate_items, repeat_suppressed, cooldown_filtered_items = suppress_recent_repeats(
        all_candidate_items,
        read_rows(normalize_path(args.history_state)),
        now,
        label,
        args,
    )
    priority_items, context_items = select_board_items(
        all_candidate_items,
        args.max_items,
        args.max_priority_items,
        args.max_context_items,
    )
    selected_items = [*priority_items, *context_items]
    decision_rows = build_decision_rows(
        now,
        board_id,
        label,
        decision_candidates,
        digest_filtered_items,
        cooldown_filtered_items,
        selected_items,
    )
    price_context = {}
    if truthy(args.include_price_context):
        price_context = fetch_price_context({str(item.get("asset") or "").upper() for item in selected_items})
        enrich_with_prices(selected_items, price_context)
    sections: list[tuple[str, list[dict]]] = []
    if priority_items:
        sections.append(("优先关注", priority_items))
    if context_items:
        sections.append(("结构信号", context_items))

    text_lines = [
        f"<b>{h(now.strftime('%H:%M'))} {h(label)}</b>",
        "",
    ]
    if not sections:
        text_lines.extend(
            [
                "当前没有新的高质量动仓/异动信号。",
                *build_card_footer(repeat_suppressed, policy_digest_filtered),
                "",
            ]
        )
    else:
        for title, items in sections:
            text_lines.append(f"<b>{h(title)}</b>")
            text_lines.extend(format_board_item(item) for item in items)
            text_lines.append("")
        text_lines.extend(build_card_footer(repeat_suppressed, policy_digest_filtered))

    board_text = "\n".join(text_lines).strip()
    item_count = len(priority_items) + len(context_items)
    readability_status, readability_flags = lint_board_text(board_text, args.max_line_chars, item_count)
    source_rows = len(watcher_events) + len(hyper_rows) + len(unlock_rows) + len(long_short_rows)
    top_section = sections[0][0] if sections else ""
    row = {
        "board_id": board_id,
        "generated_at_china": china_stamp(now),
        "board_label": label,
        "source_rows": str(source_rows),
        "section_count": str(len(sections)),
        "item_count": str(item_count),
        "top_section": top_section,
        "board_text": board_text,
    }
    summary = {
        "status": "pass",
        "generated_at_china": china_stamp(now),
        "board_id": board_id,
        "board_label": label,
        "source_rows": str(source_rows),
        "section_count": str(len(sections)),
        "item_count": str(item_count),
        "hyperliquid_rows": str(len(hyper_items_rows)),
        "token_unlock_rows": str(len(unlock_items_rows)),
        "long_short_rows": str(len(long_short_items_rows)),
        "flow_rows": str(len(flow_items_rows)),
        "price_context_rows": str(len(price_context)),
        "repeat_suppressed_rows": str(repeat_suppressed),
        "policy_boosted_rows": str(policy_counts.get("boost", 0)),
        "policy_review_rows": str(policy_counts.get("review", 0)),
        "policy_collect_more_rows": str(policy_counts.get("collect_more", 0)),
        "policy_digest_only_rows": str(policy_counts.get("digest_only", 0)),
        "policy_digest_filtered_rows": str(policy_digest_filtered),
        "policy_downranked_rows": str(policy_counts.get("downrank", 0)),
        "dynamic_boosted_rows": str(dynamic_boosted),
        "decision_log_rows": str(len(decision_rows)),
        "readability_status": readability_status,
        "readability_flags": readability_flags,
        "output": str(normalize_path(args.output)),
        "markdown_output": str(normalize_path(args.markdown_output)),
    }
    state_rows = [
        {
            "included_at_china": china_stamp(now),
            "board_id": board_id,
            "item_key": item.get("item_key", ""),
            "source_type": item.get("source_type", ""),
            "asset": item.get("asset", ""),
            "repeat_group": item.get("repeat_group", ""),
            "final_priority": f"{float(item.get('priority') or 0):.4f}",
            "policy_action": item.get("policy_action", ""),
            "policy_reason_cn": item.get("policy_reason_cn", ""),
            "dynamic_boost_reason": item.get("dynamic_boost_reason", ""),
            "last_included_china": china_stamp(now),
            "text": item.get("text", ""),
        }
        for item in selected_items
    ]
    return row, summary, board_text, state_rows, decision_rows


def main() -> int:
    args = parse_args()
    row, summary, board_text, state_rows, decision_rows = build_board(args)
    write_rows(normalize_path(args.output), [row], BOARD_COLUMNS)
    write_rows(normalize_path(args.summary), [summary], SUMMARY_COLUMNS)
    ensure_columns(normalize_path(args.history_state), STATE_COLUMNS)
    if state_rows:
        append_rows(normalize_path(args.history_state), state_rows, STATE_COLUMNS)
    if decision_rows:
        append_rows(normalize_path(args.decision_log), decision_rows, DECISION_COLUMNS)
    markdown_path = normalize_path(args.markdown_output)
    markdown_path.parent.mkdir(parents=True, exist_ok=True)
    markdown_path.write_text(
        "\n".join(
            [
                "# v0.9 TG Market Radar Board",
                "",
                f"- generated_at_china: {row['generated_at_china']}",
                f"- board_id: {row['board_id']}",
                f"- section_count: {row['section_count']}",
                "",
                "```html",
                board_text,
                "```",
                "",
            ]
        ),
        encoding="utf-8",
    )
    print(f"wrote board to {normalize_path(args.output)}")
    print(f"wrote markdown preview to {markdown_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

def _usd_compact(v: float) -> str:
    if v >= 1_000_000_000:
        return f"${v/1_000_000_000:.1f}B"
    if v >= 1_000_000:
        return f"${v/1_000_000:.1f}M"
    if v >= 1_000:
        return f"${v/1_000:.0f}K"
    return f"${v:.0f}"

_PCTL_CACHE = None
def _lookup_percentile_data() -> dict:
    """Return {asset: {funding_pctl, oi_pctl}} from percentile alerts JSON."""
    global _PCTL_CACHE
    if _PCTL_CACHE is not None:
        return _PCTL_CACHE
    _PCTL_CACHE = {}
    try:
        import json
        p = ROOT / "results" / "v15_percentile_alerts.json"
        if p.exists():
            data = json.loads(p.read_text(encoding="utf-8"))
            for bucket in ("frontpage_alerts", "watchlist_alerts", "radar_triggers", "digest_context"):
                for item in data.get(bucket, []):
                    a = str(item.get("asset_symbol", "")).upper()
                    if a not in _PCTL_CACHE:
                        _PCTL_CACHE[a] = {"funding_pctl": 0.0, "oi_pctl": 0.0}
                    atype = str(item.get("alert_type", ""))
                    pv = safe_float(item.get("percentile", 0))
                    if "funding" in atype and pv > _PCTL_CACHE[a]["funding_pctl"]:
                        _PCTL_CACHE[a]["funding_pctl"] = pv
                    if "oi" in atype:
                        oi_pv = safe_float(item.get("oi_level_percentile_90d", pv))
                        if oi_pv > _PCTL_CACHE[a]["oi_pctl"]:
                            _PCTL_CACHE[a]["oi_pctl"] = oi_pv
    except Exception:
        pass
    return _PCTL_CACHE

_HL_OI_CACHE = {}
def _get_hl_total_oi(asset: str) -> float:
    """Get Hyperliquid total open interest for asset (USD). Returns 0 if unavailable."""
    global _HL_OI_CACHE
    asset = asset.upper()
    if asset in _HL_OI_CACHE:
        return _HL_OI_CACHE[asset]
    try:
        p = ROOT / "data" / "hyperliquid" / "market_meta_snapshot.csv"
        if p.exists():
            import csv
            for row in csv.DictReader(open(p, encoding="utf-8-sig")):
                if str(row.get("asset_symbol", "")).upper() == asset:
                    v = safe_float(row.get("open_interest_usd", 0))
                    _HL_OI_CACHE[asset] = v
                    return v
    except Exception:
        pass
    _HL_OI_CACHE[asset] = 0.0
    return 0.0
