import argparse
import csv
import time
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests


ROOT = Path(__file__).resolve().parents[1]
CHINA_TZ = timezone(timedelta(hours=8))
DAY_MS = 24 * 60 * 60 * 1000
HORIZONS = ["1h", "4h", "24h", "72h"]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build BTC regime layer report for historical event performance.")
    parser.add_argument("--backfill", default=str(ROOT / "results" / "v08_historical_replay_non_benchmark_alt_200_price_backfill.csv"))
    parser.add_argument("--output", default=str(ROOT / "results" / "v13_regime_layer_report.csv"))
    parser.add_argument("--summary", default=str(ROOT / "results" / "v13_regime_layer_summary.csv"))
    parser.add_argument("--markdown-output", default=str(ROOT / "results" / "v13_regime_layer_report.md"))
    parser.add_argument("--lookback-days", type=int, default=14)
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


def china_stamp() -> str:
    return datetime.now(CHINA_TZ).replace(microsecond=0).strftime("%Y-%m-%d %H:%M:%S UTC+8")


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


def safe_float(value) -> float | None:
    raw = str(value or "").strip()
    if not raw:
        return None
    try:
        return float(raw)
    except ValueError:
        return None


def avg(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


class BinanceCloseFetcher:
    def __init__(self, timeout: float, max_retries: int):
        self.timeout = timeout
        self.max_retries = max_retries
        self.cache: dict[int, float | None] = {}

    def close_after(self, target_ms: int) -> float | None:
        if target_ms in self.cache:
            return self.cache[target_ms]
        params = {"symbol": "BTCUSDT", "interval": "1h", "startTime": target_ms, "limit": 1}
        for attempt in range(1, self.max_retries + 1):
            try:
                resp = requests.get("https://api.binance.com/api/v3/klines", params=params, timeout=self.timeout)
                if resp.status_code == 200:
                    data = resp.json()
                    value = float(data[0][4]) if data else None
                    self.cache[target_ms] = value
                    return value
                if resp.status_code in {400, 404}:
                    break
            except requests.RequestException:
                pass
            time.sleep(min(0.5 * attempt, 2.0))
        self.cache[target_ms] = None
        return None


def regime_for(return_14d: float | None) -> str:
    if return_14d is None:
        return "data_missing"
    if return_14d >= 0.08:
        return "btc_uptrend"
    if return_14d <= -0.08:
        return "btc_downtrend"
    return "btc_range"


def main() -> int:
    args = parse_args()
    rows = [row for row in read_rows(normalize_path(args.backfill)) if str(row.get("status") or "").lower() in {"ok", "partial"}]
    fetcher = BinanceCloseFetcher(args.timeout, args.max_retries)
    enriched = []
    for row in rows:
        event_ms = parse_utc_ms(row.get("event_time_utc") or row.get("event_time"))
        btc_t0 = safe_float(row.get("btc_price_t0"))
        btc_pre = fetcher.close_after(event_ms - args.lookback_days * DAY_MS) if event_ms else None
        btc_ret_14d = btc_t0 / btc_pre - 1 if btc_t0 is not None and btc_pre not in {None, 0} else None
        item = dict(row)
        item["btc_regime_return_14d"] = "" if btc_ret_14d is None else round(btc_ret_14d, 6)
        item["btc_regime_trend_14d"] = regime_for(btc_ret_14d)
        enriched.append(item)

    grouped = defaultdict(list)
    for row in enriched:
        key = (
            row.get("event_subtype") or row.get("event_type") or "unknown",
            row.get("btc_regime_trend_14d") or "unknown",
        )
        grouped[key].append(row)

    output = []
    for (event_group, regime), items in grouped.items():
        out = {
            "generated_at_china": china_stamp(),
            "event_group": event_group,
            "btc_regime_trend_14d": regime,
            "sample_count": len(items),
        }
        for horizon in HORIZONS:
            values = [safe_float(row.get(f"abnormal_vs_btc_{horizon}")) for row in items]
            values = [value for value in values if value is not None]
            out[f"computed_{horizon}_count"] = len(values)
            out[f"avg_abnormal_vs_btc_{horizon}"] = round(avg(values), 6)
            out[f"win_rate_vs_btc_{horizon}"] = round(sum(1 for value in values if value > 0) / len(values), 4) if values else 0.0
        output.append(out)
    output.sort(key=lambda row: (row["event_group"], row["btc_regime_trend_14d"]))
    write_rows(normalize_path(args.output), output, list(output[0].keys()) if output else ["event_group"])

    eligible_groups = defaultdict(set)
    for row in output:
        if int(row.get("computed_24h_count", 0) or 0) >= 10:
            eligible_groups[row["event_group"]].add(row["btc_regime_trend_14d"])
    robust_groups = {group: regimes for group, regimes in eligible_groups.items() if len(regimes) >= 2}
    summary = {
        "generated_at_china": china_stamp(),
        "status": "warning" if not robust_groups else "pass",
        "input_rows": len(rows),
        "output_rows": len(output),
        "regime_ready_event_group_count": len(robust_groups),
        "data_missing_rows": sum(1 for row in enriched if row["btc_regime_trend_14d"] == "data_missing"),
        "output": str(normalize_path(args.output)),
    }
    write_rows(normalize_path(args.summary), [summary], list(summary.keys()))

    lines = [
        "# v13 Regime Layer Report",
        "",
        f"- generated_at_china: {summary['generated_at_china']}",
        f"- input_rows: {summary['input_rows']}",
        f"- regime_ready_event_group_count: {summary['regime_ready_event_group_count']}",
        f"- status: {summary['status']}",
        "",
        "| event_group | regime | samples | avg_24h | win_rate_24h | avg_72h | win_rate_72h |",
        "|---|---|---:|---:|---:|---:|---:|",
    ]
    for row in output:
        lines.append(
            f"| {row['event_group']} | {row['btc_regime_trend_14d']} | {row['sample_count']} | "
            f"{row['avg_abnormal_vs_btc_24h']} | {row['win_rate_vs_btc_24h']} | "
            f"{row['avg_abnormal_vs_btc_72h']} | {row['win_rate_vs_btc_72h']} |"
        )
    lines.append("")
    normalize_path(args.markdown_output).write_text("\n".join(lines), encoding="utf-8")
    print(f"input_rows={len(rows)}")
    print(f"output_rows={len(output)}")
    print(f"status={summary['status']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
