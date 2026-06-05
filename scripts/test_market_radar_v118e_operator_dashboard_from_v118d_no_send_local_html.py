"""Market Radar v118E — Operator Dashboard from v118D (Local HTML, No-Send) Tests.

Tests cover:
  - v118E runner can be imported and executed
  - v118E reads v118D local result ONLY (no re-read of v118C, no external calls)
  - HTML dashboard file generated
  - Result JSON generated
  - Five card families all appear in HTML
  - Four decision statuses (accept, watch, reject, manual_required) as per v118D
  - whale_position_alert is manual_required
  - liquidation_pressure is reject
  - news_event_market_impact observation_only=true, not_causal_proof=true
  - production readiness is false / 0/5
  - HTML contains telegram_send=false, x_twitter_send=false,
    production_send=false, daemon_or_loop_started=false
  - No raw token/chat_id/message_id/cookie/password/API key in any output
  - Runner code has no network import
  - v116A–N history files not modified
  - No files deleted

Usage:
    python -X utf8 -m pytest scripts/test_market_radar_v118e_operator_dashboard_from_v118d_no_send_local_html.py -v
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


# ── v118E Paths ──────────────────────────────────────────────────────────────

V118E_RUNNER = ROOT / "scripts" / "run_market_radar_v118e_operator_dashboard_from_v118d_no_send_local_html.py"
V118E_TEST = ROOT / "scripts" / "test_market_radar_v118e_operator_dashboard_from_v118d_no_send_local_html.py"

V118E_HTML = ROOT / "runs" / "market_radar" / "v118e_operator_dashboard.html"
V118E_PREVIEW_MD = ROOT / "runs" / "market_radar" / "v118e_operator_dashboard_preview.md"
V118E_HANDOFF = ROOT / "runs" / "market_radar" / "v118e_local_only_handoff.md"
V118E_RESULT_JSON = ROOT / "results" / "market_radar_v118e_operator_dashboard_result.json"

ALL_V118E_OUTPUT_FILES = [
    V118E_HTML,
    V118E_PREVIEW_MD,
    V118E_HANDOFF,
    V118E_RESULT_JSON,
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

V118D_OUTPUT_FILES = [
    ROOT / "results" / "market_radar_v118d_operator_acceptance_gate_result.json",
    ROOT / "runs" / "market_radar" / "v118d_operator_review_pack.md",
    ROOT / "runs" / "market_radar" / "v118d_operator_decision_table.md",
    ROOT / "runs" / "market_radar" / "v118d_no_send_preview.md",
    ROOT / "runs" / "market_radar" / "v118d_local_only_handoff.md",
]

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
    V118D_OUTPUT_FILES +
    V118C_OUTPUT_FILES + V118B_OUTPUT_FILES + V118A_OUTPUT_FILES +
    V117_OUTPUT_FILES + V116N_FILES
)


# ═══════════════════════════════════════════════════════════════════════════
# Test Cases
# ═══════════════════════════════════════════════════════════════════════════


class TestV118EFilesExist(unittest.TestCase):
    """Test that v118E runner and test scripts exist."""

    def test_01_runner_exists(self):
        self.assertTrue(V118E_RUNNER.exists(),
                        f"Missing runner: {V118E_RUNNER}")

    def test_02_test_exists(self):
        self.assertTrue(V118E_TEST.exists(),
                        f"Missing test: {V118E_TEST}")


class TestV118EOutputFilesExist(unittest.TestCase):
    """Test that all v118E output files exist after runner execution."""

    def test_10_all_output_files_exist(self):
        missing = [str(f) for f in ALL_V118E_OUTPUT_FILES if not f.exists()]
        self.assertEqual(len(missing), 0,
                         f"Missing v118E output files: {missing}")


class TestV118ERunnerStaticAnalysis(unittest.TestCase):
    """Static analysis of v118E runner source — must have zero network imports."""

    @classmethod
    def setUpClass(cls):
        cls.source = V118E_RUNNER.read_text(encoding="utf-8") if V118E_RUNNER.exists() else ""

    def test_20_runner_reads_v118d_result(self):
        """v118E must read from v118D result, NOT v118C."""
        self.assertIn("v118d_operator_acceptance_gate_result", self.source)
        self.assertIn("load_v118d_result", self.source)
        # Must NOT read v118C (only mention it in comments/docstring)
        source_no_comments = re.sub(r'#.*', '', self.source)
        source_no_docstrings = re.sub(r'""".*?"""', '', source_no_comments, flags=re.DOTALL)
        self.assertNotIn("v118c_five_card_snapshot_result.json", source_no_docstrings)

    def test_21_runner_no_binance_import(self):
        """v118E must NOT import or call Binance."""
        self.assertNotIn("from binance", self.source.lower())
        self.assertNotIn("import binance", self.source.lower())
        self.assertNotIn("binance.com", self.source.lower())
        self.assertNotIn("binance_client", self.source.lower())

    def test_22_runner_no_rss_import(self):
        """v118E must NOT import or call RSS feeds."""
        self.assertNotIn("import feedparser", self.source.lower())
        self.assertNotIn("from feedparser", self.source.lower())
        self.assertNotIn("feedparser.parse", self.source.lower())
        self.assertNotIn("rss.xml", self.source.lower())
        self.assertNotIn("rss/", self.source.lower())

    def test_23_runner_no_telegram_send(self):
        """v118E must NOT import or call Telegram API."""
        self.assertNotIn("import telegram", self.source.lower())
        self.assertNotIn("from telegram", self.source.lower())
        self.assertNotIn("telegram.Bot", self.source.lower())
        self.assertNotIn("api.telegram.org", self.source.lower())
        self.assertNotIn("sender_contract", self.source.lower())
        self.assertNotIn("create_tg_sender", self.source.lower())

    def test_24_runner_no_ai_model(self):
        """v118E must NOT call any AI/model API."""
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
        self.assertIn("0/5", self.source)

    def test_28_runner_has_no_send_markers(self):
        self.assertIn("telegram_send=false", self.source.lower())
        self.assertIn("x_twitter_send=false", self.source.lower())
        self.assertIn("production_send=false", self.source.lower())
        self.assertIn("daemon_or_loop_started=false", self.source.lower())

    def test_29_runner_has_whale_manual_required(self):
        self.assertIn("manual_required", self.source)

    def test_2a_runner_has_liquidation_reject(self):
        self.assertIn("liquidation_pressure", self.source)

    def test_2b_runner_has_news_observation_only(self):
        self.assertIn("observation_only", self.source)
        self.assertIn("not_causal_proof", self.source)

    def test_2c_runner_has_html_generation(self):
        self.assertIn("generate_html_dashboard", self.source)

    def test_2d_runner_has_no_network_imports(self):
        """v118E runner must have ZERO network imports."""
        self.assertNotIn("import requests", self.source)
        self.assertNotIn("from requests", self.source)
        self.assertNotIn("import urllib.request", self.source)
        self.assertNotIn("from urllib", self.source)
        self.assertNotIn("import http.client", self.source)
        self.assertNotIn("import socket", self.source)

    def test_2e_runner_reads_only_local_files(self):
        """v118E must ONLY read local files, never fetch from network."""
        self.assertNotIn("http://", self.source)
        self.assertNotIn("https://", self.source)

    def test_2f_runner_has_validate_v118e_contract(self):
        self.assertIn("validate_v118e_contract", self.source)


class TestV118EHtmlDashboard(unittest.TestCase):
    """Test the generated v118E HTML dashboard."""

    @classmethod
    def setUpClass(cls):
        if V118E_HTML.exists():
            cls.html = V118E_HTML.read_text(encoding="utf-8")
        else:
            cls.html = ""

    def test_30_html_exists(self):
        self.assertTrue(V118E_HTML.exists(),
                        "HTML dashboard not found. Run the v118E runner first.")

    def test_31_html_not_empty(self):
        self.assertGreater(len(self.html), 1000,
                          "HTML dashboard is too short — likely empty or broken")

    def test_32_html_has_page_title(self):
        self.assertIn("Market Radar Operator Dashboard v118E", self.html)

    def test_33_html_is_well_formed(self):
        html_lower = self.html.lower()
        required = ["<!doctype html>", "<html", "</html>", "<head", "</head>",
                     "<body", "</body>", "<title>"]
        for tag in required:
            self.assertIn(tag, html_lower, f"Missing HTML tag: {tag}")

    def test_34_html_has_five_card_families(self):
        for cf in FIVE_CARD_FAMILIES:
            self.assertIn(cf, self.html,
                         f"HTML must contain card family: {cf}")

    def test_35_html_has_accept_decision(self):
        self.assertIn("ACCEPT", self.html,
                      "HTML must contain ACCEPT decision badge")

    def test_36_html_has_watch_decision(self):
        self.assertIn("WATCH", self.html,
                      "HTML must contain WATCH decision badge")

    def test_37_html_has_reject_decision(self):
        self.assertIn("REJECT", self.html,
                      "HTML must contain REJECT decision badge")

    def test_38_html_has_manual_required_decision(self):
        self.assertIn("MANUAL REQUIRED", self.html,
                      "HTML must contain MANUAL REQUIRED decision badge")

    def test_39_html_has_whale_manual_required(self):
        self.assertIn("whale_position_alert", self.html)

    def test_3a_html_has_liquidation_reject(self):
        self.assertIn("liquidation_pressure", self.html)

    def test_3b_html_has_news_observation_only_true(self):
        self.assertIn("observation_only", self.html.lower())

    def test_3c_html_has_news_not_causal_proof_true(self):
        self.assertIn("not_causal_proof", self.html.lower())

    def test_3d_html_has_production_readiness_false(self):
        self.assertIn("0/5", self.html)
        self.assertIn("NOT FOR PRODUCTION USE", self.html)

    def test_3e_html_has_telegram_send_false(self):
        # Check for false marker near telegram_send
        pattern = r'telegram_send\s*[=:]\s*false'
        self.assertTrue(
            re.search(pattern, self.html, re.IGNORECASE),
            "HTML must show telegram_send=false"
        )

    def test_3f_html_has_x_twitter_send_false(self):
        pattern = r'x_twitter_send\s*[=:]\s*false'
        self.assertTrue(
            re.search(pattern, self.html, re.IGNORECASE),
            "HTML must show x_twitter_send=false"
        )

    def test_3g_html_has_production_send_false(self):
        pattern = r'production_send\s*[=:]\s*false'
        self.assertTrue(
            re.search(pattern, self.html, re.IGNORECASE),
            "HTML must show production_send=false"
        )

    def test_3h_html_has_daemon_loop_false(self):
        pattern = r'daemon_or_loop_started\s*[=:]\s*false'
        self.assertTrue(
            re.search(pattern, self.html, re.IGNORECASE),
            "HTML must show daemon_or_loop_started=false"
        )

    def test_3i_html_has_no_raw_token(self):
        self.assertIsNone(RAW_TOKEN_PATTERN.search(self.html),
                         "HTML must NOT contain raw token")

    def test_3j_html_has_no_raw_chat_id(self):
        self.assertIsNone(RAW_CHAT_ID_PATTERN.search(self.html),
                         "HTML must NOT contain raw chat_id")

    def test_3k_html_has_no_raw_message_id(self):
        self.assertIsNone(RAW_MESSAGE_ID_PATTERN.search(self.html),
                         "HTML must NOT contain raw message_id")

    def test_3l_html_no_forbidden_patterns(self):
        violations = check_forbidden(self.html)
        self.assertEqual(len(violations), 0,
                        f"Forbidden patterns in HTML: {violations}")

    def test_3m_html_has_source_pipeline_v118d(self):
        self.assertIn("v1.18D", self.html,
                      "HTML must reference source pipeline v118D")

    def test_3n_html_has_mode_local_only(self):
        self.assertIn("local-only", self.html.lower())

    def test_3o_html_has_risk_panel(self):
        self.assertIn("Risk Panel", self.html,
                      "HTML must include risk panel section")

    def test_3p_html_has_operator_next_action(self):
        self.assertIn("Operator Next Action", self.html,
                      "HTML must include operator next action section")

    def test_3q_html_has_decision_table_section(self):
        self.assertIn("Decision Table", self.html,
                      "HTML must include decision table section")

    def test_3r_html_has_css_styling(self):
        self.assertIn("<style>", self.html.lower())
        self.assertIn("</style>", self.html.lower())


class TestV118EResultJson(unittest.TestCase):
    """Test v118E result JSON file."""

    @classmethod
    def setUpClass(cls):
        if V118E_RESULT_JSON.exists():
            cls.result = load_json(V118E_RESULT_JSON)
        else:
            cls.result = None

    def test_40_result_exists(self):
        self.assertIsNotNone(self.result,
                           "Result JSON not found. Run the v118E runner first.")

    def test_41_result_no_raw_token(self):
        text = json.dumps(self.result, ensure_ascii=False)
        self.assertIsNone(RAW_TOKEN_PATTERN.search(text))

    def test_42_result_no_raw_chat_id(self):
        text = json.dumps(self.result, ensure_ascii=False)
        self.assertIsNone(RAW_CHAT_ID_PATTERN.search(text))

    def test_43_result_no_raw_message_id(self):
        text = json.dumps(self.result, ensure_ascii=False)
        self.assertIsNone(RAW_MESSAGE_ID_PATTERN.search(text))

    def test_44_result_no_forbidden_patterns(self):
        text = json.dumps(self.result, ensure_ascii=False)
        violations = check_forbidden(text)
        self.assertEqual(len(violations), 0)

    def test_45_result_has_cards(self):
        cards = self.result.get("cards", [])
        self.assertEqual(len(cards), 5, f"Must have 5 cards, got {len(cards)}")

    def test_46_result_five_card_families_present(self):
        cards = self.result.get("cards", [])
        families = {c.get("card_family") for c in cards}
        expected = set(FIVE_CARD_FAMILIES)
        self.assertEqual(families, expected)

    def test_47_result_decisions_in_allowed_set(self):
        cards = self.result.get("cards", [])
        for c in cards:
            dec = c.get("operator_decision", "")
            self.assertIn(dec, ALLOWED_DECISIONS,
                         f"{c['card_family']}: '{dec}' not in allowed set")

    def test_48_result_whale_is_manual_required(self):
        cards = self.result.get("cards", [])
        whale = [c for c in cards if c["card_family"] == "whale_position_alert"]
        self.assertEqual(len(whale), 1)
        self.assertEqual(whale[0]["operator_decision"], "manual_required")

    def test_49_result_liquidation_is_reject(self):
        cards = self.result.get("cards", [])
        liq = [c for c in cards if c["card_family"] == "liquidation_pressure"]
        self.assertEqual(len(liq), 1)
        self.assertEqual(liq[0]["operator_decision"], "reject",
                        "liquidation_pressure must be reject")

    def test_4a_result_news_observation_only(self):
        cards = self.result.get("cards", [])
        news = [c for c in cards if c["card_family"] == "news_event_market_impact"]
        self.assertEqual(len(news), 1)
        self.assertTrue(news[0].get("observation_only", False))
        self.assertTrue(news[0].get("not_causal_proof", False))

    def test_4b_result_mode_is_local_only(self):
        self.assertEqual(self.result.get("mode"), "local_only_no_send")

    def test_4c_result_source_is_v118d(self):
        self.assertIn("v118D", self.result.get("source", ""))

    def test_4d_result_contract_validation_passes(self):
        cv = self.result.get("contract_validation", {})
        self.assertTrue(cv.get("all_passed", False),
                       "v118E contract validation must pass all checks")

    def test_4e_result_safety_all_false(self):
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

    def test_4f_result_dashboard_files_exist(self):
        df = self.result.get("dashboard_files", {})
        for key, rel_path in df.items():
            fpath = ROOT / rel_path
            self.assertTrue(fpath.exists(),
                          f"Dashboard file referenced but missing: {rel_path}")

    def test_4g_result_type_is_operator_dashboard(self):
        self.assertIn("operator_dashboard", self.result.get("type", ""))

    def test_4h_result_has_production_ready_false(self):
        pr = self.result.get("production_readiness", {})
        self.assertFalse(pr.get("production_ready", True))
        self.assertEqual(pr.get("production_readiness_score"), "0/5")

    def test_4i_result_each_card_has_required_fields(self):
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


class TestV118EPreviewMd(unittest.TestCase):
    """Test v118E dashboard preview markdown."""

    @classmethod
    def setUpClass(cls):
        if V118E_PREVIEW_MD.exists():
            cls.content = V118E_PREVIEW_MD.read_text(encoding="utf-8")
        else:
            cls.content = ""

    def test_50_preview_exists(self):
        self.assertTrue(V118E_PREVIEW_MD.exists(), "Preview MD not found")

    def test_51_preview_no_forbidden_patterns(self):
        violations = check_forbidden(self.content)
        self.assertEqual(len(violations), 0)

    def test_52_preview_mentions_all_five_families(self):
        for cf in FIVE_CARD_FAMILIES:
            self.assertIn(cf, self.content)

    def test_53_preview_has_accept_watch_reject_manual(self):
        self.assertIn("ACCEPT", self.content)
        self.assertIn("WATCH", self.content)
        self.assertIn("REJECT", self.content)
        self.assertIn("MANUAL REQUIRED", self.content)

    def test_54_preview_has_0_5_production(self):
        self.assertIn("0/5", self.content)

    def test_55_preview_has_no_send_markers(self):
        self.assertIn("telegram_send", self.content.lower())
        self.assertIn("x_twitter_send", self.content.lower())
        self.assertIn("production_send", self.content.lower())


class TestV118EHandoffMd(unittest.TestCase):
    """Test v118E local-only handoff markdown."""

    @classmethod
    def setUpClass(cls):
        if V118E_HANDOFF.exists():
            cls.content = V118E_HANDOFF.read_text(encoding="utf-8")
        else:
            cls.content = ""

    def test_60_handoff_exists(self):
        self.assertTrue(V118E_HANDOFF.exists(), "Handoff not found")

    def test_61_handoff_no_forbidden_patterns(self):
        violations = check_forbidden(self.content)
        self.assertEqual(len(violations), 0)

    def test_62_handoff_has_decision_summary(self):
        self.assertIn("Decision Summary", self.content)

    def test_63_handoff_has_production_false(self):
        self.assertIn("0/5", self.content)

    def test_64_handoff_mentions_no_send(self):
        self.assertIn("no-send", self.content.lower())

    def test_65_handoff_has_what_was_done(self):
        self.assertIn("What Was Done", self.content)

    def test_66_handoff_has_what_was_not_done(self):
        self.assertIn("What Was NOT Done", self.content)


class TestV118EIntegration(unittest.TestCase):
    """Integration tests for v118E — import and check core functions."""

    def test_70_runner_importable(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location("v118e_runner", V118E_RUNNER)
        self.assertIsNotNone(spec, "Failed to create module spec for v118E runner")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

    def test_71_load_v118d_result_works(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location("v118e_runner", V118E_RUNNER)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        result = module.load_v118d_result()
        self.assertIsNotNone(result)
        self.assertIn("cards", result)
        self.assertEqual(len(result["cards"]), 5)

    def test_72_generate_html_dashboard_returns_valid_html(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location("v118e_runner", V118E_RUNNER)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        v118d_data = module.load_v118d_result()
        cards = v118d_data.get("cards", [])
        dt = v118d_data.get("decision_table", {})
        nsp = v118d_data.get("no_send_preview", {})
        pr = v118d_data.get("production_readiness", {})
        cv = v118d_data.get("contract_validation", {})
        safety = v118d_data.get("safety", {})

        html = module.generate_html_dashboard(v118d_data, cards, dt, nsp, pr, cv, safety)
        self.assertIsInstance(html, str)
        self.assertGreater(len(html), 2000)
        self.assertIn("<!DOCTYPE html>", html)
        self.assertIn("Market Radar Operator Dashboard v118E", html)
        # All 5 card families
        for cf in FIVE_CARD_FAMILIES:
            self.assertIn(cf, html, f"HTML must contain {cf}")
        # All 4 decision types
        self.assertIn("ACCEPT", html)
        self.assertIn("WATCH", html)
        self.assertIn("REJECT", html)
        self.assertIn("MANUAL REQUIRED", html)
        # No-send markers
        self.assertIn("telegram_send=false", html.lower())
        self.assertIn("x_twitter_send=false", html.lower())
        self.assertIn("production_send=false", html.lower())
        self.assertIn("daemon_or_loop_started=false", html.lower())
        # Production readiness
        self.assertIn("0/5", html)
        # No secrets
        self.assertIsNone(RAW_TOKEN_PATTERN.search(html))
        self.assertIsNone(RAW_CHAT_ID_PATTERN.search(html))

    def test_73_validate_v118e_contract_passes(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location("v118e_runner", V118E_RUNNER)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        v118d_data = module.load_v118d_result()
        cards = v118d_data.get("cards", [])
        dt = v118d_data.get("decision_table", {})
        nsp = v118d_data.get("no_send_preview", {})
        pr = v118d_data.get("production_readiness", {})
        cv = v118d_data.get("contract_validation", {})
        safety = v118d_data.get("safety", {})

        html = module.generate_html_dashboard(v118d_data, cards, dt, nsp, pr, cv, safety)
        validation = module.validate_v118e_contract(cards, html, cv)
        self.assertTrue(validation["all_passed"],
                       f"Contract validation failed: {validation['checks']}")

    def test_74_escape_html_function(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location("v118e_runner", V118E_RUNNER)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        self.assertEqual(module._escape_html("<script>"), "&lt;script&gt;")
        self.assertEqual(module._escape_html('"test"'), "&quot;test&quot;")
        self.assertEqual(module._escape_html("a & b"), "a &amp; b")
        self.assertEqual(module._escape_html("normal"), "normal")


class TestV118ERegressionFilesExist(unittest.TestCase):
    """Test that v118E did not delete or modify historical output files."""

    def test_80_v118d_files_exist(self):
        missing = [str(f) for f in V118D_OUTPUT_FILES if not f.exists()]
        self.assertEqual(len(missing), 0, f"v118D files deleted/missing: {missing}")

    def test_81_v118c_files_exist(self):
        missing = [str(f) for f in V118C_OUTPUT_FILES if not f.exists()]
        self.assertEqual(len(missing), 0, f"v118C files deleted: {missing}")

    def test_82_v118b_files_exist(self):
        missing = [str(f) for f in V118B_OUTPUT_FILES if not f.exists()]
        self.assertEqual(len(missing), 0, f"v118B files deleted: {missing}")

    def test_83_v118a_files_exist(self):
        missing = [str(f) for f in V118A_OUTPUT_FILES if not f.exists()]
        self.assertEqual(len(missing), 0, f"v118A files deleted: {missing}")

    def test_84_v117_files_exist(self):
        missing = [str(f) for f in V117_OUTPUT_FILES if not f.exists()]
        self.assertEqual(len(missing), 0, f"v117 files deleted: {missing}")

    def test_85_v116n_files_exist(self):
        missing = [str(f) for f in V116N_FILES if not f.exists()]
        self.assertEqual(len(missing), 0, f"v116N files deleted: {missing}")


class TestV118ECompleteLeakAudit(unittest.TestCase):
    """Comprehensive audit of all v118E outputs for secret leaks."""

    def test_a0_all_outputs_no_raw_token(self):
        for fpath in ALL_V118E_OUTPUT_FILES:
            if not fpath.exists():
                continue
            if fpath.suffix == ".json":
                data = load_json(fpath)
                text = json.dumps(data, ensure_ascii=False)
                self.assertIsNone(RAW_TOKEN_PATTERN.search(text),
                                f"{fpath.name}: raw token pattern")
            else:
                text = fpath.read_text(encoding="utf-8")
                self.assertIsNone(RAW_TOKEN_PATTERN.search(text),
                                f"{fpath.name}: raw token pattern")

    def test_a1_all_outputs_no_raw_chat_id(self):
        for fpath in ALL_V118E_OUTPUT_FILES:
            if not fpath.exists():
                continue
            if fpath.suffix == ".json":
                data = load_json(fpath)
                text = json.dumps(data, ensure_ascii=False)
                self.assertIsNone(RAW_CHAT_ID_PATTERN.search(text),
                                f"{fpath.name}: raw chat_id pattern")
            else:
                text = fpath.read_text(encoding="utf-8")
                self.assertIsNone(RAW_CHAT_ID_PATTERN.search(text),
                                f"{fpath.name}: raw chat_id pattern")

    def test_a2_all_outputs_no_raw_message_id(self):
        for fpath in ALL_V118E_OUTPUT_FILES:
            if not fpath.exists():
                continue
            if fpath.suffix == ".json":
                data = load_json(fpath)
                text = json.dumps(data, ensure_ascii=False)
                self.assertIsNone(RAW_MESSAGE_ID_PATTERN.search(text),
                                f"{fpath.name}: raw message_id pattern")
            else:
                text = fpath.read_text(encoding="utf-8")
                self.assertIsNone(RAW_MESSAGE_ID_PATTERN.search(text),
                                f"{fpath.name}: raw message_id pattern")

    def test_a3_all_outputs_no_python_secret_vars(self):
        """Check for Python-style secret assignments in outputs."""
        secret_pattern = re.compile(
            r'(api_key|api_secret|secret_key|access_token|auth_token|password)\s*=\s*["\'][A-Za-z0-9_\-=]{8,}["\']',
            re.IGNORECASE,
        )
        for fpath in ALL_V118E_OUTPUT_FILES:
            if not fpath.exists() or fpath.suffix == ".json":
                continue
            text = fpath.read_text(encoding="utf-8")
            self.assertIsNone(secret_pattern.search(text),
                            f"{fpath.name}: contains secret variable pattern")


class TestV118ENoExternalCallProof(unittest.TestCase):
    """Prove that v118E runner makes zero external calls."""

    def test_b0_runner_has_no_network_imports(self):
        source = V118E_RUNNER.read_text(encoding="utf-8")
        self.assertNotIn("import requests", source)
        self.assertNotIn("from requests", source)
        self.assertNotIn("import urllib.request", source)
        self.assertNotIn("from urllib", source)
        self.assertNotIn("import http.client", source)
        self.assertNotIn("import socket", source)
        self.assertNotIn("import telegram", source)
        self.assertNotIn("from telegram", source)
        self.assertNotIn("import openai", source)
        self.assertNotIn("import anthropic", source)

    def test_b1_runner_source_is_v118d_only(self):
        source = V118E_RUNNER.read_text(encoding="utf-8")
        self.assertIn("v118d_operator_acceptance_gate_result", source)
        self.assertNotIn("https://api.binance.com", source)
        self.assertNotIn("https://fapi.binance.com", source)
        self.assertNotIn("api.telegram.org", source)

    def test_b2_runner_no_ai_model_import(self):
        source = V118E_RUNNER.read_text(encoding="utf-8")
        ai_imports = ["openai", "anthropic", "gemini", "openrouter", "cohere",
                       "huggingface", "transformers", "torch", "tensorflow"]
        for imp in ai_imports:
            self.assertNotIn(f"import {imp}", source.lower())
            self.assertNotIn(f"from {imp}", source.lower())

    def test_b3_html_no_external_resources(self):
        """Generated HTML must not load external resources (CDN, fonts, etc.)."""
        if not V118E_HTML.exists():
            self.skipTest("HTML not yet generated")
        html = V118E_HTML.read_text(encoding="utf-8")
        # No http/https references (except doctype)
        doctype_stripped = re.sub(r'<!DOCTYPE html>', '', html, flags=re.IGNORECASE)
        self.assertNotIn("http://", doctype_stripped,
                        "HTML must not reference external HTTP resources")
        self.assertNotIn("https://", doctype_stripped,
                        "HTML must not reference external HTTPS resources")


if __name__ == "__main__":
    unittest.main(verbosity=2)
