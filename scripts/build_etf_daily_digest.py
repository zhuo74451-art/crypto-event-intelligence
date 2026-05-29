import argparse
import csv
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd
import requests
from io import StringIO
import statistics


ROOT = Path(__file__).resolve().parents[1]
CHINA_TZ = timezone(timedelta(hours=8))
DEFAULT_URL = "https://farside.co.uk/bitcoin-etf-flow-all-data/"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build daily BTC ETF flow digest from Farside public table.")
    parser.add_argument("--url", default=DEFAULT_URL)
    parser.add_argument("--output", default=str(ROOT / "data" / "etf_daily_flows_farside.csv"))
    parser.add_argument("--asset", default="BTC")
    parser.add_argument("--digest-output", default=str(ROOT / "results" / "v14_etf_daily_digest.md"))
    parser.add_argument("--summary", default=str(ROOT / "results" / "v14_etf_daily_digest_summary.csv"))
    parser.add_argument("--min-abs-net-flow-usd", type=float, default=100_000_000)
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
    text = str(value or "").strip().replace(",", "")
    if not text or text in {"-", "nan", "None"}:
        return 0.0
    negative = text.startswith("(") and text.endswith(")")
    text = text.strip("()")
    try:
        number = float(text)
        return -number if negative else number
    except Exception:
        return 0.0


def fetch_farside(url: str) -> pd.DataFrame:
    resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0 CryptoEventIntelligence/0.1"}, timeout=30)
    resp.raise_for_status()
    tables = pd.read_html(StringIO(resp.text))
    if not tables:
        raise RuntimeError("no_html_tables")
    table = max(tables, key=lambda df: len(df.columns))
    table = table.dropna(how="all")
    table.columns = [str(col).strip() for col in table.columns]
    return table


def normalize_table(df: pd.DataFrame, asset: str = "BTC") -> list[dict]:
    rows = []
    for _, rec in df.iterrows():
        data = {str(k).strip(): rec[k] for k in df.columns}
        date_value = str(data.get("Date") or data.get("date") or "").strip()
        if not date_value or date_value.lower() in {"total", "average", "maximum", "minimum"}:
            continue
        total_m = safe_float(data.get("Total"))
        if total_m == 0 and "Total" not in data:
            continue
        parsed_date = pd.to_datetime(date_value, dayfirst=True, errors="coerce")
        row = {
            "date": date_value,
            "date_sort": parsed_date.strftime("%Y-%m-%d") if not pd.isna(parsed_date) else "",
            "asset": str(asset or "BTC").upper(),
            "source": "Farside Investors",
            "total_net_flow_usd": round(total_m * 1_000_000, 2),
        }
        for key, value in data.items():
            if key == "Date":
                continue
            row[key] = safe_float(value) * 1_000_000
        rows.append(row)
    rows.sort(key=lambda row: row.get("date_sort", ""), reverse=True)
    return rows


def money(value: float) -> str:
    sign = "+" if value > 0 else ""
    return f"{sign}{value / 1_000_000:.1f}M 美元"


def latest_completed_row(rows: list[dict]) -> dict:
    for row in rows:
        if safe_float(row.get("total_net_flow_usd")) != 0:
            return row
    return rows[0] if rows else {}


def parse_date_sort(value: str):
    try:
        return datetime.strptime(str(value or ""), "%Y-%m-%d").replace(tzinfo=timezone.utc)
    except Exception:
        return None


def render_digest(rows: list[dict], publishable: bool, threshold: float, asset: str = "BTC") -> str:
    asset = str(asset or "BTC").upper()
    if not rows:
        return f"📊 <b>{asset} ETF 日频资金流</b>\n暂无可用数据。\n"
    latest = latest_completed_row(rows)
    latest_total = safe_float(latest.get("total_net_flow_usd"))
    recent = [safe_float(row.get("total_net_flow_usd")) for row in rows[:30]]
    avg_7d = sum(recent[:7]) / min(len(recent), 7) if recent else 0.0
    avg_30d = sum(recent) / len(recent) if recent else 0.0
    stdev_30d = statistics.pstdev(recent) if len(recent) >= 2 else 0.0
    zscore = (latest_total - avg_30d) / stdev_30d if stdev_30d else 0.0
    issuers = []
    for key, value in latest.items():
        if key in {"date", "date_sort", "asset", "source", "total_net_flow_usd", "Total"}:
            continue
        amount = safe_float(value)
        if amount:
            issuers.append((key, amount))
    issuers.sort(key=lambda item: abs(item[1]), reverse=True)
    lines = [
        f"📊 <b>{asset} ETF 日频资金流</b>",
        f"数据源：Farside Investors｜等级：公开一手表格",
        f"数据日期：{latest.get('date')}（美股收盘后确认）",
        f"总净流：{money(latest_total)}",
        f"异常程度：z={zscore:+.2f}｜{'异常' if abs(zscore) >= 2 else '常规波动'}",
        f"状态：{'已确认日频数据' if safe_float(latest.get('total_net_flow_usd')) else '当日未完成或无数据'}",
        "",
    ]
    for key, amount in issuers[:5]:
        lines.append(f"• {key}: {money(amount)}")
    lines.extend(
        [
            "",
            f"近 7 日均值：{money(avg_7d)}",
            f"近 30 日均值：{money(avg_30d)}",
            f"发布判断：{'进入晚报候选' if publishable else f'低于 {money(threshold)} 阈值，仅归档'}",
            "验证链接：https://farside.co.uk/bitcoin-etf-flow-all-data/",
            "",
            "⚠️ ETF 资金流适合日频观察，不代表任何交易建议。",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> int:
    args = parse_args()
    status = "pass"
    error = ""
    rows: list[dict] = []
    try:
        rows = normalize_table(fetch_farside(args.url), args.asset)
        write_rows(normalize_path(args.output), rows, list(rows[0].keys()) if rows else ["date"])
    except Exception as exc:
        status = "warning"
        error = str(exc)
    if status == "pass" and not rows:
        status = "warning"
        error = "no_rows_parsed"
    latest = latest_completed_row(rows)
    latest_total = safe_float(latest.get("total_net_flow_usd")) if latest else 0.0
    recent = [safe_float(row.get("total_net_flow_usd")) for row in rows[:30]]
    avg_7d = sum(recent[:7]) / min(len(recent), 7) if recent else 0.0
    avg_30d = sum(recent) / len(recent) if recent else 0.0
    stdev_30d = statistics.pstdev(recent) if len(recent) >= 2 else 0.0
    zscore = (latest_total - avg_30d) / stdev_30d if stdev_30d else 0.0
    is_anomaly = abs(zscore) >= 2.0 or abs(latest_total) >= args.min_abs_net_flow_usd
    latest_dt = parse_date_sort(latest.get("date_sort", "")) if latest else None
    today_utc = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    days_lag = (today_utc - latest_dt).days if latest_dt else ""
    date_validation_status = "missing"
    if latest_dt:
        if latest_dt > today_utc:
            date_validation_status = "future_date_error"
        elif days_lag > 10:
            date_validation_status = "stale_warning"
        else:
            date_validation_status = "ok"
    publishable = bool(rows and is_anomaly)
    top_flows = []
    if latest:
        for key, value in latest.items():
            if key in {"date", "date_sort", "asset", "source", "total_net_flow_usd", "Total"}:
                continue
            amount = safe_float(value)
            if amount:
                top_flows.append((key, amount))
        top_flows.sort(key=lambda item: abs(item[1]), reverse=True)
    normalize_path(args.digest_output).write_text(render_digest(rows, publishable, args.min_abs_net_flow_usd, args.asset), encoding="utf-8")
    summary = {
        "generated_at_china": china_stamp(),
        "source": "Farside Investors",
        "rows": len(rows),
        "latest_date": latest.get("date", "") if latest else "",
        "latest_date_sort": latest.get("date_sort", "") if latest else "",
        "latest_days_lag": days_lag,
        "date_validation_status": date_validation_status,
        "latest_total_net_flow_usd": round(latest_total, 2),
        "flow_7d_avg": round(avg_7d, 2),
        "flow_30d_avg": round(avg_30d, 2),
        "flow_30d_std": round(stdev_30d, 2),
        "flow_zscore": round(zscore, 4),
        "is_anomaly": "true" if is_anomaly else "false",
        "anomaly_reason": "abs_zscore_ge_2_or_abs_flow_ge_threshold" if is_anomaly else "within_normal_range",
        "top_3_etf_by_flow": ";".join(f"{key}:{round(value, 2)}" for key, value in top_flows[:3]),
        "publishable_daily_digest": "true" if publishable and date_validation_status == "ok" else "false",
        "status": status if date_validation_status != "future_date_error" else "warning",
        "error": error,
    }
    write_rows(normalize_path(args.summary), [summary], list(summary.keys()))
    print(f"rows={len(rows)}")
    print(f"publishable_daily_digest={summary['publishable_daily_digest']}")
    print(f"status={status}")
    if error:
        print(f"error={error[:160]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
