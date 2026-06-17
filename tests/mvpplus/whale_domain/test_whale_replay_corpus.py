"""Whale Replay Corpus — deterministic replay test runner.

Reads whale_replay_corpus_v1.json, replays each case through the real
W2 Domain (detect_all_changes + generate_alert_candidates), and asserts
expected outputs. No network, no random, no system clock.

Expected values come exclusively from the corpus file — the test never
re-implements domain logic.
"""

from __future__ import annotations

import json
import os
import unittest
from pathlib import Path
from typing import Any

from market_radar.whale_domain.models import (
    WhalePositionInput, WhaleSnapshot, ChangeType,
    extract_snapshot, snapshot_to_dict, make_position_key, dict_to_snapshot,
)
from market_radar.whale_domain.change_detector import detect_all_changes
from market_radar.whale_domain.alert_candidate import generate_alert_candidates

CORPUS_PATH = Path(__file__).resolve().parent / "fixtures" / "whale_replay_corpus_v1.json"

# ── Helpers ────────────────────────────────────────────────────────────────


def _load_corpus() -> dict[str, Any]:
    with open(CORPUS_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def _dict_to_input(d: dict) -> WhalePositionInput:
    return WhalePositionInput(
        address=d.get("address", ""),
        label=d.get("label"),
        coin=d.get("coin", ""),
        signed_size=float(d.get("signed_size", 0)),
        entry_price=float(d.get("entry_price", 0)),
        mark_price=float(d.get("mark_price", 0)),
        position_value_usd=float(d.get("position_value_usd", 0)),
        leverage=float(d.get("leverage", 0)),
        unrealized_pnl_usd=d.get("unrealized_pnl_usd"),
        liquidation_price=d.get("liquidation_price"),
        snapshot_time_utc=d.get("snapshot_time_utc", ""),
    )


def _dict_to_snapshot(key: str, d: dict) -> WhaleSnapshot:
    """Convert a stored snapshot dict to WhaleSnapshot, ignoring None direction."""
    # Handle potential None direction for zero-size snapshots
    direction = d.get("direction", "long")
    return WhaleSnapshot(
        address=d.get("address", ""),
        label=d.get("label"),
        coin=d.get("coin", ""),
        direction=direction,
        signed_size=float(d.get("signed_size", 0)),
        absolute_size=abs(float(d.get("signed_size", 0))),
        position_value_usd=float(d.get("position_value_usd", 0)),
        entry_price=float(d.get("entry_price", 0)),
        mark_price=float(d.get("mark_price", 0)),
        leverage=float(d.get("leverage", 0)),
        unrealized_pnl_usd=d.get("unrealized_pnl_usd"),
        liquidation_price=d.get("liquidation_price"),
        liquidation_distance_pct=d.get("liquidation_distance_pct"),
        snapshot_time_utc=d.get("snapshot_time_utc", ""),
    )


def _build_previous_state(
    snapshots_dict: dict[str, dict],
) -> dict[str, WhaleSnapshot]:
    result: dict[str, WhaleSnapshot] = {}
    for key, snap_data in snapshots_dict.items():
        result[key] = _dict_to_snapshot(key, snap_data)
    return result


def _normalize_ct(ct_val: str) -> str:
    """Normalize change type string for comparison."""
    return ct_val.replace("_", "_")


# ── Schema Validator ───────────────────────────────────────────────────────


def _validate_case_schema(case: dict, case_id: str) -> list[str]:
    errors: list[str] = []
    required = [
        "case_id", "category", "description",
        "previous_snapshots", "current_inputs",
        "is_baseline_run", "detected_at_utc",
        "expected_change_types", "expected_directions",
        "expected_alert_types", "forbidden_alert_types",
        "expected_risk_flags",
        "expected_change_count", "expected_alert_count",
        "notes",
    ]
    for field in required:
        if field not in case:
            errors.append(f"{case_id}: missing required field '{field}'")

    if not isinstance(case.get("expected_change_types"), list):
        errors.append(f"{case_id}: expected_change_types must be a list")
    if not isinstance(case.get("expected_alert_types"), list):
        errors.append(f"{case_id}: expected_alert_types must be a list")
    if not isinstance(case.get("forbidden_alert_types"), list):
        errors.append(f"{case_id}: forbidden_alert_types must be a list")

    # Check for forbidden fields
    forbidden = ["api_key", "api_secret", "private_key", "wallet", "rpc_url",
                 "http_endpoint", "password", "secret", "token"]
    case_str = json.dumps(case)
    for f in forbidden:
        if f in case_str.lower():
            errors.append(f"{case_id}: contains forbidden field '{f}'")

    # Check for runtime-generated timestamps
    for inp in case.get("current_inputs", []):
        ts = inp.get("snapshot_time_utc", "")
        if ts and "now" in ts.lower():
            errors.append(f"{case_id}: runtime-generated timestamp in current_inputs")

    return errors


# ── Tests ──────────────────────────────────────────────────────────────────

CORPUS = _load_corpus()
CORPUS_CASES = CORPUS.get("cases", [])


class TestWhaleReplayCorpusSchema(unittest.TestCase):
    """Validate corpus structure and field completeness."""

    def test_corpus_meta_present(self):
        self.assertIn("corpus_meta", CORPUS)
        meta = CORPUS["corpus_meta"]
        self.assertIn("name", meta)
        self.assertIn("ticket", meta)

    def test_case_ids_unique(self):
        ids = [c.get("case_id") for c in CORPUS_CASES]
        self.assertEqual(len(ids), len(set(ids)), "Duplicate case_ids found")

    def test_all_cases_pass_schema(self):
        all_errors = []
        for case in CORPUS_CASES:
            cid = case.get("case_id", "?")
            errors = _validate_case_schema(case, cid)
            all_errors.extend(errors)
        self.assertEqual(
            all_errors, [],
            f"Schema validation errors:\n" + "\n".join(all_errors),
        )


class TestWhaleReplayCorpusRunner(unittest.TestCase):
    """Replay each corpus case through the real W2 Domain."""

    def _run_case(self, case: dict):
        case_id = case.get("case_id", "?")

        # Build previous state
        prev_state = _build_previous_state(case.get("previous_snapshots", {}))

        # Build current inputs
        current_inputs = [
            _dict_to_input(inp) for inp in case.get("current_inputs", [])
        ]

        # Run domain
        changes = detect_all_changes(
            current_inputs=current_inputs,
            previous_snapshots=prev_state,
            is_baseline_run=case.get("is_baseline_run", False),
            detected_at_utc=case.get("detected_at_utc", ""),
        )

        # Build snapshots for alert generation
        snapshots = [extract_snapshot(inp) for inp in current_inputs]

        # Run alert generation
        alerts = generate_alert_candidates(
            snapshots=snapshots,
            changes=changes,
            generated_at_utc=case.get("detected_at_utc", ""),
        )

        # Extract results
        change_types = sorted([c.change_type for c in changes])
        directions = [c.direction for c in changes]
        alert_types = sorted([a.alert_type for a in alerts])
        risk_flag_ids = sorted(set(
            rf for c in changes for rf in c.risk_flags
        ))

        expected_ct = sorted(case.get("expected_change_types", []))
        expected_dir = case.get("expected_directions", [])
        expected_at = sorted(case.get("expected_alert_types", []))
        forbidden_at = case.get("forbidden_alert_types", [])
        expected_rf = sorted(case.get("expected_risk_flags", []))
        expected_change_count = case.get("expected_change_count", 0)
        expected_alert_count = case.get("expected_alert_count", 0)

        # Assert change count
        self.assertEqual(
            len(changes), expected_change_count,
            f"[{case_id}] change count mismatch: got {len(changes)}, "
            f"expected {expected_change_count}. Got types: {change_types}",
        )

        # Assert change types
        self.assertEqual(
            change_types, expected_ct,
            f"[{case_id}] change types mismatch: got {change_types}, "
            f"expected {expected_ct}",
        )

        # Assert directions
        if directions:
            self.assertEqual(
                directions, expected_dir,
                f"[{case_id}] directions mismatch: got {directions}, "
                f"expected {expected_dir}",
            )

        # Assert alert count
        self.assertEqual(
            len(alerts), expected_alert_count,
            f"[{case_id}] alert count mismatch: got {len(alerts)}, "
            f"expected {expected_alert_count}. Got types: {alert_types}",
        )

        # Assert alert types
        self.assertEqual(
            alert_types, expected_at,
            f"[{case_id}] alert types mismatch: got {alert_types}, "
            f"expected {expected_at}",
        )

        # Assert forbidden alerts absent
        for forbidden in forbidden_at:
            self.assertNotIn(
                forbidden, alert_types,
                f"[{case_id}] forbidden alert '{forbidden}' appeared in output",
            )

        # Assert risk flags
        self.assertEqual(
            risk_flag_ids, expected_rf,
            f"[{case_id}] risk flags mismatch: got {risk_flag_ids}, "
            f"expected {expected_rf}",
        )


# Dynamically generate one test method per corpus case
def _make_case_test(case: dict):
    case_id = case["case_id"]
    category = case.get("category", "uncategorized")
    desc = case.get("description", "")

    def test(self):
        self._run_case(case)

    test.__name__ = f"test_{case_id.lower()}_{category[:20]}"
    test.__doc__ = f"[{case_id}] {desc}"
    return test


for _case in CORPUS_CASES:
    test_method = _make_case_test(_case)
    setattr(TestWhaleReplayCorpusRunner, test_method.__name__, test_method)

# Clean up module-level test references
test_method = None


# ── Edge Case Integration Tests ────────────────────────────────────────────

class TestWhaleCorpusEdgeCases(unittest.TestCase):
    """Specific edge cases that need standalone verification beyond corpus."""

    def setUp(self):
        self.corpus = _load_corpus()

    def test_c001_baseline_long_not_open(self):
        """C001: Baseline position must NOT be open_long."""
        changes = self._get_changes("C001")
        for c in changes:
            self.assertNotEqual(c.change_type, "open_long",
                                f"[C001] baseline produced open_long")

    def test_c003_baseline_suppresses_large_new_position(self):
        """C003: Baseline with 3.25M must NOT produce large_new_position."""
        changes = self._get_changes("C003")
        for c in changes:
            self.assertEqual(c.change_type, "baseline_open_position")
            self.assertNotIn("R3_LARGE_POSITION_OPEN", c.risk_flags)

    def test_c008_exact_zero_uses_previous_direction(self):
        """C008: signed_size=0 from long must produce close_long."""
        changes = self._get_changes("C008")
        self.assertEqual(len(changes), 1)
        self.assertEqual(changes[0].change_type, "close_long")
        self.assertEqual(changes[0].direction, "long")

    def test_c009_exact_zero_short_uses_previous_direction(self):
        """C009: signed_size=0 from short must produce close_short."""
        changes = self._get_changes("C009")
        self.assertEqual(len(changes), 1)
        self.assertEqual(changes[0].change_type, "close_short")
        self.assertEqual(changes[0].direction, "short")

    def test_c010_disappeared_has_no_current(self):
        """C010: Disappeared position must have current=None."""
        changes = self._get_changes("C010")
        self.assertEqual(len(changes), 1)
        self.assertIsNone(changes[0].current,
                          "Disappeared position should have current=None")
        self.assertIsNotNone(changes[0].previous,
                             "Disappeared position should have previous")

    def test_c014_widened_is_no_change_excluded(self):
        """C014: Widened liq distance must produce 0 changes."""
        changes = self._get_changes("C014")
        self.assertEqual(len(changes), 0)

    def test_c019_jitter_is_no_change_excluded(self):
        """C019: Size jitter below threshold must produce 0 changes."""
        changes = self._get_changes("C019")
        self.assertEqual(len(changes), 0)

    def test_c024_zero_baseline_no_change(self):
        """C024: Zero-size baseline must produce 0 changes."""
        changes = self._get_changes("C024")
        self.assertEqual(len(changes), 0)

    def test_c027_baseline_suppresses_r3(self):
        """C027: Baseline with 2M must NOT trigger R3."""
        changes = self._get_changes("C027")
        self.assertEqual(len(changes), 1)
        self.assertEqual(changes[0].change_type, "baseline_open_position")
        self.assertNotIn("R3_LARGE_POSITION_OPEN", changes[0].risk_flags)

    def test_c030_invalid_liq_no_narrowed(self):
        """C030: Negative/null liq diff must not trigger narrowed."""
        changes = self._get_changes("C030")
        for c in changes:
            self.assertNotEqual(c.change_type, "liquidation_distance_narrowed")

    def _get_changes(self, case_id: str):
        case = next((c for c in self.corpus["cases"]
                     if c["case_id"] == case_id), None)
        if case is None:
            self.fail(f"Case {case_id} not found")
        prev_state = _build_previous_state(case.get("previous_snapshots", {}))
        current_inputs = [_dict_to_input(inp) for inp in case.get("current_inputs", [])]
        return detect_all_changes(
            current_inputs=current_inputs,
            previous_snapshots=prev_state,
            is_baseline_run=case.get("is_baseline_run", False),
            detected_at_utc=case.get("detected_at_utc", ""),
        )


if __name__ == "__main__":
    unittest.main()
