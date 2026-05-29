import argparse
import logging
import sys
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]

MANUAL_COLUMNS = [
    "manual_decision",
    "manual_event_type_l1",
    "manual_event_type_l2",
    "manual_primary_asset_symbol",
    "manual_channel_route",
    "manual_useful_for_research",
    "manual_notes",
]

KEEP_COLUMNS = [
    "label_source",
    "candidate_id",
    "published_at",
    "published_at_utc",
    "published_at_china",
    "backtest_time",
    "backtest_time_utc",
    "backtest_time_china",
    "source_timezone",
    "source_timezone_assumption",
    "title",
    "content",
    "source",
    "url",
    "primary_asset_symbol",
    "candidate_asset_symbol",
    "event_type_l1",
    "event_type_l2",
    "event_scope",
    "publish_decision",
    "research_priority",
    "channel_route",
    "tradability_tier",
    "tradability_tier_reason",
    "relevance_score_realtime",
    "discard_reason",
    "relevance_flags",
    "detected_entity_names",
    "entity_flags",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a v0.6 manual labeling sheet from review queues.")
    parser.add_argument(
        "--publish-review",
        default=str(ROOT / "data" / "event_candidates_v06_publish_review_queue.csv"),
    )
    parser.add_argument(
        "--other-review",
        default=str(ROOT / "data" / "event_candidates_v06_other_review_queue.csv"),
    )
    parser.add_argument(
        "--discard-audit",
        default=str(ROOT / "data" / "event_candidates_v06_discard_audit_sample.csv"),
    )
    parser.add_argument("--other-limit", type=int, default=66)
    parser.add_argument("--discard-limit", type=int, default=66)
    parser.add_argument("--output", default=str(ROOT / "data" / "v06_manual_label_sheet.csv"))
    parser.add_argument("--summary", default=str(ROOT / "results" / "v06_manual_label_sheet_summary.csv"))
    return parser.parse_args()


def normalize_path(value: str) -> Path:
    path = Path(value)
    if not path.is_absolute():
        path = ROOT / path
    return path


def read_queue(path: Path, label_source: str, limit: int | None = None) -> pd.DataFrame:
    if not path.exists():
        logging.warning("queue not found: %s", path)
        return pd.DataFrame()
    df = pd.read_csv(path, dtype=str).fillna("")
    if limit is not None and limit > 0:
        df = df.head(limit)
    df.insert(0, "label_source", label_source)
    return df


def ensure_columns(df: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    for column in columns:
        if column not in df.columns:
            df[column] = ""
    return df[columns]


def build_summary(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(
            [
                {
                    "total_label_rows": 0,
                    "publish_review_rows": 0,
                    "other_review_rows": 0,
                    "discard_audit_rows": 0,
                    "alpha_candidate_rows": 0,
                    "macro_policy_rows": 0,
                    "unsupported_research_rows": 0,
                    "research_only_rows": 0,
                }
            ]
        )
    return pd.DataFrame(
        [
            {
                "total_label_rows": int(len(df)),
                "publish_review_rows": int((df["label_source"] == "publish_review").sum()),
                "other_review_rows": int((df["label_source"] == "other_review").sum()),
                "discard_audit_rows": int((df["label_source"] == "discard_audit").sum()),
                "alpha_candidate_rows": int((df["channel_route"] == "alpha_candidate").sum()),
                "macro_policy_rows": int((df["channel_route"] == "macro_policy").sum()),
                "unsupported_research_rows": int((df["channel_route"] == "unsupported_research").sum()),
                "research_only_rows": int((df["channel_route"] == "research_only").sum()),
            }
        ]
    )


def main() -> int:
    args = parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", datefmt="%H:%M:%S")
    publish = read_queue(normalize_path(args.publish_review), "publish_review")
    other = read_queue(normalize_path(args.other_review), "other_review", args.other_limit)
    discard = read_queue(normalize_path(args.discard_audit), "discard_audit", args.discard_limit)

    combined = pd.concat([publish, other, discard], ignore_index=True).fillna("")
    if combined.empty:
        logging.error("no rows available for manual label sheet")
        return 1

    combined = ensure_columns(combined, KEEP_COLUMNS)
    for column in reversed(MANUAL_COLUMNS):
        combined.insert(0, column, "")

    output_path = normalize_path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    combined.to_csv(output_path, index=False)

    summary = build_summary(combined)
    summary_path = normalize_path(args.summary)
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary.to_csv(summary_path, index=False)

    logging.info("wrote %s label rows to %s", len(combined), output_path)
    logging.info("wrote summary to %s", summary_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
