"""Generate coverage report from replay outputs."""
import json, sys, argparse
from collections import Counter


def generate(results_path: str, hypotheses_path: str, abstentions_path: str, output_path: str):
    report = {"events_by_family": {}, "strategy_state_distribution": {}, "total_results": 0, "total_hypotheses": 0}

    try:
        with open(results_path, "r", encoding="utf-8") as f:
            states = Counter()
            for line in f:
                r = json.loads(line)
                states[r.get("strategy_state", "unknown")] += 1
                fam = r.get("strategy_id", "unknown")
                report["events_by_family"][fam] = report["events_by_family"].get(fam, 0) + 1
                report["total_results"] += 1
            report["strategy_state_distribution"] = dict(states)
    except FileNotFoundError:
        pass

    try:
        with open(hypotheses_path, "r", encoding="utf-8") as f:
            horizons = Counter()
            for line in f:
                h = json.loads(line)
                horizons[h.get("time_horizon", "unknown")] += 1
                report["total_hypotheses"] += 1
            report["hypotheses_by_horizon"] = dict(horizons)
    except FileNotFoundError:
        pass

    try:
        with open(abstentions_path, "r", encoding="utf-8") as f:
            reasons = Counter()
            count = 0
            for line in f:
                a = json.loads(line)
                for r in a.get("reason_codes", []):
                    reasons[r] += 1
                count += 1
            report["abstention_count"] = count
            report["abstention_reason_distribution"] = dict(reasons)
    except FileNotFoundError:
        pass

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    print(f"Report written to {output_path}")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--results", default="data/intelligence/strategy_replay/replay_results/strategy_replay_results_v1.jsonl")
    parser.add_argument("--hypotheses", default="data/intelligence/strategy_replay/hypotheses/strategy_hypotheses_v1.jsonl")
    parser.add_argument("--abstentions", default="data/intelligence/strategy_replay/abstentions/abstention_records_v1.jsonl")
    parser.add_argument("--output", default="data/intelligence/strategy_replay/reports/coverage_report_v1.json")
    args = parser.parse_args()
    generate(args.results, args.hypotheses, args.abstentions, args.output)
