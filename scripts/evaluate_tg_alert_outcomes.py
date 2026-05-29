import argparse
import csv
import json
import math
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests


ROOT = Path(__file__).resolve().parents[1]
SPOT_BASE = "https://api.binance.com"
FUTURES_BASE = "https://fapi.binance.com"
HORIZONS = [("1h", 1), ("4h", 4), ("24h", 24), ("72h", 72)]


try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass


OUTCOME_COLUMNS = [
    "alert_id",
    "evaluated_at_china",
    "published_at_china",
    "published_at_utc",
    "asset_symbol",
    "event_type",
    "event_subtype",
    "source_type",
    "benchmark_primary",
    "benchmark_secondary",
    "market_type_used",
    "symbol_used",
    "price_t0",
    "price_pre_1h",
    "price_pre_4h",
    "pre_return_1h",
    "pre_return_4h",
    "priced_in_flag",
    "priced_in_reason",
    "btc_price_t0",
    "eth_price_t0",
    "btc_return_14d",
    "btc_realized_vol_7d",
    "btc_regime_trend_14d",
    "btc_regime_vol_7d",
    "asset_return_1h",
    "asset_return_4h",
    "asset_return_24h",
    "asset_return_72h",
    "btc_return_1h",
    "btc_return_4h",
    "btc_return_24h",
    "btc_return_72h",
    "eth_return_1h",
    "eth_return_4h",
    "eth_return_24h",
    "eth_return_72h",
    "abnormal_primary_1h",
    "abnormal_primary_4h",
    "abnormal_primary_24h",
    "abnormal_primary_72h",
    "abnormal_secondary_1h",
    "abnormal_secondary_4h",
    "abnormal_secondary_24h",
    "abnormal_secondary_72h",
    "horizons_evaluated",
    "horizons_pending",
    "quality_status",
    "skip_reason",
]


SUMMARY_COLUMNS = [
    "status",
    "evaluated_at_china",
    "ledger_rows",
    "outcome_rows",
    "new_or_updated_rows",
    "evaluable_alerts",
    "skipped_alerts",
    "output",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate post-publish outcomes for TG alert ledger rows.")
    parser.add_argument("--ledger", default=str(ROOT / "data" / "tg_alert_ledger.csv"))
    parser.add_argument("--output", default=str(ROOT / "data" / "tg_alert_outcomes.csv"))
    parser.add_argument("--summary", default=str(ROOT / "results" / "tg_alert_outcome_eval_summary.csv"))
    parser.add_argument("--limit", type=int, default=500)
    parser.add_argument("--interval", default="1m")
    parser.add_argument("--timeout", type=int, default=10)
    parser.add_argument("--retries", type=int, default=3)
    return parser.parse_args()


def normalize_path(value: str | Path) -> Path:
    path = Path(value)
    if not path.is_absolute():
        path = ROOT / path
    return path


def china_now() -> datetime:
    return datetime.now(timezone(timedelta(hours=8))).replace(microsecond=0)


def china_stamp(dt: datetime | None = None) -> str:
    return (dt or china_now()).strftime("%Y-%m-%d %H:%M:%S UTC+8")


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


def parse_utc(value: str) -> datetime | None:
    raw = str(value or "").strip()
    if not raw:
        return None
    try:
        if raw.endswith("Z"):
            return datetime.fromisoformat(raw.replace("Z", "+00:00")).astimezone(timezone.utc)
        dt = datetime.fromisoformat(raw)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception:
        return None


def ms(dt: datetime) -> int:
    return int(dt.timestamp() * 1000)


def safe_float(value) -> float:
    try:
        return float(str(value or "").strip())
    except Exception:
        return math.nan


def fmt(value) -> str:
    if value is None:
        return ""
    try:
        number = float(value)
    except Exception:
        return ""
    if math.isnan(number) or math.isinf(number):
        return ""
    return f"{number:.10f}".rstrip("0").rstrip(".")


def pct_return(start, end) -> float:
    start_f = safe_float(start)
    end_f = safe_float(end)
    if math.isnan(start_f) or math.isnan(end_f) or start_f == 0:
        return math.nan
    return end_f / start_f - 1


def request_json(url: str, params: dict, timeout: int, retries: int):
    last_error = None
    for attempt in range(1, retries + 1):
        try:
            resp = requests.get(url, params=params, timeout=timeout)
            if resp.status_code == 200:
                return resp.json()
            last_error = RuntimeError(f"http={resp.status_code}; body={resp.text[:120]}")
        except Exception as exc:
            last_error = exc
        time.sleep(min(attempt, 3))
    raise RuntimeError(str(last_error))


def fetch_close(symbol: str, target: datetime, market_type: str, interval: str, args: argparse.Namespace) -> tuple[float, str]:
    if not symbol:
        return math.nan, ""
    if market_type == "spot":
        url = f"{SPOT_BASE}/api/v3/klines"
    else:
        url = f"{FUTURES_BASE}/fapi/v1/klines"
    payload = request_json(
        url,
        {
            "symbol": symbol,
            "interval": interval,
            "startTime": ms(target),
            "limit": 1,
        },
        args.timeout,
        args.retries,
    )
    if not isinstance(payload, list) or not payload:
        return math.nan, ""
    row = payload[0]
    try:
        return float(row[4]), str(row[0])
    except Exception:
        return math.nan, ""


def fetch_close_any(asset: str, target: datetime, args: argparse.Namespace) -> tuple[float, str, str]:
    symbol = f"{asset.upper()}USDT"
    for market_type in ["spot", "futures"]:
        try:
            price, _ = fetch_close(symbol, target, market_type, args.interval, args)
            if not math.isnan(price):
                return price, market_type, symbol
        except Exception:
            continue
    return math.nan, "", symbol


def fetch_klines(symbol: str, start: datetime, market_type: str, interval: str, limit: int, args: argparse.Namespace) -> list:
    if market_type == "spot":
        url = f"{SPOT_BASE}/api/v3/klines"
    else:
        url = f"{FUTURES_BASE}/fapi/v1/klines"
    payload = request_json(
        url,
        {
            "symbol": symbol,
            "interval": interval,
            "startTime": ms(start),
            "limit": limit,
        },
        args.timeout,
        args.retries,
    )
    if not isinstance(payload, list):
        return []
    return payload


def realized_vol_from_closes(closes: list[float]) -> float:
    returns = []
    for prev, cur in zip(closes, closes[1:]):
        if prev:
            returns.append(cur / prev - 1)
    if len(returns) < 24:
        return math.nan
    mean = sum(returns) / len(returns)
    variance = sum((value - mean) ** 2 for value in returns) / max(len(returns) - 1, 1)
    return math.sqrt(variance) * math.sqrt(len(returns))


def btc_regime(published_at: datetime, btc_t0: float, args: argparse.Namespace) -> dict[str, str]:
    result = {
        "btc_return_14d": "",
        "btc_realized_vol_7d": "",
        "btc_regime_trend_14d": "",
        "btc_regime_vol_7d": "",
    }
    btc_14d, _, _ = fetch_close_any("BTC", published_at - timedelta(days=14), args)
    btc_return = pct_return(btc_14d, btc_t0)
    result["btc_return_14d"] = fmt(btc_return)
    if not math.isnan(btc_return):
        if btc_return >= 0.05:
            result["btc_regime_trend_14d"] = "uptrend"
        elif btc_return <= -0.05:
            result["btc_regime_trend_14d"] = "downtrend"
        else:
            result["btc_regime_trend_14d"] = "range"

    try:
        rows = fetch_klines("BTCUSDT", published_at - timedelta(days=7), "spot", "1h", 168, args)
        closes = [float(row[4]) for row in rows if len(row) > 4]
        vol = realized_vol_from_closes(closes)
        result["btc_realized_vol_7d"] = fmt(vol)
        if not math.isnan(vol):
            if vol >= 0.12:
                result["btc_regime_vol_7d"] = "high_vol"
            elif vol <= 0.06:
                result["btc_regime_vol_7d"] = "low_vol"
            else:
                result["btc_regime_vol_7d"] = "mid_vol"
    except Exception:
        pass
    return result


def choose_benchmarks(asset: str) -> tuple[str, str]:
    asset = asset.upper()
    if asset == "BTC":
        return "ETH", ""
    if asset == "ETH":
        return "BTC", ""
    return "BTC", "ETH"


def primary_return(row: dict, horizon: str) -> float:
    bench = row.get("benchmark_primary", "")
    if bench == "BTC":
        return safe_float(row.get(f"btc_return_{horizon}"))
    if bench == "ETH":
        return safe_float(row.get(f"eth_return_{horizon}"))
    return math.nan


def secondary_return(row: dict, horizon: str) -> float:
    bench = row.get("benchmark_secondary", "")
    if bench == "BTC":
        return safe_float(row.get(f"btc_return_{horizon}"))
    if bench == "ETH":
        return safe_float(row.get(f"eth_return_{horizon}"))
    return math.nan


def priced_in_flags(pre_1h: float, pre_4h: float) -> tuple[str, str]:
    flags = []
    if not math.isnan(pre_1h):
        if abs(pre_1h) >= 0.05:
            flags.append("hard_pre_1h")
        elif abs(pre_1h) >= 0.02:
            flags.append("soft_pre_1h")
    if not math.isnan(pre_4h):
        if abs(pre_4h) >= 0.08:
            flags.append("hard_pre_4h")
        elif abs(pre_4h) >= 0.04:
            flags.append("soft_pre_4h")
    if any(flag.startswith("hard") for flag in flags):
        return "hard", ",".join(flags)
    if flags:
        return "soft", ",".join(flags)
    return "none", ""


def evaluate_alert(alert: dict, args: argparse.Namespace, now_utc: datetime) -> dict:
    asset = str(alert.get("asset_symbol") or "").upper().strip()
    published_at = parse_utc(alert.get("published_at_utc", ""))
    base = {column: "" for column in OUTCOME_COLUMNS}
    base.update(
        {
            "alert_id": alert.get("alert_id", ""),
            "evaluated_at_china": china_stamp(),
            "published_at_china": alert.get("published_at_china", ""),
            "published_at_utc": alert.get("published_at_utc", ""),
            "asset_symbol": asset,
            "event_type": alert.get("event_type", ""),
            "event_subtype": alert.get("event_subtype", ""),
            "source_type": alert.get("source_type", ""),
        }
    )
    if not asset or asset in {"USDT", "USDC", "DAI"}:
        base.update({"quality_status": "skipped", "skip_reason": "stablecoin_or_missing_asset"})
        return base
    if not published_at:
        base.update({"quality_status": "skipped", "skip_reason": "missing_published_at_utc"})
        return base

    primary, secondary = choose_benchmarks(asset)
    base["benchmark_primary"] = primary
    base["benchmark_secondary"] = secondary

    price_t0, market_type, symbol = fetch_close_any(asset, published_at, args)
    if math.isnan(price_t0):
        base.update({"quality_status": "skipped", "skip_reason": "unsupported_symbol", "symbol_used": symbol})
        return base
    base["price_t0"] = fmt(price_t0)
    base["market_type_used"] = market_type
    base["symbol_used"] = symbol

    price_pre_1h, _, _ = fetch_close_any(asset, published_at - timedelta(hours=1), args)
    price_pre_4h, _, _ = fetch_close_any(asset, published_at - timedelta(hours=4), args)
    pre_1h = pct_return(price_pre_1h, price_t0)
    pre_4h = pct_return(price_pre_4h, price_t0)
    base["price_pre_1h"] = fmt(price_pre_1h)
    base["price_pre_4h"] = fmt(price_pre_4h)
    base["pre_return_1h"] = fmt(pre_1h)
    base["pre_return_4h"] = fmt(pre_4h)
    priced_flag, priced_reason = priced_in_flags(pre_1h, pre_4h)
    base["priced_in_flag"] = priced_flag
    base["priced_in_reason"] = priced_reason

    btc_t0, _, _ = fetch_close_any("BTC", published_at, args)
    eth_t0, _, _ = fetch_close_any("ETH", published_at, args)
    base["btc_price_t0"] = fmt(btc_t0)
    base["eth_price_t0"] = fmt(eth_t0)
    base.update(btc_regime(published_at, btc_t0, args))

    evaluated = []
    pending = []
    for label, hours in HORIZONS:
        target = published_at + timedelta(hours=hours)
        if now_utc < target:
            pending.append(label)
            continue
        asset_px, _, _ = fetch_close_any(asset, target, args)
        btc_px, _, _ = fetch_close_any("BTC", target, args)
        eth_px, _, _ = fetch_close_any("ETH", target, args)
        asset_ret = pct_return(price_t0, asset_px)
        btc_ret = pct_return(btc_t0, btc_px)
        eth_ret = pct_return(eth_t0, eth_px)
        base[f"asset_return_{label}"] = fmt(asset_ret)
        base[f"btc_return_{label}"] = fmt(btc_ret)
        base[f"eth_return_{label}"] = fmt(eth_ret)
        p_ret = btc_ret if primary == "BTC" else eth_ret if primary == "ETH" else math.nan
        s_ret = btc_ret if secondary == "BTC" else eth_ret if secondary == "ETH" else math.nan
        base[f"abnormal_primary_{label}"] = fmt(asset_ret - p_ret if not math.isnan(asset_ret) and not math.isnan(p_ret) else math.nan)
        base[f"abnormal_secondary_{label}"] = fmt(asset_ret - s_ret if not math.isnan(asset_ret) and not math.isnan(s_ret) else math.nan)
        evaluated.append(label)

    base["horizons_evaluated"] = ",".join(evaluated)
    base["horizons_pending"] = ",".join(pending)
    base["quality_status"] = "partial" if pending else "ok"
    base["skip_reason"] = ""
    return base


def main() -> int:
    args = parse_args()
    ledger_rows = read_rows(normalize_path(args.ledger))
    existing_outcomes = {row.get("alert_id", ""): row for row in read_rows(normalize_path(args.output))}
    now_utc = datetime.now(timezone.utc).replace(microsecond=0)
    selected = [
        row
        for row in ledger_rows
        if str(row.get("alert_status") or row.get("send_status") or "").lower() in {"published", "sent"}
    ][-args.limit :]

    output_rows = []
    skipped = 0
    changed = 0
    for alert in selected:
        try:
            outcome = evaluate_alert(alert, args, now_utc)
        except Exception as exc:
            outcome = {column: "" for column in OUTCOME_COLUMNS}
            outcome.update(
                {
                    "alert_id": alert.get("alert_id", ""),
                    "evaluated_at_china": china_stamp(),
                    "published_at_china": alert.get("published_at_china", ""),
                    "published_at_utc": alert.get("published_at_utc", ""),
                    "asset_symbol": alert.get("asset_symbol", ""),
                    "event_type": alert.get("event_type", ""),
                    "event_subtype": alert.get("event_subtype", ""),
                    "source_type": alert.get("source_type", ""),
                    "quality_status": "error",
                    "skip_reason": str(exc)[:220],
                }
            )
        if outcome.get("quality_status") in {"skipped", "error"}:
            skipped += 1
        previous = existing_outcomes.get(outcome.get("alert_id", ""))
        if json.dumps(previous or {}, sort_keys=True, ensure_ascii=False) != json.dumps(outcome, sort_keys=True, ensure_ascii=False):
            changed += 1
        output_rows.append(outcome)

    write_rows(normalize_path(args.output), output_rows, OUTCOME_COLUMNS)
    summary = {
        "status": "pass",
        "evaluated_at_china": china_stamp(),
        "ledger_rows": str(len(ledger_rows)),
        "outcome_rows": str(len(output_rows)),
        "new_or_updated_rows": str(changed),
        "evaluable_alerts": str(len(output_rows) - skipped),
        "skipped_alerts": str(skipped),
        "output": str(normalize_path(args.output)),
    }
    write_rows(normalize_path(args.summary), [summary], SUMMARY_COLUMNS)
    print(f"evaluated {len(output_rows)} TG alerts; skipped={skipped}; changed={changed}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
