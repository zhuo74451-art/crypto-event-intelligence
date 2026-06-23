"""Unified entry point for Lane C pipeline."""
import json, sys, argparse, os
from datetime import datetime, timezone
sys.path.insert(0, ".")
from market_radar.intelligence.strategy_replay.replay_engine import run_batch_replay
from market_radar.intelligence.strategy_replay.strategies import ALL_MACRO_STRATEGIES


def run_pipeline(macro_events: str, market_windows: str = None, reaction_labels: str = None,
                 output_dir: str = "data/intelligence/strategy_replay", resume: str = None):
    os.makedirs(f"{output_dir}/replay_results", exist_ok=True)
    os.makedirs(f"{output_dir}/hypotheses", exist_ok=True)
    os.makedirs(f"{output_dir}/abstentions", exist_ok=True)
    os.makedirs(f"{output_dir}/kernel_packages", exist_ok=True)
    os.makedirs(f"{output_dir}/definitions", exist_ok=True)

    # Build definitions
    from .build_strategy_definitions import build as build_defs
    build_defs(f"{output_dir}/definitions/strategy_definitions_v1.json")

    strategies = list(ALL_MACRO_STRATEGIES.values())
    events = []
    with open(macro_events, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                events.append(json.loads(line))

    result = run_batch_replay(events=events, strategies=strategies, resume_from=resume)

    # Write all outputs
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

    print(f"Pipeline complete. Processed: {result['processed_count']}")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--macro-events", required=True)
    parser.add_argument("--market-windows", default=None)
    parser.add_argument("--reaction-labels", default=None)
    parser.add_argument("--output-dir", default="data/intelligence/strategy_replay")
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()
    run_pipeline(args.macro_events, args.market_windows, args.reaction_labels, args.output_dir,
                 resume="__resume__" if args.resume else None)
