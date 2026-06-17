"""Run Diff — compare two run-history trees.

Compares parent status, child counts, source health, and configuration
between two snapshots.  Does NOT interpret market data.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional

from market_radar.operations.run_history import get_run, list_child_runs, list_runs
from market_radar.operations.sqlite_schema import get_connection


def diff_runs(
    db_path: str | Path,
    run_id_a: str,
    run_id_b: str,
) -> dict[str, Any]:
    """Compare two runs and their child trees.

    Args:
        db_path: Path to the run_history database.
        run_id_a: First run ID.
        run_id_b: Second run ID.

    Returns:
        Structured diff dict.
    """
    a = get_run(str(db_path), run_id_a)
    b = get_run(str(db_path), run_id_b)

    diff: dict[str, Any] = {
        "run_id_a": run_id_a,
        "run_id_b": run_id_b,
        "a_exists": a is not None,
        "b_exists": b is not None,
        "changes": [],
    }

    if a is None and b is None:
        diff["changes"].append({"field": "both", "change": "both runs missing"})
        return diff
    if a is None:
        diff["changes"].append({"field": "a", "change": "run_id_a not found"})
        return diff
    if b is None:
        diff["changes"].append({"field": "b", "change": "run_id_b not found"})
        return diff

    # Parent status
    _diff_field(diff, a, b, "status")
    _diff_field(diff, a, b, "runner_label")
    _diff_field(diff, a, b, "error", label="error")
    _diff_field(diff, a, b, "run_kind")

    # Timing
    _diff_field(diff, a, b, "started_at")
    _diff_field(diff, a, b, "finished_at")
    if a.get("started_at") and b.get("started_at") and a.get("finished_at") and b.get("finished_at"):
        dur_a = _duration_seconds(a["started_at"], a["finished_at"])
        dur_b = _duration_seconds(b["started_at"], b["finished_at"])
        if dur_a is not None and dur_b is not None:
            delta = round(dur_b - dur_a, 3)
            if delta != 0 or dur_a != dur_b:
                diff["changes"].append({
                    "field": "duration_seconds",
                    "a": round(dur_a, 3),
                    "b": round(dur_b, 3),
                    "delta": delta,
                })

    # Child comparison
    children_a = list_child_runs(str(db_path), run_id_a)
    children_b = list_child_runs(str(db_path), run_id_b)
    diff["child_count_a"] = len(children_a)
    diff["child_count_b"] = len(children_b)
    if len(children_a) != len(children_b):
        diff["changes"].append({
            "field": "child_count",
            "a": len(children_a),
            "b": len(children_b),
        })

    # Child status comparison
    for i, (ca, cb) in enumerate(zip(children_a, children_b)):
        if ca["status"] != cb["status"]:
            diff["changes"].append({
                "field": f"child[{i}].status",
                "a": ca["status"],
                "b": cb["status"],
            })

    # Summary diff
    sa = _safe_summary(a)
    sb = _safe_summary(b)
    for key in ("attempted_runs", "completed_runs", "degraded_runs", "failed_runs", "skipped_runs"):
        va = sa.get(key) if isinstance(sa, dict) else None
        vb = sb.get(key) if isinstance(sb, dict) else None
        if va != vb:
            diff["changes"].append({"field": f"summary.{key}", "a": va, "b": vb})

    # Config diff
    ca = sa.get("config") if isinstance(sa, dict) else None
    cb = sb.get("config") if isinstance(sb, dict) else None
    if ca != cb and isinstance(ca, dict) and isinstance(cb, dict):
        for k in set(ca) | set(cb):
            if ca.get(k) != cb.get(k):
                diff["changes"].append({
                    "field": f"config.{k}",
                    "a": ca.get(k),
                    "b": cb.get(k),
                })

    return diff


def _diff_field(diff: dict, a: dict, b: dict, field: str, label: Optional[str] = None) -> None:
    va, vb = a.get(field), b.get(field)
    if va != vb:
        diff["changes"].append({
            "field": label or field,
            "a": va,
            "b": vb,
        })


def _safe_summary(run: dict) -> Any:
    s = run.get("summary") or run.get("summary_json")
    if isinstance(s, str):
        try:
            return json.loads(s)
        except (json.JSONDecodeError, TypeError):
            return None
    return s


def _duration_seconds(start: str, finish: str) -> Optional[float]:
    import re
    ma = re.match(r"(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2})", start)
    mb = re.match(r"(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2})", finish)
    if not ma or not mb:
        return None
    from datetime import datetime, timezone
    ta = datetime(int(ma[1]), int(ma[2]), int(ma[3]),
                  int(ma[4]), int(ma[5]), int(ma[6]), tzinfo=timezone.utc)
    tb = datetime(int(mb[1]), int(mb[2]), int(mb[3]),
                  int(mb[4]), int(mb[5]), int(mb[6]), tzinfo=timezone.utc)
    return (tb - ta).total_seconds()
