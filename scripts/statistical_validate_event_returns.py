import argparse
import logging
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
WINDOWS = ["1h", "4h", "24h", "72h"]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run v0.5 statistical validation for event abnormal returns."
    )
    parser.add_argument(
        "--backfill",
        default=str(ROOT / "results" / "v043_older_mature50_event_price_backfill.csv"),
    )
    parser.add_argument(
        "--quality",
        default=str(ROOT / "results" / "v043_older_mature50_event_quality_report.csv"),
    )
    parser.add_argument(
        "--output",
        default=str(ROOT / "results" / "v05_event_return_statistical_validation.csv"),
    )
    parser.add_argument(
        "--report",
        default=str(ROOT / "results" / "v05_event_return_statistical_validation.md"),
    )
    parser.add_argument("--group-column", default="event_type")
    parser.add_argument("--metric-prefix", default="abnormal_vs_btc")
    parser.add_argument("--min-samples", type=int, default=10)
    parser.add_argument("--bootstrap", type=int, default=2000)
    parser.add_argument("--permutations", type=int, default=5000)
    parser.add_argument("--seed", type=int, default=42)
    return parser.parse_args()


def normalize_path(path_value: str) -> Path:
    path = Path(path_value)
    if not path.is_absolute():
        path = ROOT / path
    return path


def merge_quality(backfill: pd.DataFrame, quality_path: Path) -> pd.DataFrame:
    if not quality_path.exists():
        backfill["quality_status"] = ""
        return backfill

    quality = pd.read_csv(quality_path, dtype=str).fillna("")
    keep = [col for col in ["event_id", "quality_status", "quality_flags"] if col in quality.columns]
    if "event_id" not in keep:
        backfill["quality_status"] = ""
        return backfill
    quality = quality[keep].drop_duplicates(subset=["event_id"], keep="last")
    merged = backfill.merge(quality, on="event_id", how="left")
    merged["quality_status"] = merged["quality_status"].fillna("")
    return merged


def usable_rows(df: pd.DataFrame) -> pd.Series:
    base = df["status"].isin(["ok", "partial"])
    if "quality_status" in df.columns and not (df["quality_status"].fillna("") == "").all():
        return base & (df["quality_status"] != "fail")
    return base


def bootstrap_ci(values: np.ndarray, rng: np.random.Generator, rounds: int) -> tuple[float, float]:
    if len(values) < 2 or rounds <= 0:
        mean_value = float(np.mean(values)) if len(values) else math.nan
        return mean_value, mean_value
    samples = rng.choice(values, size=(rounds, len(values)), replace=True)
    means = samples.mean(axis=1)
    low, high = np.percentile(means, [2.5, 97.5])
    return float(low), float(high)


def sign_flip_p_value(values: np.ndarray, rng: np.random.Generator, rounds: int) -> float:
    if len(values) == 0:
        return math.nan
    observed = abs(float(np.mean(values)))
    if observed == 0:
        return 1.0
    if rounds <= 0:
        return math.nan
    signs = rng.choice([-1, 1], size=(rounds, len(values)), replace=True)
    null_means = np.abs((signs * values).mean(axis=1))
    return float((np.sum(null_means >= observed) + 1) / (rounds + 1))


def bh_fdr(p_values: pd.Series) -> pd.Series:
    numeric = pd.to_numeric(p_values, errors="coerce")
    result = pd.Series(np.nan, index=p_values.index, dtype=float)
    valid = numeric.dropna()
    m = len(valid)
    if m == 0:
        return result
    ordered = valid.sort_values(ascending=True)
    adjusted_by_index = {}
    previous = 1.0
    ranked_items = list(enumerate(ordered.items(), start=1))
    for original_rank, (original_idx, original_p) in reversed(ranked_items):
        value = min(previous, float(original_p) * m / original_rank, 1.0)
        adjusted_by_index[original_idx] = value
        previous = value
    for idx, value in adjusted_by_index.items():
        result.loc[idx] = value
    return result


def reliability_label(sample_count: int, min_samples: int, p_value: float, ci_low: float, ci_high: float) -> str:
    if sample_count < min_samples:
        return "too_small"
    if pd.isna(p_value) or pd.isna(ci_low) or pd.isna(ci_high):
        return "insufficient_data"
    if ci_low > 0 or ci_high < 0:
        return "directional_candidate"
    return "not_significant"


def build_validation(df: pd.DataFrame, args: argparse.Namespace) -> pd.DataFrame:
    rng = np.random.default_rng(args.seed)
    rows = []
    usable = df[usable_rows(df)].copy()

    for window in WINDOWS:
        col = f"{args.metric_prefix}_{window}"
        if col not in usable.columns:
            continue
        usable[col] = pd.to_numeric(usable[col], errors="coerce")

        for group_value, group in usable.groupby(args.group_column, dropna=False):
            values = group[col].dropna().to_numpy(dtype=float)
            sample_count = int(len(values))
            if sample_count == 0:
                continue
            ci_low, ci_high = bootstrap_ci(values, rng, args.bootstrap)
            p_value = sign_flip_p_value(values, rng, args.permutations)
            rows.append(
                {
                    "group_column": args.group_column,
                    "group_value": group_value,
                    "window": window,
                    "metric": col,
                    "sample_count": sample_count,
                    "mean": float(np.mean(values)),
                    "median": float(np.median(values)),
                    "std": float(np.std(values, ddof=1)) if sample_count > 1 else 0.0,
                    "win_rate": float(np.mean(values > 0)),
                    "bootstrap_ci_low": ci_low,
                    "bootstrap_ci_high": ci_high,
                    "permutation_p_value": p_value,
                    "passes_min_sample": sample_count >= args.min_samples,
                    "ci_excludes_zero": bool(ci_low > 0 or ci_high < 0),
                }
            )

    result = pd.DataFrame(rows)
    if result.empty:
        return result

    m = len(result)
    result["bonferroni_p_value"] = (
        pd.to_numeric(result["permutation_p_value"], errors="coerce") * m
    ).clip(upper=1.0)
    result["fdr_bh_p_value"] = bh_fdr(result["permutation_p_value"])
    result["significant_fdr_0_05"] = result["fdr_bh_p_value"] <= 0.05
    result["reliability_label"] = result.apply(
        lambda row: reliability_label(
            int(row["sample_count"]),
            args.min_samples,
            row["permutation_p_value"],
            row["bootstrap_ci_low"],
            row["bootstrap_ci_high"],
        ),
        axis=1,
    )
    return result


def markdown_table(df: pd.DataFrame, columns: list[str], max_rows: int | None = None) -> str:
    if max_rows is not None:
        df = df.head(max_rows)
    if df.empty:
        return "_No rows._"
    lines = ["| " + " | ".join(columns) + " |", "| " + " | ".join(["---"] * len(columns)) + " |"]
    for _, row in df.iterrows():
        cells = []
        for col in columns:
            value = row.get(col, "")
            if isinstance(value, float):
                cells.append(f"{value:.6f}")
            else:
                cells.append(str(value).replace("\n", " ")[:160])
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines)


def write_report(result: pd.DataFrame, output_path: Path, args: argparse.Namespace) -> None:
    lines = [
        "# v0.5 Event Return Statistical Validation",
        "",
        "This report tests whether grouped abnormal returns look distinguishable from zero.",
        "It is a research validation step, not a trading signal.",
        "",
        "## Method",
        f"- Group column: `{args.group_column}`",
        f"- Metric prefix: `{args.metric_prefix}`",
        f"- Minimum sample threshold: `{args.min_samples}`",
        f"- Bootstrap rounds: `{args.bootstrap}`",
        f"- Sign-flip permutation rounds: `{args.permutations}`",
        "- Multiple-testing correction: Bonferroni and Benjamini-Hochberg FDR.",
        "",
    ]

    if result.empty:
        lines.extend(["## Result", "No usable rows found."])
        output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return

    candidates = result[
        (result["passes_min_sample"])
        & (result["ci_excludes_zero"])
        & (result["fdr_bh_p_value"] <= 0.05)
    ].sort_values(["window", "fdr_bh_p_value"])
    weak = result[result["reliability_label"] == "directional_candidate"].sort_values(
        ["window", "permutation_p_value"]
    )
    small = result[result["sample_count"] < args.min_samples].sort_values(
        ["window", "sample_count"], ascending=[True, False]
    )

    lines.extend(
        [
            "## FDR-Significant Candidates",
            markdown_table(
                candidates,
                [
                    "group_value",
                    "window",
                    "sample_count",
                    "mean",
                    "bootstrap_ci_low",
                    "bootstrap_ci_high",
                    "permutation_p_value",
                    "fdr_bh_p_value",
                ],
            ),
            "",
            "## Directional Candidates Before FDR",
            markdown_table(
                weak,
                [
                    "group_value",
                    "window",
                    "sample_count",
                    "mean",
                    "bootstrap_ci_low",
                    "bootstrap_ci_high",
                    "permutation_p_value",
                    "reliability_label",
                ],
                20,
            ),
            "",
            "## Small-Sample Buckets",
            markdown_table(
                small,
                ["group_value", "window", "sample_count", "mean", "reliability_label"],
                30,
            ),
            "",
            "## Interpretation Rules",
            "- Buckets below the minimum sample threshold should not be used as conclusions.",
            "- A positive mean without an interval excluding zero is only descriptive.",
            "- A significant raw p-value that fails FDR should be treated as possible multiple-testing noise.",
            "- Event types such as `other` should be split before drawing any research conclusion.",
        ]
    )
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    args = parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", datefmt="%H:%M:%S")

    backfill_path = normalize_path(args.backfill)
    quality_path = normalize_path(args.quality)
    output_path = normalize_path(args.output)
    report_path = normalize_path(args.report)

    if not backfill_path.exists():
        logging.error("backfill file not found: %s", backfill_path)
        return 1

    df = pd.read_csv(backfill_path, dtype=str).fillna("")
    if args.group_column not in df.columns:
        logging.error("group column not found: %s", args.group_column)
        return 1
    df = merge_quality(df, quality_path)
    result = build_validation(df, args)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(output_path, index=False)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    write_report(result, report_path, args)

    logging.info("wrote validation csv: %s", output_path)
    logging.info("wrote validation report: %s", report_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
