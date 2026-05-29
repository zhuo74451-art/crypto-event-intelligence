import argparse
import csv
import json
import sqlite3
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests


ROOT = Path(__file__).resolve().parents[1]
CHINA_TZ = timezone(timedelta(hours=8))
CACHE_DB = ROOT / "data" / "price_cache.sqlite"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build 5m/15m/1h pre-event price-in checks using Binance public klines.")
    parser.add_argument("--backfill", default=str(ROOT / "results" / "v08_historical_replay_non_benchmark_alt_500_price_backfill.csv"))
    parser.add_argument("--output", default=str(ROOT / "data" / "v14_short_price_in.csv"))
    parser.add_argument("--summary", default=str(ROOT / "results" / "v14_short_price_in_summary.csv"))
    parser.add_argument("--limit", type=int, default=500)
    parser.add_argument("--force-refresh", action="store_true")
    parser.add_argument("--flush-every", type=int, default=25)
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


def parse_utc(value: str) -> datetime | None:
    raw = str(value or "").strip()
    if not raw:
        return None
    try:
        if raw.endswith("Z"):
            return datetime.fromisoformat(raw.replace("Z", "+00:00")).astimezone(timezone.utc)
        return datetime.fromisoformat(raw).replace(tzinfo=timezone.utc)
    except Exception:
        return None


def safe_float(value) -> float:
    try:
        return float(str(value or "").strip())
    except Exception:
        return 0.0


def ensure_cache(con: sqlite3.Connection) -> None:
    con.execute(
        """
        CREATE TABLE IF NOT EXISTS price_cache (
            provider TEXT NOT NULL,
            market_type TEXT NOT NULL,
            symbol TEXT NOT NULL,
            interval TEXT NOT NULL,
            target_timestamp_ms INTEGER NOT NULL,
            kline_open_time_ms INTEGER NOT NULL,
            close_price REAL NOT NULL,
            raw_json TEXT NOT NULL,
            created_at TEXT NOT NULL,
            PRIMARY KEY (provider, market_type, symbol, interval, target_timestamp_ms)
        )
        """
    )
    con.commit()


def cache_get(con: sqlite3.Connection, provider: str, market_type: str, symbol: str, interval: str, target_ms: int) -> tuple[int, float] | None:
    row = con.execute(
        """
        SELECT kline_open_time_ms, close_price FROM price_cache
        WHERE provider=? AND market_type=? AND symbol=? AND interval=? AND target_timestamp_ms=?
        """,
        (provider, market_type, symbol, interval, target_ms),
    ).fetchone()
    if not row:
        return None
    return int(row[0]), float(row[1])


def cache_put(con: sqlite3.Connection, provider: str, market_type: str, symbol: str, interval: str, target_ms: int, open_ms: int, close: float, raw) -> None:
    con.execute(
        """
        INSERT OR REPLACE INTO price_cache
        (provider, market_type, symbol, interval, target_timestamp_ms, kline_open_time_ms, close_price, raw_json, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (provider, market_type, symbol, interval, target_ms, open_ms, close, json.dumps(raw, ensure_ascii=False), china_stamp()),
    )
    con.commit()


def fetch_close(con: sqlite3.Connection, symbol: str, market_type: str, target_ms: int, force_refresh: bool) -> tuple[int, float, str]:
    provider = "binance"
    interval = "1m"
    market_type = market_type if market_type in {"spot", "futures"} else "spot"
    cached = None if force_refresh else cache_get(con, provider, market_type, symbol, interval, target_ms)
    if cached:
        return cached[0], cached[1], "cache"
    if market_type == "futures":
        url = "https://fapi.binance.com/fapi/v1/klines"
    else:
        url = "https://api.binance.com/api/v3/klines"
    params = {"symbol": symbol, "interval": interval, "startTime": target_ms, "limit": 1}
    last_error = ""
    for attempt in range(3):
        try:
            resp = requests.get(url, params=params, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                if data:
                    open_ms = int(data[0][0])
                    close = float(data[0][4])
                    cache_put(con, provider, market_type, symbol, interval, target_ms, open_ms, close, data[0])
                    return open_ms, close, "api"
                last_error = "empty_kline"
            else:
                last_error = f"http_{resp.status_code}"
        except requests.RequestException as exc:
            last_error = type(exc).__name__
        time.sleep(0.05 * (attempt + 1))
    raise RuntimeError(last_error or "request_failed")


def pct_change(current: float, previous: float) -> float:
    if current <= 0 or previous <= 0:
        return 0.0
    return current / previous - 1


def main() -> int:
    args = parse_args()
    rows = read_rows(normalize_path(args.backfill))[: args.limit]
    output_path = normalize_path(args.output)
    processed = set()
    output = []
    if output_path.exists() and not args.force_refresh:
        output = read_rows(output_path)
        processed = {str(row.get("event_id") or "") for row in output}
    CACHE_DB.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(CACHE_DB)
    ensure_cache(con)
    for index, row in enumerate(rows, 1):
        if str(row.get("event_id") or "") in processed:
            continue
        event_time = parse_utc(row.get("event_time_utc") or row.get("event_time"))
        symbol = str(row.get("symbol_used") or row.get("binance_spot_symbol") or row.get("binance_futures_symbol") or "").strip().upper()
        market_type = str(row.get("market_type") or "spot").strip()
        t0_price = safe_float(row.get("asset_price_t0"))
        item = {
            "event_id": row.get("event_id", ""),
            "asset_symbol": row.get("asset_symbol", ""),
            "symbol": symbol,
            "event_time_utc": row.get("event_time_utc", ""),
            "price_in_5m": "",
            "price_in_15m": "",
            "price_in_1h": "",
            "short_price_in_flag": "missing",
            "short_price_in_reason": "",
            "title": row.get("title", ""),
        }
        if not event_time or not symbol or t0_price <= 0:
            item["short_price_in_reason"] = "missing_time_symbol_or_t0"
            output.append(item)
            continue
        reasons = []
        for minutes, threshold in [(5, 0.01), (15, 0.02), (60, 0.03)]:
            target_ms = int((event_time - timedelta(minutes=minutes)).timestamp() * 1000)
            try:
                _, pre_price, _ = fetch_close(con, symbol, market_type, target_ms, args.force_refresh)
                move = pct_change(t0_price, pre_price)
                item[f"price_in_{minutes if minutes != 60 else '1h'}{'m' if minutes != 60 else ''}"] = f"{move:.6f}"
                if abs(move) > threshold:
                    reasons.append(f"already_priced_in_{minutes}m_{move:+.2%}")
            except Exception as exc:
                reasons.append(f"missing_{minutes}m_price:{exc}")
        item["short_price_in_flag"] = "price_in_block" if any(r.startswith("already_priced_in") for r in reasons) else "pass"
        item["short_price_in_reason"] = ",".join(reasons) if reasons else "pass"
        output.append(item)
        if index % max(1, args.flush_every) == 0:
            write_rows(output_path, output, list(output[0].keys()) if output else ["event_id"])
            print(f"processed={len(output)}/{len(rows)}", flush=True)
    write_rows(output_path, output, list(output[0].keys()) if output else ["event_id"])
    summary = {
        "generated_at_china": china_stamp(),
        "input_rows": len(output),
        "pass_rows": sum(1 for row in output if row["short_price_in_flag"] == "pass"),
        "price_in_block_rows": sum(1 for row in output if row["short_price_in_flag"] == "price_in_block"),
        "missing_rows": sum(1 for row in output if row["short_price_in_flag"] == "missing"),
        "status": "pass",
    }
    write_rows(normalize_path(args.summary), [summary], list(summary.keys()))
    print(f"input_rows={summary['input_rows']}")
    print(f"pass_rows={summary['pass_rows']}")
    print(f"price_in_block_rows={summary['price_in_block_rows']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
