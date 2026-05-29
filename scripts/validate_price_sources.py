import argparse
import json
import logging
import sqlite3
import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any

import pandas as pd
import requests


ROOT = Path(__file__).resolve().parents[1]
SPOT_URL = "https://api.binance.com/api/v3/klines"
FUTURES_URL = "https://fapi.binance.com/fapi/v1/klines"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate cached Binance kline prices by refetching public API data.")
    parser.add_argument("--cache", default=str(ROOT / "data" / "price_cache.sqlite"))
    parser.add_argument("--output", default=str(ROOT / "results" / "price_source_validation_report.csv"))
    parser.add_argument("--sample-size", type=int, default=30)
    parser.add_argument("--timeout", type=int, default=10)
    parser.add_argument("--retries", type=int, default=3)
    parser.add_argument("--recent-symbol", default="BTCUSDT")
    parser.add_argument("--recent-market-type", choices=["spot", "futures"], default="spot")
    parser.add_argument("--recent-hours-ago", type=float, default=24.0)
    parser.add_argument(
        "--recent-output",
        default=str(ROOT / "results" / "recent_price_point_sample.csv"),
    )
    return parser.parse_args()


def normalize_path(value: str) -> Path:
    path = Path(value)
    if not path.is_absolute():
        path = ROOT / path
    return path


def endpoint(market_type: str) -> str:
    if market_type == "spot":
        return SPOT_URL
    if market_type == "futures":
        return FUTURES_URL
    raise ValueError(f"unsupported market_type={market_type}")


def fetch_kline(
    market_type: str,
    symbol: str,
    interval: str,
    target_timestamp_ms: int,
    timeout: int,
    retries: int,
) -> list[Any] | None:
    last_error: Exception | None = None
    for attempt in range(1, retries + 1):
        try:
            response = requests.get(
                endpoint(market_type),
                params={
                    "symbol": symbol,
                    "interval": interval,
                    "startTime": int(target_timestamp_ms),
                    "limit": 1,
                },
                timeout=timeout,
            )
            if response.status_code != 200:
                raise RuntimeError(f"http_{response.status_code}: {response.text[:200]}")
            data = response.json()
            if not data:
                return None
            return data[0]
        except Exception as exc:
            last_error = exc
            if attempt < retries:
                time.sleep(0.5 * attempt)
    if last_error:
        raise last_error
    return None


def load_cache_sample(cache_path: Path, sample_size: int) -> pd.DataFrame:
    if not cache_path.exists():
        raise FileNotFoundError(f"cache not found: {cache_path}")
    conn = sqlite3.connect(cache_path)
    try:
        query = """
            SELECT
                provider,
                market_type,
                symbol,
                interval,
                target_timestamp_ms,
                kline_open_time_ms,
                close_price,
                raw_json,
                created_at
            FROM price_cache
            WHERE provider = 'binance'
            ORDER BY RANDOM()
            LIMIT ?
        """
        return pd.read_sql_query(query, conn, params=(sample_size,))
    finally:
        conn.close()


def validate_cache_rows(df: pd.DataFrame, timeout: int, retries: int) -> pd.DataFrame:
    rows = []
    for _, row in df.iterrows():
        result = row.to_dict()
        try:
            kline = fetch_kline(
                str(row["market_type"]),
                str(row["symbol"]),
                str(row["interval"]),
                int(row["target_timestamp_ms"]),
                timeout,
                retries,
            )
            if not kline:
                result.update({"validation_status": "missing_fresh_kline", "validation_error": ""})
            else:
                fresh_open = int(kline[0])
                fresh_close = float(kline[4])
                cached_close = float(row["close_price"])
                diff_abs = fresh_close - cached_close
                diff_pct = diff_abs / cached_close if cached_close else ""
                result.update(
                    {
                        "fresh_kline_open_time_ms": fresh_open,
                        "fresh_close_price": fresh_close,
                        "close_diff_abs": diff_abs,
                        "close_diff_pct": diff_pct,
                        "open_time_diff_ms": fresh_open - int(row["kline_open_time_ms"]),
                        "target_to_open_lag_ms": fresh_open - int(row["target_timestamp_ms"]),
                        "validation_status": "ok" if abs(diff_abs) < 1e-12 and fresh_open == int(row["kline_open_time_ms"]) else "mismatch",
                        "validation_error": "",
                    }
                )
        except Exception as exc:
            result.update({"validation_status": "request_failed", "validation_error": str(exc)})
        rows.append(result)
    return pd.DataFrame(rows)


def fetch_recent_point(symbol: str, market_type: str, hours_ago: float, timeout: int, retries: int) -> pd.DataFrame:
    now = datetime.now(timezone.utc)
    target = now - timedelta(hours=hours_ago)
    target_ms = int(target.timestamp() * 1000)
    kline = fetch_kline(market_type, symbol.upper(), "1m", target_ms, timeout, retries)
    if not kline:
        return pd.DataFrame(
            [
                {
                    "symbol": symbol.upper(),
                    "market_type": market_type,
                    "interval": "1m",
                    "target_time_utc": target.strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "target_timestamp_ms": target_ms,
                    "status": "missing_kline",
                }
            ]
        )
    open_time_ms = int(kline[0])
    close_time_ms = int(kline[6])
    return pd.DataFrame(
        [
            {
                "symbol": symbol.upper(),
                "market_type": market_type,
                "interval": "1m",
                "target_time_utc": target.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "target_time_china": target.astimezone(timezone(timedelta(hours=8))).strftime("%Y-%m-%d %H:%M:%S UTC+8"),
                "target_timestamp_ms": target_ms,
                "kline_open_time_utc": datetime.fromtimestamp(open_time_ms / 1000, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "kline_open_time_china": datetime.fromtimestamp(open_time_ms / 1000, timezone.utc).astimezone(timezone(timedelta(hours=8))).strftime("%Y-%m-%d %H:%M:%S UTC+8"),
                "kline_open_time_ms": open_time_ms,
                "kline_close_time_utc": datetime.fromtimestamp(close_time_ms / 1000, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "kline_close_time_china": datetime.fromtimestamp(close_time_ms / 1000, timezone.utc).astimezone(timezone(timedelta(hours=8))).strftime("%Y-%m-%d %H:%M:%S UTC+8"),
                "open_price": float(kline[1]),
                "high_price": float(kline[2]),
                "low_price": float(kline[3]),
                "close_price": float(kline[4]),
                "volume": float(kline[5]),
                "raw_json": json.dumps(kline, ensure_ascii=False),
                "status": "ok",
            }
        ]
    )


def main() -> int:
    args = parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", datefmt="%H:%M:%S")
    cache_path = normalize_path(args.cache)
    output_path = normalize_path(args.output)
    recent_output_path = normalize_path(args.recent_output)

    try:
        sample = load_cache_sample(cache_path, args.sample_size)
        report = validate_cache_rows(sample, args.timeout, args.retries)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        report.to_csv(output_path, index=False)

        recent = fetch_recent_point(
            args.recent_symbol,
            args.recent_market_type,
            args.recent_hours_ago,
            args.timeout,
            args.retries,
        )
        recent_output_path.parent.mkdir(parents=True, exist_ok=True)
        recent.to_csv(recent_output_path, index=False)

        status_counts = report["validation_status"].value_counts().to_dict() if not report.empty else {}
        logging.info("wrote validation report to %s", output_path)
        logging.info("validation status counts: %s", status_counts)
        logging.info("wrote recent price point to %s", recent_output_path)
        return 0
    except Exception as exc:
        logging.error("price validation failed: %s", exc)
        return 1


if __name__ == "__main__":
    sys.exit(main())
