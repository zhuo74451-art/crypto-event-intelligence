"""Test Lane C is unblocked only after Lane A relock: verify execution state,
pilot V3 manifest, absence of placeholders, repair request resolution,
output file counts, and no stale Lane A SHA references."""

import sys
import json
from pathlib import Path

_project_root = Path(__file__).resolve().parents[3]
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

import pytest

STATE_FILE = Path("docs/execution/lane_b/EXECUTION_STATE.yaml")
V3_MANIFEST = Path("docs/execution/lane_b/PILOT_V3_INTEGRATION_MANIFEST.yaml")
REPAIR_REQUEST = Path("docs/execution/lane_b/LANE_A_HASH_REPAIR_REQUEST.yaml")
PILOT_DIR = Path("data/intelligence/historical_market/pilot_v3")

EXPECTED_FILE_COUNTS = {
    "horizon_windows_v3.jsonl": 72,
    "reaction_labels_v3.jsonl": 72,
    "cross_asset_context_v3.jsonl": 120,
    "funding_context_v3.jsonl": 24,
}

PLACEHOLDER_PATTERNS = ["CHANGE_ME", "UPDATE_ME"]
OLD_LANE_A_SHA = "2c582860da37086f2ed0b89aa9efa1ad83c5d63d"

class TestLaneCUnblockedOnlyAfterRelock:
    """Validate that Lane C consumption is permitted only after the
    Lane A relock has been completed and all state files are clean."""

    def _read_text(self, path):
        return path.read_text(encoding="utf-8")

    def test_execution_state_allows_lane_c_consumption(self):
        text = self._read_text(STATE_FILE)
        assert "lane_c_pilot_consumption_allowed: true" in text, (
            "EXECUTION_STATE.yaml missing lane_c_pilot_consumption_allowed: true"
        )

    def test_v3_manifest_has_lane_c_pilot_consumption(self):
        text = self._read_text(V3_MANIFEST)
        assert "lane_c_pilot_consumption: True" in text, (
            "PILOT_V3_INTEGRATION_MANIFEST.yaml missing lane_c_pilot_consumption: True"
        )

    def test_no_change_me_in_execution_state(self):
        text = self._read_text(STATE_FILE)
        assert "CHANGE_ME" not in text, (
            "EXECUTION_STATE.yaml still contains CHANGE_ME placeholder"
        )

    def test_no_update_me_in_execution_state(self):
        text = self._read_text(STATE_FILE)
        assert "UPDATE_ME" not in text, (
            "EXECUTION_STATE.yaml still contains UPDATE_ME placeholder"
        )

    def test_no_change_me_in_v3_manifest(self):
        text = self._read_text(V3_MANIFEST)
        assert "CHANGE_ME" not in text, (
            "PILOT_V3_INTEGRATION_MANIFEST.yaml still contains CHANGE_ME placeholder"
        )

    def test_no_update_me_in_v3_manifest(self):
        text = self._read_text(V3_MANIFEST)
        assert "UPDATE_ME" not in text, (
            "PILOT_V3_INTEGRATION_MANIFEST.yaml still contains UPDATE_ME placeholder"
        )

    def test_no_placeholders_in_any_state_file(self):
        for label, fpath in [
            ("EXECUTION_STATE.yaml", STATE_FILE),
            ("PILOT_V3_INTEGRATION_MANIFEST.yaml", V3_MANIFEST),
            ("LANE_A_HASH_REPAIR_REQUEST.yaml", REPAIR_REQUEST),
        ]:
            text = self._read_text(fpath)
            for pat in PLACEHOLDER_PATTERNS:
                assert pat not in text, (
                    f"{label} still contains placeholder {pat}"
                )

    def test_repair_request_has_status_resolved(self):
        text = self._read_text(REPAIR_REQUEST)
        assert "status: resolved" in text, (
            "LANE_A_HASH_REPAIR_REQUEST.yaml does not have status: resolved"
        )

    def test_repair_request_has_resolution_block(self):
        text = self._read_text(REPAIR_REQUEST)
        assert "resolution:" in text, (
            "LANE_A_HASH_REPAIR_REQUEST.yaml missing resolution: block"
        )

    def test_repair_request_resolution_has_hash_match(self):
        text = self._read_text(REPAIR_REQUEST)
        assert "manifest_artifact_hash_match: true" in text, (
            "Repair request resolution missing manifest_artifact_hash_match: true"
        )

    def test_repair_request_resolution_has_copy_equal(self):
        text = self._read_text(REPAIR_REQUEST)
        assert "source_and_copy_equal: true" in text, (
            "Repair request resolution missing source_and_copy_equal: true"
        )

    def _count_jsonl_records(self, filename):
        fpath = PILOT_DIR / filename
        assert fpath.exists(), f"Output file not found: {fpath}"
        count = 0
        with open(fpath, "r") as f:
            for line in f:
                line = line.strip()
                if line:
                    count += 1
        return count

    def test_horizon_windows_count(self):
        count = self._count_jsonl_records("horizon_windows_v3.jsonl")
        expected = EXPECTED_FILE_COUNTS["horizon_windows_v3.jsonl"]
        assert count == expected, (
            f"horizon_windows_v3.jsonl: expected {expected}, got {count}"
        )

    def test_reaction_labels_count(self):
        count = self._count_jsonl_records("reaction_labels_v3.jsonl")
        expected = EXPECTED_FILE_COUNTS["reaction_labels_v3.jsonl"]
        assert count == expected, (
            f"reaction_labels_v3.jsonl: expected {expected}, got {count}"
        )

    def test_cross_asset_context_count(self):
        count = self._count_jsonl_records("cross_asset_context_v3.jsonl")
        expected = EXPECTED_FILE_COUNTS["cross_asset_context_v3.jsonl"]
        assert count == expected, (
            f"cross_asset_context_v3.jsonl: expected {expected}, got {count}"
        )

    def test_funding_context_count(self):
        count = self._count_jsonl_records("funding_context_v3.jsonl")
        expected = EXPECTED_FILE_COUNTS["funding_context_v3.jsonl"]
        assert count == expected, (
            f"funding_context_v3.jsonl: expected {expected}, got {count}"
        )

    def test_no_old_lane_a_sha_in_execution_state(self):
        text = self._read_text(STATE_FILE)
        assert OLD_LANE_A_SHA not in text, (
            f"EXECUTION_STATE.yaml still references old Lane A SHA {OLD_LANE_A_SHA}"
        )

    def test_no_old_lane_a_sha_in_v3_manifest(self):
        text = self._read_text(V3_MANIFEST)
        assert OLD_LANE_A_SHA not in text, (
            f"PILOT_V3_INTEGRATION_MANIFEST.yaml still references old Lane A SHA {OLD_LANE_A_SHA}"
        )

    def test_no_old_lane_a_sha_in_repair_resolution(self):
        text = self._read_text(REPAIR_REQUEST)
        resolution_idx = text.find("resolution:")
        if resolution_idx >= 0:
            resolution_text = text[resolution_idx:]
            assert OLD_LANE_A_SHA not in resolution_text, (
                f"Old Lane A SHA {OLD_LANE_A_SHA} found in resolution section"
            )

    def test_execution_state_references_new_sha(self):
        text = self._read_text(STATE_FILE)
        assert "9aaabc82f34141e6797d3f92b773d5c463ad99b8" in text, (
            "EXECUTION_STATE.yaml does not reference new Lane A SHA"
        )

    def test_v3_manifest_references_new_sha(self):
        text = self._read_text(V3_MANIFEST)
        assert "9aaabc82f34141e6797d3f92b773d5c463ad99b8" in text, (
            "PILOT_V3_INTEGRATION_MANIFEST.yaml does not reference new Lane A SHA"
        )
