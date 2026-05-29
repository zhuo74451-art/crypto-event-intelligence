import argparse
import logging
import sys
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build an auto-selected review file for quick backtesting.")
    parser.add_argument(
        "--input", default=str(ROOT / "data" / "event_candidates_real_200_review_suggested.csv")
    )
    parser.add_argument(
        "--output", default=str(ROOT / "data" / "event_candidates_real_200_review_auto50.csv")
    )
    parser.add_argument("--limit", type=int, default=50)
    return parser.parse_args()


def normalize_path(path_value: str) -> Path:
    path = Path(path_value)
    if not path.is_absolute():
        path = ROOT / path
    return path


def ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def has_flag(row: pd.Series, flag: str) -> bool:
    return flag in [part.strip() for part in str(row.get("quality_flags", "")).split(",") if part.strip()]


def eligible(row: pd.Series, allow_fix: bool = False) -> bool:
    if has_flag(row, "missing_asset") or has_flag(row, "time_parse_failed"):
        return False
    if str(row.get("candidate_asset_symbol", "")).strip() == "":
        return False
    if (
        str(row.get("candidate_binance_spot_symbol", "")).strip() == ""
        and str(row.get("candidate_binance_futures_symbol", "")).strip() == ""
    ):
        return False
    if str(row.get("backtest_time_utc", "")).strip() == "":
        return False
    score = float(row.get("auto_quality_score", 0) or 0)
    if str(row.get("event_scope", "")).strip() == "multi_asset" and score < 90:
        return False
    if allow_fix:
        return str(row.get("suggested_review_decision", "")).strip() in {"include", "fix"}
    return str(row.get("suggested_review_decision", "")).strip() == "include"


def main() -> int:
    args = parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", datefmt="%H:%M:%S")
    input_path = normalize_path(args.input)
    output_path = normalize_path(args.output)

    if not input_path.exists():
        logging.error("input file not found: %s", input_path)
        return 1

    df = pd.read_csv(input_path, dtype=str).fillna("")
    df["auto_quality_score_num"] = pd.to_numeric(df["auto_quality_score"], errors="coerce").fillna(-9999)
    sorted_df = df.sort_values(["auto_quality_score_num", "candidate_importance"], ascending=[False, False])

    selected = sorted_df[sorted_df.apply(lambda row: eligible(row, allow_fix=False), axis=1)].copy()
    if len(selected) < args.limit:
        remaining_ids = set(selected["candidate_id"])
        fillers = sorted_df[
            (~sorted_df["candidate_id"].isin(remaining_ids))
            & sorted_df.apply(lambda row: eligible(row, allow_fix=True), axis=1)
        ].copy()
        selected = pd.concat([selected, fillers], ignore_index=True)

    selected = selected.head(args.limit).copy()
    selected["review_decision"] = "include"
    selected = selected.drop(columns=["auto_quality_score_num"], errors="ignore")

    ensure_parent(output_path)
    selected.to_csv(output_path, index=False)
    print(f"selected_count={len(selected)}")
    logging.info("wrote auto review file to %s", output_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
