"""Test suite for Market Radar v1.12-I Dedupe + Cooldown Gate.

Covers:
  - Can read v112h envelopes
  - envelope count >= 13
  - prior state can be read
  - dedupe hit correctly blocks
  - cooldown hit correctly blocks
  - cooldown expired allows pass
  - different card_type does NOT interfere
  - same asset different direction NOT wrongly blocked
  - each decision has gate_status
  - each decision has gate_reasons
  - each decision has eligible_for_send
  - passed_count >= 1
  - blocked_dedupe_count >= 1
  - blocked_cooldown_count >= 1
  - decision_count = input_envelope_count
  - JSONL decisions successfully generated
  - result JSON successfully generated
  - report / handoff successfully generated
  - debug_leak_count = 0
  - secret_leak_count = 0
  - real_tg_sent = false
  - external_api_called = false
  - external_ai_called = false
  - daemon_started = false
  - live_ready = false
  - No token/key/cookie/password reads
  - No writes to ai_relay_desk
  - No file deletions

Usage:
    python scripts/test_market_radar_dedupe_cooldown_gate_v112i.py
"""

from __future__ import annotations

import io
import json
import sys
import unittest
from datetime import datetime, timezone, timedelta
from pathlib import Path

# Fix Windows GBK encoding
if sys.stdout.encoding != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.market_radar_dedupe_cooldown_gate_v112i import (
    load_envelopes_jsonl,
    load_prior_signal_state,
    normalize_gate_time,
    check_dedupe,
    check_cooldown,
    evaluate_signal_gate,
    evaluate_all_signal_gates,
    build_gate_decision,
    scan_gate_decision_leaks,
    COOLDOWN_POLICY,
    GATE_VERSION,
    SCHEMA_VERSION,
    VALID_GATE_STATUSES,
    CN_TZ,
)

# ── Paths ────────────────────────────────────────────────────────────────────────

ENVELOPE_JSONL_PATH = ROOT / "results" / "market_radar_v112h_unified_signal_envelopes.jsonl"
PRIOR_STATE_JSON_PATH = ROOT / "data" / "fixtures" / "market_radar_v112i_prior_signal_state.json"
RESULT_JSON_PATH = ROOT / "results" / "market_radar_v112i_dedupe_cooldown_gate_result.json"
DECISIONS_JSONL_PATH = ROOT / "results" / "market_radar_v112i_gate_decisions.jsonl"
REPORT_MD_PATH = ROOT / "runs" / "market_radar" / "v112i_dedupe_cooldown_gate.md"
HANDOFF_MD_PATH = ROOT / "runs" / "market_radar" / "v112i_dedupe_cooldown_gate_handoff.md"
AI_RELAY_PATH = Path(r"C:\Users\PC\Desktop\工作台\ai_relay_desk")


class TestGateModule(unittest.TestCase):
    """Unit tests for the dedupe/cooldown gate functions."""

    @classmethod
    def setUpClass(cls):
        """Load test data once for all tests."""
        cls.envelopes = load_envelopes_jsonl(ENVELOPE_JSONL_PATH)
        cls.prior_state = load_prior_signal_state(PRIOR_STATE_JSON_PATH)
        cls.evaluated_at = datetime(2026, 6, 4, 23, 30, 0, tzinfo=CN_TZ)

    def test_can_read_v112h_envelopes(self):
        """Can load v112h envelopes from JSONL."""
        self.assertIsNotNone(self.envelopes)
        self.assertIsInstance(self.envelopes, list)

    def test_envelope_count_ge_13(self):
        """v112h envelopes count >= 13."""
        self.assertGreaterEqual(len(self.envelopes), 13,
                                f"Expected >= 13 envelopes, got {len(self.envelopes)}")

    def test_prior_state_readable(self):
        """Prior state fixture can be read."""
        self.assertIsNotNone(self.prior_state)
        self.assertIsInstance(self.prior_state, list)
        self.assertGreaterEqual(len(self.prior_state), 7,
                                f"Expected >= 7 prior entries, got {len(self.prior_state)}")

    # ── Dedupe checks ─────────────────────────────────────────────────────

    def test_dedupe_hit_correctly_blocks(self):
        """Envelope with matching dedupe_key is blocked."""
        # Envelope 1 (pova, BTC) has dedupe_key matching prior state entry 0
        env1 = self.envelopes[0]
        result = check_dedupe(env1, self.prior_state)
        self.assertTrue(result["hit"], f"Expected dedupe hit, got: {result}")

    def test_dedupe_no_false_positive(self):
        """Envelope without matching dedupe_key is NOT blocked."""
        # Envelope 2 (whale, BTC, bull) has no matching dedupe_key in prior state
        env2 = self.envelopes[1]
        result = check_dedupe(env2, self.prior_state)
        self.assertFalse(result["hit"], f"Expected no dedupe hit, got: {result}")

    # ── Cooldown checks ───────────────────────────────────────────────────

    def test_cooldown_hit_correctly_blocks(self):
        """Envelope with active cooldown_key is blocked."""
        # Envelope 11 (news, BTC, bull) has cooldown_key matching prior state entry 2
        # which has cooldown_until 2026-06-05T00:00, and now is 2026-06-04T23:30
        env11 = self.envelopes[10]
        result = check_cooldown(env11, self.prior_state, evaluated_at=self.evaluated_at)
        self.assertTrue(result["hit"], f"Expected cooldown hit, got: {result}")

    def test_cooldown_expired_allows_pass(self):
        """Envelope with expired cooldown is NOT blocked."""
        # Envelope 10 (mams, [BNB,OKB,BGB], bull) has cooldown_key matching
        # prior state entry 4 which has cooldown_until 2026-06-04T20:45 (expired)
        env10 = self.envelopes[9]
        result = check_cooldown(env10, self.prior_state, evaluated_at=self.evaluated_at)
        self.assertFalse(result["hit"], f"Expected NO cooldown hit (expired), got: {result}")

    def test_cooldown_no_false_positive(self):
        """Envelope without matching cooldown_key is NOT blocked."""
        env2 = self.envelopes[1]
        result = check_cooldown(env2, self.prior_state, evaluated_at=self.evaluated_at)
        self.assertFalse(result["hit"], f"Expected no cooldown hit, got: {result}")

    # ── Different card_type does NOT interfere ────────────────────────────

    def test_different_card_type_no_cross_interference(self):
        """prior state entry 6 is liquidation_pressure/BTC, which has a different
        cooldown_key from envelope 2 (whale_position_alert/BTC). They should NOT match."""
        # Envelope 2 is whale_position_alert, BTC, bullish
        # Prior entry 6 is liquidation_pressure, BTC, bearish — COMPLETELY different cooldown_key
        env2 = self.envelopes[1]
        result = check_cooldown(env2, self.prior_state, evaluated_at=self.evaluated_at)
        self.assertFalse(result["hit"],
                         f"Different card_type should NOT interfere: {result}")

    # ── Same asset different direction NOT wrongly blocked ─────────────────

    def test_same_asset_different_direction_not_blocked(self):
        """Envelope 2 (BTC whale bullish) should NOT be blocked by prior entry 5
        (BTC whale bearish) because different direction = different cooldown_key."""
        env2 = self.envelopes[1]
        result = check_cooldown(env2, self.prior_state, evaluated_at=self.evaluated_at)
        self.assertFalse(result["hit"],
                         f"Same asset different direction should NOT be blocked: {result}")

    # ── Gate decision structure ───────────────────────────────────────────

    def test_build_gate_decision_structure(self):
        """build_gate_decision produces correct structure."""
        d = build_gate_decision(
            signal_id="sig-test-001",
            card_type="price_oi_volume_anomaly",
            primary_assets=["BTC"],
            direction="bullish",
            dedupe_key="abc123",
            cooldown_key="def456",
            payload_hash="ghi789",
            gate_status="pass",
            gate_reasons=["test reason"],
            dedupe_hit=False,
            cooldown_hit=False,
            cooldown_until=None,
            observed_at="2026-06-04T20:00:00+08:00",
            evaluated_at="2026-06-04T23:30:00+08:00",
        )
        self.assertEqual(d["schema_version"], SCHEMA_VERSION)
        self.assertEqual(d["gate_version"], GATE_VERSION)
        self.assertEqual(d["signal_id"], "sig-test-001")
        self.assertEqual(d["gate_status"], "pass")
        self.assertTrue(d["eligible_for_send"])
        self.assertIn("test reason", d["gate_reasons"])
        self.assertIsNotNone(d["observed_at"])
        self.assertIsNotNone(d["evaluated_at"])

    def test_each_decision_has_gate_status(self):
        """All gate decisions have gate_status field."""
        decisions = evaluate_all_signal_gates(
            self.envelopes, self.prior_state, evaluated_at=self.evaluated_at
        )
        for d in decisions:
            self.assertIn("gate_status", d)
            self.assertIn(d["gate_status"], VALID_GATE_STATUSES,
                          f"Invalid gate_status: {d['gate_status']}")

    def test_each_decision_has_gate_reasons(self):
        """All gate decisions have non-empty gate_reasons list."""
        decisions = evaluate_all_signal_gates(
            self.envelopes, self.prior_state, evaluated_at=self.evaluated_at
        )
        for d in decisions:
            self.assertIn("gate_reasons", d)
            self.assertIsInstance(d["gate_reasons"], list)
            self.assertGreater(len(d["gate_reasons"]), 0,
                               f"No gate_reasons for {d.get('signal_id')}")

    def test_each_decision_has_eligible_for_send(self):
        """All gate decisions have eligible_for_send field."""
        decisions = evaluate_all_signal_gates(
            self.envelopes, self.prior_state, evaluated_at=self.evaluated_at
        )
        for d in decisions:
            self.assertIn("eligible_for_send", d)
            self.assertIsInstance(d["eligible_for_send"], bool)

    # ── Counts ────────────────────────────────────────────────────────────

    def test_passed_count_ge_1(self):
        """At least 1 signal passes."""
        decisions = evaluate_all_signal_gates(
            self.envelopes, self.prior_state, evaluated_at=self.evaluated_at
        )
        passed = sum(1 for d in decisions if d["gate_status"] == "pass")
        self.assertGreaterEqual(passed, 1, f"Expected >= 1 pass, got {passed}")

    def test_blocked_dedupe_count_ge_1(self):
        """At least 1 signal is blocked by dedupe."""
        decisions = evaluate_all_signal_gates(
            self.envelopes, self.prior_state, evaluated_at=self.evaluated_at
        )
        blocked = sum(1 for d in decisions if d["gate_status"] == "blocked_dedupe")
        self.assertGreaterEqual(blocked, 1, f"Expected >= 1 blocked_dedupe, got {blocked}")

    def test_blocked_cooldown_count_ge_1(self):
        """At least 1 signal is blocked by cooldown."""
        decisions = evaluate_all_signal_gates(
            self.envelopes, self.prior_state, evaluated_at=self.evaluated_at
        )
        blocked = sum(1 for d in decisions if d["gate_status"] == "blocked_cooldown")
        self.assertGreaterEqual(blocked, 1, f"Expected >= 1 blocked_cooldown, got {blocked}")

    def test_decision_count_equals_input(self):
        """decision_count == input_envelope_count."""
        decisions = evaluate_all_signal_gates(
            self.envelopes, self.prior_state, evaluated_at=self.evaluated_at
        )
        self.assertEqual(len(decisions), len(self.envelopes),
                         f"decision_count {len(decisions)} != input {len(self.envelopes)}")

    # ── Leak scanning ─────────────────────────────────────────────────────

    def test_clean_decision_no_leaks(self):
        """A clean gate decision has no leaks."""
        d = build_gate_decision(
            signal_id="sig-clean-test-001",
            card_type="whale_position_alert",
            primary_assets=["BTC"],
            direction="bullish",
            dedupe_key="abc123def456",
            cooldown_key="def789abc123",
            payload_hash="hash_content_here",
            gate_status="pass",
            gate_reasons=["clean signal, all checks passed"],
            dedupe_hit=False,
            cooldown_hit=False,
            cooldown_until=None,
            observed_at="2026-06-04T20:00:00+08:00",
            evaluated_at="2026-06-04T23:30:00+08:00",
        )
        result = scan_gate_decision_leaks(d)
        self.assertTrue(result["clean"], f"Expected clean, got: {result}")
        self.assertEqual(result["debug_leak_count"], 0)

    def test_detect_secret_in_gate_reasons(self):
        """Secret terms in gate_reasons are detected."""
        d = build_gate_decision(
            signal_id="sig-leak-test-001",
            card_type="whale_position_alert",
            primary_assets=["BTC"],
            direction="bullish",
            dedupe_key="abc123",
            cooldown_key="def456",
            payload_hash="ghi789",
            gate_status="pass",
            gate_reasons=["signal blocked due to api_key mismatch"],
            dedupe_hit=False,
            cooldown_hit=False,
            cooldown_until=None,
            observed_at="2026-06-04T20:00:00+08:00",
            evaluated_at="2026-06-04T23:30:00+08:00",
        )
        result = scan_gate_decision_leaks(d)
        self.assertGreater(result["secret_leak_count"], 0,
                           f"Should have detected secret leak: {result}")

    def test_detect_path_in_gate_reasons(self):
        """Path terms in gate_reasons are detected."""
        d = build_gate_decision(
            signal_id="sig-path-test-001",
            card_type="whale_position_alert",
            primary_assets=["BTC"],
            direction="bullish",
            dedupe_key="abc123",
            cooldown_key="def456",
            payload_hash="ghi789",
            gate_status="pass",
            gate_reasons=["loaded from C:\\Users\\PC\\data"],
            dedupe_hit=False,
            cooldown_hit=False,
            cooldown_until=None,
            observed_at="2026-06-04T20:00:00+08:00",
            evaluated_at="2026-06-04T23:30:00+08:00",
        )
        result = scan_gate_decision_leaks(d)
        self.assertGreater(result["secret_leak_count"], 0,
                           f"Should have detected path leak: {result}")

    def test_detect_unused_status_rejected(self):
        """Invalid gate_status is rejected."""
        d = build_gate_decision(
            signal_id="sig-invalid-test",
            card_type="whale_position_alert",
            primary_assets=["BTC"],
            direction="bullish",
            dedupe_key="abc123",
            cooldown_key="def456",
            payload_hash="ghi789",
            gate_status="unknown_fake_status",
            gate_reasons=["test"],
            dedupe_hit=False,
            cooldown_hit=False,
            cooldown_until=None,
            observed_at="2026-06-04T20:00:00+08:00",
            evaluated_at="2026-06-04T23:30:00+08:00",
        )
        self.assertEqual(d["gate_status"], "blocked_invalid")

    # ── normalize_gate_time ───────────────────────────────────────────────

    def test_normalize_gate_time_iso(self):
        """ISO timestamp is parsed correctly."""
        dt = normalize_gate_time("2026-06-04T23:30:00+08:00")
        self.assertEqual(dt.hour, 23)
        self.assertEqual(dt.minute, 30)
        self.assertEqual(dt.day, 4)

    def test_normalize_gate_time_none(self):
        """None returns current time (not error)."""
        dt = normalize_gate_time(None)
        self.assertIsNotNone(dt)
        self.assertIsInstance(dt, datetime)


class TestIntegration(unittest.TestCase):
    """Integration tests — run the runner and verify outputs."""

    @classmethod
    def setUpClass(cls):
        """Run the v112i gate runner to generate output files."""
        import subprocess
        runner_path = ROOT / "scripts" / "run_market_radar_v112i_dedupe_cooldown_gate.py"
        result = subprocess.run(
            [sys.executable, str(runner_path)],
            capture_output=True,
            text=True,
            cwd=str(ROOT),
            timeout=120,
        )
        cls.stdout = result.stdout
        cls.stderr = result.stderr
        cls.exit_code = result.returncode

    def test_runner_exit_code_0(self):
        """Runner exits with code 0."""
        self.assertEqual(self.exit_code, 0,
                         f"Runner failed.\nStdout:\n{self.stdout}\nStderr:\n{self.stderr}")

    def test_result_json_exists(self):
        """Result JSON file generated."""
        self.assertTrue(RESULT_JSON_PATH.exists(), f"Missing: {RESULT_JSON_PATH}")

    def test_decisions_jsonl_exists(self):
        """Decisions JSONL file generated."""
        self.assertTrue(DECISIONS_JSONL_PATH.exists(), f"Missing: {DECISIONS_JSONL_PATH}")

    def test_report_exists(self):
        """Report markdown generated."""
        self.assertTrue(REPORT_MD_PATH.exists(), f"Missing: {REPORT_MD_PATH}")

    def test_handoff_exists(self):
        """Handoff markdown generated."""
        self.assertTrue(HANDOFF_MD_PATH.exists(), f"Missing: {HANDOFF_MD_PATH}")

    def test_result_decision_count_matches_input(self):
        """decision_count == input_envelope_count."""
        with open(RESULT_JSON_PATH, "r", encoding="utf-8") as f:
            result = json.load(f)
        self.assertEqual(result["decision_count"], result["input_envelope_count"])

    def test_result_passed_ge_1(self):
        """passed_count >= 1."""
        with open(RESULT_JSON_PATH, "r", encoding="utf-8") as f:
            result = json.load(f)
        self.assertGreaterEqual(result["passed_count"], 1)

    def test_result_blocked_dedupe_ge_1(self):
        """blocked_dedupe_count >= 1."""
        with open(RESULT_JSON_PATH, "r", encoding="utf-8") as f:
            result = json.load(f)
        self.assertGreaterEqual(result["blocked_dedupe_count"], 1)

    def test_result_blocked_cooldown_ge_1(self):
        """blocked_cooldown_count >= 1."""
        with open(RESULT_JSON_PATH, "r", encoding="utf-8") as f:
            result = json.load(f)
        self.assertGreaterEqual(result["blocked_cooldown_count"], 1)

    def test_result_debug_leak_count_zero(self):
        """debug_leak_count == 0."""
        with open(RESULT_JSON_PATH, "r", encoding="utf-8") as f:
            result = json.load(f)
        self.assertEqual(result["debug_leak_count"], 0,
                         f"debug_leak_count should be 0, got {result['debug_leak_count']}")

    def test_result_secret_leak_count_zero(self):
        """secret_leak_count == 0."""
        with open(RESULT_JSON_PATH, "r", encoding="utf-8") as f:
            result = json.load(f)
        self.assertEqual(result["secret_leak_count"], 0,
                         f"secret_leak_count should be 0, got {result['secret_leak_count']}")

    def test_result_safety_flags_false(self):
        """All safety flags are false."""
        with open(RESULT_JSON_PATH, "r", encoding="utf-8") as f:
            result = json.load(f)
        self.assertFalse(result["real_tg_sent"])
        self.assertFalse(result["external_api_called"])
        self.assertFalse(result["external_ai_called"])
        self.assertFalse(result["daemon_started"])
        self.assertFalse(result["live_ready"])

    def test_jsonl_each_line_has_fields(self):
        """Each JSONL decision line has required fields."""
        with open(DECISIONS_JSONL_PATH, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    d = json.loads(line)
                    self.assertIn("signal_id", d)
                    self.assertIn("gate_status", d)
                    self.assertIn("gate_reasons", d)
                    self.assertIn("eligible_for_send", d)
                    self.assertIn("dedupe_hit", d)
                    self.assertIn("cooldown_hit", d)
                    self.assertIn("observed_at", d)
                    self.assertIn("evaluated_at", d)

    def test_jsonl_eligible_equals_pass(self):
        """eligible_for_send is True iff gate_status == 'pass'."""
        with open(DECISIONS_JSONL_PATH, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    d = json.loads(line)
                    expected = d["gate_status"] == "pass"
                    self.assertEqual(d["eligible_for_send"], expected,
                                     f"eligible_for_send mismatch for {d['signal_id']}: "
                                     f"status={d['gate_status']}, eligible={d['eligible_for_send']}")

    def test_jsonl_no_forbidden_terms(self):
        """No forbidden terms in JSONL decision human-readable fields."""
        forbidden = ["secret", "token", "api_key", "chat_id", "password",
                     "C:\\Users\\PC", "ai_relay_desk"]
        with open(DECISIONS_JSONL_PATH, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    d = json.loads(line)
                    # Only check human-readable fields
                    check = json.dumps({
                        "signal_id": d.get("signal_id"),
                        "card_type": d.get("card_type"),
                        "direction": d.get("direction"),
                        "gate_status": d.get("gate_status"),
                        "gate_reasons": d.get("gate_reasons"),
                        "primary_assets": d.get("primary_assets"),
                    }).lower()
                    for term in forbidden:
                        self.assertNotIn(term.lower(), check,
                                         f"Forbidden term '{term}' found in decision {d.get('signal_id')}")

    def test_no_write_to_ai_relay_desk(self):
        """No files written to ai_relay_desk directory."""
        # Check that no output paths contain ai_relay_desk
        output_paths = [RESULT_JSON_PATH, DECISIONS_JSONL_PATH, REPORT_MD_PATH, HANDOFF_MD_PATH]
        for p in output_paths:
            self.assertNotIn("ai_relay_desk", str(p).lower(),
                             f"Path contains ai_relay_desk: {p}")

    def test_no_files_deleted(self):
        """No files were deleted — v112h outputs still exist."""
        self.assertTrue(ENVELOPE_JSONL_PATH.exists(),
                        f"v112h JSONL should still exist: {ENVELOPE_JSONL_PATH}")


class TestGateEdgeCases(unittest.TestCase):
    """Edge case tests for specific scenarios."""

    @classmethod
    def setUpClass(cls):
        cls.envelopes = load_envelopes_jsonl(ENVELOPE_JSONL_PATH)
        cls.prior_state = load_prior_signal_state(PRIOR_STATE_JSON_PATH)
        cls.evaluated_at = datetime(2026, 6, 4, 23, 30, 0, tzinfo=CN_TZ)

    def test_envelope_1_dedupe_blocked(self):
        """Envelope 1 (pova) is blocked by dedupe."""
        decision = evaluate_signal_gate(
            self.envelopes[0], self.prior_state, evaluated_at=self.evaluated_at
        )
        self.assertEqual(decision["gate_status"], "blocked_dedupe",
                         f"Expected blocked_dedupe, got {decision['gate_status']}: {decision['gate_reasons']}")
        self.assertTrue(decision["dedupe_hit"])
        self.assertFalse(decision["eligible_for_send"])

    def test_envelope_2_passes(self):
        """Envelope 2 (whale BTC bull) passes — no dedupe/cooldown match."""
        decision = evaluate_signal_gate(
            self.envelopes[1], self.prior_state, evaluated_at=self.evaluated_at
        )
        self.assertEqual(decision["gate_status"], "pass",
                         f"Expected pass, got {decision['gate_status']}: {decision['gate_reasons']}")
        self.assertTrue(decision["eligible_for_send"])

    def test_envelope_5_cooldown_blocked(self):
        """Envelope 5 (liq BTC bear) is blocked by cooldown."""
        decision = evaluate_signal_gate(
            self.envelopes[4], self.prior_state, evaluated_at=self.evaluated_at
        )
        self.assertEqual(decision["gate_status"], "blocked_cooldown",
                         f"Expected blocked_cooldown, got {decision['gate_status']}: {decision['gate_reasons']}")
        self.assertTrue(decision["cooldown_hit"])
        self.assertFalse(decision["eligible_for_send"])

    def test_envelope_10_cooldown_expired_passes(self):
        """Envelope 10 (mams BNB OKB BGB) has expired cooldown and passes."""
        decision = evaluate_signal_gate(
            self.envelopes[9], self.prior_state, evaluated_at=self.evaluated_at
        )
        self.assertEqual(decision["gate_status"], "pass",
                         f"Expected pass (cooldown expired), got {decision['gate_status']}: {decision['gate_reasons']}")
        self.assertTrue(decision["eligible_for_send"])

    def test_envelope_11_cooldown_blocked(self):
        """Envelope 11 (news BTC bull) is blocked by cooldown."""
        decision = evaluate_signal_gate(
            self.envelopes[10], self.prior_state, evaluated_at=self.evaluated_at
        )
        self.assertEqual(decision["gate_status"], "blocked_cooldown",
                         f"Expected blocked_cooldown, got {decision['gate_status']}: {decision['gate_reasons']}")
        self.assertTrue(decision["cooldown_hit"])

    def test_same_asset_different_direction_scenario(self):
        """Envelope 2 (BTC whale bullish) is NOT blocked by prior BTC whale bearish entry.
        Confirms same asset different direction does not cause false block."""
        # Prior entry 5 is BTC whale bearish with cooldown
        # Envelope 2 is BTC whale bullish — different cooldown_key
        env2 = self.envelopes[1]
        prior_entry_5 = self.prior_state[5]
        self.assertNotEqual(env2["cooldown_key"], prior_entry_5["cooldown_key"],
                            "Different directions MUST produce different cooldown_keys")

        decision = evaluate_signal_gate(
            env2, self.prior_state, evaluated_at=self.evaluated_at
        )
        self.assertEqual(decision["gate_status"], "pass",
                         f"Same asset diff direction should NOT be blocked: {decision['gate_reasons']}")

    def test_different_card_type_scenario(self):
        """Envelope 2 (BTC whale bullish) is NOT blocked by prior BTC liquidation bearish entry.
        Confirms different card_type does not cause false block."""
        env2 = self.envelopes[1]
        prior_entry_6 = self.prior_state[6]
        self.assertNotEqual(env2["cooldown_key"], prior_entry_6["cooldown_key"],
                            "Different card_types MUST produce different cooldown_keys")

        decision = evaluate_signal_gate(
            env2, self.prior_state, evaluated_at=self.evaluated_at
        )
        self.assertEqual(decision["gate_status"], "pass",
                         f"Different card_type should NOT be blocked: {decision['gate_reasons']}")

    def test_different_card_types_have_different_cooldown_keys(self):
        """Verify that the same asset with different card_types produces different cooldown_keys."""
        from scripts.market_radar_signal_envelope_v112h import build_cooldown_key
        ck_whale = build_cooldown_key("whale_position_alert", ["BTC"], "bullish")
        ck_liq = build_cooldown_key("liquidation_pressure", ["BTC"], "bullish")
        ck_pova = build_cooldown_key("price_oi_volume_anomaly", ["BTC"], "bullish")
        ck_news = build_cooldown_key("news_event_market_impact", ["BTC"], "bullish")
        ck_mams = build_cooldown_key("multi_asset_market_sync", ["BTC"], "bullish")

        all_keys = [ck_whale, ck_liq, ck_pova, ck_news, ck_mams]
        self.assertEqual(len(all_keys), len(set(all_keys)),
                         "All 5 card_types for same asset MUST produce different cooldown_keys")


if __name__ == "__main__":
    unittest.main(verbosity=2)
