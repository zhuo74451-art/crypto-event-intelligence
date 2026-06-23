"""Test Lane A V7 relock: verify that the pilot_v3 PRODUCER_LOCK.yaml
reflects the corrected Lane A SHA, resolved manifest hash basis, and
all lock-level assertions after the hash repair."""

import sys
import re
from pathlib import Path

_project_root = Path(__file__).resolve().parents[3]
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

import pytest

PILOT_V3_LOCK = Path(
    "data/intelligence/historical_market/pilot_v3/lane_a_input/PRODUCER_LOCK.yaml"
)
REPAIR_REQUEST = Path("docs/execution/lane_b/LANE_A_HASH_REPAIR_REQUEST.yaml")

EXPECTED_FINAL_SHA = "9aaabc82f34141e6797d3f92b773d5c463ad99b8"
EXPECTED_IMPL_SHA = "6f0848537ca5a5f7c257fb6c67c5d87e202d7d69"
EXPECTED_RELEASE_EVENTS_SHA_PREFIX = "ba93cce3"
EXPECTED_RECORD_COUNT = 12


def _read_text(path):
    """Read file content as utf-8 text."""
    return path.read_text(encoding="utf-8")


def _get_lock_value(key, text):
    """Extract value for a top-level key from raw lock text using regex."""
    pattern = re.compile(r"^" + re.escape(key) + r":\s*(.+)$", re.MULTILINE)
    m = pattern.search(text)
    if m:
        return m.group(1).strip()
    return None


class TestLaneAV7Relock:
    """Validate the Lane A V7 producer lock post-repair and its
    consistency with the hash repair resolution."""

    def test_pilot_v3_lock_file_exists(self):
        assert PILOT_V3_LOCK.exists(), f"Lock file not found: {PILOT_V3_LOCK}"

    def test_repair_request_file_exists(self):
        assert REPAIR_REQUEST.exists(), (
            f"Repair request not found: {REPAIR_REQUEST}"
        )

    def test_lane_a_final_sha_matches(self):
        text = _read_text(PILOT_V3_LOCK)
        actual = _get_lock_value("producer_final_sha", text)
        assert actual == EXPECTED_FINAL_SHA, (
            f"producer_final_sha expected {EXPECTED_FINAL_SHA}, got {actual}"
        )

    def test_lane_a_final_sha_in_repair_resolution(self):
        text = _read_text(REPAIR_REQUEST)
        pattern = re.compile(r"^resolved_lane_a_final_sha:\s*(.+)$", re.MULTILINE)
        m = pattern.search(text)
        assert m is not None, "resolved_lane_a_final_sha not found"
        assert m.group(1).strip() == EXPECTED_FINAL_SHA, (
            f"resolved_lane_a_final_sha expected {EXPECTED_FINAL_SHA}, "
            f"got {m.group(1).strip()}"
        )

    def test_lane_a_implementation_sha_matches(self):
        text = _read_text(PILOT_V3_LOCK)
        actual = _get_lock_value("producer_implementation_sha", text)
        assert actual == EXPECTED_IMPL_SHA, (
            f"producer_implementation_sha expected {EXPECTED_IMPL_SHA}, "
            f"got {actual}"
        )

    def test_manifest_hash_basis_is_git_object_bytes(self):
        text = _read_text(REPAIR_REQUEST)
        assert "hash_basis: git_object_bytes" in text, (
            "Repair request resolution missing hash_basis: git_object_bytes"
        )

    def test_hash_basis_commit_is_implementation_sha(self):
        text = _read_text(REPAIR_REQUEST)
        pattern = re.compile(r"^  hash_basis_commit:\s*(.+)$", re.MULTILINE)
        m = pattern.search(text)
        assert m is not None, "hash_basis_commit not found"
        assert m.group(1).strip() == EXPECTED_IMPL_SHA, (
            f"hash_basis_commit expected {EXPECTED_IMPL_SHA}, "
            f"got {m.group(1).strip()}"
        )

    def test_release_events_sha_matches_expected_prefix(self):
        text = _read_text(PILOT_V3_LOCK)
        sha = _get_lock_value("manifest_recorded_artifact_sha256", text)
        assert sha is not None, "manifest_recorded_artifact_sha256 not found"
        assert sha.startswith(EXPECTED_RELEASE_EVENTS_SHA_PREFIX), (
            f"manifest_recorded_artifact_sha256 does not start "
            f"with {EXPECTED_RELEASE_EVENTS_SHA_PREFIX}"
        )

    def test_actual_git_object_sha_matches_manifest_sha(self):
        text = _read_text(PILOT_V3_LOCK)
        manifest_sha = _get_lock_value("manifest_recorded_artifact_sha256", text)
        actual_sha = _get_lock_value("actual_git_object_artifact_sha256", text)
        assert manifest_sha == actual_sha, (
            f"manifest SHA ({manifest_sha}) != actual git object SHA "
            f"({actual_sha}) - expected convergence after relock"
        )

    def test_copied_artifact_sha_matches_actual(self):
        text = _read_text(PILOT_V3_LOCK)
        copied = _get_lock_value("copied_artifact_sha256", text)
        actual = _get_lock_value("actual_git_object_artifact_sha256", text)
        assert copied == actual, (
            f"copied SHA ({copied}) != actual git object SHA ({actual})"
        )

    def test_producer_lock_status_is_locked(self):
        text = _read_text(PILOT_V3_LOCK)
        status = _get_lock_value("producer_lock_status", text)
        assert status == "locked", (
            f"producer_lock_status expected locked, got {status}"
        )

    def test_manifest_artifact_hash_match_is_true(self):
        text = _read_text(PILOT_V3_LOCK)
        val = _get_lock_value("manifest_artifact_hash_match", text)
        assert val is not None, "manifest_artifact_hash_match not found"
        assert val.lower() == "true", (
            f"manifest_artifact_hash_match expected True, got {val}"
        )

    def test_manifest_artifact_hash_match_in_repair_resolution(self):
        text = _read_text(REPAIR_REQUEST)
        assert "manifest_artifact_hash_match: true" in text, (
            "Repair request resolution missing manifest_artifact_hash_match: true"
        )

    def test_source_and_copy_equal_is_true(self):
        text = _read_text(PILOT_V3_LOCK)
        val = _get_lock_value("source_and_copy_equal", text)
        assert val is not None, "source_and_copy_equal not found"
        assert val.lower() == "true", (
            f"source_and_copy_equal expected True, got {val}"
        )

    def test_source_and_copy_equal_in_repair_resolution(self):
        text = _read_text(REPAIR_REQUEST)
        assert "source_and_copy_equal: true" in text, (
            "Repair request resolution missing source_and_copy_equal: true"
        )

    def test_record_count_is_12(self):
        text = _read_text(PILOT_V3_LOCK)
        count_str = _get_lock_value("record_count", text)
        assert count_str is not None, "record_count not found"
        assert int(count_str) == EXPECTED_RECORD_COUNT, (
            f"record_count expected {EXPECTED_RECORD_COUNT}, got {count_str}"
        )
