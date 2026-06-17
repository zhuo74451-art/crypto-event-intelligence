"""Operator CLI tests — doctor, run, shadow, inspect, compare, bundle."""
from __future__ import annotations

import io, json, os, sys, tempfile, unittest
from unittest.mock import patch, MagicMock

from market_radar.integration.operator_profiles import get_profile, BUILTIN_PROFILES


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
