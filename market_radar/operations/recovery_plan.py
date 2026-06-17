"""Recovery Plan — non-destructive issue analysis.

Only generates plans.  Never executes DELETE, UPDATE, VACUUM, or REINDEX.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

from market_radar.operations.doctor import DoctorReport, DoctorCheck


@dataclass
class RecoveryAction:
    """A single proposed recovery action (never executed by this tool)."""

    issue: str
    affected_rows: int
    proposed_action: str
    risk: str  # "low" | "medium" | "high"
    reversible: bool
    requires_approval: bool
    backup_required: bool
    sql_preview: Optional[str] = None
    expected_result: str = ""


@dataclass
class RecoveryPlan:
    """A non-executing recovery plan."""

    actions: list[RecoveryAction] = field(default_factory=list)
    total_issues: int = 0
    requires_backup: bool = False
    requires_approval: bool = False


def generate_recovery_plan(report: DoctorReport) -> RecoveryPlan:
    """Generate a recovery plan from a DoctorReport.

    Only produces proposed actions — never executes anything.
    """
    plan = RecoveryPlan()

    for check in report.checks:
        if check.status == "pass":
            continue
        action = _propose_action(check)
        if action is not None:
            plan.actions.append(action)
            if action.backup_required:
                plan.requires_backup = True
            if action.requires_approval:
                plan.requires_approval = True

    plan.total_issues = len(plan.actions)
    return plan


def _propose_action(check: DoctorCheck) -> Optional[RecoveryAction]:
    mappings = {
        "db:exists": RecoveryAction(
            issue="Database missing",
            affected_rows=-1,
            proposed_action="Initialize the database via initialize_sqlite()",
            risk="low", reversible=True, requires_approval=False,
            backup_required=False,
            expected_result="Database created at the configured path.",
        ),
        "db:integrity": RecoveryAction(
            issue="Database integrity check failed",
            affected_rows=-1,
            proposed_action="Restore from backup; then run PRAGMA integrity_check",
            risk="high", reversible=True, requires_approval=True,
            backup_required=True,
            expected_result="Restored database passes integrity check.",
        ),
        "ordinal:duplicates": RecoveryAction(
            issue="Duplicate parent+ordinal entries",
            affected_rows=check.evidence.get("count", 0),
            proposed_action="Review duplicate rows; determine correct ordinal; "
                           "delete or update the duplicate via explicit SQL",
            risk="high", reversible=False, requires_approval=True,
            backup_required=True,
            expected_result="Each parent+ordinal pair is unique.",
        ),
        "orphan:children": RecoveryAction(
            issue="Children reference missing parent",
            affected_rows=1,
            proposed_action="Re-insert missing parent record or re-link children",
            risk="medium", reversible=True, requires_approval=True,
            backup_required=True,
            expected_result="All children reference existing parents.",
        ),
        "unfinished:runs": RecoveryAction(
            issue="Runs without finished_at",
            affected_rows=1,
            proposed_action="Determine if run is still active; "
                           "update finished_at and status if stale",
            risk="low", reversible=True, requires_approval=False,
            backup_required=False,
            expected_result="All runs have finished_at set.",
        ),
        "summary:json": RecoveryAction(
            issue="Corrupt summary_json",
            affected_rows=1,
            proposed_action="Review and manually correct the summary_json field",
            risk="low", reversible=True, requires_approval=False,
            backup_required=False,
            expected_result="All summary_json fields parse as valid JSON.",
        ),
    }
    for prefix in ("summary_json:", "source_health:", "time_travel:",
                   "abnormal_status:", "parent_child:count_"):
        if check.check_id.startswith(prefix):
            return RecoveryAction(
                issue=f"{check.message[:80]}",
                affected_rows=1,
                proposed_action="Review the specific issue and apply targeted correction",
                risk="low", reversible=True, requires_approval=True,
                backup_required=False,
                expected_result="Issue resolved.",
            )
    return mappings.get(check.check_id.split(":")[0] + ":" + check.check_id.split(":")[1]
                        if ":" in check.check_id else check.check_id)
