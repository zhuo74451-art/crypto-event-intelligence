#!/usr/bin/env python3
"""MVP+ — Crypto Signal Intelligence Workbench: One-Shot Runner.

Usage:
    python scripts/run_mvp_workbench.py

Or with options:
    python scripts/run_mvp_workbench.py --skip-l4 --output-dir ./artifacts

Design:
  - One-shot: single run, no daemon/cron
  - Read-only: never writes to user files, only to artifacts/
  - Bounded concurrency: sequential lane execution
  - Graceful degradation: individual lane failures don't crash the run
  - Local output: generates a self-contained HTML workbench

Output artifacts (under artifacts/):
  reports/run_report.json     — Full RunReport as JSON
  state/current_positions.json — Current positions for next run's diff
  evidence/evidence_ledger.json — Evidence ledger summary
  workbench/workbench_*.html   — Self-contained HTML dashboard
  logs/run_*.json              — Run log
"""

from __future__ import annotations

import argparse
import os
import sys
import webbrowser

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)


def main():
    parser = argparse.ArgumentParser(
        description="MVP+ Crypto Signal Intelligence Workbench",
    )
    parser.add_argument(
        "--skip-l1", action="store_true",
        help="Skip L1 (Hyperliquid Provider) — use empty positions",
    )
    parser.add_argument(
        "--skip-l2", action="store_true",
        help="Skip L2 (Whale Engine) — skip position change detection",
    )
    parser.add_argument(
        "--skip-l3", action="store_true",
        help="Skip L3 (Market Context) — use empty market data",
    )
    parser.add_argument(
        "--skip-l4", action="store_true",
        help="Skip L4 (Existing Feeds) — use empty feed list",
    )
    parser.add_argument(
        "--skip-l5", action="store_true",
        help="Skip L5 (Workbench UI) — no HTML generation",
    )
    parser.add_argument(
        "--open", action="store_true", default=True,
        help="Open workbench HTML in browser after completion (default: True)",
    )
    parser.add_argument(
        "--no-open", action="store_false", dest="open",
        help="Do NOT open workbench HTML in browser",
    )
    parser.add_argument(
        "--output-dir", type=str, default=None,
        help="Override artifacts output directory",
    )
    args = parser.parse_args()

    print("═" * 60)
    print("  MVP+ — Crypto Signal Intelligence Workbench")
    print("  Internal | Read-Only | One-Shot")
    print("═" * 60)
    print(f"\nProject root: {_PROJECT_ROOT}")
    print(f"Skipped lanes: ", end="")
    skips = []
    if args.skip_l1:
        skips.append("L1")
    if args.skip_l2:
        skips.append("L2")
    if args.skip_l3:
        skips.append("L3")
    if args.skip_l4:
        skips.append("L4")
    if args.skip_l5:
        skips.append("L5")
    print(", ".join(skips) if skips else "none")

    from market_radar.l6_integration.integration_runner import run as run_integration

    result = run_integration(project_root=_PROJECT_ROOT)

    r = result.as_dict()
    print(f"\n{'═' * 60}")
    print(f"  Run ID:   {r['run_id']}")
    print(f"  Status:   {r['status']}")
    print(f"{'═' * 60}")
    print(f"\n📊 Lane Results:")
    for lane_id, lr in sorted(result.run_report.lane_results.items()):
        print(f"  {lane_id}: {lr.status} ({lr.item_count} items, {lr.error_count} errors)")

    if result.workbench_path:
        full_path = os.path.abspath(result.workbench_path)
        file_url = f"file:///{full_path.replace(os.sep, '/')}"
        print(f"\n{'=' * 60}")
        print(f"  📊 Workbench: {file_url}")
        print(f"{'=' * 60}")
        if args.open:
            try:
                webbrowser.open(file_url)
                print("  (Opened in browser)")
            except Exception:
                print("  (Could not auto-open browser)")
    else:
        print("\n❌ No workbench HTML generated")

    if result.run_report.error:
        print(f"\n❌ Fatal error: {result.run_report.error}")

    if result.run_report.warnings:
        print(f"\n⚠ Warnings:")
        for w in result.run_report.warnings[:5]:
            print(f"  - {w}")

    if result.run_report.degraded_paths:
        print(f"\n🔻 Degraded paths:")
        for p in result.run_report.degraded_paths[:5]:
            print(f"  - {p}")

    print(f"\n📁 Artifacts:")
    if result.workbench_path:
        print(f"  Workbench: artifacts/workbench/{os.path.basename(result.workbench_path)}")
    print(f"  Report:    artifacts/reports/run_report.json")
    print(f"  Evidence:  {result.evidence_path}")
    print(f"  Log:       {result.run_log_path}")

    exit_code = 0 if r['status'] == 'OK' else 1
    print(f"\n{'=' * 60}")
    print(f"  MVP_WORKBENCH_COMPLETE (exit={exit_code})")
    print(f"{'=' * 60}")
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
