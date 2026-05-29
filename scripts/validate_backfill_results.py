import argparse
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import List

import pandas as pd

try:
    from utils.time_utils import parse_any_time_to_utc_iso, utc_iso_to_china_iso
except ModuleNotFoundError:
    from scripts.utils.time_utils import parse_any_time_to_utc_iso, utc_iso_to_china_iso


ROOT = Path(__file__).resolve().parents[1]

KEY_PRICE_COLUMNS = [
    "asset_price_t0",
    "asset_price_1h",
    "asset_price_4h",
    "asset_price_24h",
    "asset_price_72h",
    "btc_price_t0",
    "btc_price_24h",
    "eth_price_t0",
    "eth_price_24h",
]

ABNORMAL_VS_BTC_COLUMNS = [
    "abnormal_vs_btc_1h",
    "abnormal_vs_btc_4h",
    "abnormal_vs_btc_24h",
    "abnormal_vs_btc_72h",
]

OUTPUT_COLUMNS = [
    "event_id",
    "event_time",
    "title",
    "asset_symbol",
    "event_type",
    "status",
    "parsed_event_time_utc",
    "parsed_event_time_china",
    "time_quality_status",
    "quality_status",
    "quality_flags",
    "skip_reason",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate event price backfill quality.")
    parser.add_argument(
        "--input", default=str(ROOT / "results" / "event_price_backfill.csv")
    )
    parser.add_argument(
        "--output", default=str(ROOT / "results" / "event_quality_report.csv")
    )
    return parser.parse_args()


def normalize_path(path_value: str) -> Path:
    path = Path(path_value)
    if not path.is_absolute():
        path = ROOT / path
    return path


def ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def is_blank(value) -> bool:
    return pd.isna(value) or str(value).strip() == ""


def quality_status_from_flags(status: str, flags: List[str]) -> str:
    fail_flags = {
        "invalid_status",
        "status_error",
        "status_skipped",
        "invalid_event_time",
        "future_event_time",
        "missing_asset_symbol",
        "missing_symbol",
    }
    if any(flag in fail_flags for flag in flags):
        return "fail"
    if flags:
        return "warning"
    return "pass"


def validate_row(row: pd.Series) -> dict:
    flags: List[str] = []
    status = str(row.get("status", "")).strip().lower()
    raw_event_time = str(row.get("event_time_utc", "") or row.get("event_time", "")).strip()
    parsed_event_time_utc = parse_any_time_to_utc_iso(raw_event_time)
    parsed_event_time_china = utc_iso_to_china_iso(parsed_event_time_utc)
    time_quality_status = "pass"

    if status not in {"ok", "partial", "skipped", "error"}:
        flags.append("invalid_status")
    elif status == "skipped":
        flags.append("status_skipped")
    elif status == "error":
        flags.append("status_error")

    if not parsed_event_time_utc:
        flags.append("invalid_event_time")
        time_quality_status = "fail"
    else:
        if raw_event_time != parsed_event_time_utc:
            flags.append("non_standard_time_format")
            time_quality_status = "warning"
        event_dt = datetime.strptime(parsed_event_time_utc, "%Y-%m-%dT%H:%M:%SZ").replace(
            tzinfo=timezone.utc
        )
        if event_dt > datetime.now(timezone.utc):
            flags.append("future_event_time")
            time_quality_status = "fail"

    if is_blank(row.get("asset_symbol", "")):
        flags.append("missing_asset_symbol")

    if is_blank(row.get("binance_spot_symbol", "")) and is_blank(
        row.get("binance_futures_symbol", "")
    ):
        flags.append("missing_symbol")

    for column in KEY_PRICE_COLUMNS:
        if column not in row.index or is_blank(row.get(column, "")):
            flags.append(f"missing_{column}")

    for column in ABNORMAL_VS_BTC_COLUMNS:
        if column not in row.index or is_blank(row.get(column, "")):
            flags.append(f"missing_{column}")
            continue
        value = pd.to_numeric(pd.Series([row.get(column)]), errors="coerce").iloc[0]
        if pd.isna(value):
            flags.append(f"invalid_{column}")
        elif abs(float(value)) > 0.5:
            flags.append("suspicious_extreme_return")

    flags = sorted(set(flags), key=flags.index)
    return {
        "event_id": row.get("event_id", ""),
        "event_time": row.get("event_time", ""),
        "title": row.get("title", ""),
        "asset_symbol": row.get("asset_symbol", ""),
        "event_type": row.get("event_type", ""),
        "status": row.get("status", ""),
        "parsed_event_time_utc": parsed_event_time_utc,
        "parsed_event_time_china": parsed_event_time_china,
        "time_quality_status": time_quality_status,
        "quality_status": quality_status_from_flags(status, flags),
        "quality_flags": ",".join(flags),
        "skip_reason": row.get("skip_reason", ""),
    }


def build_quality_report(df: pd.DataFrame) -> pd.DataFrame:
    rows = [validate_row(row) for _, row in df.fillna("").iterrows()]
    return pd.DataFrame(rows, columns=OUTPUT_COLUMNS)


def main() -> int:
    args = parse_args()
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        datefmt="%H:%M:%S",
    )

    input_path = normalize_path(args.input)
    output_path = normalize_path(args.output)

    if not input_path.exists():
        logging.error("input file not found: %s", input_path)
        return 1

    df = pd.read_csv(input_path, dtype=str).fillna("")
    report = build_quality_report(df)
    ensure_parent(output_path)
    report.to_csv(output_path, index=False)
    logging.info("wrote %s rows to %s", len(report), output_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
