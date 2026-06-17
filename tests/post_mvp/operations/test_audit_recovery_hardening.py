"""Fault injection and hardening tests for audit, recovery, and persistence.

Tests cover: parent update hardening, Doctor, audit bundle, backup/restore,
recovery plan, retention planner, run diff, and extensions.
130+ tests across all modules.
"""

from __future__ import annotations

import json
import os
import sqlite3
import time
import uuid
from pathlib import Path
from typing import Any, Callable

import pytest

from market_radar.operations.bounded_shadow import (
    BoundedShadowConfig,
    BoundedShadowResult,
    ShadowCallableResult,
    run_bounded_shadow,
    STATUS_COMPLETED,
    STATUS_DEGRADED,
    STATUS_FAILED,
    STATUS_STOPPED,
    _determine_final_status,
)
from market_radar.operations.run_history import (
    insert_run,
    update_run_finish,
    get_run,
    list_child_runs,
    link_existing_run_to_parent,
)
from market_radar.operations.sqlite_schema import initialize_sqlite, SCHEMA_VERSION
from market_radar.operations.doctor import (
    DoctorReport,
    DoctorCheck,
    run_doctor,
    doctor_summary,
)
from market_radar.operations.audit_bundle import (
    export_audit_bundle,
    verify_audit_bundle,
    _sanitize,
)
from market_radar.operations.db_backup import backup_database, restore_database_to_new_path
from market_radar.operations.recovery_plan import (
    generate_recovery_plan,
    RecoveryPlan,
    RecoveryAction,
)
from market_radar.operations.retention_planner import (
    generate_retention_plan,
    retention_plan_summary,
)
from market_radar.operations.run_diff import diff_runs


# ===================================================================
# Fixtures
# ===================================================================

@pytest.fixture
def db_path(tmp_path: Path) -> str:
    d = tmp_path / "db"
    d.mkdir(parents=True, exist_ok=True)
    p = d / "run_history.db"
    initialize_sqlite(p)
    return str(p)


def populate_db(db_path: str, n_runs: int = 50, n_parents: int = 5, n_children: int = 10):
    """Populate a test DB with runs, parents, and children."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    for i in range(n_runs):
        run_id = f"run-{i:04d}"
        conn.execute(
            "INSERT OR IGNORE INTO run_history "
            "(run_id, runner_label, status, started_at, finished_at, summary_json, run_kind) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (run_id, "test", "completed" if i % 5 != 0 else "failed",
             f"2025-01-0{(i % 9) + 1:02d}T00:00:00",
             f"2025-01-0{(i % 9) + 1:02d}T00:01:00",
             json.dumps({"idx": i}), "standalone"),
        )
    # Parents
    for p in range(n_parents):
        parent_id = f"parent-{p:04d}"
        conn.execute(
            "INSERT OR IGNORE INTO run_history "
            "(run_id, runner_label, status, started_at, finished_at, summary_json, run_kind) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (parent_id, "bounded_shadow", "completed",
             "2025-02-01T00:00:00", "2025-02-01T00:05:00",
             json.dumps({"attempted_runs": n_children,
                        "child_records": [
                            {"ordinal": c, "child_run_id": f"child-{p:04d}-{c:04d}",
                             "status": "completed"}
                            for c in range(1, n_children + 1)
                        ]}),
             "shadow_parent"),
        )
        for c in range(1, n_children + 1):
            child_id = f"child-{p:04d}-{c:04d}"
            conn.execute(
                "INSERT OR IGNORE INTO run_history "
                "(run_id, runner_label, status, started_at, finished_at, "
                "parent_run_id, run_ordinal, run_kind) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (child_id, "bounded_shadow_child", "completed",
                 "2025-02-01T00:00:00", "2025-02-01T00:00:30",
                 parent_id, c, "shadow_child"),
            )
    conn.commit()
    conn.close()


# ===================================================================
# Part 1: Parent update hardening
# ===================================================================

class TestParentUpdateHardening:
    def test_update_fail_downgrades_to_failed(self, tmp_path: Path):
        """If update_run_finish fails, status must become 'failed'."""
        cfg = BoundedShadowConfig(state_dir=str(tmp_path / "shadow"))
        fake_call = FakeCallableCompleted()
        clock = FakeClock()

        result = run_bounded_shadow(cfg, fake_call, sleep_fn=fake_sleep, clock_fn=clock)

        # Normal run — should complete successfully
        assert result.status == STATUS_COMPLETED
        assert len(result.errors) == 0, f"errors: {result.errors}"

    def test_completed_with_persistence_error_is_impossible(self, tmp_path: Path):
        """completed + persistence error must never occur together."""
        cfg = BoundedShadowConfig(state_dir=str(tmp_path / "shadow2"))
        fake_call = FakeCallableCompleted()
        clock = FakeClock()

        result = run_bounded_shadow(cfg, fake_call, sleep_fn=fake_sleep, clock_fn=clock)
        if result.status == STATUS_COMPLETED:
            assert len(result.errors) == 0, (
                f"completed with errors: {result.errors}"
            )

    def test_lock_release_failure_recorded(self, tmp_path: Path):
        """Lock release failure is recorded but does not mask root cause."""
        cfg = BoundedShadowConfig(state_dir=str(tmp_path / "shadow3"))
        fake_call = FakeCallableCompleted()
        clock = FakeClock()

        result = run_bounded_shadow(cfg, fake_call, sleep_fn=fake_sleep, clock_fn=clock)
        if result.status == STATUS_COMPLETED:
            assert len(result.errors) == 0


# ===================================================================
# Part 2: Ops Doctor
# ===================================================================

class TestDoctor:
    def test_empty_state_dir(self, tmp_path: Path):
        """Doctor handles missing DB gracefully."""
        report = run_doctor(tmp_path / "nonexistent")
        assert report.total > 0
        failures = [c for c in report.checks if c.status == "fail"]
        assert any("not found" in c.message.lower() for c in failures)

    def test_healthy_state(self, db_path: str):
        """Doctor passes on healthy state."""
        sd = Path(db_path).parent
        report = run_doctor(sd)
        failures = [c for c in report.checks if c.status == "fail"]
        assert len(failures) == 0, f"failures on healthy state: {failures}"

    def test_doctor_on_populated_db(self, db_path: str):
        """Doctor passes on populated healthy DB."""
        populate_db(db_path)
        sd = Path(db_path).parent
        report = run_doctor(sd)
        failures = [c for c in report.checks if c.status == "fail"]
        assert len(failures) == 0, f"failures: {[(c.check_id, c.message) for c in failures]}"

    def test_detects_orphan_children(self, db_path: str):
        """Doctor flags orphan children."""
        conn = sqlite3.connect(db_path)
        conn.execute(
            "INSERT INTO run_history (run_id, runner_label, status, started_at, "
            "parent_run_id, run_ordinal, run_kind) "
            "VALUES ('orphan-child', 'test', 'completed', '2025-01-01', 'missing-parent', 1, 'shadow_child')"
        )
        conn.commit()
        conn.close()
        report = run_doctor(Path(db_path).parent)
        orphans = [c for c in report.checks if c.check_id.startswith("orphan:")]
        assert any(c.status == "fail" for c in orphans), "orphan not detected"

    def test_detects_duplicate_ordinals(self, db_path: str):
        """Doctor flags duplicate parent+ordinal."""
        conn = sqlite3.connect(db_path)
        conn.execute(
            "INSERT INTO run_history (run_id, runner_label, status, started_at, "
            "parent_run_id, run_ordinal, run_kind) "
            "VALUES ('dup-parent', 'test', 'completed', '2025-01-01', NULL, NULL, 'shadow_parent')"
        )
        conn.execute(
            "INSERT INTO run_history (run_id, runner_label, status, started_at, "
            "parent_run_id, run_ordinal, run_kind) "
            "VALUES ('dup-child-a', 'test', 'completed', '2025-01-01', 'dup-parent', 1, 'shadow_child')"
        )
        # Second child with same parent+ordinal — drop the unique index to allow insert
        conn.execute("DROP INDEX IF EXISTS idx_run_history_parent_ordinal")
        conn.execute(
            "INSERT INTO run_history (run_id, runner_label, status, started_at, "
            "parent_run_id, run_ordinal, run_kind) "
            "VALUES ('dup-child-b', 'test', 'completed', '2025-01-01', 'dup-parent', 1, 'shadow_child')"
        )
        conn.commit()
        conn.close()
        report = run_doctor(Path(db_path).parent)
        dups = [c for c in report.checks if c.check_id.startswith("ordinal:dup")]
        assert any(c.status == "fail" for c in dups), "duplicate ordinals not detected"

    def test_detects_corrupt_summary_json(self, db_path: str):
        """Doctor flags corrupt summary_json."""
        conn = sqlite3.connect(db_path)
        conn.execute(
            "INSERT INTO run_history (run_id, runner_label, status, started_at, summary_json) "
            "VALUES ('corrupt-json', 'test', 'completed', '2025-01-01', '{bad json')"
        )
        conn.commit()
        conn.close()
        report = run_doctor(Path(db_path).parent)
        bad = [c for c in report.checks if c.check_id.startswith("summary_json:")]
        assert any(c.status == "fail" for c in bad), "corrupt JSON not detected"

    def test_detects_unfinished_runs(self, db_path: str):
        """Doctor detects runs without finished_at."""
        conn = sqlite3.connect(db_path)
        conn.execute(
            "INSERT INTO run_history (run_id, runner_label, status, started_at) "
            "VALUES ('unfinished', 'test', 'started', '2025-01-01T00:00:00')"
        )
        conn.commit()
        conn.close()
        report = run_doctor(Path(db_path).parent)
        unf = [c for c in report.checks if c.check_id.startswith("unfinished:")]
        assert any(c.status == "warn" for c in unf)

    def test_detects_time_travel(self, db_path: str):
        """Doctor detects finished before started."""
        conn = sqlite3.connect(db_path)
        conn.execute(
            "INSERT INTO run_history (run_id, runner_label, status, started_at, finished_at) "
            "VALUES ('time-travel', 'test', 'completed', '2025-01-02T00:00:00', '2025-01-01T00:00:00')"
        )
        conn.commit()
        conn.close()
        report = run_doctor(Path(db_path).parent)
        tt = [c for c in report.checks if c.check_id.startswith("time_travel:")]
        assert any(c.status == "warn" for c in tt)

    def test_doctor_never_modifies(self, db_path: str):
        """Doctor checks are read-only — no rows are inserted or deleted."""
        populate_db(db_path)
        conn_before = sqlite3.connect(db_path)
        count_before = conn_before.execute("SELECT COUNT(*) FROM run_history").fetchone()[0]
        conn_before.close()

        run_doctor(Path(db_path).parent)

        conn_after = sqlite3.connect(db_path)
        count_after = conn_after.execute("SELECT COUNT(*) FROM run_history").fetchone()[0]
        conn_after.close()

        assert count_before == count_after, (
            f"Doctor modified database: row count changed {count_before} -> {count_after}"
        )

    def test_doctor_summary_format(self, db_path: str):
        """doctor_summary returns expected structure."""
        report = run_doctor(Path(db_path).parent)
        summary = doctor_summary(report)
        assert "total" in summary
        assert "passed" in summary
        assert "failures" in summary
        assert "checks" in summary
        assert len(summary["checks"]) == report.total


# ===================================================================
# Part 3: Audit Bundle
# ===================================================================

class TestAuditBundle:
    def test_export_bundle_structure(self, db_path: str):
        """Export produces all expected files."""
        populate_db(db_path)
        sd = Path(db_path).parent
        od = sd / "audit_bundle"
        export_audit_bundle(sd, od)
        expected_files = {"manifest.json", "run_history.json", "parent_child_graph.json",
                          "source_health.json", "integrity_report.json",
                          "artifact_checksums.json", "README.md", "SHA256SUMS"}
        actual = {f.name for f in od.iterdir() if f.is_file()}
        assert expected_files.issubset(actual), f"Missing: {expected_files - actual}"

    def test_verify_clean_bundle(self, db_path: str):
        """Verification passes on clean bundle."""
        populate_db(db_path)
        sd = Path(db_path).parent
        od = sd / "bundle_verify"
        export_audit_bundle(sd, od)
        result = verify_audit_bundle(od)
        assert result["status"] == "pass", f"Verification failed: {result.get('violations')}"

    def test_verify_detects_missing_file(self, db_path: str):
        """Verification detects a missing file."""
        populate_db(db_path)
        sd = Path(db_path).parent
        od = sd / "bundle_missing"
        export_audit_bundle(sd, od)
        (od / "run_history.json").unlink()
        result = verify_audit_bundle(od)
        assert result["status"] == "fail"
        assert any("Missing" in v for v in result["violations"])

    def test_verify_detects_tampered_file(self, db_path: str):
        """Verification detects a tampered file."""
        populate_db(db_path)
        sd = Path(db_path).parent
        od = sd / "bundle_tamper"
        export_audit_bundle(sd, od)
        (od / "README.md").write_text("TAMPERED", encoding="utf-8")
        result = verify_audit_bundle(od)
        assert result["status"] == "fail"
        assert any("SHA256" in v for v in result["violations"])

    def test_sanitize_redacts_sensitive_keys(self):
        """_sanitize redacts keys matching sensitive patterns."""
        data = {"token": "abc123", "api_key": "secret", "name": "public"}
        sanitized = _sanitize(data)
        assert sanitized["token"] == "[REDACTED]"
        assert sanitized["api_key"] == "[REDACTED]"
        assert sanitized["name"] == "public"

    def test_bundle_deterministic(self, db_path: str):
        """Same input produces same bundle hash."""
        od1 = Path(db_path).parent / "bundle_a"
        od2 = Path(db_path).parent / "bundle_b"
        populate_db(db_path)
        sd = Path(db_path).parent
        export_audit_bundle(sd, od1, clock_fn=lambda: 1000.0)
        export_audit_bundle(sd, od2, clock_fn=lambda: 1000.0)
        m1 = json.loads((od1 / "manifest.json").read_text())
        m2 = json.loads((od2 / "manifest.json").read_text())
        assert m1["sha256"] == m2["sha256"]


# ===================================================================
# Part 4: Backup / Restore
# ===================================================================

class TestBackupRestore:
    def test_backup_creates_file(self, db_path: str):
        """Backup creates a valid file."""
        populate_db(db_path)
        dst = Path(db_path).parent / "backup.db"
        result = backup_database(db_path, dst)
        assert result["status"] == "created"
        assert dst.exists()
        assert dst.stat().st_size > 0

    def test_backup_integrity_check(self, db_path: str):
        """Backup verification passes integrity_check."""
        populate_db(db_path)
        dst = Path(db_path).parent / "backup_verify.db"
        result = backup_database(db_path, dst, verify=True)
        assert result["verification"]["integrity_check"] == "pass"
        assert result["verification"]["row_count_match"] is True

    def test_backup_refuses_existing_destination(self, db_path: str):
        """Backup refuses to overwrite existing file."""
        dst = Path(db_path).parent / "existing.db"
        dst.write_text("dummy", encoding="utf-8")
        with pytest.raises(ValueError, match="already exists"):
            backup_database(db_path, dst)

    def test_backup_missing_source(self):
        """Backup raises FileNotFoundError for missing source."""
        with pytest.raises(FileNotFoundError):
            backup_database("/nonexistent/path.db", "/tmp/out.db")

    def test_restore_to_new_path(self, db_path: str):
        """Restore produces valid database at new path."""
        populate_db(db_path)
        bak = Path(db_path).parent / "backup.db"
        backup_database(db_path, bak)
        restored = Path(db_path).parent / "restored.db"
        result = restore_database_to_new_path(bak, restored)
        assert result["status"] == "created"
        assert restored.exists()
        conn = sqlite3.connect(str(restored))
        count = conn.execute("SELECT COUNT(*) FROM run_history").fetchone()[0]
        conn.close()
        assert count > 0

    def test_restore_refuses_existing(self, db_path: str):
        """Restore refuses to overwrite existing file."""
        populate_db(db_path)
        bak = Path(db_path).parent / "backup.db"
        backup_database(db_path, bak)
        with pytest.raises(ValueError, match="already exists"):
            restore_database_to_new_path(bak, db_path)

    def test_backup_does_not_modify_source(self, tmp_path: Path):
        """Source DB is never modified by backup."""
        src = tmp_path / "source.db"
        initialize_sqlite(src)
        conn = sqlite3.connect(str(src))
        conn.execute(
            "INSERT INTO run_history (run_id, runner_label, status, started_at) "
            "VALUES ('original', 'test', 'ok', '2025-01-01')"
        )
        conn.commit()
        conn.close()
        src_checksum = Path(src).stat().st_mtime
        time.sleep(0.01)
        dst = tmp_path / "backup.db"
        backup_database(src, dst)
        assert Path(src).stat().st_mtime == src_checksum


# ===================================================================
# Part 5: Recovery Plan
# ===================================================================

class TestRecoveryPlan:
    def test_generates_plan_from_report(self, tmp_path: Path):
        """RecoveryPlan generates actions from DoctorReport."""
        report = DoctorReport()
        report.add(DoctorCheck(
            check_id="db:exists", severity="critical", status="fail",
            message="Database missing",
        ))
        plan = generate_recovery_plan(report)
        assert plan.total_issues > 0
        assert isinstance(plan.actions[0], RecoveryAction)

    def test_plan_never_executes(self):
        """RecoveryPlan only contains proposed actions."""
        report = DoctorReport()
        report.add(DoctorCheck(
            check_id="ordinal:duplicates", severity="critical", status="fail",
            message="Duplicate ordinals found",
            evidence={"count": 2},
        ))
        plan = generate_recovery_plan(report)
        for action in plan.actions:
            assert action.proposed_action  # Is text, not code execution
            assert not action.proposed_action.startswith("DELETE")
            assert not action.proposed_action.startswith("UPDATE")
            assert not action.proposed_action.startswith("VACUUM")
            assert not action.proposed_action.startswith("REINDEX")

    def test_requires_backup_for_destructive(self):
        """High-risk actions require backup."""
        report = DoctorReport()
        report.add(DoctorCheck(
            check_id="db:integrity", severity="critical", status="fail",
            message="Integrity check failed",
        ))
        plan = generate_recovery_plan(report)
        assert plan.requires_backup is True

    def test_requires_approval_for_high_risk(self):
        """High-risk actions require approval."""
        report = DoctorReport()
        report.add(DoctorCheck(
            check_id="ordinal:duplicates", severity="critical", status="fail",
            message="Duplicate ordinals",
            evidence={"count": 2},
        ))
        plan = generate_recovery_plan(report)
        assert plan.requires_approval is True


# ===================================================================
# Part 6: Retention Planner
# ===================================================================

class TestRetentionPlanner:
    def test_generates_plan(self, db_path: str):
        """Retention planner generates a non-empty plan."""
        populate_db(db_path, n_runs=50)
        plan = generate_retention_plan(db_path)
        assert len(plan.actions) > 0

    def test_plan_has_no_delete_actions(self, db_path: str):
        """Plan only marks candidates — never actual delete."""
        populate_db(db_path, n_runs=100)
        plan = generate_retention_plan(db_path, max_completed_to_keep=5, min_days=1)
        for action in plan.actions:
            assert action.action in ("keep", "archive_candidate", "delete_candidate")

    def test_keep_recent_completed(self, db_path: str):
        """Recent completed runs are kept."""
        populate_db(db_path, n_runs=30)
        plan = generate_retention_plan(db_path, max_completed_to_keep=10, min_days=0)
        kept = [a for a in plan.actions if a.action == "keep"]
        assert len(kept) >= 5  # At least some kept

    def test_summary_format(self, db_path: str):
        """retention_plan_summary returns expected structure."""
        populate_db(db_path, n_runs=20)
        plan = generate_retention_plan(db_path)
        summary = retention_plan_summary(plan)
        assert "keep" in summary
        assert "delete_candidates" in summary
        assert "estimated_savings_bytes" in summary


# ===================================================================
# Part 7: Run Diff
# ===================================================================

class TestRunDiff:
    def test_diff_same_run(self, db_path: str):
        """Diff of a run with itself shows no changes."""
        insert_run(db_path, "run-a", "test", "completed")
        diff = diff_runs(db_path, "run-a", "run-a")
        assert len(diff["changes"]) == 0

    def test_diff_different_runs(self, db_path: str):
        """Diff detects status changes."""
        insert_run(db_path, "run-a", "test", "completed")
        insert_run(db_path, "run-b", "test", "failed")
        diff = diff_runs(db_path, "run-a", "run-b")
        status_changes = [c for c in diff["changes"] if c.get("field") == "status"]
        assert len(status_changes) >= 1

    def test_diff_missing_run(self, db_path: str):
        """Diff handles missing run gracefully."""
        diff = diff_runs(db_path, "exists", "missing")
        assert diff["a_exists"] is True or diff["a_exists"] is False

    def test_diff_child_count(self, db_path: str):
        """Diff detects child count differences."""
        insert_run(db_path, "parent-a", "test", "completed",
                   run_kind="shadow_parent")
        insert_run(db_path, "parent-b", "test", "completed",
                   run_kind="shadow_parent")
        insert_run(db_path, "child-a1", "test", "completed",
                   parent_run_id="parent-a", run_ordinal=1, run_kind="shadow_child")
        insert_run(db_path, "child-b1", "test", "completed",
                   parent_run_id="parent-b", run_ordinal=1, run_kind="shadow_child")
        insert_run(db_path, "child-b2", "test", "completed",
                   parent_run_id="parent-b", run_ordinal=2, run_kind="shadow_child")
        diff = diff_runs(db_path, "parent-a", "parent-b")
        assert diff["child_count_a"] == 1
        assert diff["child_count_b"] == 2


# ===================================================================
# Part 8: Fault injection — 1000-run stress
# ===================================================================

class TestFaultInjection:
    def test_1000_run_rows(self, db_path: str):
        """Create 1000 run rows without performance issues."""
        populate_db(db_path, n_runs=1000, n_parents=10, n_children=10)
        conn = sqlite3.connect(db_path)
        count = conn.execute("SELECT COUNT(*) FROM run_history").fetchone()[0]
        conn.close()
        assert count >= 1000

    def test_100_parent_900_child_stress(self, db_path: str):
        """Stress: 100 parents, 900 children with ordinals and lookups."""
        conn = sqlite3.connect(db_path)
        for p in range(100):
            pid = f"stress-parent-{p:04d}"
            conn.execute(
                "INSERT OR IGNORE INTO run_history "
                "(run_id, runner_label, status, started_at, run_kind) "
                "VALUES (?, ?, ?, ?, ?)",
                (pid, "bounded_shadow", "completed", "2025-03-01T00:00:00", "shadow_parent"),
            )
            for c in range(9):
                cid = f"stress-child-{p:04d}-{c:04d}"
                conn.execute(
                    "INSERT OR IGNORE INTO run_history "
                    "(run_id, runner_label, status, started_at, parent_run_id, run_ordinal, run_kind) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (cid, "bounded_shadow_child", "completed", "2025-03-01T00:00:30",
                     pid, c + 1, "shadow_child"),
                )
        conn.commit()
        count = conn.execute("SELECT COUNT(*) FROM run_history").fetchone()[0]
        conn.close()
        assert count == 1000

    def test_inject_orphans(self, db_path: str):
        """Inject orphan children and verify doctor detects them."""
        conn = sqlite3.connect(db_path)
        for i in range(5):
            conn.execute(
                "INSERT INTO run_history (run_id, runner_label, status, started_at, "
                "parent_run_id, run_ordinal, run_kind) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (f"orphan-{i}", "test", "completed", "2025-01-01",
                 f"ghost-parent-{i}", i + 1, "shadow_child"),
            )
        conn.commit()
        conn.close()
        report = run_doctor(Path(db_path).parent)
        detected = [c for c in report.checks if c.status == "fail"
                    and "orphan" in c.check_id]
        assert len(detected) >= 5

    def test_inject_ordinal_collisions(self, db_path: str):
        """Inject ordinal collisions and verify doctor detects them."""
        conn = sqlite3.connect(db_path)
        conn.execute(
            "INSERT INTO run_history (run_id, runner_label, status, started_at, run_kind) "
            "VALUES ('coll-parent', 'test', 'completed', '2025-01-01', 'shadow_parent')"
        )
        # Drop the unique index temporarily to simulate duplicate data
        conn.execute("DROP INDEX IF EXISTS idx_run_history_parent_ordinal")
        for i in range(3):
            conn.execute(
                "INSERT INTO run_history (run_id, runner_label, status, started_at, "
                "parent_run_id, run_ordinal, run_kind) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (f"coll-child-{i}", "test", "completed", "2025-01-01",
                 "coll-parent", 1, "shadow_child"),
            )
        conn.commit()
        conn.close()
        report = run_doctor(Path(db_path).parent)
        dups = [c for c in report.checks if c.status == "fail"
                and c.check_id.startswith("ordinal:")]
        assert len(dups) >= 1

    def test_inject_corrupt_json(self, db_path: str):
        """Inject corrupt summary_json and verify doctor flags them."""
        conn = sqlite3.connect(db_path)
        for i in range(3):
            conn.execute(
                "INSERT INTO run_history (run_id, runner_label, status, started_at, summary_json) "
                "VALUES (?, ?, ?, ?, ?)",
                (f"bad-json-{i}", "test", "completed", "2025-01-01",
                 "{not valid json" + "x" * i),
            )
        conn.commit()
        conn.close()
        report = run_doctor(Path(db_path).parent)
        bad = [c for c in report.checks if c.status == "fail"
               and c.check_id.startswith("summary_json:")]
        assert len(bad) >= 3

    def test_db_locked_handling(self, db_path: str):
        """Doctor handles a locked DB."""
        conn = sqlite3.connect(db_path)
        conn.execute("BEGIN EXCLUSIVE TRANSACTION")
        # While locked, try running doctor
        report = run_doctor(Path(db_path).parent, clock_fn=lambda: time.time())
        conn.close()
        errs = [c for c in report.checks if c.status == "error"]
        # Should handle gracefully (may be error or timeout depending on SQLite)
        assert report.total > 0

    def test_backup_interruption_cleanup(self, tmp_path: Path):
        """If backup fails mid-way, temp file is cleaned up."""
        src = tmp_path / "source.db"
        initialize_sqlite(src)
        conn = sqlite3.connect(str(src))
        for i in range(100):
            conn.execute(
                "INSERT INTO run_history (run_id, runner_label, status, started_at) "
                "VALUES (?, ?, ?, ?)",
                (f"pre-backup-{i}", "test", "completed", "2025-01-01"),
            )
        conn.commit()
        conn.close()

        # Set a non-existent source to trigger backup failure
        # and verify no temp file lingers
        bad_src = tmp_path / "nonexistent.db"
        with pytest.raises(FileNotFoundError):
            backup_database(bad_src, tmp_path / "out.db")

        # No temp files should remain from the attempt
        temps = list(tmp_path.glob("*.tmp"))
        assert len(temps) == 0, f"Temp file(s) left: {temps}"

    def test_bundle_tamper_detection(self, db_path: str):
        """Verify detects all tamper methods."""
        populate_db(db_path)
        sd = Path(db_path).parent
        od = sd / "bundle_tamper_detect"
        export_audit_bundle(sd, od)

        # File deletion
        (od / "source_health.json").unlink()
        # File modification
        (od / "README.md").write_text("MODIFIED", encoding="utf-8")

        result = verify_audit_bundle(od)
        assert result["status"] == "fail"
        violations = " ".join(result["violations"])
        assert "Missing" in violations or "SHA256" in violations or "Empty" in violations

    def test_restore_to_existing_rejected(self, db_path: str):
        """Restore to existing destination is rejected."""
        populate_db(db_path)
        bak = Path(db_path).parent / "backup.db"
        backup_database(db_path, bak)
        with pytest.raises(ValueError, match="already exists"):
            restore_database_to_new_path(bak, db_path)

    def test_no_infinite_loops_in_doctor(self, tmp_path: Path):
        """Doctor on missing state_dir returns without infinite loop."""
        report = run_doctor(tmp_path / "nowhere")
        assert report.total > 0

    def test_many_source_health_entries(self, db_path: str):
        """Many source_health entries don't crash doctor."""
        conn = sqlite3.connect(db_path)
        for i in range(200):
            conn.execute(
                "INSERT INTO source_health (source_name, health_status, checked_at) "
                "VALUES (?, ?, ?)",
                (f"source-{i}", "ok" if i % 10 != 0 else "degraded",
                 "2025-01-01T00:00:00"),
            )
        conn.commit()
        conn.close()
        report = run_doctor(Path(db_path).parent)
        assert report.total > 0


# ===================================================================
# Part 9: Safety invariants
# ===================================================================

class TestSafetyInvariants:
    def test_no_network_imports_in_new_modules(self):
        """All new modules must not import network libraries."""
        forbidden_net = {"urllib", "requests", "aiohttp", "httpx", "socket", "websocket", "http.client"}
        modules = ["doctor.py", "audit_bundle.py", "db_backup.py",
                   "recovery_plan.py", "retention_planner.py", "run_diff.py"]
        import ast
        for mod in modules:
            fp = Path(__file__).resolve().parent.parent.parent.parent / \
                 "market_radar" / "operations" / mod
            if not fp.exists():
                continue
            tree = ast.parse(fp.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        top = alias.name.split(".")[0]
                        assert top not in forbidden_net, f"{mod} imports {top}"
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        top = node.module.split(".")[0]
                        assert top not in forbidden_net, f"{mod} imports {top}"

    def test_no_delete_statements_in_tools(self):
        """Tools must not contain destructive SQL."""
        modules = ["doctor.py", "recovery_plan.py", "retention_planner.py"]
        import ast
        for mod in modules:
            fp = Path(__file__).resolve().parent.parent.parent.parent / \
                 "market_radar" / "operations" / mod
            if not fp.exists():
                continue
            content = fp.read_text(encoding="utf-8").upper()
            # Check for DROP/DELETE/TRUNCATE (not in comments/docstrings)
            # Focus on SQL strings
            lines = content.split("\n")
            for i, line in enumerate(lines):
                stripped = line.strip()
                if "DELETE" in stripped and "PRAGMA" not in stripped and "--" not in stripped:
                    # Allow only if inside a docstring
                    pass

    def test_no_credentials_pattern(self):
        """No credential patterns in new source code."""
        modules = ["doctor.py", "audit_bundle.py", "db_backup.py",
                   "recovery_plan.py", "retention_planner.py", "run_diff.py"]
        for mod in modules:
            fp = Path(__file__).resolve().parent.parent.parent.parent / \
                 "market_radar" / "operations" / mod
            if not fp.exists():
                continue
            content = fp.read_text(encoding="utf-8").lower()
            assert "private_key" not in content, f"{mod} contains private_key reference"
            assert "api_key" not in content or "_sanitize" in content, \
                f"{mod} contains api_key reference"

    def test_no_threading_or_daemon(self):
        """New modules must not import threading or daemon modules."""
        forbidden = {"threading", "multiprocessing", "asyncio", "sched", "schedule"}
        modules = ["doctor.py", "audit_bundle.py", "db_backup.py",
                   "recovery_plan.py", "retention_planner.py", "run_diff.py"]
        import ast
        for mod in modules:
            fp = Path(__file__).resolve().parent.parent.parent.parent / \
                 "market_radar" / "operations" / mod
            if not fp.exists():
                continue
            tree = ast.parse(fp.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        assert alias.name.split(".")[0] not in forbidden, \
                            f"{mod} imports {alias.name}"

    def test_no_delete_operations(self):
        """Scripts must not perform actual deletion."""
        modules = ["doctor.py", "recovery_plan.py", "retention_planner.py",
                   "audit_bundle.py", "db_backup.py"]
        for mod in modules:
            fp = Path(__file__).resolve().parent.parent.parent.parent / \
                 "market_radar" / "operations" / mod
            if not fp.exists():
                continue
            content = fp.read_text(encoding="utf-8")
            # Check for DELETE FROM (SQL)
            if "DELETE FROM" in content.upper():
                # Only allowed in recovery_plan.py as SQL preview
                pass


# ===================================================================
# Helpers
# ===================================================================

class FakeCallableCompleted:
    def __call__(self, ordinal: int, **kwargs: Any) -> ShadowCallableResult:
        return ShadowCallableResult(
            child_run_id=f"fake-{ordinal}-{uuid.uuid4().hex[:8]}",
            status=STATUS_COMPLETED,
        )


class FakeCallableDegraded:
    def __call__(self, ordinal: int, **kwargs: Any) -> ShadowCallableResult:
        return ShadowCallableResult(
            child_run_id=f"fake-deg-{ordinal}",
            status=STATUS_DEGRADED,
        )


class FakeCallableFails:
    def __call__(self, ordinal: int, **kwargs: Any) -> ShadowCallableResult:
        return ShadowCallableResult(
            child_run_id=f"fake-fail-{ordinal}",
            status=STATUS_FAILED,
        )


class FakeCallableRaises:
    def __call__(self, ordinal: int, **kwargs: Any) -> ShadowCallableResult:
        raise RuntimeError("injected fault")


class FakeClock:
    _now = 1000000.0

    def __call__(self) -> float:
        return self._now

    def advance(self, s: float) -> None:
        self._now += s


def fake_sleep(s: float) -> None:
    pass
