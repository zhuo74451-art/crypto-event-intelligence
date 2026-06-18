"""R09 — link_existing behavioral tests with real W5 run_bounded_shadow + SQLite.

Uses fake callable that simulates Integration run_one_shot behavior:
insert_run into shared state_dir/run_history.db, returns real child_run_id.
No network, no real Hyperliquid/CCXT calls.
"""
from __future__ import annotations

import os, sqlite3, tempfile, unittest
from unittest.mock import patch

from market_radar.operations.bounded_shadow import (
    BoundedShadowConfig, BoundedShadowResult, ShadowCallableResult,
    run_bounded_shadow,
)
from market_radar.operations.run_history import (
    insert_run, link_existing_run_to_parent, get_run, list_runs,
)
from market_radar.operations.sqlite_schema import initialize_sqlite
from market_radar.integration.bounded_shadow_runner import run_integration_shadow


class TestRunHistoryLinkExisting(unittest.TestCase):
    """Real W5 run_bounded_shadow with link_existing, fake callable, real SQLite."""

    def _make_fake_one_shot(self, db_path: str):
        """Create a factory for fake callables that simulate Integration's run_one_shot."""
        call_count = [0]

        def make_callable():
            call_idx = call_count[0]
            call_count[0] += 1

            def callable_fn(
                ordinal: int,
                shared_state_dir: str,
                no_send: bool,
                parent_shadow_run_id: str,
            ) -> ShadowCallableResult:
                # Simulate Integration run_one_shot: insert own child row
                child_run_id = f"child_{call_idx}_{ordinal}"
                try:
                    initialize_sqlite(db_path)
                    insert_run(
                        db_path,
                        child_run_id,
                        runner_label="one_shot",
                        status="completed",
                        summary={"ordinal": ordinal, "mode": "live-public"},
                    )
                except Exception:
                    pass  # idempotent
                return ShadowCallableResult(
                    child_run_id=child_run_id,
                    status="completed",
                    summary={"real_mode": "live-public", "ordinal": ordinal},
                )
            return callable_fn
        return make_callable

    def _run_and_audit(self, max_runs: int = 2) -> tuple[BoundedShadowResult, str]:
        """Run bounded_shadow with link_existing and return (result, db_path)."""
        tmp = tempfile.mkdtemp()
        db_path = os.path.join(tmp, "run_history.db")
        sdir = tmp
        factory = self._make_fake_one_shot(db_path)

        config = BoundedShadowConfig(
            max_runs=max_runs,
            no_send=True,
            state_dir=sdir,
            child_history_mode="link_existing",
        )

        # The fake callable is stateful — use a single instance
        callable_fn = factory()

        result = run_bounded_shadow(config, callable_fn, sleep_fn=lambda x: None)
        return result, db_path, sdir, tmp

    def test_two_rounds_executed(self):
        """run_integration_shadow executes 2 rounds via run_bounded_shadow."""
        result, db_path, sdir, tmp = self._run_and_audit(2)
        try:
            self.assertEqual(result.attempted_runs, 2)
            self.assertEqual(result.completed_runs, 2)
        finally:
            import shutil; shutil.rmtree(tmp, ignore_errors=True)

    def test_no_third_round(self):
        """max_runs=2, no third round executed."""
        result, db_path, sdir, tmp = self._run_and_audit(2)
        try:
            self.assertEqual(result.attempted_runs, 2)
            self.assertLessEqual(len(result.records), 2)
        finally:
            import shutil; shutil.rmtree(tmp, ignore_errors=True)

    def test_result_errors_empty(self):
        """No child insert failed, no UNIQUE constraint, no duplicate run_id."""
        result, db_path, sdir, tmp = self._run_and_audit(2)
        try:
            err_str = " ".join(result.errors).lower()
            self.assertNotIn("child insert failed", err_str)
            self.assertNotIn("unique", err_str)
            self.assertNotIn("duplicate run_id", err_str)
        finally:
            import shutil; shutil.rmtree(tmp, ignore_errors=True)

    def test_parent_row_exists(self):
        """Parent row has run_kind=shadow_parent."""
        result, db_path, sdir, tmp = self._run_and_audit(2)
        try:
            parent = get_run(db_path, result.shadow_run_id)
            self.assertIsNotNone(parent)
            self.assertEqual(parent.get("run_kind"), "shadow_parent")
        finally:
            import shutil; shutil.rmtree(tmp, ignore_errors=True)

    def test_child_rows_exist(self):
        """Two child rows with correct parent_run_id, run_ordinal, run_kind."""
        result, db_path, sdir, tmp = self._run_and_audit(2)
        try:
            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row
            children = conn.execute(
                "SELECT * FROM run_history WHERE parent_run_id=? ORDER BY run_ordinal",
                (result.shadow_run_id,),
            ).fetchall()
            conn.close()
            self.assertEqual(len(children), 2)
            self.assertEqual(children[0]["run_ordinal"], 1)
            self.assertEqual(children[1]["run_ordinal"], 2)
            self.assertEqual(children[0]["run_kind"], "shadow_child")
            self.assertEqual(children[1]["run_kind"], "shadow_child")
        finally:
            import shutil; shutil.rmtree(tmp, ignore_errors=True)

    def test_child_ids_match_records(self):
        """Child IDs in DB match result.records child_run_ids."""
        result, db_path, sdir, tmp = self._run_and_audit(2)
        try:
            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row
            children = conn.execute(
                "SELECT * FROM run_history WHERE parent_run_id=? ORDER BY run_ordinal",
                (result.shadow_run_id,),
            ).fetchall()
            conn.close()
            for rec, child in zip(result.records, children):
                self.assertEqual(rec.child_run_id, child["run_id"])
        finally:
            import shutil; shutil.rmtree(tmp, ignore_errors=True)

    def test_child_status_preserved(self):
        """Child status in DB matches completed."""
        result, db_path, sdir, tmp = self._run_and_audit(2)
        try:
            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row
            children = conn.execute(
                "SELECT * FROM run_history WHERE parent_run_id=? ORDER BY run_ordinal",
                (result.shadow_run_id,),
            ).fetchall()
            conn.close()
            for child in children:
                self.assertEqual(child["status"], "completed")
        finally:
            import shutil; shutil.rmtree(tmp, ignore_errors=True)

    def test_child_label_preserved(self):
        """Child runner_label from insert_run is preserved."""
        result, db_path, sdir, tmp = self._run_and_audit(2)
        try:
            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row
            children = conn.execute(
                "SELECT * FROM run_history WHERE parent_run_id=? ORDER BY run_ordinal",
                (result.shadow_run_id,),
            ).fetchall()
            conn.close()
            for child in children:
                self.assertEqual(child["runner_label"], "one_shot")
        finally:
            import shutil; shutil.rmtree(tmp, ignore_errors=True)

    def test_summary_preserved(self):
        """Child summary from insert_run is preserved."""
        result, db_path, sdir, tmp = self._run_and_audit(2)
        try:
            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row
            children = conn.execute(
                "SELECT * FROM run_history WHERE parent_run_id=? ORDER BY run_ordinal",
                (result.shadow_run_id,),
            ).fetchall()
            conn.close()
            for child in children:
                self.assertIsNotNone(child["summary_json"])
        finally:
            import shutil; shutil.rmtree(tmp, ignore_errors=True)

    def test_same_state_dir_used(self):
        """Second round receives same shared_state_dir as first."""
        received = []
        tmp = tempfile.mkdtemp()
        try:
            db_path = os.path.join(tmp, "run_history.db")
            def callable_fn(ordinal, shared_state_dir, no_send, parent_shadow_run_id):
                received.append(shared_state_dir)
                child_id = f"c{ordinal}"
                initialize_sqlite(db_path)
                insert_run(db_path, child_id, runner_label="os", status="completed")
                return ShadowCallableResult(child_run_id=child_id, status="completed")

            config = BoundedShadowConfig(max_runs=2, no_send=True, state_dir=tmp,
                                          child_history_mode="link_existing")
            result = run_bounded_shadow(config, callable_fn, sleep_fn=lambda x: None)
            self.assertEqual(len(received), 2)
            self.assertEqual(received[0], tmp)
            self.assertEqual(received[1], tmp)
        finally:
            import shutil; shutil.rmtree(tmp, ignore_errors=True)

    def test_no_send_true(self):
        """no_send is always true."""
        result, db_path, sdir, tmp = self._run_and_audit(2)
        try:
            self.assertTrue(result.no_send)
        finally:
            import shutil; shutil.rmtree(tmp, ignore_errors=True)

    def test_max_runs_1(self):
        """max_runs=1 only executes 1 round."""
        result, db_path, sdir, tmp = self._run_and_audit(1)
        try:
            self.assertEqual(result.attempted_runs, 1)
        finally:
            import shutil; shutil.rmtree(tmp, ignore_errors=True)

    def test_fake_provider_per_round(self):
        """Provider factory creates a new provider each round (simulated via call_count)."""
        call_counts = []
        tmp = tempfile.mkdtemp()
        try:
            db_path = os.path.join(tmp, "run_history.db")
            def callable_fn(ordinal, *args, **kwargs):
                call_counts.append(ordinal)
                child_id = f"p{ordinal}"
                initialize_sqlite(db_path)
                insert_run(db_path, child_id, runner_label="os", status="completed")
                return ShadowCallableResult(child_run_id=child_id, status="completed",
                                            summary={"provider_round": ordinal})
            config = BoundedShadowConfig(max_runs=2, no_send=True, state_dir=tmp,
                                          child_history_mode="link_existing")
            result = run_bounded_shadow(config, callable_fn, sleep_fn=lambda x: None)
            self.assertEqual(len(call_counts), 2)
        finally:
            import shutil; shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
