import argparse
import csv
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import requests


ROOT = Path(__file__).resolve().parents[2]
BASE_URL = "https://fapi.binance.com"
CN_TZ = timezone(timedelta(hours=8))


try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass


DETAIL_COLUMNS = [
    "asset_symbol",
    "binance_futures_symbol",
    "metric",
    "sample_time_utc",
    "sample_time_china",
    "value",
]

SUMMARY_COLUMNS = [
    "generated_at_china",
    "asset_symbol",
    "binance_futures_symbol",
    "funding_samples",
    "funding_latest_time_china",
    "funding_latest_rate",
    "funding_abs_percentile_90d",
    "funding_label",
    "oi_samples",
    "oi_latest_time_china",
    "oi_latest_value_usd",
    "oi_24h_change_pct",
    "oi_24h_abs_change_percentile_90d",
    "oi_level_percentile_90d",
    "oi_label",
    "quality_status",
    "skip_reason",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build Binance USD-M funding and open-interest historical percentiles.")
    parser.add_argument("--watchlist", default=str(ROOT / "data" / "funding_watchlist.csv"))
    parser.add_argument("--market-state", default=str(ROOT / "results" / "v14_market_state_snapshot.csv"))
    parser.add_argument("--funding-output", default=str(ROOT / "data" / "funding_rate" / "funding_rate_percentiles.csv"))
    parser.add_argument("--oi-output", default=str(ROOT / "data" / "oi" / "oi_percentiles.csv"))
    parser.add_argument("--summary", default=str(ROOT / "results" / "v14_derivatives_history_percentiles_summary.csv"))
    parser.add_argument("--markdown-output", default=str(ROOT / "results" / "v14_derivatives_history_percentiles.md"))
    parser.add_argument("--days", type=int, default=90)
    parser.add_argument("--funding-limit", type=int, default=1000)
    parser.add_argument("--oi-period", default="4h")
    parser.add_argument("--oi-limit", type=int, default=500)
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


def enabled_watch_rows(path: Path) -> list[dict]:
    return [row for row in read_rows(path) if str(row.get("enabled", "")).strip().lower() in {"1", "true", "yes", "y"}]


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(str(value).strip())
    except Exception:
        return default


def request_json(session: requests.Session, endpoint: str, params: dict, timeout: int = 20, retries: int = 3) -> Any:
    last_error = None
    for attempt in range(1, retries + 1):
        try:
            response = session.get(f"{BASE_URL}{endpoint}", params=params, timeout=timeout)
            if response.status_code < 500:
                response.raise_for_status()
                return response.json()
            last_error = RuntimeError(f"http={response.status_code}; body={response.text[:200]}")
        except Exception as exc:
            last_error = exc
        time.sleep(min(2 * attempt, 6))
    raise RuntimeError(f"request_failed:{last_error}")


def ms_to_utc(ms: Any) -> str:
    try:
        return datetime.fromtimestamp(int(ms) / 1000, tz=timezone.utc).replace(microsecond=0).strftime("%Y-%m-%dT%H:%M:%SZ")
    except Exception:
        return ""


def utc_to_china(utc_iso: str) -> str:
    raw = str(utc_iso or "").strip()
    if raw.endswith("Z"):
        raw = raw[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(raw).astimezone(CN_TZ)
    except Exception:
        return ""
    return dt.strftime("%Y-%m-%d %H:%M:%S UTC+8")


def china_now() -> str:
    return datetime.now(CN_TZ).replace(microsecond=0).strftime("%Y-%m-%d %H:%M:%S UTC+8")


def percentile(values: list[float], current: float, absolute: bool = False) -> float:
    sample = [abs(v) if absolute else v for v in values if v is not None]
    if not sample:
        return 0.0
    cur = abs(current) if absolute else current
    return round(sum(1 for v in sample if v <= cur) / len(sample) * 100, 1)


def label_from_percentile(pct: float, high_word: str = "偏高") -> str:
    if pct >= 95:
        return "极端"
    if pct >= 75:
        return high_word
    if pct >= 25:
        return "中性"
    return "偏低"


def market_by_symbol(path: Path) -> dict[str, dict]:
    output = {}
    for row in read_rows(path):
        symbol = str(row.get("binance_futures_symbol") or "").strip().upper()
        if symbol:
            output[symbol] = row
    return output


def fetch_funding(session: requests.Session, symbol: str, days: int, limit: int) -> list[dict]:
    end = datetime.now(timezone.utc)
    start_ms = int((end - timedelta(days=days)).timestamp() * 1000)
    end_ms = int(end.timestamp() * 1000)
    data = request_json(
        session,
        "/fapi/v1/fundingRate",
        {"symbol": symbol, "startTime": start_ms, "endTime": end_ms, "limit": limit},
    )
    return data if isinstance(data, list) else []


def fetch_oi(session: requests.Session, symbol: str, period: str, limit: int) -> list[dict]:
    data = request_json(session, "/futures/data/openInterestHist", {"symbol": symbol, "period": period, "limit": limit})
    return data if isinstance(data, list) else []


def period_to_24h_lag(period: str) -> int:
    mapping = {
        "1h": 24,
        "2h": 12,
        "4h": 6,
        "6h": 4,
        "8h": 3,
        "12h": 2,
        "1d": 1,
    }
    return mapping.get(str(period).lower(), 1)


def oi_24h_changes(records: list[dict], period: str) -> list[float]:
    values = [safe_float(row.get("sumOpenInterestValue")) for row in records if safe_float(row.get("sumOpenInterestValue")) > 0]
    lag = period_to_24h_lag(period)
    changes = []
    for idx in range(lag, len(values)):
        prev = values[idx - lag]
        curr = values[idx]
        if prev > 0:
            changes.append((curr / prev - 1) * 100)
    return changes


def detail_row(asset: str, symbol: str, metric: str, time_ms: Any, value: float) -> dict:
    utc = ms_to_utc(time_ms)
    return {
        "asset_symbol": asset,
        "binance_futures_symbol": symbol,
        "metric": metric,
        "sample_time_utc": utc,
        "sample_time_china": utc_to_china(utc),
        "value": f"{value:.10f}",
    }


def build_for_symbol(session: requests.Session, item: dict, args: argparse.Namespace, market_rows: dict[str, dict]) -> tuple[list[dict], list[dict], dict]:
    asset = str(item.get("asset_symbol") or "").strip().upper()
    symbol = str(item.get("binance_futures_symbol") or "").strip().upper()
    summary = {column: "" for column in SUMMARY_COLUMNS}
    summary.update({"generated_at_china": china_now(), "asset_symbol": asset, "binance_futures_symbol": symbol})
    if not symbol:
        summary["quality_status"] = "skipped"
        summary["skip_reason"] = "missing_symbol"
        return [], [], summary
    funding_details = []
    oi_details = []
    try:
        funding = fetch_funding(session, symbol, args.days, args.funding_limit)
        oi = fetch_oi(session, symbol, args.oi_period, args.oi_limit)
    except Exception as exc:
        summary["quality_status"] = "skipped"
        summary["skip_reason"] = str(exc)[:180]
        return [], [], summary

    funding_values = []
    for row in funding:
        rate = safe_float(row.get("fundingRate"))
        funding_values.append(rate)
        funding_details.append(detail_row(asset, symbol, "funding_rate", row.get("fundingTime"), rate))
    latest_funding = funding_values[-1] if funding_values else safe_float(market_rows.get(symbol, {}).get("funding_rate"))
    latest_funding_time = funding_details[-1]["sample_time_china"] if funding_details else ""
    funding_pct = percentile(funding_values, latest_funding, absolute=True)

    oi_values = []
    for row in oi:
        value = safe_float(row.get("sumOpenInterestValue"))
        if value > 0:
            oi_values.append(value)
            oi_details.append(detail_row(asset, symbol, "open_interest_value_usd", row.get("timestamp"), value))
    changes = oi_24h_changes(oi, args.oi_period)
    current_market = market_rows.get(symbol, {})
    latest_oi = safe_float(current_market.get("open_interest_usd")) or (oi_values[-1] if oi_values else 0.0)
    latest_oi_time = oi_details[-1]["sample_time_china"] if oi_details else ""
    latest_oi_change = safe_float(current_market.get("open_interest_change_pct_24h")) or (changes[-1] if changes else 0.0)
    oi_change_pctile = percentile(changes, latest_oi_change, absolute=True)
    oi_level_pctile = percentile(oi_values, latest_oi, absolute=False)

    summary.update(
        {
            "funding_samples": len(funding_values),
            "funding_latest_time_china": latest_funding_time,
            "funding_latest_rate": f"{latest_funding:.8f}",
            "funding_abs_percentile_90d": f"{funding_pct:.1f}",
            "funding_label": label_from_percentile(funding_pct),
            "oi_samples": len(oi_values),
            "oi_latest_time_china": latest_oi_time,
            "oi_latest_value_usd": f"{latest_oi:.2f}",
            "oi_24h_change_pct": f"{latest_oi_change:.4f}",
            "oi_24h_abs_change_percentile_90d": f"{oi_change_pctile:.1f}",
            "oi_level_percentile_90d": f"{oi_level_pctile:.1f}",
            "oi_label": label_from_percentile(max(oi_change_pctile, oi_level_pctile)),
            "quality_status": "ok" if funding_values or oi_values else "partial",
            "skip_reason": "" if funding_values or oi_values else "no_history_records",
        }
    )
    return funding_details, oi_details, summary


def amount_yi(value: Any) -> str:
    return f"{safe_float(value) / 100_000_000:.2f} 亿美元"


def render_markdown(rows: list[dict]) -> str:
    ok_rows = [row for row in rows if row.get("quality_status") in {"ok", "partial"}]
    lines = [
        "# v14 合约历史分位",
        "",
        f"- 生成时间：{china_now()}",
        f"- 覆盖资产：{len(ok_rows)}",
        "",
        "## 核心资产",
    ]
    for row in [r for r in ok_rows if r.get("asset_symbol") in {"BTC", "ETH"}]:
        lines.append(
            f"- {row.get('asset_symbol')}: 资金费率 {safe_float(row.get('funding_latest_rate')) * 100:.4f}%"
            f"（90日绝对分位 {row.get('funding_abs_percentile_90d')}%，{row.get('funding_label')}）；"
            f"OI 24h {row.get('oi_24h_change_pct')}%"
            f"（变化分位 {row.get('oi_24h_abs_change_percentile_90d')}%，水平分位 {row.get('oi_level_percentile_90d')}%，{row.get('oi_label')}）。"
        )
    lines.extend(["", "## 其他资产高分位"])
    high = sorted(
        [row for row in ok_rows if row.get("asset_symbol") not in {"BTC", "ETH"}],
        key=lambda row: max(safe_float(row.get("funding_abs_percentile_90d")), safe_float(row.get("oi_24h_abs_change_percentile_90d"))),
        reverse=True,
    )
    for row in high[:5]:
        lines.append(
            f"- {row.get('asset_symbol')}: 资金费率分位 {row.get('funding_abs_percentile_90d')}%，OI变化分位 {row.get('oi_24h_abs_change_percentile_90d')}%。"
        )
    lines.extend(["", "说明：历史分位用于判断当前值是否异常，不构成任何交易建议。"])
    return "\n".join(lines) + "\n"


def main() -> int:
    args = parse_args()
    session = requests.Session()
    session.trust_env = False
    watch_rows = enabled_watch_rows(normalize_path(args.watchlist))
    market_rows = market_by_symbol(normalize_path(args.market_state))
    funding_details_all = []
    oi_details_all = []
    summaries = []
    for index, item in enumerate(watch_rows, start=1):
        symbol = str(item.get("binance_futures_symbol") or "").strip().upper()
        print(f"[{index}/{len(watch_rows)}] history_percentiles symbol={symbol}")
        funding_details, oi_details, summary = build_for_symbol(session, item, args, market_rows)
        funding_details_all.extend(funding_details)
        oi_details_all.extend(oi_details)
        summaries.append(summary)
    write_rows(normalize_path(args.funding_output), funding_details_all, DETAIL_COLUMNS)
    write_rows(normalize_path(args.oi_output), oi_details_all, DETAIL_COLUMNS)
    write_rows(normalize_path(args.summary), summaries, SUMMARY_COLUMNS)
    normalize_path(args.markdown_output).write_text(render_markdown(summaries), encoding="utf-8")
    ok_count = sum(1 for row in summaries if row.get("quality_status") == "ok")
    print(f"history_percentile_rows={len(summaries)} ok={ok_count}")
    return 0 if ok_count else 1


if __name__ == "__main__":
    raise SystemExit(main())
