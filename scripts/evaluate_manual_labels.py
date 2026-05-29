import argparse
import logging
import sys
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]

DECISION_MAP = {
    "approve_publish": "human_review",
    "keep_review": "human_review",
    "discard": "discard",
    "fix_taxonomy": "human_review",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate v0.6 intake decisions against manual labels.")
    parser.add_argument("--input", default=str(ROOT / "data" / "v06_manual_label_sheet.csv"))
    parser.add_argument("--summary", default=str(ROOT / "results" / "v06_manual_label_eval_summary.csv"))
    parser.add_argument("--errors", default=str(ROOT / "results" / "v06_manual_label_eval_errors.csv"))
    return parser.parse_args()


def normalize_path(value: str) -> Path:
    path = Path(value)
    if not path.is_absolute():
        path = ROOT / path
    return path


def clean(value: str) -> str:
    return str(value or "").strip()


def lower(value: str) -> str:
    return clean(value).lower()


def boolish_yes(value: str) -> bool | None:
    value = lower(value)
    if value in {"yes", "y", "true", "1", "是", "有用"}:
        return True
    if value in {"no", "n", "false", "0", "否", "无用"}:
        return False
    return None


def labeled_mask(df: pd.DataFrame) -> pd.Series:
    return df.get("manual_decision", pd.Series("", index=df.index)).fillna("").astype(str).str.strip() != ""


def expected_decision(manual_decision: str) -> str:
    return DECISION_MAP.get(lower(manual_decision), "")


def row_errors(row: pd.Series) -> list[str]:
    errors = []
    manual_decision = lower(row.get("manual_decision", ""))
    expected = expected_decision(manual_decision)
    auto_decision = lower(row.get("publish_decision", ""))
    if expected and auto_decision != expected:
        errors.append("publish_decision_mismatch")

    manual_l1 = lower(row.get("manual_event_type_l1", ""))
    auto_l1 = lower(row.get("event_type_l1", ""))
    if manual_l1 and manual_l1 != auto_l1:
        errors.append("event_type_l1_mismatch")

    manual_l2 = lower(row.get("manual_event_type_l2", ""))
    auto_l2 = lower(row.get("event_type_l2", ""))
    if manual_l2 and manual_l2 != auto_l2:
        errors.append("event_type_l2_mismatch")

    manual_asset = lower(row.get("manual_primary_asset_symbol", ""))
    auto_asset = lower(row.get("primary_asset_symbol", "") or row.get("candidate_asset_symbol", ""))
    if manual_asset and manual_asset != auto_asset:
        errors.append("primary_asset_mismatch")

    manual_route = lower(row.get("manual_channel_route", ""))
    auto_route = lower(row.get("channel_route", ""))
    if manual_route and manual_route != auto_route:
        errors.append("channel_route_mismatch")

    useful = boolish_yes(row.get("manual_useful_for_research", ""))
    if useful is False and auto_decision == "human_review":
        errors.append("false_positive_review")
    if useful is True and auto_decision == "discard":
        errors.append("false_negative_discard")

    return errors


def build_summary(df: pd.DataFrame, labeled: pd.DataFrame, errors_df: pd.DataFrame) -> pd.DataFrame:
    total = len(df)
    labeled_count = len(labeled)
    auto_prefilled_count = int(df.get("auto_prefilled", pd.Series("", index=df.index)).fillna("").astype(str).str.lower().isin({"1", "true", "yes"}).sum())
    error_flags = errors_df["error_flags"].fillna("").astype(str) if not errors_df.empty else pd.Series([], dtype=str)

    def count_flag(flag: str) -> int:
        if error_flags.empty:
            return 0
        return int(error_flags.str.contains(flag, regex=False).sum())

    return pd.DataFrame(
        [
            {
                "total_rows": total,
                "labeled_rows": labeled_count,
                "unlabeled_rows": total - labeled_count,
                "label_coverage_pct": round(labeled_count / total * 100, 2) if total else 0,
                "auto_prefilled_rows": auto_prefilled_count,
                "error_rows": int(len(errors_df)),
                "error_rate_pct": round(len(errors_df) / labeled_count * 100, 2) if labeled_count else "",
                "publish_decision_mismatch_count": count_flag("publish_decision_mismatch"),
                "event_type_l1_mismatch_count": count_flag("event_type_l1_mismatch"),
                "event_type_l2_mismatch_count": count_flag("event_type_l2_mismatch"),
                "primary_asset_mismatch_count": count_flag("primary_asset_mismatch"),
                "channel_route_mismatch_count": count_flag("channel_route_mismatch"),
                "false_positive_review_count": count_flag("false_positive_review"),
                "false_negative_discard_count": count_flag("false_negative_discard"),
            }
        ]
    )


def main() -> int:
    args = parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", datefmt="%H:%M:%S")
    input_path = normalize_path(args.input)
    summary_path = normalize_path(args.summary)
    errors_path = normalize_path(args.errors)
    if not input_path.exists():
        logging.error("input not found: %s", input_path)
        return 1

    df = pd.read_csv(input_path, dtype=str).fillna("")
    labeled = df[labeled_mask(df)].copy()
    error_rows = []
    for _, row in labeled.iterrows():
        errors = row_errors(row)
        if errors:
            item = row.to_dict()
            item["error_flags"] = ",".join(errors)
            error_rows.append(item)

    errors_df = pd.DataFrame(error_rows)
    summary = build_summary(df, labeled, errors_df)

    summary_path.parent.mkdir(parents=True, exist_ok=True)
    errors_path.parent.mkdir(parents=True, exist_ok=True)
    summary.to_csv(summary_path, index=False)
    errors_df.to_csv(errors_path, index=False)
    logging.info("wrote summary to %s", summary_path)
    logging.info("wrote error rows to %s", errors_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
