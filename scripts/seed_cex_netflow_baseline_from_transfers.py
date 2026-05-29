import argparse
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

try:
    from utils.watcher_utils import (
        address_key,
        dt_to_utc_iso,
        estimate_usd,
        etherscan_token_transfers,
        is_enabled,
        load_symbol_map,
        normalize_path,
        read_csv_rows,
        safe_float,
        token_amount,
        utc_iso_to_china,
        write_csv_rows,
        write_summary,
    )
except ModuleNotFoundError:
    from scripts.utils.watcher_utils import (
        address_key,
        dt_to_utc_iso,
        estimate_usd,
        etherscan_token_transfers,
        is_enabled,
        load_symbol_map,
        normalize_path,
        read_csv_rows,
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
    parser = argparse.ArgumentParser(description="Seed CEX netflow baseline from recent historical Etherscan token transfers.")
    parser.add_argument("--watchlist", default=str(ROOT / "data" / "watchlist_addresses.csv"))
    parser.add_argument("--symbol-map", default=str(ROOT / "data" / "symbol_map.csv"))
    parser.add_argument("--output", default=str(ROOT / "data" / "cex_netflow_baseline_state.csv"))
    parser.add_argument("--summary", default=str(ROOT / "results" / "v08_cex_netflow_baseline_seed_summary.csv"))
    parser.add_argument("--hours", type=float, default=168)
    parser.add_argument("--bucket-hours", type=float, default=4)
    parser.add_argument("--limit-addresses", type=int, default=25)
    parser.add_argument("--max-transfers-per-address", type=int, default=1000)
    parser.add_argument("--chain-id", default="1")
    parser.add_argument("--api-key-env", default="ETHERSCAN_API_KEY")
    parser.add_argument("--merge-existing", default="true")
    return parser.parse_args()


def truthy(value: str) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "y"}


def floor_bucket(dt: datetime, bucket_hours: float) -> datetime:
    bucket_seconds = int(bucket_hours * 3600)
    ts = int(dt.timestamp())
    return datetime.fromtimestamp(ts - ts % bucket_seconds, timezone.utc)


def transfer_dt(row: dict) -> datetime | None:
    try:
        return datetime.fromtimestamp(int(str(row.get("timeStamp", "0"))), timezone.utc)
    except Exception:
        return None


def normalize_symbol(symbol: str) -> str:
    return str(symbol or "").strip().upper()


def row_key(row: dict) -> tuple:
    return (
        str(row.get("observed_at_utc", "")),
        str(row.get("entity", "")),
        normalize_symbol(row.get("asset_symbol", "")),
        str(row.get("window_hours", "")),
    )


def main() -> int:
    args = parse_args()
    api_key = os.environ.get(args.api_key_env, "").strip()
    output_path = normalize_path(args.output)
    summary_path = normalize_path(args.summary)
    if not api_key:
        write_summary(summary_path, {"status": "missing_api_key", "rows_added": 0})
        print(f"{args.api_key_env} missing; baseline seed skipped")
        return 0

    symbol_map = load_symbol_map(normalize_path(args.symbol_map))
    watch_rows = [
        row
        for row in read_csv_rows(normalize_path(args.watchlist))
        if is_enabled(row)
        and str(row.get("blockchain", "")).strip().lower() == "ethereum"
        and str(row.get("category", "")).strip() == "cex_hot"
    ][: args.limit_addresses]
    since = datetime.now(timezone.utc) - timedelta(hours=args.hours)
    buckets: dict[tuple[str, str, datetime], dict] = {}
    request_failed = 0
    raw_transfer_rows = 0
    used_transfer_rows = 0

    for index, watch_item in enumerate(watch_rows, start=1):
        address = str(watch_item.get("address", "") or "").strip()
        entity = str(watch_item.get("entity", "") or watch_item.get("label", "") or "").strip()
        print(f"[{index}/{len(watch_rows)}] seed cex baseline entity={entity} address={address}")
        try:
            transfers = etherscan_token_transfers(
                address=address,
                api_key=api_key,
                chain_id=args.chain_id,
                offset=args.max_transfers_per_address,
            )
        except Exception as exc:
            request_failed += 1
            print(f"  request_failed={exc}")
            continue
        watched = address_key(address)
        for transfer in transfers:
            raw_transfer_rows += 1
            dt = transfer_dt(transfer)
            if not dt or dt < since:
                continue
            symbol = normalize_symbol(transfer.get("tokenSymbol", ""))
            if not symbol:
                continue
            amount_native = token_amount(transfer.get("value"), transfer.get("tokenDecimal"))
            amount_usd, _price = estimate_usd(symbol, amount_native, symbol_map)
            if amount_usd <= 0:
                continue
            bucket_time = floor_bucket(dt, args.bucket_hours)
            key = (entity, symbol, bucket_time)
            bucket = buckets.setdefault(
                key,
                {
                    "observed_at_utc": dt_to_utc_iso(bucket_time),
                    "observed_at_china": utc_iso_to_china(dt_to_utc_iso(bucket_time)),
                    "entity": entity,
                    "asset_symbol": symbol,
                    "window_hours": args.bucket_hours,
                    "inflow_usd": 0.0,
                    "outflow_usd": 0.0,
                    "tx_count": 0,
                },
            )
            from_address = address_key(transfer.get("from"))
            to_address = address_key(transfer.get("to"))
            if to_address == watched:
                bucket["inflow_usd"] += amount_usd
            elif from_address == watched:
                bucket["outflow_usd"] += amount_usd
            else:
                continue
            bucket["tx_count"] += 1
            used_transfer_rows += 1

    new_rows = []
    for bucket in buckets.values():
        inflow = safe_float(bucket.get("inflow_usd"))
        outflow = safe_float(bucket.get("outflow_usd"))
        gross = inflow + outflow
        if gross <= 0:
            continue
        new_rows.append(
            {
                "observed_at_utc": bucket["observed_at_utc"],
                "observed_at_china": bucket["observed_at_china"],
                "entity": bucket["entity"],
                "asset_symbol": bucket["asset_symbol"],
                "window_hours": bucket["window_hours"],
                "inflow_usd": f"{inflow:.2f}",
                "outflow_usd": f"{outflow:.2f}",
                "net_usd": f"{(inflow - outflow):.2f}",
                "gross_usd": f"{gross:.2f}",
                "tx_count": bucket["tx_count"],
            }
        )
    existing = read_csv_rows(output_path) if truthy(args.merge_existing) else []
    merged = {row_key(row): row for row in existing}
    for row in new_rows:
        merged[row_key(row)] = row
    output_rows = sorted(merged.values(), key=lambda row: (row.get("observed_at_utc", ""), row.get("entity", ""), row.get("asset_symbol", "")))
    write_csv_rows(output_path, output_rows, BASELINE_COLUMNS)
    summary = {
        "status": "pass",
        "watch_addresses": len(watch_rows),
        "raw_transfer_rows": raw_transfer_rows,
        "used_transfer_rows": used_transfer_rows,
        "new_bucket_rows": len(new_rows),
        "output_rows": len(output_rows),
        "request_failed": request_failed,
        "hours": args.hours,
        "bucket_hours": args.bucket_hours,
        "output": str(output_path),
    }
    write_summary(summary_path, summary)
    print(f"new_bucket_rows={len(new_rows)}")
    print(f"output_rows={len(output_rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
