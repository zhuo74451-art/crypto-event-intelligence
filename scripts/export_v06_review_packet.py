import argparse
import logging
import sys
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]

PACKET_COLUMNS = [
    "candidate_id",
    "label_source",
    "title",
    "source",
    "published_at_china",
    "primary_asset_symbol",
    "event_type_l1",
    "event_type_l2",
    "event_scope",
    "channel_route",
    "relevance_score_realtime",
    "review_focus",
    "manual_decision",
    "manual_event_type_l1",
    "manual_event_type_l2",
    "manual_primary_asset_symbol",
    "manual_channel_route",
    "manual_useful_for_research",
    "manual_notes",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Export a compact review packet from v0.6 batch file.")
    parser.add_argument("--input", default=str(ROOT / "data" / "v06_manual_label_batch.csv"))
    parser.add_argument("--output", default=str(ROOT / "data" / "v06_manual_label_batch_review.csv"))
    return parser.parse_args()


def normalize_path(value: str) -> Path:
    path = Path(value)
    if not path.is_absolute():
        path = ROOT / path
    return path


def ensure_columns(df: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    for col in columns:
        if col not in df.columns:
            df[col] = ""
    return df[columns]


def main() -> int:
    args = parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", datefmt="%H:%M:%S")
    input_path = normalize_path(args.input)
    output_path = normalize_path(args.output)
    if not input_path.exists():
        logging.error("input not found: %s", input_path)
        return 1

    df = pd.read_csv(input_path, dtype=str).fillna("")
    out = ensure_columns(df, PACKET_COLUMNS)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(output_path, index=False)
    logging.info("wrote %s review rows to %s", len(out), output_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
