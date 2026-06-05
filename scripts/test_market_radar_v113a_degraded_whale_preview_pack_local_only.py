"""Test suite for Market Radar v1.13-A — Degraded Whale Preview Pack (Local Only).

Covers:
  - Result JSON exists and has correct fields
  - Preview cards JSONL exists
  - Markdown report exists
  - Handoff markdown exists
  - Input envelopes count > 0
  - Preview cards count equals input envelopes count
  - external_api_called=false
  - local_preview_only=true
  - degraded_preview_pack_built=true
  - eligible_for_real_send_count=0
  - real_send_candidate_count=0
  - tg_send_allowed_count=0
  - prod_state_write=false
  - daemon_started=false
  - watcher_started=false
  - credentials_read=false
  - files_deleted=false
  - All cards have local_preview_only=true
  - All cards have eligible_for_real_send=false
  - All cards have real_send_candidate=false
  - All cards have tg_send_allowed=false
  - All cards have label_confidence
  - Low/medium confidence cards have label_explanation
  - Null liquidation_price shows "清算价格不可用"
  - Delta unavailable shows "单次快照，暂无法计算仓位变化"
  - Local timestamp shows "本地观察时间"
  - Degraded preview NOT disguised as live passed
  - No card enters TG send path

Usage:
    python scripts/test_market_radar_v113a_degraded_whale_preview_pack_local_only.py
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


class TestV113ARunner(unittest.TestCase):
    """Test the v113A runner produces correct output files and invariants."""

    @classmethod
    def setUpClass(cls):
        """Run the v113A runner to generate output files."""
        import subprocess
        runner_path = ROOT / "scripts" / "run_market_radar_v113a_degraded_whale_preview_pack_local_only.py"
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
        cls.result_json_path = ROOT / "results" / "market_radar_v113a_degraded_whale_preview_pack_result.json"
        cls.jsonl_path = ROOT / "results" / "market_radar_v113a_degraded_whale_preview_cards.jsonl"
        cls.report_path = ROOT / "runs" / "market_radar" / "v113a_degraded_whale_preview_pack_local_only.md"
        cls.handoff_path = ROOT / "runs" / "market_radar" / "v113a_degraded_whale_preview_pack_local_only_handoff.md"

        # Load result
        if cls.result_json_path.exists():
            with open(cls.result_json_path, "r", encoding="utf-8") as f:
                cls.result = json.load(f)
        else:
            cls.result = {}

        # Load preview cards
        cls.cards: list[dict] = []
        if cls.jsonl_path.exists():
            with open(cls.jsonl_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        try:
                            cls.cards.append(json.loads(line))
                        except json.JSONDecodeError:
                            pass

    # ══════════════════════════════════════════════════════════════════════════════════
    # Runner exit code and output existence
    # ══════════════════════════════════════════════════════════════════════════════════

    def test_01_runner_exit_code_zero(self):
        """v113A runner exit code = 0."""
        self.assertEqual(self.exit_code, 0, f"Runner exited with {self.exit_code}\n{self.stderr}")

    def test_02_result_json_exists(self):
        """Result JSON exists."""
        self.assertTrue(self.result_json_path.exists(), f"Missing: {self.result_json_path}")

    def test_03_preview_cards_jsonl_exists(self):
        """Preview cards JSONL exists."""
        self.assertTrue(self.jsonl_path.exists(), f"Missing: {self.jsonl_path}")

    def test_04_markdown_report_exists(self):
        """Markdown report exists."""
        self.assertTrue(self.report_path.exists(), f"Missing: {self.report_path}")

    def test_05_handoff_markdown_exists(self):
        """Handoff markdown exists."""
        self.assertTrue(self.handoff_path.exists(), f"Missing: {self.handoff_path}")

    # ══════════════════════════════════════════════════════════════════════════════════
    # Result JSON field checks
    # ══════════════════════════════════════════════════════════════════════════════════

    def test_10_input_envelopes_gt_zero(self):
        """Input envelopes count > 0."""
        self.assertGreater(self.result.get("input_envelopes_loaded", 0), 0,
                           "input_envelopes_loaded must be > 0")

    def test_11_cards_equal_envelopes(self):
        """Preview cards count equals input envelopes count."""
        self.assertEqual(
            self.result.get("preview_cards_written", 0),
            self.result.get("input_envelopes_loaded", 0),
            "preview_cards_written must equal input_envelopes_loaded"
        )

    def test_12_status_passed(self):
        """Status is 'passed'."""
        self.assertEqual(self.result.get("status"), "passed",
                         f"Expected status='passed', got '{self.result.get('status')}'")

    def test_13_external_api_called_false(self):
        """external_api_called=false."""
        self.assertFalse(self.result.get("external_api_called"),
                         "external_api_called must be false")

    def test_14_local_preview_only_true(self):
        """local_preview_only=true."""
        self.assertTrue(self.result.get("local_preview_only"),
                        "local_preview_only must be true")

    def test_15_degraded_preview_pack_built_true(self):
        """degraded_preview_pack_built=true."""
        self.assertTrue(self.result.get("degraded_preview_pack_built"),
                        "degraded_preview_pack_built must be true")

    def test_16_eligible_for_real_send_count_zero(self):
        """eligible_for_real_send_count=0."""
        self.assertEqual(self.result.get("eligible_for_real_send_count"), 0,
                         "eligible_for_real_send_count must be 0")

    def test_17_real_send_candidate_count_zero(self):
        """real_send_candidate_count=0."""
        self.assertEqual(self.result.get("real_send_candidate_count"), 0,
                         "real_send_candidate_count must be 0")

    def test_18_tg_send_allowed_count_zero(self):
        """tg_send_allowed_count=0."""
        self.assertEqual(self.result.get("tg_send_allowed_count"), 0,
                         "tg_send_allowed_count must be 0")

    def test_19_prod_state_write_false(self):
        """prod_state_write=false."""
        self.assertFalse(self.result.get("prod_state_write"),
                         "prod_state_write must be false")

    def test_20_daemon_started_false(self):
        """daemon_started=false."""
        self.assertFalse(self.result.get("daemon_started"),
                         "daemon_started must be false")

    def test_21_watcher_started_false(self):
        """watcher_started=false."""
        self.assertFalse(self.result.get("watcher_started"),
                         "watcher_started must be false")

    def test_22_credentials_read_false(self):
        """credentials_read=false."""
        self.assertFalse(self.result.get("credentials_read"),
                         "credentials_read must be false")

    def test_23_files_deleted_false(self):
        """files_deleted=false."""
        self.assertFalse(self.result.get("files_deleted"),
                         "files_deleted must be false")

    def test_24_label_confidence_displayed(self):
        """label_confidence_displayed=true."""
        self.assertTrue(self.result.get("label_confidence_displayed"),
                        "label_confidence_displayed must be true")

    def test_25_liq_price_unavailable_displayed(self):
        """liquidation_price_unavailable_displayed=true."""
        self.assertTrue(self.result.get("liquidation_price_unavailable_displayed"),
                        "liquidation_price_unavailable_displayed must be true")

    def test_26_delta_unavailable_displayed(self):
        """delta_unavailable_displayed=true."""
        self.assertTrue(self.result.get("delta_unavailable_displayed"),
                        "delta_unavailable_displayed must be true")

    def test_27_local_timestamp_displayed(self):
        """local_timestamp_displayed=true."""
        self.assertTrue(self.result.get("local_timestamp_displayed"),
                        "local_timestamp_displayed must be true")

    # ══════════════════════════════════════════════════════════════════════════════════
    # Preview card field checks (all cards)
    # ══════════════════════════════════════════════════════════════════════════════════

    def test_30_cards_not_empty(self):
        """Preview cards list is not empty."""
        self.assertGreater(len(self.cards), 0, "Preview cards list must not be empty")

    def test_31_all_cards_local_preview_only_true(self):
        """All cards must have local_preview_only=true."""
        for i, card in enumerate(self.cards):
            self.assertTrue(card.get("local_preview_only"),
                            f"Card {i}: local_preview_only must be true")

    def test_32_all_cards_eligible_for_real_send_false(self):
        """All cards must have eligible_for_real_send=false."""
        for i, card in enumerate(self.cards):
            self.assertFalse(card.get("eligible_for_real_send"),
                             f"Card {i}: eligible_for_real_send must be false")

    def test_33_all_cards_real_send_candidate_false(self):
        """All cards must have real_send_candidate=false."""
        for i, card in enumerate(self.cards):
            self.assertFalse(card.get("real_send_candidate"),
                             f"Card {i}: real_send_candidate must be false")

    def test_34_all_cards_tg_send_allowed_false(self):
        """All cards must have tg_send_allowed=false."""
        for i, card in enumerate(self.cards):
            self.assertFalse(card.get("tg_send_allowed"),
                             f"Card {i}: tg_send_allowed must be false")

    def test_35_all_cards_degraded_true(self):
        """All cards must have degraded=true."""
        for i, card in enumerate(self.cards):
            self.assertTrue(card.get("degraded"),
                            f"Card {i}: degraded must be true")

    def test_36_all_cards_mock_replay_only_true(self):
        """All cards must have mock_replay_only=true."""
        for i, card in enumerate(self.cards):
            self.assertTrue(card.get("mock_replay_only"),
                            f"Card {i}: mock_replay_only must be true")

    def test_37_all_cards_prod_state_write_allowed_false(self):
        """All cards must have prod_state_write_allowed=false."""
        for i, card in enumerate(self.cards):
            self.assertFalse(card.get("prod_state_write_allowed"),
                             f"Card {i}: prod_state_write_allowed must be false")

    def test_38_all_cards_have_label_confidence(self):
        """All cards must have label_confidence."""
        for i, card in enumerate(self.cards):
            self.assertTrue(card.get("label_confidence"),
                            f"Card {i}: label_confidence missing")

    # ══════════════════════════════════════════════════════════════════════════════════
    # Low/medium confidence card checks
    # ══════════════════════════════════════════════════════════════════════════════════

    def test_40_low_medium_cards_have_label_explanation(self):
        """Low/medium confidence cards must have label_explanation."""
        for i, card in enumerate(self.cards):
            lc = str(card.get("label_confidence", ""))
            if lc in ("low", "medium"):
                self.assertTrue(card.get("label_explanation"),
                                f"Card {i}: {lc} confidence card missing label_explanation")

    def test_41_low_confidence_not_disguised_as_confirmed(self):
        """Low/medium confidence labels must NOT contain 'confirmed'/'verified' claims."""
        for i, card in enumerate(self.cards):
            lc = str(card.get("label_confidence", ""))
            if lc in ("low", "medium"):
                label = str(card.get("label", "")).lower()
                self.assertNotIn("confirmed", label,
                                 f"Card {i}: {lc}-confidence label contains 'confirmed'")
                self.assertNotIn("verified", label,
                                 f"Card {i}: {lc}-confidence label contains 'verified'")
                explanation = str(card.get("label_explanation", "")).lower()
                # Check for AFFIRMATIVE claims only (not negations)
                expl_lower = explanation.lower()
                # Remove negation patterns before checking
                import re
                cleaned = re.sub(r"not\s+(a\s+)?high[\s-]?confidence", "", expl_lower)
                self.assertNotIn("high-confidence", cleaned,
                                 f"Card {i}: label_explanation incorrectly claims high-confidence")
                self.assertNotIn("high confidence", cleaned,
                                 f"Card {i}: label_explanation incorrectly claims high confidence")

    # ══════════════════════════════════════════════════════════════════════════════════
    # Liquidation price, delta, timestamp display checks
    # ══════════════════════════════════════════════════════════════════════════════════

    def test_50_null_liq_price_shows_unavailable(self):
        """Cards with null liquidation_price must show '清算价格不可用'."""
        for i, card in enumerate(self.cards):
            if card.get("liquidation_price") is None:
                display = str(card.get("liquidation_price_display", ""))
                self.assertIn("清算价格不可用", display,
                              f"Card {i}: null liquidation_price but display='{display}'")

    def test_51_delta_unavailable_shows_explanation(self):
        """Cards with unavailable delta must show explanation."""
        for i, card in enumerate(self.cards):
            delta_status = str(card.get("delta_status", ""))
            if "unavailable" in delta_status:
                display = str(card.get("delta_display", ""))
                self.assertIn("暂无法计算仓位变化", display,
                              f"Card {i}: delta unavailable but display='{display}'")

    def test_52_local_timestamp_shows_explanation(self):
        """Cards with local timestamp must show '本地观察时间'."""
        for i, card in enumerate(self.cards):
            ts_status = str(card.get("timestamp_status", ""))
            if "local" in ts_status:
                display = str(card.get("timestamp_display", ""))
                self.assertIn("本地观察时间", display,
                              f"Card {i}: local timestamp but display='{display}'")

    # ══════════════════════════════════════════════════════════════════════════════════
    # Routing guard / TG send path checks
    # ══════════════════════════════════════════════════════════════════════════════════

    def test_60_no_card_enters_tg_send_path(self):
        """No card enters TG send path (tg_send_allowed must ALL be false)."""
        for i, card in enumerate(self.cards):
            self.assertFalse(card.get("tg_send_allowed"),
                             f"Card {i}: tg_send_allowed=true — card would enter TG send path!")

    def test_61_no_card_is_real_send_candidate(self):
        """No card is a real send candidate."""
        for i, card in enumerate(self.cards):
            self.assertFalse(card.get("real_send_candidate"),
                             f"Card {i}: real_send_candidate=true")

    def test_62_no_card_eligible_for_real_send(self):
        """No card is eligible for real send."""
        for i, card in enumerate(self.cards):
            self.assertFalse(card.get("eligible_for_real_send"),
                             f"Card {i}: eligible_for_real_send=true")

    def test_63_no_degraded_disguised_as_live_passed(self):
        """No degraded preview disguised as live passed."""
        for i, card in enumerate(self.cards):
            self.assertTrue(card.get("degraded"),
                            f"Card {i}: degraded=false — would be disguised as live passed")
            self.assertTrue(card.get("local_preview_only"),
                            f"Card {i}: local_preview_only=false — would be disguised as live")

    # ══════════════════════════════════════════════════════════════════════════════════
    # Title / body checks
    # ══════════════════════════════════════════════════════════════════════════════════

    def test_70_all_cards_have_title(self):
        """All cards must have a title."""
        for i, card in enumerate(self.cards):
            self.assertTrue(card.get("title"),
                            f"Card {i}: title missing")

    def test_71_all_cards_have_body(self):
        """All cards must have a body."""
        for i, card in enumerate(self.cards):
            self.assertTrue(card.get("body"),
                            f"Card {i}: body missing")

    def test_72_title_contains_degraded_indicator(self):
        """Title must indicate degraded/preview status."""
        for i, card in enumerate(self.cards):
            title = str(card.get("title", ""))
            self.assertIn("降级", title,
                          f"Card {i}: title missing '降级' indicator: '{title}'")

    # ══════════════════════════════════════════════════════════════════════════════════
    # Warnings checks
    # ══════════════════════════════════════════════════════════════════════════════════

    def test_80_all_cards_have_warnings(self):
        """All cards must have at least some warnings."""
        for i, card in enumerate(self.cards):
            warnings = card.get("warnings", [])
            self.assertIsInstance(warnings, list,
                                  f"Card {i}: warnings is not a list")
            self.assertGreater(len(warnings), 0,
                               f"Card {i}: warnings list is empty")


if __name__ == "__main__":
    unittest.main(verbosity=2)
