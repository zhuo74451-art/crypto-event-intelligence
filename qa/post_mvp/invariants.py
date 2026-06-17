"""Post-MVP System Invariants — machine-executable rules.

All invariants are pure functions operating on structured data.
No network, no mutation of business code.
"""
from __future__ import annotations
from dataclasses import dataclass, field, asdict
from typing import Any, Optional


@dataclass
class InvariantResult:
    name: str
    status: str  # PASS | FAIL | NOT_APPLICABLE
    detail: str = ""
    violations: list[str] = field(default_factory=list)


# ── Status Invariants ───────────────────────────────────────────────────────

def check_status_completed_no_persistence_error(report: dict) -> InvariantResult:
    """status=completed → no persistence error in errors."""
    violations = []
    if report.get("status") == "completed":
        for err in report.get("errors", []):
            if any(w in str(err).lower() for w in ["write", "insert", "db", "sqlite", "persist", "atomic"]):
                violations.append(f"completed but has persistence error: {err}")
    return InvariantResult("status_completed_no_persistence_error",
                           "PASS" if not violations else "FAIL",
                           violations=violations)


def check_source_status_ok_consistency(source: dict) -> InvariantResult:
    """source status=ok → ok=true; status=degraded/unavailable → ok=false."""
    violations = []
    if source.get("status") == "ok" and source.get("ok") != True:
        violations.append(f"source={source.get('source')}: status=ok but ok={source.get('ok')}")
    if source.get("status") in ("degraded", "unavailable") and source.get("ok") != False:
        violations.append(f"source={source.get('source')}: status={source.get('status')} but ok={source.get('ok')}")
    return InvariantResult("source_status_ok_consistency", "PASS" if not violations else "FAIL",
                           violations=violations)


def check_empty_feed_ok(feed_summary: dict) -> InvariantResult:
    """Normal empty feed → status=ok (not degraded)."""
    violations = []
    if feed_summary.get("live_count", 0) == 0 and feed_summary.get("fixture_count", 0) == 0:
        if feed_summary.get("status") and feed_summary["status"] != "ok":
            violations.append(f"Empty feed has status={feed_summary['status']}, expected ok")
    return InvariantResult("empty_feed_ok", "PASS" if not violations else "FAIL", violations=violations)


def check_internal_exception_failed(report: dict) -> InvariantResult:
    """Internal exception → status=failed (not degraded/completed)."""
    violations = []
    for err in report.get("errors", []):
        if "unhandled" in str(err).lower() or "exception" in str(err).lower():
            if report.get("status") != "failed":
                violations.append(f"Internal exception but status={report.get('status')}: {err}")
    return InvariantResult("internal_exception_failed", "PASS" if not violations else "FAIL",
                           violations=violations)


def check_partial_failure_degraded(report: dict) -> InvariantResult:
    """External partial failure → degraded, not failed overall."""
    violations = []
    sources = report.get("sources", [])
    degraded_external = any(s.get("status") == "degraded" for s in sources)
    if degraded_external and report.get("status") == "failed":
        violations.append("External degraded sources caused overall=failed, expected degraded")
    return InvariantResult("partial_failure_degraded", "PASS" if not violations else "FAIL",
                           violations=violations)


def check_all_ok_completed(report: dict) -> InvariantResult:
    """All sources ok → status=completed."""
    violations = []
    sources = report.get("sources", [])
    if sources and all(s.get("ok") == True for s in sources):
        if report.get("status") != "completed":
            violations.append("All sources ok but status not completed")
    return InvariantResult("all_ok_completed", "PASS" if not violations else "FAIL",
                           violations=violations)


# ── Cursor Invariants ───────────────────────────────────────────────────────

def check_cursor_advance_on_success(feed_summary: dict) -> InvariantResult:
    """Success + cursor_safe → cursor_advanced=true or already at tip."""
    violations = []
    if feed_summary.get("cursor_safe", True) and feed_summary.get("cursor_after"):
        if not feed_summary.get("cursor_advanced") and feed_summary.get("live_count", 0) > 0:
            violations.append("Items found but cursor did not advance")
    return InvariantResult("cursor_advance_on_success", "PASS" if not violations else "FAIL",
                           violations=violations)


def check_cursor_no_advance_on_failure(feed_summary: dict, provider_ok: bool) -> InvariantResult:
    """Provider failure → cursor must NOT advance."""
    violations = []
    if not provider_ok and feed_summary.get("cursor_advanced"):
        violations.append("Provider failed but cursor advanced")
    return InvariantResult("cursor_no_advance_on_failure", "PASS" if not violations else "FAIL",
                           violations=violations)


def check_cursor_no_rollback(feed_summary: dict, previous_cursor: Optional[str] = None) -> InvariantResult:
    """Cursor must not go backwards."""
    violations = []
    if previous_cursor and feed_summary.get("cursor_after"):
        if feed_summary["cursor_after"] < previous_cursor:
            violations.append(f"Cursor rolled back: {previous_cursor} → {feed_summary['cursor_after']}")
    return InvariantResult("cursor_no_rollback", "PASS" if not violations else "FAIL",
                           violations=violations)


# ── Run-history Invariants ──────────────────────────────────────────────────

def check_run_history_parent_child(rows: list[dict]) -> InvariantResult:
    """Parent/child relationships, ordinal continuity, no orphans."""
    violations = []
    parents = [r for r in rows if r.get("run_kind") == "shadow_parent"]
    children = [r for r in rows if r.get("run_kind") == "shadow_child"]

    if parents:
        for p in parents:
            pid = p["run_id"]
            my_children = [c for c in children if c.get("parent_run_id") == pid]
            if not my_children:
                violations.append(f"Parent {pid} has no children")
            ordinals = sorted(c.get("run_ordinal") for c in my_children if c.get("run_ordinal") is not None)
            if ordinals and len(ordinals) != len(set(ordinals)):
                violations.append(f"Parent {pid} has duplicate ordinals: {ordinals}")

    # Detect orphans: children whose parent doesn't exist
    parent_ids = {p["run_id"] for p in parents}
    for c in children:
        if c.get("parent_run_id") and c["parent_run_id"] not in parent_ids:
            violations.append(f"Orphan child {c['run_id']}: parent {c['parent_run_id']} not found")

    return InvariantResult("run_history_parent_child", "PASS" if not violations else "FAIL",
                           violations=violations)


def check_no_persistence_error_in_completed(rows: list[dict]) -> InvariantResult:
    """No row with status=completed has persistence error."""
    violations = []
    for r in rows:
        if r.get("status") == "completed":
            err = (r.get("error") or "")
            if any(w in err.lower() for w in ["insert", "unique", "constraint", "write", "sqlite"]):
                violations.append(f"Row {r['run_id']}: completed but error={err}")
    return InvariantResult("no_persistence_error_completed", "PASS" if not violations else "FAIL",
                           violations=violations)


# ── No-Send Invariants ──────────────────────────────────────────────────────

def check_no_send_invariant(config: dict, result: dict) -> InvariantResult:
    """no_send must be true everywhere relevant."""
    violations = []
    if config and config.get("no_send") != True:
        violations.append(f"Config no_send={config.get('no_send')}")
    if result.get("no_send") != True:
        violations.append(f"Result no_send={result.get('no_send')}")
    if result.get("scheduler_started") != False:
        violations.append(f"scheduler_started={result.get('scheduler_started')}")
    if result.get("credentials_used") != False:
        violations.append(f"credentials_used={result.get('credentials_used')}")
    return InvariantResult("no_send_invariant", "PASS" if not violations else "FAIL",
                           violations=violations)
