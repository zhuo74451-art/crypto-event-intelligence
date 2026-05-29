import argparse
import os
from datetime import timedelta
from pathlib import Path

try:
    from utils.watcher_utils import (
        ALERT_COLUMNS,
        address_key,
        dt_to_utc_iso,
        estimate_usd,
        etherscan_token_transfers,
        is_enabled,
        json_dumps,
        load_symbol_map,
        make_alert_id,
        make_dedupe_key,
        normalize_path,
        now_utc,
        read_csv_rows,
        redact_secret,
        safe_float,
        token_amount,
        utc_iso_to_china,
        write_csv_rows,
        write_summary,
    )
except ModuleNotFoundError:
    from scripts.utils.watcher_utils import (
        ALERT_COLUMNS,
        address_key,
        dt_to_utc_iso,
        estimate_usd,
        etherscan_token_transfers,
        is_enabled,
        json_dumps,
        load_symbol_map,
        make_alert_id,
        make_dedupe_key,
        normalize_path,
        now_utc,
        read_csv_rows,
        redact_secret,
        safe_float,
        token_amount,
        utc_iso_to_china,
        write_csv_rows,
        write_summary,
    )


ROOT = Path(__file__).resolve().parents[1]

BASELINE_COLUMNS = [
    "observed_at_utc",
    "observed_at_china",
    "entity",
    "asset_symbol",
    "window_hours",
    "inflow_usd",
    "outflow_usd",
    "net_usd",
    "gross_usd",
    "tx_count",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Aggregate CEX watched-wallet ERC20 transfers into net-flow alerts.")
    parser.add_argument("--watchlist", default=str(ROOT / "data" / "watchlist_addresses.csv"))
    parser.add_argument("--symbol-map", default=str(ROOT / "data" / "symbol_map.csv"))
    parser.add_argument("--output", default=str(ROOT / "data" / "watcher_alerts_cex_netflows.csv"))
    parser.add_argument("--summary", default=str(ROOT / "results" / "v08_cex_netflow_watcher_summary.csv"))
    parser.add_argument("--hours", type=float, default=4)
    parser.add_argument("--window-hours", type=float, default=4)
    parser.add_argument("--min-net-usd", type=float, default=20_000_000)
    parser.add_argument("--min-gross-usd", type=float, default=50_000_000)
    parser.add_argument("--baseline-state", default=str(ROOT / "data" / "cex_netflow_baseline_state.csv"))
    parser.add_argument("--baseline-lookback", type=int, default=72)
    parser.add_argument("--baseline-multiple", type=float, default=3.0)
    parser.add_argument("--limit-addresses", type=int, default=25)
    parser.add_argument("--max-transfers-per-address", type=int, default=100)
    parser.add_argument("--chain-id", default="1")
    parser.add_argument("--api-key-env", default="ETHERSCAN_API_KEY")
    parser.add_argument("--sample-if-no-key", default="true")
    return parser.parse_args()


def truthy(value: str) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes", "y"}


def sample_alerts(window_hours: float) -> list[dict]:
    observed = dt_to_utc_iso(now_utc())
    alert = {column: "" for column in ALERT_COLUMNS}
    alert.update(
        {
            "alert_id": make_alert_id("cex_netflow_sample", observed, "Binance", "USDT"),
            "observed_at_utc": observed,
            "observed_at_china": utc_iso_to_china(observed),
            "source_type": "first_hand",
            "watcher_source": "etherscan_v2_cex_netflow",
            "blockchain": "ethereum",
            "primary_entity": "Binance",
            "primary_address": "multiple_cex_hot_wallets",
            "counterparty_entity": "aggregated_external_wallets",
            "counterparty_address": "aggregated",
            "asset_symbol": "USDT",
            "amount_native": "65000000",
            "amount_usd": "65000000.00",
            "metric_type": "cex_netflow_in",
            "metric_value": "65000000.00",
            "metric_change_pct": "",
            "event_type_l1": "cex_netflow",
            "event_type_l2": "cex_net_inflow",
            "risk_category": "market_structure",
            "confidence": "sample",
            "relevance_score": "0.86",
            "threshold_rule": f"sample_net_usd>=20000000;window_hours={window_hours}",
            "dedupe_key": make_dedupe_key("cex_netflow_sample", "Binance", "USDT", observed[:13]),
            "needs_model_review": "false",
            "model_review_reason": "",
            "publish_route": "review",
            "status": "sample",
            "raw_json": json_dumps({"sample": True, "window_hours": window_hours}),
        }
    )
    return [alert]


def normalize_symbol(symbol: str) -> str:
    return str(symbol or "").strip().upper()


def load_baseline(path: Path) -> list[dict]:
    return read_csv_rows(path)


def baseline_stats(rows: list[dict], entity: str, symbol: str, lookback: int) -> dict:
    matched = [
        row
        for row in rows
        if str(row.get("entity", "")) == entity and normalize_symbol(row.get("asset_symbol", "")) == symbol
    ][-max(1, lookback) :]
    if not matched:
        return {"samples": 0, "avg_abs_net_usd": 0.0, "avg_gross_usd": 0.0}
    avg_abs_net = sum(abs(safe_float(row.get("net_usd"))) for row in matched) / len(matched)
    avg_gross = sum(safe_float(row.get("gross_usd")) for row in matched) / len(matched)
    return {"samples": len(matched), "avg_abs_net_usd": avg_abs_net, "avg_gross_usd": avg_gross}


def append_baseline(path: Path, rows: list[dict], max_rows: int = 5000) -> None:
    existing = load_baseline(path)
    existing.extend(rows)
    if len(existing) > max_rows:
        existing = existing[-max_rows:]
    write_csv_rows(path, existing, BASELINE_COLUMNS)


def main() -> int:
    args = parse_args()
    output_path = normalize_path(args.output)
    summary_path = normalize_path(args.summary)
    api_key = os.environ.get(args.api_key_env, "").strip()

    if not api_key and truthy(args.sample_if_no_key):
        rows = sample_alerts(args.window_hours)
        write_csv_rows(output_path, rows, ALERT_COLUMNS)
        write_summary(
            summary_path,
            {
                "watcher": "cex_netflows",
                "mode": "sample_no_api_key",
                "cex_watch_addresses": 0,
                "raw_transfer_rows": 0,
                "alert_rows": len(rows),
                "status": "sample",
            },
        )
        print(f"{args.api_key_env} missing; wrote sample CEX netflow alerts to {output_path}")
        return 0

    if not api_key:
        write_csv_rows(output_path, [], ALERT_COLUMNS)
        write_summary(
            summary_path,
            {
                "watcher": "cex_netflows",
                "mode": "live",
                "cex_watch_addresses": 0,
                "raw_transfer_rows": 0,
                "alert_rows": 0,
                "status": "missing_api_key",
            },
        )
        print(f"{args.api_key_env} missing; no live CEX netflow request sent")
        return 0

    watch_rows = [
        row
        for row in read_csv_rows(normalize_path(args.watchlist))
        if is_enabled(row)
        and str(row.get("blockchain", "")).strip().lower() == "ethereum"
        and str(row.get("category", "")).strip() == "cex_hot"
    ][: args.limit_addresses]
    symbol_map = load_symbol_map(normalize_path(args.symbol_map))
    baseline_path = normalize_path(args.baseline_state)
    baseline_rows = load_baseline(baseline_path)
    since_ts = int((now_utc() - timedelta(hours=args.hours)).timestamp())
    window_label = f"{int(args.window_hours)}h" if float(args.window_hours).is_integer() else f"{args.window_hours:g}h"

    buckets: dict[tuple[str, str], dict] = {}
    raw_count = 0
    request_failed = 0

    for index, watch_item in enumerate(watch_rows, start=1):
        address = str(watch_item.get("address", "")).strip()
        entity = str(watch_item.get("entity", "") or watch_item.get("label", "")).strip()
        print(f"[{index}/{len(watch_rows)}] aggregate cex address={address} entity={entity}")
        try:
            transfers = etherscan_token_transfers(
                address=address,
                api_key=api_key,
                chain_id=args.chain_id,
                offset=args.max_transfers_per_address,
            )
        except Exception as exc:
            request_failed += 1
            print(f"  request_failed={redact_secret(exc)}")
            continue

        watched = address_key(address)
        for transfer in transfers:
            try:
                if int(str(transfer.get("timeStamp", "0"))) < since_ts:
                    continue
            except Exception:
                continue
            symbol = normalize_symbol(transfer.get("tokenSymbol", ""))
            if not symbol:
                continue
            amount_native = token_amount(transfer.get("value"), transfer.get("tokenDecimal"))
            amount_usd, _price = estimate_usd(symbol, amount_native, symbol_map)
            if amount_usd <= 0:
                continue
            raw_count += 1
            from_address = address_key(transfer.get("from"))
            to_address = address_key(transfer.get("to"))
            key = (entity, symbol)
            bucket = buckets.setdefault(
                key,
                {
                    "entity": entity,
                    "symbol": symbol,
                    "inflow_usd": 0.0,
                    "outflow_usd": 0.0,
                    "inflow_native": 0.0,
                    "outflow_native": 0.0,
                    "tx_count": 0,
                    "addresses": set(),
                    "last_ts": 0,
                    "last_tx": "",
                },
            )
            bucket["tx_count"] += 1
            bucket["addresses"].add(address)
            ts = int(str(transfer.get("timeStamp", "0") or "0"))
            if ts >= bucket["last_ts"]:
                bucket["last_ts"] = ts
                bucket["last_tx"] = str(transfer.get("hash", "") or "")
            if to_address == watched:
                bucket["inflow_usd"] += amount_usd
                bucket["inflow_native"] += amount_native
            elif from_address == watched:
                bucket["outflow_usd"] += amount_usd
                bucket["outflow_native"] += amount_native

    observed = dt_to_utc_iso(now_utc())
    baseline_append_rows = []
    enriched_buckets = []
    for (entity, symbol), bucket in buckets.items():
        inflow = float(bucket["inflow_usd"])
        outflow = float(bucket["outflow_usd"])
        net = inflow - outflow
        gross = inflow + outflow
        base = baseline_stats(baseline_rows, entity, symbol, args.baseline_lookback)
        baseline_abs_net = float(base["avg_abs_net_usd"])
        baseline_gross = float(base["avg_gross_usd"])
        abnormal_multiple = abs(net) / baseline_abs_net if baseline_abs_net > 0 else 0.0
        gross_multiple = gross / baseline_gross if baseline_gross > 0 else 0.0
        enriched_buckets.append(
            {
                "key": (entity, symbol),
                "bucket": bucket,
                "inflow": inflow,
                "outflow": outflow,
                "net": net,
                "gross": gross,
                "baseline_samples": int(base["samples"]),
                "baseline_abs_net": baseline_abs_net,
                "baseline_gross": baseline_gross,
                "abnormal_multiple": abnormal_multiple,
                "gross_multiple": gross_multiple,
            }
        )
        baseline_append_rows.append(
            {
                "observed_at_utc": observed,
                "observed_at_china": utc_iso_to_china(observed),
                "entity": entity,
                "asset_symbol": symbol,
                "window_hours": args.window_hours,
                "inflow_usd": f"{inflow:.2f}",
                "outflow_usd": f"{outflow:.2f}",
                "net_usd": f"{net:.2f}",
                "gross_usd": f"{gross:.2f}",
                "tx_count": bucket["tx_count"],
            }
        )

    alerts = []
    baseline_alert_rows = 0
    for item in sorted(enriched_buckets, key=lambda item: abs(item["net"]), reverse=True):
        entity, symbol = item["key"]
        bucket = item["bucket"]
        inflow = item["inflow"]
        outflow = item["outflow"]
        net = item["net"]
        gross = item["gross"]
        absolute_gate = abs(net) >= args.min_net_usd and gross >= args.min_gross_usd
        baseline_gate = (
            item["baseline_samples"] >= 6
            and abs(net) >= args.min_net_usd * 0.5
            and item["abnormal_multiple"] >= args.baseline_multiple
        )
        if not absolute_gate and not baseline_gate:
            continue
        if baseline_gate and not absolute_gate:
            baseline_alert_rows += 1
        direction = "in" if net > 0 else "out"
        amount_native = bucket["inflow_native"] if net > 0 else bucket["outflow_native"]
        metric_type = f"cex_netflow_{'in' if net > 0 else 'out'}"
        alert = {column: "" for column in ALERT_COLUMNS}
        alert.update(
            {
                "alert_id": make_alert_id("cex_netflow", entity, symbol, window_label, int(abs(net) // 1_000_000)),
                "observed_at_utc": observed,
                "observed_at_china": utc_iso_to_china(observed),
                "source_type": "first_hand",
                "watcher_source": "etherscan_v2_cex_netflow",
                "blockchain": "ethereum",
                "tx_hash": bucket["last_tx"],
                "primary_entity": entity,
                "primary_address": ",".join(sorted(bucket["addresses"])),
                "counterparty_entity": "aggregated_external_wallets",
                "counterparty_address": "aggregated",
                "asset_symbol": symbol,
                "amount_native": f"{amount_native:.12g}",
                "amount_usd": f"{abs(net):.2f}",
                "metric_type": metric_type,
                "metric_value": f"{net:.2f}",
                "metric_change_pct": f"{item['abnormal_multiple']:.6f}" if item["abnormal_multiple"] else "",
                "event_type_l1": "cex_netflow",
                "event_type_l2": f"cex_net_{'inflow' if direction == 'in' else 'outflow'}",
                "risk_category": "market_structure",
                "confidence": "medium",
                "relevance_score": "0.88" if abs(net) >= 50_000_000 else "0.76",
                "threshold_rule": (
                    f"abs_net_usd>={args.min_net_usd:.0f};gross_usd>={args.min_gross_usd:.0f};"
                    f"baseline_multiple>={args.baseline_multiple:.2f};window={window_label};"
                    f"tx_count={bucket['tx_count']};in={inflow:.2f};out={outflow:.2f};"
                    f"baseline_samples={item['baseline_samples']};baseline_abs_net={item['baseline_abs_net']:.2f};"
                    f"abnormal_multiple={item['abnormal_multiple']:.2f};gate={'baseline' if baseline_gate and not absolute_gate else 'absolute'}"
                ),
                "dedupe_key": make_dedupe_key("cex_netflow", entity, symbol, direction, observed[:13]),
                "needs_model_review": "true" if abs(net) >= 50_000_000 else "false",
                "model_review_reason": "large_cex_netflow" if abs(net) >= 50_000_000 else "",
                "publish_route": "review",
                "status": "ok",
                "raw_json": json_dumps(
                    {
                        "window_hours": args.window_hours,
                        "entity": entity,
                        "symbol": symbol,
                        "inflow_usd": inflow,
                        "outflow_usd": outflow,
                        "net_usd": net,
                        "gross_usd": gross,
                        "tx_count": bucket["tx_count"],
                        "baseline_samples": item["baseline_samples"],
                        "baseline_abs_net_usd": item["baseline_abs_net"],
                        "baseline_gross_usd": item["baseline_gross"],
                        "abnormal_multiple": item["abnormal_multiple"],
                        "gross_multiple": item["gross_multiple"],
                        "alert_gate": "baseline" if baseline_gate and not absolute_gate else "absolute",
                    }
                ),
            }
        )
        alerts.append(alert)

    write_csv_rows(output_path, alerts, ALERT_COLUMNS)
    append_baseline(baseline_path, baseline_append_rows)
    write_summary(
        summary_path,
        {
            "watcher": "cex_netflows",
            "mode": "live",
            "window_hours": args.window_hours,
            "cex_watch_addresses": len(watch_rows),
            "raw_transfer_rows": raw_count,
            "bucket_count": len(buckets),
            "alert_rows": len(alerts),
            "baseline_alert_rows": baseline_alert_rows,
            "baseline_state_rows_added": len(baseline_append_rows),
            "baseline_lookback": args.baseline_lookback,
            "baseline_multiple": args.baseline_multiple,
            "request_failed": request_failed,
            "min_net_usd": args.min_net_usd,
            "min_gross_usd": args.min_gross_usd,
            "status": "pass",
        },
    )
    print(f"cex_netflow_alert_rows={len(alerts)}")
    print(f"wrote_output={output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
