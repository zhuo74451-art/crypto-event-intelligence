"""Bounded shadow-run command with explicit iteration maximum.

A shadow run executes a runner up to *max_iterations* times,
respecting stop markers. Designed for verification without production effect.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Callable, Optional

from market_radar.operations.runner_protocol import InjectedRunner, RunResult
from market_radar.operations.run_once import run_once
from market_radar.operations.stop_marker import StopMarker


def shadow_run(
    runner_fn: Callable[[dict[str, Any]], dict[str, Any]],
    label: str,
    max_iterations: int = 3,
    stop_marker: Optional[StopMarker] = None,
    config: Optional[dict[str, Any]] = None,
) -> list[RunResult]:
    """Execute a runner in shadow mode with an iteration cap.

    Args:
        runner_fn: Callable conforming to (dict) → dict.
        label: Human-readable label for the runner.
        max_iterations: Maximum number of iterations (must be >= 1).
        stop_marker: Optional stop marker to check between iterations.
        config: Optional config passed to each run.

    Returns:
        List of RunResult, one per completed iteration.

    Raises:
        ValueError: If max_iterations < 1.
    """
    if max_iterations < 1:
        raise ValueError(f"max_iterations must be >= 1, got {max_iterations}")

    results: list[RunResult] = []
    runner = InjectedRunner(label=label, fn=runner_fn)

    for i in range(max_iterations):
        if stop_marker and stop_marker.check():
            results.append(RunResult(
                run_id=f"shadow_{i}_stopped",
                runner_label=label,
                status="stopped",
                summary={"iteration": i, "reason": "stop_marker"},
            ))
            break

        result = run_once(runner, config=config, run_id=f"shadow_{label}_{i}_{uuid.uuid4().hex[:8]}")
        results.append(result)

        if result.status == "failed":
            break

    return results
