"""Status command.

Provides a snapshot of the operations subsystem state.
No side effects.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from market_radar.operations.run_history import list_runs
from market_radar.operations.recovery import recovery_state


def status(db_path: str | Path, lock_path: Optional[str | Path] = None) -> dict[str, Any]:
    """Produce an operations status snapshot."""
    recent = list_runs(db_path, limit=5)
    recovery = recovery_state(db_path, lock_path=lock_path)

    ok_count = sum(1 for r in recent if r.get("status") == "ok")
    fail_count = sum(1 for r in recent if r.get("status") == "failed")

    return {
        "recent_runs": len(recent),
        "ok_count": ok_count,
        "fail_count": fail_count,
        "interrupted": recovery.get("interrupted", False),
        "lock_stale": recovery.get("lock_stale"),
        "ok": fail_count == 0 and not recovery.get("interrupted", False),
    }
