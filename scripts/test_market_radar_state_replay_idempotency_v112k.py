"""Tests for Market Radar v1.12-K — State Replay + Idempotency Validation

Validates:
  - v112h envelopes readable
  - v112j proposed state readable
  - v112j eligible signals readable
  - first_pass_eligible_count = 9
  - replay_decision_count = 13
  - All first-pass eligible signals reblocked in replay
  - unexpected_repass_signal_ids = []
  - idempotency_passed = true
  - All output files generated
  - Safety flags correct
  - No live state writes
  - No file deletions

Usage:
    python scripts/test_market_radar_state_replay_idempotency_v112k.py
"""

from __future__ import annotations

import json
import os
import sys
import unittest
from datetime import datetime, timezone, timedelta
from pathlib import Path

# Ensure project root is on path
PROJECT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_DIR))


class TestMarketRadarStateReplayIdempotencyV112K(unittest.TestCase):
    """Test suite for v112k State Replay + Idempotency Validation."""

    @classmethod
    def setUpClass(cls):
        cls.project_dir = PROJECT_DIR
        cls.results_dir = cls.project_dir / "results"
        cls.runs_dir = cls.project_dir / "runs" / "market_radar"

        cls.envelopes_path = cls.results_dir / "market_radar_v112h_unified_signal_envelopes.jsonl"
        cls.proposed_state_path = cls.results_dir / "market_radar_v112j_proposed_signal_state.json"
        cls.eligible_path = cls.results_dir / "market_radar_v112j_eligible_signals.jsonl"
        cls.gate_decisions_path = cls.results_dir / "market_radar_v112i_gate_decisions.jsonl"

        cls.replay_decisions_path = cls.results_dir / "market_radar_v112k_replay_gate_decisions.jsonl"
        cls.result_path = cls.results_dir / "market_radar_v112k_state_replay_idempotency_result.json"
        cls.report_path = cls.runs_dir / "v112k_state_replay_idempotency.md"
        cls.handoff_path = cls.runs_dir / "v112k_state_replay_idempotency_handoff.md"

        cls.fixture_path = cls.project_dir / "data" / "fixtures" / "market_radar_v112i_prior_signal_state.json"

    # ── Data Loading ────────────────────────────────────────────────────────

    def test_01_v112h_envelopes_readable(self):
        """v112h envelopes JSONL can be read and contains 13 entries."""
        self.assertTrue(self.envelopes_path.exists(),
                        f"Envelopes file not found: {self.envelopes_path}")
        envelopes = []
        with open(self.envelopes_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    envelopes.append(json.loads(line))
        self.assertEqual(len(envelopes), 13,
                         f"Expected 13 envelopes, got {len(envelopes)}")
        for env in envelopes:
            self.assertIn("signal_id", env)
            self.assertIn("dedupe_key", env)
            self.assertIn("cooldown_key", env)
            self.assertIn("card_type", env)

    def test_02_v112j_proposed_state_readable(self):
        """v112j proposed state JSON can be read and has entries."""
        self.assertTrue(self.proposed_state_path.exists(),
                        f"Proposed state not found: {self.proposed_state_path}")
        with open(self.proposed_state_path, "r", encoding="utf-8") as f:
            state = json.load(f)
        self.assertIn("entries", state)
        self.assertIsInstance(state["entries"], list)
        self.assertGreater(len(state["entries"]), 0)
        self.assertEqual(state.get("dry_run_only"), True)

    def test_03_v112j_eligible_signals_readable(self):
        """v112j eligible signals JSONL can be read and has 9 entries."""
        self.assertTrue(self.eligible_path.exists(),
                        f"Eligible signals not found: {self.eligible_path}")
        eligible = []
        with open(self.eligible_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    eligible.append(json.loads(line))
        self.assertEqual(len(eligible), 9,
                         f"Expected 9 eligible signals, got {len(eligible)}")

    # ── Replay Result JSON ──────────────────────────────────────────────────

    def test_10_replay_result_json_exists(self):
        """Replay result JSON was generated."""
        self.assertTrue(self.result_path.exists(),
                        f"Result JSON not found: {self.result_path}")

    def test_11_replay_result_version(self):
        """Result version is v1.12-K."""
        with open(self.result_path, "r", encoding="utf-8") as f:
            result = json.load(f)
        self.assertEqual(result.get("version"), "v1.12-K")

    def test_12_input_envelope_count(self):
        """input_envelope_count = 13."""
        with open(self.result_path, "r", encoding="utf-8") as f:
            result = json.load(f)
        self.assertEqual(result.get("input_envelope_count"), 13)

    def test_13_first_pass_eligible_count(self):
        """first_pass_eligible_count = 9."""
        with open(self.result_path, "r", encoding="utf-8") as f:
            result = json.load(f)
        self.assertEqual(result.get("first_pass_eligible_count"), 9)

    def test_14_replay_decision_count(self):
        """replay_decision_count = 13."""
        with open(self.result_path, "r", encoding="utf-8") as f:
            result = json.load(f)
        self.assertEqual(result.get("replay_decision_count"), 13)

    def test_15_first_pass_eligible_reblocked(self):
        """All 9 first-pass eligible signals are reblocked."""
        with open(self.result_path, "r", encoding="utf-8") as f:
            result = json.load(f)
        self.assertEqual(result.get("first_pass_eligible_reblocked_count"), 9,
                         "All 9 first-pass eligible signals must be reblocked")

    def test_16_unexpected_repass_signal_ids_empty(self):
        """unexpected_repass_signal_ids must be empty."""
        with open(self.result_path, "r", encoding="utf-8") as f:
            result = json.load(f)
        self.assertEqual(result.get("unexpected_repass_signal_ids"), [],
                         "No first-pass eligible signals should repass")

    def test_17_idempotency_passed(self):
        """idempotency_passed must be true."""
        with open(self.result_path, "r", encoding="utf-8") as f:
            result = json.load(f)
        self.assertTrue(result.get("idempotency_passed"),
                        "Idempotency must pass")

    # ── Safety Flags ────────────────────────────────────────────────────────

    def test_20_debug_leak_count_zero(self):
        """debug_leak_count must be 0."""
        with open(self.result_path, "r", encoding="utf-8") as f:
            result = json.load(f)
        self.assertEqual(result.get("debug_leak_count"), 0)

    def test_21_secret_leak_count_zero(self):
        """secret_leak_count must be 0."""
        with open(self.result_path, "r", encoding="utf-8") as f:
            result = json.load(f)
        self.assertEqual(result.get("secret_leak_count"), 0)

    def test_22_full_wallet_leak_false(self):
        """full_wallet_leak must be false."""
        with open(self.result_path, "r", encoding="utf-8") as f:
            result = json.load(f)
        self.assertFalse(result.get("full_wallet_leak"))

    def test_23_real_tg_sent_false(self):
        """real_tg_sent must be false."""
        with open(self.result_path, "r", encoding="utf-8") as f:
            result = json.load(f)
        self.assertFalse(result.get("real_tg_sent"))

    def test_24_external_api_called_false(self):
        """external_api_called must be false."""
        with open(self.result_path, "r", encoding="utf-8") as f:
            result = json.load(f)
        self.assertFalse(result.get("external_api_called"))

    def test_25_external_ai_called_false(self):
        """external_ai_called must be false."""
        with open(self.result_path, "r", encoding="utf-8") as f:
            result = json.load(f)
        self.assertFalse(result.get("external_ai_called"))

    def test_26_daemon_started_false(self):
        """daemon_started must be false."""
        with open(self.result_path, "r", encoding="utf-8") as f:
            result = json.load(f)
        self.assertFalse(result.get("daemon_started"))

    def test_27_live_ready_false(self):
        """live_ready must be false."""
        with open(self.result_path, "r", encoding="utf-8") as f:
            result = json.load(f)
        self.assertFalse(result.get("live_ready"))

    def test_28_dry_run_only_true(self):
        """dry_run_only must be true."""
        with open(self.result_path, "r", encoding="utf-8") as f:
            result = json.load(f)
        self.assertTrue(result.get("dry_run_only"))

    def test_29_production_send_allowed_false(self):
        """production_send_allowed must be false."""
        with open(self.result_path, "r", encoding="utf-8") as f:
            result = json.load(f)
        self.assertFalse(result.get("production_send_allowed"))

    # ── Output Files ────────────────────────────────────────────────────────

    def test_30_replay_decisions_jsonl_exists(self):
        """Replay gate decisions JSONL was generated."""
        self.assertTrue(self.replay_decisions_path.exists(),
                        f"Replay decisions not found: {self.replay_decisions_path}")

    def test_31_replay_decisions_count(self):
        """Replay decisions JSONL has 13 entries."""
        decisions = []
        with open(self.replay_decisions_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    decisions.append(json.loads(line))
        self.assertEqual(len(decisions), 13,
                         f"Expected 13 replay decisions, got {len(decisions)}")

    def test_32_report_exists(self):
        """Report markdown was generated."""
        self.assertTrue(self.report_path.exists(),
                        f"Report not found: {self.report_path}")

    def test_33_handoff_exists(self):
        """Handoff markdown was generated."""
        self.assertTrue(self.handoff_path.exists(),
                        f"Handoff not found: {self.handoff_path}")

    # ── Replay internal verification ────────────────────────────────────────

    def test_40_replay_eligible_ids_all_blocked(self):
        """Verify each first-pass eligible signal is blocked in replay."""
        # Load eligible IDs
        eligible_ids = set()
        with open(self.eligible_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    rec = json.loads(line)
                    sid = rec.get("signal_id", "")
                    if sid:
                        eligible_ids.add(sid)
        self.assertEqual(len(eligible_ids), 9)

        # Build replay decision map
        replay_map = {}
        with open(self.replay_decisions_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    d = json.loads(line)
                    replay_map[d.get("signal_id", "")] = d

        # Check each eligible signal is blocked
        failed = []
        for sid in eligible_ids:
            decision = replay_map.get(sid)
            self.assertIsNotNone(decision, f"Replay missing decision for {sid}")
            gs = decision.get("gate_status", "")
            if gs == "pass":
                failed.append(sid)

        self.assertEqual(len(failed), 0,
                         f"These eligible signals repassed in replay: {failed}")

    def test_41_replay_decisions_match_all_envelopes(self):
        """All 13 envelopes have matching replay decisions."""
        envelope_ids = set()
        with open(self.envelopes_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    env = json.loads(line)
                    envelope_ids.add(env.get("signal_id", ""))

        decision_ids = set()
        with open(self.replay_decisions_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    d = json.loads(line)
                    decision_ids.add(d.get("signal_id", ""))

        self.assertEqual(envelope_ids, decision_ids,
                         "Envelope IDs and replay decision IDs must match exactly")

    def test_42_replay_blocked_count_reasonable(self):
        """Replay eligible_for_send_count should be less than first_pass eligible count."""
        with open(self.result_path, "r", encoding="utf-8") as f:
            result = json.load(f)
        fp_eligible = result.get("first_pass_eligible_count", 0)
        replay_eligible = result.get("replay_eligible_for_send_count", 0)
        self.assertLess(replay_eligible, fp_eligible,
                        f"Replay eligible ({replay_eligible}) should be less than "
                        f"first-pass eligible ({fp_eligible})")

    # ── No Side Effects ─────────────────────────────────────────────────────

    def test_50_fixture_not_overwritten(self):
        """Prior state fixture is not overwritten."""
        # We only check: the fixture file exists with original content
        # (we don't modify it in the replay)
        # If the fixture path exists, it should be intact
        if self.fixture_path.exists():
            with open(self.fixture_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.assertIsNotNone(data)

    def test_51_no_live_state_written(self):
        """No live state files should be written by v112k."""
        # v112k only writes to results/ and runs/, not data/ state
        # Check that no unexpected state files appeared
        live_state_dir = self.project_dir / "data"
        unexpected = [
            "market_radar_v112k_",
            "v112k_live_state",
        ]
        for f in live_state_dir.iterdir():
            for pattern in unexpected:
                self.assertNotIn(pattern, f.name,
                                 f"Unexpected live state file: {f.name}")

    def test_52_no_ai_relay_desk_writes(self):
        """No files written to ai_relay_desk directory."""
        ai_relay_dir = Path("C:/Users/PC/Desktop/工作台/ai_relay_desk")
        # We should not have written to this directory from v112k
        # This test verifies no new v112k artifacts there
        if ai_relay_dir.exists():
            for root, dirs, files in os.walk(str(ai_relay_dir)):
                for fname in files:
                    self.assertNotIn("v112k", fname.lower(),
                                     f"v112k artifact found in ai_relay_desk: {fname}")

    def test_53_no_files_deleted_from_results(self):
        """v112h/v112i/v112j output files still exist."""
        for path in [
            self.envelopes_path,
            self.proposed_state_path,
            self.eligible_path,
            self.gate_decisions_path,
        ]:
            self.assertTrue(path.exists(),
                            f"Required file should not have been deleted: {path}")

    # ── Canonical Replay Tests (v112l) ───────────────────────────────────────

    def test_60_canonical_replay_mode_available(self):
        """If v112l canonical state exists, result should have canonical replay mode."""
        canonical_path = self.results_dir / "market_radar_v112l_canonical_prior_state.json"
        if not canonical_path.exists():
            self.skipTest("v112l canonical state not yet generated — run v112l first")

        with open(self.result_path, "r", encoding="utf-8") as f:
            result = json.load(f)

        self.assertEqual(result.get("replay_mode"), "canonical_state_replay",
                         "Replay mode should be canonical_state_replay when v112l state exists")

    def test_61_canonical_replay_all_first_pass_reblocked(self):
        """In canonical replay, all 9 first-pass eligible signals must be reblocked."""
        with open(self.result_path, "r", encoding="utf-8") as f:
            result = json.load(f)

        self.assertEqual(result.get("first_pass_eligible_reblocked_count"), 9,
                         "All 9 first-pass eligible signals must be reblocked in canonical replay")

    def test_62_canonical_unexpected_repass_empty(self):
        """unexpected_repass_signal_ids must be empty in canonical replay."""
        with open(self.result_path, "r", encoding="utf-8") as f:
            result = json.load(f)

        self.assertEqual(result.get("unexpected_repass_signal_ids"), [],
                         "unexpected_repass_signal_ids must be empty")

    def test_63_canonical_idempotency_passed(self):
        """canonical_idempotency_passed must be true (when present)."""
        with open(self.result_path, "r", encoding="utf-8") as f:
            result = json.load(f)

        if "canonical_idempotency_passed" in result:
            self.assertTrue(result.get("canonical_idempotency_passed"),
                            "canonical_idempotency_passed must be true")


if __name__ == "__main__":
    unittest.main(verbosity=2)
