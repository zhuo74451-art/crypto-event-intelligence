"""Run-once wrapper.

Ensures a runner is executed exactly once with proper context setup.
No daemon, no loop.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from market_radar.operations.runner_protocol import RunnerProtocol, RunResult


def run_once(
    runner: RunnerProtocol,
    config: Optional[dict[str, Any]] = None,
    run_id: Optional[str] = None,
) -> RunResult:
    """Execute a runner exactly once.

    Args:
        runner: A RunnerProtocol-compliant object.
        config: Optional configuration.
        run_id: Optional explicit run ID (auto-generated if omitted).

    Returns:
        RunResult with execution outcome.
    """
    rid = run_id or str(uuid.uuid4())
    label = getattr(runner, "label", runner.__class__.__name__)
    context: dict[str, Any] = {
        "run_id": rid,
        "config": config or {},
        "state": {},
        "started_at": datetime.now(timezone.utc).isoformat(),
    }

    try:
        result = runner.run(context)
        status = result.get("status", "ok")
        return RunResult(
            run_id=rid,
            runner_label=label,
            status=status,
            summary=result,
        )
    except Exception as e:
        return RunResult(
            run_id=rid,
            runner_label=label,
            status="failed",
            error=f"{type(e).__name__}: {e}",
        )
