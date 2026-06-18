"""Retention Planner — plan-only.  Never deletes or moves files.

Generates a retention plan based on configurable rules.  All actions are
proposed — none are executed.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

from market_radar.operations.run_history import list_runs, get_run, list_child_runs
from market_radar.operations.sqlite_schema import get_connection


@dataclass
class RetentionAction:
    """A proposed retention action (never executed)."""

    run_id: str
    action: str  # "keep" | "archive_candidate" | "delete_candidate"
    reason: str
    estimated_size_bytes: int = 0
    risk: str = "low"


@dataclass
class RetentionPlan:
    """A non-executing retention plan."""

    actions: list[RetentionAction] = field(default_factory=list)
    estimated_savings_bytes: int = 0
    estimated_savings_label: str = "estimate only"


def generate_retention_plan(
    db_path: str | Path,
    max_completed_to_keep: int = 20,
    min_days: int = 7,
    keep_all_failed: bool = True,
    keep_evidence_referenced: bool = True,
) -> RetentionPlan:
    """Generate a retention plan.

    Rules:
    * Keep the most recent N completed runs.
    * Keep all failed runs (if keep_all_failed).
    * Keep parents and all their children.
    * Keep runs referenced by evidence (heuristic: runner_label has 'evidence').
    * Mark older completed runs as "delete_candidate".
    * Mark very old degraded runs as "archive_candidate".

    Args:
        db_path: Path to the run_history database.
        max_completed_to_keep: Number of recent completed runs to retain.
        min_days: Minimum age in days for delete candidacy.
        keep_all_failed: Keep all failed runs.
        keep_evidence_referenced: Keep evidence-referenced runs.

    Returns:
        RetentionPlan (plan only — no deletion).
    """
    plan = RetentionPlan()
    cutoff = time.time() - (min_days * 86400)
    protected: set[str] = set()

    all_runs = list_runs(str(db_path), limit=5000)

    # Collect parent+children protection
    if keep_evidence_referenced:
        for r in all_runs:
            label = r.get("runner_label", "")
            if "evidence" in label.lower() or r.get("run_kind") == "shadow_parent":
                protected.add(r["run_id"])
                children = list_child_runs(str(db_path), r["run_id"])
                for c in children:
                    protected.add(c["run_id"])

    # Keep all failed
    if keep_all_failed:
        for r in all_runs:
            if r.get("status") in ("failed", "stopped"):
                protected.add(r["run_id"])
                if r.get("parent_run_id"):
                    protected.add(r["parent_run_id"])

    # Keep recent completed
    completed_sorted = sorted(
        [r for r in all_runs if r.get("status") == "completed" and r["run_id"] not in protected],
        key=lambda x: x.get("started_at", ""),
        reverse=True,
    )
    for r in completed_sorted[:max_completed_to_keep]:
        protected.add(r["run_id"])

    # Evaluate candidates
    for r in all_runs:
        if r["run_id"] in protected:
            plan.actions.append(RetentionAction(
                run_id=r["run_id"],
                action="keep",
                reason="Protected by retention policy",
            ))
            continue

        try:
            started_at = r.get("started_at", "")
            # Simple timestamp heuristic
            epoch = _parse_epoch(started_at)
        except (ValueError, TypeError):
            epoch = 0

        if epoch > 0 and epoch < cutoff:
            size = _estimate_run_size(r)
            if r.get("status") == "completed":
                plan.actions.append(RetentionAction(
                    run_id=r["run_id"],
                    action="delete_candidate",
                    reason=f"Completed run older than {min_days} days",
                    estimated_size_bytes=size,
                ))
                plan.estimated_savings_bytes += size
            else:
                plan.actions.append(RetentionAction(
                    run_id=r["run_id"],
                    action="archive_candidate",
                    reason=f"Run with status '{r.get('status')}' older than {min_days} days",
                    estimated_size_bytes=size,
                ))
                plan.estimated_savings_bytes += size

    plan.estimated_savings_label = f"~{plan.estimated_savings_bytes / 1024:.1f} KB (estimate only)"
    return plan


def retention_plan_summary(plan: RetentionPlan) -> dict[str, Any]:
    return {
        "total_actions": len(plan.actions),
        "keep": sum(1 for a in plan.actions if a.action == "keep"),
        "archive_candidates": sum(1 for a in plan.actions if a.action == "archive_candidate"),
        "delete_candidates": sum(1 for a in plan.actions if a.action == "delete_candidate"),
        "estimated_savings_bytes": plan.estimated_savings_bytes,
        "estimated_savings_label": plan.estimated_savings_label,
    }


def _parse_epoch(iso_str: str) -> float:
    """Crude ISO-8601 to epoch.  Accepts '2025-01-01T00:00:00'."""
    import re
    m = re.match(r"(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2})", iso_str)
    if not m:
        return 0
    from datetime import datetime, timezone
    return datetime(
        int(m[1]), int(m[2]), int(m[3]),
        int(m[4]), int(m[5]), int(m[6]),
        tzinfo=timezone.utc,
    ).timestamp()


def _estimate_run_size(run: dict) -> int:
    """Estimate the storage footprint of a run record (bytes)."""
    size = 256  # Base row overhead
    summary = run.get("summary_json") or ""
    error = run.get("error") or ""
    return size + len(summary) + len(error)
