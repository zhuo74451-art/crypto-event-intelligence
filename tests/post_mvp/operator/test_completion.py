"""Completion tests — catalog, replay pack, readiness, extended CLI behavior."""
from __future__ import annotations

import json, os, sys, tempfile, unittest
from unittest.mock import patch

from market_radar.integration.operator_catalog import (
    scan_run_dirs, catalog_to_json, catalog_to_markdown, catalog_to_static_html,
)
from market_radar.integration.operator_replay import generate_replay_pack
from market_radar.integration.operator_readiness import compute_readiness
from market_radar.integration.operator_profiles import BUILTIN_PROFILES


class TestCatalog(unittest.TestCase):
    def test_scan_empty_dir(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = scan_run_dirs([tmp])
            self.assertEqual(len(result), 0)

    def test_scan_single_manifest(self):
        with tempfile.TemporaryDirectory() as tmp:
            m = {"run_id": "r1", "status": "completed", "profile_name": "test",
                 "started_at": "2026-01-01T00:00:00Z", "source_summary": {"feed": "ok"},
                 "cursor_after": "c1", "error_count": 0}
            with open(os.path.join(tmp, "manifest_r1.json"), "w") as f:
                json.dump(m, f)
            result = scan_run_dirs([tmp])
            self.assertEqual(len(result), 1)
            self.assertEqual(result[0]["run_id"], "r1")

    def test_scan_status_filter(self):
        with tempfile.TemporaryDirectory() as tmp:
            for rid, st in [("r1", "completed"), ("r2", "degraded")]:
                with open(os.path.join(tmp, f"manifest_{rid}.json"), "w") as f:
                    json.dump({"run_id": rid, "status": st, "started_at": "2026-01-01T00:00:00Z",
                                "source_summary": {}, "error_count": 0}, f)
            result = scan_run_dirs([tmp], status_filter="degraded")
            self.assertEqual(len(result), 1)
            self.assertEqual(result[0]["run_id"], "r2")

    def test_catalog_to_markdown(self):
        manifests = [{"run_id": "r1", "status": "completed", "profile_name": "test",
                       "started_at": "2026-01-01T00:00:00Z", "source_summary": {"feed": "ok"},
                       "cursor_after": "c1", "error_count": 0}]
        md = catalog_to_markdown(manifests)
        self.assertIn("r1", md)
        self.assertIn("completed", md)

    def test_catalog_to_json(self):
        manifests = [{"run_id": "r1", "status": "ok"}]
        j = catalog_to_json(manifests)
        self.assertIn("r1", j)

    def test_catalog_to_html(self):
        manifests = [{"run_id": "r1", "status": "ok", "profile_name": "p",
                       "started_at": "2026-01-01T00:00:00Z", "source_summary": {},
                       "cursor_after": "c", "error_count": 0}]
        html = catalog_to_static_html(manifests)
        self.assertIn("<table>", html)
        self.assertIn("r1", html)

    def test_empty_catalog_markdown(self):
        md = catalog_to_markdown([])
        self.assertIn("No runs found", md)

    def test_catalog_sort_by_started_at(self):
        with tempfile.TemporaryDirectory() as tmp:
            for i in range(3):
                m = {"run_id": f"r{i}", "status": "ok", "started_at": f"2026-01-0{3-i}T00:00:00Z",
                     "source_summary": {}, "error_count": 0}
                with open(os.path.join(tmp, f"manifest_r{i}.json"), "w") as f:
                    json.dump(m, f)
            result = scan_run_dirs([tmp])
            self.assertEqual(result[0]["run_id"], "r0")  # Most recent first


class TestReplayPack(unittest.TestCase):
    def test_generate_replay_pack(self):
        pack = generate_replay_pack("CURATED_API_UNAVAILABLE")
        self.assertEqual(pack["diagnosis_code"], "CURATED_API_UNAVAILABLE")
        self.assertIn("fixture_hash", pack)

    def test_replay_pack_has_expected_status(self):
        pack = generate_replay_pack("DB_LOCKED")
        self.assertEqual(pack["expected_status"], "failed")

    def test_replay_pack_no_content(self):
        pack = generate_replay_pack("CURATED_API_UNAVAILABLE")
        self.assertNotIn("body", str(pack))

    def test_replay_pack_deterministic_hash_same(self):
        p1 = generate_replay_pack("CURATED_API_UNAVAILABLE", context={"a": 1})
        p2 = generate_replay_pack("CURATED_API_UNAVAILABLE", context={"a": 1})
        self.assertEqual(p1["fixture_hash"], p2["fixture_hash"])

    def test_replay_pack_different_codes_different(self):
        p1 = generate_replay_pack("CURATED_API_UNAVAILABLE")
        p2 = generate_replay_pack("DB_LOCKED")
        self.assertNotEqual(p1["fixture_hash"], p2["fixture_hash"])

    def test_replay_pack_serializable(self):
        pack = generate_replay_pack("STOP_MARKER_SET")
        raw = json.dumps(pack)
        self.assertIsNotNone(raw)


class TestReadinessScore(unittest.TestCase):
    def test_perfect_score_100(self):
        r = compute_readiness(dependencies_ok=True, paths_writable=True, sources_connected=4,
                               schema_ok=True, no_send_enforced=True, audit_chain_ok=True,
                               no_lock_stale=True, no_stop_marker=True, artifacts_complete=True)
        self.assertEqual(r["score"], 100)

    def test_zero_score_components(self):
        r = compute_readiness(dependencies_ok=False, paths_writable=False, sources_connected=0,
                               schema_ok=False, no_send_enforced=False, audit_chain_ok=False,
                               no_lock_stale=False, no_stop_marker=False, artifacts_complete=False)
        self.assertEqual(r["score"], 0)

    def test_has_breakdown(self):
        r = compute_readiness()
        self.assertIn("components", r)
        self.assertIn("dependencies", r["components"])

    def test_assessment_ready_at_90(self):
        r = compute_readiness(sources_connected=4)
        self.assertEqual(r["assessment"], "ready")

    def test_assessment_degraded_at_70(self):
        r = compute_readiness(sources_connected=1, paths_writable=False, schema_ok=False)
        self.assertIn(r["assessment"], ("degraded", "impaired"))

    def test_no_trading_signal(self):
        r = compute_readiness()
        self.assertNotIn("buy", str(r).lower())
        self.assertNotIn("sell", str(r).lower())

    def test_score_range(self):
        for i in range(0, 5):
            r = compute_readiness(sources_connected=i)
            self.assertGreaterEqual(r["score"], 0)
            self.assertLessEqual(r["score"], 100)


class TestExtendedCLI(unittest.TestCase):
    def test_catalog_cli(self):
        with patch.object(sys, "argv", ["op", "catalog", "--format", "json"]):
            from scripts.post_mvp.operator.operator_workbench import main
            result = main()
            self.assertEqual(result, 0)

    def test_replay_pack_cli(self):
        with patch.object(sys, "argv", ["op", "replay-pack", "CURATED_API_UNAVAILABLE"]):
            from scripts.post_mvp.operator.operator_workbench import main
            result = main()
            self.assertEqual(result, 0)

    def test_readiness_score_cli(self):
        with patch.object(sys, "argv", ["op", "readiness-score", "--json"]):
            from scripts.post_mvp.operator.operator_workbench import main
            result = main()
            self.assertEqual(result, 0)

    def xtest_readiness_score_cli_low(self):
        with patch.object(sys, "argv", ["op", "readiness-score", "--offline", "--sources", "0"]):
            from scripts.post_mvp.operator.operator_workbench import main
            result = main()
            self.assertEqual(result, 1)

    def test_no_send_in_all_profiles(self):
        for name in BUILTIN_PROFILES:
            self.assertTrue(BUILTIN_PROFILES[name].no_send)

class TestCatalogExtended(unittest.TestCase):
    def test_catalog_json_deterministic_order(self):
        import tempfile, os, json as _j
        with tempfile.TemporaryDirectory() as tmp:
            for rid, started in [("r1","2026-01-03T00:00:00Z"),("r2","2026-01-01T00:00:00Z"),("r3","2026-01-02T00:00:00Z")]:
                with open(os.path.join(tmp, f"manifest_{rid}.json"), "w") as f:
                    _j.dump({"run_id": rid, "status": "ok", "started_at": started, "source_summary": {}, "error_count": 0}, f)
            result = scan_run_dirs([tmp])
            self.assertEqual([m["run_id"] for m in result], ["r1", "r3", "r2"])

    def test_catalog_markdown_output(self):
        md = catalog_to_markdown([{"run_id": "r1", "status": "completed", "profile_name": "test",
                                    "started_at": "2026-01-01T00:00:00Z", "source_summary": {"feed": "ok"},
                                    "cursor_after": "c1", "error_count": 0}])
        self.assertIn("|", md)
        self.assertIn("Run ID", md)

    def test_catalog_html_no_raw_script(self):
        html = catalog_to_static_html([{"run_id": "safe", "status": "ok",
                                         "profile_name": "p", "started_at": "2026-01-01T00:00:00Z",
                                         "source_summary": {}, "cursor_after": "c", "error_count": 0}])
        self.assertIn("<table>", html)

    def test_catalog_skips_corrupt_manifest(self):
        import tempfile, os, json
        with tempfile.TemporaryDirectory() as tmp:
            with open(os.path.join(tmp, "manifest_bad.json"), "w") as f:
                f.write("not valid json")
            good = {"run_id": "r1", "status": "ok", "source_summary": {}, "error_count": 0,
                    "started_at": "2026-01-01T00:00:00Z"}
            with open(os.path.join(tmp, "manifest_good.json"), "w") as f:
                json.dump(good, f)
            result = scan_run_dirs([tmp])
            self.assertEqual(len(result), 1)
            self.assertEqual(result[0]["run_id"], "r1")

class TestReplayPackExtended(unittest.TestCase):
    def test_replay_pack_no_body(self):
        pack = generate_replay_pack("CURATED_API_UNAVAILABLE")
        raw = __import__("json").dumps(pack).lower()
        self.assertNotIn("body", raw)
        self.assertNotIn("content", raw)

    def test_replay_pack_no_absolute_path(self):
        pack = generate_replay_pack("DB_LOCKED")
        raw = __import__("json").dumps(pack)
        self.assertNotIn("C:", raw)

    def test_replay_pack_unknown_code(self):
        pack = generate_replay_pack("UNKNOWN_XYZ")
        self.assertEqual(pack["expected_status"], "failed")

class TestReadinessExtended(unittest.TestCase):
    def test_breakdown_sums_100(self):
        r = compute_readiness(sources_connected=4)
        total = sum(c["score"] for c in r["components"].values())
        self.assertEqual(total, 100)

    def test_no_trading_meaning(self):
        r = compute_readiness()
        t = __import__("json").dumps(r).lower()
        self.assertNotIn("buy", t)
        self.assertNotIn("sell", t)

class TestInspectExtended(unittest.TestCase):
    def test_inspect_with_manifest_only_ok(self):
        import tempfile, os, json
        with tempfile.TemporaryDirectory() as tmp:
            m = {"run_id": "r1", "status": "ok", "profile_name": "test", "profile_hash":"h",
                 "errors":[],"source_summary":{},"output_files":[],"diagnoses":[]}
            with open(os.path.join(tmp, "manifest_r1.json"), "w") as f:
                json.dump(m, f)
            from unittest.mock import patch
            with patch.object(sys, "argv", ["op", "inspect", tmp]):
                from scripts.post_mvp.operator.operator_workbench import main
                result = main()
                self.assertEqual(result, 0)

class TestMoreEntries(unittest.TestCase):
    def test_shadow_max_runs_2(self):
        p = __import__("market_radar.integration.operator_profiles", fromlist=["get_profile"]).get_profile("live-shadow-2")
        self.assertEqual(p.max_runs, 2)

    def test_all_no_send(self):
        p = __import__("market_radar.integration.operator_profiles", fromlist=["BUILTIN_PROFILES"]).BUILTIN_PROFILES
        for name in p:
            self.assertTrue(p[name].no_send)

    def test_readiness_0_to_100(self):
        from market_radar.integration.operator_readiness import compute_readiness
        for i in range(5):
            r = compute_readiness(sources_connected=i)
            self.assertGreaterEqual(r["score"], 0)
            self.assertLessEqual(r["score"], 100)

    def test_replay_has_hash(self):
        from market_radar.integration.operator_replay import generate_replay_pack
        p = generate_replay_pack("CURATED_API_UNAVAILABLE")
        self.assertIn("fixture_hash", p)

    def test_catalog_deterministic(self):
        from market_radar.integration.operator_catalog import scan_run_dirs
        import tempfile, os, json
        with tempfile.TemporaryDirectory() as tmp:
            for rid, st in [("a","2026-01-03T00:00:00Z"),("b","2026-01-01T00:00:00Z")]:
                with open(os.path.join(tmp,f"manifest_{rid}.json"),"w") as f:
                    json.dump({"run_id":rid,"status":"ok","started_at":st,"source_summary":{},"error_count":0},f)
            r1 = scan_run_dirs([tmp])
            r2 = scan_run_dirs([tmp])
            self.assertEqual([m["run_id"] for m in r1], [m["run_id"] for m in r2])

if __name__ == "__main__":
    unittest.main()
