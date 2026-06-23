"""Run baseline replays across all events."""
import json, sys, argparse
sys.path.insert(0, ".")
from market_radar.intelligence.strategy_replay.baselines import BASELINE_DEFINITIONS, run_baseline_replay


def run(macro_events_path: str, output_dir: str):
    events = []
    with open(macro_events_path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                events.append(json.loads(line))

    results = []
    for event in events:
        for base_id in BASELINE_DEFINITIONS:
            r = run_baseline_replay(base_id, event)
            results.append(r)

    with open(f"{output_dir}/baselines/baseline_replay_results_v1.jsonl", "w", encoding="utf-8") as f:
        for r in results:
            f.write(json.dumps(r.__dict__, ensure_ascii=False) + "\n")
    print(f"Written {len(results)} baseline results")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--macro-events", required=True)
    parser.add_argument("--output-dir", default="data/intelligence/strategy_replay")
    args = parser.parse_args()
    run(args.macro_events, args.output_dir)
