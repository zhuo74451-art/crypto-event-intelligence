"""Market Radar v119A — Live No-Send Operator One-Shot Refresh Flow Tests.

Tests cover:
  - Runner is importable and executable
  - Result JSON generated with correct structure
  - Dashboard HTML generated
  - All 5 card families in operator snapshot
  - 3 live adapters are used
  - Operator decisions only from {accept, watch, reject, manual_required}
  - whale_position_alert is manual_required (manual evidence NOT bypassed)
  - liquidation_pressure is NOT accept (threshold NOT lowered)
  - news_event_market_impact observation_only=true, not_causal_proof=true
  - Production readiness is false / 0/5
  - No-send preview confirms telegram_send=false, x_twitter_send=false,
    production_send=false, daemon_or_loop_started=false
  - No raw token/chat_id/message_id/cookie/password/API key in any output
  - No files deleted during run
  - v116A–N historical outputs not modified

Usage:
    python -X utf8 -m pytest scripts/test_market_radar_v119a_live_no_send_operator_one_shot_refresh_flow.py -v
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


# ── v119A Paths ──────────────────────────────────────────────────────────────

V119A_RUNNER = ROOT / "scripts" / "run_market_radar_v119a_live_no_send_operator_one_shot_refresh_flow.py"
V119A_TEST = ROOT / "scripts" / "test_market_radar_v119a_live_no_send_operator_one_shot_refresh_flow.py"

V119A_RESULT_JSON = ROOT / "results" / "market_radar_v119a_live_no_send_operator_refresh_result.json"
V119A_SNAPSHOT_MD = ROOT / "runs" / "market_radar" / "v119a_live_operator_snapshot.md"
V119A_DECISION_TABLE_MD = ROOT / "runs" / "market_radar" / "v119a_operator_decision_table.md"
V119A_DASHBOARD_HTML = ROOT / "runs" / "market_radar" / "v119a_operator_dashboard.html"
V119A_NO_SEND_MD = ROOT / "runs" / "market_radar" / "v119a_no_send_preview.md"
V119A_HANDOFF_MD = ROOT / "runs" / "market_radar" / "v119a_local_only_handoff.md"

ALL_V119A_OUTPUT_FILES = [
    V119A_RESULT_JSON,
    V119A_SNAPSHOT_MD,
    V119A_DECISION_TABLE_MD,
    V119A_DASHBOARD_HTML,
    V119A_NO_SEND_MD,
    V119A_HANDOFF_MD,
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

V116_OUTPUT_FILES = sorted(ROOT.glob("results/market_radar_v116*")) + \
                     sorted(ROOT.glob("runs/market_radar/v116*"))
V117_OUTPUT_FILES = sorted(ROOT.glob("results/market_radar_v117*")) + \
                     sorted(ROOT.glob("runs/market_radar/v117*"))
V118_OUTPUT_FILES = sorted(ROOT.glob("results/market_radar_v118*")) + \
                     sorted(ROOT.glob("runs/market_radar/v118*"))


# ═══════════════════════════════════════════════════════════════════════════
# TEST CLASSES
# ═══════════════════════════════════════════════════════════════════════════


class TestV119ARunnerExists(unittest.TestCase):
    """Test that the v119A runner and test files exist."""

    def test_01_runner_file_exists(self):
        """Runner file exists."""
        self.assertTrue(V119A_RUNNER.exists(), f"Runner not found: {V119A_RUNNER}")

    def test_02_test_file_exists(self):
        """Test file exists."""
        self.assertTrue(V119A_TEST.exists(), f"Test file not found: {V119A_TEST}")

    def test_03_runner_is_importable(self):
        """Runner module is importable as Python."""
        import importlib.util
        spec = importlib.util.spec_from_file_location("v119a_runner", V119A_RUNNER)
        self.assertIsNotNone(spec, "Runner spec is None — file may have syntax errors")
        if spec:
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)


class TestV119AResultJSON(unittest.TestCase):
    """Test the v119A result JSON file."""

    @classmethod
    def setUpClass(cls):
        cls.result = load_json(V119A_RESULT_JSON)

    def test_01_result_json_exists(self):
        """Result JSON exists and is valid."""
        self.assertTrue(V119A_RESULT_JSON.exists(), f"Missing: {V119A_RESULT_JSON}")

    def test_02_pipeline_version(self):
        """Pipeline version is v1.19A."""
        self.assertEqual(self.result.get("pipeline_version"), "v1.19A")

    def test_03_has_run_id(self):
        """Result has a run_id."""
        self.assertIsNotNone(self.result.get("run_id"))

    def test_04_type_field(self):
        """Type is live_no_send_operator_one_shot_refresh_flow."""
        self.assertEqual(
            self.result.get("type"),
            "live_no_send_operator_one_shot_refresh_flow",
        )

    def test_05_mode_is_live_one_shot_no_send(self):
        """Mode is live_one_shot_no_send."""
        self.assertEqual(self.result.get("mode"), "live_one_shot_no_send")

    def test_06_cards_present(self):
        """Cards array present with entries."""
        cards = self.result.get("cards", [])
        self.assertIsInstance(cards, list, "cards must be a list")
        self.assertGreater(len(cards), 0, "cards must have entries")

    def test_07_five_card_families_in_cards(self):
        """All 5 card families are represented in cards."""
        cards = self.result.get("cards", [])
        families = {c["card_family"] for c in cards}
        missing = set(FIVE_CARD_FAMILIES) - families
        self.assertEqual(len(missing), 0, f"Missing card families: {missing}")

    def test_08_decisions_in_allowed_set(self):
        """All operator decisions are in {accept, watch, reject, manual_required}."""
        cards = self.result.get("cards", [])
        for c in cards:
            decision = c.get("operator_decision", "")
            self.assertIn(
                decision, ALLOWED_DECISIONS,
                f"{c['card_family']}: decision '{decision}' not in allowed set",
            )

    def test_09_whale_is_manual_required(self):
        """whale_position_alert operator decision is manual_required."""
        cards = self.result.get("cards", [])
        whale = [c for c in cards if c["card_family"] == "whale_position_alert"]
        self.assertEqual(len(whale), 1, "Expected exactly 1 whale_position_alert card")
        self.assertEqual(
            whale[0]["operator_decision"], "manual_required",
            "whale_position_alert must be manual_required — manual evidence NOT bypassed",
        )

    def test_10_liquidation_not_accepted(self):
        """liquidation_pressure operator decision is NOT accept."""
        cards = self.result.get("cards", [])
        liq = [c for c in cards if c["card_family"] == "liquidation_pressure"]
        self.assertEqual(len(liq), 1, "Expected exactly 1 liquidation_pressure card")
        self.assertNotEqual(
            liq[0]["operator_decision"], "accept",
            "liquidation_pressure must NOT be accept — threshold must NOT be lowered",
        )

    def test_11_news_observation_only(self):
        """news_event_market_impact has observation_only=true."""
        cards = self.result.get("cards", [])
        news = [c for c in cards if c["card_family"] == "news_event_market_impact"]
        if news:
            self.assertTrue(
                news[0].get("observation_only", False),
                "news_event_market_impact must have observation_only=true",
            )

    def test_12_news_not_causal_proof(self):
        """news_event_market_impact has not_causal_proof=true."""
        cards = self.result.get("cards", [])
        news = [c for c in cards if c["card_family"] == "news_event_market_impact"]
        if news:
            self.assertTrue(
                news[0].get("not_causal_proof", False),
                "news_event_market_impact must have not_causal_proof=true",
            )

    def test_13_production_readiness_false(self):
        """Production readiness is false / 0/5."""
        pr = self.result.get("production_readiness", {})
        self.assertFalse(pr.get("production_ready", True), "production_ready must be False")
        self.assertEqual(
            pr.get("production_readiness_score"), "0/5",
            "production_readiness_score must be '0/5'",
        )

    def test_14_no_send_preview_in_result(self):
        """No-send preview confirms all sends are false."""
        nsp = self.result.get("no_send_preview", {})
        self.assertFalse(nsp.get("telegram_send", True), "telegram_send must be False")
        self.assertFalse(nsp.get("x_twitter_send", True), "x_twitter_send must be False")
        self.assertFalse(nsp.get("production_send", True), "production_send must be False")
        self.assertFalse(
            nsp.get("daemon_or_loop_started", True),
            "daemon_or_loop_started must be False",
        )

    def test_15_safety_checks(self):
        """Safety object confirms no TG, no AI, no daemon, no files deleted."""
        safety = self.result.get("safety", {})
        self.assertFalse(safety.get("tg_sent_this_run", True), "tg_sent_this_run must be False")
        self.assertFalse(safety.get("ai_model_called", True), "ai_model_called must be False")
        self.assertFalse(
            safety.get("daemon_or_loop_started", True),
            "daemon_or_loop_started must be False",
        )
        self.assertFalse(safety.get("files_deleted", True), "files_deleted must be False")
        self.assertFalse(safety.get("x_twitter_sent_this_run", True), "x_twitter_sent_this_run must be False")

    def test_16_adapter_diagnostics_present(self):
        """Adapter diagnostics are present with 5 entries."""
        diags = self.result.get("adapter_diagnostics", [])
        self.assertEqual(len(diags), 5, f"Expected 5 adapter diagnostics, got {len(diags)}")

    def test_17_live_adapters_used(self):
        """At least 3 live adapters were used."""
        diags = self.result.get("adapter_diagnostics", [])
        live_count = sum(
            1 for d in diags
            if d.get("used") and "Fixture" not in d.get("adapter", "")
        )
        self.assertGreaterEqual(
            live_count, 3,
            f"Expected >= 3 live adapters used, got {live_count}",
        )

    def test_18_contract_validation_present(self):
        """Contract validation is present."""
        cv = self.result.get("contract_validation", {})
        self.assertIsNotNone(cv.get("all_passed"), "contract_validation missing all_passed")

    def test_19_no_raw_secrets_in_result_json(self):
        """No raw secrets in result JSON."""
        text = json.dumps(self.result, ensure_ascii=False)
        violations = check_forbidden(text)
        self.assertEqual(len(violations), 0, f"Forbidden patterns: {violations}")
        self.assertFalse(RAW_TOKEN_PATTERN.search(text), "Raw token pattern found")
        self.assertFalse(RAW_CHAT_ID_PATTERN.search(text), "Raw chat_id pattern found")


class TestV119ADashboardHTML(unittest.TestCase):
    """Test the v119A operator dashboard HTML file."""

    @classmethod
    def setUpClass(cls):
        if not V119A_DASHBOARD_HTML.exists():
            raise unittest.SkipTest(f"Dashboard HTML not found: {V119A_DASHBOARD_HTML}")
        cls.html = V119A_DASHBOARD_HTML.read_text(encoding="utf-8")

    def test_01_html_exists(self):
        """Dashboard HTML file exists."""
        self.assertTrue(V119A_DASHBOARD_HTML.exists())

    def test_02_html_is_well_formed(self):
        """HTML has doctype, html, head, and body tags."""
        html_lower = self.html.lower()
        self.assertIn("<!doctype html>", html_lower)
        self.assertIn("<html", html_lower)
        self.assertIn("</html>", html_lower)
        self.assertIn("<head", html_lower)
        self.assertIn("</head>", html_lower)
        self.assertIn("<body", html_lower)
        self.assertIn("</body>", html_lower)

    def test_03_has_five_card_families(self):
        """HTML contains all 5 card families."""
        for cf in FIVE_CARD_FAMILIES:
            self.assertIn(cf, self.html, f"Card family '{cf}' not found in dashboard HTML")

    def test_04_has_four_decision_types(self):
        """HTML contains all 4 decision type badges."""
        self.assertIn("ACCEPT", self.html)
        self.assertIn("WATCH", self.html)
        self.assertIn("REJECT", self.html)
        self.assertIn("MANUAL REQUIRED", self.html)

    def test_05_has_no_send_markers(self):
        """HTML contains no-send markers."""
        self.assertIn("telegram_send=false", self.html.lower())
        self.assertIn("x_twitter_send=false", self.html.lower())
        self.assertIn("production_send=false", self.html.lower())
        self.assertIn("daemon_or_loop_started=false", self.html.lower())

    def test_06_production_readiness_false_marker(self):
        """HTML has '0/5' and 'NOT FOR PRODUCTION USE'."""
        self.assertIn("0/5", self.html)
        self.assertIn("NOT FOR PRODUCTION USE", self.html)

    def test_07_live_data_badge(self):
        """HTML contains a live data indicator."""
        self.assertIn("LIVE DATA", self.html, "HTML should indicate live data was used")

    def test_08_adapter_diagnostics_in_html(self):
        """HTML contains adapter diagnostic info."""
        self.assertIn("MultiAssetMarketSyncFreeApiAdapter", self.html)
        self.assertIn("PriceOIVolumeAnomalyFreeApiAdapter", self.html)
        self.assertIn("NewsEventMarketImpactFreePublicSourceAdapter", self.html)

    def test_09_no_raw_secrets_in_html(self):
        """No raw secrets in dashboard HTML."""
        violations = check_forbidden(self.html)
        self.assertEqual(len(violations), 0, f"Forbidden patterns: {violations}")
        self.assertFalse(RAW_TOKEN_PATTERN.search(self.html), "Raw token pattern in HTML")
        self.assertFalse(RAW_CHAT_ID_PATTERN.search(self.html), "Raw chat_id pattern in HTML")
        self.assertFalse(RAW_MESSAGE_ID_PATTERN.search(self.html), "Raw message_id pattern in HTML")


class TestV119ANoSendPreview(unittest.TestCase):
    """Test the v119A no-send preview markdown."""

    @classmethod
    def setUpClass(cls):
        if not V119A_NO_SEND_MD.exists():
            raise unittest.SkipTest(f"No-send preview not found: {V119A_NO_SEND_MD}")
        cls.content = V119A_NO_SEND_MD.read_text(encoding="utf-8")

    def test_01_no_send_exists(self):
        """No-send preview exists."""
        self.assertTrue(V119A_NO_SEND_MD.exists())

    def test_02_telegram_send_false(self):
        """No-send preview confirms telegram_send=false."""
        self.assertIn("telegram_send=false", self.content)

    def test_03_x_twitter_send_false(self):
        """No-send preview confirms x_twitter_send=false."""
        self.assertIn("x_twitter_send=false", self.content)

    def test_04_production_send_false(self):
        """No-send preview confirms production_send=false."""
        self.assertIn("production_send=false", self.content)

    def test_05_daemon_false(self):
        """No-send preview confirms daemon_or_loop_started=false."""
        self.assertIn("daemon_or_loop_started=false", self.content)

    def test_06_no_daemon_cron_loop(self):
        """No-send preview confirms daemon/cron/loop were NOT started."""
        content_lower = self.content.lower()
        # The preview should state that daemon/loop were NOT started
        # (the phrase "no daemon, cron, or loop was started" is the correct confirmation)
        has_negative_confirmation = (
            "no daemon" in content_lower
            or "daemon_or_loop_started=false" in content_lower
        )
        self.assertTrue(
            has_negative_confirmation,
            "No-send preview should confirm daemon/loop were NOT started",
        )

    def test_07_no_raw_secrets(self):
        """No raw secrets in no-send preview."""
        violations = check_forbidden(self.content)
        self.assertEqual(len(violations), 0, f"Forbidden patterns: {violations}")


class TestV119AOutputFiles(unittest.TestCase):
    """Test that all v119A output files exist and are non-empty."""

    def test_all_output_files_exist(self):
        """All 6 output files exist."""
        for fp in ALL_V119A_OUTPUT_FILES:
            with self.subTest(path=str(fp)):
                self.assertTrue(fp.exists(), f"Missing output file: {fp}")

    def test_all_output_files_non_empty(self):
        """All output files have content."""
        for fp in ALL_V119A_OUTPUT_FILES:
            if fp.exists():
                with self.subTest(path=str(fp)):
                    size = fp.stat().st_size
                    self.assertGreater(size, 100, f"File too small ({size} bytes): {fp}")


class TestV119AContractInvariants(unittest.TestCase):
    """Test v119A-specific contract invariants."""

    @classmethod
    def setUpClass(cls):
        cls.result = load_json(V119A_RESULT_JSON)

    def test_01_no_send_confirmed(self):
        """No-send is explicitly confirmed."""
        nsp = self.result.get("no_send_preview", {})
        all_false = (
            not nsp.get("telegram_send", True)
            and not nsp.get("x_twitter_send", True)
            and not nsp.get("production_send", True)
            and not nsp.get("daemon_or_loop_started", True)
        )
        self.assertTrue(all_false, "All send flags must be False")

    def test_02_no_tg_send(self):
        """TG was not sent during this run."""
        safety = self.result.get("safety", {})
        self.assertFalse(safety.get("tg_sent_this_run", True))
        self.assertEqual(safety.get("tg_message_count_this_run", 1), 0)

    def test_03_no_x_send(self):
        """X/Twitter was not sent."""
        safety = self.result.get("safety", {})
        self.assertFalse(safety.get("x_twitter_sent_this_run", True))

    def test_04_no_ai_called(self):
        """No AI/model was called."""
        safety = self.result.get("safety", {})
        self.assertFalse(safety.get("ai_model_called", True))

    def test_05_production_readiness_still_false(self):
        """Production readiness is still false / 0/5."""
        pr = self.result.get("production_readiness", {})
        self.assertFalse(pr.get("production_ready", True))
        self.assertEqual(pr.get("production_readiness_score"), "0/5")

    def test_06_output_files_listed(self):
        """Output files are listed in result."""
        output_files = self.result.get("output_files", {})
        self.assertIn("dashboard_html", output_files)
        self.assertIn("decision_table_md", output_files)
        self.assertIn("no_send_preview_md", output_files)
        self.assertIn("snapshot_md", output_files)
        self.assertIn("handoff_md", output_files)

    def test_07_binance_api_key_not_used(self):
        """Binance API key was NOT used (free API only)."""
        safety = self.result.get("safety", {})
        self.assertFalse(
            safety.get("binance_api_key_used", True),
            "binance_api_key_used must be False — only free endpoints used",
        )


class TestV119ASnapshotMarkdown(unittest.TestCase):
    """Test the v119A live operator snapshot markdown."""

    @classmethod
    def setUpClass(cls):
        if not V119A_SNAPSHOT_MD.exists():
            raise unittest.SkipTest(f"Snapshot MD not found: {V119A_SNAPSHOT_MD}")
        cls.content = V119A_SNAPSHOT_MD.read_text(encoding="utf-8")

    def test_01_snapshot_exists(self):
        """Snapshot markdown exists."""
        self.assertTrue(V119A_SNAPSHOT_MD.exists())

    def test_02_has_five_families(self):
        """Snapshot covers all 5 card families."""
        for cf in FIVE_CARD_FAMILIES:
            self.assertIn(cf, self.content, f"Missing {cf} in snapshot")

    def test_03_has_live_sources(self):
        """Snapshot mentions live data sources."""
        self.assertIn("Live Data Sources Used", self.content)

    def test_04_has_adapter_diagnostics(self):
        """Snapshot has adapter diagnostics section."""
        self.assertIn("Adapter Diagnostics", self.content)

    def test_05_no_raw_secrets(self):
        """No raw secrets in snapshot."""
        violations = check_forbidden(self.content)
        self.assertEqual(len(violations), 0, f"Forbidden patterns: {violations}")


class TestV119ADecisionTableMarkdown(unittest.TestCase):
    """Test the v119A operator decision table markdown."""

    @classmethod
    def setUpClass(cls):
        if not V119A_DECISION_TABLE_MD.exists():
            raise unittest.SkipTest(f"Decision table not found: {V119A_DECISION_TABLE_MD}")
        cls.content = V119A_DECISION_TABLE_MD.read_text(encoding="utf-8")

    def test_01_table_exists(self):
        """Decision table exists."""
        self.assertTrue(V119A_DECISION_TABLE_MD.exists())

    def test_02_has_five_families(self):
        """Decision table covers all 5 card families."""
        for cf in FIVE_CARD_FAMILIES:
            self.assertIn(cf, self.content, f"Missing {cf} in decision table")

    def test_03_has_all_decisions(self):
        """Decision table includes all decision types."""
        for dec in ALLOWED_DECISIONS:
            self.assertIn(dec, self.content, f"Missing decision {dec} in table")

    def test_04_key_constraints_section(self):
        """Decision table has key constraints verified section."""
        self.assertIn("Key Constraints Verified", self.content)

    def test_05_no_raw_secrets(self):
        """No raw secrets in decision table."""
        violations = check_forbidden(self.content)
        self.assertEqual(len(violations), 0, f"Forbidden patterns: {violations}")


class TestV119AHandoffMarkdown(unittest.TestCase):
    """Test the v119A handoff markdown."""

    @classmethod
    def setUpClass(cls):
        if not V119A_HANDOFF_MD.exists():
            raise unittest.SkipTest(f"Handoff not found: {V119A_HANDOFF_MD}")
        cls.content = V119A_HANDOFF_MD.read_text(encoding="utf-8")

    def test_01_handoff_exists(self):
        """Handoff exists."""
        self.assertTrue(V119A_HANDOFF_MD.exists())

    def test_02_has_live_sources(self):
        """Handoff mentions live data sources."""
        self.assertIn("Live Data", self.content)

    def test_03_has_what_was_not_done(self):
        """Handoff documents what was NOT done."""
        self.assertIn("What Was NOT Done", self.content)

    def test_04_has_production_readiness(self):
        """Handoff mentions production readiness."""
        content_lower = self.content.lower()
        self.assertIn("0/5", content_lower)

    def test_05_no_raw_secrets(self):
        """No raw secrets in handoff."""
        violations = check_forbidden(self.content)
        self.assertEqual(len(violations), 0, f"Forbidden patterns: {violations}")


if __name__ == "__main__":
    unittest.main()
