#!/usr/bin/env python3
"""Verify QA evidence artifact against schema.

Usage:
  python -X utf8 scripts/mvpplus/independent_qa/verify_evidence.py artifacts/evidence/w6_qa_foundation_report.json
"""

import json
import os
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
    schema_path = os.path.join(PROJ, "qa", "mvpplus", "evidence_schema.json")
    if not os.path.isfile(schema_path):
        print(f"[BLOCKED] Schema not found: {schema_path}")
        sys.exit(2)
    with open(schema_path, "r", encoding="utf-8") as f:
        schema = json.load(f)
    result = scan_evidence_schema(evidence, schema)
    print(f"Evidence: {path}")
    print(f"Status: {result.status}")
    if result.violations:
        for v in result.violations:
            print(f"  [FAIL] {v}")
        sys.exit(1)
    else:
        print("[PASS] Evidence structure valid")
        sys.exit(0)


if __name__ == "__main__":
    main()
