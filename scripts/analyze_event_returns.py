import argparse
import logging
import sys
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
WINDOWS = ["1h", "4h", "24h", "72h"]

METRIC_COLUMNS = [
    "sample_count",
    "valid_sample_count",
    "skipped_sample_count",
    "failed_quality_count",
    "warning_quality_count",
    "avg_asset_return_1h",
    "avg_asset_return_4h",
    "avg_asset_return_24h",
    "avg_asset_return_72h",
    "avg_abnormal_vs_btc_1h",
    "avg_abnormal_vs_btc_4h",
    "avg_abnormal_vs_btc_24h",
    "avg_abnormal_vs_btc_72h",
    "avg_abnormal_vs_eth_1h",
    "avg_abnormal_vs_eth_4h",
    "avg_abnormal_vs_eth_24h",
    "avg_abnormal_vs_eth_72h",
    "median_abnormal_vs_btc_24h",
    "median_abnormal_vs_eth_24h",
    "win_rate_vs_btc_1h",
    "win_rate_vs_btc_4h",
    "win_rate_vs_btc_24h",
    "win_rate_vs_btc_72h",
    "win_rate_vs_eth_1h",
    "win_rate_vs_eth_4h",
    "win_rate_vs_eth_24h",
    "win_rate_vs_eth_72h",
    "best_case_title",
    "best_case_abnormal_vs_btc_24h",
    "worst_case_title",
    "worst_case_abnormal_vs_btc_24h",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Aggregate event return backtest results.")
    parser.add_argument(
        "--input", default=str(ROOT / "results" / "event_price_backfill.csv")
    )
    parser.add_argument(
        "--output", default=str(ROOT / "results" / "event_backtest_summary.csv")
    )
    parser.add_argument(
        "--quality-input", default=str(ROOT / "results" / "event_quality_report.csv")
    )
    parser.add_argument(
        "--direction-output",
        default=str(ROOT / "results" / "event_backtest_summary_by_direction.csv"),
    )
    return parser.parse_args()


def normalize_path(path_value: str) -> Path:
    path = Path(path_value)
    if not path.is_absolute():
        path = ROOT / path
    return path


def ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def mean_positive(series: pd.Series):
    clean = series.dropna()
    if clean.empty:
        return ""
    return float((clean > 0).mean())


def best_worst_titles(group: pd.DataFrame):
    clean = group.dropna(subset=["abnormal_vs_btc_24h"])
    if clean.empty:
        return "", "", "", ""
    best_idx = clean["abnormal_vs_btc_24h"].idxmax()
    worst_idx = clean["abnormal_vs_btc_24h"].idxmin()
    best = clean.loc[best_idx]
    worst = clean.loc[worst_idx]
    return (
        best.get("title", ""),
        float(best["abnormal_vs_btc_24h"]),
        worst.get("title", ""),
        float(worst["abnormal_vs_btc_24h"]),
    )


def merge_quality_report(df: pd.DataFrame, quality_path: Path) -> pd.DataFrame:
    if not quality_path.exists():
        logging.info("quality report not found; using status=ok/partial fallback")
        df["quality_status"] = ""
        return df

    quality = pd.read_csv(quality_path, dtype=str).fillna("")
    quality_columns = ["event_id", "quality_status", "quality_flags"]
    available_columns = [column for column in quality_columns if column in quality.columns]
    if "event_id" not in available_columns:
        logging.warning("quality report has no event_id column; using fallback")
        df["quality_status"] = ""
        return df

    quality = quality[available_columns].drop_duplicates(subset=["event_id"], keep="last")
    merged = df.merge(quality, on="event_id", how="left", suffixes=("", "_quality"))
    merged["quality_status"] = merged["quality_status"].fillna("")
    return merged


def is_usable(df: pd.DataFrame) -> pd.Series:
    base = df["status"].isin(["ok", "partial"])
    if "quality_status" not in df.columns or (df["quality_status"].fillna("") == "").all():
        return base
    return base & (df["quality_status"] != "fail")


def build_summary(df: pd.DataFrame, group_column: str) -> pd.DataFrame:
    numeric_columns = []
    for window in WINDOWS:
        numeric_columns.extend(
            [
                f"asset_return_{window}",
                f"abnormal_vs_btc_{window}",
                f"abnormal_vs_eth_{window}",
            ]
        )

    for column in numeric_columns:
        if column in df.columns:
            df[column] = pd.to_numeric(df[column], errors="coerce")

    usable_mask = is_usable(df)
    rows = []
    output_columns = [group_column] + METRIC_COLUMNS

    for group_value, full_group in df.groupby(group_column, dropna=False):
        usable = full_group[usable_mask.loc[full_group.index]].copy()
        row = {column: "" for column in output_columns}
        row[group_column] = group_value
        row["sample_count"] = int(len(full_group))
        row["valid_sample_count"] = int(len(usable))
        row["skipped_sample_count"] = int((full_group["status"] == "skipped").sum())
        row["failed_quality_count"] = int(
            (full_group.get("quality_status", pd.Series("", index=full_group.index)) == "fail").sum()
        )
        row["warning_quality_count"] = int(
            (full_group.get("quality_status", pd.Series("", index=full_group.index)) == "warning").sum()
        )

        for window in WINDOWS:
            row[f"avg_asset_return_{window}"] = usable[f"asset_return_{window}"].mean()
            row[f"avg_abnormal_vs_btc_{window}"] = usable[
                f"abnormal_vs_btc_{window}"
            ].mean()
            row[f"avg_abnormal_vs_eth_{window}"] = usable[
                f"abnormal_vs_eth_{window}"
            ].mean()
            row[f"win_rate_vs_btc_{window}"] = mean_positive(
                usable[f"abnormal_vs_btc_{window}"]
            )
            row[f"win_rate_vs_eth_{window}"] = mean_positive(
                usable[f"abnormal_vs_eth_{window}"]
            )

        row["median_abnormal_vs_btc_24h"] = usable["abnormal_vs_btc_24h"].median()
        row["median_abnormal_vs_eth_24h"] = usable["abnormal_vs_eth_24h"].median()

        (
            row["best_case_title"],
            row["best_case_abnormal_vs_btc_24h"],
            row["worst_case_title"],
            row["worst_case_abnormal_vs_btc_24h"],
        ) = best_worst_titles(usable)
        rows.append(row)

    return pd.DataFrame(rows, columns=output_columns)


def main() -> int:
    args = parse_args()
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        datefmt="%H:%M:%S",
    )

    input_path = normalize_path(args.input)
    output_path = normalize_path(args.output)
    quality_path = normalize_path(args.quality_input)
    direction_output_path = normalize_path(args.direction_output)

    if not input_path.exists():
        logging.error("input file not found: %s", input_path)
        return 1

    df = pd.read_csv(input_path)
    df = merge_quality_report(df, quality_path)
    summary = build_summary(df, "event_type")
    direction_summary = build_summary(df, "direction_hint")
    ensure_parent(output_path)
    summary.to_csv(output_path, index=False)
    ensure_parent(direction_output_path)
    direction_summary.to_csv(direction_output_path, index=False)
    logging.info("wrote %s rows to %s", len(summary), output_path)
    logging.info("wrote %s rows to %s", len(direction_summary), direction_output_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
