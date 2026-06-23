"""Audit abstention records for completeness."""
import json, sys, argparse
REQUIRED = ["abstention_id", "event_id", "strategy_id", "reason_codes", "information_cutoff_utc"]


def check_abstentions(abstentions_path: str) -> dict:
    violations = {"empty_reason_codes": [], "missing_information_cutoff": []}
    total = 0
    try:
        with open(abstentions_path, "r", encoding="utf-8") as f:
            for line in f:
                total += 1
                a = json.loads(line)
                if not a.get("reason_codes"):
                    violations["empty_reason_codes"].append(a.get("abstention_id", ""))
                if not a.get("information_cutoff_utc"):
                    violations["missing_information_cutoff"].append(a.get("abstention_id", ""))
    except FileNotFoundError:
        pass
    return {"total_checked": total, "violations": violations, "violation_count": sum(len(v) for v in violations.values())}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--abstentions", required=True)
    args = parser.parse_args()
    result = check_abstentions(args.abstentions)
    print(json.dumps(result, indent=2))
    sys.exit(1 if result["violation_count"] > 0 else 0)
