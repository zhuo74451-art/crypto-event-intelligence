"""Operator Readiness Score — 0-100 system readiness assessment.

Components: dependencies, paths, connectivity, schema, no-send, audit, lock/STOP, artifacts.
Not a trading signal.
"""
from __future__ import annotations

from typing import Any


def compute_readiness(
    dependencies_ok: bool = True,
    paths_writable: bool = True,
    sources_connected: int = 0,
    sources_total: int = 4,
    schema_ok: bool = True,
    no_send_enforced: bool = True,
    audit_chain_ok: bool = True,
    no_lock_stale: bool = True,
    no_stop_marker: bool = True,
    artifacts_complete: bool = True,
) -> dict:
    """Compute 0-100 readiness score with component breakdown.

    Returns dict with overall score, component scores, and assessment.
    """
    components = {
        "dependencies": _score_dependency(dependencies_ok),
        "paths": _score_bool(paths_writable, 10),
        "source_connectivity": _score_connectivity(sources_connected, sources_total),
        "schema": _score_bool(schema_ok, 10),
        "no_send": _score_bool(no_send_enforced, 15),
        "audit_integrity": _score_bool(audit_chain_ok, 15),
        "lock_and_stop": _score_lock_stop(no_lock_stale, no_stop_marker),
        "artifact_completeness": _score_bool(artifacts_complete, 10),
    }

    total = sum(c["score"] for c in components.values())
    max_score = sum(c["max"] for c in components.values())
    percentage = int(round(total / max_score * 100)) if max_score > 0 else 0
    percentage = max(0, min(100, percentage))

    if percentage >= 90:
        assessment = "ready"
    elif percentage >= 70:
        assessment = "degraded"
    elif percentage >= 40:
        assessment = "impaired"
    else:
        assessment = "blocked"

    return {
        "score": percentage,
        "assessment": assessment,
        "components": components,
    }


def _score_bool(ok: bool, max_score: int) -> dict:
    return {"score": max_score if ok else 0, "max": max_score, "status": "PASS" if ok else "FAIL"}


def _score_dependency(ok: bool) -> dict:
    return _score_bool(ok, 15)


def _score_connectivity(connected: int, total: int) -> dict:
    pct = connected / total if total > 0 else 0
    score = int(pct * 15)
    return {"score": score, "max": 15, "status": f"{connected}/{total}", "detail": f"{connected} of {total} sources reachable"}


def _score_lock_stop(no_lock: bool, no_stop: bool) -> dict:
    score = 0
    if no_lock:
        score += 5
    if no_stop:
        score += 5
    return {"score": score, "max": 10, "status": "PASS" if score == 10 else "WARN"}
