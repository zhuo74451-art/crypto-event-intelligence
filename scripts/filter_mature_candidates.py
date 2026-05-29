import argparse
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

try:
    from utils.time_utils import parse_any_time_to_utc_iso
except ModuleNotFoundError:
    from scripts.utils.time_utils import parse_any_time_to_utc_iso


ROOT = Path(__file__).resolve().parents[1]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Filter review candidates mature enough for 72h backtests.")
    parser.add_argument(
        "--input", default=str(ROOT / "data" / "event_candidates_real_200_review_suggested.csv")
    )
    parser.add_argument(
        "--output", default=str(ROOT / "data" / "event_candidates_real_mature_review_suggested.csv")
    )
    parser.add_argument(
        "--summary", default=str(ROOT / "results" / "v042_mature_filter_summary.csv")
    )
    parser.add_argument("--min-age-hours", type=float, default=80.0)
    parser.add_argument("--now-utc", default="")
    return parser.parse_args()


def normalize_path(path_value: str) -> Path:
    path = Path(path_value)
    if not path.is_absolute():
        path = ROOT / path
    return path


def parse_utc_dt(value: str):
    iso = parse_any_time_to_utc_iso(value)
    if not iso:
        return None, ""
    return datetime.strptime(iso, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc), iso


def horizon_status(age_hours: float | None) -> str:
    if age_hours is None:
        return "time_parse_failed"
    if age_hours >= 80:
        return "mature_72h"
    if age_hours >= 24:
        return "mature_24h_only"
    if age_hours >= 4:
        return "mature_4h_only"
    if age_hours >= 1:
        return "mature_1h_only"
    return "too_new"


def main() -> int:
    args = parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", datefmt="%H:%M:%S")
    input_path = normalize_path(args.input)
    output_path = normalize_path(args.output)
    summary_path = normalize_path(args.summary)

    if not input_path.exists():
        logging.error("input file not found: %s", input_path)
        return 1

    now_iso = parse_any_time_to_utc_iso(args.now_utc) if args.now_utc else ""
    if now_iso:
        now = datetime.strptime(now_iso, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    else:
        now = datetime.now(timezone.utc).replace(microsecond=0)

    df = pd.read_csv(input_path, dtype=str).fillna("")
    ages = []
    statuses = []
    mature_flags = []
    parsed_times = []
    for _, row in df.iterrows():
        value = row.get("backtest_time_utc", "") or row.get("backtest_time", "") or row.get("published_at_utc", "")
        dt, parsed = parse_utc_dt(str(value))
        parsed_times.append(parsed)
        if dt is None:
            ages.append("")
            statuses.append("time_parse_failed")
            mature_flags.append(False)
            continue
        age = (now - dt).total_seconds() / 3600.0
        ages.append(round(age, 4))
        status = horizon_status(age)
        statuses.append(status)
        mature_flags.append(age >= args.min_age_hours)

    df["parsed_backtest_time_utc"] = parsed_times
    df["event_age_hours"] = ages
    df["horizon_status"] = statuses
    df["is_mature_72h"] = [str(flag).lower() for flag in mature_flags]
    mature = df[df["is_mature_72h"] == "true"].copy()

    output_path.parent.mkdir(parents=True, exist_ok=True)
    mature.to_csv(output_path, index=False)

    summary = pd.DataFrame(
        [
            {
                "total_candidates": len(df),
                "mature_72h_count": int((df["is_mature_72h"] == "true").sum()),
                "mature_24h_only_count": int((df["horizon_status"] == "mature_24h_only").sum()),
                "mature_4h_only_count": int((df["horizon_status"] == "mature_4h_only").sum()),
                "mature_1h_only_count": int((df["horizon_status"] == "mature_1h_only").sum()),
                "too_new_count": int((df["horizon_status"] == "too_new").sum()),
                "time_parse_failed_count": int((df["horizon_status"] == "time_parse_failed").sum()),
                "now_utc": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "min_age_hours": args.min_age_hours,
            }
        ]
    )
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary.to_csv(summary_path, index=False)
    logging.info("wrote mature candidates to %s", output_path)
    logging.info("wrote mature filter summary to %s", summary_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
