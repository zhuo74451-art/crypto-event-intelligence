"""Test suite for Market Radar v1.12-Z — Degraded Whale Envelope Compatibility.

Covers:
  - Result JSON exists and has correct fields
  - Envelopes JSONL exists
  - Markdown report exists
  - Handoff markdown exists
  - Input records count > 0
  - Envelopes count equals input records count
  - external_api_called=false
  - degraded_compatible=true
  - mock_replay_only=true
  - eligible_for_real_send_count=0
  - real_send_candidate_count=0
  - preview_allowed_count=0
  - tg_send_allowed_count=0
  - prod_state_write=false
  - daemon_started=false
  - watcher_started=false
  - credentials_read=false
  - files_deleted=false
  - All envelopes have label_confidence
  - All envelopes have label_explanation
  - All null liquidation_price have note
  - All envelopes preserve delta_status
  - All envelopes preserve timestamp_status
  - All envelopes preserve quality_flags
  - All envelopes eligible_for_real_send=false
  - All envelopes real_send_candidate=false
  - No degraded envelope enters TG send path
  - No degraded envelope disguised as live passed

Usage:
    python scripts/test_market_radar_v112z_degraded_whale_envelope_compatibility.py
"""

from __future__ import annotations

import io
import json
import sys
import unittest
from pathlib import Path

# Fix Windows GBK encoding
if sys.stdout.encoding != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


class TestV112ZRunner(unittest.TestCase):
    """Test the v112Z runner produces correct output files."""

    @classmethod
    def setUpClass(cls):
        """Run the v112Z runner to generate output files."""
        import subprocess
        runner_path = ROOT / "scripts" / "run_market_radar_v112z_degraded_whale_envelope_compatibility.py"
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
        cls.result_json_path = ROOT / "results" / "market_radar_v112z_degraded_whale_envelope_compatibility_result.json"
        cls.jsonl_path = ROOT / "results" / "market_radar_v112z_degraded_whale_envelopes.jsonl"
        cls.report_path = ROOT / "runs" / "market_radar" / "v112z_degraded_whale_envelope_compatibility.md"
        cls.handoff_path = ROOT / "runs" / "market_radar" / "v112z_degraded_whale_envelope_compatibility_handoff.md"

        # Load result
        if cls.result_json_path.exists():
            with open(cls.result_json_path, "r", encoding="utf-8") as f:
                cls.result = json.load(f)
        else:
            cls.result = {}

        # Load envelopes
        cls.envelopes = []
        if cls.jsonl_path.exists():
            with open(cls.jsonl_path, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        cls.envelopes.append(json.loads(line))

    # ── File existence tests ──────────────────────────────────────────────────

    def test_runner_exit_code_0(self):
        """v112Z runner exits with code 0."""
        self.assertEqual(self.exit_code, 0,
                         f"Runner failed.\nStdout:\n{self.stdout}\nStderr:\n{self.stderr}")

    def test_result_json_exists(self):
        """Result JSON file exists."""
        self.assertTrue(self.result_json_path.exists(),
                        f"Missing: {self.result_json_path}")

    def test_envelopes_jsonl_exists(self):
        """Envelopes JSONL file exists."""
        self.assertTrue(self.jsonl_path.exists(),
                        f"Missing: {self.jsonl_path}")

    def test_report_md_exists(self):
        """Markdown report exists."""
        self.assertTrue(self.report_path.exists(),
                        f"Missing: {self.report_path}")

    def test_handoff_md_exists(self):
        """Handoff markdown exists."""
        self.assertTrue(self.handoff_path.exists(),
                        f"Missing: {self.handoff_path}")

    # ── Result JSON field tests ───────────────────────────────────────────────

    def test_input_records_gt_0(self):
        """Input records count > 0."""
        self.assertGreater(self.result.get("input_records_loaded", 0), 0)

    def test_envelopes_equal_input_records(self):
        """Envelopes count equals input records count."""
        self.assertEqual(
            self.result.get("envelopes_written", 0),
            self.result.get("input_records_loaded", 0),
            "Envelope count should equal input record count"
        )

    def test_external_api_called_false(self):
        """external_api_called is false."""
        self.assertFalse(self.result.get("external_api_called"))

    def test_degraded_compatible_true(self):
        """degraded_compatible is true."""
        self.assertTrue(self.result.get("degraded_compatible"))

    def test_mock_replay_only_true(self):
        """mock_replay_only is true."""
        self.assertTrue(self.result.get("mock_replay_only"))

    def test_eligible_for_real_send_count_zero(self):
        """eligible_for_real_send_count is 0."""
        self.assertEqual(self.result.get("eligible_for_real_send_count"), 0)

    def test_real_send_candidate_count_zero(self):
        """real_send_candidate_count is 0."""
        self.assertEqual(self.result.get("real_send_candidate_count"), 0)

    def test_preview_allowed_count_zero(self):
        """preview_allowed_count is 0."""
        self.assertEqual(self.result.get("preview_allowed_count"), 0)

    def test_tg_send_allowed_count_zero(self):
        """tg_send_allowed_count is 0."""
        self.assertEqual(self.result.get("tg_send_allowed_count"), 0)

    def test_prod_state_write_false(self):
        """prod_state_write is false."""
        self.assertFalse(self.result.get("prod_state_write"))

    def test_daemon_started_false(self):
        """daemon_started is false."""
        self.assertFalse(self.result.get("daemon_started"))

    def test_watcher_started_false(self):
        """watcher_started is false."""
        self.assertFalse(self.result.get("watcher_started"))

    def test_credentials_read_false(self):
        """credentials_read is false."""
        self.assertFalse(self.result.get("credentials_read"))

    def test_files_deleted_false(self):
        """files_deleted is false."""
        self.assertFalse(self.result.get("files_deleted"))

    def test_quality_flags_preserved(self):
        """quality_flags_preserved is true."""
        self.assertTrue(self.result.get("quality_flags_preserved"))

    def test_label_confidence_preserved(self):
        """label_confidence_preserved is true."""
        self.assertTrue(self.result.get("label_confidence_preserved"))

    def test_liquidation_price_note_preserved(self):
        """liquidation_price_note_preserved is true."""
        self.assertTrue(self.result.get("liquidation_price_note_preserved"))

    def test_delta_status_preserved(self):
        """delta_status_preserved is true."""
        self.assertTrue(self.result.get("delta_status_preserved"))

    def test_timestamp_status_preserved(self):
        """timestamp_status_preserved is true."""
        self.assertTrue(self.result.get("timestamp_status_preserved"))

    # ── Per-envelope tests ────────────────────────────────────────────────────

    def test_envelope_count_positive(self):
        """At least one envelope generated."""
        self.assertGreater(len(self.envelopes), 0,
                           "Expected at least 1 envelope")

    def test_envelope_count_matches_result(self):
        """JSONL line count matches result.envelopes_written."""
        self.assertEqual(
            len(self.envelopes),
            self.result.get("envelopes_written", -1),
        )

    def test_all_envelopes_have_v112z_extension(self):
        """Every envelope has v112z_extension."""
        for i, env in enumerate(self.envelopes):
            self.assertIn("v112z_extension", env,
                          f"Envelope {i} missing v112z_extension")

    def test_all_envelopes_have_label_confidence(self):
        """Every envelope has label_confidence in extension."""
        for i, env in enumerate(self.envelopes):
            ext = env.get("v112z_extension", {})
            self.assertTrue(
                ext.get("label_confidence"),
                f"Envelope {i} [{ext.get('asset', '?')}] missing label_confidence"
            )
            self.assertIn(
                ext.get("label_confidence"),
                ["high", "medium", "low"],
                f"Envelope {i} label_confidence invalid: {ext.get('label_confidence')}"
            )

    def test_all_envelopes_have_label_explanation(self):
        """Every envelope has label_explanation in extension."""
        for i, env in enumerate(self.envelopes):
            ext = env.get("v112z_extension", {})
            self.assertTrue(
                ext.get("label_explanation"),
                f"Envelope {i} [{ext.get('asset', '?')}] missing label_explanation"
            )
            self.assertGreater(
                len(ext.get("label_explanation", "")),
                20,
                f"Envelope {i} label_explanation too short"
            )

    def test_all_null_liquidation_have_note(self):
        """All envelopes with null liquidation_price have liquidation_price_note."""
        for i, env in enumerate(self.envelopes):
            ext = env.get("v112z_extension", {})
            liq_price = ext.get("liquidation_price")
            if liq_price is None:
                self.assertTrue(
                    ext.get("liquidation_price_note"),
                    f"Envelope {i} null liquidation_price has empty note"
                )
                self.assertIn(
                    "清算价格不可用",
                    ext.get("liquidation_price_note", ""),
                    f"Envelope {i} liquidation_price_note missing Chinese note"
                )

    def test_all_envelopes_have_delta_status(self):
        """Every envelope has delta_status in extension."""
        for i, env in enumerate(self.envelopes):
            ext = env.get("v112z_extension", {})
            self.assertTrue(
                ext.get("delta_status"),
                f"Envelope {i} missing delta_status"
            )
            self.assertEqual(
                ext.get("delta_status"),
                "unavailable_one_shot_no_previous_position",
                f"Envelope {i} delta_status unexpected: {ext.get('delta_status')}"
            )

    def test_all_envelopes_have_timestamp_status(self):
        """Every envelope has timestamp_status in extension."""
        for i, env in enumerate(self.envelopes):
            ext = env.get("v112z_extension", {})
            self.assertTrue(
                ext.get("timestamp_status"),
                f"Envelope {i} missing timestamp_status"
            )
            self.assertEqual(
                ext.get("timestamp_status"),
                "local_observed_at_no_hl_server_timestamp",
                f"Envelope {i} timestamp_status unexpected: {ext.get('timestamp_status')}"
            )

    def test_all_envelopes_have_quality_flags(self):
        """Every envelope has non-empty quality_flags in extension."""
        for i, env in enumerate(self.envelopes):
            ext = env.get("v112z_extension", {})
            qf = ext.get("quality_flags", [])
            self.assertTrue(
                isinstance(qf, list) and len(qf) > 0,
                f"Envelope {i} quality_flags empty or not a list"
            )

    def test_all_envelopes_have_degrade_reasons(self):
        """Every envelope has non-empty degrade_reasons in extension."""
        for i, env in enumerate(self.envelopes):
            ext = env.get("v112z_extension", {})
            dr = ext.get("degrade_reasons", [])
            self.assertTrue(
                isinstance(dr, list) and len(dr) > 0,
                f"Envelope {i} degrade_reasons empty or not a list"
            )

    def test_all_envelopes_eligible_for_real_send_false(self):
        """Every envelope has eligible_for_real_send=false."""
        for i, env in enumerate(self.envelopes):
            ext = env.get("v112z_extension", {})
            self.assertFalse(
                ext.get("eligible_for_real_send"),
                f"Envelope {i} eligible_for_real_send is not false"
            )

    def test_all_envelopes_real_send_candidate_false(self):
        """Every envelope has real_send_candidate=false."""
        for i, env in enumerate(self.envelopes):
            ext = env.get("v112z_extension", {})
            self.assertFalse(
                ext.get("real_send_candidate"),
                f"Envelope {i} real_send_candidate is not false"
            )

    def test_all_envelopes_degraded_true(self):
        """Every envelope has degraded=true."""
        for i, env in enumerate(self.envelopes):
            ext = env.get("v112z_extension", {})
            self.assertTrue(
                ext.get("degraded"),
                f"Envelope {i} degraded is not true"
            )

    def test_all_envelopes_mock_replay_only_true(self):
        """Every envelope has mock_replay_only=true."""
        for i, env in enumerate(self.envelopes):
            ext = env.get("v112z_extension", {})
            self.assertTrue(
                ext.get("mock_replay_only"),
                f"Envelope {i} mock_replay_only is not true"
            )

    def test_no_envelope_enters_tg_send_path(self):
        """No degraded envelope has tg_send_allowed=true in routing_guard."""
        for i, env in enumerate(self.envelopes):
            ext = env.get("v112z_extension", {})
            rg = ext.get("routing_guard", {})
            self.assertFalse(
                rg.get("tg_send_allowed"),
                f"Envelope {i} tg_send_allowed is true — would enter TG send path!"
            )

    def test_no_envelope_disguised_as_live_passed(self):
        """No degraded envelope is disguised as live passed."""
        for i, env in enumerate(self.envelopes):
            ext = env.get("v112z_extension", {})
            # Check: if degraded=true, envelope_status must NOT be "live_passed"
            self.assertNotEqual(
                ext.get("envelope_status"),
                "live_passed",
                f"Envelope {i} has envelope_status='live_passed' but is degraded!"
            )
            # Check: degraded=true must be clearly stated
            self.assertTrue(
                ext.get("degraded"),
                f"Envelope {i} degraded flag not set"
            )

    def test_no_low_confidence_disguised_as_high(self):
        """Low-confidence labels are NOT disguised as high-confidence institutions."""
        for i, env in enumerate(self.envelopes):
            ext = env.get("v112z_extension", {})
            lc = ext.get("label_confidence", "")
            label = ext.get("label", "")
            # low confidence labels must stay low
            if "Unknown" in str(label) or "unknown" in str(label).lower():
                self.assertEqual(
                    lc,
                    "low",
                    f"Envelope {i} unknown whale '{label}' has confidence '{lc}', should be 'low'"
                )

    def test_all_envelopes_have_routing_guard(self):
        """Every envelope has routing_guard with all false."""
        for i, env in enumerate(self.envelopes):
            ext = env.get("v112z_extension", {})
            rg = ext.get("routing_guard", {})
            self.assertIsNotNone(rg, f"Envelope {i} missing routing_guard")
            self.assertFalse(rg.get("preview_allowed"),
                             f"Envelope {i} preview_allowed is true")
            self.assertFalse(rg.get("tg_send_allowed"),
                             f"Envelope {i} tg_send_allowed is true")
            self.assertFalse(rg.get("prod_state_write_allowed"),
                             f"Envelope {i} prod_state_write_allowed is true")

    def test_all_envelopes_have_envelope_status(self):
        """Every envelope has envelope_status='degraded_compatible'."""
        for i, env in enumerate(self.envelopes):
            ext = env.get("v112z_extension", {})
            self.assertEqual(
                ext.get("envelope_status"),
                "degraded_compatible",
                f"Envelope {i} envelope_status is not 'degraded_compatible'"
            )

    def test_all_envelopes_have_address_and_asset(self):
        """Every envelope has address, address_short, and asset."""
        for i, env in enumerate(self.envelopes):
            ext = env.get("v112z_extension", {})
            self.assertTrue(ext.get("address"),
                            f"Envelope {i} missing address")
            self.assertTrue(ext.get("address_short"),
                            f"Envelope {i} missing address_short")
            self.assertTrue(ext.get("asset"),
                            f"Envelope {i} missing asset")

    # ── v112H base envelope integration tests ─────────────────────────────────

    def test_all_v112h_base_envelopes_have_required_keys(self):
        """All envelopes have v112H base required keys."""
        required_keys = [
            "schema_version", "signal_id", "card_type", "adapter_version",
            "source_kind", "observed_at", "primary_assets", "direction",
            "severity_score", "confidence_score", "event_key",
            "dedupe_key", "cooldown_key", "payload_hash",
            "readiness", "live_ready", "public_card", "safety_flags", "metadata",
        ]
        for i, env in enumerate(self.envelopes):
            for key in required_keys:
                self.assertIn(key, env,
                              f"Envelope {i} missing v112H base key: {key}")

    def test_all_v112h_base_card_type_correct(self):
        """All envelopes have card_type=whale_position_alert."""
        for i, env in enumerate(self.envelopes):
            self.assertEqual(
                env.get("card_type"),
                "whale_position_alert",
                f"Envelope {i} card_type not whale_position_alert"
            )

    def test_all_v112h_base_live_ready_false(self):
        """All envelopes have live_ready=false."""
        for i, env in enumerate(self.envelopes):
            self.assertFalse(
                env.get("live_ready"),
                f"Envelope {i} live_ready is true"
            )

    def test_all_v112h_base_safety_flags_correct(self):
        """All envelopes have correct v112H safety_flags."""
        for i, env in enumerate(self.envelopes):
            sf = env.get("safety_flags", {})
            self.assertFalse(sf.get("real_tg_sent"),
                             f"Envelope {i} real_tg_sent is true")
            self.assertFalse(sf.get("external_api_called"),
                             f"Envelope {i} external_api_called is true")
            self.assertFalse(sf.get("external_ai_called"),
                             f"Envelope {i} external_ai_called is true")
            self.assertFalse(sf.get("daemon_started"),
                             f"Envelope {i} daemon_started is true")

    def test_all_v112h_base_public_card_not_empty(self):
        """All envelopes have non-empty public_card."""
        for i, env in enumerate(self.envelopes):
            pc = env.get("public_card", "")
            self.assertTrue(pc and len(pc.strip()) > 20,
                            f"Envelope {i} public_card too short or empty")

    # ── Leak scan tests ──────────────────────────────────────────────────────

    def test_no_wallet_leak_in_public_card(self):
        """No full 0x... wallet address in any public_card."""
        import re
        wallet_pat = re.compile(r'0x[a-fA-F0-9]{40}')
        for i, env in enumerate(self.envelopes):
            pc = env.get("public_card", "")
            matches = wallet_pat.findall(pc)
            self.assertEqual(
                len(matches), 0,
                f"Envelope {i} has full wallet address in public_card: {matches}"
            )

    def test_no_forbidden_paths_in_public_card(self):
        """No local path terms in any public_card."""
        forbidden = ["C:\\Users\\PC", "ai_relay_desk", "C:\\Users"]
        for i, env in enumerate(self.envelopes):
            pc = env.get("public_card", "").lower()
            for fp in forbidden:
                self.assertNotIn(
                    fp.lower(), pc,
                    f"Envelope {i} public_card contains forbidden path: {fp}"
                )

    def test_no_debug_terms_in_public_card(self):
        """No debug/internal terms in any public_card."""
        debug_terms = ["debug", "internal", "trace", "fixture"]
        for i, env in enumerate(self.envelopes):
            pc = env.get("public_card", "").lower()
            for dt in debug_terms:
                self.assertNotIn(
                    dt, pc,
                    f"Envelope {i} public_card contains debug term: {dt}"
                )

    def test_leak_scan_clean(self):
        """scan_envelope_leaks returns clean for all envelopes."""
        from scripts.market_radar_signal_envelope_v112h import scan_envelope_leaks
        for i, env in enumerate(self.envelopes):
            result = scan_envelope_leaks(env)
            self.assertTrue(
                result["clean"],
                f"Envelope {i} leak scan not clean: debug={result['debug_terms_found']}, "
                f"secret={result['secret_terms_found']}, wallet={result['wallet_leak_details']}"
            )

    # ── Label confidence summary ─────────────────────────────────────────────

    def test_label_confidence_distribution(self):
        """Label confidence distribution is correct."""
        lc_dist = self.result.get("label_confidence_distribution", {})
        total = sum(lc_dist.values())
        self.assertEqual(total, len(self.envelopes),
                         f"Label confidence distribution total {total} != envelope count {len(self.envelopes)}")
        self.assertEqual(lc_dist.get("high", 0), 0,
                         "Should have 0 high confidence labels")
        self.assertGreater(lc_dist.get("medium", 0) + lc_dist.get("low", 0), 0,
                           "Should have some medium or low confidence labels")

    def test_low_confidence_labels_exist(self):
        """Low confidence labels are present (not missing)."""
        lc_dist = self.result.get("label_confidence_distribution", {})
        self.assertGreater(lc_dist.get("low", 0), 0,
                           "Expected some low confidence labels")

    # ── Quality flags summary ─────────────────────────────────────────────────

    def test_quality_flags_distribution(self):
        """Quality flags distribution is meaningful."""
        qf_dist = self.result.get("quality_flags_distribution", {})
        self.assertGreater(len(qf_dist), 0,
                           "Quality flags distribution should not be empty")
        # Key flags should be present
        self.assertIn("degraded_label_confidence", qf_dist,
                      "degraded_label_confidence flag should appear")
        self.assertIn("delta_unavailable", qf_dist,
                      "delta_unavailable flag should appear")
        self.assertIn("local_timestamp_only", qf_dist,
                      "local_timestamp_only flag should appear")


if __name__ == "__main__":
    unittest.main(verbosity=2)
