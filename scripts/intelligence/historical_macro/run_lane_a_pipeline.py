#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Unified entry point for Lane A pipeline."""
import argparse
import os
import subprocess
import sys
import time

SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))


def run_step(name, script, extra_args=None):
    print("\n" + "=" * 60)
    print(f"STEP: {name}")
    print("=" * 60)
    script_path = os.path.join(SCRIPTS_DIR, script)
    cmd = [sys.executable, "-X", "utf8", script_path]
    if extra_args:
        cmd.extend(extra_args)
    start = time.time()
    result = subprocess.run(cmd, capture_output=True, text=True)
    elapsed = time.time() - start
    if result.stdout:
        print(result.stdout[:2000])
    if result.stderr:
        print("STDERR:", result.stderr[:1000])
    status = "OK" if result.returncode == 0 else "FAIL"
    print(f"  [{status}] {name} ({elapsed:.1f}s)")
    return result.returncode == 0


def main():
    parser = argparse.ArgumentParser(description="Run Lane A Pipeline")
    parser.add_argument("--start-date", default="2010-01-01")
    parser.add_argument("--end-date", default="2026-12-31")
    parser.add_argument("--cache-dir", default="data/intelligence/historical_macro/cache")
    parser.add_argument("--output-dir", default="data/intelligence/historical_macro")
    parser.add_argument("--resume", action="store_true", default=True)
    parser.add_argument("--skip-consensus", action="store_true")
    parser.add_argument("--skip-revisions", action="store_true")
    args = parser.parse_args()

    start_year = args.start_date[:4]
    end_year = args.end_date[:4]
    base_args = [
        f"--start-year={start_year}", f"--end-year={end_year}",
        f"--output-dir={args.output_dir}", f"--cache-dir={args.cache_dir}",
    ]
    if args.resume:
        base_args.append("--resume")

    steps = [
        ("Build Release Events", "build_release_events.py", base_args),
    ]

    if not args.skip_consensus:
        steps.append(("Build Consensus Observations", "build_consensus_observations.py",
                      [f"--output-dir={args.output_dir}", f"--cache-dir={args.cache_dir}"]))
    if not args.skip_revisions:
        steps.append(("Build Revision Chains", "build_revision_chains.py",
                      [f"--output-dir={args.output_dir}"]))

    steps.append(("Build Dataset", "build_macro_evidence_dataset.py",
                  [f"--output-dir={args.output_dir}"]))
    steps.append(("Point-in-Time Audit", "audit_point_in_time.py",
                  [f"--output-dir={args.output_dir}"]))
    steps.append(("Coverage Report", "generate_coverage_report.py",
                  [f"--output-dir={args.output_dir}"]))

    all_ok = True
    for name, script, extra in steps:
        ok = run_step(name, script, extra)
        if not ok:
            all_ok = False
            print(f"WARNING: step failed: {name}")

    print("\n" + "=" * 60)
    print("PIPELINE FINISHED")
    print(f"All steps OK: {all_ok}")
    print("=" * 60)
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
