"""Operator CLI tests — doctor, run, shadow, inspect, compare, bundle."""
from __future__ import annotations

import io, json, os, sys, tempfile, unittest
from unittest.mock import patch, MagicMock

from market_radar.integration.operator_profiles import get_profile, BUILTIN_PROFILES
from pathlib import Path


class TestDoctor(unittest.TestCase):
    def test_doctor_offline(self):
        with patch.object(sys, "argv", ["op", "doctor", "--offline", "--json"]):
            from scripts.post_mvp.operator.operator_workbench import main
            result = main()
        self.assertEqual(result, 0)

    def test_doctor_returns_json(self):
        with patch.object(sys, "argv", ["op", "doctor", "--offline", "--json"]):
            from scripts.post_mvp.operator.operator_workbench import main
            result = main()
            self.assertEqual(result, 0)


class TestRun(unittest.TestCase):
    def test_unknown_profile_rejected(self):
        with patch.object(sys, "argv", ["op", "run", "nonexistent"]):
            with self.assertRaises(SystemExit):
                from scripts.post_mvp.operator.operator_workbench import main
                main()

    def test_profile_choices_correct(self):
        for name in ["fixture-smoke", "live-one-shot", "live-shadow-2"]:
            p = get_profile(name)
            self.assertEqual(p.name, name)


class TestShadow(unittest.TestCase):
    def test_shadow_rejects_no_confirm(self):
        with patch.object(sys, "argv", ["op", "shadow", "live-shadow-2"]):
            from scripts.post_mvp.operator.operator_workbench import main
            result = main()
            self.assertEqual(result, 1)

    def test_shadow_max_runs_2(self):
        p = get_profile("live-shadow-2")
        self.assertEqual(p.max_runs, 2)


class TestInspect(unittest.TestCase):
    def test_inspect_missing_dir(self):
        with patch.object(sys, "argv", ["op", "inspect", "/nonexistent/path"]):
            from scripts.post_mvp.operator.operator_workbench import main
            result = main()
            self.assertEqual(result, 1)

    def test_inspect_empty_dir(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(sys, "argv", ["op", "inspect", tmp]):
                from scripts.post_mvp.operator.operator_workbench import main
                result = main()
                self.assertEqual(result, 1)

    def test_inspect_with_manifest(self):
        with tempfile.TemporaryDirectory() as tmp:
            manifest = {"run_id": "test", "status": "completed", "profile_name": "test",
                         "profile_hash": "abc", "errors": [], "source_summary": {},
                         "output_files": [], "diagnoses": []}
            with open(os.path.join(tmp, "manifest_test.json"), "w") as f:
                json.dump(manifest, f)
            with patch.object(sys, "argv", ["op", "inspect", tmp]):
                from scripts.post_mvp.operator.operator_workbench import main
                result = main()
                self.assertEqual(result, 0)


class TestCompare(unittest.TestCase):
    def test_compare_two_runs(self):
        with tempfile.TemporaryDirectory() as tmp1, tempfile.TemporaryDirectory() as tmp2:
            for d, data in [(tmp1, {"status": "completed", "sources": [{"source": "feed", "status": "ok"}]}),
                            (tmp2, {"status": "degraded", "sources": [{"source": "feed", "status": "degraded"}]})]:
                with open(os.path.join(d, "run_test.json"), "w") as f:
                    json.dump(data, f)
            with patch.object(sys, "argv", ["op", "compare", tmp1, tmp2]):
                from scripts.post_mvp.operator.operator_workbench import main
                result = main()
                self.assertEqual(result, 0)


class TestBundle(unittest.TestCase):
    def test_bundle_missing_dir(self):
        with patch.object(sys, "argv", ["op", "bundle", "/nonexistent"]):
            from scripts.post_mvp.operator.operator_workbench import main
            result = main()
            self.assertEqual(result, 1)

    def test_bundle_with_report(self):
        with tempfile.TemporaryDirectory() as tmp:
            report = {"run_id": "r1", "status": "completed", "sources": [],
                       "markets": [], "errors": [], "no_send": True}
            with open(os.path.join(tmp, "run_test.json"), "w") as f:
                json.dump(report, f)
            with patch.object(sys, "argv", ["op", "bundle", tmp, "--output", os.path.join(tmp, "bundle")]):
                from scripts.post_mvp.operator.operator_workbench import main
                result = main()
                self.assertEqual(result, 0)
                bundle_dir = os.path.join(tmp, "bundle")
                self.assertTrue(os.path.exists(os.path.join(bundle_dir, "manifest.json")))
                self.assertTrue(os.path.exists(os.path.join(bundle_dir, "SHA256SUMS")))

    def test_bundle_no_full_content(self):
        with tempfile.TemporaryDirectory() as tmp:
            report = {"run_id": "r1", "status": "completed",
                       "sources": [], "markets": [],
                       "errors": [], "no_send": True,
                       "feed_summary": {"items": [{"title": "secret"}]}}
            with open(os.path.join(tmp, "run_test.json"), "w") as f:
                json.dump(report, f)
            with patch.object(sys, "argv", ["op", "bundle", tmp, "--output", os.path.join(tmp, "bundle")]):
                from scripts.post_mvp.operator.operator_workbench import main
                main()
                bundle_path = os.path.join(tmp, "bundle", "manifest.json")
                with open(bundle_path, "r") as f:
                    bundle = json.load(f)
                self.assertIn("report", bundle)
                self.assertIn("report", bundle)

    def test_profile_list_in_builtins(self):
        for name in ["fixture-smoke", "live-one-shot", "live-shadow-2",
                       "feed-diagnostic", "market-diagnostic",
                       "whale-diagnostic", "full-internal-review"]:
            self.assertIn(name, BUILTIN_PROFILES)


if __name__ == "__main__":
    unittest.main()


class TestStatusEmpty(unittest.TestCase):

    def test_status_empty_json(self):
        with patch.object(sys, "argv", ["op", "status", "--json"]):
            from scripts.post_mvp.operator.operator_workbench import main
            result = main()
            self.assertEqual(result, 0)

    def test_status_empty_text(self):
        with patch.object(sys, "argv", ["op", "status"]):
            from scripts.post_mvp.operator.operator_workbench import main
            result = main()
            self.assertEqual(result, 0)

    def test_status_with_custom_state_dir(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(sys, "argv", ["op", "status", "--state-dir", tmp, "--output-dir", tmp, "--json"]):
                from scripts.post_mvp.operator.operator_workbench import main
                result = main()
                self.assertEqual(result, 0)


class TestStatusNormalRun(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.state_dir = Path(self.tmp.name) / "state"
        self.output_dir = Path(self.tmp.name) / "output"
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self._setup_run_history()

    def _setup_run_history(self):
        db_path = self.state_dir / "run_history.db"
        from market_radar.operations.sqlite_schema import initialize_sqlite
        initialize_sqlite(str(db_path))
        import sqlite3
        conn = sqlite3.connect(str(db_path))
        conn.execute(
            "INSERT INTO run_history (run_id, runner_label, status, started_at, finished_at) "
            "VALUES (?, ?, ?, ?, ?)",
            ("run_001", "one-shot", "completed", "2026-06-18T10:00:00Z", "2026-06-18T10:01:30Z"),
        )
        conn.commit()
        conn.close()
        manifest = {
            "run_id": "run_001",
            "profile_name": "fixture-smoke",
            "status": "completed",
            "source_summary": {"feed": "ok", "whale": "ok", "markets": "ok"},
            "feed_summary": {"live_count": 42, "overall_status": "healthy"},
            "whale": {"positions": 3},
            "markets": [{"market": "BTC/USD", "status": "ok", "price": 50000}],
            "cursor_before": "abc", "cursor_after": "def",
            "error_count": 0,
        }
        with open(self.output_dir / "manifest_run_001.json", "w") as f:
            json.dump(manifest, f)

    def tearDown(self):
        self.tmp.cleanup()

    def test_status_healthy_json(self):
        with patch.object(sys, "argv", ["op", "status", "--json",
                                        "--state-dir", str(self.state_dir),
                                        "--output-dir", str(self.output_dir)]):
            from scripts.post_mvp.operator.operator_workbench import main
            result = main()
            self.assertEqual(result, 0)

    def test_status_latest_run_present(self):
        with patch.object(sys, "argv", ["op", "status", "--json",
                                        "--state-dir", str(self.state_dir),
                                        "--output-dir", str(self.output_dir)]):
            from scripts.post_mvp.operator.operator_workbench import main
            with patch("sys.stdout", new_callable=io.StringIO) as mock_out:
                result = main()
                output = json.loads(mock_out.getvalue())
                self.assertIsNotNone(output.get("latest_run"))
                self.assertEqual(output["latest_run"]["run_id"], "run_001")
                self.assertEqual(output["latest_run"]["status"], "completed")
                self.assertIn("time_ago", output["latest_run"])
                self.assertEqual(result, 0)

    def test_status_sources_from_manifest(self):
        with patch.object(sys, "argv", ["op", "status", "--json",
                                        "--state-dir", str(self.state_dir),
                                        "--output-dir", str(self.output_dir)]):
            from scripts.post_mvp.operator.operator_workbench import main
            with patch("sys.stdout", new_callable=io.StringIO) as mock_out:
                main()
                output = json.loads(mock_out.getvalue())
                self.assertEqual(output["sources"].get("feed"), "ok")
                self.assertEqual(output["feed"].get("live_count"), 42)
                self.assertEqual(output["whale"].get("positions"), 3)

    def test_status_cursor(self):
        with patch.object(sys, "argv", ["op", "status", "--json",
                                        "--state-dir", str(self.state_dir),
                                        "--output-dir", str(self.output_dir)]):
            from scripts.post_mvp.operator.operator_workbench import main
            with patch("sys.stdout", new_callable=io.StringIO) as mock_out:
                main()
                output = json.loads(mock_out.getvalue())
                self.assertEqual(output["cursor"]["before"], "abc")
                self.assertEqual(output["cursor"]["after"], "def")

    def test_status_paths_and_disk(self):
        with patch.object(sys, "argv", ["op", "status", "--json",
                                        "--state-dir", str(self.state_dir),
                                        "--output-dir", str(self.output_dir)]):
            from scripts.post_mvp.operator.operator_workbench import main
            with patch("sys.stdout", new_callable=io.StringIO) as mock_out:
                main()
                output = json.loads(mock_out.getvalue())
                self.assertIn("paths", output)
                self.assertIn("disk", output)
                self.assertIsInstance(output["disk"].get("free_gb"), (int, float))


class TestStatusDegraded(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.state_dir = Path(self.tmp.name) / "state"
        self.output_dir = Path(self.tmp.name) / "output"
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def _make_run(self, status, source_health=None):
        from market_radar.operations.sqlite_schema import initialize_sqlite
        db_path = self.state_dir / "run_history.db"
        initialize_sqlite(str(db_path))
        import sqlite3
        conn = sqlite3.connect(str(db_path))
        conn.execute(
            "INSERT INTO run_history (run_id, runner_label, status, started_at, finished_at) "
            "VALUES (?, ?, ?, ?, ?)",
            ("run_d1", "one-shot", status, "2026-06-18T10:00:00Z", "2026-06-18T10:02:00Z"),
        )
        conn.commit()
        conn.close()
        manifest = {
            "run_id": "run_d1",
            "profile_name": "live-one-shot",
            "status": status,
            "source_summary": source_health or {"feed": "degraded", "whale": "ok", "markets": "failed"},
            "error_count": 2,
        }
        with open(self.output_dir / "manifest_run_d1.json", "w") as f:
            json.dump(manifest, f)

    def tearDown(self):
        self.tmp.cleanup()

    def test_status_degraded_returns_warning(self):
        self._make_run("degraded", {"feed": "degraded", "whale": "ok", "markets": "ok"})
        with patch.object(sys, "argv", ["op", "status", "--json",
                                        "--state-dir", str(self.state_dir),
                                        "--output-dir", str(self.output_dir)]):
            from scripts.post_mvp.operator.operator_workbench import main
            result = main()
            self.assertEqual(result, 1)

    def test_status_failed_returns_unhealthy(self):
        self._make_run("failed", {"feed": "failed", "whale": "failed", "markets": "failed"})
        with patch.object(sys, "argv", ["op", "status", "--json",
                                        "--state-dir", str(self.state_dir),
                                        "--output-dir", str(self.output_dir)]):
            from scripts.post_mvp.operator.operator_workbench import main
            result = main()
            self.assertEqual(result, 2)


class TestStatusStaleRun(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.state_dir = Path(self.tmp.name) / "state"
        self.state_dir.mkdir(parents=True, exist_ok=True)

    def _make_unfinished_run(self):
        from market_radar.operations.sqlite_schema import initialize_sqlite
        db_path = self.state_dir / "run_history.db"
        initialize_sqlite(str(db_path))
        import sqlite3
        conn = sqlite3.connect(str(db_path))
        conn.execute(
            "INSERT INTO run_history (run_id, runner_label, status, started_at, finished_at) "
            "VALUES (?, ?, ?, ?, ?)",
            ("run_stale", "one-shot", "in_progress",
             "2026-06-18T08:00:00Z", None),
        )
        conn.commit()
        conn.close()

    def tearDown(self):
        self.tmp.cleanup()

    def test_stale_run_unhealthy(self):
        self._make_unfinished_run()
        with patch.object(sys, "argv", ["op", "status", "--json",
                                        "--state-dir", str(self.state_dir)]):
            from scripts.post_mvp.operator.operator_workbench import main
            result = main()
            self.assertEqual(result, 2)


class TestStatusOrphanLock(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.state_dir = Path(self.tmp.name) / "state"
        self.state_dir.mkdir(parents=True, exist_ok=True)

    def _create_stale_lock(self):
        lock_path = self.state_dir / "one_shot.lock"
        import time
        old_ts = time.time() - 600
        lock_path.write_text("99999|%s|ops-foundation-v1" % (old_ts,))

    def tearDown(self):
        self.tmp.cleanup()

    def test_orphan_lock_warning(self):
        self._create_stale_lock()
        with patch.object(sys, "argv", ["op", "status", "--json",
                                        "--state-dir", str(self.state_dir)]):
            from scripts.post_mvp.operator.operator_workbench import main
            result = main()
            self.assertEqual(result, 1)

    def test_lock_listed(self):
        self._create_stale_lock()
        with patch.object(sys, "argv", ["op", "status", "--json",
                                        "--state-dir", str(self.state_dir)]):
            from scripts.post_mvp.operator.operator_workbench import main
            with patch("sys.stdout", new_callable=io.StringIO) as mock_out:
                main()
                output = json.loads(mock_out.getvalue())
                self.assertTrue(len(output.get("locks", [])) > 0)


class TestStatusStopMarker(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.state_dir = Path(self.tmp.name) / "state"
        self.state_dir.mkdir(parents=True, exist_ok=True)
        stop_path = self.state_dir / "STOP"
        stop_path.write_text("stop")

    def tearDown(self):
        self.tmp.cleanup()

    def test_stop_marker_warning(self):
        with patch.object(sys, "argv", ["op", "status", "--json",
                                        "--state-dir", str(self.state_dir)]):
            from scripts.post_mvp.operator.operator_workbench import main
            result = main()
            self.assertEqual(result, 1)

    def test_stop_marker_listed(self):
        with patch.object(sys, "argv", ["op", "status", "--json",
                                        "--state-dir", str(self.state_dir)]):
            from scripts.post_mvp.operator.operator_workbench import main
            with patch("sys.stdout", new_callable=io.StringIO) as mock_out:
                main()
                output = json.loads(mock_out.getvalue())
                self.assertTrue(len(output.get("stop_marker", [])) > 0)


class TestStatusAlertState(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.state_dir = Path(self.tmp.name) / "state"
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self._setup_alert_state()

    def _setup_alert_state(self):
        import sqlite3
        db_path = self.state_dir / "alert_state.db"
        conn = sqlite3.connect(str(db_path))
        conn.execute("""
            CREATE TABLE IF NOT EXISTS alert_state (
                alert_key TEXT PRIMARY KEY,
                state TEXT NOT NULL DEFAULT 'new',
                first_seen_at TEXT NOT NULL,
                last_seen_at TEXT NOT NULL,
                last_changed_at TEXT,
                last_delivery_at TEXT,
                severity TEXT NOT NULL DEFAULT 'low',
                previous_severity TEXT,
                snapshot_json TEXT NOT NULL DEFAULT '{}',
                previous_snapshot_json TEXT NOT NULL DEFAULT '{}',
                resolved_at TEXT,
                delivery_count INTEGER NOT NULL DEFAULT 0
            )
        """)
        conn.execute(
            "INSERT INTO alert_state (alert_key, state, first_seen_at, last_seen_at) "
            "VALUES (?, ?, ?, ?)", ("key1", "new", "2026-06-18T10:00:00Z", "2026-06-18T10:00:00Z")
        )
        conn.execute(
            "INSERT INTO alert_state (alert_key, state, first_seen_at, last_seen_at) "
            "VALUES (?, ?, ?, ?)", ("key2", "persistent", "2026-06-17T10:00:00Z", "2026-06-18T10:00:00Z")
        )
        conn.execute(
            "INSERT INTO alert_state (alert_key, state, first_seen_at, last_seen_at) "
            "VALUES (?, ?, ?, ?)", ("key3", "changed", "2026-06-16T10:00:00Z", "2026-06-18T10:00:00Z")
        )
        conn.commit()
        conn.close()

    def tearDown(self):
        self.tmp.cleanup()

    def test_alert_state_counts(self):
        with patch.object(sys, "argv", ["op", "status", "--json",
                                        "--state-dir", str(self.state_dir)]):
            from scripts.post_mvp.operator.operator_workbench import main
            with patch("sys.stdout", new_callable=io.StringIO) as mock_out:
                main()
                output = json.loads(mock_out.getvalue())
                alert_state = output.get("alert_state", {})
                self.assertTrue(alert_state.get("db_found"))
                self.assertEqual(alert_state.get("new"), 1)
                self.assertEqual(alert_state.get("persistent"), 1)
                self.assertEqual(alert_state.get("changed"), 1)
                self.assertEqual(alert_state.get("resolved"), 0)
                self.assertEqual(alert_state.get("delivery_candidates"), 2)


class TestStatusJSONOutput(unittest.TestCase):

    def test_json_structure_empty(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(sys, "argv", ["op", "status", "--json",
                                            "--state-dir", tmp, "--output-dir", tmp]):
                from scripts.post_mvp.operator.operator_workbench import main
                with patch("sys.stdout", new_callable=io.StringIO) as mock_out:
                    result = main()
                    output = json.loads(mock_out.getvalue())
                    self.assertIn("release_sha", output)
                    self.assertIn("branch", output)
                    self.assertIn("timestamp", output)
                    self.assertIn("latest_run", output)
                    self.assertIn("run_history", output)
                    self.assertIn("sources", output)
                    self.assertIn("locks", output)
                    self.assertIn("stop_marker", output)
                    self.assertIn("paths", output)
                    self.assertIn("disk", output)
                    self.assertIn("alert_state", output)
                    self.assertIn("telegram_receipt", output)
                    self.assertIn("exit_code", output)
                    self.assertIn("health", output)
                    self.assertEqual(result, 0)

    def test_json_exit_codes(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(sys, "argv", ["op", "status", "--json",
                                            "--state-dir", tmp, "--output-dir", tmp]):
                from scripts.post_mvp.operator.operator_workbench import main
                with patch("sys.stdout", new_callable=io.StringIO) as mock_out:
                    main()
                    output = json.loads(mock_out.getvalue())
                    health_map = {0: "healthy", 1: "warning", 2: "unhealthy"}
                    self.assertEqual(health_map[output["exit_code"]], output["health"])


class TestStatusExitCodes(unittest.TestCase):

    def test_exit_healthy(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(sys, "argv", ["op", "status", "--json",
                                            "--state-dir", tmp, "--output-dir", tmp]):
                from scripts.post_mvp.operator.operator_workbench import main
                result = main()
                self.assertEqual(result, 0)

    def test_exit_code_matches_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(sys, "argv", ["op", "status", "--json",
                                            "--state-dir", tmp, "--output-dir", tmp]):
                from scripts.post_mvp.operator.operator_workbench import main
                with patch("sys.stdout", new_callable=io.StringIO) as mock_out:
                    exit_code = main()
                    output = json.loads(mock_out.getvalue())
                    self.assertEqual(exit_code, output["exit_code"])


if __name__ == "__main__":
    unittest.main()
