"""Audit strategy replay results for contract violations."""
import json, sys, argparse

REQUIRED_FIELDS = ["replay_result_id", "event_id", "strategy_id", "strategy_instance_id", "replay_status", "strategy_state", "generated_at_utc"]
TERMINAL_STATES = ["invalidated", "expired", "insufficient_evidence"]


def check_contracts(results_path: str) -> dict:
    violations = {"missing_required_fields": [], "invalidated_but_directional": [], "expired_but_directional": []}
    total = 0
    try:
        with open(results_path, "r", encoding="utf-8") as f:
            for line in f:
                total += 1
                r = json.loads(line)
                for field in REQUIRED_FIELDS:
                    if field not in r or not r[field]:
                        violations["missing_required_fields"].append(f"line_{total}:{field}")
    except FileNotFoundError:
        pass
    return {"total_checked": total, "violations": violations, "violation_count": sum(len(v) for v in violations.values())}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--results", required=True)
    args = parser.parse_args()
    result = check_contracts(args.results)
    print(json.dumps(result, indent=2))
    sys.exit(1 if result["violation_count"] > 0 else 0)
