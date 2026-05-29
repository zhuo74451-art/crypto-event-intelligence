import argparse
import csv
import time
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests


ROOT = Path(__file__).resolve().parents[1]
CHINA_TZ = timezone(timedelta(hours=8))
HOUR_MS = 60 * 60 * 1000


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate pre-event price-in effects for historical event backfills.")
    parser.add_argument("--backfill", default=str(ROOT / "results" / "v08_historical_replay_non_benchmark_alt_200_price_backfill.csv"))
    parser.add_argument("--output", default=str(ROOT / "results" / "v13_price_in_report.csv"))
    parser.add_argument("--summary", default=str(ROOT / "results" / "v13_price_in_summary.csv"))
    parser.add_argument("--markdown-output", default=str(ROOT / "results" / "v13_price_in_report.md"))
    parser.add_argument("--timeout", type=float, default=10.0)
    parser.add_argument("--max-retries", type=int, default=3)
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


def safe_float(value) -> float | None:
    raw = str(value or "").strip()
    if not raw:
        return None
    try:
        return float(raw)
    except ValueError:
        return None


def parse_utc_ms(value: str) -> int | None:
    text = str(value or "").strip()
    if not text:
        return None
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(text)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return int(dt.astimezone(timezone.utc).timestamp() * 1000)


def utc_ms_to_iso(ms: int | None) -> str:
    if ms is None:
        return ""
    return datetime.fromtimestamp(ms / 1000, tz=timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def china_stamp() -> str:
    return datetime.now(CHINA_TZ).replace(microsecond=0).strftime("%Y-%m-%d %H:%M:%S UTC+8")


class KlineFetcher:
    def __init__(self, timeout: float, max_retries: int):
        self.timeout = timeout
        self.max_retries = max_retries
        self.memory_cache: dict[tuple[str, str, str, int], tuple[float | None, int | None]] = {}

    def endpoint(self, market_type: str) -> str:
        if str(market_type or "").lower() == "futures":
            return "https://fapi.binance.com/fapi/v1/klines"
        return "https://api.binance.com/api/v3/klines"

    def close_after(self, symbol: str, market_type: str, target_ms: int) -> tuple[float | None, int | None]:
        symbol = str(symbol or "").strip().upper()
        market_type = str(market_type or "spot").strip().lower()
        if not symbol:
            return None, None
        for interval in ("1m", "5m"):
            key = (market_type, symbol, interval, target_ms)
            if key in self.memory_cache:
                return self.memory_cache[key]
            params = {"symbol": symbol, "interval": interval, "startTime": target_ms, "limit": 1}
            url = self.endpoint(market_type)
            for attempt in range(1, self.max_retries + 1):
                try:
                    resp = requests.get(url, params=params, timeout=self.timeout)
                    if resp.status_code == 200:
                        data = resp.json()
                        if data:
                            result = (float(data[0][4]), int(data[0][0]))
                            self.memory_cache[key] = result
                            return result
                        break
                    if resp.status_code in {400, 404}:
                        break
                except requests.RequestException:
                    pass
                time.sleep(min(0.5 * attempt, 2.0))
            self.memory_cache[key] = (None, None)
        return None, None


def calc_return(end: float | None, start: float | None) -> float | None:
    if end is None or start is None or start == 0:
        return None
    return end / start - 1


def price_in_ratio(pre_abnormal: float | None, post_abnormal: float | None) -> float | None:
    if pre_abnormal is None or post_abnormal is None:
        return None
    if post_abnormal > 0:
        pre = max(pre_abnormal, 0.0)
        post = max(post_abnormal, 0.0)
    elif post_abnormal < 0:
        pre = max(-pre_abnormal, 0.0)
        post = max(-post_abnormal, 0.0)
    else:
        pre = abs(pre_abnormal)
        post = 0.0
    denom = pre + post
    if denom <= 0:
        return 0.0
    return min(max(pre / denom, 0.0), 1.0)


def flag_for(ratio: float | None) -> str:
    if ratio is None:
        return "data_missing"
    if ratio >= 0.7:
        return "severe"
    if ratio >= 0.5:
        return "moderate"
    return "none"


def main() -> int:
    args = parse_args()
    rows = read_rows(normalize_path(args.backfill))
    fetcher = KlineFetcher(timeout=args.timeout, max_retries=args.max_retries)
    output = []
    for row in rows:
        event_ms = parse_utc_ms(row.get("event_time_utc") or row.get("price_target_t0_utc") or row.get("event_time"))
        symbol = str(row.get("symbol_used") or row.get("binance_futures_symbol") or row.get("binance_spot_symbol") or "").strip().upper()
        market_type = str(row.get("market_type") or "spot").strip().lower()
        asset_t0 = safe_float(row.get("asset_price_t0"))
        asset_24h = safe_float(row.get("asset_price_24h"))
        btc_t0 = safe_float(row.get("btc_price_t0"))
        btc_24h = safe_float(row.get("btc_price_24h"))
        pre_ms = event_ms - 6 * HOUR_MS if event_ms else None
        asset_pre, asset_pre_kline = fetcher.close_after(symbol, market_type, pre_ms) if pre_ms else (None, None)
        btc_pre, btc_pre_kline = fetcher.close_after("BTCUSDT", "spot", pre_ms) if pre_ms else (None, None)
        asset_pre_return = calc_return(asset_t0, asset_pre)
        btc_pre_return = calc_return(btc_t0, btc_pre)
        pre_abnormal = asset_pre_return - btc_pre_return if asset_pre_return is not None and btc_pre_return is not None else None
        asset_post_24h = calc_return(asset_24h, asset_t0)
        btc_post_24h = calc_return(btc_24h, btc_t0)
        post_abnormal = asset_post_24h - btc_post_24h if asset_post_24h is not None and btc_post_24h is not None else safe_float(row.get("abnormal_vs_btc_24h"))
        ratio = price_in_ratio(pre_abnormal, post_abnormal)
        output.append(
            {
                "event_id": row.get("event_id", ""),
                "event_type": row.get("event_type", ""),
                "event_subtype": row.get("event_subtype", ""),
                "asset_symbol": row.get("asset_symbol", ""),
                "source": row.get("source", ""),
                "event_time_utc": row.get("event_time_utc") or row.get("price_target_t0_utc") or "",
                "pre_target_6h_utc": utc_ms_to_iso(pre_ms),
                "asset_price_pre_6h": "" if asset_pre is None else f"{asset_pre:.12g}",
                "asset_price_pre_6h_kline_time_utc": utc_ms_to_iso(asset_pre_kline),
                "btc_price_pre_6h": "" if btc_pre is None else f"{btc_pre:.12g}",
                "btc_price_pre_6h_kline_time_utc": utc_ms_to_iso(btc_pre_kline),
                "pre_asset_return_6h": "" if asset_pre_return is None else round(asset_pre_return, 6),
                "pre_btc_return_6h": "" if btc_pre_return is None else round(btc_pre_return, 6),
                "pre_event_abnormal_6h": "" if pre_abnormal is None else round(pre_abnormal, 6),
                "post_event_abnormal_24h": "" if post_abnormal is None else round(post_abnormal, 6),
                "price_in_ratio": "" if ratio is None else round(ratio, 6),
                "price_in_flag": flag_for(ratio),
                "title": row.get("title", ""),
            }
        )

    fields = list(output[0].keys()) if output else ["event_id"]
    write_rows(normalize_path(args.output), output, fields)

    grouped = defaultdict(list)
    for row in output:
        grouped[row["event_subtype"] or row["event_type"] or "unknown"].append(row)
    summary_rows = []
    for name, items in sorted(grouped.items(), key=lambda kv: (-len(kv[1]), kv[0])):
        ratios = [safe_float(row.get("price_in_ratio")) for row in items]
        ratios = [ratio for ratio in ratios if ratio is not None]
        severe = sum(1 for row in items if row.get("price_in_flag") == "severe")
        data_missing = sum(1 for row in items if row.get("price_in_flag") == "data_missing")
        severe_ratio = severe / len(items) if items else 0.0
        status = "fail" if severe_ratio >= 0.6 else "warning" if severe_ratio >= 0.3 or data_missing else "pass"
        summary_rows.append(
            {
                "generated_at_china": china_stamp(),
                "event_group": name,
                "total_events": len(items),
                "computed_count": len(ratios),
                "data_missing_count": data_missing,
                "severe_price_in_count": severe,
                "severe_price_in_ratio": round(severe_ratio, 4),
                "avg_price_in_ratio": round(sum(ratios) / len(ratios), 6) if ratios else 0.0,
                "status": status,
            }
        )
    write_rows(normalize_path(args.summary), summary_rows, list(summary_rows[0].keys()) if summary_rows else ["event_group"])

    severe_cases = [row for row in output if row.get("price_in_flag") == "severe"][:10]
    none_cases = [row for row in output if row.get("price_in_flag") == "none"][:10]
    lines = [
        "# v13 Price-In Report",
        "",
        f"- generated_at_china: {china_stamp()}",
        f"- input_rows: {len(rows)}",
        f"- output_rows: {len(output)}",
        "",
        "## Summary",
        "",
        "| event_group | total | severe_ratio | avg_price_in_ratio | status |",
        "|---|---:|---:|---:|---|",
    ]
    for row in summary_rows[:30]:
        lines.append(f"| {row['event_group']} | {row['total_events']} | {row['severe_price_in_ratio']} | {row['avg_price_in_ratio']} | {row['status']} |")
    lines.extend(["", "## Severe Cases", "", "| event_id | asset | group | pre_abn_6h | post_abn_24h | ratio | title |", "|---|---|---|---:|---:|---:|---|"])
    for row in severe_cases:
        title = str(row.get("title", "")).replace("|", "\\|")[:120]
        lines.append(f"| {row['event_id']} | {row['asset_symbol']} | {row['event_subtype'] or row['event_type']} | {row['pre_event_abnormal_6h']} | {row['post_event_abnormal_24h']} | {row['price_in_ratio']} | {title} |")
    lines.extend(["", "## Non Price-In Cases", "", "| event_id | asset | group | pre_abn_6h | post_abn_24h | ratio | title |", "|---|---|---|---:|---:|---:|---|"])
    for row in none_cases:
        title = str(row.get("title", "")).replace("|", "\\|")[:120]
        lines.append(f"| {row['event_id']} | {row['asset_symbol']} | {row['event_subtype'] or row['event_type']} | {row['pre_event_abnormal_6h']} | {row['post_event_abnormal_24h']} | {row['price_in_ratio']} | {title} |")
    lines.append("")
    normalize_path(args.markdown_output).write_text("\n".join(lines), encoding="utf-8")
    print(f"output_rows={len(output)}")
    print(f"summary_rows={len(summary_rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
