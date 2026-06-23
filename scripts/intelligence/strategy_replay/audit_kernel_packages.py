"""Audit kernel packages for missing or empty fields."""
import json, sys, argparse

REQUIRED = ["kernel_package_id", "event_id", "hypotheses", "hypothesis_contexts"]


def check_kernel_packages(packages_path: str) -> dict:
    violations = {
        "empty_required_inputs": [],
        "duplicate_hypothesis_ids": [],
        "missing_4h_hypothesis": [],
        "missing_24h_hypothesis": [],
    }
    total = 0
    try:
        with open(packages_path, "r", encoding="utf-8") as f:
            for line in f:
                total += 1
                p = json.loads(line)
                for field in REQUIRED:
                    if field not in p or not p[field]:
                        violations["empty_required_inputs"].append(f"line_{total}:{field}")
                hyps = p.get("hypotheses", [])
                hids = [h.get("hypothesis_id", "") for h in hyps if isinstance(h, dict)]
                if len(hids) != len(set(hids)):
                    violations["duplicate_hypothesis_ids"].append(p.get("kernel_package_id", ""))
                horizons = [h.get("time_horizon", "") for h in hyps if isinstance(h, dict)]
                if "continuation_to_4h" not in horizons:
                    violations["missing_4h_hypothesis"].append(p.get("kernel_package_id", ""))
                if "continuation_to_24h" not in horizons:
                    violations["missing_24h_hypothesis"].append(p.get("kernel_package_id", ""))
    except FileNotFoundError:
        pass
    return {"total_checked": total, "violations": violations, "violation_count": sum(len(v) for v in violations.values())}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--packages", required=True)
    args = parser.parse_args()
    result = check_kernel_packages(args.packages)
    print(json.dumps(result, indent=2))
    if result["violation_count"] > 0:
        sys.exit(1)
