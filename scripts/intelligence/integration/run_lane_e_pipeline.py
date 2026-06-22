#!/usr/bin/env python3
"""
Lane E Pipeline — Unified Entry Point

Usage:
  python scripts/intelligence/integration/run_lane_e_pipeline.py \
    --producer-locks docs/execution/lane_e/PRODUCER_LOCKS.yaml \
    --integration-output data/intelligence/integration \
    --research-output data/intelligence/research \
    --resume
"""

import argparse
import json
import os
import sys
import subprocess
from datetime import datetime, timezone

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))


def run_step(label: str, cmd: list) -> dict:
    """Run a pipeline step and return result."""
    print(f"\n{'='*60}")
    print(f"[{label}]")
    print(f"{'='*60}")
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=PROJECT_ROOT)
    if result.returncode != 0:
        print(f"[FAIL] {label}")
        print(result.stderr[:500])
    else:
        print(f"[OK] {label}")
        if result.stdout:
            print(result.stdout[-300:])
    return {
        "label": label,
        "returncode": result.returncode,
        "stdout_summary": result.stdout[-200:] if result.stdout else "",
        "stderr_summary": result.stderr[-200:] if result.stderr else "",
    }


def main():
    parser = argparse.ArgumentParser(description="Lane E Unified Pipeline Entry Point")
    parser.add_argument("--producer-locks", default="docs/execution/lane_e/PRODUCER_LOCKS.yaml")
    parser.add_argument("--integration-output", default="data/intelligence/integration")
    parser.add_argument("--research-output", default="data/intelligence/research")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--skip-gates", action="store_true")
    parser.add_argument("--skip-reports", action="store_true")
    args = parser.parse_args()

    results = []
    pipeline_py = os.path.join(PROJECT_ROOT, "market_radar/intelligence/integration/internal_pipeline.py")

    # Step 1: Run internal pipeline
    cmd = [
        sys.executable, "-X", "utf8", pipeline_py,
        "--producer-locks", args.producer_locks,
        "--integration-output", args.integration_output,
        "--research-output", args.research_output,
    ]
    if args.resume:
        cmd.append("--resume")
    results.append(run_step("Internal Pipeline", cmd))

    # Step 2: Run integration gates
    if not args.skip_gates:
        gates_py = os.path.join(PROJECT_ROOT, "scripts/intelligence/integration/run_integration_gates.py")
        cmd = [
            sys.executable, "-X", "utf8", gates_py,
            "--producer-locks", args.producer_locks,
        ]
        results.append(run_step("Integration Gates", cmd))

    # Step 3: Generate reports
    if not args.skip_reports:
        reports_py = os.path.join(PROJECT_ROOT, "scripts/intelligence/integration/generate_integration_report.py")
        cmd = [
            sys.executable, "-X", "utf8", reports_py,
            "--integration-output", args.integration_output,
            "--research-output", args.research_output,
        ]
        results.append(run_step("Generate Reports", cmd))

    # Summary
    print(f"\n{'='*60}")
    print("LANE E PIPELINE SUMMARY")
    print(f"{'='*60}")
    all_ok = all(r["returncode"] == 0 for r in results)
    for r in results:
        status = "PASS" if r["returncode"] == 0 else "FAIL"
        print(f"  [{status}] {r['label']}")
    print(f"\nOverall: {'ALL PASS' if all_ok else 'SOME FAILURES'}")
    sys.exit(0 if all_ok else 1)


if __name__ == "__main__":
    main()
