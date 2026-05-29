import argparse
import csv
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
CN_TZ = timezone(timedelta(hours=8))


try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass


CSV_COLUMNS = [
    "bucket",
    "asset_symbol",
    "alert_type",
    "percentile",
    "price_change_pct_1h",
    "price_change_pct_24h",
    "quote_volume_usd_1h",
    "quote_volume_change_pct_1h",
    "funding_rate",
    "oi_change_pct_24h",
    "oi_level_percentile_90d",
    "interpretation",
    "reason",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate layered percentile alerts from funding/OI historical percentiles.")
    parser.add_argument("--derivatives-summary", default=str(ROOT / "results" / "v14_derivatives_history_percentiles_summary.csv"))
    parser.add_argument("--market-state", default=str(ROOT / "results" / "v14_market_state_snapshot.csv"))
    parser.add_argument("--json-output", default=str(ROOT / "results" / "v15_percentile_alerts.json"))
    parser.add_argument("--csv-output", default=str(ROOT / "results" / "v15_percentile_alerts.csv"))
    parser.add_argument("--markdown-output", default=str(ROOT / "results" / "v15_percentile_alerts.md"))
    parser.add_argument("--summary", default=str(ROOT / "results" / "v15_percentile_alerts_summary.csv"))
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


def safe_float(value: Any) -> float:
    try:
        return float(str(value).strip())
    except Exception:
        return 0.0


def china_now() -> str:
    return datetime.now(CN_TZ).replace(microsecond=0).strftime("%Y-%m-%d %H:%M:%S UTC+8")


def market_by_asset(rows: list[dict]) -> dict[str, dict]:
    return {str(row.get("asset_symbol") or "").strip().upper(): row for row in rows}


def funding_interpretation(percentile: float, price_change: float, funding_rate: float) -> tuple[str, str] | None:
    if percentile < 90:
        return None
    if funding_rate >= 0:
        if price_change > 5:
            return "多头持仓成本偏高且价格上涨，情绪偏热", "positive_funding_ge_90_and_price_up_gt_5"
        if price_change < -3:
            return "多头持仓成本偏高但价格下跌，若继续回调可能触发多头平仓", "positive_funding_ge_90_and_price_down_gt_3"
        return "多头持仓成本偏高，需结合价格变化确认", "positive_funding_ge_90"
    if price_change > 3:
        return "空头持仓成本偏高且价格反向上涨，空头可能被迫平仓", "negative_funding_ge_90_and_price_up_gt_3"
    if price_change < -3:
        return "空头持仓成本偏高，若反弹可能触发空头平仓", "negative_funding_ge_90_and_price_down_gt_3"
    return "空头持仓成本偏高，需结合价格变化确认", "negative_funding_ge_90"


def interpret_oi(change_pctile: float, level_pctile: float) -> str:
    if change_pctile >= 79.5:
        if level_pctile < 50:
            return "快速增加，从低位反弹"
        if level_pctile >= 70:
            return "快速增加且已处高位，市场拥挤"
        return "快速增加，接近历史中位数"
    if change_pctile <= 20:
        if level_pctile >= 70:
            return "快速下降但仍处高位，可能获利了结"
        return "快速下降，市场降温"
    return ""


def make_alert(bucket: str, asset: str, alert_type: str, percentile: float, market: dict, deriv: dict, interpretation: str, reason: str) -> dict:
    return {
        "bucket": bucket,
        "asset_symbol": asset,
        "alert_type": alert_type,
        "percentile": round(percentile, 1),
        "price_change_pct_1h": round(safe_float(market.get("price_change_pct_1h")), 4),
        "price_change_pct_24h": round(safe_float(market.get("price_change_pct_24h")), 4),
        "quote_volume_usd_1h": round(safe_float(market.get("quote_volume_usd_1h")), 2),
        "quote_volume_change_pct_1h": round(safe_float(market.get("quote_volume_change_pct_1h")), 4),
        "funding_rate": round(safe_float(deriv.get("funding_latest_rate")), 8),
        "oi_change_pct_24h": round(safe_float(deriv.get("oi_24h_change_pct")), 4),
        "oi_level_percentile_90d": round(safe_float(deriv.get("oi_level_percentile_90d")), 1),
        "interpretation": interpretation,
        "reason": reason,
    }


def build_alerts(deriv_rows: list[dict], market_rows: list[dict]) -> dict:
    market = market_by_asset(market_rows)
    frontpage = []
    watchlist = []
    radar = []
    digest_only = []

    for deriv in deriv_rows:
        if str(deriv.get("quality_status") or "") not in {"ok", "partial"}:
            continue
        asset = str(deriv.get("asset_symbol") or "").strip().upper()
        m = market.get(asset, {})
        funding_pctile = safe_float(deriv.get("funding_abs_percentile_90d"))
        funding_rate = safe_float(deriv.get("funding_latest_rate"))
        oi_change_pctile = safe_float(deriv.get("oi_24h_abs_change_percentile_90d"))
        oi_level_pctile = safe_float(deriv.get("oi_level_percentile_90d"))
        price_change = safe_float(m.get("price_change_pct_24h"))

        if asset in {"BTC", "ETH"} and (funding_pctile >= 90 or funding_pctile <= 10):
            frontpage.append(
                make_alert("frontpage_alerts", asset, "funding_rate_percentile", funding_pctile, m, deriv, "核心资产资金费率达到异常分位", "core_asset_funding_extreme")
            )

        oi_text = interpret_oi(oi_change_pctile, oi_level_pctile)
        if asset in {"BTC", "ETH"} and oi_text:
            frontpage.append(make_alert("frontpage_alerts", asset, "oi_change_percentile", oi_change_pctile, m, deriv, oi_text, "core_asset_oi_change_extreme"))

        funding_watch = funding_interpretation(funding_pctile, price_change, funding_rate)
        if funding_watch:
            watchlist.append(make_alert("watchlist_alerts", asset, "funding_price_confirmation", funding_pctile, m, deriv, funding_watch[0], funding_watch[1]))

        if funding_pctile >= 90 or funding_pctile <= 10 or oi_change_pctile >= 80 or oi_change_pctile <= 20:
            digest_only.append(
                make_alert("digest_context", asset, "percentile_context", max(funding_pctile, oi_change_pctile), m, deriv, oi_text or "分位偏离，进入早晚报观察", "digest_percentile_context")
            )

        price_change_1h = safe_float(m.get("price_change_pct_1h"))
        if funding_pctile >= 95 and abs(price_change_1h) >= 1.5:
            radar_text = (
                "资金费率极端分位叠加1小时价格异动，盘中波动风险升高"
                if funding_rate >= 0
                else "负费率极端分位叠加1小时价格异动，空头平仓/继续压价风险都需观察"
            )
            radar.append(make_alert("radar_triggers", asset, "funding_1h_price_radar", funding_pctile, m, deriv, radar_text, "funding_ge_95_and_abs_1h_price_ge_1_5"))

    return {
        "generated_at_china": china_now(),
        "frontpage_alerts": frontpage,
        "watchlist_alerts": watchlist,
        "radar_triggers": radar,
        "digest_context": digest_only,
    }


def flatten(payload: dict) -> list[dict]:
    rows = []
    for bucket in ("frontpage_alerts", "watchlist_alerts", "radar_triggers", "digest_context"):
        for item in payload.get(bucket, []):
            row = {column: "" for column in CSV_COLUMNS}
            row.update(item)
            row["bucket"] = bucket
            rows.append(row)
    return rows


def render_markdown(payload: dict) -> str:
    lines = ["# v15 分位数分层告警", "", f"- 生成时间：{payload.get('generated_at_china','-')}"]
    for title, key in [("首屏告警", "frontpage_alerts"), ("今日关注候选", "watchlist_alerts"), ("盘中雷达触发", "radar_triggers"), ("早晚报背景", "digest_context")]:
        lines.extend(["", f"## {title}"])
        items = payload.get(key, [])
        if not items:
            lines.append("- 暂无。")
            continue
        for item in items:
            lines.append(
                f"- {item['asset_symbol']}｜{item['alert_type']}｜分位 {item['percentile']}%｜1h {item.get('price_change_pct_1h','-')}%｜24h {item['price_change_pct_24h']}%｜{item['interpretation']}"
            )
    lines.extend(["", "说明：分位数只表示当前指标相对历史的位置，不构成任何交易建议。"])
    return "\n".join(lines) + "\n"


def main() -> int:
    args = parse_args()
    payload = build_alerts(read_rows(normalize_path(args.derivatives_summary)), read_rows(normalize_path(args.market_state)))
    rows = flatten(payload)
    normalize_path(args.json_output).parent.mkdir(parents=True, exist_ok=True)
    normalize_path(args.json_output).write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    write_rows(normalize_path(args.csv_output), rows, CSV_COLUMNS)
    normalize_path(args.markdown_output).write_text(render_markdown(payload), encoding="utf-8")
    summary = {
        "generated_at_china": payload["generated_at_china"],
        "frontpage_count": len(payload["frontpage_alerts"]),
        "watchlist_count": len(payload["watchlist_alerts"]),
        "radar_trigger_count": len(payload["radar_triggers"]),
        "digest_context_count": len(payload["digest_context"]),
        "status": "pass",
    }
    write_rows(normalize_path(args.summary), [summary], list(summary.keys()))
    print(f"frontpage={summary['frontpage_count']} watchlist={summary['watchlist_count']} radar={summary['radar_trigger_count']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
