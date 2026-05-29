import argparse
import csv
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests


ROOT = Path(__file__).resolve().parents[1]
CHINA_TZ = timezone(timedelta(hours=8))
HYPERLIQUID_INFO_URL = "https://api.hyperliquid.xyz/info"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Aggregate Hyperliquid monitored positions with baseline and market-share context.")
    parser.add_argument("--input", default=str(ROOT / "data" / "watcher_alerts_hyperliquid_positions.csv"))
    parser.add_argument("--previous-input", default=str(ROOT / "data" / "watcher_alerts_hyperliquid_positions_previous.csv"))
    parser.add_argument("--state-history", default=str(ROOT / "data" / "hyperliquid_position_state_history.csv"))
    parser.add_argument("--baseline-hours", type=float, default=24.0)
    parser.add_argument("--output", default=str(ROOT / "results" / "v14_hyperliquid_snapshot_card_v2.md"))
    parser.add_argument("--summary", default=str(ROOT / "results" / "v14_hyperliquid_snapshot_v2_summary.csv"))
    parser.add_argument("--timeout", type=int, default=20)
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


def write_rows(path: Path, rows: list[dict], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def china_stamp() -> str:
    return datetime.now(CHINA_TZ).replace(microsecond=0).strftime("%Y-%m-%d %H:%M:%S UTC+8")


def safe_float(value) -> float:
    try:
        return float(str(value or "").replace(",", "").strip())
    except Exception:
        return 0.0


def money(value: float) -> str:
    if abs(value) >= 100_000_000:
        return f"{value / 100_000_000:.2f} 亿美元"
    if abs(value) >= 10_000:
        return f"{value / 10_000:.2f} 万美元"
    return f"{value:.2f} 美元"


def pct(value: float | None) -> str:
    if value is None:
        return "无基线"
    sign = "+" if value >= 0 else ""
    return f"{sign}{value:.1f}%"


def change_pct_text(current: float, previous: float, baseline_status: str) -> str:
    if baseline_status == "missing_previous_snapshot" or previous <= 0:
        return "无基线"
    sign = "+" if current >= previous else ""
    return f"{sign}{(current - previous) / previous * 100:.1f}%"


def parse_position(row: dict) -> dict:
    raw = {}
    try:
        raw = json.loads(row.get("raw_json") or "{}")
    except Exception:
        raw = {}
    pos = raw.get("current", {}).get("position", {}) if isinstance(raw, dict) else {}
    entry = safe_float(pos.get("entryPx"))
    liq = safe_float(pos.get("liquidationPx"))
    value = safe_float(row.get("amount_usd") or pos.get("positionValue"))
    szi = safe_float(pos.get("szi"))
    mark = abs(value / szi) if value and szi else entry
    leverage = safe_float((pos.get("leverage") or {}).get("value")) if isinstance(pos.get("leverage"), dict) else 0.0
    distance = abs(mark - liq) / mark if mark and liq else 0.0
    metric = str(row.get("metric_type") or "").lower()
    side = "多" if ("long" in metric or szi > 0) else "空" if ("short" in metric or szi < 0) else "未知"
    key = f"{row.get('primary_address','')}|{row.get('asset_symbol','')}|{side}"
    return {
        "key": key,
        "asset": row.get("asset_symbol", ""),
        "entity": row.get("primary_entity", ""),
        "address": row.get("primary_address", ""),
        "side": side,
        "value": abs(value),
        "entry": entry,
        "mark": mark,
        "liquidation": liq,
        "liq_distance_pct": distance * 100,
        "leverage": leverage,
    }


def parse_iso(value: str):
    try:
        return datetime.fromisoformat(str(value or "").replace("Z", "+00:00"))
    except Exception:
        return None


def parse_state_position(row: dict) -> dict:
    side_raw = str(row.get("side") or "").lower()
    side = "多" if side_raw == "long" else "空" if side_raw == "short" else "未知"
    address = str(row.get("address") or "").strip()
    asset = str(row.get("asset_symbol") or "").strip()
    return {
        "key": f"{address}|{asset}|{side}",
        "asset": asset,
        "entity": row.get("entity", ""),
        "address": address,
        "side": side,
        "value": abs(safe_float(row.get("position_value_usd"))),
        "entry": safe_float(row.get("entry_px")),
        "mark": safe_float(row.get("mark_px")) or safe_float(row.get("entry_px")),
        "liquidation": safe_float(row.get("liquidation_px")),
        "liq_distance_pct": safe_float(row.get("liquidation_distance_pct")) * 100,
        "leverage": 0.0,
    }


def load_state_history_baseline(path: Path, current_positions: list[dict], baseline_hours: float) -> tuple[list[dict], str, float]:
    rows = read_rows(path)
    if not rows or not current_positions:
        return [], "missing_previous_snapshot", 0.0
    parsed = [(parse_iso(row.get("updated_at_utc", "")), row) for row in rows]
    parsed = [(dt, row) for dt, row in parsed if dt]
    if not parsed:
        return [], "missing_previous_snapshot", 0.0
    current_time = max(dt for dt, _ in parsed)
    target = current_time - timedelta(hours=baseline_hours)
    candidates = sorted({dt for dt, _ in parsed if dt <= target})
    if candidates:
        chosen = candidates[-1]
        status = "ok"
    else:
        chosen = min({dt for dt, _ in parsed})
        status = "partial_baseline_less_than_24h"
    age_hours = (current_time - chosen).total_seconds() / 3600
    current_keys = {pos["key"] for pos in current_positions}
    selected = [parse_state_position(row) for dt, row in parsed if dt == chosen]
    selected = [pos for pos in selected if pos["key"] in current_keys]
    if not selected:
        return [], "missing_previous_snapshot", 0.0
    return selected, status, age_hours


def fetch_hyperliquid_total_oi(timeout: int) -> tuple[float, str]:
    try:
        session = requests.Session()
        session.trust_env = False
        resp = session.post(HYPERLIQUID_INFO_URL, json={"type": "metaAndAssetCtxs"}, timeout=timeout)
        resp.raise_for_status()
        data = resp.json()
        contexts = data[1] if isinstance(data, list) and len(data) > 1 else []
        total = 0.0
        for ctx in contexts:
            total += safe_float(ctx.get("openInterest")) * safe_float(ctx.get("markPx"))
        return total, "ok"
    except Exception as exc:
        return 0.0, f"warning:{str(exc)[:120]}"


def aggregate(positions: list[dict], previous: list[dict], total_oi: float) -> dict:
    total = sum(pos["value"] for pos in positions)
    prev_total = sum(pos["value"] for pos in previous)
    long_total = sum(pos["value"] for pos in positions if pos["side"] == "多")
    short_total = sum(pos["value"] for pos in positions if pos["side"] == "空")
    prev_long = sum(pos["value"] for pos in previous if pos["side"] == "多")
    prev_short = sum(pos["value"] for pos in previous if pos["side"] == "空")
    near_10 = [pos for pos in positions if pos["liq_distance_pct"] and pos["liq_distance_pct"] < 10]
    near_5 = [pos for pos in positions if pos["liq_distance_pct"] and pos["liq_distance_pct"] < 5]
    leverages = [pos["leverage"] for pos in positions if pos["leverage"]]
    non_hype_long = sum(pos["value"] for pos in positions if pos["side"] == "多" and pos["asset"] != "HYPE")
    non_hype_short = sum(pos["value"] for pos in positions if pos["side"] == "空" and pos["asset"] != "HYPE")
    hype_long = sum(pos["value"] for pos in positions if pos["side"] == "多" and pos["asset"] == "HYPE")
    hype_short = sum(pos["value"] for pos in positions if pos["side"] == "空" and pos["asset"] == "HYPE")
    return {
        "total": total,
        "prev_total": prev_total,
        "total_change_pct": ((total - prev_total) / prev_total * 100) if prev_total else None,
        "long_total": long_total,
        "short_total": short_total,
        "prev_long": prev_long,
        "prev_short": prev_short,
        "long_short_ratio": (long_total / short_total) if short_total else 0.0,
        "prev_long_short_ratio": (prev_long / prev_short) if prev_short else 0.0,
        "market_share_pct": (total / total_oi * 100) if total_oi else 0.0,
        "near_10_count": len(near_10),
        "near_10_value": sum(pos["value"] for pos in near_10),
        "near_5_count": len(near_5),
        "near_5_value": sum(pos["value"] for pos in near_5),
        "avg_leverage": sum(leverages) / len(leverages) if leverages else 0.0,
        "non_hype_long_short_ratio": (non_hype_long / non_hype_short) if non_hype_short else 0.0,
        "hype_long_short_ratio": (hype_long / hype_short) if hype_short else 0.0,
        "hype_position_value": hype_long + hype_short,
    }


def previous_value_map(previous: list[dict]) -> dict[str, float]:
    return {pos["key"]: pos["value"] for pos in previous}


def max_position_change_pct(positions: list[dict], previous: list[dict]) -> float:
    prev_map = previous_value_map(previous)
    max_change = 0.0
    for pos in positions:
        prev_value = prev_map.get(pos["key"])
        if prev_value and prev_value > 0:
            max_change = max(max_change, abs((pos["value"] - prev_value) / prev_value * 100))
    return max_change


def parse_pct_text(value: str) -> float:
    try:
        return float(str(value).replace("%", "").replace("+", "").strip())
    except Exception:
        return 0.0


def should_send_card(summary: dict) -> tuple[bool, str]:
    if int(summary.get("near_liquidation_10pct_count") or 0) > 0:
        return True, "有价格反向变动 10% 内触发清算的监控仓位"
    if abs(parse_pct_text(str(summary.get("total_position_change_pct") or ""))) > 10:
        return True, "监控总仓位规模较基线变化超过 10%"
    if safe_float(summary.get("max_single_position_change_pct")) > 20:
        return True, "单个监控仓位较基线变化超过 20%"
    return False, "无近爆仓仓位，监控总规模和单仓变化未达到推送阈值"


def render(positions: list[dict], previous: list[dict], summary: dict) -> str:
    prev_map = previous_value_map(previous)
    lines = [
        "## Hyperliquid 市场结构背景",
        "",
        f"生成时间：中国时间 {summary['generated_at_china']}",
        f"监控总规模：**{money(float(summary['total_position_value_usd']))}**（基线 {summary['baseline_age_hours']}h 前 {money(float(summary['previous_total_position_value_usd'])) if summary['baseline_status'] != 'missing_previous_snapshot' else '无基线'}，{summary['total_position_change_pct']}）",
        f"市场占比：**{summary['market_share_pct']}%**（监控仓位 / Hyperliquid 总持仓 {money(float(summary['hyperliquid_total_open_interest_usd']))}）",
        f"多空比：**{summary['long_short_ratio']} : 1**（含 HYPE）｜非 HYPE 多空比：{summary['non_hype_long_short_ratio']} : 1｜HYPE 多空比：{summary['hype_long_short_ratio']} : 1",
        f"平均杠杆：{summary['avg_leverage']}x｜HYPE 仓位占监控仓位：{summary['hype_position_share_pct']}%",
        f"TG发送建议：**{summary['send_recommendation']}**｜{summary['send_reason']}",
        "",
        "### 风险指标",
        f"- 价格需反向变动 <10% 触发清算：{summary['near_liquidation_10pct_count']} 个，合计 {money(float(summary['near_liquidation_10pct_value_usd']))}",
        f"- 价格需反向变动 <5% 触发清算：{summary['near_liquidation_5pct_count']} 个，合计 {money(float(summary['near_liquidation_5pct_value_usd']))}",
        "",
        "### Top 持仓变化",
        "| 标的 | 方向 | 规模 | 24h 变化 | 价格反向变动触发清算 | 实体 |",
        "|---|---:|---:|---:|---:|---|",
    ]
    for pos in positions[:8]:
        prev_value = prev_map.get(pos["key"])
        delta = pos["value"] - prev_value if prev_value is not None else None
        delta_text = money(delta) if delta is not None else "无基线"
        lines.append(f"| {pos['asset']} | {pos['side']} | {money(pos['value'])} | {delta_text} | {pos['liq_distance_pct']:.1f}% | {pos['entity']} |")
    if summary["baseline_status"] != "ok":
        lines.extend(["", "⚠️ 暂无完整 24h 基线，本卡只展示可用的最近历史对比；如果运行满 24h 后仍缺失，需要检查快照落盘。"])
    if summary["hyperliquid_total_oi_status"] != "ok":
        lines.extend(["", f"⚠️ Hyperliquid 总持仓读取异常：{summary['hyperliquid_total_oi_status']}"])
    lines.extend(
        [
            "",
            "读取方式：这是市场结构背景。清算字段表示“价格需反向变动约 X% 才会触发清算”；静态大仓位不应反复推送。",
            "",
            "⚠️ 仅作市场结构观察，不构成任何交易建议。",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> int:
    args = parse_args()
    positions = sorted([parse_position(row) for row in read_rows(normalize_path(args.input))], key=lambda item: item["value"], reverse=True)
    previous_path = normalize_path(args.previous_input)
    previous = sorted([parse_position(row) for row in read_rows(previous_path)], key=lambda item: item["value"], reverse=True)
    baseline_status = "ok" if previous else "missing_previous_snapshot"
    baseline_age_hours = args.baseline_hours if previous else 0.0
    if not previous:
        previous, baseline_status, baseline_age_hours = load_state_history_baseline(
            normalize_path(args.state_history), positions, args.baseline_hours
        )
        previous = sorted(previous, key=lambda item: item["value"], reverse=True)
    total_oi, oi_status = fetch_hyperliquid_total_oi(args.timeout)
    agg = aggregate(positions, previous, total_oi)
    max_single_change = max_position_change_pct(positions, previous)
    summary = {
        "generated_at_china": china_stamp(),
        "position_count": len(positions),
        "total_position_value_usd": round(agg["total"], 2),
        "previous_total_position_value_usd": round(agg["prev_total"], 2),
        "total_position_change_pct": change_pct_text(agg["total"], agg["prev_total"], baseline_status),
        "long_position_value_usd": round(agg["long_total"], 2),
        "short_position_value_usd": round(agg["short_total"], 2),
        "long_short_ratio": round(agg["long_short_ratio"], 3),
        "non_hype_long_short_ratio": round(agg["non_hype_long_short_ratio"], 3),
        "hype_long_short_ratio": round(agg["hype_long_short_ratio"], 3),
        "hype_position_share_pct": round((agg["hype_position_value"] / agg["total"] * 100), 2) if agg["total"] else 0.0,
        "avg_leverage": round(agg["avg_leverage"], 2),
        "hyperliquid_total_open_interest_usd": round(total_oi, 2),
        "hyperliquid_total_oi_status": oi_status,
        "market_share_pct": round(agg["market_share_pct"], 3),
        "near_liquidation_10pct_count": agg["near_10_count"],
        "near_liquidation_10pct_value_usd": round(agg["near_10_value"], 2),
        "near_liquidation_5pct_count": agg["near_5_count"],
        "near_liquidation_5pct_value_usd": round(agg["near_5_value"], 2),
        "max_single_position_change_pct": round(max_single_change, 2),
        "liquidation_distance_definition": "当前标记价距离清算价的百分比；即价格需反向变动约 X% 才会触发清算。",
        "baseline_status": baseline_status,
        "baseline_age_hours": round(baseline_age_hours, 2),
        "status": "pass",
    }
    send_it, send_reason = should_send_card(summary)
    summary["should_send_card"] = "yes" if send_it else "no"
    summary["send_recommendation"] = "发送" if send_it else "不单独发送"
    summary["send_reason"] = send_reason
    normalize_path(args.output).write_text(render(positions, previous, summary), encoding="utf-8")
    write_rows(normalize_path(args.summary), [summary], list(summary.keys()))
    print(f"position_count={summary['position_count']}")
    print(f"total_position_value_usd={summary['total_position_value_usd']}")
    print(f"market_share_pct={summary['market_share_pct']}")
    print(f"baseline_status={summary['baseline_status']}")
    print(f"hyperliquid_total_oi_status={summary['hyperliquid_total_oi_status']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
