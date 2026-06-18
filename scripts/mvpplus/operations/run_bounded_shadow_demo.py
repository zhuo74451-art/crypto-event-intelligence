#!/usr/bin/env python3
"""Bounded Shadow Demo — local demonstration only, never sends.

This CLI uses a built-in fake one-shot callable to demonstrate the
Bounded Shadow Runner.  It does NOT import Integration, access the
network, or start any background threads.

Usage:
    python scripts/mvpplus/operations/run_bounded_shadow_demo.py \\
        --max-runs 3 \\
        --interval-seconds 0.1 \\
        --state-dir /tmp/bounded_shadow_demo \\
        --statuses completed,degraded,completed

All runs terminate after ``--max-runs`` iterations.
``--no-send`` is always True and cannot be disabled.
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path
from typing import Any

# Ensure the project root is on sys.path
_proj_root = Path(__file__).resolve().parent.parent.parent
if str(_proj_root) not in sys.path:
    sys.path.insert(0, str(_proj_root))

from market_radar.operations.bounded_shadow import (
    BoundedShadowConfig,
    BoundedShadowResult,
    ShadowCallableResult,
    run_bounded_shadow,
)


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Bounded Shadow Demo — local fake execution only, never sends.",
    )
    parser.add_argument("--max-runs", type=int, default=2, help="Runs (1-10)")
    parser.add_argument(
        "--interval-seconds", type=float, default=0.0,
        help="Sleep between rounds (0-3600)",
    )
    parser.add_argument(
        "--state-dir", type=str, default="/tmp/bounded_shadow_demo",
        help="Directory for state (lock, stop marker, DB)",
    )
    parser.add_argument(
        "--statuses", type=str,
        default="completed,completed",
        help="Comma-separated result statuses, e.g. completed,degraded,completed",
    )
    parser.add_argument("--stop-on-failure", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--continue-on-degraded", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument(
        "--no-send", action=argparse.BooleanOptionalAction, default=True,
        help="MUST always be True. Bounded shadow never sends.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)

    if args.no_send is not True:
        print("ERROR: --no-send must be True. Bounded shadow never sends.")
        return 1

    # Build statuses list
    statuses = [s.strip() for s in args.statuses.split(",")]
    if not statuses:
        print("ERROR: --statuses must have at least one value")
        return 1

    # Create a fake one-shot callable that cycles through the given statuses
    class FakeCallable:
        def __init__(self, status_list: list[str]):
            self._status_list = status_list
            self._idx = 0

        def __call__(self, ordinal: int, **kwargs: Any) -> ShadowCallableResult:
            status = self._status_list[min(self._idx, len(self._status_list) - 1)]
            self._idx += 1
            run_id = f"demo-child-{ordinal}"
            print(f"  [{ordinal}] → {status}  (child_run_id={run_id})")
            return ShadowCallableResult(
                child_run_id=run_id,
                status=status,
            )

    config = BoundedShadowConfig(
        max_runs=args.max_runs,
        interval_seconds=args.interval_seconds,
        stop_on_failure=args.stop_on_failure,
        continue_on_degraded=args.continue_on_degraded,
        state_dir=args.state_dir,
        no_send=True,  # Always locked
    )

    print(f"Bounded Shadow Demo")
    print(f"  state_dir:   {config.state_dir}")
    print(f"  max_runs:    {config.max_runs}")
    print(f"  statuses:    {statuses}")
    print(f"  no_send:     {config.no_send}")
    print(f"  lock_path:   {config.lock_path}")
    print(f"  db_path:     {config.run_history_db}")
    print()

    result: BoundedShadowResult = run_bounded_shadow(config, FakeCallable(statuses))

    print()
    print("Result:")
    print(f"  status:            {result.status}")
    print(f"  attempted_runs:    {result.attempted_runs}")
    print(f"  completed_runs:    {result.completed_runs}")
    print(f"  degraded_runs:     {result.degraded_runs}")
    print(f"  failed_runs:       {result.failed_runs}")
    print(f"  skipped_runs:      {result.skipped_runs}")
    print(f"  stopped_by_marker: {result.stopped_by_marker}")
    print(f"  stopped_by_failure:{result.stopped_by_failure}")
    print(f"  stopped_by_policy: {result.stopped_by_policy}")
    print(f"  lock_acquired:     {result.lock_acquired}")
    print(f"  no_send:           {result.no_send}")
    if result.errors:
        print(f"  errors:            {result.errors}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
