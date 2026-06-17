"""Operator Manifest tests — build, hash, sanitise."""
from __future__ import annotations

import json, unittest
from market_radar.integration.operator_manifest import (
    build_manifest, sanitise_path, OperatorManifest,
)


class TestManifest(unittest.TestCase):
    def test_build_manifest_has_required_fields(self):
        m = build_manifest(
            run_id="test-1",
            profile_name="live-one-shot",
            profile_hash="abc123",
            data_mode="live-public",
            no_send=True,
            network_allowed=True,
            status="completed",
            source_summary={"feed": "ok"},
            output_files=[{"name": "run_test.json"}],
        )
        self.assertEqual(m.run_id, "test-1")
        self.assertEqual(m.status, "completed")
        self.assertTrue(m.no_send)

    def test_config_hash_deterministic(self):
        m1 = build_manifest(run_id="a", profile_name="p", profile_hash="h",
                             data_mode="fixture", no_send=True, network_allowed=False,
                             status="ok", source_summary={}, output_files=[])
        m2 = build_manifest(run_id="b", profile_name="p", profile_hash="h",
                             data_mode="fixture", no_send=True, network_allowed=False,
                             status="ok", source_summary={}, output_files=[])
        self.assertEqual(m1.compute_config_hash(), m2.compute_config_hash())

    def test_config_hash_differs_with_different_profile(self):
        m1 = build_manifest(run_id="a", profile_name="p1", profile_hash="h1",
                             data_mode="fixture", no_send=True, network_allowed=False,
                             status="ok", source_summary={}, output_files=[])
        m2 = build_manifest(run_id="b", profile_name="p2", profile_hash="h2",
                             data_mode="fixture", no_send=True, network_allowed=False,
                             status="ok", source_summary={}, output_files=[])
        self.assertNotEqual(m1.compute_config_hash(), m2.compute_config_hash())

    def test_sanitise_path_removes_absolute(self):
        self.assertEqual(sanitise_path("/tmp/foo/bar/run_test.json"), "run_test.json")
        self.assertEqual(sanitise_path("C:\\Users\\test\\run.json"), "run.json")
        self.assertEqual(sanitise_path("relative/path/file.txt"), "file.txt")

    def test_as_dict_includes_config_hash(self):
        m = build_manifest(run_id="x", profile_name="p", profile_hash="h",
                             data_mode="fixture", no_send=True, network_allowed=False,
                             status="ok", source_summary={}, output_files=[])
        d = m.as_dict()
        self.assertIn("config_hash", d)

    def test_parent_shadow_id_optional(self):
        m = build_manifest(run_id="x", profile_name="p", profile_hash="h",
                             data_mode="fixture", no_send=True, network_allowed=False,
                             status="ok", source_summary={}, output_files=[],
                             parent_shadow_id="shadow-1")
        self.assertEqual(m.parent_shadow_id, "shadow-1")

    def test_as_dict_json_serializable(self):
        m = build_manifest(run_id="x", profile_name="p", profile_hash="h",
                             data_mode="fixture", no_send=True, network_allowed=False,
                             status="ok", source_summary={}, output_files=[])
        raw = json.dumps(m.as_dict(), default=str)
        self.assertIsNotNone(raw)

    def test_limitations_recorded(self):
        m = build_manifest(run_id="x", profile_name="p", profile_hash="h",
                             data_mode="fixture", no_send=True, network_allowed=False,
                             status="ok", source_summary={}, output_files=[],
                             limitations=["feed not wired"])
        self.assertIn("feed not wired", m.limitations)

    def test_diagnoses_recorded(self):
        d = [{"code": "TEST", "severity": "info", "summary": "test diag"}]
        m = build_manifest(run_id="x", profile_name="p", profile_hash="h",
                             data_mode="fixture", no_send=True, network_allowed=False,
                             status="ok", source_summary={}, output_files=[],
                             diagnoses=d)
        self.assertEqual(len(m.diagnoses), 1)


if __name__ == "__main__":
    unittest.main()
