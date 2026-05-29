import argparse
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run v0.6 event intake quality pipeline.")
    parser.add_argument(
        "--input",
        default=str(ROOT / "data" / "event_candidates_real_500_older_review_suggested.csv"),
    )
    parser.add_argument("--entity-dictionary", default=str(ROOT / "data" / "entity_dictionary.csv"))
    parser.add_argument("--symbol-map", default=str(ROOT / "data" / "symbol_map.csv"))
    parser.add_argument("--enriched-output", default=str(ROOT / "data" / "event_candidates_v06_enriched.csv"))
    parser.add_argument("--deduped-output", default=str(ROOT / "data" / "event_candidates_v06_deduped.csv"))
    parser.add_argument(
        "--scored-output",
        default=str(ROOT / "data" / "event_candidates_v06_relevance_scored.csv"),
    )
    parser.add_argument("--summary", default=str(ROOT / "results" / "v06_relevance_filter_summary.csv"))
    parser.add_argument("--window-hours", type=int, default=2)
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
                "scripts/enrich_event_entities.py",
                "--input",
                args.input,
                "--entity-dictionary",
                args.entity_dictionary,
                "--symbol-map",
                args.symbol_map,
                "--output",
                args.enriched_output,
            ]
        )
        run(
            [
                sys.executable,
                "scripts/deduplicate_event_candidates.py",
                "--input",
                args.enriched_output,
                "--output",
                args.deduped_output,
                "--window-hours",
                str(args.window_hours),
            ]
        )
        run(
            [
                sys.executable,
                "scripts/filter_research_relevant_events.py",
                "--input",
                args.deduped_output,
                "--output",
                args.scored_output,
                "--summary",
                args.summary,
            ]
        )
    except subprocess.CalledProcessError as exc:
        print(f"v0.6 pipeline failed with exit code {exc.returncode}")
        return exc.returncode
    print("v0.6 event intake quality pipeline complete")
    return 0


if __name__ == "__main__":
    sys.exit(main())
