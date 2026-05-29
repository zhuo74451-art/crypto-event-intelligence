import argparse
import logging
import subprocess
import sys
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run optional v0.4.2 24h-only quick backtest.")
    parser.add_argument("--input", default=str(ROOT / "data" / "event_candidates_real_200_review_suggested.csv"))
    parser.add_argument("--limit", type=int, default=50)
    return parser.parse_args()


def normalize_path(path_value: str) -> Path:
    path = Path(path_value)
    if not path.is_absolute():
        path = ROOT / path
    return path


def run(command: list) -> int:
    return subprocess.run(command, cwd=ROOT, text=True).returncode


def main() -> int:
    args = parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", datefmt="%H:%M:%S")
    input_path = normalize_path(args.input)
    if not input_path.exists():
        logging.error("input not found: %s", input_path)
        return 1

    temp_mature = ROOT / "data" / "event_candidates_real_24h_only_suggested.csv"
    auto_review = ROOT / "data" / "event_candidates_real_24h_only_auto50.csv"
    events_output = ROOT / "data" / "events_real_24h_only_50.csv"
    backfill = ROOT / "results" / "v042_24h_only_event_price_backfill.csv"
    quality = ROOT / "results" / "v042_24h_only_event_quality_report.csv"
    summary = ROOT / "results" / "v042_24h_only_backtest_summary.csv"
    direction = ROOT / "results" / "v042_24h_only_backtest_summary_by_direction.csv"
    findings = ROOT / "results" / "v042_24h_only_backtest_findings.md"

    if run([
        sys.executable, "scripts/filter_mature_candidates.py",
        "--input", str(input_path),
        "--output", str(temp_mature),
        "--summary", str(ROOT / "results" / "v042_24h_only_filter_summary.csv"),
        "--min-age-hours", "32",
    ]) != 0:
        return 1

    df = pd.read_csv(temp_mature, dtype=str).fillna("")
    df["event_age_hours_num"] = pd.to_numeric(df.get("event_age_hours", ""), errors="coerce")
    df = df[(df["event_age_hours_num"] >= 32) & (df["event_age_hours_num"] < 80)].drop(columns=["event_age_hours_num"])
    temp_mature.to_csv(temp_mature, index=False)
    df.to_csv(temp_mature, index=False)

    steps = [
        [sys.executable, "scripts/build_stratified_auto_review.py", "--input", str(temp_mature), "--output", str(auto_review), "--summary", str(ROOT / "results" / "v042_24h_only_selection_summary.csv"), "--limit", str(args.limit)],
        [sys.executable, "scripts/build_events_from_review.py", "--input", str(auto_review), "--output", str(events_output), "--limit", str(args.limit)],
        [sys.executable, "scripts/backfill_event_prices.py", "--input", str(events_output), "--output", str(backfill), "--limit", str(args.limit), "--quality-output", str(quality)],
        [sys.executable, "scripts/validate_backfill_results.py", "--input", str(backfill), "--output", str(quality)],
        [sys.executable, "scripts/analyze_event_returns.py", "--input", str(backfill), "--output", str(summary), "--quality-input", str(quality), "--direction-output", str(direction)],
        [sys.executable, "scripts/summarize_backtest_findings.py", "--backfill", str(backfill), "--quality", str(quality), "--summary", str(summary), "--output", str(findings)],
    ]
    for step in steps:
        if run(step) != 0:
            return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
