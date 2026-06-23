"""Audit kernel packages for missing or empty fields."""
import json, sys, argparse
REQUIRED = ["kernel_package_id", "event_id", "hypotheses", "hypothesis_contexts", "source_strategy_ids", "information_cutoff_utc"]


def check_kernel_packages(packages_path: str) -> dict:
    violations = {"empty_required_inputs": [], "missing_origin_group": [], "missing_transmission_signature": []}
    total = 0
    try:
        with open(packages_path, "r", encoding="utf-8") as f:
            for line in f:
                total += 1
                p = json.loads(line)
                for field in REQUIRED:
                    if field not in p or not p[field]:
                        violations["empty_required_inputs"].append(f"line_{total}:{field}")
                for ctx in p.get("hypothesis_contexts", {}).values():
                    if isinstance(ctx, dict) and not ctx.get("strategy_origin_group"):
                        violations["missing_origin_group"].append(ctx.get("hypothesis_id", ""))
                    if isinstance(ctx, dict) and not ctx.get("transmission_signature"):
                        violations["missing_transmission_signature"].append(ctx.get("hypothesis_id", ""))
    except FileNotFoundError:
        pass
    return {"total_checked": total, "violations": violations, "violation_count": sum(len(v) for v in violations.values())}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--packages", required=True)
    args = parser.parse_args()
    result = check_kernel_packages(args.packages)
    print(json.dumps(result, indent=2))
    sys.exit(1 if result["violation_count"] > 0 else 0)
