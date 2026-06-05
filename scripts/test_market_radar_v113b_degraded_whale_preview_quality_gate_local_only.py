"""Test suite for Market Radar v1.13-B — Degraded Whale Preview Quality Gate (Local Only).

Covers:
  - result JSON exists
  - decisions JSONL exists
  - markdown report exists
  - handoff markdown exists
  - input preview cards count > 0
  - quality decisions count equals input cards count
  - external_api_called=false
  - local_quality_gate_only=true
  - eligible_for_real_send_count=0
  - real_send_candidate_count=0
  - tg_send_allowed_count=0
  - prod_state_write=false
  - daemon_started=false
  - watcher_started=false
  - credentials_read=false
  - files_deleted=false
  - All decisions have eligible_for_real_send=false
  - All decisions have tg_send_allowed=false
  - All decisions have quality_gate_decision
  - quality_gate_decision is one of valid values
  - All decisions have gate_checks
  - Low-confidence cards pass label confidence gate or are blocked
  - Missing liquidation_price warning cards are blocked
  - Missing delta explanation cards are blocked
  - Missing local timestamp explanation cards are blocked
  - Cards with misleading wording are blocked or review_only
  - No degraded preview disguised as live passed
  - No card enters TG send path

Usage:
    python scripts/test_market_radar_v113b_degraded_whale_preview_quality_gate_local_only.py
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

VALID_DECISIONS = {"operator_preview_ready", "review_only", "blocked"}


class TestV113BRunner(unittest.TestCase):
    """Test the v113B runner produces correct outputs and invariants."""

    @classmethod
    def setUpClass(cls):
        """Run the v113B runner to generate output files."""
        import subprocess
        runner_path = ROOT / "scripts" / "run_market_radar_v113b_degraded_whale_preview_quality_gate_local_only.py"
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
        cls.result_json_path = ROOT / "results" / "market_radar_v113b_degraded_whale_preview_quality_gate_result.json"
        cls.decisions_path = ROOT / "results" / "market_radar_v113b_degraded_whale_preview_quality_decisions.jsonl"
        cls.report_path = ROOT / "runs" / "market_radar" / "v113b_degraded_whale_preview_quality_gate_local_only.md"
        cls.handoff_path = ROOT / "runs" / "market_radar" / "v113b_degraded_whale_preview_quality_gate_local_only_handoff.md"
        cls.input_cards_path = ROOT / "results" / "market_radar_v113a_degraded_whale_preview_cards.jsonl"

        # Load result
        if cls.result_json_path.exists():
            with open(cls.result_json_path, "r", encoding="utf-8") as f:
                cls.result = json.load(f)
        else:
            cls.result = {}

        # Load decisions
        cls.decisions: list[dict] = []
        if cls.decisions_path.exists():
            with open(cls.decisions_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        try:
                            cls.decisions.append(json.loads(line))
                        except json.JSONDecodeError:
                            pass

        # Load input cards
        cls.cards: list[dict] = []
        if cls.input_cards_path.exists():
            with open(cls.input_cards_path, "r", encoding="utf-8") as f:
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
        """v113B runner exit code = 0."""
        self.assertEqual(self.exit_code, 0,
                         f"Runner exited with {self.exit_code}\n{self.stderr}")

    def test_02_result_json_exists(self):
        """Result JSON exists."""
        self.assertTrue(self.result_json_path.exists(),
                        f"Missing: {self.result_json_path}")

    def test_03_decisions_jsonl_exists(self):
        """Decisions JSONL exists."""
        self.assertTrue(self.decisions_path.exists(),
                        f"Missing: {self.decisions_path}")

    def test_04_markdown_report_exists(self):
        """Markdown report exists."""
        self.assertTrue(self.report_path.exists(),
                        f"Missing: {self.report_path}")

    def test_05_handoff_markdown_exists(self):
        """Handoff markdown exists."""
        self.assertTrue(self.handoff_path.exists(),
                        f"Missing: {self.handoff_path}")

    # ══════════════════════════════════════════════════════════════════════════════════
    # Result JSON field checks
    # ══════════════════════════════════════════════════════════════════════════════════

    def test_10_input_preview_cards_gt_zero(self):
        """Input preview cards count > 0."""
        self.assertGreater(self.result.get("input_preview_cards_loaded", 0), 0,
                           "input_preview_cards_loaded must be > 0")

    def test_11_decisions_equal_input_cards(self):
        """Quality decisions count equals input cards count."""
        self.assertEqual(
            self.result.get("quality_decisions_written", 0),
            self.result.get("input_preview_cards_loaded", 0),
            "quality_decisions_written must equal input_preview_cards_loaded"
        )
        self.assertEqual(
            len(self.decisions),
            self.result.get("input_preview_cards_loaded", 0),
            "JSONL line count must equal input_preview_cards_loaded"
        )

    def test_12_external_api_called_false(self):
        """external_api_called=false."""
        self.assertFalse(self.result.get("external_api_called"),
                         "external_api_called must be false")

    def test_13_local_quality_gate_only_true(self):
        """local_quality_gate_only=true."""
        self.assertTrue(self.result.get("local_quality_gate_only"),
                        "local_quality_gate_only must be true")

    def test_14_eligible_for_real_send_count_zero(self):
        """eligible_for_real_send_count=0."""
        self.assertEqual(self.result.get("eligible_for_real_send_count"), 0,
                         "eligible_for_real_send_count must be 0")

    def test_15_real_send_candidate_count_zero(self):
        """real_send_candidate_count=0."""
        self.assertEqual(self.result.get("real_send_candidate_count"), 0,
                         "real_send_candidate_count must be 0")

    def test_16_tg_send_allowed_count_zero(self):
        """tg_send_allowed_count=0."""
        self.assertEqual(self.result.get("tg_send_allowed_count"), 0,
                         "tg_send_allowed_count must be 0")

    def test_17_prod_state_write_false(self):
        """prod_state_write=false."""
        self.assertFalse(self.result.get("prod_state_write"),
                         "prod_state_write must be false")

    def test_18_daemon_started_false(self):
        """daemon_started=false."""
        self.assertFalse(self.result.get("daemon_started"),
                         "daemon_started must be false")

    def test_19_watcher_started_false(self):
        """watcher_started=false."""
        self.assertFalse(self.result.get("watcher_started"),
                         "watcher_started must be false")

    def test_20_credentials_read_false(self):
        """credentials_read=false."""
        self.assertFalse(self.result.get("credentials_read"),
                         "credentials_read must be false")

    def test_21_files_deleted_false(self):
        """files_deleted=false."""
        self.assertFalse(self.result.get("files_deleted"),
                         "files_deleted must be false")

    # ══════════════════════════════════════════════════════════════════════════════════
    # Per-decision field checks
    # ══════════════════════════════════════════════════════════════════════════════════

    def test_30_decisions_not_empty(self):
        """Decisions list is not empty."""
        self.assertGreater(len(self.decisions), 0,
                           "Decisions list must not be empty")

    def test_31_all_decisions_eligible_for_real_send_false(self):
        """All decisions must have eligible_for_real_send=false."""
        for i, d in enumerate(self.decisions):
            self.assertFalse(d.get("eligible_for_real_send"),
                             f"Decision {i}: eligible_for_real_send must be false")

    def test_32_all_decisions_tg_send_allowed_false(self):
        """All decisions must have tg_send_allowed=false."""
        for i, d in enumerate(self.decisions):
            self.assertFalse(d.get("tg_send_allowed"),
                             f"Decision {i}: tg_send_allowed must be false")

    def test_33_all_decisions_have_quality_gate_decision(self):
        """All decisions must have quality_gate_decision."""
        for i, d in enumerate(self.decisions):
            self.assertTrue(d.get("quality_gate_decision"),
                            f"Decision {i}: quality_gate_decision missing")

    def test_34_quality_gate_decision_valid_values(self):
        """quality_gate_decision must be one of the valid values."""
        for i, d in enumerate(self.decisions):
            self.assertIn(d.get("quality_gate_decision"), VALID_DECISIONS,
                          f"Decision {i}: invalid quality_gate_decision '{d.get('quality_gate_decision')}'")

    def test_35_all_decisions_have_gate_checks(self):
        """All decisions must have gate_checks."""
        for i, d in enumerate(self.decisions):
            gc = d.get("gate_checks", {})
            self.assertTrue(isinstance(gc, dict) and len(gc) > 0,
                            f"Decision {i}: gate_checks missing or empty")
            required_gates = [
                "safety_routing_gate",
                "degraded_disclosure_gate",
                "label_confidence_gate",
                "misleading_wording_gate",
                "preview_usability_gate",
            ]
            for gate in required_gates:
                self.assertIn(gate, gc,
                              f"Decision {i}: gate_checks missing '{gate}'")
                self.assertIn(gc[gate], ("pass", "fail"),
                              f"Decision {i}: gate '{gate}' value is not pass/fail")

    def test_36_all_decisions_prod_state_write_allowed_false(self):
        """All decisions must have prod_state_write_allowed=false."""
        for i, d in enumerate(self.decisions):
            self.assertFalse(d.get("prod_state_write_allowed"),
                             f"Decision {i}: prod_state_write_allowed must be false")

    def test_37_all_decisions_degraded_true(self):
        """All decisions must have degraded=true."""
        for i, d in enumerate(self.decisions):
            self.assertTrue(d.get("degraded"),
                            f"Decision {i}: degraded must be true")

    def test_38_all_decisions_mock_replay_only_true(self):
        """All decisions must have mock_replay_only=true."""
        for i, d in enumerate(self.decisions):
            self.assertTrue(d.get("mock_replay_only"),
                            f"Decision {i}: mock_replay_only must be true")

    def test_39_all_decisions_have_card_id(self):
        """All decisions must have card_id."""
        for i, d in enumerate(self.decisions):
            self.assertTrue(d.get("card_id"),
                            f"Decision {i}: card_id missing")

    def test_40_all_decisions_have_source_hash(self):
        """All decisions must have source_preview_card_hash."""
        for i, d in enumerate(self.decisions):
            self.assertTrue(d.get("source_preview_card_hash"),
                            f"Decision {i}: source_preview_card_hash missing")
            self.assertEqual(len(d.get("source_preview_card_hash", "")), 64,
                             f"Decision {i}: source_preview_card_hash not SHA-256")

    # ══════════════════════════════════════════════════════════════════════════════════
    # Label confidence gate checks
    # ══════════════════════════════════════════════════════════════════════════════════

    def test_50_low_confidence_cards_pass_label_gate_or_blocked(self):
        """Low-confidence cards must pass label confidence gate or be blocked."""
        for i, d in enumerate(self.decisions):
            lc = d.get("label_confidence", "")
            if lc == "low":
                gate_ok = d["gate_checks"]["label_confidence_gate"] == "pass"
                blocked_or_review = d["quality_gate_decision"] in ("blocked", "review_only")
                self.assertTrue(gate_ok or blocked_or_review,
                                f"Decision {i}: low-confidence label not gated. "
                                f"gate={d['gate_checks']['label_confidence_gate']}, "
                                f"decision={d['quality_gate_decision']}")

    def test_51_medium_confidence_labels_not_disguised(self):
        """Medium-confidence labels must NOT be written as confirmed institutions."""
        for i, d in enumerate(self.decisions):
            lc = d.get("label_confidence", "")
            if lc == "medium":
                label = str(d.get("label", ""))
                self.assertNotIn("confirmed", label.lower(),
                                 f"Decision {i}: medium-confidence label '{label}' uses 'confirmed'")
                self.assertNotIn("verified", label.lower(),
                                 f"Decision {i}: medium-confidence label '{label}' uses 'verified'")
                self.assertNotIn("确定", label,
                                 f"Decision {i}: medium-confidence label '{label}' uses '确定'")

    # ══════════════════════════════════════════════════════════════════════════════════
    # Degraded disclosure gate checks (applied to input cards)
    # ══════════════════════════════════════════════════════════════════════════════════

    def test_60_null_liquidation_price_cards_have_warning_or_blocked(self):
        """Cards with null liquidation_price must have '清算价格不可用' warning or be blocked."""
        for i, card in enumerate(self.cards):
            if card.get("liquidation_price") is None:
                warnings_text = " | ".join(card.get("warnings", []))
                has_warning = "清算价格不可用" in warnings_text
                if not has_warning:
                    # Must be blocked
                    if i < len(self.decisions):
                        self.assertEqual(
                            self.decisions[i]["quality_gate_decision"], "blocked",
                            f"Card {i}: null liquidation_price without warning must be blocked"
                        )

    def test_61_delta_unavailable_cards_have_explanation_or_blocked(self):
        """Cards with unavailable delta must have explanation or be blocked."""
        for i, card in enumerate(self.cards):
            delta_status = str(card.get("delta_status", ""))
            if "unavailable" in delta_status:
                warnings_text = " | ".join(card.get("warnings", []))
                has_delta_warning = "暂无法计算仓位变化" in warnings_text
                if not has_delta_warning:
                    if i < len(self.decisions):
                        self.assertEqual(
                            self.decisions[i]["quality_gate_decision"], "blocked",
                            f"Card {i}: delta unavailable without explanation must be blocked"
                        )

    def test_62_local_timestamp_cards_have_explanation_or_blocked(self):
        """Cards with local timestamp must have explanation or be blocked."""
        for i, card in enumerate(self.cards):
            ts_status = str(card.get("timestamp_status", ""))
            if "local" in ts_status:
                warnings_text = " | ".join(card.get("warnings", []))
                has_ts_warning = "本地观察时间" in warnings_text
                if not has_ts_warning:
                    if i < len(self.decisions):
                        self.assertEqual(
                            self.decisions[i]["quality_gate_decision"], "blocked",
                            f"Card {i}: local timestamp without explanation must be blocked"
                        )

    # ══════════════════════════════════════════════════════════════════════════════════
    # Misleading wording gate
    # ══════════════════════════════════════════════════════════════════════════════════

    def test_70_misleading_wording_blocked_or_review_only(self):
        """Cards with misleading wording must be blocked or review_only."""
        forbidden_terms = ["确认", "实锤", "确定机构", "强信号",
                           "立即发送", "可直接发布", "已触发报警", "正式信号"]
        for i, card in enumerate(self.cards):
            title = str(card.get("title", ""))
            body = str(card.get("body", ""))
            combined = title + body
            found_terms = [t for t in forbidden_terms if t in combined]
            if found_terms:
                if i < len(self.decisions):
                    decision = self.decisions[i]["quality_gate_decision"]
                    self.assertIn(decision, ("blocked", "review_only"),
                                  f"Card {i}: contains forbidden terms {found_terms} "
                                  f"but decision is '{decision}' (must be blocked or review_only)")

    # ══════════════════════════════════════════════════════════════════════════════════
    # No TG send path / no live passed disguise
    # ══════════════════════════════════════════════════════════════════════════════════

    def test_80_no_card_enters_tg_send_path(self):
        """No decision enters TG send path."""
        for i, d in enumerate(self.decisions):
            self.assertFalse(d.get("tg_send_allowed"),
                             f"Decision {i}: tg_send_allowed=true — would enter TG send path!")

    def test_81_no_decision_eligible_for_real_send(self):
        """No decision has eligible_for_real_send=true."""
        for i, d in enumerate(self.decisions):
            self.assertFalse(d.get("eligible_for_real_send"),
                             f"Decision {i}: eligible_for_real_send=true")

    def test_82_no_degraded_disguised_as_live_passed(self):
        """No degraded preview disguised as live passed."""
        for i, d in enumerate(self.decisions):
            self.assertTrue(d.get("degraded"),
                            f"Decision {i}: degraded=false — disguised as live passed")
            # operator_preview_ready still has degraded=true and eligible_for_real_send=false
            if d["quality_gate_decision"] == "operator_preview_ready":
                self.assertFalse(d.get("eligible_for_real_send"),
                                 f"Decision {i}: operator_preview_ready but eligible_for_real_send=true")
                self.assertFalse(d.get("tg_send_allowed"),
                                 f"Decision {i}: operator_preview_ready but tg_send_allowed=true")

    # ══════════════════════════════════════════════════════════════════════════════════
    # Completeness checks
    # ══════════════════════════════════════════════════════════════════════════════════

    def test_90_all_degraded_disclosures_checked(self):
        """all_degraded_disclosures_checked=true."""
        self.assertTrue(self.result.get("all_degraded_disclosures_checked"),
                        "all_degraded_disclosures_checked must be true")

    def test_91_label_confidence_checked(self):
        """label_confidence_checked=true."""
        self.assertTrue(self.result.get("label_confidence_checked"),
                        "label_confidence_checked must be true")

    def test_92_misleading_wording_checked(self):
        """misleading_wording_checked=true."""
        self.assertTrue(self.result.get("misleading_wording_checked"),
                        "misleading_wording_checked must be true")

    def test_93_next_step_correct(self):
        """next_step references v113C."""
        next_step = self.result.get("next_step", "")
        self.assertIn("v113c", next_step.lower(),
                      f"next_step should reference v113C, got '{next_step}'")

    # ══════════════════════════════════════════════════════════════════════════════════
    # Input card invariant checks
    # ══════════════════════════════════════════════════════════════════════════════════

    def test_100_cards_count_matches_result(self):
        """Input cards count matches result's input_preview_cards_loaded."""
        self.assertEqual(
            len(self.cards),
            self.result.get("input_preview_cards_loaded", 0),
            "Loaded card count differs from result"
        )

    def test_101_decisions_count_matches_result(self):
        """Decisions JSONL line count matches result's quality_decisions_written."""
        self.assertEqual(
            len(self.decisions),
            self.result.get("quality_decisions_written", 0),
            "Decisions count differs from result"
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
