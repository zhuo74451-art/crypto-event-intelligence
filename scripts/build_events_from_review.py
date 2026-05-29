import argparse
import logging
import sys
from pathlib import Path
from typing import Dict

import pandas as pd

try:
    from utils.time_utils import parse_any_time_to_utc_iso, utc_iso_to_china_iso
except ModuleNotFoundError:
    from scripts.utils.time_utils import parse_any_time_to_utc_iso, utc_iso_to_china_iso


ROOT = Path(__file__).resolve().parents[1]

OUTPUT_COLUMNS = [
    "event_id",
    "event_time",
    "event_time_utc",
    "event_time_china",
    "title",
    "content",
    "source",
    "asset_symbol",
    "binance_spot_symbol",
    "binance_futures_symbol",
    "event_type",
    "event_subtype",
    "source_type",
    "direction_hint",
    "importance",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build backfillable event samples from manually reviewed candidates."
    )
    parser.add_argument("--input", default=str(ROOT / "data" / "event_candidates_review.csv"))
    parser.add_argument("--output", default=str(ROOT / "data" / "events_raw_50.csv"))
    parser.add_argument("--limit", type=int, default=50)
    parser.add_argument("--symbol-map", default=str(ROOT / "data" / "symbol_map.csv"))
    return parser.parse_args()


def normalize_path(path_value: str) -> Path:
    path = Path(path_value)
    if not path.is_absolute():
        path = ROOT / path
    return path


def ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def load_symbol_map(path: Path) -> Dict[str, Dict[str, str]]:
    if not path.exists():
        logging.warning("symbol map not found: %s", path)
        return {}
    df = pd.read_csv(path, dtype=str).fillna("")
    result: Dict[str, Dict[str, str]] = {}
    for _, row in df.iterrows():
        asset = str(row.get("asset_symbol", "")).strip().upper()
        if not asset:
            continue
        result[asset] = {
            "binance_spot_symbol": str(row.get("binance_spot_symbol", "")).strip().upper(),
            "binance_futures_symbol": str(row.get("binance_futures_symbol", "")).strip().upper(),
        }
    return result


def first_value(*values, default=""):
    for value in values:
        if not pd.isna(value) and str(value).strip() != "":
            return str(value).strip()
    return default


def build_event(row: pd.Series, idx: int, symbol_map: Dict[str, Dict[str, str]]) -> dict:
    asset = first_value(row.get("candidate_asset_symbol", "")).upper()
    mapped = symbol_map.get(asset, {})
    spot_symbol = first_value(
        row.get("candidate_binance_spot_symbol", ""),
        mapped.get("binance_spot_symbol", ""),
    ).upper()
    futures_symbol = first_value(
        row.get("candidate_binance_futures_symbol", ""),
        mapped.get("binance_futures_symbol", ""),
    ).upper()

    event_time_utc = first_value(
        row.get("backtest_time_utc", ""),
        row.get("published_at_utc", ""),
        row.get("backtest_time", ""),
        row.get("published_at", ""),
    )
    event_time_utc = parse_any_time_to_utc_iso(event_time_utc)
    event_time_china = first_value(
        row.get("backtest_time_china", ""),
        row.get("published_at_china", ""),
        utc_iso_to_china_iso(event_time_utc),
    )

    return {
        "event_id": first_value(row.get("candidate_id", ""), default=f"evt50_{idx + 1:03d}"),
        "event_time": event_time_china,
        "event_time_utc": event_time_utc,
        "event_time_china": event_time_china,
        "title": row.get("title", ""),
        "content": row.get("content", ""),
        "source": row.get("source", ""),
        "asset_symbol": asset,
        "binance_spot_symbol": spot_symbol,
        "binance_futures_symbol": futures_symbol,
        "event_type": first_value(row.get("candidate_event_type", ""), default="other"),
        "event_subtype": first_value(row.get("candidate_event_subtype", ""), row.get("event_subtype", ""), default=first_value(row.get("candidate_event_type", ""), default="other")),
        "source_type": first_value(row.get("source_type", ""), row.get("source", ""), default="historical_unknown"),
        "direction_hint": first_value(row.get("candidate_direction_hint", ""), default="observe"),
        "importance": first_value(row.get("candidate_importance", ""), default="3"),
    }


def main() -> int:
    args = parse_args()
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        datefmt="%H:%M:%S",
    )

    input_path = normalize_path(args.input)
    output_path = normalize_path(args.output)
    symbol_map_path = normalize_path(args.symbol_map)

    if not input_path.exists():
        logging.error("input file not found: %s", input_path)
        return 1

    review = pd.read_csv(input_path, dtype=str).fillna("")
    included = review[
        review["review_decision"].astype(str).str.strip().str.lower() == "include"
    ].copy()
    if args.limit and args.limit > 0:
        included = included.head(args.limit)

    symbol_map = load_symbol_map(symbol_map_path)
    rows = [build_event(row, idx, symbol_map) for idx, row in included.iterrows()]
    output = pd.DataFrame(rows, columns=OUTPUT_COLUMNS)
    ensure_parent(output_path)
    output.to_csv(output_path, index=False)
    logging.info("wrote %s included events to %s", len(output), output_path)
    if len(output) < args.limit:
        logging.warning("included sample count is below requested limit: %s/%s", len(output), args.limit)
    return 0


if __name__ == "__main__":
    sys.exit(main())
