"""Ops Doctor — non-destructive diagnostic checks for Operations state.

The Doctor inspects databases, locks, stop markers, file integrity, and
parent-child consistency.  It NEVER modifies data.
"""

from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Optional

from market_radar.operations.file_lock import FileLock
from market_radar.operations.run_history import get_run, list_child_runs, list_runs
from market_radar.operations.sqlite_schema import get_connection, initialize_sqlite
from market_radar.operations.stop_marker import StopMarker


@dataclass
class DoctorCheck:
    """A single diagnostic check result."""

    check_id: str
    status: str  # "pass" | "warn" | "fail" | "error"
    severity: str  # "info" | "low" | "medium" | "high" | "critical"
    message: str
    evidence: dict[str, Any] = field(default_factory=dict)
    safe_action: str = ""
    destructive: bool = False


@dataclass
class DoctorReport:
    """Aggregate doctor report."""

    checks: list[DoctorCheck] = field(default_factory=list)
    total: int = 0
    passed: int = 0
    warnings: int = 0
    failures: int = 0
    errors: int = 0

    def add(self, check: DoctorCheck) -> None:
        self.checks.append(check)
        self.total += 1
        if check.status == "pass":
            self.passed += 1
        elif check.status == "warn":
            self.warnings += 1
        elif check.status == "fail":
            self.failures += 1
        elif check.status == "error":
            self.errors += 1


def run_doctor(
    state_dir: str | Path,
    clock_fn: Callable[[], float] = time.time,
    check_artifacts: bool = True,
) -> DoctorReport:
    """Run all diagnostic checks on an Operations state directory.

    Args:
        state_dir: Path to the Operations state directory.
        clock_fn: Clock function (injectable for tests).
        check_artifacts: If True, check artifact file integrity.

    Returns:
        ``DoctorReport`` with all check results.
    """
    report = DoctorReport()
    sd = Path(state_dir)
    db_path = sd / "run_history.db"
    _check_db_exists(report, db_path)
    _check_schema_version(report, db_path)
    _check_integrity(report, db_path)
    _check_wal_status(report, db_path)
    _check_tables_and_indexes(report, db_path)
    _check_parent_child_integrity(report, db_path)
    _check_duplicate_ordinals(report, db_path)
    _check_orphan_children(report, db_path)
    _check_unfinished_runs(report, db_path)
    _check_abnormal_statuses(report, db_path)
    _check_time_travel(report, db_path)
    _check_summary_json(report, db_path)
    _check_source_health(report, db_path)
    _check_lock(report, sd)
    _check_stop_marker(report, sd)
    _check_db_file_checksum(report, db_path)
    _check_path_leak(report, db_path)
    _check_sensitive_key_in_summary(report, db_path)
    _check_artifact_checksum(report, sd, db_path, check_artifacts)
    return report


def _check(report: DoctorReport, check_id: str, severity: str,
           status: str, message: str, **kwargs: Any) -> None:
    report.add(DoctorCheck(
        check_id=check_id, severity=severity, status=status,
        message=message, **kwargs,
    ))


def _db_ok(report: DoctorReport, db_path: Path) -> sqlite3.Connection | None:
    if not db_path.exists():
        return None
    try:
        return get_connection(db_path)
    except Exception as e:
        _check(report, "db:connect", "critical", "error",
               f"Cannot connect to database: {e}")
        return None


# ---------------------------------------------------------------------------
# Individual checks
# ---------------------------------------------------------------------------


def _check_db_exists(report: DoctorReport, db_path: Path) -> None:
    if db_path.exists():
        sz = db_path.stat().st_size
        _check(report, "db:exists", "high", "pass",
               f"Database exists ({sz} bytes)",
               evidence={"path": str(db_path), "size_bytes": sz},
               safe_action="None required.")
    else:
        _check(report, "db:exists", "critical", "fail",
               "Database file not found",
               evidence={"path": str(db_path)},
               destructive=False)


def _check_schema_version(report: DoctorReport, db_path: Path) -> None:
    conn = _db_ok(report, db_path)
    if conn is None:
        return
    try:
        ver = conn.execute("PRAGMA user_version").fetchone()[0]
        _check(report, "db:schema_version", "high", "pass",
               f"Schema version = {ver}",
               evidence={"user_version": ver})
    except Exception as e:
        _check(report, "db:schema_version", "high", "fail",
               f"Cannot read schema version: {e}")
    finally:
        conn.close()


def _check_integrity(report: DoctorReport, db_path: Path) -> None:
    conn = _db_ok(report, db_path)
    if conn is None:
        return
    try:
        rows = conn.execute("PRAGMA integrity_check").fetchall()
        errors = [r[0] for r in rows if r[0] != "ok"]
        if errors:
            _check(report, "db:integrity", "critical", "fail",
                   f"Integrity check found {len(errors)} issues",
                   evidence={"errors": errors[:10]})
        else:
            _check(report, "db:integrity", "high", "pass",
                   "Integrity check passed")
    except Exception as e:
        _check(report, "db:integrity", "critical", "error",
               f"Integrity check failed: {e}")
    finally:
        conn.close()


def _check_wal_status(report: DoctorReport, db_path: Path) -> None:
    wal = db_path.with_suffix(".db-wal")
    shm = db_path.with_suffix(".db-shm")
    details = {}
    if wal.exists():
        details["wal_size"] = wal.stat().st_size
    if shm.exists():
        details["shm_size"] = shm.stat().st_size
    if details:
        _check(report, "db:wal_status", "low", "warn",
               f"WAL/SHM files present: {details}",
               evidence=details,
               safe_action="Run PRAGMA wal_checkpoint or open/close cleanly.")
    else:
        _check(report, "db:wal_status", "low", "pass",
               "No WAL/SHM residuals")


def _check_tables_and_indexes(report: DoctorReport, db_path: Path) -> None:
    conn = _db_ok(report, db_path)
    if conn is None:
        return
    try:
        tables = {r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
        expected_tables = {"run_history", "source_health", "snapshot_metadata",
                           "alert_candidates", "schema_version"}
        missing_tables = expected_tables - tables
        if missing_tables:
            _check(report, "db:tables", "critical", "fail",
                   f"Missing tables: {missing_tables}",
                   evidence={"present": list(tables), "missing": list(missing_tables)})
        else:
            _check(report, "db:tables", "high", "pass",
                   f"All {len(expected_tables)} tables present")

        indexes = {r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='index'").fetchall()}
        expected_indexes = {"idx_run_history_status", "idx_run_history_started",
                            "idx_run_history_parent", "idx_run_history_parent_ordinal",
                            "idx_run_history_kind"}
        missing_idx = expected_indexes - indexes
        if missing_idx:
            _check(report, "db:indexes", "medium", "warn",
                   f"Missing indexes: {missing_idx}",
                   evidence={"present": list(indexes), "missing": list(missing_idx)})
        else:
            _check(report, "db:indexes", "medium", "pass",
                   "All expected indexes present")
    except Exception as e:
        _check(report, "db:tables", "high", "error", f"Table scan failed: {e}")
    finally:
        conn.close()


def _check_parent_child_integrity(report: DoctorReport, db_path: Path) -> None:
    conn = _db_ok(report, db_path)
    if conn is None:
        return
    try:
        parents = conn.execute(
            "SELECT run_id, status, summary_json FROM run_history WHERE run_kind='shadow_parent'"
        ).fetchall()
        for p in parents:
            parent_id = p["run_id"]
            children = conn.execute(
                "SELECT run_id, status, run_ordinal FROM run_history WHERE parent_run_id=? ORDER BY run_ordinal",
                (parent_id,),
            ).fetchall()
            # Check parent summary matches children
            try:
                summary = json.loads(p["summary_json"]) if p["summary_json"] else {}
            except (json.JSONDecodeError, TypeError):
                summary = {}
            child_records = summary.get("child_records", [])
            if len(child_records) != len(children):
                _check(report, f"parent_child:count_{parent_id[:12]}", "medium", "warn",
                       f"Parent {parent_id[:12]}: summary has {len(child_records)} records "
                       f"but DB has {len(children)} children",
                       evidence={"parent_run_id": parent_id})
        _check(report, "parent_child:integrity", "medium", "pass",
               f"Checked {len(parents)} parents")
    except Exception as e:
        _check(report, "parent_child:integrity", "high", "error",
               f"Parent-child check failed: {e}")
    finally:
        conn.close()


def _check_duplicate_ordinals(report: DoctorReport, db_path: Path) -> None:
    conn = _db_ok(report, db_path)
    if conn is None:
        return
    try:
        dups = conn.execute("""
            SELECT parent_run_id, run_ordinal, COUNT(*), GROUP_CONCAT(run_id)
            FROM run_history
            WHERE parent_run_id IS NOT NULL AND run_ordinal IS NOT NULL
            GROUP BY parent_run_id, run_ordinal
            HAVING COUNT(*) > 1
        """).fetchall()
        if dups:
            for d in dups:
                _check(report, f"ordinal:dup_{d['parent_run_id'][:12]}_{d['run_ordinal']}",
                       "critical", "fail",
                       f"Duplicate ordinal {d['run_ordinal']} for parent {d['parent_run_id'][:12]}",
                       evidence={"parent_run_id": d["parent_run_id"],
                                  "ordinal": d["run_ordinal"],
                                  "count": d["COUNT(*)"],
                                  "run_ids": d["GROUP_CONCAT(run_id)"]})
        else:
            _check(report, "ordinal:duplicates", "medium", "pass",
                   "No duplicate ordinals")
    except Exception as e:
        _check(report, "ordinal:duplicates", "high", "error", str(e))
    finally:
        conn.close()


def _check_orphan_children(report: DoctorReport, db_path: Path) -> None:
    conn = _db_ok(report, db_path)
    if conn is None:
        return
    try:
        orphans = conn.execute("""
            SELECT c.run_id, c.parent_run_id
            FROM run_history c
            WHERE c.parent_run_id IS NOT NULL
              AND c.parent_run_id NOT IN (SELECT run_id FROM run_history)
        """).fetchall()
        if orphans:
            for o in orphans:
                _check(report, f"orphan:{o['run_id'][:12]}", "high", "fail",
                       f"Child {o['run_id'][:12]} references missing parent {o['parent_run_id'][:12]}",
                       evidence={"child_run_id": o["run_id"],
                                  "missing_parent": o["parent_run_id"]})
        else:
            _check(report, "orphan:children", "medium", "pass",
                   "No orphan children")
    except Exception as e:
        _check(report, "orphan:children", "high", "error", str(e))
    finally:
        conn.close()


def _check_unfinished_runs(report: DoctorReport, db_path: Path) -> None:
    conn = _db_ok(report, db_path)
    if conn is None:
        return
    try:
        unfinished = conn.execute(
            "SELECT run_id, runner_label, status, started_at FROM run_history "
            "WHERE finished_at IS NULL"
        ).fetchall()
        if unfinished:
            for u in unfinished:
                _check(report, f"unfinished:{u['run_id'][:12]}", "medium", "warn",
                       f"Run {u['run_id'][:12]} ({u['runner_label']}) started at "
                       f"{u['started_at']} has no finished_at",
                       evidence={"run_id": u["run_id"], "started_at": u["started_at"]})
        else:
            _check(report, "unfinished:runs", "medium", "pass",
                   "No unfinished runs")
    except Exception as e:
        _check(report, "unfinished:runs", "high", "error", str(e))
    finally:
        conn.close()


def _check_abnormal_statuses(report: DoctorReport, db_path: Path) -> None:
    conn = _db_ok(report, db_path)
    if conn is None:
        return
    try:
        abnormal = conn.execute(
            "SELECT run_id, status FROM run_history "
            "WHERE status NOT IN ('completed','degraded','failed','stopped','started','ok')"
        ).fetchall()
        for a in abnormal:
            _check(report, f"abnormal_status:{a['run_id'][:12]}", "medium", "warn",
                   f"Abnormal status '{a['status']}' on {a['run_id'][:12]}",
                   evidence={"run_id": a["run_id"], "status": a["status"]})
        if not abnormal:
            _check(report, "status:abnormal", "low", "pass",
                   "All statuses are recognised")
    except Exception as e:
        _check(report, "status:abnormal", "high", "error", str(e))
    finally:
        conn.close()


def _check_time_travel(report: DoctorReport, db_path: Path) -> None:
    conn = _db_ok(report, db_path)
    if conn is None:
        return
    try:
        rows = conn.execute(
            "SELECT run_id, started_at, finished_at FROM run_history "
            "WHERE finished_at IS NOT NULL AND finished_at < started_at "
            "LIMIT 10"
        ).fetchall()
        if rows:
            for r in rows:
                _check(report, f"time_travel:{r['run_id'][:12]}", "medium", "warn",
                       f"Run {r['run_id'][:12]} finished before it started",
                       evidence={"run_id": r["run_id"],
                                  "started_at": r["started_at"],
                                  "finished_at": r["finished_at"]})
        else:
            _check(report, "time:travel", "low", "pass",
                   "No time-travel anomalies")
    except Exception as e:
        _check(report, "time:travel", "high", "error", str(e))
    finally:
        conn.close()


def _check_summary_json(report: DoctorReport, db_path: Path) -> None:
    conn = _db_ok(report, db_path)
    if conn is None:
        return
    try:
        bad = 0
        rows = conn.execute(
            "SELECT run_id, summary_json FROM run_history "
            "WHERE summary_json IS NOT NULL"
        ).fetchall()
        for r in rows:
            try:
                json.loads(r["summary_json"])
            except (json.JSONDecodeError, TypeError):
                bad += 1
                _check(report, f"summary_json:{r['run_id'][:12]}", "medium", "fail",
                       f"Corrupt summary_json on {r['run_id'][:12]}",
                       evidence={"run_id": r["run_id"]})
        if bad == 0:
            _check(report, "summary:json", "medium", "pass",
                   f"All {len(rows)} summary_json fields valid")
    except Exception as e:
        _check(report, "summary:json", "high", "error", str(e))
    finally:
        conn.close()


def _check_source_health(report: DoctorReport, db_path: Path) -> None:
    conn = _db_ok(report, db_path)
    if conn is None:
        return
    try:
        rows = conn.execute(
            "SELECT source_name, health_status, error_message FROM source_health "
            "WHERE health_status != 'ok' LIMIT 20"
        ).fetchall()
        if rows:
            for r in rows:
                _check(report, f"source_health:{r['source_name']}", "medium", "warn",
                       f"Source '{r['source_name']}' status={r['health_status']}",
                       evidence={"source": r["source_name"],
                                  "status": r["health_status"],
                                  "error": r["error_message"]})
        else:
            _check(report, "source_health:all", "low", "pass",
                   "All sources healthy")
    except Exception as e:
        _check(report, "source_health:all", "high", "error", str(e))
    finally:
        conn.close()


def _check_lock(report: DoctorReport, state_dir: Path) -> None:
    lock_path = state_dir / "bounded_shadow.lock"
    if lock_path.exists():
        try:
            data = lock_path.read_text(encoding="utf-8").strip()
            _check(report, "lock:exists", "low", "warn",
                   f"Lock file present: {data[:60]}",
                   evidence={"lock_path": str(lock_path), "content": data},
                   safe_action="Verify no shadow is running, then remove the lock file.")
        except Exception as e:
            _check(report, "lock:exists", "low", "warn",
                   f"Lock file present but unreadable: {e}")
    else:
        _check(report, "lock:exists", "low", "pass", "No lock file")


def _check_stop_marker(report: DoctorReport, state_dir: Path) -> None:
    stop_path = state_dir / "STOP"
    if stop_path.exists():
        _check(report, "stop_marker:exists", "low", "warn",
               "STOP marker present — shadow runs will not start",
               evidence={"path": str(stop_path)},
               safe_action="Remove STOP file to allow new runs.")
    else:
        _check(report, "stop_marker:exists", "low", "pass", "No STOP marker")


def _check_db_file_checksum(report: DoctorReport, db_path: Path) -> None:
    if not db_path.exists():
        return
    try:
        h = hashlib.sha256()
        with open(db_path, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                h.update(chunk)
        _check(report, "db:sha256", "info", "pass",
               f"SHA256: {h.hexdigest()[:32]}...",
               evidence={"sha256_prefix": h.hexdigest()[:32]})
    except Exception as e:
        _check(report, "db:sha256", "low", "error", f"Checksum failed: {e}")


def _check_path_leak(report: DoctorReport, db_path: Path) -> None:
    """Detect absolute Windows/POSIX paths in run_history fields."""
    conn = _db_ok(report, db_path)
    if conn is None:
        return
    try:
        import re
        leaked: list[dict] = []
        rows = conn.execute(
            "SELECT run_id, summary_json, error FROM run_history "
            "WHERE summary_json IS NOT NULL OR error IS NOT NULL"
        ).fetchall()
        for r in rows:
            text = (r["summary_json"] or "") + " " + (r["error"] or "")
            # Windows path: C:\...  or  /absolute/path
            win_paths = re.findall(r"[A-Za-z]:\\[^\s:,)]{5,}", text)
            posix_paths = re.findall(r"/[a-z]{2,}/[^\s:,)]{5,}", text.lower())
            if win_paths or posix_paths:
                leaked.append({
                    "run_id": r["run_id"],
                    "windows_paths": win_paths[:3],
                    "posix_paths": posix_paths[:3],
                })
        if leaked:
            _check(report, "security:path_leak", "medium", "warn",
                   f"Found {len(leaked)} run(s) with absolute paths",
                   evidence={"leaked_runs": leaked[:5]})
        else:
            _check(report, "security:path_leak", "medium", "pass",
                   "No absolute paths detected")
    except Exception as e:
        _check(report, "security:path_leak", "high", "error", str(e))
    finally:
        conn.close()


def _check_sensitive_key_in_summary(report: DoctorReport, db_path: Path) -> None:
    """Detect potential sensitive keys in summary_json."""
    conn = _db_ok(report, db_path)
    if conn is None:
        return
    sensitive_patterns = {"token", "secret", "password", "api_key", "authorization",
                          "private_key", "credential"}
    try:
        import json as _json
        flagged = 0
        rows = conn.execute(
            "SELECT run_id, summary_json FROM run_history WHERE summary_json IS NOT NULL"
        ).fetchall()
        for r in rows:
            try:
                obj = _json.loads(r["summary_json"])
                if isinstance(obj, dict):
                    for key in obj:
                        if any(p in key.lower() for p in sensitive_patterns):
                            flagged += 1
            except (json.JSONDecodeError, TypeError):
                pass
        if flagged:
            _check(report, "security:sensitive_key", "medium", "warn",
                   f"Found {flagged} summary run(s) with potentially sensitive keys",
                   evidence={"flagged_count": flagged})
        else:
            _check(report, "security:sensitive_key", "medium", "pass",
                   "No sensitive keys detected")
    except Exception as e:
        _check(report, "security:sensitive_key", "high", "error", str(e))
    finally:
        conn.close()


def _check_artifact_checksum(report: DoctorReport, state_dir: Path,
                              db_path: Path, enabled: bool) -> None:
    """Check file checksums against stored artifacts (if any)."""
    if not enabled:
        return
    if not db_path.exists():
        return
    import hashlib
    try:
        h = hashlib.sha256()
        with open(db_path, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                h.update(chunk)
        _check(report, "artifact:db_checksum", "info", "pass",
               f"DB SHA256: {h.hexdigest()[:16]}...",
               evidence={"sha256_prefix": h.hexdigest()[:16]})
    except Exception as e:
        _check(report, "artifact:db_checksum", "low", "error", str(e))


# ---------------------------------------------------------------------------
# Doctor result summary
# ---------------------------------------------------------------------------


def doctor_summary(report: DoctorReport) -> dict[str, Any]:
    return {
        "total": report.total,
        "passed": report.passed,
        "warnings": report.warnings,
        "failures": report.failures,
        "errors": report.errors,
        "checks": [
            {
                "check_id": c.check_id,
                "status": c.status,
                "severity": c.severity,
                "message": c.message,
            }
            for c in report.checks
        ],
    }
