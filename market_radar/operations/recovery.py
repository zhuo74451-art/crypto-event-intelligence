"""Recovery after interrupted run.

Detects interrupted runs and provides recovery state.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

from market_radar.operations.run_history import get_run, list_runs


def find_interrupted_run(
    db_path: str | Path,
) -> Optional[dict[str, Any]]:
    """Find the most recent run that did not finish.

    A run is considered interrupted if its status is NOT 'ok'
    and it does NOT have a 'finished' state.
    """
    recent = list_runs(db_path, limit=50)
    for run in recent:
        status = run.get("status", "")
        if status in ("failed",):
            return run
        # A run without 'finished_at' near its 'started_at' is suspect
        started = run.get("started_at")
        finished = run.get("finished_at")
        if started and not finished:
            return run
    return None


def recovery_state(
    db_path: str | Path,
    lock_path: Optional[str | Path] = None,
) -> dict[str, Any]:
    """Assess recovery state after a potential interruption.

    Returns a dict with:
      - interrupted: bool
      - last_run: dict or None
      - lock_stale: bool or None
    """
    state: dict[str, Any] = {
        "interrupted": False,
        "last_run": None,
        "lock_stale": None,
    }

    interrupted = find_interrupted_run(db_path)
    if interrupted:
        state["interrupted"] = True
        state["last_run"] = interrupted

    if lock_path:
        lp = Path(lock_path)
        if lp.exists():
            import time
            try:
                data = lp.read_text(encoding="utf-8").strip()
                parts = data.split("|")
                timestamp = float(parts[1]) if len(parts) > 1 and parts[1] else 0
                age = time.time() - timestamp
                state["lock_stale"] = age > 300
            except (OSError, ValueError, IndexError):
                state["lock_stale"] = None

    return state
