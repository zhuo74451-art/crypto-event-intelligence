"""Market Radar v118D — Operator Acceptance Gate + No-Send Review Pack Tests.

Tests cover:
  - v118D runner can be imported and executed
  - v118D reads v118C local result ONLY (no external calls)
  - Five card families all enter decision table
  - Operator decisions only from {accept, watch, reject, manual_required}
  - whale_position_alert is manual_required (not bypassed)
  - liquidation_pressure is NOT accept (threshold not lowered)
  - news_event_market_impact observation_only=true, not_causal_proof=true
  - production readiness is false / 0/5
  - no-send preview confirms telegram_send=false, x_twitter_send=false,
    production_send=false, daemon_or_loop_started=false
  - No raw token/chat_id/message_id in any output
  - v116A–N history files not modified
  - No files deleted

Usage:
    python -X utf8 -m pytest scripts/test_market_radar_v118d_operator_acceptance_gate_and_no_send_review_pack.py -v
"""

from __future__ import annotations

import json
import os
import re
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


# ── Forbidden patterns ──────────────────────────────────────────────────────

FORBIDDEN_PATTERNS = [
    r'\b[0-9]{8,10}:[A-Za-z0-9_-]{35,}\b',
    r'bot[0-9]{8,10}:',
    r'api_key\s*[:=]\s*["\'][A-Za-z0-9_-]{20,}',
    r'chat_id\s*[:=]\s*["\']-?[0-9]{5,}',
    r'password\s*[:=]\s*["\'][^"\']+["\']',
    r'secret\s*[:=]\s*["\'][A-Za-z0-9_-]{10,}',
    r'cookie\s*[:=]\s*["\'][^"\']+["\']',
]

RAW_TOKEN_PATTERN = re.compile(r'\b\d{9,10}:[A-Za-z0-9_-]{35,}\b')
RAW_CHAT_ID_PATTERN = re.compile(r'chat_id["\']?\s*:\s*["\']-?[0-9]{5,}["\']')
RAW_MESSAGE_ID_PATTERN = re.compile(r'message_id["\']?\s*:\s*["\']\d{3,}["\']')


def check_forbidden(text: str) -> list[str]:
    violations = []
    for p in FORBIDDEN_PATTERNS:
        if re.search(p, text, re.IGNORECASE):
            violations.append(f"Pattern: {p[:60]}")
    return violations


def load_json(path: Path) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


# ── v118D Paths ──────────────────────────────────────────────────────────────

V118D_RUNNER = ROOT / "scripts" / "run_market_radar_v118d_operator_acceptance_gate_and_no_send_review_pack.py"
V118D_TEST = ROOT / "scripts" / "test_market_radar_v118d_operator_acceptance_gate_and_no_send_review_pack.py"

V118D_RESULT_JSON = ROOT / "results" / "market_radar_v118d_operator_acceptance_gate_result.json"
V118D_REVIEW_PACK = ROOT / "runs" / "market_radar" / "v118d_operator_review_pack.md"
V118D_DECISION_TABLE = ROOT / "runs" / "market_radar" / "v118d_operator_decision_table.md"
V118D_NO_SEND_PREVIEW = ROOT / "runs" / "market_radar" / "v118d_no_send_preview.md"
V118D_HANDOFF = ROOT / "runs" / "market_radar" / "v118d_local_only_handoff.md"

ALL_V118D_OUTPUT_FILES = [
    V118D_RESULT_JSON,
    V118D_REVIEW_PACK,
    V118D_DECISION_TABLE,
    V118D_NO_SEND_PREVIEW,
    V118D_HANDOFF,
]

FIVE_CARD_FAMILIES = [
    "multi_asset_market_sync",
    "price_oi_volume_anomaly",
    "news_event_market_impact",
    "liquidation_pressure",
    "whale_position_alert",
]

ALLOWED_DECISIONS = {"accept", "watch", "reject", "manual_required"}

# ── Historical output files (must not be modified) ──────────────────────────

V118C_OUTPUT_FILES = [
    ROOT / "results" / "market_radar_v118c_five_card_snapshot_preflight.json",
    ROOT / "results" / "market_radar_v118c_five_card_snapshot_result.json",
    ROOT / "results" / "market_radar_v118c_five_card_snapshot_delivery_result.json",
    ROOT / "results" / "market_radar_v118c_five_card_snapshot_evidence_ledger.jsonl",
    ROOT / "runs" / "market_radar" / "v118c_five_card_snapshot_plain_text_delivery_report.md",
    ROOT / "runs" / "market_radar" / "v118c_operator_snapshot_preview.md",
    ROOT / "runs" / "market_radar" / "v118c_local_only_handoff.md",
]

V118B_OUTPUT_FILES = [
    ROOT / "results" / "market_radar_v118b_five_card_snapshot_preflight.json",
    ROOT / "results" / "market_radar_v118b_five_card_snapshot_result.json",
    ROOT / "results" / "market_radar_v118b_five_card_snapshot_evidence_ledger.jsonl",
    ROOT / "runs" / "market_radar" / "v118b_five_card_operator_snapshot_report.md",
    ROOT / "runs" / "market_radar" / "v118b_operator_snapshot_preview.md",
    ROOT / "runs" / "market_radar" / "v118b_local_only_handoff.md",
]

V118A_OUTPUT_FILES = [
    ROOT / "results" / "market_radar_v118a_three_card_digest_preflight.json",
    ROOT / "results" / "market_radar_v118a_three_card_digest_result.json",
    ROOT / "results" / "market_radar_v118a_three_card_digest_evidence_ledger.jsonl",
    ROOT / "runs" / "market_radar" / "v118a_three_card_digest_shared_pipeline_tg_one_shot_report.md",
    ROOT / "runs" / "market_radar" / "v118a_operator_digest_preview.md",
    ROOT / "runs" / "market_radar" / "v118a_local_only_handoff.md",
]

V117_OUTPUT_FILES = [
    ROOT / "results" / "market_radar_v117_shared_infra_manifest.json",
    ROOT / "results" / "market_radar_v117_shared_pipeline_fixture_results.json",
    ROOT / "results" / "market_radar_v117_shared_pipeline_real_one_shot_result.json",
    ROOT / "results" / "market_radar_v117_shared_pipeline_tg_evidence_ledger.jsonl",
]

V116N_FILES = [
    ROOT / "runs" / "market_radar" / "v116n_one_pager_acceptance_summary.md",
    ROOT / "runs" / "market_radar" / "v116n_operator_review_pack_user_facing.md",
    ROOT / "runs" / "market_radar" / "v116n_user_decision_tree.md",
    ROOT / "runs" / "market_radar" / "v116n_demo_sequence_10min.md",
    ROOT / "runs" / "market_radar" / "v116n_production_readiness_checklist.md",
    ROOT / "runs" / "market_radar" / "v116n_whale_manual_evidence_checklist.md",
    ROOT / "runs" / "market_radar" / "v116n_local_only_handoff.md",
    ROOT / "results" / "market_radar_v116n_user_acceptance_overlay_manifest.json",
]

ALL_REGRESSION_FILES = (
    V118C_OUTPUT_FILES + V118B_OUTPUT_FILES + V118A_OUTPUT_FILES +
    V117_OUTPUT_FILES + V116N_FILES
)


# ═══════════════════════════════════════════════════════════════════════════
# Test Cases
# ═══════════════════════════════════════════════════════════════════════════


class TestV118DFilesExist(unittest.TestCase):
    """Test that v118D runner and test scripts exist."""

    def test_01_runner_exists(self):
        self.assertTrue(V118D_RUNNER.exists(),
                        f"Missing runner: {V118D_RUNNER}")

    def test_02_test_exists(self):
        self.assertTrue(V118D_TEST.exists(),
                        f"Missing test: {V118D_TEST}")


class TestV118DOutputFilesExist(unittest.TestCase):
    """Test that all v118D output files exist after runner execution."""

    def test_10_all_output_files_exist(self):
        missing = [str(f) for f in ALL_V118D_OUTPUT_FILES if not f.exists()]
        self.assertEqual(len(missing), 0,
                         f"Missing v118D output files: {missing}")


class TestV118DRunnerStaticAnalysis(unittest.TestCase):
    """Static analysis of v118D runner source."""

    @classmethod
    def setUpClass(cls):
        cls.source = V118D_RUNNER.read_text(encoding="utf-8") if V118D_RUNNER.exists() else ""

    def test_20_runner_reads_v118c_result(self):
        self.assertIn("v118c_five_card_snapshot_result", self.source)

    def test_21_runner_no_binance_import(self):
        """v118D must NOT import or call Binance (excluding docstring mentions about not calling)."""
        self.assertNotIn("from binance", self.source.lower())
        self.assertNotIn("import binance", self.source.lower())
        self.assertNotIn("binance.com", self.source.lower())
        self.assertNotIn("binance_client", self.source.lower())
        # Check there's no requests.get or urllib call combined with binance
        has_requests = "requests" in self.source.lower()
        has_binance_url = "binance" in self.source.lower()
        if has_requests and has_binance_url:
            self.fail("Must not have requests to binance")

    def test_22_runner_no_rss_import(self):
        """v118D must NOT import or call RSS feeds."""
        self.assertNotIn("import feedparser", self.source.lower())
        self.assertNotIn("from feedparser", self.source.lower())
        self.assertNotIn("feedparser.parse", self.source.lower())
        # Must not have RSS URL patterns
        self.assertNotIn("rss.xml", self.source.lower())
        self.assertNotIn("rss/", self.source.lower())

    def test_23_runner_no_telegram_send(self):
        """v118D must NOT import or call Telegram API."""
        self.assertNotIn("import telegram", self.source.lower())
        self.assertNotIn("from telegram", self.source.lower())
        self.assertNotIn("telegram.Bot", self.source.lower())
        self.assertNotIn("api.telegram.org", self.source.lower())
        self.assertNotIn("sender_contract", self.source.lower())
        self.assertNotIn("create_tg_sender", self.source.lower())

    def test_24_runner_no_ai_model(self):
        """v118D must NOT call any AI/model API."""
        self.assertNotIn("openai", self.source.lower())
        self.assertNotIn("anthropic", self.source.lower())
        self.assertNotIn("openrouter", self.source.lower())

    def test_25_runner_has_five_card_families(self):
        for cf in FIVE_CARD_FAMILIES:
            self.assertIn(cf, self.source, f"Runner must reference {cf}")

    def test_26_runner_has_allowed_decisions(self):
        for dec in ALLOWED_DECISIONS:
            self.assertIn(dec, self.source,
                         f"Runner must support decision '{dec}'")

    def test_27_runner_has_production_false(self):
        self.assertIn("production_readiness_score", self.source)
        self.assertIn("0/5", self.source)

    def test_28_runner_has_no_send_confirmation(self):
        self.assertIn("telegram_send", self.source.lower())
        self.assertIn("x_twitter_send", self.source.lower())
        self.assertIn("production_send", self.source.lower())

    def test_29_runner_has_whale_manual_required(self):
        self.assertIn("manual_required", self.source)

    def test_2a_runner_has_liquidation_not_accept(self):
        self.assertIn("liquidation_pressure", self.source)
        self.assertIn("NOT lowered", self.source)

    def test_2b_runner_has_news_observation_only(self):
        self.assertIn("observation_only", self.source)
        self.assertIn("not_causal_proof", self.source)

    def test_2c_runner_has_daemon_false(self):
        self.assertIn("daemon_or_loop_started", self.source)

    def test_2d_runner_has_contract_validation(self):
        self.assertIn("validate_contract", self.source)

    def test_2e_runner_has_no_external_api(self):
        self.assertNotIn("requests.get", self.source)
        self.assertNotIn("urllib.request", self.source)

    def test_2f_runner_reads_only_local_files(self):
        """v118D must ONLY read local JSON files, never fetch from network."""
        self.assertNotIn("http://", self.source)
        self.assertNotIn("https://", self.source)


class TestV118DResultFile(unittest.TestCase):
    """Test v118D result JSON file."""

    @classmethod
    def setUpClass(cls):
        if V118D_RESULT_JSON.exists():
            cls.result = load_json(V118D_RESULT_JSON)
        else:
            cls.result = None

    def test_30_result_exists(self):
        self.assertIsNotNone(self.result,
                           "Result file not found. Run the v118D runner first.")

    def test_31_result_no_raw_token(self):
        text = json.dumps(self.result, ensure_ascii=False)
        self.assertIsNone(RAW_TOKEN_PATTERN.search(text))

    def test_32_result_no_raw_chat_id(self):
        text = json.dumps(self.result, ensure_ascii=False)
        self.assertIsNone(RAW_CHAT_ID_PATTERN.search(text))

    def test_33_result_no_raw_message_id(self):
        text = json.dumps(self.result, ensure_ascii=False)
        self.assertIsNone(RAW_MESSAGE_ID_PATTERN.search(text))

    def test_34_result_no_forbidden_patterns(self):
        text = json.dumps(self.result, ensure_ascii=False)
        violations = check_forbidden(text)
        self.assertEqual(len(violations), 0)

    def test_35_result_has_five_cards(self):
        cards = self.result.get("cards", [])
        self.assertEqual(len(cards), 5, f"Must have 5 cards, got {len(cards)}")

    def test_36_result_five_card_families_present(self):
        cards = self.result.get("cards", [])
        families = {c.get("card_family") for c in cards}
        expected = set(FIVE_CARD_FAMILIES)
        self.assertEqual(families, expected)

    def test_37_result_decisions_in_allowed_set(self):
        cards = self.result.get("cards", [])
        for c in cards:
            dec = c.get("operator_decision", "")
            self.assertIn(dec, ALLOWED_DECISIONS,
                         f"{c['card_family']}: '{dec}' not in allowed set")

    def test_38_result_whale_is_manual_required(self):
        cards = self.result.get("cards", [])
        whale = [c for c in cards if c["card_family"] == "whale_position_alert"]
        self.assertEqual(len(whale), 1, "whale_position_alert card missing")
        self.assertEqual(whale[0]["operator_decision"], "manual_required",
                        "whale_position_alert MUST be manual_required")

    def test_39_result_liquidation_not_accepted(self):
        cards = self.result.get("cards", [])
        liq = [c for c in cards if c["card_family"] == "liquidation_pressure"]
        self.assertEqual(len(liq), 1, "liquidation_pressure card missing")
        self.assertNotEqual(liq[0]["operator_decision"], "accept",
                           "liquidation_pressure MUST NOT be accept")

    def test_3a_result_news_observation_only(self):
        cards = self.result.get("cards", [])
        news = [c for c in cards if c["card_family"] == "news_event_market_impact"]
        self.assertEqual(len(news), 1)
        self.assertTrue(news[0].get("observation_only", False),
                       "news_event_market_impact must be observation_only=true")
        self.assertTrue(news[0].get("not_causal_proof", False),
                       "news_event_market_impact must be not_causal_proof=true")

    def test_3b_result_has_decision_table(self):
        dt = self.result.get("decision_table", {})
        self.assertIn("table", dt)
        self.assertEqual(len(dt["table"]), 5)

    def test_3c_result_has_no_send_preview(self):
        nsp = self.result.get("no_send_preview", {})
        self.assertFalse(nsp.get("telegram_send", True),
                        "telegram_send must be false")
        self.assertFalse(nsp.get("x_twitter_send", True),
                        "x_twitter_send must be false")
        self.assertFalse(nsp.get("production_send", True),
                        "production_send must be false")
        self.assertFalse(nsp.get("daemon_or_loop_started", True),
                        "daemon_or_loop_started must be false")

    def test_3d_result_production_readiness_false(self):
        pr = self.result.get("production_readiness", {})
        self.assertFalse(pr.get("production_ready", True))
        self.assertEqual(pr.get("production_readiness_score"), "0/5")

    def test_3e_result_contract_validation_passes(self):
        cv = self.result.get("contract_validation", {})
        self.assertTrue(cv.get("all_passed", False),
                       "Contract validation must pass all checks")

    def test_3f_result_mode_is_local_only(self):
        self.assertEqual(self.result.get("mode"), "local_only_no_send")

    def test_3g_result_source_is_v118c(self):
        self.assertIn("v118C", self.result.get("source", ""))

    def test_3h_result_safety_all_false(self):
        safety = self.result.get("safety", {})
        self.assertFalse(safety.get("external_api_called", True))
        self.assertFalse(safety.get("tg_sent_this_run", True))
        self.assertEqual(safety.get("tg_message_count_this_run", 999), 0)
        self.assertFalse(safety.get("production_send", True))
        self.assertFalse(safety.get("ai_model_called", True))
        self.assertFalse(safety.get("daemon_or_loop_started", True))
        self.assertFalse(safety.get("files_deleted", True))
        self.assertFalse(safety.get("credentials_printed", True))
        self.assertFalse(safety.get("x_twitter_send", True))
        self.assertFalse(safety.get("binance_called", True))
        self.assertFalse(safety.get("rss_called", True))

    def test_3i_result_each_card_has_required_fields(self):
        required = [
            "card_family", "v118c_status", "operator_decision",
            "evidence_summary", "reason", "publishability",
            "next_operator_action",
        ]
        cards = self.result.get("cards", [])
        for c in cards:
            for field in required:
                self.assertIn(field, c,
                             f"{c.get('card_family', '?')} missing '{field}'")

    def test_3j_result_no_deterministic_causal_language(self):
        text = json.dumps(self.result, ensure_ascii=False).lower()
        for marker in ["will cause", "guaranteed to", "definitely", "certainly"]:
            self.assertNotIn(marker, text)


class TestV118DReviewPack(unittest.TestCase):
    """Test v118D operator review pack markdown."""

    @classmethod
    def setUpClass(cls):
        if V118D_REVIEW_PACK.exists():
            cls.content = V118D_REVIEW_PACK.read_text(encoding="utf-8")
        else:
            cls.content = ""

    def test_40_review_pack_exists(self):
        self.assertTrue(V118D_REVIEW_PACK.exists(), "Review pack not found")

    def test_41_review_pack_no_forbidden_patterns(self):
        violations = check_forbidden(self.content)
        self.assertEqual(len(violations), 0)

    def test_42_review_pack_mentions_all_five_families(self):
        for cf in FIVE_CARD_FAMILIES:
            self.assertIn(cf, self.content,
                         f"Review pack must mention {cf}")

    def test_43_review_pack_has_accept_watch_reject_manual(self):
        self.assertIn("ACCEPT", self.content)
        self.assertIn("WATCH", self.content)
        self.assertIn("REJECT", self.content)
        self.assertIn("MANUAL", self.content)

    def test_44_review_pack_has_production_readiness(self):
        self.assertIn("0/5", self.content)
        self.assertIn("NOT FOR LIVE USE", self.content)

    def test_45_review_pack_has_no_send_confirmation(self):
        self.assertIn("No-Send", self.content)

    def test_46_review_pack_has_contract_validation(self):
        self.assertIn("Contract Validation", self.content)

    def test_47_review_pack_has_evidence_summaries(self):
        self.assertIn("Evidence Summary", self.content)

    def test_48_review_pack_has_next_operator_action(self):
        self.assertIn("Next Operator Action", self.content)


class TestV118DDecisionTable(unittest.TestCase):
    """Test v118D operator decision table markdown."""

    @classmethod
    def setUpClass(cls):
        if V118D_DECISION_TABLE.exists():
            cls.content = V118D_DECISION_TABLE.read_text(encoding="utf-8")
        else:
            cls.content = ""

    def test_50_decision_table_exists(self):
        self.assertTrue(V118D_DECISION_TABLE.exists(), "Decision table not found")

    def test_51_decision_table_no_forbidden_patterns(self):
        violations = check_forbidden(self.content)
        self.assertEqual(len(violations), 0)

    def test_52_decision_table_has_all_five_rows(self):
        """Each of the 5 card families should appear in a table row."""
        for cf in FIVE_CARD_FAMILIES:
            self.assertIn(cf, self.content,
                         f"Decision table must include {cf}")

    def test_53_decision_table_has_whale_manual(self):
        self.assertIn("MANUAL", self.content)

    def test_54_decision_table_has_liq_reject(self):
        self.assertIn("REJECT", self.content)

    def test_55_decision_table_has_key_constraints_section(self):
        self.assertIn("Key Constraints", self.content)


class TestV118DNoSendPreview(unittest.TestCase):
    """Test v118D no-send preview markdown."""

    @classmethod
    def setUpClass(cls):
        if V118D_NO_SEND_PREVIEW.exists():
            cls.content = V118D_NO_SEND_PREVIEW.read_text(encoding="utf-8")
        else:
            cls.content = ""

    def test_60_no_send_preview_exists(self):
        self.assertTrue(V118D_NO_SEND_PREVIEW.exists(), "No-send preview not found")

    def test_61_no_send_preview_no_forbidden_patterns(self):
        violations = check_forbidden(self.content)
        self.assertEqual(len(violations), 0)

    def test_62_telegram_send_false_explicit(self):
        self.assertIn("telegram_send=False", self.content)

    def test_63_x_twitter_send_false_explicit(self):
        self.assertIn("x_twitter_send=False", self.content)

    def test_64_production_send_false_explicit(self):
        self.assertIn("production_send=False", self.content)

    def test_65_daemon_loop_false_explicit(self):
        self.assertIn("daemon_or_loop_started=False", self.content)

    def test_66_binance_not_called(self):
        self.assertIn("Binance API called", self.content)
        self.assertIn("False", self.content)

    def test_67_tg_not_sent(self):
        self.assertIn("Telegram message sent", self.content)

    def test_68_all_send_blocked(self):
        self.assertIn("ALL BLOCKED", self.content)


class TestV118DHandoff(unittest.TestCase):
    """Test v118D local-only handoff markdown."""

    @classmethod
    def setUpClass(cls):
        if V118D_HANDOFF.exists():
            cls.content = V118D_HANDOFF.read_text(encoding="utf-8")
        else:
            cls.content = ""

    def test_70_handoff_exists(self):
        self.assertTrue(V118D_HANDOFF.exists(), "Handoff not found")

    def test_71_handoff_no_forbidden_patterns(self):
        violations = check_forbidden(self.content)
        self.assertEqual(len(violations), 0)

    def test_72_handoff_mentions_local_only(self):
        self.assertIn("local_only_handoff", self.content.lower().replace(" ", "_"))

    def test_73_handoff_mentions_no_send(self):
        self.assertIn("no-send", self.content.lower())

    def test_74_handoff_has_decision_summary(self):
        self.assertIn("Decision Summary", self.content)

    def test_75_handoff_has_production_false(self):
        self.assertIn("0/5", self.content)


class TestV118DIntegration(unittest.TestCase):
    """Integration tests for v118D — import and check core functions."""

    def test_80_runner_importable(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location("v118d_runner", V118D_RUNNER)
        self.assertIsNotNone(spec, "Failed to create module spec for v118D runner")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

    def test_81_make_operator_decision_returns_valid(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location("v118d_runner", V118D_RUNNER)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        make_decision = module.make_operator_decision

        # Test whale → manual_required
        result = make_decision({
            "card_family": "whale_position_alert",
            "status": "manual_required",
            "send_eligible": False,
            "evidence_status": "manual_attribution_evidence_required",
            "gate_reason": "manual evidence required",
            "top_signal": "4 addresses tracked",
            "risk_note": "requires manual attribution",
        })
        self.assertEqual(result["operator_decision"], "manual_required")

        # Test liquidation → reject (blocked)
        result = make_decision({
            "card_family": "liquidation_pressure",
            "status": "blocked",
            "send_eligible": False,
            "evidence_status": "blocked_by_gate_threshold",
            "gate_reason": "calm market",
            "top_signal": "no active liquidation signal",
            "risk_note": "",
        })
        self.assertEqual(result["operator_decision"], "reject")

        # Test news → watch (observation_only)
        result = make_decision({
            "card_family": "news_event_market_impact",
            "status": "active",
            "send_eligible": True,
            "evidence_status": "clean",
            "observation_only": True,
            "not_causal_proof": True,
            "gate_reason": "high intensity event accepted",
            "top_signal": "[high] other: test event",
            "risk_note": "rule_based, not causal",
        })
        self.assertEqual(result["operator_decision"], "watch")
        self.assertTrue(result["observation_only"])
        self.assertTrue(result["not_causal_proof"])

        # Test multi_asset → accept (active + eligible)
        result = make_decision({
            "card_family": "multi_asset_market_sync",
            "status": "active",
            "send_eligible": True,
            "evidence_status": "clean",
            "gate_reason": "multi-asset data available",
            "top_signal": "BTC: -0.44%, ETH: -4.52%",
            "risk_note": "",
        })
        self.assertEqual(result["operator_decision"], "accept")

    def test_82_validate_contract_passes(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location("v118d_runner", V118D_RUNNER)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        test_decisions = [
            {
                "card_family": "multi_asset_market_sync",
                "operator_decision": "accept",
                "observation_only": False,
                "not_causal_proof": False,
            },
            {
                "card_family": "price_oi_volume_anomaly",
                "operator_decision": "reject",
                "observation_only": False,
                "not_causal_proof": False,
            },
            {
                "card_family": "news_event_market_impact",
                "operator_decision": "watch",
                "observation_only": True,
                "not_causal_proof": True,
            },
            {
                "card_family": "liquidation_pressure",
                "operator_decision": "reject",
                "observation_only": False,
                "not_causal_proof": False,
            },
            {
                "card_family": "whale_position_alert",
                "operator_decision": "manual_required",
                "observation_only": False,
                "not_causal_proof": False,
            },
        ]

        validation = module.validate_contract(test_decisions)
        self.assertTrue(validation["all_passed"],
                       f"Contract validation failed: {validation['checks']}")

    def test_83_build_no_send_preview(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location("v118d_runner", V118D_RUNNER)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        nsp = module.build_no_send_preview([{"card_family": "test"}] * 5)
        self.assertFalse(nsp["telegram_send"])
        self.assertFalse(nsp["x_twitter_send"])
        self.assertFalse(nsp["production_send"])
        self.assertFalse(nsp["daemon_or_loop_started"])
        self.assertFalse(nsp["external_api_called"])
        self.assertFalse(nsp["ai_model_called"])

    def test_84_evaluate_production_readiness(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location("v118d_runner", V118D_RUNNER)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        pr = module.evaluate_production_readiness([])
        self.assertFalse(pr["production_ready"])
        self.assertEqual(pr["production_readiness_score"], "0/5")
        self.assertEqual(len(pr["criteria"]), 5)


class TestV118DRegressionFilesExist(unittest.TestCase):
    """Test that v118D did not delete historical output files."""

    def test_90_v118c_files_exist(self):
        missing = [str(f) for f in V118C_OUTPUT_FILES if not f.exists()]
        self.assertEqual(len(missing), 0, f"v118C files deleted: {missing}")

    def test_91_v118b_files_exist(self):
        missing = [str(f) for f in V118B_OUTPUT_FILES if not f.exists()]
        self.assertEqual(len(missing), 0, f"v118B files deleted: {missing}")

    def test_92_v118a_files_exist(self):
        missing = [str(f) for f in V118A_OUTPUT_FILES if not f.exists()]
        self.assertEqual(len(missing), 0, f"v118A files deleted: {missing}")

    def test_93_v117_files_exist(self):
        missing = [str(f) for f in V117_OUTPUT_FILES if not f.exists()]
        self.assertEqual(len(missing), 0, f"v117 files deleted: {missing}")

    def test_94_v116n_files_exist(self):
        missing = [str(f) for f in V116N_FILES if not f.exists()]
        self.assertEqual(len(missing), 0, f"v116N files deleted: {missing}")


class TestV118DCompleteLeakAudit(unittest.TestCase):
    """Comprehensive audit of all v118D outputs for secret leaks."""

    def test_a0_all_outputs_no_raw_token(self):
        for fpath in ALL_V118D_OUTPUT_FILES:
            if not fpath.exists():
                continue
            if fpath.suffix == ".json":
                data = load_json(fpath)
                text = json.dumps(data, ensure_ascii=False)
                self.assertIsNone(RAW_TOKEN_PATTERN.search(text),
                                f"{fpath.name}: raw token pattern")
            elif fpath.suffix == ".md":
                text = fpath.read_text(encoding="utf-8")
                self.assertIsNone(RAW_TOKEN_PATTERN.search(text),
                                f"{fpath.name}: raw token pattern")

    def test_a1_all_outputs_no_raw_chat_id(self):
        for fpath in ALL_V118D_OUTPUT_FILES:
            if not fpath.exists():
                continue
            if fpath.suffix == ".json":
                data = load_json(fpath)
                text = json.dumps(data, ensure_ascii=False)
                self.assertIsNone(RAW_CHAT_ID_PATTERN.search(text),
                                f"{fpath.name}: raw chat_id pattern")
            elif fpath.suffix == ".md":
                text = fpath.read_text(encoding="utf-8")
                self.assertIsNone(RAW_CHAT_ID_PATTERN.search(text),
                                f"{fpath.name}: raw chat_id pattern")

    def test_a2_all_outputs_no_raw_message_id(self):
        for fpath in ALL_V118D_OUTPUT_FILES:
            if not fpath.exists():
                continue
            if fpath.suffix == ".json":
                data = load_json(fpath)
                text = json.dumps(data, ensure_ascii=False)
                self.assertIsNone(RAW_MESSAGE_ID_PATTERN.search(text),
                                f"{fpath.name}: raw message_id pattern")
            elif fpath.suffix == ".md":
                text = fpath.read_text(encoding="utf-8")
                self.assertIsNone(RAW_MESSAGE_ID_PATTERN.search(text),
                                f"{fpath.name}: raw message_id pattern")


class TestV118DNoExternalCallProof(unittest.TestCase):
    """Prove that v118D runner makes zero external calls."""

    def test_b0_runner_has_no_network_imports(self):
        source = V118D_RUNNER.read_text(encoding="utf-8")
        # No http client imports
        self.assertNotIn("import requests", source)
        self.assertNotIn("from requests", source)
        self.assertNotIn("import urllib.request", source)
        self.assertNotIn("from urllib", source)
        self.assertNotIn("import http.client", source)
        self.assertNotIn("import socket", source)
        # No external API library imports
        self.assertNotIn("import telegram", source)
        self.assertNotIn("from telegram", source)
        self.assertNotIn("import openai", source)
        self.assertNotIn("import anthropic", source)

    def test_b1_runner_source_is_v118c_only(self):
        """Confirm runner reads v118C file only, no other data source."""
        source = V118D_RUNNER.read_text(encoding="utf-8")
        # Should reference reading v118C result
        self.assertIn("v118c_five_card_snapshot_result", source)
        # Should NOT reference any external URL
        self.assertNotIn("https://api.binance.com", source)
        self.assertNotIn("https://fapi.binance.com", source)
        self.assertNotIn("api.telegram.org", source)


if __name__ == "__main__":
    unittest.main(verbosity=2)
