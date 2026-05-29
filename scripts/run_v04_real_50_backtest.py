import argparse
import logging
import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the v0.4 reviewed real 50-sample backtest pipeline.")
    parser.add_argument("--review-input", default=str(ROOT / "data" / "event_candidates_real_200_review_auto50.csv"))
    parser.add_argument("--limit", type=int, default=50)
    parser.add_argument("--symbol-map", default=str(ROOT / "data" / "symbol_map.csv"))
    return parser.parse_args()


def normalize_path(path_value: str) -> Path:
    path = Path(path_value)
    if not path.is_absolute():
        path = ROOT / path
    return path


def run_step(name: str, command: list) -> None:
    logging.info("starting step: %s", name)
    result = subprocess.run(command, cwd=ROOT, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"{name} failed with exit code {result.returncode}")
    logging.info("finished step: %s", name)


def copy_if_exists(src: Path, dst: Path) -> None:
    if src.exists():
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, dst)


def main() -> int:
    args = parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", datefmt="%H:%M:%S")

    review_input = normalize_path(args.review_input)
    symbol_map = normalize_path(args.symbol_map)
    events_output = ROOT / "data" / "events_raw_real_50.csv"
    backfill_output = ROOT / "results" / "v04_real_event_price_backfill_50.csv"
    quality_output = ROOT / "results" / "v04_real_event_quality_report_50.csv"
    summary_output = ROOT / "results" / "v04_real_event_backtest_summary_50.csv"
    direction_output = ROOT / "results" / "v04_real_event_backtest_summary_by_direction_50.csv"

    if not review_input.exists():
        logging.error("review input not found: %s", review_input)
        return 1

    steps = [
        (
            "build reviewed events",
            [
                sys.executable,
                "scripts/build_events_from_review.py",
                "--input",
                str(review_input),
                "--output",
                str(events_output),
                "--limit",
                str(args.limit),
                "--symbol-map",
                str(symbol_map),
            ],
        ),
        (
            "backfill prices",
            [
                sys.executable,
                "scripts/backfill_event_prices.py",
                "--input",
                str(events_output),
                "--output",
                str(backfill_output),
                "--limit",
                str(args.limit),
                "--symbol-map",
                str(symbol_map),
                "--quality-output",
                str(quality_output),
            ],
        ),
        (
            "validate backfill results",
            [
                sys.executable,
                "scripts/validate_backfill_results.py",
                "--input",
                str(backfill_output),
                "--output",
                str(quality_output),
            ],
        ),
        (
            "analyze event returns",
            [
                sys.executable,
                "scripts/analyze_event_returns.py",
                "--input",
                str(backfill_output),
                "--output",
                str(summary_output),
                "--quality-input",
                str(quality_output),
                "--direction-output",
                str(direction_output),
            ],
        ),
    ]

    try:
        for name, command in steps:
            run_step(name, command)
    except Exception as exc:
        logging.error("v0.4 real 50 pipeline failed: %s", exc)
        return 1

    copy_if_exists(backfill_output, ROOT / "results" / "v041_auto50_event_price_backfill.csv")
    copy_if_exists(quality_output, ROOT / "results" / "v041_auto50_event_quality_report.csv")
    copy_if_exists(summary_output, ROOT / "results" / "v041_auto50_event_backtest_summary.csv")
    copy_if_exists(direction_output, ROOT / "results" / "v041_auto50_event_backtest_summary_by_direction.csv")

    logging.info("v0.4 real 50 pipeline completed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
