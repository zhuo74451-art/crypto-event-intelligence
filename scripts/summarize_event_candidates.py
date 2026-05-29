import argparse
import logging
import sys
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]

SUMMARY_COLUMNS = [
    "total_candidates",
    "needs_review_count",
    "include_count",
    "exclude_count",
    "fix_count",
    "missing_review_decision_count",
    "missing_asset_count",
    "multi_asset_count",
    "market_wide_count",
    "unknown_event_type_count",
    "time_parse_failed_count",
    "asset_confidence_low_count",
    "asset_confidence_medium_count",
    "asset_confidence_high_count",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Summarize imported event candidate quality.")
    parser.add_argument("--input", default=str(ROOT / "data" / "event_candidates_review.csv"))
    parser.add_argument("--output-dir", default=str(ROOT / "results"))
    return parser.parse_args()


def normalize_path(path_value: str) -> Path:
    path = Path(path_value)
    if not path.is_absolute():
        path = ROOT / path
    return path


def flag_contains(series: pd.Series, flag: str) -> pd.Series:
    return series.fillna("").astype(str).str.split(",").apply(lambda parts: flag in parts)


def count_equals(series: pd.Series, value: str) -> int:
    return int((series.fillna("").astype(str).str.strip().str.lower() == value).sum())


def build_overall_summary(df: pd.DataFrame) -> pd.DataFrame:
    review_decision = df.get("review_decision", pd.Series("", index=df.index))
    quality_flags = df.get("quality_flags", pd.Series("", index=df.index))
    asset_confidence = df.get("asset_confidence", pd.Series("", index=df.index))
    event_scope = df.get("event_scope", pd.Series("", index=df.index))
    event_type = df.get("candidate_event_type", pd.Series("", index=df.index))
    time_parse_status = df.get("time_parse_status", pd.Series("", index=df.index))

    row = {
        "total_candidates": int(len(df)),
        "needs_review_count": count_equals(df.get("needs_review", pd.Series("", index=df.index)), "true"),
        "include_count": count_equals(review_decision, "include"),
        "exclude_count": count_equals(review_decision, "exclude"),
        "fix_count": count_equals(review_decision, "fix"),
        "missing_review_decision_count": int((review_decision.fillna("").astype(str).str.strip() == "").sum()),
        "missing_asset_count": int(flag_contains(quality_flags, "missing_asset").sum()),
        "multi_asset_count": int((event_scope.fillna("").astype(str) == "multi_asset").sum()),
        "market_wide_count": int((event_scope.fillna("").astype(str) == "market_wide").sum()),
        "unknown_event_type_count": int((event_type.fillna("").astype(str) == "other").sum()),
        "time_parse_failed_count": int(
            (
                (time_parse_status.fillna("").astype(str) == "failed")
                | flag_contains(quality_flags, "time_parse_failed")
            ).sum()
        ),
        "asset_confidence_low_count": count_equals(asset_confidence, "low"),
        "asset_confidence_medium_count": count_equals(asset_confidence, "medium"),
        "asset_confidence_high_count": count_equals(asset_confidence, "high"),
    }
    return pd.DataFrame([row], columns=SUMMARY_COLUMNS)


def grouped_summary(df: pd.DataFrame, column: str) -> pd.DataFrame:
    if column not in df.columns:
        return pd.DataFrame(columns=[column, "candidate_count", "needs_review_count", "include_count"])
    grouped = (
        df.assign(
            needs_review_bool=df.get(
                "needs_review", pd.Series("", index=df.index)
            ).astype(str).str.lower()
            == "true",
            include_bool=df.get(
                "review_decision", pd.Series("", index=df.index)
            ).astype(str).str.lower()
            == "include",
        )
        .groupby(column, dropna=False)
        .agg(
            candidate_count=("candidate_id", "count"),
            needs_review_count=("needs_review_bool", "sum"),
            include_count=("include_bool", "sum"),
        )
        .reset_index()
    )
    return grouped


def main() -> int:
    args = parse_args()
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        datefmt="%H:%M:%S",
    )

    input_path = normalize_path(args.input)
    output_dir = normalize_path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    if not input_path.exists():
        logging.error("input file not found: %s", input_path)
        return 1

    df = pd.read_csv(input_path, dtype=str).fillna("")
    overall = build_overall_summary(df)
    by_event_type = grouped_summary(df, "candidate_event_type")
    by_scope = grouped_summary(df, "event_scope")

    overall_path = output_dir / "v03_candidate_import_summary.csv"
    event_type_path = output_dir / "v03_candidate_summary_by_event_type.csv"
    scope_path = output_dir / "v03_candidate_summary_by_scope.csv"

    overall.to_csv(overall_path, index=False)
    by_event_type.to_csv(event_type_path, index=False)
    by_scope.to_csv(scope_path, index=False)

    logging.info("wrote %s", overall_path)
    logging.info("wrote %s", event_type_path)
    logging.info("wrote %s", scope_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
