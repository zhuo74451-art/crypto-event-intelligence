import argparse
import csv
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
CHINA_TZ = timezone(timedelta(hours=8))


EXCLUDE_COLUMNS = {"date", "date_sort", "asset", "source", "total_net_flow_usd", "Total"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build BTC ETF daily digest with 90d baseline and same-period context.")
    parser.add_argument("--input", default=str(ROOT / "data" / "etf_daily_flows_farside.csv"))
    parser.add_argument("--output", default=str(ROOT / "results" / "v14_etf_daily_digest_with_context.md"))
    parser.add_argument("--summary", default=str(ROOT / "results" / "v14_etf_daily_digest_with_context_summary.csv"))
    return parser.parse_args()


def normalize_path(value: str | Path) -> Path:
    path = Path(value)
    if not path.is_absolute():
        path = ROOT / path
    return path


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


def parse_date(value: str):
    try:
        return datetime.strptime(str(value or ""), "%Y-%m-%d").date()
    except Exception:
        return None


def money_yi(value: float, show_sign: bool = True) -> str:
    if not show_sign:
        return f"{abs(value) / 100_000_000:.2f} 亿美元"
    sign = "+" if value > 0 else ""
    return f"{sign}{value / 100_000_000:.2f} 亿美元"


def percent(value: float) -> str:
    return f"{value:.1f}%"


def pp(value: float | None) -> str:
    if value is None:
        return "无前值"
    sign = "+" if value >= 0 else ""
    return f"{sign}{value:.1f}pp"


def latest_completed(df: pd.DataFrame) -> pd.Series:
    completed = df[df["total_net_flow_usd"].abs() > 0].copy()
    if completed.empty:
        return df.iloc[0]
    return completed.sort_values("date_sort", ascending=False).iloc[0]


def issuer_flows(row: pd.Series) -> list[tuple[str, float]]:
    flows = []
    for key, value in row.items():
        if key in EXCLUDE_COLUMNS:
            continue
        amount = safe_float(value)
        if amount:
            flows.append((str(key), amount))
    flows.sort(key=lambda item: abs(item[1]), reverse=True)
    return flows


def issuer_share_map(row: pd.Series) -> dict[str, float]:
    total = abs(safe_float(row.get("total_net_flow_usd")))
    if not total:
        return {}
    return {key: abs(value) / total * 100 for key, value in issuer_flows(row)}


def calendar_effect_window(day) -> tuple[bool, str]:
    if day is None:
        return False, ""
    if day.month in {3, 6, 9, 12} and day.day >= 25:
        return True, "quarter_end_rebalance_window"
    if day.day >= 25:
        return True, "month_end_rebalance_window"
    return False, ""


def render_markdown(summary: dict, top_rows: list[dict]) -> str:
    anomaly_text = "异常" if summary["is_dynamic_anomaly"] == "true" else "常规"
    lines = [
        "## BTC ETF 日频资金流背景",
        "",
        f"数据日期：{summary['latest_date']}｜生成时间：中国时间 {summary['generated_at_china']}",
        f"昨日净流：**{money_yi(float(summary['latest_total_net_flow_usd']))}**，在过去 90 个交易日中绝对值排名第 **{summary['abs_rank_90d']}**，分位数 **{summary['abs_percentile_90d']}%**。",
        f"动态阈值：90 日绝对流量 {summary['adjusted_abs_percentile_threshold']} 分位为 **{money_yi(float(summary['adjusted_abs_threshold_usd']), show_sign=False)}**，当前判断：**{anomaly_text}**。",
        f"日历效应：{summary['calendar_effect_window']}｜{summary['calendar_effect_note']}",
        "",
        "### 历史对比",
        f"- 近 30 日均值：{money_yi(float(summary['avg_30d_net_flow_usd']))}",
        f"- 去年同期 ±7 天均值：{money_yi(float(summary['same_period_last_year_avg_usd'])) if summary['same_period_last_year_rows'] != '0' else '暂无去年同期样本'}",
        f"- 结论：{summary['context_conclusion']}",
        "",
        "### Top 3 ETF",
        "| ETF | 流量 | 占比 | 环比变化 |",
        "|---|---:|---:|---:|",
    ]
    for row in top_rows:
        lines.append(f"| {row['issuer']} | {money_yi(float(row['flow_usd']))} | {row['share_pct']}% | {row['share_change_pp']} |")
    lines.extend(
        [
            "",
            "读取方式：ETF 日频流量适合放在早晚报，不适合当成盘中即时信号。重点看绝对金额、90 日分位、发行商集中度和是否属于月末/节假日结算效应。",
            "",
            "⚠️ 仅作市场结构观察，不构成任何交易建议。",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> int:
    args = parse_args()
    input_path = normalize_path(args.input)
    if not input_path.exists():
        raise FileNotFoundError(input_path)
    df = pd.read_csv(input_path)
    df["date_sort"] = df["date_sort"].astype(str)
    df["parsed_date"] = df["date_sort"].map(parse_date)
    df["total_net_flow_usd"] = pd.to_numeric(df["total_net_flow_usd"], errors="coerce").fillna(0.0)
    df = df[df["parsed_date"].notna()].copy()
    df = df.sort_values("date_sort", ascending=False)
    latest = latest_completed(df)
    latest_date = latest["parsed_date"]
    prior = df[df["parsed_date"] < latest_date].sort_values("date_sort", ascending=False)
    rolling_90 = prior.head(89).copy()
    current_plus_90 = pd.concat([latest.to_frame().T, rolling_90], ignore_index=True)
    abs_values = current_plus_90["total_net_flow_usd"].abs()
    p95 = float(abs_values.quantile(0.95)) if len(abs_values) else 0.0
    p98 = float(abs_values.quantile(0.98)) if len(abs_values) else 0.0
    latest_abs = abs(float(latest["total_net_flow_usd"]))
    calendar_window, calendar_reason = calendar_effect_window(latest_date)
    threshold_quantile = 0.98 if calendar_window else 0.95
    adjusted_threshold = p98 if calendar_window else p95
    rank = int((abs_values > latest_abs).sum() + 1)
    percentile = round((abs_values <= latest_abs).sum() / len(abs_values) * 100, 1) if len(abs_values) else 0.0
    recent_30 = prior.head(29)
    avg_30 = float(pd.concat([latest.to_frame().T, recent_30], ignore_index=True)["total_net_flow_usd"].mean())
    same_start = latest_date.replace(year=latest_date.year - 1) - timedelta(days=7)
    same_end = latest_date.replace(year=latest_date.year - 1) + timedelta(days=7)
    same_period = df[(df["parsed_date"] >= same_start) & (df["parsed_date"] <= same_end) & (df["total_net_flow_usd"].abs() > 0)]
    same_avg = float(same_period["total_net_flow_usd"].mean()) if not same_period.empty else 0.0
    dynamic_anomaly = latest_abs >= adjusted_threshold if adjusted_threshold else False
    if not same_period.empty and latest_abs > abs(same_avg) * 2:
        context = "当前流量显著高于去年同期基线，需要进入晚报背景观察。"
    elif dynamic_anomaly:
        context = "当前流量超过 90 日动态阈值，但去年同期样本不足或差异不极端。"
    else:
        context = "当前流量未超过 90 日动态阈值，作为常规日频背景记录。"

    previous = prior.iloc[0] if not prior.empty else None
    prev_shares = issuer_share_map(previous) if previous is not None else {}
    latest_shares = issuer_share_map(latest)
    top_rows = []
    for issuer, amount in issuer_flows(latest)[:3]:
        share = latest_shares.get(issuer, 0.0)
        prev_share = prev_shares.get(issuer)
        top_rows.append(
            {
                "issuer": issuer,
                "flow_usd": round(amount, 2),
                "share_pct": round(share, 1),
                "share_change_pp": pp(round(share - prev_share, 1) if prev_share is not None else None),
            }
        )

    summary = {
        "generated_at_china": china_stamp(),
        "latest_date": latest.get("date", ""),
        "latest_date_sort": latest.get("date_sort", ""),
        "latest_total_net_flow_usd": round(float(latest["total_net_flow_usd"]), 2),
        "rolling_90d_abs_p95": round(p95, 2),
        "rolling_90d_abs_p98": round(p98, 2),
        "calendar_effect_window": "true" if calendar_window else "false",
        "calendar_effect_reason": calendar_reason,
        "calendar_effect_note": "月末/季末窗口提高阈值，避免把结算再平衡误当事件信号。" if calendar_window else "非月末/季末再平衡窗口。",
        "adjusted_abs_percentile_threshold": int(threshold_quantile * 100),
        "adjusted_abs_threshold_usd": round(adjusted_threshold, 2),
        "abs_rank_90d": rank,
        "abs_percentile_90d": percentile,
        "avg_30d_net_flow_usd": round(avg_30, 2),
        "same_period_last_year_rows": len(same_period),
        "same_period_last_year_avg_usd": round(same_avg, 2),
        "is_dynamic_anomaly": "true" if dynamic_anomaly else "false",
        "top_3_etf_by_share": ";".join(f"{row['issuer']}:{row['share_pct']}:{row['share_change_pp']}" for row in top_rows),
        "context_conclusion": context,
        "status": "pass",
    }
    normalize_path(args.output).write_text(render_markdown(summary, top_rows), encoding="utf-8")
    write_rows(normalize_path(args.summary), [summary], list(summary.keys()))
    print(f"latest_date={summary['latest_date']}")
    print(f"latest_total_net_flow_usd={summary['latest_total_net_flow_usd']}")
    print(f"abs_percentile_90d={summary['abs_percentile_90d']}")
    print(f"is_dynamic_anomaly={summary['is_dynamic_anomaly']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
