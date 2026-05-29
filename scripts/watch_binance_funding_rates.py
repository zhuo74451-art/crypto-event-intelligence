import argparse
from pathlib import Path

try:
    from utils.watcher_utils import (
        ALERT_COLUMNS,
        dt_to_utc_iso,
        epoch_to_utc_iso,
        is_enabled,
        json_dumps,
        make_alert_id,
        make_dedupe_key,
        normalize_path,
        now_utc,
        read_csv_rows,
        request_json,
        safe_float,
        safe_int,
        utc_iso_to_china,
        write_csv_rows,
        write_summary,
    )
except ModuleNotFoundError:
    from scripts.utils.watcher_utils import (
        ALERT_COLUMNS,
        dt_to_utc_iso,
        epoch_to_utc_iso,
        is_enabled,
        json_dumps,
        make_alert_id,
        make_dedupe_key,
        normalize_path,
        now_utc,
        read_csv_rows,
        request_json,
        safe_float,
        safe_int,
        utc_iso_to_china,
        write_csv_rows,
        write_summary,
    )


ROOT = Path(__file__).resolve().parents[1]
FUNDING_URL = "https://fapi.binance.com/fapi/v1/fundingRate"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Watch Binance USD-M funding-rate anomalies.")
    parser.add_argument("--watchlist", default=str(ROOT / "data" / "funding_watchlist.csv"))
    parser.add_argument("--output", default=str(ROOT / "data" / "watcher_alerts_binance_funding.csv"))
    parser.add_argument("--summary", default=str(ROOT / "results" / "v08_funding_rate_watcher_summary.csv"))
    parser.add_argument("--default-limit", type=int, default=24)
    parser.add_argument("--sample-if-empty", default="true")
    return parser.parse_args()


def truthy(value: str) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes", "y"}


def sample_alerts() -> list[dict]:
    observed = dt_to_utc_iso(now_utc())
    row = {column: "" for column in ALERT_COLUMNS}
    row.update(
        {
            "alert_id": make_alert_id("sample_funding_rate", "BTCUSDT", observed),
            "observed_at_utc": observed,
            "observed_at_china": utc_iso_to_china(observed),
            "source_type": "first_hand",
            "watcher_source": "binance_usdm_funding_rate",
            "blockchain": "binance_usdm",
            "primary_entity": "Binance USD-M",
            "primary_address": "BTCUSDT",
            "counterparty_entity": "perp_market",
            "counterparty_address": "BTCUSDT",
            "asset_symbol": "BTC",
            "amount_native": "0.0012",
            "amount_usd": "0",
            "metric_type": "funding_rate_high_positive",
            "metric_value": "0.0012",
            "metric_change_pct": "0.0008",
            "event_type_l1": "funding_rate",
            "event_type_l2": "binance_usdm_funding_anomaly",
            "risk_category": "market_structure",
            "confidence": "sample",
            "relevance_score": "0.78",
            "threshold_rule": "sample_abs_rate>=0.0005;sample_change>=0.0003",
            "dedupe_key": make_dedupe_key("sample_funding_rate", "BTCUSDT", observed[:13]),
            "needs_model_review": "false",
            "model_review_reason": "",
            "publish_route": "review",
            "status": "sample",
            "raw_json": json_dumps({"sample": True}),
        }
    )
    return [row]


def classify_rate(rate: float) -> str:
    if rate > 0:
        return "funding_rate_high_positive"
    return "funding_rate_high_negative"


def build_alert(item: dict, records: list[dict], observed_iso: str) -> tuple[dict | None, str]:
    if not records:
        return None, "no_funding_records"
    symbol = str(item.get("binance_futures_symbol") or "").strip().upper()
    asset = str(item.get("asset_symbol") or "").strip().upper()
    latest = records[-1]
    latest_rate = safe_float(latest.get("fundingRate"))
    prev_rate = safe_float(records[-2].get("fundingRate")) if len(records) >= 2 else 0.0
    avg_rate = sum(safe_float(row.get("fundingRate")) for row in records) / max(1, len(records))
    change = latest_rate - prev_rate
    abs_threshold = safe_float(item.get("alert_abs_rate_threshold"), 0.0008)
    change_threshold = safe_float(item.get("alert_change_threshold"), 0.0005)

    if abs(latest_rate) < abs_threshold and abs(change) < change_threshold:
        return None, "below_threshold"

    funding_time = latest.get("fundingTime") or ""
    if str(funding_time).isdigit() and len(str(funding_time)) > 10:
        funding_iso = epoch_to_utc_iso(int(int(funding_time) / 1000))
    else:
        funding_iso = epoch_to_utc_iso(funding_time)
    if not funding_iso:
        funding_iso = observed_iso

    metric_type = classify_rate(latest_rate)
    alert = {column: "" for column in ALERT_COLUMNS}
    alert.update(
        {
            "alert_id": make_alert_id("binance_funding", symbol, funding_time, f"{latest_rate:.8f}"),
            "observed_at_utc": funding_iso,
            "observed_at_china": utc_iso_to_china(funding_iso),
            "source_type": "first_hand",
            "watcher_source": "binance_usdm_funding_rate",
            "blockchain": "binance_usdm",
            "primary_entity": "Binance USD-M",
            "primary_address": symbol,
            "counterparty_entity": "perp_market",
            "counterparty_address": symbol,
            "asset_symbol": asset,
            "amount_native": f"{latest_rate:.8f}",
            "amount_usd": f"{abs(latest_rate) * 100_000_000:.2f}",
            "metric_type": metric_type,
            "metric_value": f"{latest_rate:.8f}",
            "metric_change_pct": f"{change:.8f}",
            "event_type_l1": "funding_rate",
            "event_type_l2": "binance_usdm_funding_anomaly",
            "risk_category": "market_structure",
            "confidence": "high" if abs(latest_rate) >= abs_threshold else "medium",
            "relevance_score": "0.86" if abs(latest_rate) >= abs_threshold else "0.74",
            "threshold_rule": f"abs_rate>={abs_threshold:.8f};change>={change_threshold:.8f};latest={latest_rate:.8f};prev={prev_rate:.8f};avg={avg_rate:.8f};records={len(records)}",
            "dedupe_key": make_dedupe_key("binance_funding", symbol, funding_iso[:13], metric_type),
            "needs_model_review": "false",
            "model_review_reason": "",
            "publish_route": "review",
            "status": "ok",
            "raw_json": json_dumps({"latest": latest, "prev_rate": prev_rate, "avg_rate": avg_rate, "records": records[-5:]}),
        }
    )
    return alert, ""


def main() -> int:
    args = parse_args()
    watch_rows = [row for row in read_csv_rows(normalize_path(args.watchlist)) if is_enabled(row)]

    if not watch_rows and truthy(args.sample_if_empty):
        rows = sample_alerts()
        write_csv_rows(normalize_path(args.output), rows, ALERT_COLUMNS)
        write_summary(
            normalize_path(args.summary),
            {
                "watcher": "binance_funding_rates",
                "mode": "sample_empty_watchlist",
                "watchlist_rows": 0,
                "queried_markets": 0,
                "alert_rows": len(rows),
                "status": "sample",
            },
        )
        print(f"empty watchlist; wrote sample funding alerts to {args.output}")
        return 0

    observed_iso = dt_to_utc_iso(now_utc())
    alerts = []
    queried = 0
    skipped = 0
    skip_reasons: dict[str, int] = {}

    for index, item in enumerate(watch_rows, start=1):
        symbol = str(item.get("binance_futures_symbol") or "").strip().upper()
        if not symbol:
            skipped += 1
            skip_reasons["missing_symbol"] = skip_reasons.get("missing_symbol", 0) + 1
            continue
        limit = safe_int(item.get("lookback_limit"), args.default_limit)
        print(f"[{index}/{len(watch_rows)}] funding symbol={symbol}")
        try:
            records = request_json(FUNDING_URL, params={"symbol": symbol, "limit": limit}, timeout=15, retries=3)
        except Exception as exc:
            skipped += 1
            skip_reasons["request_failed"] = skip_reasons.get("request_failed", 0) + 1
            print(f"  request_failed={exc}")
            continue
        queried += 1
        if not isinstance(records, list):
            skipped += 1
            skip_reasons["bad_response"] = skip_reasons.get("bad_response", 0) + 1
            continue
        alert, reason = build_alert(item, records, observed_iso)
        if alert:
            alerts.append(alert)
            print(f"  alert {alert['asset_symbol']} {alert['metric_type']} rate={alert['metric_value']} change={alert['metric_change_pct']}")
        elif reason:
            skipped += 1
            skip_reasons[reason] = skip_reasons.get(reason, 0) + 1

    write_csv_rows(normalize_path(args.output), alerts, ALERT_COLUMNS)
    write_summary(
        normalize_path(args.summary),
        {
            "watcher": "binance_funding_rates",
            "mode": "live",
            "watchlist_rows": len(watch_rows),
            "queried_markets": queried,
            "alert_rows": len(alerts),
            "skipped_rows": skipped,
            "skip_reasons": json_dumps(skip_reasons),
            "status": "pass",
        },
    )
    print(f"funding_alert_rows={len(alerts)}")
    print(f"wrote_output={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
