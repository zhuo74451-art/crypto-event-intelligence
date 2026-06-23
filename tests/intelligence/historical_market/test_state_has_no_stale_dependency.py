"""Test EXECUTION_STATE.yaml has no '33 temporary' or 'Lane A not yet available'
strings. Test lane_status contains 'pilot_v3'. Test next_exact_action is not
'commit and push'."""

import sys
from pathlib import Path

_project_root = Path(__file__).resolve().parents[3]
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

import pytest

STATE_FILE = Path("docs/execution/lane_b/EXECUTION_STATE.yaml")

STALE_PATTERNS = ["33 temporary", "Lane A not yet available"]
FORBIDDEN_NEXT_ACTION = "commit and push"
EXPECTED_LANE_STATUS_SUBSTRING = "pilot_v3"


class TestStateHasNoStaleDependency:
    """Validate that the execution state file does not reference stale
    dependencies or temporary data, and that it reflects the correct
    lane and next action."""

    def _read_text(self):
        assert STATE_FILE.exists(), (
            f"EXECUTION_STATE.yaml not found at {STATE_FILE}"
        )
        return STATE_FILE.read_text(encoding="utf-8")

    def test_state_file_exists(self):
        assert STATE_FILE.exists(), (
            f"EXECUTION_STATE.yaml not found at {STATE_FILE}"
        )

    def test_state_file_is_nonempty(self):
        assert STATE_FILE.stat().st_size > 0, "EXECUTION_STATE.yaml is empty"

    def test_no_33_temporary_string(self):
        text = self._read_text()
        assert "33 temporary" not in text, (
            "EXECUTION_STATE.yaml contains stale reference '33 temporary'"
        )

    def test_no_lane_a_not_yet_available_string(self):
        text = self._read_text()
        assert "Lane A not yet available" not in text, (
            "EXECUTION_STATE.yaml contains stale reference "
            "'Lane A not yet available'"
        )

    def test_no_stale_patterns(self):
        text = self._read_text()
        found = [p for p in STALE_PATTERNS if p in text]
        assert not found, (
            f"EXECUTION_STATE.yaml contains stale pattern(s): {found}"
        )

    def test_lane_status_contains_pilot_v3(self):
        """The lane_status or current_stage should reference pilot_v3."""
        text = self._read_text()
        # Check current_stage and dependency_status sections
        assert "pilot_v3" in text or "lane_a_producer_relocked" in text, (
            "EXECUTION_STATE.yaml does not contain 'pilot_v3' — "
            "lane may not be up to date"
        )

    def test_next_exact_action_is_not_commit_and_push(self):
        text = self._read_text()
        assert "commit and push" not in text, (
            "EXECUTION_STATE.yaml next_exact_action is 'commit and push' — "
            "expected a different action (e.g., 'review and validate')"
        )

    def test_next_exact_action_is_defined(self):
        text = self._read_text()
        assert "next_exact_action:" in text, (
            "EXECUTION_STATE.yaml missing 'next_exact_action' field"
        )
