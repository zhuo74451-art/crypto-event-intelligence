import argparse
import os
from datetime import timedelta
from pathlib import Path

try:
    from utils.watcher_utils import (
        ALERT_COLUMNS,
        address_key,
        compact_number,
        dt_to_utc_iso,
        ensure_parent,
        estimate_usd,
        epoch_to_utc_iso,
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
        safe_int,
        sample_transfer_alerts,
        token_amount,
        utc_iso_to_china,
        write_csv_rows,
        write_summary,
    )
except ModuleNotFoundError:
    from scripts.utils.watcher_utils import (
        ALERT_COLUMNS,
        address_key,
        compact_number,
        dt_to_utc_iso,
        ensure_parent,
        estimate_usd,
        epoch_to_utc_iso,
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
        safe_int,
        sample_transfer_alerts,
        token_amount,
        utc_iso_to_china,
        write_csv_rows,
        write_summary,
    )


ROOT = Path(__file__).resolve().parents[1]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Watch curated Ethereum addresses for large ERC20 transfers.")
    parser.add_argument("--watchlist", default=str(ROOT / "data" / "watchlist_addresses.csv"))
    parser.add_argument("--symbol-map", default=str(ROOT / "data" / "symbol_map.csv"))
    parser.add_argument("--output", default=str(ROOT / "data" / "watcher_alerts_address_transfers.csv"))
    parser.add_argument("--summary", default=str(ROOT / "results" / "v07_address_transfer_watcher_summary.csv"))
    parser.add_argument("--hours", type=float, default=24)
    parser.add_argument("--limit-addresses", type=int, default=25)
    parser.add_argument("--max-transfers-per-address", type=int, default=100)
    parser.add_argument("--chain-id", default="1")
    parser.add_argument("--api-key-env", default="ETHERSCAN_API_KEY")
    parser.add_argument("--sample-if-no-key", default="true")
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def truthy(value: str) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes", "y"}


def classify_transfer(row: dict, watch_item: dict, watch_map: dict[str, dict], amount_usd: float) -> tuple[str, str, str, str, str, str]:
    watched = address_key(watch_item.get("address"))
    from_address = address_key(row.get("from"))
    to_address = address_key(row.get("to"))
    category = str(watch_item.get("category", "")).strip()

    if from_address == watched:
        direction = "transfer_out"
        counterparty = to_address
    else:
        direction = "transfer_in"
        counterparty = from_address

    event_type_l1 = "onchain_transfer"
    if category == "stablecoin_issuer":
        event_type_l1 = "stablecoin_flow"
        event_type_l2 = f"stablecoin_treasury_{'inflow' if direction == 'transfer_in' else 'outflow'}"
        metric_type = f"stablecoin_treasury_{'in' if direction == 'transfer_in' else 'out'}"
        risk_category = "supply_change"
    elif category == "protocol_treasury" and direction == "transfer_out":
        event_type_l2 = "protocol_treasury_outflow"
        metric_type = "treasury_transfer_out"
        risk_category = "protocol_treasury"
    elif category == "cex_hot":
        event_type_l2 = "cex_wallet_flow"
        metric_type = f"cex_{direction}"
        risk_category = "cex_flow"
    elif category == "bridge":
        event_type_l2 = "bridge_flow"
        metric_type = f"bridge_{direction}"
        risk_category = "bridge_flow"
    elif category == "staking":
        event_type_l2 = "staking_flow"
        metric_type = f"staking_{direction}"
        risk_category = "staking"
    else:
        event_type_l2 = "watched_address_transfer"
        metric_type = direction
        risk_category = "whale_movement"

    counterparty_entity = watch_map.get(counterparty, {}).get("entity", "unknown")
    needs_review = "true" if amount_usd >= 10_000_000 or category in {"protocol_treasury", "bridge"} else "false"
    review_reason = "large_or_context_sensitive_transfer" if needs_review == "true" else ""
    return event_type_l1, metric_type, event_type_l2, risk_category, str(counterparty_entity or "unknown"), review_reason


def build_alert(row: dict, watch_item: dict, watch_map: dict[str, dict], symbol_map: dict[str, dict]) -> tuple[dict | None, str]:
    watched = address_key(watch_item.get("address"))
    from_address = address_key(row.get("from"))
    to_address = address_key(row.get("to"))
    if watched not in {from_address, to_address}:
        return None, "watched_address_not_in_transfer"

    counterparty = to_address if from_address == watched else from_address
    same_entity = (
        counterparty in watch_map
        and str(watch_map[counterparty].get("entity", "")).strip().lower()
        == str(watch_item.get("entity", "")).strip().lower()
    )
    if same_entity and str(watch_item.get("category", "")).strip() == "cex_hot":
        return None, "same_entity_internal_transfer"

    symbol = str(row.get("tokenSymbol", "")).strip().upper()
    amount_native = token_amount(row.get("value"), row.get("tokenDecimal"))
    amount_usd, price = estimate_usd(symbol, amount_native, symbol_map)
    threshold = safe_float(watch_item.get("alert_threshold_usd"), 1_000_000)
    if amount_usd < threshold:
        return None, "below_threshold"

    observed_utc = row.get("timeStamp")
    observed_iso = dt_to_utc_iso(now_utc())
    if observed_utc:
        observed_iso = epoch_to_utc_iso(observed_utc)

    event_type_l1, metric_type, event_type_l2, risk_category, counterparty_entity, review_reason = classify_transfer(
        row, watch_item, watch_map, amount_usd
    )
    dedupe_key = make_dedupe_key(row.get("hash"), row.get("logIndex"), watched, symbol, metric_type)
    alert = {column: "" for column in ALERT_COLUMNS}
    alert.update(
        {
            "alert_id": make_alert_id("eth_address_transfer", row.get("hash"), row.get("logIndex"), watched, symbol),
            "observed_at_utc": observed_iso,
            "observed_at_china": utc_iso_to_china(observed_iso),
            "source_type": "first_hand",
            "watcher_source": "etherscan_v2_account_tokentx",
            "blockchain": "ethereum",
            "block_number": row.get("blockNumber", ""),
            "tx_hash": row.get("hash", ""),
            "log_index": row.get("logIndex", ""),
            "primary_entity": watch_item.get("entity", ""),
            "primary_address": watch_item.get("address", ""),
            "counterparty_entity": counterparty_entity,
            "counterparty_address": counterparty,
            "asset_symbol": symbol,
            "token_address": row.get("contractAddress", ""),
            "amount_native": f"{amount_native:.12g}",
            "amount_usd": f"{amount_usd:.2f}",
            "metric_type": metric_type,
            "metric_value": f"{amount_usd:.2f}",
            "metric_change_pct": "",
            "event_type_l1": event_type_l1,
            "event_type_l2": event_type_l2,
            "risk_category": risk_category,
            "confidence": watch_item.get("label_confidence", "medium"),
            "relevance_score": "0.85" if amount_usd >= 10_000_000 else "0.72",
            "threshold_rule": f"amount_usd>={threshold:.0f};price={price:.8g}",
            "dedupe_key": dedupe_key,
            "needs_model_review": "true" if review_reason else "false",
            "model_review_reason": review_reason,
            "publish_route": "review",
            "status": "ok",
            "skip_reason": "",
            "raw_json": json_dumps(row),
        }
    )
    return alert, ""


def main() -> int:
    args = parse_args()
    watchlist_path = normalize_path(args.watchlist)
    output_path = normalize_path(args.output)
    summary_path = normalize_path(args.summary)
    symbol_map = load_symbol_map(normalize_path(args.symbol_map))
    api_key = os.environ.get(args.api_key_env, "").strip()

    if not api_key and truthy(args.sample_if_no_key):
        rows = sample_transfer_alerts()
        write_csv_rows(output_path, rows, ALERT_COLUMNS)
        write_summary(
            summary_path,
            {
                "watcher": "eth_address_transfers",
                "mode": "sample_no_api_key",
                "watchlist_rows": 0,
                "queried_addresses": 0,
                "raw_transfer_rows": 0,
                "alert_rows": len(rows),
                "skipped_rows": 0,
                "status": "sample",
                "message": f"{args.api_key_env} missing; wrote sample alerts for pipeline validation",
            },
        )
        print(f"{args.api_key_env} missing; wrote sample alerts to {output_path}")
        return 0

    if not api_key:
        write_csv_rows(output_path, [], ALERT_COLUMNS)
        write_summary(
            summary_path,
            {
                "watcher": "eth_address_transfers",
                "mode": "live",
                "watchlist_rows": 0,
                "queried_addresses": 0,
                "raw_transfer_rows": 0,
                "alert_rows": 0,
                "skipped_rows": 0,
                "status": "missing_api_key",
                "message": f"Set {args.api_key_env} in the current terminal to query Etherscan.",
            },
        )
        print(f"{args.api_key_env} missing; no live request sent")
        return 0

    watch_rows = [
        row
        for row in read_csv_rows(watchlist_path)
        if is_enabled(row) and str(row.get("blockchain", "")).strip().lower() == "ethereum"
    ][: args.limit_addresses]
    watch_map = {address_key(row.get("address")): row for row in watch_rows}
    since_ts = int((now_utc() - timedelta(hours=args.hours)).timestamp())

    alerts = []
    seen = set()
    raw_count = 0
    skipped_count = 0
    skip_reasons: dict[str, int] = {}

    for index, watch_item in enumerate(watch_rows, start=1):
        address = str(watch_item.get("address", "")).strip()
        print(f"[{index}/{len(watch_rows)}] query address={address} label={watch_item.get('label', '')}")
        try:
            transfers = etherscan_token_transfers(
                address=address,
                api_key=api_key,
                chain_id=args.chain_id,
                offset=args.max_transfers_per_address,
            )
        except Exception as exc:
            skipped_count += 1
            skip_reasons["request_failed"] = skip_reasons.get("request_failed", 0) + 1
            print(f"  request_failed={redact_secret(exc)}")
            continue
        for transfer in transfers:
            raw_count += 1
            if safe_int(transfer.get("timeStamp")) < since_ts:
                continue
            alert, reason = build_alert(transfer, watch_item, watch_map, symbol_map)
            if reason:
                skipped_count += 1
                skip_reasons[reason] = skip_reasons.get(reason, 0) + 1
                continue
            if not alert:
                continue
            if alert["dedupe_key"] in seen:
                skipped_count += 1
                skip_reasons["duplicate"] = skip_reasons.get("duplicate", 0) + 1
                continue
            seen.add(alert["dedupe_key"])
            alerts.append(alert)
            print(
                f"  alert {alert['asset_symbol']} {compact_number(safe_float(alert['amount_usd']))} {alert['metric_type']}"
            )

    if not args.dry_run:
        write_csv_rows(output_path, alerts, ALERT_COLUMNS)
    top_skip_reason = max(skip_reasons, key=skip_reasons.get) if skip_reasons else ""
    write_summary(
        summary_path,
        {
            "watcher": "eth_address_transfers",
            "mode": "live",
            "watchlist_rows": len(watch_rows),
            "queried_addresses": len(watch_rows),
            "raw_transfer_rows": raw_count,
            "alert_rows": len(alerts),
            "skipped_rows": skipped_count,
            "top_skip_reason": top_skip_reason,
            "top_skip_count": skip_reasons.get(top_skip_reason, 0) if top_skip_reason else 0,
            "status": "pass",
            "message": "ok",
        },
    )
    print(f"alert_rows={len(alerts)}")
    print(f"wrote_output={output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
