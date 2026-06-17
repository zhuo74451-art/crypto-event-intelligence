"""Rollback documentation.

Provides structured rollback information for operations schema and state.
No destructive operations are executed without backup, explicit approval,
and a dry-run / plan output.
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
        action="Roll back SQLite schema (DESTRUCTIVE)",
        command=(
            "echo '[DRY-RUN] Plan: DROP run_history, source_health, "
            "snapshot_metadata, alert_candidates; PRAGMA user_version = 0'\n"
            "# ⚠ DESTRUCTIVE — requires:\n"
            "#   1. Backup confirmed (step 2)\n"
            "#   2. Explicit operator approval (set APPROVED=true)\n"
            "#   3. Dry-run output reviewed\n"
            "# Only then, replace the echo above with:\n"
            "# sqlite3 ops.db 'DROP TABLE IF EXISTS run_history; ...'"
        ),
        risk="high",
        reversible=False,
        note=(
            "DESTRUCTIVE — data loss.  NOT a default action.  "
            "Requires: (1) backup confirmed, (2) explicit operator approval, "
            "(3) dry-run / plan output reviewed.  "
            "Use only if schema migration introduced a bug that cannot be "
            "resolved by other means."
        ),
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


def dry_run_rollback() -> dict:
    """Return a dry-run / plan output for the destructive rollback step.

    Calling this function does NOT execute any destructive operation.
    Its output must be reviewed and explicitly approved before acting.
    """
    step3 = ROLLBACK_PROCEDURE[2]  # The destructive step
    return {
        "plan": {
            "step": step3.step,
            "action": step3.action,
            "tables_to_drop": [
                "run_history",
                "source_health",
                "snapshot_metadata",
                "alert_candidates",
            ],
            "pragma_change": "user_version = 0",
        },
        "prerequisites": [
            "backup_confirmed: ops.db → ops.db.pre_rollback (step 2)",
            "operator_approval: set APPROVED=true after reviewing this plan",
        ],
        "risk": step3.risk,
        "reversible": step3.reversible,
        "note": step3.note,
        "dry_run": True,
        "executed": False,
    }
