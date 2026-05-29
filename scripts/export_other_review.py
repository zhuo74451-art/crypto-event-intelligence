import argparse
import logging
import sys
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Export event_type=other rows for manual taxonomy review.")
    parser.add_argument(
        "--input",
        default=str(ROOT / "results" / "v043_older_mature50_event_price_backfill.csv"),
    )
    parser.add_argument(
        "--output",
        default=str(ROOT / "data" / "v05_other_event_review.csv"),
    )
    parser.add_argument("--event-type", default="other")
    return parser.parse_args()


def normalize_path(path_value: str) -> Path:
    path = Path(path_value)
    if not path.is_absolute():
        path = ROOT / path
    return path


def main() -> int:
    args = parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", datefmt="%H:%M:%S")
    input_path = normalize_path(args.input)
    output_path = normalize_path(args.output)

    if not input_path.exists():
        logging.error("input file not found: %s", input_path)
        return 1

    df = pd.read_csv(input_path, dtype=str).fillna("")
    if "event_type" not in df.columns:
        logging.error("input has no event_type column")
        return 1

    review = df[df["event_type"] == args.event_type].copy()
    for col in ["abnormal_vs_btc_24h", "abnormal_vs_btc_72h"]:
        if col in review.columns:
            review[col] = pd.to_numeric(review[col], errors="coerce")
    if "abnormal_vs_btc_72h" in review.columns:
        review = review.sort_values("abnormal_vs_btc_72h", ascending=False)

    keep = [
        "event_id",
        "event_time",
        "title",
        "content",
        "source",
        "asset_symbol",
        "event_type",
        "direction_hint",
        "importance",
        "abnormal_vs_btc_1h",
        "abnormal_vs_btc_4h",
        "abnormal_vs_btc_24h",
        "abnormal_vs_btc_72h",
        "status",
        "skip_reason",
    ]
    keep = [col for col in keep if col in review.columns]
    review = review[keep]
    review["proposed_event_type"] = ""
    review["taxonomy_issue"] = ""
    review["review_decision"] = ""
    review["review_notes"] = ""

    output_path.parent.mkdir(parents=True, exist_ok=True)
    review.to_csv(output_path, index=False)
    logging.info("wrote %s rows to %s", len(review), output_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
