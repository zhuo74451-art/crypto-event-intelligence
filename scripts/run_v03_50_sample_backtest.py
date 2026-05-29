import argparse
import logging
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the v0.3 reviewed 50-sample backtest pipeline.")
    parser.add_argument(
        "--review-input", default=str(ROOT / "data" / "event_candidates_review.csv")
    )
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
    logging.info("command: %s", " ".join(str(part) for part in command))
    result = subprocess.run(command, cwd=ROOT, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"{name} failed with exit code {result.returncode}")
    logging.info("finished step: %s", name)


def main() -> int:
    args = parse_args()
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        datefmt="%H:%M:%S",
    )

    review_input = normalize_path(args.review_input)
    symbol_map = normalize_path(args.symbol_map)
    events_output = ROOT / "data" / "events_raw_50.csv"
    backfill_output = ROOT / "results" / "v03_event_price_backfill_50.csv"
    quality_output = ROOT / "results" / "v03_event_quality_report_50.csv"
    summary_output = ROOT / "results" / "v03_event_backtest_summary_50.csv"
    direction_output = ROOT / "results" / "v03_event_backtest_summary_by_direction_50.csv"

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
        logging.error("v0.3 pipeline failed: %s", exc)
        return 1

    logging.info("v0.3 pipeline completed")
    logging.info("price backfill: %s", backfill_output)
    logging.info("quality report: %s", quality_output)
    logging.info("summary by event_type: %s", summary_output)
    logging.info("summary by direction: %s", direction_output)
    return 0


if __name__ == "__main__":
    sys.exit(main())
