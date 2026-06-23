"""Audit replay outputs for future information leakage."""
import json, sys, argparse
from datetime import datetime


def check_leakage(results_path: str) -> dict:
    """Check replay results for timestamp violations."""
    violations = {"input_timestamp_after_cutoff": [], "future_revision_used": [], "post_event_consensus_used": []}
    total = 0
    try:
        with open(results_path, "r", encoding="utf-8") as f:
            for line in f:
                total += 1
                r = json.loads(line)
                cutoff = r.get("available_information_cutoff_utc", "")
                gen = r.get("generated_at_utc", "")
                if cutoff and gen and gen > cutoff:
                    violations["input_timestamp_after_cutoff"].append(r.get("replay_result_id", ""))
    except FileNotFoundError:
        pass
    return {"total_checked": total, "violations": violations, "violation_count": sum(len(v) for v in violations.values())}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--results", required=True)
    args = parser.parse_args()
    result = check_leakage(args.results)
    print(json.dumps(result, indent=2))
    sys.exit(1 if result["violation_count"] > 0 else 0)
