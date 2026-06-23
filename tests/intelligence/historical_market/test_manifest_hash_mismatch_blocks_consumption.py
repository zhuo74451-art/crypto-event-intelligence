"""Test that LANE_A_HASH_REPAIR_REQUEST.yaml exists and that
source_and_copy_equal is true but manifest_artifact_hash_match is false."""

import sys
from pathlib import Path

_project_root = Path(__file__).resolve().parents[3]
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

import pytest

REPAIR_REQUEST_FILE = Path(
    "docs/execution/lane_b/LANE_A_HASH_REPAIR_REQUEST.yaml"
)


class TestManifestHashMismatchBlocksConsumption:
    """Validate that the hash repair request exists and documents the
    manifest mismatch where source_and_copy_equal=True but the manifest
    recorded hash does not match the actual file hash."""

    def _read_text(self):
        # File contains non-UTF-8 bytes; read as latin-1 to preserve content
        return REPAIR_REQUEST_FILE.read_text(encoding="latin-1")

    def test_repair_request_file_exists(self):
        assert REPAIR_REQUEST_FILE.exists(), (
            f"LANE_A_HASH_REPAIR_REQUEST.yaml not found at {REPAIR_REQUEST_FILE}"
        )

    def test_repair_request_is_nonempty(self):
        assert REPAIR_REQUEST_FILE.stat().st_size > 0, (
            "Repair request file is empty"
        )

    def test_source_and_copy_equal_is_true(self):
        """The source file and the copied artifact must be byte-identical."""
        text = self._read_text()
        assert "source_and_copy_equal: True" in text, (
            "Expected source_and_copy_equal: True not found in repair request"
        )

    def test_manifest_artifact_hash_match_is_false(self):
        """The manifest recorded hash must differ from the actual artifact
        hash, meaning manifest_artifact_hash_match is effectively false."""
        text = self._read_text()
        # Parse the three SHA values from the YAML
        manifest_sha = None
        actual_sha = None
        copied_sha = None
        for line in text.strip().split("\n"):
            stripped = line.strip()
            if stripped.startswith("manifest_recorded_sha256:"):
                manifest_sha = stripped.split(":", 1)[1].strip()
            elif stripped.startswith("actual_git_artifact_sha256:"):
                actual_sha = stripped.split(":", 1)[1].strip()
            elif stripped.startswith("copied_artifact_sha256:"):
                copied_sha = stripped.split(":", 1)[1].strip()

        assert manifest_sha is not None, (
            "Could not find manifest_recorded_sha256 in repair request"
        )
        assert actual_sha is not None, (
            "Could not find actual_git_artifact_sha256 in repair request"
        )
        assert copied_sha is not None, (
            "Could not find copied_artifact_sha256 in repair request"
        )

        # source_and_copy_equal=True means actual SHA == copied SHA
        assert actual_sha == copied_sha, (
            f"actual_git_artifact_sha256 ({actual_sha}) != "
            f"copied_artifact_sha256 ({copied_sha}) — "
            "they must match when source_and_copy_equal is True"
        )

        # manifest_artifact_hash_match is false because manifest SHA
        # does not match the actual artifact SHA
        assert manifest_sha != actual_sha, (
            f"manifest_recorded_sha256 ({manifest_sha}) unexpectedly equals "
            f"actual_git_artifact_sha256 ({actual_sha}) — "
            "expected a manifest hash mismatch"
        )
