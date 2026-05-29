import argparse
import logging
import sys
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
WINDOWS = ["1h", "4h", "24h", "72h"]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create a markdown findings report for a backtest run.")
    parser.add_argument("--backfill", default=str(ROOT / "results" / "v04_real_event_price_backfill_50.csv"))
    parser.add_argument("--quality", default=str(ROOT / "results" / "v04_real_event_quality_report_50.csv"))
    parser.add_argument("--summary", default=str(ROOT / "results" / "v04_real_event_backtest_summary_50.csv"))
    parser.add_argument("--output", default=str(ROOT / "results" / "v041_auto50_backtest_findings.md"))
    parser.add_argument("--title", default="v0.4.1 Auto50 Backtest Findings")
    return parser.parse_args()


def normalize_path(path_value: str) -> Path:
    path = Path(path_value)
    if not path.is_absolute():
        path = ROOT / path
    return path


def count_table(series: pd.Series) -> str:
    counts = series.fillna("").astype(str).value_counts(dropna=False)
    lines = ["| value | count |", "|---|---:|"]
    for value, count in counts.items():
        lines.append(f"| {value or '(blank)'} | {count} |")
    return "\n".join(lines)


def markdown_table(df: pd.DataFrame, columns: list, max_rows: int | None = None) -> str:
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
                cells.append(str(value).replace("\n", " ")[:180])
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines)


def numeric(df: pd.DataFrame, columns: list) -> pd.DataFrame:
    for col in columns:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


def main() -> int:
    args = parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", datefmt="%H:%M:%S")
    backfill_path = normalize_path(args.backfill)
    quality_path = normalize_path(args.quality)
    summary_path = normalize_path(args.summary)
    output_path = normalize_path(args.output)

    for path in [backfill_path, quality_path, summary_path]:
        if not path.exists():
            logging.error("required input not found: %s", path)
            return 1

    backfill = pd.read_csv(backfill_path, dtype=str).fillna("")
    quality = pd.read_csv(quality_path, dtype=str).fillna("")
    summary = pd.read_csv(summary_path, dtype=str).fillna("")

    metric_cols = [f"abnormal_vs_btc_{window}" for window in WINDOWS]
    backfill = numeric(backfill, metric_cols)
    for col in [f"avg_abnormal_vs_btc_{w}" for w in WINDOWS] + [f"win_rate_vs_btc_{w}" for w in WINDOWS]:
        if col in summary.columns:
            summary[col] = pd.to_numeric(summary[col], errors="coerce")

    best = backfill.dropna(subset=["abnormal_vs_btc_24h"]).sort_values("abnormal_vs_btc_24h", ascending=False)
    worst = backfill.dropna(subset=["abnormal_vs_btc_24h"]).sort_values("abnormal_vs_btc_24h", ascending=True)
    suspicious = quality[quality.get("quality_flags", "").astype(str).str.contains("suspicious_extreme_return", na=False)]

    lines = [
        f"# {args.title}",
        "",
        f"- Total samples: {len(backfill)}",
        "",
        "## Backfill Status",
        count_table(backfill.get("status", pd.Series("", index=backfill.index))),
        "",
        "## Quality Status",
        count_table(quality.get("quality_status", pd.Series("", index=quality.index))),
        "",
        "## Samples By Event Type",
        count_table(backfill.get("event_type", pd.Series("", index=backfill.index))),
        "",
        "## Event Type Abnormal Return",
        markdown_table(
            summary,
            ["event_type"] + [f"avg_abnormal_vs_btc_{w}" for w in WINDOWS],
        ),
        "",
        "## Event Type Win Rate",
        markdown_table(
            summary,
            ["event_type"] + [f"win_rate_vs_btc_{w}" for w in WINDOWS],
        ),
        "",
        "## Best 10 Events By 24h Abnormal Vs BTC",
        markdown_table(best, ["event_id", "title", "event_type", "asset_symbol", "abnormal_vs_btc_24h"], 10),
        "",
        "## Worst 10 Events By 24h Abnormal Vs BTC",
        markdown_table(worst, ["event_id", "title", "event_type", "asset_symbol", "abnormal_vs_btc_24h"], 10),
        "",
        "## Suspicious Extreme Return Samples",
        markdown_table(suspicious, ["event_id", "title", "asset_symbol", "quality_flags"], None),
        "",
        "## Preliminary Notes",
    ]

    if not summary.empty and "avg_abnormal_vs_btc_24h" in summary.columns:
        valid_summary = summary.dropna(subset=["avg_abnormal_vs_btc_24h"])
        if not valid_summary.empty:
            best_type = valid_summary.sort_values("avg_abnormal_vs_btc_24h", ascending=False).iloc[0]
            lines.append(f"- Strongest 24h event_type in this run: {best_type.get('event_type', '')}.")
    if "valid_sample_count" in summary.columns:
        small = summary[pd.to_numeric(summary["valid_sample_count"], errors="coerce").fillna(0) < 5]
        if not small.empty:
            lines.append("- Event types with fewer than 5 valid samples are too small to judge: " + ", ".join(small["event_type"].astype(str).tolist()) + ".")
    if not suspicious.empty:
        lines.append("- Review suspicious_extreme_return rows before trusting aggregate results.")
    if suspicious.empty:
        lines.append("- No suspicious_extreme_return rows were flagged.")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    logging.info("wrote findings to %s", output_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
