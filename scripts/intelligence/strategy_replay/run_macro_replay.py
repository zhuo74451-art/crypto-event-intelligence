"""Run macro replay on cached Lane A/B inputs."""
import json, sys, argparse
from datetime import datetime, timezone
sys.path.insert(0, ".")
from market_radar.intelligence.strategy_replay.replay_engine import run_batch_replay
from market_radar.intelligence.strategy_replay.strategies import ALL_MACRO_STRATEGIES


def run(macro_path: str, output_dir: str, resume: str = None):
    strategies = list(ALL_MACRO_STRATEGIES.values())
    events = []
    try:
        with open(macro_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    events.append(json.loads(line))
    except FileNotFoundError:
        print(f"File not found: {macro_path}")
        return

    result = run_batch_replay(events=events, strategies=strategies, resume_from=resume)

    for r in result.get("results", []):
        with open(f"{output_dir}/replay_results/strategy_replay_results_v1.jsonl", "a", encoding="utf-8") as f:
            f.write(json.dumps(r.__dict__, ensure_ascii=False) + "\n")
    for h in result.get("hypotheses", []):
        with open(f"{output_dir}/hypotheses/strategy_hypotheses_v1.jsonl", "a", encoding="utf-8") as f:
            f.write(json.dumps(h.__dict__, ensure_ascii=False) + "\n")
    for a in result.get("abstentions", []):
        with open(f"{output_dir}/abstentions/abstention_records_v1.jsonl", "a", encoding="utf-8") as f:
            f.write(json.dumps(a.__dict__, ensure_ascii=False) + "\n")
    for kp in result.get("kernel_packages", []):
        with open(f"{output_dir}/kernel_packages/kernel_input_packages_v1.jsonl", "a", encoding="utf-8") as f:
            f.write(json.dumps(kp.__dict__, ensure_ascii=False) + "\n")

    print(f"Processed: {result['processed_count']}, Skipped: {result['skipped_count']}")
    print(f"Results: {len(result['results'])}, Hypotheses: {len(result['hypotheses'])}")
    print(f"Abstentions: {len(result['abstentions'])}, Kernel packages: {len(result['kernel_packages'])}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--macro-events", required=True)
    parser.add_argument("--output-dir", default="data/intelligence/strategy_replay")
    parser.add_argument("--resume", default=None)
    args = parser.parse_args()
    run(args.macro_events, args.output_dir, args.resume)
