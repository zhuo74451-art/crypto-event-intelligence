"""Test suite for Market Radar v1.12-H Unified Signal Envelope.

Covers:
  - 5 card types all produce envelopes
  - envelope count >= 13
  - Each envelope has signal_id, dedupe_key, cooldown_key, payload_hash
  - Re-running same input produces stable payload_hash, dedupe_key
  - cooldown_key does not contain volatile fields
  - severity/confidence score ranges valid
  - direction/card_type enum valid
  - public_card not empty
  - debug_leak_count=0, secret_leak_count=0
  - real_tg_sent=false, external_api_called=false, external_ai_called=false,
    daemon_started=false, live_ready=false
  - No full wallet addresses in public output
  - No forbidden path terms
  - Result JSON and JSONL successfully generated

Usage:
    python scripts/test_market_radar_signal_envelope_v112h.py
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

from scripts.market_radar_signal_envelope_v112h import (
    build_signal_envelope,
    build_dedupe_key,
    build_cooldown_key,
    build_payload_hash,
    validate_signal_envelope,
    scan_envelope_leaks,
    VALID_CARD_TYPES,
    VALID_DIRECTIONS,
    build_envelope_from_position_result,
    build_envelope_from_sync_result,
    build_envelope_from_liquidation_record,
    build_envelope_from_news_signal,
    build_envelope_from_pova_sample,
)


class TestSignalEnvelope(unittest.TestCase):
    """Core unit tests for signal envelope functions."""

    def _make_envelope(self, **overrides) -> dict:
        """Build a minimal valid envelope for testing."""
        defaults = {
            "card_type": "price_oi_volume_anomaly",
            "adapter_version": "v1.12-A",
            "source_kind": "fixture",
            "observed_at": "2026-06-04T20:00:00+08:00",
            "primary_assets": ["BTC"],
            "direction": "bullish",
            "severity_score": 50.0,
            "confidence_score": 0.8,
            "event_key": "test_pova_001",
            "public_card": "Test public card content.",
            "safety_flags": None,
            "metadata": {"test": True},
        }
        defaults.update(overrides)
        return build_signal_envelope(**defaults)

    # ── Basic envelope structure ────────────────────────────────────────────

    def test_can_build_envelope(self):
        """All 5 card types can generate an envelope."""
        for ct in VALID_CARD_TYPES:
            env = self._make_envelope(card_type=ct, event_key=f"test_{ct}_001")
            self.assertEqual(env["card_type"], ct)
            self.assertIsNotNone(env["signal_id"])
            self.assertTrue(len(env["signal_id"]) > 0)

    def test_signal_id_present(self):
        """Each envelope has a non-empty signal_id."""
        env = self._make_envelope()
        self.assertTrue(len(env["signal_id"]) > 0)
        self.assertTrue(env["signal_id"].startswith("sig-"))

    def test_dedupe_key_present(self):
        """Each envelope has a non-empty dedupe_key."""
        env = self._make_envelope()
        self.assertTrue(len(env["dedupe_key"]) > 0)
        self.assertEqual(len(env["dedupe_key"]), 64)  # SHA-256 hex

    def test_cooldown_key_present(self):
        """Each envelope has a non-empty cooldown_key."""
        env = self._make_envelope()
        self.assertTrue(len(env["cooldown_key"]) > 0)
        self.assertEqual(len(env["cooldown_key"]), 64)

    def test_payload_hash_present(self):
        """Each envelope has a non-empty payload_hash."""
        env = self._make_envelope()
        self.assertTrue(len(env["payload_hash"]) > 0)
        self.assertEqual(len(env["payload_hash"]), 64)

    # ── Key/Hash stability ─────────────────────────────────────────────────

    def test_dedupe_key_stable(self):
        """Same input produces the same dedupe_key."""
        dk1 = build_dedupe_key("whale_position_alert", "evt_001", ["BTC"], "2026-06-04T20:00:00+08:00")
        dk2 = build_dedupe_key("whale_position_alert", "evt_001", ["BTC"], "2026-06-04T20:00:00+08:00")
        self.assertEqual(dk1, dk2)

    def test_dedupe_key_different_event(self):
        """Different event_key produces different dedupe_key."""
        dk1 = build_dedupe_key("whale_position_alert", "evt_001", ["BTC"], "2026-06-04T20:00:00+08:00")
        dk2 = build_dedupe_key("whale_position_alert", "evt_002", ["BTC"], "2026-06-04T20:00:00+08:00")
        self.assertNotEqual(dk1, dk2)

    def test_dedupe_key_minute_normalization(self):
        """dedupe_key normalizes to minute granularity."""
        # Same minute should produce same key
        dk1 = build_dedupe_key("whale_position_alert", "evt_001", ["BTC"], "2026-06-04T20:00:15+08:00")
        dk2 = build_dedupe_key("whale_position_alert", "evt_001", ["BTC"], "2026-06-04T20:00:45+08:00")
        self.assertEqual(dk1, dk2)

    def test_payload_hash_stable(self):
        """Same input produces the same payload_hash."""
        card = "Test public card content."
        ph1 = build_payload_hash(card, "price_oi_volume_anomaly", ["BTC"], "bullish")
        ph2 = build_payload_hash(card, "price_oi_volume_anomaly", ["BTC"], "bullish")
        self.assertEqual(ph1, ph2)

    def test_payload_hash_different_card(self):
        """Different public_card produces different payload_hash."""
        ph1 = build_payload_hash("Card A", "price_oi_volume_anomaly", ["BTC"], "bullish")
        ph2 = build_payload_hash("Card B", "price_oi_volume_anomaly", ["BTC"], "bullish")
        self.assertNotEqual(ph1, ph2)

    def test_cooldown_key_stable(self):
        """Same input produces the same cooldown_key."""
        ck1 = build_cooldown_key("whale_position_alert", ["BTC", "ETH"], "bullish")
        ck2 = build_cooldown_key("whale_position_alert", ["BTC", "ETH"], "bullish")
        self.assertEqual(ck1, ck2)

    def test_cooldown_key_asset_order_independent(self):
        """cooldown_key is independent of asset order (sorted)."""
        ck1 = build_cooldown_key("whale_position_alert", ["ETH", "BTC"], "bullish")
        ck2 = build_cooldown_key("whale_position_alert", ["BTC", "ETH"], "bullish")
        self.assertEqual(ck1, ck2)

    def test_cooldown_key_no_volatile_fields(self):
        """cooldown_key does not contain volatile timestamp fields."""
        ck1 = build_cooldown_key("whale_position_alert", ["BTC"], "bullish")
        ck2 = build_cooldown_key("whale_position_alert", ["BTC"], "bullish")
        # Should be identical regardless of when called
        self.assertEqual(ck1, ck2)

    def test_cooldown_key_different_direction(self):
        """Different direction produces different cooldown_key."""
        ck1 = build_cooldown_key("whale_position_alert", ["BTC"], "bullish")
        ck2 = build_cooldown_key("whale_position_alert", ["BTC"], "bearish")
        self.assertNotEqual(ck1, ck2)

    # ── Score range validation ──────────────────────────────────────────────

    def test_severity_score_range(self):
        """severity_score is in [0, 100]."""
        env = self._make_envelope(severity_score=50.0)
        self.assertTrue(0 <= env["severity_score"] <= 100)

        env2 = self._make_envelope(severity_score=0.0)
        self.assertTrue(0 <= env2["severity_score"] <= 100)

        env3 = self._make_envelope(severity_score=100.0)
        self.assertTrue(0 <= env3["severity_score"] <= 100)

    def test_severity_score_clamped(self):
        """severity_score is clamped to [0, 100]."""
        env = self._make_envelope(severity_score=150.0)
        self.assertEqual(env["severity_score"], 100.0)

        env2 = self._make_envelope(severity_score=-10.0)
        self.assertEqual(env2["severity_score"], 0.0)

    def test_confidence_score_range(self):
        """confidence_score is in [0, 1]."""
        env = self._make_envelope(confidence_score=0.85)
        self.assertTrue(0 <= env["confidence_score"] <= 1)

        env2 = self._make_envelope(confidence_score=0.0)
        self.assertTrue(0 <= env2["confidence_score"] <= 1)

        env3 = self._make_envelope(confidence_score=1.0)
        self.assertTrue(0 <= env3["confidence_score"] <= 1)

    def test_confidence_score_clamped(self):
        """confidence_score is clamped to [0, 1]."""
        env = self._make_envelope(confidence_score=2.5)
        self.assertEqual(env["confidence_score"], 1.0)

        env2 = self._make_envelope(confidence_score=-0.5)
        self.assertEqual(env2["confidence_score"], 0.0)

    # ── Enum validation ────────────────────────────────────────────────────

    def test_direction_enum_valid(self):
        """direction is one of the valid values."""
        for d in VALID_DIRECTIONS:
            env = self._make_envelope(direction=d)
            self.assertEqual(env["direction"], d)
            self.assertIn(env["direction"], VALID_DIRECTIONS)

    def test_invalid_direction_raises(self):
        """Invalid direction raises ValueError."""
        with self.assertRaises(ValueError):
            self._make_envelope(direction="invalid_direction")

    def test_card_type_enum_valid(self):
        """card_type is one of VALID_CARD_TYPES."""
        for ct in VALID_CARD_TYPES:
            env = self._make_envelope(card_type=ct)
            self.assertIn(env["card_type"], VALID_CARD_TYPES)

    def test_invalid_card_type_raises(self):
        """Invalid card_type raises ValueError."""
        with self.assertRaises(ValueError):
            self._make_envelope(card_type="unknown_card_type")

    # ── public_card validation ─────────────────────────────────────────────

    def test_public_card_not_empty(self):
        """public_card is not empty for all envelopes."""
        for ct in VALID_CARD_TYPES:
            env = self._make_envelope(card_type=ct, public_card=f"Test card for {ct}")
            self.assertTrue(len(env["public_card"]) > 0, f"public_card empty for {ct}")

    # ── Safety flags ───────────────────────────────────────────────────────

    def test_safety_flags_defaults(self):
        """Default safety flags are all false/zero."""
        env = self._make_envelope()
        sf = env["safety_flags"]
        self.assertFalse(sf["real_tg_sent"])
        self.assertFalse(sf["external_api_called"])
        self.assertFalse(sf["external_ai_called"])
        self.assertFalse(sf["daemon_started"])
        self.assertFalse(sf["live_ready"])

    def test_live_ready_is_false(self):
        """live_ready is False for all fixture envelopes."""
        for ct in VALID_CARD_TYPES:
            env = self._make_envelope(card_type=ct)
            self.assertFalse(env["live_ready"], f"live_ready should be false for {ct}")

    # ── Leak scanning ─────────────────────────────────────────────────────

    def test_no_debug_leak(self):
        """Envelopes should not contain debug terms."""
        env = self._make_envelope(public_card="Clean public market observation.")
        result = scan_envelope_leaks(env)
        self.assertEqual(result["debug_leak_count"], 0, f"Debug leaks found: {result['debug_terms_found']}")

    def test_detects_debug_leak(self):
        """scan_envelope_leaks detects debug terms in public_card."""
        env = self._make_envelope(public_card="This has debug info in it.")
        result = scan_envelope_leaks(env)
        self.assertGreater(result["debug_leak_count"], 0)

    def test_detects_secret_leak(self):
        """scan_envelope_leaks detects secret/key terms in public_card."""
        env = self._make_envelope(public_card="This contains an api_key reference.")
        result = scan_envelope_leaks(env)
        self.assertGreater(result["secret_leak_count"], 0)

    def test_detects_path_leak(self):
        """scan_envelope_leaks detects local path terms."""
        env = self._make_envelope(public_card="File at C:\\Users\\PC\\data.")
        result = scan_envelope_leaks(env)
        self.assertGreater(result["secret_leak_count"], 0)

    def test_detects_wallet_leak(self):
        """scan_envelope_leaks detects full 0x wallet addresses."""
        env = self._make_envelope(public_card="Wallet: 0x082d2ca88b5e0e6c1e8c0b5e2d3f4a5b6c7d8e9f")
        result = scan_envelope_leaks(env)
        self.assertTrue(result["full_wallet_leak"])

    def test_clean_envelope(self):
        """A clean envelope passes leak scan."""
        env = self._make_envelope(
            public_card=(
                "📈 Market observation for BTC.\n\n"
                "BTC price moved +5% in 24h, OI up 12%.\n\n"
                "⚠️ Not trading advice."
            )
        )
        result = scan_envelope_leaks(env)
        self.assertTrue(result["clean"], f"Expected clean, got: {result}")

    # ── Validation ─────────────────────────────────────────────────────────

    def test_valid_envelope_passes_validation(self):
        """A well-formed envelope passes validate_signal_envelope."""
        env = self._make_envelope()
        result = validate_signal_envelope(env)
        self.assertTrue(result["valid"], f"Validation errors: {result['errors']}")

    def test_missing_field_fails_validation(self):
        """Missing required field fails validation."""
        env = self._make_envelope()
        del env["signal_id"]
        result = validate_signal_envelope(env)
        self.assertFalse(result["valid"])
        self.assertTrue(any("signal_id" in e for e in result["errors"]))

    def test_invalid_severity_fails_validation(self):
        """Out-of-range severity fails validation."""
        # Build an envelope directly and override severity to test validation
        env = self._make_envelope()
        env["severity_score"] = 999.0
        result = validate_signal_envelope(env)
        self.assertFalse(result["valid"])

    def test_empty_public_card_fails_validation(self):
        """Empty public_card fails validation."""
        env = self._make_envelope(public_card="")
        result = validate_signal_envelope(env)
        self.assertFalse(result["valid"])

    # ── Adapter-to-envelope converters ────────────────────────────────────

    def test_build_from_position_result(self):
        """Can build envelope from v112f position result."""
        pr = {
            "event_id": "whale_v112f_test",
            "observed_at": "2026-06-04T19:45:00+08:00",
            "asset": "BTC",
            "side": "long",
            "wallet_short": "0x7a9f...6b8c",
            "label": "Smart Money",
            "entity_type": "smart_money",
            "label_confidence": "high",
            "position_size_usd": 5_200_000,
            "leverage": 5.0,
            "public_card": "Whale alert test card.",
            "valid": True,
            "blocked": False,
            "debug_leak_count": 0,
            "secret_leak_count": 0,
            "real_tg_sent": False,
            "external_api_called": False,
            "external_ai_called": False,
            "daemon_started": False,
            "live_ready": False,
        }
        env = build_envelope_from_position_result(pr)
        self.assertEqual(env["card_type"], "whale_position_alert")
        self.assertEqual(env["primary_assets"], ["BTC"])
        self.assertFalse(env["safety_flags"]["real_tg_sent"])

    def test_build_from_sync_result(self):
        """Can build envelope from v112g sync result."""
        sr = {
            "event_id": "sync_v112g_test",
            "observed_at": "2026-06-04T14:30:00+08:00",
            "primary_assets": ["BTC", "ETH", "SOL"],
            "direction": "up",
            "sync_score": 91.6,
            "direction_agreement": 1.0,
            "asset_count": 3,
            "public_card": "Multi-asset sync test card.",
            "valid": True,
            "blocked": False,
            "debug_leak_count": 0,
            "secret_leak_count": 0,
            "real_tg_sent": False,
            "external_api_called": False,
            "external_ai_called": False,
            "daemon_started": False,
            "live_ready": False,
        }
        env = build_envelope_from_sync_result(sr)
        self.assertEqual(env["card_type"], "multi_asset_market_sync")
        self.assertEqual(env["direction"], "bullish")  # up -> bullish

    def test_build_from_liquidation_record(self):
        """Can build envelope from v112c liquidation record."""
        lr = {
            "signal_id": "liq_test_001",
            "asset": "ETH",
            "observed_at": "2026-06-04T18:00:00+08:00",
            "signal": {
                "pressure_type": "short_liquidation_pressure",
                "long_liquidation_usd_1h": 5_000_000,
                "short_liquidation_usd_1h": 25_000_000,
                "cluster_above_total_usd": 10_000_000,
                "cluster_below_total_usd": 0,
                "trigger_description": "ETH short liquidation pressure alert.",
            },
            "public_card": "Liquidation test card.",
            "real_tg_sent": False,
            "external_api_called": False,
            "daemon_started": False,
            "live_ready": False,
        }
        env = build_envelope_from_liquidation_record(lr)
        self.assertEqual(env["card_type"], "liquidation_pressure")
        self.assertEqual(env["direction"], "bullish")  # short pressure -> bullish (price up)

    def test_build_from_news_signal(self):
        """Can build envelope from v112d news signal."""
        ns = {
            "sample_id": "news_test_001",
            "affected_assets": ["BTC", "ETH"],
            "impact_direction": "bullish",
            "category": "etf_flow",
            "trading_relevance": "高",
            "public_card": "News event test card.",
            "real_tg_sent": False,
            "external_api_called": False,
            "external_ai_called": False,
            "daemon_started": False,
            "live_ready": False,
        }
        env = build_envelope_from_news_signal(ns)
        self.assertEqual(env["card_type"], "news_event_market_impact")
        self.assertEqual(env["direction"], "bullish")

    def test_build_from_pova_sample(self):
        """Can build envelope from v112e POVA sample."""
        sample = {
            "sample_id": "pova_test_001",
            "asset": "BTC",
            "price_change_pct": 7.2,
            "open_interest": 28_500_000_000,
            "volume": 45_000_000_000,
            "public_preview": "POVA test card.",
        }
        env = build_envelope_from_pova_sample(sample)
        self.assertEqual(env["card_type"], "price_oi_volume_anomaly")
        self.assertEqual(env["primary_assets"], ["BTC"])
        self.assertEqual(env["direction"], "bullish")  # positive price change


class TestIntegration(unittest.TestCase):
    """Integration tests — run the runner and verify outputs."""

    @classmethod
    def setUpClass(cls):
        """Run the v112h runner to generate output files."""
        import subprocess
        runner_path = ROOT / "scripts" / "run_market_radar_v112h_unified_signal_envelope.py"
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
        cls.result_json_path = ROOT / "results" / "market_radar_v112h_unified_signal_envelope_result.json"
        cls.jsonl_path = ROOT / "results" / "market_radar_v112h_unified_signal_envelopes.jsonl"
        cls.report_path = ROOT / "runs" / "market_radar" / "v112h_unified_signal_envelope.md"
        cls.handoff_path = ROOT / "runs" / "market_radar" / "v112h_unified_signal_envelope_handoff.md"

    def test_runner_exit_code_0(self):
        """Runner exits with code 0."""
        self.assertEqual(self.exit_code, 0, f"Runner failed.\nStdout:\n{self.stdout}\nStderr:\n{self.stderr}")

    def test_result_json_exists(self):
        """Result JSON file generated."""
        self.assertTrue(self.result_json_path.exists(), f"Missing: {self.result_json_path}")

    def test_jsonl_exists(self):
        """JSONL file generated."""
        self.assertTrue(self.jsonl_path.exists(), f"Missing: {self.jsonl_path}")

    def test_report_exists(self):
        """Report markdown generated."""
        self.assertTrue(self.report_path.exists(), f"Missing: {self.report_path}")

    def test_handoff_exists(self):
        """Handoff markdown generated."""
        self.assertTrue(self.handoff_path.exists(), f"Missing: {self.handoff_path}")

    def test_total_envelopes_ge_13(self):
        """Total envelopes >= 13."""
        with open(self.result_json_path, "r", encoding="utf-8") as f:
            result = json.load(f)
        self.assertGreaterEqual(result["total_envelopes"], 13)

    def test_all_5_card_types_present(self):
        """All 5 card types are present."""
        with open(self.result_json_path, "r", encoding="utf-8") as f:
            result = json.load(f)
        self.assertTrue(result["all_card_types_present"])

    def test_all_envelopes_valid(self):
        """All envelopes pass validation."""
        with open(self.result_json_path, "r", encoding="utf-8") as f:
            result = json.load(f)
        self.assertTrue(result["all_envelopes_valid"], f"Some envelopes invalid")

    def test_debug_leak_count_zero(self):
        """debug_leak_count is 0 in overall result."""
        with open(self.result_json_path, "r", encoding="utf-8") as f:
            result = json.load(f)
        self.assertEqual(result["debug_leak_count"], 0)

    def test_secret_leak_count_zero(self):
        """secret_leak_count is 0 in overall result."""
        with open(self.result_json_path, "r", encoding="utf-8") as f:
            result = json.load(f)
        self.assertEqual(result["secret_leak_count"], 0)

    def test_jsonl_line_count(self):
        """JSONL has correct line count."""
        with open(self.jsonl_path, "r", encoding="utf-8") as f:
            lines = [l for l in f if l.strip()]
        self.assertGreaterEqual(len(lines), 13)

    def test_each_jsonl_line_has_signal_id(self):
        """Every JSONL line has signal_id."""
        with open(self.jsonl_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    env = json.loads(line)
                    self.assertTrue(len(env.get("signal_id", "")) > 0)

    def test_each_jsonl_line_has_keys(self):
        """Every JSONL line has dedupe_key, cooldown_key, payload_hash."""
        with open(self.jsonl_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    env = json.loads(line)
                    self.assertTrue(len(env.get("dedupe_key", "")) > 0)
                    self.assertTrue(len(env.get("cooldown_key", "")) > 0)
                    self.assertTrue(len(env.get("payload_hash", "")) > 0)

    def test_each_jsonl_safety_flags_correct(self):
        """Every JSONL envelope has correct safety flags."""
        with open(self.jsonl_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    env = json.loads(line)
                    sf = env.get("safety_flags", {})
                    self.assertFalse(sf.get("real_tg_sent", True), f"real_tg_sent should be false: {env.get('signal_id')}")
                    self.assertFalse(sf.get("external_api_called", True))
                    self.assertFalse(sf.get("external_ai_called", True))
                    self.assertFalse(sf.get("daemon_started", True))
                    self.assertFalse(sf.get("live_ready", True), f"live_ready should be false: {env.get('signal_id')}")

    def test_hash_stability(self):
        """Key/hash stability confirmed in result."""
        with open(self.result_json_path, "r", encoding="utf-8") as f:
            result = json.load(f)
        self.assertTrue(result["dedupe_key_stable"])
        self.assertTrue(result["cooldown_key_stable"])
        self.assertTrue(result["payload_hash_stable"])

    def test_cardinality(self):
        """Cardinality checks pass."""
        with open(self.result_json_path, "r", encoding="utf-8") as f:
            result = json.load(f)
        self.assertGreaterEqual(result["cardinality"]["price_oi_volume_anomaly"]["actual"], 1)
        self.assertGreaterEqual(result["cardinality"]["whale_position_alert"]["actual"], 3)
        self.assertGreaterEqual(result["cardinality"]["liquidation_pressure"]["actual"], 3)
        self.assertGreaterEqual(result["cardinality"]["multi_asset_market_sync"]["actual"], 3)
        self.assertGreaterEqual(result["cardinality"]["news_event_market_impact"]["actual"], 3)

    def test_no_wallet_leak_in_jsonl(self):
        """No full wallet address in any JSONL public_card."""
        import re
        wallet_pat = re.compile(r'0x[a-fA-F0-9]{40}')
        with open(self.jsonl_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    env = json.loads(line)
                    pc = env.get("public_card", "")
                    matches = wallet_pat.findall(pc)
                    self.assertEqual(len(matches), 0, f"Wallet leak in {env.get('signal_id')}: {matches}")

    def test_no_forbidden_path_in_jsonl(self):
        """No local path terms in any JSONL public_card."""
        forbidden_paths = ["C:\\Users\\PC", "ai_relay_desk"]
        with open(self.jsonl_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    env = json.loads(line)
                    pc = env.get("public_card", "").lower()
                    for fp in forbidden_paths:
                        self.assertNotIn(fp.lower(), pc, f"Forbidden path '{fp}' in {env.get('signal_id')}")


class TestCoverageEnvelopeCounts(unittest.TestCase):
    """Test that each card type produces the required minimum count."""

    @classmethod
    def setUpClass(cls):
        jsonl_path = ROOT / "results" / "market_radar_v112h_unified_signal_envelopes.jsonl"
        cls.envelopes = []
        if jsonl_path.exists():
            with open(jsonl_path, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        cls.envelopes.append(json.loads(line))

    def test_price_oi_volume_anomaly_count(self):
        count = sum(1 for e in self.envelopes if e["card_type"] == "price_oi_volume_anomaly")
        self.assertGreaterEqual(count, 1, f"Expected >= 1, got {count}")

    def test_whale_position_alert_count(self):
        count = sum(1 for e in self.envelopes if e["card_type"] == "whale_position_alert")
        self.assertGreaterEqual(count, 3, f"Expected >= 3, got {count}")

    def test_liquidation_pressure_count(self):
        count = sum(1 for e in self.envelopes if e["card_type"] == "liquidation_pressure")
        self.assertGreaterEqual(count, 3, f"Expected >= 3, got {count}")

    def test_multi_asset_market_sync_count(self):
        count = sum(1 for e in self.envelopes if e["card_type"] == "multi_asset_market_sync")
        self.assertGreaterEqual(count, 3, f"Expected >= 3, got {count}")

    def test_news_event_market_impact_count(self):
        count = sum(1 for e in self.envelopes if e["card_type"] == "news_event_market_impact")
        self.assertGreaterEqual(count, 3, f"Expected >= 3, got {count}")

    def test_total_count(self):
        self.assertGreaterEqual(len(self.envelopes), 13, f"Expected >= 13, got {len(self.envelopes)}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
