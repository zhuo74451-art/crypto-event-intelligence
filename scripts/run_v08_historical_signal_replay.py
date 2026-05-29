import argparse
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run v0.8 historical signal replay backtest.")
    parser.add_argument("--input", default=str(ROOT / "data" / "event_candidates_real_500_older_mature_review_suggested.csv"))
    parser.add_argument("--limit", type=int, default=200)
    parser.add_argument("--mode", choices=["broad", "conservative", "non_btc_single_asset", "non_benchmark_alt"], default="broad")
    parser.add_argument("--symbol-map", default=str(ROOT / "data" / "symbol_map.csv"))
    return parser.parse_args()


def normalize_path(value: str | Path) -> Path:
    path = Path(value)
    if not path.is_absolute():
        path = ROOT / path
    return path


def run_step(name: str, command: list[str]) -> None:
    print(f"[{name}] start")
    result = subprocess.run(command, cwd=ROOT, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"{name} failed with exit code {result.returncode}")
    print(f"[{name}] done")


def main() -> int:
    args = parse_args()
    suffix = f"{args.mode}_{args.limit}"
    review_output = ROOT / f"data/event_candidates_v08_historical_replay_{suffix}.csv"
    events_output = ROOT / f"data/events_v08_historical_replay_{suffix}.csv"
    sample_summary = ROOT / f"results/v08_historical_replay_{suffix}_sample_summary.csv"
    backfill_output = ROOT / f"results/v08_historical_replay_{suffix}_price_backfill.csv"
    quality_output = ROOT / f"results/v08_historical_replay_{suffix}_quality_report.csv"
    summary_output = ROOT / f"results/v08_historical_replay_{suffix}_backtest_summary.csv"
    direction_output = ROOT / f"results/v08_historical_replay_{suffix}_backtest_summary_by_direction.csv"
    findings_output = ROOT / f"results/v08_historical_replay_{suffix}_findings.md"

    steps = [
        (
            "build replay sample",
            [
                sys.executable,
                "scripts/build_historical_signal_replay_sample.py",
                "--input",
                str(normalize_path(args.input)),
                "--output",
                str(review_output),
                "--summary",
                str(sample_summary),
                "--limit",
                str(args.limit),
                "--mode",
                args.mode,
            ],
        ),
        (
            "build events",
            [
                sys.executable,
                "scripts/build_events_from_review.py",
                "--input",
                str(review_output),
                "--output",
                str(events_output),
                "--limit",
                str(args.limit),
                "--symbol-map",
                str(normalize_path(args.symbol_map)),
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
                str(normalize_path(args.symbol_map)),
                "--quality-output",
                str(quality_output),
            ],
        ),
        (
            "validate quality",
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
            "analyze returns",
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
        (
            "summarize replay",
            [
                sys.executable,
                "scripts/summarize_historical_signal_replay.py",
                "--backfill",
                str(backfill_output),
                "--quality",
                str(quality_output),
                "--summary",
                str(summary_output),
                "--output",
                str(findings_output),
            ],
        ),
    ]

    try:
        for name, command in steps:
            run_step(name, command)
    except Exception as exc:
        print(f"failed: {exc}")
        return 1

    print(f"review_output={review_output}")
    print(f"events_output={events_output}")
    print(f"backfill_output={backfill_output}")
    print(f"quality_output={quality_output}")
    print(f"findings_output={findings_output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
