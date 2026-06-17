"""Rollback documentation.

Provides structured rollback information for operations schema and state.
No destructive operations are executed — this is documentation only.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class RollbackStep:
    """A single rollback step with instructions."""
    step: int
    action: str
    command: str
    risk: str  # "low" | "medium" | "high"
    reversible: bool
    note: str


ROLLBACK_PROCEDURE: list[RollbackStep] = [
    RollbackStep(
        step=1,
        action="Stop all running operations",
        command="touch STOP_MARKER; wait for graceful shutdown",
        risk="low",
        reversible=True,
        note="Stop marker prevents new iterations.",
    ),
    RollbackStep(
        step=2,
        action="Export current database",
        command="cp ops.db ops.db.pre_rollback",
        risk="low",
        reversible=True,
        note="Always backup before destructive operations.",
    ),
    RollbackStep(
        step=3,
        action="Roll back SQLite schema",
        command="DROP TABLE IF EXISTS run_history; DROP TABLE IF EXISTS source_health; DROP TABLE IF EXISTS snapshot_metadata; DROP TABLE IF EXISTS alert_candidates; PRAGMA user_version = 0;",
        risk="high",
        reversible=False,
        note="Destructive. Use only if schema migration introduced a bug. Data loss.",
    ),
    RollbackStep(
        step=4,
        action="Revert code",
        command="git revert <commit>",
        risk="medium",
        reversible=True,
        note="Revert the ops-foundation commit. No business code affected.",
    ),
    RollbackStep(
        step=5,
        action="Verify rollback",
        command="python -m pytest tests/ -q --tb=line",
        risk="low",
        reversible=True,
        note="Run full test suite after rollback.",
    ),
]


def get_rollback_procedure() -> list[dict]:
    """Return the rollback procedure as serializable dicts."""
    return [{
        "step": s.step,
        "action": s.action,
        "command": s.command,
        "risk": s.risk,
        "reversible": s.reversible,
        "note": s.note,
    } for s in ROLLBACK_PROCEDURE]
