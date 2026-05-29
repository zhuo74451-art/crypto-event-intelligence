import argparse
import csv
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CHINA_TZ = timezone(timedelta(hours=8))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Aggregate Hyperliquid static position snapshots into a morning/evening background card.")
    parser.add_argument("--input", default=str(ROOT / "data" / "watcher_alerts_hyperliquid_positions.csv"))
    parser.add_argument("--output", default=str(ROOT / "results" / "v14_hyperliquid_snapshot_card.md"))
    parser.add_argument("--summary", default=str(ROOT / "results" / "v14_hyperliquid_snapshot_summary.csv"))
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
        return float(str(value or "").strip())
    except Exception:
        return 0.0


def money(value: float) -> str:
    if value >= 100_000_000:
        return f"{value / 100_000_000:.2f} 亿美元"
    if value >= 10_000:
        return f"{value / 10_000:.2f} 万美元"
    return f"{value:.2f} 美元"


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
    distance = abs(entry - liq) / entry if entry and liq else 0.0
    side = "多" if "long" in str(row.get("metric_type") or "") else "空" if "short" in str(row.get("metric_type") or "") else "未知"
    return {
        "asset": row.get("asset_symbol", ""),
        "entity": row.get("primary_entity", ""),
        "address": row.get("primary_address", ""),
        "side": side,
        "value": value,
        "entry": entry,
        "liquidation": liq,
        "liq_distance_pct": distance * 100,
    }


def render(positions: list[dict], summary: dict) -> str:
    lines = [
        "📊 <b>Hyperliquid 市场结构背景</b>",
        f"时间：{summary['generated_at_china']}",
        "",
        f"监控仓位数：{summary['position_count']}｜总规模：{money(safe_float(summary['total_position_value_usd']))}",
        f"Top 持仓集中度：{summary['top10_concentration_pct']}%",
        f"距离清算价 <5%：{money(safe_float(summary['near_liquidation_value_usd']))}",
        "",
        "<b>Top 持仓</b>",
    ]
    for idx, pos in enumerate(positions[:5], 1):
        lines.append(
            f"{idx}. {pos['asset']} {pos['side']}｜{money(pos['value'])}｜清算距 {pos['liq_distance_pct']:.1f}%｜{pos['entity']}"
        )
    lines.extend(
        [
            "",
            "阅读方式：这是静态市场结构背景，不是盘中事件；只有仓位明显变化才进入实时提醒。",
            "⚠️ 仅作市场结构观察，不构成任何交易建议。",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> int:
    args = parse_args()
    positions = [parse_position(row) for row in read_rows(normalize_path(args.input))]
    positions = sorted(positions, key=lambda item: item["value"], reverse=True)
    total = sum(pos["value"] for pos in positions)
    top10 = sum(pos["value"] for pos in positions[:10])
    near_liq = sum(pos["value"] for pos in positions if pos["liq_distance_pct"] and pos["liq_distance_pct"] < 5)
    summary = {
        "generated_at_china": china_stamp(),
        "position_count": len(positions),
        "total_position_value_usd": round(total, 2),
        "top10_concentration_pct": round((top10 / total * 100), 2) if total else 0.0,
        "near_liquidation_value_usd": round(near_liq, 2),
        "baseline_status": "missing_previous_snapshot",
        "status": "pass",
    }
    write_rows(normalize_path(args.summary), [summary], list(summary.keys()))
    normalize_path(args.output).write_text(render(positions, summary), encoding="utf-8")
    print(f"position_count={len(positions)}")
    print(f"total_position_value_usd={summary['total_position_value_usd']}")
    print("status=pass")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
