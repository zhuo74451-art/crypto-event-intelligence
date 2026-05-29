import argparse
from pathlib import Path

try:
    from utils.watcher_utils import (
        dt_to_utc_iso,
        is_enabled,
        json_dumps,
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
        dt_to_utc_iso,
        is_enabled,
        json_dumps,
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
BASE_URL = "https://fapi.binance.com"

SNAPSHOT_COLUMNS = [
    "observed_at_utc",
    "observed_at_china",
    "asset_symbol",
    "binance_futures_symbol",
    "period",
    "top_position_long_short_ratio",
    "top_position_long_account",
    "top_position_short_account",
    "top_account_long_short_ratio",
    "top_account_long_account",
    "top_account_short_account",
    "global_account_long_short_ratio",
    "global_account_long_account",
    "global_account_short_account",
    "taker_buy_sell_ratio",
    "taker_buy_volume",
    "taker_sell_volume",
    "crowding_bias",
    "crowding_score",
    "quality_status",
    "skip_reason",
    "raw_json",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Fetch Binance USD-M public long/short sentiment ratios.")
    parser.add_argument("--watchlist", default=str(ROOT / "data" / "funding_watchlist.csv"))
    parser.add_argument("--output", default=str(ROOT / "data" / "binance_long_short_snapshot.csv"))
    parser.add_argument("--summary", default=str(ROOT / "results" / "v08_binance_long_short_summary.csv"))
    parser.add_argument("--period", default="1h")
    parser.add_argument("--limit", type=int, default=2)
    return parser.parse_args()


def latest_record(endpoint: str, symbol: str, period: str, limit: int) -> dict:
    payload = request_json(
        f"{BASE_URL}{endpoint}",
        params={"symbol": symbol, "period": period, "limit": max(1, limit)},
        timeout=15,
        retries=3,
    )
    if isinstance(payload, list) and payload:
        return payload[-1]
    return {}


def ratio_fields(record: dict) -> tuple[str, str, str]:
    return (
        str(record.get("longShortRatio", "") or "").strip(),
        str(record.get("longAccount", "") or "").strip(),
        str(record.get("shortAccount", "") or "").strip(),
    )


def taker_fields(record: dict) -> tuple[str, str, str]:
    ratio = str(record.get("buySellRatio", "") or "").strip()
    buy = str(record.get("buyVol", "") or record.get("buyVolume", "") or "").strip()
    sell = str(record.get("sellVol", "") or record.get("sellVolume", "") or "").strip()
    return ratio, buy, sell


def crowding(top_position_ratio: float, global_account_ratio: float, taker_ratio: float) -> tuple[str, float]:
    score = 0.0
    if top_position_ratio:
        score += min(35, abs(top_position_ratio - 1.0) * 35)
    if global_account_ratio:
        score += min(25, abs(global_account_ratio - 1.0) * 25)
    if taker_ratio:
        score += min(20, abs(taker_ratio - 1.0) * 20)

    weighted = top_position_ratio or global_account_ratio or taker_ratio
    if weighted >= 1.25:
        bias = "多头拥挤"
    elif weighted <= 0.80 and weighted > 0:
        bias = "空头拥挤"
    else:
        bias = "相对均衡"
    return bias, round(score, 2)


def build_row(item: dict, period: str, limit: int, observed_utc: str) -> dict:
    asset = str(item.get("asset_symbol", "") or "").strip().upper()
    symbol = str(item.get("binance_futures_symbol", "") or "").strip().upper()
    row = {column: "" for column in SNAPSHOT_COLUMNS}
    row.update(
        {
            "observed_at_utc": observed_utc,
            "observed_at_china": utc_iso_to_china(observed_utc),
            "asset_symbol": asset,
            "binance_futures_symbol": symbol,
            "period": period,
        }
    )
    if not symbol:
        row["quality_status"] = "skipped"
        row["skip_reason"] = "missing_futures_symbol"
        return row

    try:
        top_pos = latest_record("/futures/data/topLongShortPositionRatio", symbol, period, limit)
        top_acc = latest_record("/futures/data/topLongShortAccountRatio", symbol, period, limit)
        global_acc = latest_record("/futures/data/globalLongShortAccountRatio", symbol, period, limit)
        taker = latest_record("/futures/data/takerlongshortRatio", symbol, period, limit)
    except Exception as exc:
        row["quality_status"] = "skipped"
        row["skip_reason"] = f"request_failed:{str(exc)[:160]}"
        return row

    (
        row["top_position_long_short_ratio"],
        row["top_position_long_account"],
        row["top_position_short_account"],
    ) = ratio_fields(top_pos)
    (
        row["top_account_long_short_ratio"],
        row["top_account_long_account"],
        row["top_account_short_account"],
    ) = ratio_fields(top_acc)
    (
        row["global_account_long_short_ratio"],
        row["global_account_long_account"],
        row["global_account_short_account"],
    ) = ratio_fields(global_acc)
    row["taker_buy_sell_ratio"], row["taker_buy_volume"], row["taker_sell_volume"] = taker_fields(taker)

    bias, score = crowding(
        safe_float(row["top_position_long_short_ratio"]),
        safe_float(row["global_account_long_short_ratio"]),
        safe_float(row["taker_buy_sell_ratio"]),
    )
    row["crowding_bias"] = bias
    row["crowding_score"] = score
    row["quality_status"] = "ok" if row["top_position_long_short_ratio"] or row["global_account_long_short_ratio"] else "partial"
    row["raw_json"] = json_dumps(
        {
            "top_position": top_pos,
            "top_account": top_acc,
            "global_account": global_acc,
            "taker": taker,
        }
    )
    return row


def main() -> int:
    args = parse_args()
    watch_rows = [row for row in read_csv_rows(normalize_path(args.watchlist)) if is_enabled(row)]
    observed_utc = dt_to_utc_iso(now_utc())
    rows = []
    for index, item in enumerate(watch_rows, start=1):
        symbol = str(item.get("binance_futures_symbol", "") or "").strip().upper()
        print(f"[{index}/{len(watch_rows)}] long_short symbol={symbol}")
        rows.append(build_row(item, args.period, safe_int(args.limit, 2), observed_utc))

    output_path = normalize_path(args.output)
    write_csv_rows(output_path, rows, SNAPSHOT_COLUMNS)
    ok_rows = sum(1 for row in rows if row["quality_status"] == "ok")
    partial_rows = sum(1 for row in rows if row["quality_status"] == "partial")
    skipped_rows = sum(1 for row in rows if row["quality_status"] == "skipped")
    top_crowded = sorted(
        [row for row in rows if row.get("crowding_score") not in {"", None}],
        key=lambda row: safe_float(row.get("crowding_score")),
        reverse=True,
    )
    write_summary(
        normalize_path(args.summary),
        {
            "watcher": "binance_long_short_ratios",
            "observed_at_china": utc_iso_to_china(observed_utc),
            "period": args.period,
            "watchlist_rows": len(watch_rows),
            "ok_rows": ok_rows,
            "partial_rows": partial_rows,
            "skipped_rows": skipped_rows,
            "top_crowded_asset": top_crowded[0]["asset_symbol"] if top_crowded else "",
            "top_crowded_bias": top_crowded[0]["crowding_bias"] if top_crowded else "",
            "top_crowded_score": top_crowded[0]["crowding_score"] if top_crowded else "",
            "status": "pass" if ok_rows or partial_rows else "warning",
        },
    )
    print(f"long_short_rows={len(rows)} ok={ok_rows} partial={partial_rows} skipped={skipped_rows}")
    print(f"wrote_output={output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
