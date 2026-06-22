#!/usr/bin/env python3
"""
Audit Research Integrity — checks for forbidden patterns and data quality issues.
"""

import argparse
import json
import os
import sys

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))


FORBIDDEN_TERMS = ["proven", "guaranteed", "certain", "profitable",
                   "production_ready", "fully_proven"]


def audit_claims(claims_path: str) -> dict:
    """Audit research claims for integrity violations."""
    issues = []
    counts = {"total": 0, "supported": 0, "contested": 0, "contradicted": 0,
              "insufficient": 0, "observed": 0, "rejected": 0, "stale": 0, "superseded": 0}
    forbidden_uses = []

    with open(claims_path) as f:
        for line in f:
            claim = json.loads(line)
            counts["total"] += 1
            status = claim.get("claim_status", "")
            if status in counts:
                counts[status] += 1

            # Check for forbidden status values in limitations
            limitations = claim.get("limitations", [])
            for lim in limitations:
                for term in FORBIDDEN_TERMS:
                    if term in lim.lower():
                        forbidden_uses.append({
                            "claim_id": claim.get("claim_id"),
                            "term": term,
                            "context": lim,
                        })

            # Check for missing evidence edges
            if not claim.get("supporting_evidence_edge_ids") and not claim.get("opposing_evidence_edge_ids"):
                issues.append({
                    "claim_id": claim.get("claim_id"),
                    "issue": "no evidence edges",
                })

    return {
        "total_claims": counts["total"],
        "status_distribution": counts,
        "forbidden_term_uses": len(forbidden_uses),
        "forbidden_details": forbidden_uses[:5],
        "claims_without_evidence": len(issues),
        "integrity_issues": issues[:10],
        "passed": len(forbidden_uses) == 0,
    }


def main():
    parser = argparse.ArgumentParser(description="Audit Research Integrity")
    parser.add_argument("--claims-path", default="data/intelligence/research/claims/research_claims_v1.jsonl")
    args = parser.parse_args()

    claims_path = os.path.join(PROJECT_ROOT, args.claims_path)
    if not os.path.isfile(claims_path):
        print(f"Claims file not found: {claims_path}")
        sys.exit(1)

    result = audit_claims(claims_path)
    print(json.dumps(result, indent=2))

    if not result.get("passed", True):
        print("\n⚠️  INTEGRITY ISSUES FOUND")
        sys.exit(1)
    else:
        print("\n✅ Integrity check passed")


if __name__ == "__main__":
    main()
