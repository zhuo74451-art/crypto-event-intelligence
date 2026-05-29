import argparse
import csv
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
CHINA_TZ = timezone(timedelta(hours=8))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build monitored-liquidation-risk context from monitored Hyperliquid positions.")
    parser.add_argument("--input", default=str(ROOT / "data" / "hyperliquid_position_state.csv"))
    parser.add_argument("--output", default=str(ROOT / "results" / "v15_hyperliquid_liquidation_wall.md"))
    parser.add_argument("--csv-output", default=str(ROOT / "results" / "v15_hyperliquid_liquidation_wall.csv"))
    parser.add_argument("--summary", default=str(ROOT / "results" / "v15_hyperliquid_liquidation_wall_summary.csv"))
    parser.add_argument("--digest-threshold-pct", type=float, default=10.0)
    parser.add_argument("--radar-threshold-pct", type=float, default=5.0)
    return parser.parse_args()


def normalize_path(value: str | Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else ROOT / path


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


def safe_float(value: Any) -> float:
    try:
        return float(str(value or "").replace(",", "").strip())
    except Exception:
        return 0.0


def money(value: Any) -> str:
    number = safe_float(value)
    if abs(number) >= 100_000_000:
        return f"{number / 100_000_000:.2f} 亿美元"
    if abs(number) >= 10_000:
        return f"{number / 10_000:.2f} 万美元"
    return f"{number:.2f} 美元"


def china_stamp() -> str:
    return datetime.now(CHINA_TZ).replace(microsecond=0).strftime("%Y-%m-%d %H:%M:%S UTC+8")


def route_for(distance_pct: float, radar_threshold: float, digest_threshold: float) -> str:
    if 0 < distance_pct <= radar_threshold:
        return "radar"
    if 0 < distance_pct <= digest_threshold:
        return "digest"
    return "hidden"


def normalize_position(row: dict, radar_threshold: float, digest_threshold: float) -> dict:
    side = str(row.get("side") or "").strip().lower()
    distance_pct = safe_float(row.get("liquidation_distance_pct")) * 100
    mark_px = safe_float(row.get("mark_px"))
    liquidation_px = safe_float(row.get("liquidation_px"))
    return {
        "asset_symbol": str(row.get("asset_symbol") or "").strip().upper(),
        "side": side,
        "trigger_direction": "价格下跌触发多头清算" if side == "long" else "价格上涨触发空头清算" if side == "short" else "方向未知",
        "position_value_usd": round(safe_float(row.get("position_value_usd")), 2),
        "mark_px": mark_px,
        "liquidation_px": liquidation_px,
        "liquidation_distance_pct": round(distance_pct, 2),
        "route": route_for(distance_pct, radar_threshold, digest_threshold),
        "entity": str(row.get("entity") or "").strip(),
        "address": str(row.get("address") or "").strip(),
        "updated_at_china": str(row.get("updated_at_china") or "").strip(),
    }


def build_groups(rows: list[dict]) -> dict[tuple[str, str], dict]:
    grouped: dict[tuple[str, str], dict] = defaultdict(
        lambda: {
            "position_count": 0,
            "position_value_usd": 0.0,
            "nearest_distance_pct": 0.0,
            "nearest_liquidation_px": 0.0,
            "nearest_entity": "",
            "route": "hidden",
        }
    )
    route_rank = {"hidden": 0, "digest": 1, "radar": 2}
    for row in rows:
        key = (row["asset_symbol"], row["side"])
        item = grouped[key]
        item["position_count"] += 1
        item["position_value_usd"] += row["position_value_usd"]
        current_distance = row["liquidation_distance_pct"]
        if not item["nearest_distance_pct"] or current_distance < item["nearest_distance_pct"]:
            item["nearest_distance_pct"] = current_distance
            item["nearest_liquidation_px"] = row["liquidation_px"]
            item["nearest_entity"] = row["entity"]
        if route_rank[row["route"]] > route_rank[item["route"]]:
            item["route"] = row["route"]
    output = []
    for (asset, side), item in grouped.items():
        output.append(
            {
                "asset_symbol": asset,
                "side": side,
                "trigger_direction": "价格下跌触发多头清算" if side == "long" else "价格上涨触发空头清算" if side == "short" else "方向未知",
                "position_count": item["position_count"],
                "position_value_usd": round(item["position_value_usd"], 2),
                "nearest_distance_pct": round(item["nearest_distance_pct"], 2),
                "nearest_liquidation_px": round(item["nearest_liquidation_px"], 8),
                "nearest_entity": item["nearest_entity"],
                "route": item["route"],
            }
        )
    return sorted(output, key=lambda item: ({"radar": 0, "digest": 1, "hidden": 2}[item["route"]], item["nearest_distance_pct"]))


def render(groups: list[dict], rows: list[dict]) -> str:
    visible_groups = [row for row in groups if row["route"] in {"radar", "digest"}]
    lines = ["# Hyperliquid 监控大户监控地址清算风险", ""]
    lines.append(f"- 时间：中国时间 {china_stamp()}")
    lines.append("- 口径：只使用已监控的大户仓位，不使用第三方清算热力图估算。")
    lines.append("")
    if not visible_groups:
        lines.append("当前没有距离清算价 10% 以内的监控仓位；盘中不建议单独推送，只在早晚报保留一句背景。")
    else:
        lines.append("## 需要进入摘要的监控地址清算风险")
        for item in visible_groups[:12]:
            label = "盘中雷达" if item["route"] == "radar" else "摘要关注"
            lines.append(
                f"- {label}｜{item['asset_symbol']} {item['side']}｜{item['trigger_direction']}｜"
                f"最近距离 {item['nearest_distance_pct']:.2f}%｜清算价 {item['nearest_liquidation_px']}｜"
                f"合计 {money(item['position_value_usd'])}｜{item['position_count']} 个监控仓位"
            )
    lines.append("")
    lines.append("## 最近的单仓")
    nearest = sorted(rows, key=lambda item: item["liquidation_distance_pct"])[:8]
    for item in nearest:
        lines.append(
            f"- {item['asset_symbol']} {item['side']}｜{item['liquidation_distance_pct']:.2f}%｜"
            f"{money(item['position_value_usd'])}｜{item['entity']}"
        )
    lines.append("")
    lines.append("提示：这是链上/合约结构观察，不构成任何交易建议。")
    return "\n".join(lines) + "\n"


def main() -> int:
    args = parse_args()
    rows = [
        normalize_position(row, args.radar_threshold_pct, args.digest_threshold_pct)
        for row in read_rows(normalize_path(args.input))
        if str(row.get("above_threshold") or "").lower() in {"true", "1", "yes"}
    ]
    rows = [row for row in rows if row["asset_symbol"] and row["position_value_usd"] > 0]
    groups = build_groups(rows)

    csv_fields = [
        "asset_symbol",
        "side",
        "trigger_direction",
        "position_count",
        "position_value_usd",
        "nearest_distance_pct",
        "nearest_liquidation_px",
        "nearest_entity",
        "route",
    ]
    write_rows(normalize_path(args.csv_output), groups, csv_fields)
    normalize_path(args.output).parent.mkdir(parents=True, exist_ok=True)
    normalize_path(args.output).write_text(render(groups, rows), encoding="utf-8")

    summary = {
        "position_rows": len(rows),
        "wall_rows": len(groups),
        "radar_count": sum(1 for row in groups if row["route"] == "radar"),
        "digest_count": sum(1 for row in groups if row["route"] == "digest"),
        "hidden_count": sum(1 for row in groups if row["route"] == "hidden"),
        "near_10_value_usd": round(sum(row["position_value_usd"] for row in groups if row["route"] in {"radar", "digest"}), 2),
        "status": "pass" if rows else "warning",
    }
    write_rows(normalize_path(args.summary), [summary], list(summary.keys()))
    print(f"liquidation_wall wall_rows={summary['wall_rows']} radar={summary['radar_count']} digest={summary['digest_count']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
