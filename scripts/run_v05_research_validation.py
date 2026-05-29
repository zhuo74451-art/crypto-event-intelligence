import argparse
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run v0.5 research validation steps.")
    parser.add_argument(
        "--backfill",
        default=str(ROOT / "results" / "v043_older_mature50_event_price_backfill.csv"),
    )
    parser.add_argument(
        "--quality",
        default=str(ROOT / "results" / "v043_older_mature50_event_quality_report.csv"),
    )
    parser.add_argument(
        "--stats-output",
        default=str(ROOT / "results" / "v05_event_return_statistical_validation.csv"),
    )
    parser.add_argument(
        "--stats-report",
        default=str(ROOT / "results" / "v05_event_return_statistical_validation.md"),
    )
    parser.add_argument(
        "--other-output",
        default=str(ROOT / "data" / "v05_other_event_review.csv"),
    )
    return parser.parse_args()


def run(cmd: list[str]) -> None:
    print("running: " + " ".join(cmd))
    subprocess.run(cmd, cwd=ROOT, check=True)


def main() -> int:
    args = parse_args()
    try:
        run(
            [
                sys.executable,
                "scripts/statistical_validate_event_returns.py",
                "--backfill",
                args.backfill,
                "--quality",
                args.quality,
                "--output",
                args.stats_output,
                "--report",
                args.stats_report,
            ]
        )
        run(
            [
                sys.executable,
                "scripts/export_other_review.py",
                "--input",
                args.backfill,
                "--output",
                args.other_output,
            ]
        )
    except subprocess.CalledProcessError as exc:
        print(f"v0.5 validation failed with exit code {exc.returncode}")
        return exc.returncode
    print("v0.5 validation complete")
    return 0


if __name__ == "__main__":
    sys.exit(main())
