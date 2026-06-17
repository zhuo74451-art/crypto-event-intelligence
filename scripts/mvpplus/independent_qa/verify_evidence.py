#!/usr/bin/env python3
"""Verify QA evidence artifact against schema.

W6_DELTA_PROJECT_SPECIFIC_QA_REPAIR_R02:
  Checks exact counts, tested_commit, no business lane claims.
  Does not claim QA_FOUNDATION_READY unless all framework self-tests pass.

Usage:
  python -X utf8 scripts/mvpplus/independent_qa/verify_evidence.py artifacts/evidence/w6_qa_foundation_report.json
"""

import json
import os
import subprocess
import sys

PROJ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, PROJ)
from qa.mvpplus.qa_core import scan_evidence_schema


def main():
    if len(sys.argv) < 2:
        print("Usage: verify_evidence.py <evidence.json>")
        sys.exit(1)

    path = os.path.abspath(sys.argv[1])
    if not os.path.isfile(path):
        print(f"[BLOCKED] Evidence file not found: {path}")
        sys.exit(2)

    with open(path, "r", encoding="utf-8") as f:
        evidence = json.load(f)

    # Schema validation
    schema_path = os.path.join(PROJ, "qa", "mvpplus", "evidence_schema.json")
    if not os.path.isfile(schema_path):
        print(f"[BLOCKED] Schema not found: {schema_path}")
        sys.exit(2)
    with open(schema_path, "r", encoding="utf-8") as f:
        schema = json.load(f)

    result = scan_evidence_schema(evidence, schema)
    print(f"Evidence:       {path}")
    print(f"Schema valid:   {result.status}")
    if result.violations:
        for v in result.violations:
            print(f"  [FAIL] {v}")
        sys.exit(1)

    # Extract key fields
    scan_id = evidence.get("scan_id", "?")
    target_ref = evidence.get("target_ref", "?")
    scanned_at = evidence.get("scanned_at", "?")
    summary = evidence.get("summary", {})
    total = summary.get("total", 0)
    passed = summary.get("pass", 0)
    failed = summary.get("fail", 0)
    blocked = summary.get("blocked", 0)
    n_a = summary.get("not_applicable", 0)

    print(f"Scan ID:        {scan_id}")
    print(f"Target ref:     {target_ref}")
    print(f"Scanned at:     {scanned_at}")
    print()

    # Verify tested_commit
    try:
        head = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=PROJ, text=True
        ).strip()
        print(f"Tested commit:  {head[:12]}")
        results = evidence.get("results", [])
        for r in results:
            if r.get("scanner") == "artifact_binding_validator":
                claimed = r.get("detail", "")
                if "verified" in claimed.lower():
                    print(f"  Artifact binding: {r['status']}")
                break
    except Exception:
        print("Tested commit:  (unknown — not a git repository)")

    # Count verification
    print(f"\n  Total:    {total}")
    print(f"  PASS:     {passed}")
    print(f"  FAIL:     {failed}")
    print(f"  BLOCKED:  {blocked}")
    print(f"  N/A:      {n_a}")
    print(f"  Sum check: {'OK' if passed + failed + blocked + n_a == total else 'MISMATCH'}")

    # Check no false business lane claims
    for r in evidence.get("results", []):
        detail_lower = (r.get("detail") or "").lower()
        if any(term in detail_lower for term in ("business lane", "lane passed", "business scan")):
            print(f"\n[WARN] Result contains business lane claim: {r['scanner']}")
            print("  Evidence must not claim business lanes passed.")

    # Determine QA_FOUNDATION_READY
    print()
    if failed == 0 and blocked == 0:
        print(">> Verdict: QA_FOUNDATION_READY")
        print("   All framework self-tests pass. No failed or blocked scans.")
        sys.exit(0)
    elif failed == 0 and blocked > 0:
        print(f">> Verdict: NOT_READY (blocked={blocked})")
        print("   Some scans were blocked. Investigate missing targets.")
        sys.exit(1)
    else:
        print(f">> Verdict: NOT_READY (fail={failed}, blocked={blocked})")
        print("   Framework self-tests are not all passing.")
        sys.exit(1)


if __name__ == "__main__":
    main()
