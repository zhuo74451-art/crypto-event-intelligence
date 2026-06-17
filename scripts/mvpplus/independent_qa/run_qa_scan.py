#!/usr/bin/env python3
"""Independent QA Scan Runner — mvpplus.

Usage:
  python -X utf8 scripts/mvpplus/independent_qa/run_qa_scan.py \\
    --repo /path/to/repo \\
    --ref cfc1e09b9c4e0c734ae4bfc913b726c6e2b145f9

Read-only. No network. No business code modification.
"""

import argparse
import json
import os
import sys

PROJ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, PROJ)

from qa.mvpplus.qa_core import run_all_scans, QAScanReport


def main():
    parser = argparse.ArgumentParser(description="mvpplus Independent QA Scan Runner")
    parser.add_argument("--repo", default=PROJ, help="Repository root path")
    parser.add_argument("--ref", default="HEAD", help="Target ref for ownership diff")
    parser.add_argument("--expected-tests", type=int, default=81,
                        help="Expected test count for focused QA tests")
    parser.add_argument("--output", default=None,
                        help="Output path for evidence JSON (default: artifacts/evidence/)")
    args = parser.parse_args()

    repo_root = os.path.abspath(args.repo)
    print(f"QA Scan: {repo_root} @ {args.ref}")

    owned = [
        "qa/mvpplus/",
        "tests/mvpplus/",
        "scripts/mvpplus/",
        "docs/qa/",
        "artifacts/evidence/",
    ]
    scan_paths = ["market_radar/", "fixtures/", "scripts/"]
    test_paths = ["tests/test_pilot_v1_protocol_seal.py"]
    manifest = "requirements.txt"
    corpus_dir = os.path.join("qa", "mvpplus", "corpus")

    report = run_all_scans(
        repo_root=repo_root,
        target_ref=args.ref,
        owned_paths=owned,
        scan_paths=scan_paths,
        expected_test_count=args.expected_tests,
        test_paths=test_paths,
        manifest_path=manifest,
        corpus_dir=corpus_dir,
    )

    # Determine output path
    if args.output:
        out_path = args.output
    else:
        head = report.scan_id.split("_")[-1] if "_" in report.scan_id else "unknown"
        ev_dir = os.path.join(repo_root, "artifacts", "evidence")
        os.makedirs(ev_dir, exist_ok=True)
        out_path = os.path.join(ev_dir, f"w6_qa_foundation_report.json")

    # Save
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(report.as_dict(), f, ensure_ascii=False, indent=2)

    # Summary
    s = report.summary
    print(f"\nQA Scan Complete: {out_path}")
    print(f"  Total:  {s['total']}")
    print(f"  PASS:   {s['pass']}")
    print(f"  FAIL:   {s['fail']}")
    print(f"  BLOCKED: {s['blocked']}")
    print(f"  N/A:    {s['not_applicable']}")
    if s['fail'] > 0 or s['blocked'] > 0:
        print("\n  Failures/Blocked:")
        for r in report.results:
            if r.status in ("FAIL", "BLOCKED"):
                print(f"    {r.scanner}: {r.status} — {r.detail}")
                for v in r.violations[:3]:
                    print(f"      - {v}")

    # Exit code
    if s['fail'] > 0:
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
