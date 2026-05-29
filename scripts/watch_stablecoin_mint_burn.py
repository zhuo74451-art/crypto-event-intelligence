import argparse
import os
from datetime import timedelta
from pathlib import Path

try:
    from utils.watcher_utils import (
        ALERT_COLUMNS,
        ZERO_ADDRESS,
        address_key,
        compact_number,
        etherscan_token_transfers,
        epoch_to_utc_iso,
        is_enabled,
        json_dumps,
        make_alert_id,
        make_dedupe_key,
        normalize_path,
        now_utc,
        read_csv_rows,
        redact_secret,
        safe_float,
        safe_int,
        sample_stablecoin_alerts,
        token_amount,
        utc_iso_to_china,
        write_csv_rows,
        write_summary,
    )
except ModuleNotFoundError:
    from scripts.utils.watcher_utils import (
        ALERT_COLUMNS,
        ZERO_ADDRESS,
        address_key,
        compact_number,
        etherscan_token_transfers,
        epoch_to_utc_iso,
        is_enabled,
        json_dumps,
        make_alert_id,
        make_dedupe_key,
        normalize_path,
        now_utc,
        read_csv_rows,
        redact_secret,
        safe_float,
        safe_int,
        sample_stablecoin_alerts,
        token_amount,
        utc_iso_to_china,
        write_csv_rows,
        write_summary,
    )


ROOT = Path(__file__).resolve().parents[1]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Watch USDT/USDC treasury mint/burn flows on Ethereum.")
    parser.add_argument("--watchlist", default=str(ROOT / "data" / "stablecoin_watchlist.csv"))
    parser.add_argument("--output", default=str(ROOT / "data" / "watcher_alerts_stablecoin_mint_burn.csv"))
    parser.add_argument("--summary", default=str(ROOT / "results" / "v07_stablecoin_watcher_summary.csv"))
    parser.add_argument("--hours", type=float, default=24)
    parser.add_argument("--max-transfers-per-token", type=int, default=100)
    parser.add_argument("--chain-id", default="1")
    parser.add_argument("--api-key-env", default="ETHERSCAN_API_KEY")
    parser.add_argument("--sample-if-no-key", default="true")
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def truthy(value: str) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes", "y"}


def classify_stablecoin_transfer(row: dict, item: dict) -> tuple[str, float, str]:
    from_address = address_key(row.get("from"))
    to_address = address_key(row.get("to"))
    amount = token_amount(row.get("value"), row.get("tokenDecimal") or item.get("decimals"))
    if from_address == ZERO_ADDRESS.lower():
        return "stablecoin_mint", amount, "mint"
    if to_address == ZERO_ADDRESS.lower():
        return "stablecoin_burn", amount, "burn"
    return "", amount, ""


def build_alert(row: dict, item: dict) -> tuple[dict | None, str]:
    token_address = address_key(item.get("token_address"))
    row_token = address_key(row.get("contractAddress"))
    if token_address and row_token and token_address != row_token:
        return None, "wrong_token_contract"

    metric_type, amount_native, side = classify_stablecoin_transfer(row, item)
    if not metric_type:
        return None, "not_mint_or_burn"
    amount_usd = amount_native
    threshold = safe_float(item.get("mint_threshold_usd") if side == "mint" else item.get("burn_threshold_usd"))
    if amount_usd < threshold:
        return None, "below_threshold"

    observed_iso = epoch_to_utc_iso(row.get("timeStamp"))
    symbol = str(item.get("token_symbol") or row.get("tokenSymbol", "")).strip().upper()
    dedupe_key = make_dedupe_key(row.get("hash"), row.get("logIndex"), symbol, metric_type)
    alert = {column: "" for column in ALERT_COLUMNS}
    alert.update(
        {
            "alert_id": make_alert_id("stablecoin_mint_burn", row.get("hash"), row.get("logIndex"), symbol, metric_type),
            "observed_at_utc": observed_iso,
            "observed_at_china": utc_iso_to_china(observed_iso),
            "source_type": "first_hand",
            "watcher_source": "etherscan_v2_stablecoin_treasury_tokentx",
            "blockchain": "ethereum",
            "block_number": row.get("blockNumber", ""),
            "tx_hash": row.get("hash", ""),
            "log_index": row.get("logIndex", ""),
            "primary_entity": item.get("issuer_label", ""),
            "primary_address": item.get("treasury_address", ""),
            "counterparty_entity": "zero_address",
            "counterparty_address": ZERO_ADDRESS,
            "asset_symbol": symbol,
            "token_address": item.get("token_address", ""),
            "amount_native": f"{amount_native:.12g}",
            "amount_usd": f"{amount_usd:.2f}",
            "metric_type": metric_type,
            "metric_value": f"{amount_usd:.2f}",
            "metric_change_pct": "",
            "event_type_l1": "stablecoin_flow",
            "event_type_l2": metric_type,
            "risk_category": "supply_change",
            "confidence": item.get("label_confidence", "medium"),
            "relevance_score": "0.90",
            "threshold_rule": f"{side}_usd>={threshold:.0f}",
            "dedupe_key": dedupe_key,
            "needs_model_review": "false",
            "model_review_reason": "",
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
    api_key = os.environ.get(args.api_key_env, "").strip()

    if not api_key and truthy(args.sample_if_no_key):
        rows = sample_stablecoin_alerts()
        write_csv_rows(output_path, rows, ALERT_COLUMNS)
        write_summary(
            summary_path,
            {
                "watcher": "stablecoin_mint_burn",
                "mode": "sample_no_api_key",
                "watchlist_rows": 0,
                "queried_tokens": 0,
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
                "watcher": "stablecoin_mint_burn",
                "mode": "live",
                "watchlist_rows": 0,
                "queried_tokens": 0,
                "raw_transfer_rows": 0,
                "alert_rows": 0,
                "skipped_rows": 0,
                "status": "missing_api_key",
                "message": f"Set {args.api_key_env} in the current terminal to query Etherscan.",
            },
        )
        print(f"{args.api_key_env} missing; no live request sent")
        return 0

    watch_rows = [row for row in read_csv_rows(watchlist_path) if is_enabled(row)]
    since_ts = int((now_utc() - timedelta(hours=args.hours)).timestamp())
    alerts = []
    seen = set()
    raw_count = 0
    skipped_count = 0
    skip_reasons: dict[str, int] = {}

    for index, item in enumerate(watch_rows, start=1):
        treasury = str(item.get("treasury_address", "")).strip()
        print(f"[{index}/{len(watch_rows)}] query stablecoin={item.get('token_symbol')} treasury={treasury}")
        try:
            transfers = etherscan_token_transfers(
                address=treasury,
                api_key=api_key,
                chain_id=args.chain_id,
                offset=args.max_transfers_per_token,
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
            alert, reason = build_alert(transfer, item)
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
            print(f"  alert {alert['asset_symbol']} {compact_number(safe_float(alert['amount_usd']))} {alert['metric_type']}")

    if not args.dry_run:
        write_csv_rows(output_path, alerts, ALERT_COLUMNS)
    top_skip_reason = max(skip_reasons, key=skip_reasons.get) if skip_reasons else ""
    write_summary(
        summary_path,
        {
            "watcher": "stablecoin_mint_burn",
            "mode": "live",
            "watchlist_rows": len(watch_rows),
            "queried_tokens": len(watch_rows),
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
