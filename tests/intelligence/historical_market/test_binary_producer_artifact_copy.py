"""Test that the Lane A artifact was byte-preserved (SHA256 check)
and that PRODUCER_LOCK.yaml exists in the expected lane path."""

import sys
from pathlib import Path

_project_root = Path(__file__).resolve().parents[3]
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

import hashlib
import pytest

LANE_A_DIR = Path("data/intelligence/historical_market/pilot_v2/lane_a_input")
LOCK_FILE = LANE_A_DIR / "PRODUCER_LOCK.yaml"
EVENTS_FILE = Path(
    "data/intelligence/historical_market/pilot_v3/lane_a_input/macro_release_events_v1.jsonl"
)
EXPECTED_ARTIFACT_SHA = "ba93cce3ca298fdb48ecf690247ad449b57a0afe826f8832b587498c8f62fc1c"


class TestBinaryProducerArtifactCopy:
    """Validate that the Lane A event artifact is byte-identical (SHA256)
    and the producer lock file is present."""

    def test_producer_lock_exists(self):
        assert LOCK_FILE.exists(), (
            f"PRODUCER_LOCK.yaml not found at {LOCK_FILE}"
        )

    def test_lock_contains_expected_sha(self):
        """The lock file must record the known artifact SHA256."""
        text = LOCK_FILE.read_text(encoding="utf-8")
        assert EXPECTED_ARTIFACT_SHA in text, (
            f"Expected SHA256 {EXPECTED_ARTIFACT_SHA} not found in lock file"
        )

    def test_artifact_sha256_matches_expected(self):
        """The events JSONL file must hash to the expected SHA256."""
        sha256_hash = hashlib.sha256()
        with open(EVENTS_FILE, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                sha256_hash.update(chunk)
        actual_sha = sha256_hash.hexdigest()
        assert actual_sha == EXPECTED_ARTIFACT_SHA, (
            f"Artifact SHA256 mismatch:\n"
            f"  Expected: {EXPECTED_ARTIFACT_SHA}\n"
            f"  Actual:   {actual_sha}"
        )

    def test_events_file_exists_and_nonempty(self):
        assert EVENTS_FILE.exists(), f"Events file not found: {EVENTS_FILE}"
        assert EVENTS_FILE.stat().st_size > 0, "Events file is empty"
