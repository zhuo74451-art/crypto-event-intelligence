import argparse
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run v0.8.1 source quality/readiness reports.")
    parser.add_argument("--candidates", default=str(ROOT / "data" / "event_candidates_real_500_older_v081_review_suggested.csv"))
    parser.add_argument("--backfill", default=str(ROOT / "results" / "v08_historical_replay_conservative_120_price_backfill.csv"))
    parser.add_argument("--quality", default=str(ROOT / "results" / "v08_historical_replay_conservative_120_quality_report.csv"))
    return parser.parse_args()


def run_step(name: str, command: list[str]) -> None:
    print(f"[{name}] start")
    result = subprocess.run(command, cwd=ROOT, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"{name} failed with exit code {result.returncode}")
    print(f"[{name}] done")


def main() -> int:
    args = parse_args()
    py = sys.executable
    steps = [
        (
            "fetch CoinMarketCap token unlock calendar",
            [
                py,
                "scripts/fetch_coinmarketcap_token_unlocks.py",
                "--output",
                "data/token_unlock_calendar_cmc.csv",
                "--raw-output",
                "data/token_unlock_calendar_cmc_raw.json",
                "--summary",
                "results/v081_cmc_token_unlock_fetch_summary.csv",
                "--limit",
                "500",
                "--include-small-unlocks",
                "true",
            ],
        ),
        (
            "token unlock calendar quality",
            [
                py,
                "scripts/build_token_unlock_calendar_quality_report.py",
                "--input",
                "data/token_unlock_calendar_cmc.csv",
                "--output",
                "results/v081_cmc_token_unlock_quality_report.md",
                "--summary",
                "results/v081_cmc_token_unlock_quality_summary.csv",
                "--require-symbol-map",
                "false",
                "--require-amount-usd",
                "false",
            ],
        ),
        (
            "CEX netflow baseline report",
            [py, "scripts/build_cex_netflow_baseline_report.py"],
        ),
        (
            "Hyperliquid state history report",
            [py, "scripts/build_hyperliquid_state_history_report.py"],
        ),
        (
            "historical source usefulness",
            [
                py,
                "scripts/build_historical_source_usefulness_from_backtest.py",
                "--backfill",
                args.backfill,
                "--quality",
                args.quality,
                "--by-event-type",
                "results/v081_historical_source_usefulness_by_event_type.csv",
                "--by-source",
                "results/v081_historical_source_usefulness_by_source.csv",
                "--summary",
                "results/v081_historical_source_usefulness_summary.csv",
                "--output",
                "results/v081_historical_source_usefulness_report.md",
            ],
        ),
        (
            "source readiness",
            [
                py,
                "scripts/build_v08_source_readiness_report.py",
                "--candidates",
                args.candidates,
                "--historical-event-type",
                "results/v081_historical_source_usefulness_by_event_type.csv",
                "--historical-source",
                "results/v081_historical_source_usefulness_by_source.csv",
                "--token-calendar",
                "data/token_unlock_calendar_cmc.csv",
                "--output",
                "results/v081_source_readiness_report.md",
                "--summary",
                "results/v081_source_readiness_summary.csv",
            ],
        ),
    ]
    try:
        for name, command in steps:
            run_step(name, command)
    except Exception as exc:
        print(f"failed: {exc}")
        return 1
    print("v0.8.1 source quality reports completed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
