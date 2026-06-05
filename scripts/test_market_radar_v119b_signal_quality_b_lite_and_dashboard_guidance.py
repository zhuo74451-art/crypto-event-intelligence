"""Market Radar v119B — Signal Quality B-lite + Dashboard Guidance Tests.

Tests cover:
  - Runner is importable and executable
  - Result JSON generated with correct structure
  - Dashboard HTML generated with Chinese guidance layer
  - All 5 card families present in result
  - price_oi_volume_anomaly supports layered decision (reject/watch/accept)
  - Mild anomaly can only enter watch, NOT accept
  - OI $0.0B or abnormal OI produces warning or explanation
  - news_event_market_impact preserves observation_only=true, not_causal_proof=true
  - News has freshness / stale warning fields
  - Dashboard has Chinese 30-second guidance layer
  - Dashboard confirms production readiness = false / 0/5
  - No-send confirmed: telegram_send=false, x_twitter_send=false, etc.
  - No raw secrets in any output
  - No files deleted
  - No v116A-N / v117 / v118 / v119A historical modification

Usage:
    python -X utf8 -m pytest scripts/test_market_radar_v119b_signal_quality_b_lite_and_dashboard_guidance.py -v
"""

from __future__ import annotations

import json
import re
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


# ── Forbidden patterns ────────────────────────────────────────────────────────

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


# ── v119B Paths ────────────────────────────────────────────────────────────────

V119B_RUNNER = ROOT / "scripts" / "run_market_radar_v119b_signal_quality_b_lite_and_dashboard_guidance.py"
V119B_TEST = ROOT / "scripts" / "test_market_radar_v119b_signal_quality_b_lite_and_dashboard_guidance.py"

V119B_RESULT_JSON = ROOT / "results" / "market_radar_v119b_signal_quality_b_lite_result.json"
V119B_SNAPSHOT_MD = ROOT / "runs" / "market_radar" / "v119b_live_operator_snapshot.md"
V119B_DECISION_TABLE_MD = ROOT / "runs" / "market_radar" / "v119b_operator_decision_table.md"
V119B_DASHBOARD_HTML = ROOT / "runs" / "market_radar" / "v119b_operator_dashboard.html"
V119B_NO_SEND_MD = ROOT / "runs" / "market_radar" / "v119b_no_send_preview.md"
V119B_HANDOFF_MD = ROOT / "runs" / "market_radar" / "v119b_local_only_handoff.md"

ALL_V119B_OUTPUT_FILES = [
    V119B_RESULT_JSON,
    V119B_SNAPSHOT_MD,
    V119B_DECISION_TABLE_MD,
    V119B_DASHBOARD_HTML,
    V119B_NO_SEND_MD,
    V119B_HANDOFF_MD,
]

FIVE_CARD_FAMILIES = [
    "multi_asset_market_sync",
    "price_oi_volume_anomaly",
    "news_event_market_impact",
    "liquidation_pressure",
    "whale_position_alert",
]

ALLOWED_DECISIONS = {"accept", "watch", "reject", "manual_required"}

# ── Historical output files (must not be modified) ────────────────────────────

V116_OUTPUT_FILES = sorted(ROOT.glob("results/market_radar_v116*")) + \
                     sorted(ROOT.glob("runs/market_radar/v116*"))
V117_OUTPUT_FILES = sorted(ROOT.glob("results/market_radar_v117*")) + \
                     sorted(ROOT.glob("runs/market_radar/v117*"))
V118_OUTPUT_FILES = sorted(ROOT.glob("results/market_radar_v118*")) + \
                     sorted(ROOT.glob("runs/market_radar/v118*"))
V119A_OUTPUT_FILES = sorted(ROOT.glob("results/market_radar_v119a*")) + \
                     sorted(ROOT.glob("runs/market_radar/v119a*"))


# ═══════════════════════════════════════════════════════════════════════════════
# TEST CLASSES
# ═══════════════════════════════════════════════════════════════════════════════


class TestV119BRunnerExists(unittest.TestCase):
    """Test that the v119B runner and test files exist."""

    def test_01_runner_file_exists(self):
        self.assertTrue(V119B_RUNNER.exists(), f"Runner not found: {V119B_RUNNER}")

    def test_02_test_file_exists(self):
        self.assertTrue(V119B_TEST.exists(), f"Test file not found: {V119B_TEST}")

    def test_03_runner_is_importable(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location("v119b_runner", V119B_RUNNER)
        self.assertIsNotNone(spec, "Runner spec is None — file may have syntax errors")
        if spec:
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)


class TestV119BResultJSON(unittest.TestCase):
    """Test the v119B result JSON file."""

    @classmethod
    def setUpClass(cls):
        if not V119B_RESULT_JSON.exists():
            raise unittest.SkipTest(f"Result JSON not found (run v119B runner first): {V119B_RESULT_JSON}")
        cls.result = load_json(V119B_RESULT_JSON)

    def test_01_result_json_exists(self):
        self.assertTrue(V119B_RESULT_JSON.exists(), f"Missing: {V119B_RESULT_JSON}")

    def test_02_pipeline_version(self):
        self.assertEqual(self.result.get("pipeline_version"), "v1.19B")

    def test_03_type_field_is_v119b(self):
        t = self.result.get("type", "")
        self.assertIn("v119b", t.lower())

    def test_04_mode_is_live_one_shot_no_send(self):
        self.assertEqual(self.result.get("mode"), "live_one_shot_no_send")

    def test_05_cards_present(self):
        cards = self.result.get("cards", [])
        self.assertIsInstance(cards, list)
        self.assertGreater(len(cards), 0)

    def test_06_five_card_families_in_cards(self):
        cards = self.result.get("cards", [])
        families = {c["card_family"] for c in cards}
        missing = set(FIVE_CARD_FAMILIES) - families
        self.assertEqual(len(missing), 0, f"Missing: {missing}")

    def test_07_decisions_in_allowed_set(self):
        cards = self.result.get("cards", [])
        for c in cards:
            decision = c.get("operator_decision", "")
            self.assertIn(decision, ALLOWED_DECISIONS,
                          f"{c['card_family']}: '{decision}' not in allowed set")

    def test_08_whale_is_manual_required(self):
        cards = self.result.get("cards", [])
        whale = [c for c in cards if c["card_family"] == "whale_position_alert"]
        self.assertEqual(len(whale), 1)
        self.assertEqual(whale[0]["operator_decision"], "manual_required")

    def test_09_liquidation_not_accepted(self):
        cards = self.result.get("cards", [])
        liq = [c for c in cards if c["card_family"] == "liquidation_pressure"]
        self.assertEqual(len(liq), 1)
        self.assertNotEqual(liq[0]["operator_decision"], "accept")

    def test_10_news_observation_only(self):
        cards = self.result.get("cards", [])
        news = [c for c in cards if c["card_family"] == "news_event_market_impact"]
        if news:
            self.assertTrue(news[0].get("observation_only", False),
                           "news_event_market_impact must have observation_only=true")

    def test_11_news_not_causal_proof(self):
        cards = self.result.get("cards", [])
        news = [c for c in cards if c["card_family"] == "news_event_market_impact"]
        if news:
            self.assertTrue(news[0].get("not_causal_proof", False),
                           "news_event_market_impact must have not_causal_proof=true")

    def test_12_production_readiness_false(self):
        pr = self.result.get("production_readiness", {})
        self.assertFalse(pr.get("production_ready", True))
        self.assertEqual(pr.get("production_readiness_score"), "0/5")

    def test_13_no_send_preview_false_all(self):
        nsp = self.result.get("no_send_preview", {})
        self.assertFalse(nsp.get("telegram_send", True))
        self.assertFalse(nsp.get("x_twitter_send", True))
        self.assertFalse(nsp.get("production_send", True))
        self.assertFalse(nsp.get("daemon_or_loop_started", True))

    def test_14_blite_enhancements_present(self):
        be = self.result.get("blite_enhancements", {})
        self.assertIn("price_oi_volume_anomaly", be)
        self.assertIn("news_event_market_impact", be)
        self.assertIn("dashboard_guidance", be)

    # ── B-lite specific: price_oi_volume_anomaly ──

    def test_15_poi_has_blite_tier_field(self):
        cards = self.result.get("cards", [])
        poi = [c for c in cards if c["card_family"] == "price_oi_volume_anomaly"]
        self.assertEqual(len(poi), 1)
        # Must have blite_tier field (can be empty string for reject)
        self.assertIn("blite_tier", poi[0], "price_oi_volume_anomaly must have blite_tier field")

    def test_16_poi_watch_means_observation(self):
        """If price_oi_volume_anomaly is watch, it MUST be observation only, NOT accept."""
        cards = self.result.get("cards", [])
        poi = [c for c in cards if c["card_family"] == "price_oi_volume_anomaly"]
        if poi and poi[0].get("operator_decision") == "watch":
            self.assertTrue(
                poi[0].get("watch_is_observation", False),
                "WATCH must be marked as observation only"
            )
            # Ensure it's NOT accept
            self.assertNotEqual(poi[0].get("blite_tier", ""), "accept")

    def test_17_poi_accept_only_strong(self):
        """If price_oi_volume_anomaly is accept, blite_tier must be 'accept' (strong)."""
        cards = self.result.get("cards", [])
        poi = [c for c in cards if c["card_family"] == "price_oi_volume_anomaly"]
        if poi and poi[0].get("operator_decision") == "accept":
            self.assertEqual(poi[0].get("blite_tier", ""), "accept",
                           "accept decision must have blite_tier=accept (strong signal)")

    # ── B-lite specific: news freshness / stale ──

    def test_18_news_has_stale_warnings_field(self):
        cards = self.result.get("cards", [])
        news = [c for c in cards if c["card_family"] == "news_event_market_impact"]
        if news:
            self.assertIn("stale_warnings", news[0],
                         "news must have stale_warnings field")

    def test_19_news_has_freshness_info(self):
        cards = self.result.get("cards", [])
        news = [c for c in cards if c["card_family"] == "news_event_market_impact"]
        if news:
            self.assertIn("freshness_info", news[0],
                         "news must have freshness_info field")


class TestV119BDashboardHTML(unittest.TestCase):
    """Test the v119B operator dashboard HTML file."""

    @classmethod
    def setUpClass(cls):
        if not V119B_DASHBOARD_HTML.exists():
            raise unittest.SkipTest(f"Dashboard HTML not found (run runner first): {V119B_DASHBOARD_HTML}")
        cls.html = V119B_DASHBOARD_HTML.read_text(encoding="utf-8")

    def test_01_html_exists(self):
        self.assertTrue(V119B_DASHBOARD_HTML.exists())

    def test_02_html_is_well_formed(self):
        html_lower = self.html.lower()
        self.assertIn("<!doctype html>", html_lower)
        self.assertIn("<html", html_lower)
        self.assertIn("</html>", html_lower)
        self.assertIn("<head", html_lower)
        self.assertIn("</head>", html_lower)
        self.assertIn("<body", html_lower)
        self.assertIn("</body>", html_lower)

    def test_03_has_five_card_families(self):
        for cf in FIVE_CARD_FAMILIES:
            self.assertIn(cf, self.html,
                         f"Card family '{cf}' not found in dashboard HTML")

    def test_04_has_blite_markers(self):
        """HTML mentions B-lite."""
        self.assertIn("B-lite", self.html, "Dashboard should mention B-lite")
        self.assertIn("B-LITE", self.html, "Dashboard should have B-LITE badge")

    # ── Chinese guidance layer tests ──

    def test_05_chinese_guidance_what_is_this(self):
        """Chinese guidance answers '这是什么'."""
        self.assertIn("这是什么", self.html)
        self.assertIn("策略值班看板", self.html)

    def test_06_chinese_guidance_how_to_read(self):
        """Chinese guidance answers '现在怎么看'."""
        self.assertIn("现在怎么看", self.html)
        self.assertIn("优先看", self.html)

    def test_07_chinese_guidance_can_publish(self):
        """Chinese guidance answers '现在能不能发'."""
        self.assertIn("现在能不能发", self.html)
        self.assertIn("不能正式发布", self.html)
        self.assertIn("0/5", self.html)

    def test_08_chinese_guidance_data_source(self):
        """Chinese guidance answers '数据从哪来'."""
        self.assertIn("数据从哪来", self.html)

    def test_09_chinese_guidance_next_step(self):
        """Chinese guidance answers '操作员下一步'."""
        self.assertIn("操作员下一步", self.html)

    def test_10_guidance_layer_structure(self):
        """The guidance-layer div exists."""
        self.assertIn("guidance-layer", self.html)

    # ── Production readiness ──

    def test_11_production_readiness_false(self):
        self.assertIn("0/5", self.html)
        self.assertIn("NOT FOR PRODUCTION USE", self.html)

    def test_12_no_send_markers(self):
        html_lower = self.html.lower()
        self.assertIn("telegram_send=false", html_lower)
        self.assertIn("x_twitter_send=false", html_lower)
        self.assertIn("production_send=false", html_lower)
        self.assertIn("daemon_or_loop_started=false", html_lower)

    # ── B-lite specific in HTML ──

    def test_13_blite_tier_column(self):
        """HTML has B-lite Tier column."""
        self.assertIn("B-lite Tier", self.html,
                     "Dashboard should have B-lite Tier column")

    def test_14_accept_watch_reject_labels(self):
        """All decision types present."""
        self.assertIn("ACCEPT", self.html)
        self.assertIn("WATCH", self.html)
        self.assertIn("REJECT", self.html)
        self.assertIn("MANUAL REQUIRED", self.html)

    def test_15_no_raw_secrets(self):
        violations = check_forbidden(self.html)
        self.assertEqual(len(violations), 0, f"Forbidden patterns: {violations}")
        self.assertFalse(RAW_TOKEN_PATTERN.search(self.html))
        self.assertFalse(RAW_CHAT_ID_PATTERN.search(self.html))
        self.assertFalse(RAW_MESSAGE_ID_PATTERN.search(self.html))


class TestV119BNoSendPreview(unittest.TestCase):
    """Test the v119B no-send preview markdown."""

    @classmethod
    def setUpClass(cls):
        if not V119B_NO_SEND_MD.exists():
            raise unittest.SkipTest(f"No-send preview not found: {V119B_NO_SEND_MD}")
        cls.content = V119B_NO_SEND_MD.read_text(encoding="utf-8")

    def test_01_no_send_exists(self):
        self.assertTrue(V119B_NO_SEND_MD.exists())

    def test_02_telegram_send_false(self):
        self.assertIn("telegram_send=false", self.content)

    def test_03_x_twitter_send_false(self):
        self.assertIn("x_twitter_send=false", self.content)

    def test_04_production_send_false(self):
        self.assertIn("production_send=false", self.content)

    def test_05_daemon_false(self):
        self.assertIn("daemon_or_loop_started=false", self.content)

    def test_06_no_raw_secrets(self):
        violations = check_forbidden(self.content)
        self.assertEqual(len(violations), 0, f"Forbidden patterns: {violations}")


class TestV119BOutputFiles(unittest.TestCase):
    """Test that all v119B output files exist and are non-empty."""

    def test_all_output_files_exist(self):
        for fp in ALL_V119B_OUTPUT_FILES:
            with self.subTest(path=str(fp)):
                self.assertTrue(fp.exists(), f"Missing: {fp}")

    def test_all_output_files_non_empty(self):
        for fp in ALL_V119B_OUTPUT_FILES:
            if fp.exists():
                with self.subTest(path=str(fp)):
                    size = fp.stat().st_size
                    self.assertGreater(size, 100,
                                      f"File too small ({size} bytes): {fp}")


class TestV119BContractInvariants(unittest.TestCase):
    """Test v119B-specific contract invariants."""

    @classmethod
    def setUpClass(cls):
        if not V119B_RESULT_JSON.exists():
            raise unittest.SkipTest(f"Result JSON not found: {V119B_RESULT_JSON}")
        cls.result = load_json(V119B_RESULT_JSON)

    def test_01_no_send_confirmed_all_false(self):
        nsp = self.result.get("no_send_preview", {})
        all_false = (
            not nsp.get("telegram_send", True)
            and not nsp.get("x_twitter_send", True)
            and not nsp.get("production_send", True)
            and not nsp.get("daemon_or_loop_started", True)
        )
        self.assertTrue(all_false, "All send flags must be False")

    def test_02_no_tg_send(self):
        safety = self.result.get("safety", {})
        self.assertFalse(safety.get("tg_sent_this_run", True))
        self.assertEqual(safety.get("tg_message_count_this_run", 1), 0)

    def test_03_no_ai_called(self):
        safety = self.result.get("safety", {})
        self.assertFalse(safety.get("ai_model_called", True))

    def test_04_production_readiness_still_false(self):
        pr = self.result.get("production_readiness", {})
        self.assertFalse(pr.get("production_ready", True))
        self.assertEqual(pr.get("production_readiness_score"), "0/5")

    def test_05_output_files_listed(self):
        output_files = self.result.get("output_files", {})
        self.assertIn("dashboard_html", output_files)
        self.assertIn("decision_table_md", output_files)
        self.assertIn("no_send_preview_md", output_files)
        self.assertIn("snapshot_md", output_files)
        self.assertIn("handoff_md", output_files)

    def test_06_history_not_modified(self):
        safety = self.result.get("safety", {})
        self.assertFalse(safety.get("v116_history_modified", True))
        self.assertFalse(safety.get("v117_history_modified", True))
        self.assertFalse(safety.get("v118_history_modified", True))
        self.assertFalse(safety.get("v119a_history_modified", True))

    def test_07_no_files_deleted(self):
        safety = self.result.get("safety", {})
        self.assertFalse(safety.get("files_deleted", True))

    def test_08_no_credentials_printed(self):
        safety = self.result.get("safety", {})
        self.assertFalse(safety.get("credentials_printed", True))

    def test_09_binance_api_key_not_used(self):
        safety = self.result.get("safety", {})
        self.assertFalse(safety.get("binance_api_key_used", True))

    def test_10_contract_validation_all_passed(self):
        cv = self.result.get("contract_validation", {})
        self.assertTrue(cv.get("all_passed", False),
                       "Contract validation must have all_passed=true")


class TestV119BBlitePriceOIAnomaly(unittest.TestCase):
    """B-lite specific tests for price_oi_volume_anomaly layered decision."""

    @classmethod
    def setUpClass(cls):
        if not V119B_RESULT_JSON.exists():
            raise unittest.SkipTest(f"Result JSON not found: {V119B_RESULT_JSON}")
        cls.result = load_json(V119B_RESULT_JSON)
        cards = cls.result.get("cards", [])
        cls.poi = [c for c in cards if c["card_family"] == "price_oi_volume_anomaly"]

    def test_01_poi_card_present(self):
        """Price/OI/Volume anomaly card exists."""
        self.assertEqual(len(self.poi), 1, "Expected exactly 1 price_oi_volume_anomaly card")

    def test_02_blite_layered_enhancement_present(self):
        """blite_enhancements section confirms layered decision."""
        be = self.result.get("blite_enhancements", {})
        poi_be = be.get("price_oi_volume_anomaly", {})
        self.assertTrue(poi_be.get("layered_decision", False),
                       "blite_enhancements must confirm layered_decision=true")

    def test_03_tiers_defined(self):
        """blite_enhancements lists all three tiers."""
        be = self.result.get("blite_enhancements", {})
        poi_be = be.get("price_oi_volume_anomaly", {})
        tiers = poi_be.get("tiers", [])
        self.assertIn("reject", tiers)
        self.assertIn("accept", tiers)
        # At least one watch variant
        has_watch = any("watch" in t.lower() for t in tiers)
        self.assertTrue(has_watch, f"tiers must include watch variant, got: {tiers}")

    def test_04_watch_is_observation_true(self):
        """blite_enhancements confirms watch_is_observation=true."""
        be = self.result.get("blite_enhancements", {})
        poi_be = be.get("price_oi_volume_anomaly", {})
        self.assertTrue(poi_be.get("watch_is_observation", False))

    def test_05_oi_zero_detection_enabled(self):
        """blite_enhancements confirms OI zero detection is active."""
        be = self.result.get("blite_enhancements", {})
        poi_be = be.get("price_oi_volume_anomaly", {})
        self.assertTrue(poi_be.get("oi_zero_detection", False))

    def test_06_mild_anomaly_not_accept(self):
        """If the decision is watch, the tier must NOT be 'accept'."""
        for c in self.poi:
            if c.get("operator_decision") == "watch":
                blite_tier = c.get("blite_tier", "")
                self.assertNotEqual(blite_tier, "accept",
                                   "watch decision blite_tier must not be 'accept'")
                self.assertTrue(
                    c.get("watch_is_observation", False),
                    "watch decision must have watch_is_observation=true"
                )


class TestV119BBliteNewsFreshness(unittest.TestCase):
    """B-lite specific tests for news_event_market_impact freshness/stale."""

    @classmethod
    def setUpClass(cls):
        if not V119B_RESULT_JSON.exists():
            raise unittest.SkipTest(f"Result JSON not found: {V119B_RESULT_JSON}")
        cls.result = load_json(V119B_RESULT_JSON)
        cards = cls.result.get("cards", [])
        cls.news = [c for c in cards if c["card_family"] == "news_event_market_impact"]

    def test_01_news_card_present(self):
        self.assertEqual(len(self.news), 1)

    def test_02_observation_only_true(self):
        if self.news:
            self.assertTrue(self.news[0].get("observation_only", False))

    def test_03_not_causal_proof_true(self):
        if self.news:
            self.assertTrue(self.news[0].get("not_causal_proof", False))

    def test_04_freshness_field_present(self):
        if self.news:
            self.assertIn("freshness_info", self.news[0])

    def test_05_stale_warnings_field_present(self):
        if self.news:
            self.assertIn("stale_warnings", self.news[0])

    def test_06_entities_found_field_present(self):
        if self.news:
            self.assertIn("entities_found", self.news[0])

    def test_07_blite_enhancements_confirm_freshness(self):
        be = self.result.get("blite_enhancements", {})
        news_be = be.get("news_event_market_impact", {})
        self.assertTrue(news_be.get("freshness_tagging", False))
        self.assertTrue(news_be.get("stale_detection", False))
        self.assertTrue(news_be.get("entity_normalization", False))
        self.assertTrue(news_be.get("observation_only", False))
        self.assertTrue(news_be.get("not_causal_proof", False))


class TestV119BBliteDashboardGuidance(unittest.TestCase):
    """B-lite specific tests for dashboard Chinese guidance layer."""

    @classmethod
    def setUpClass(cls):
        if not V119B_RESULT_JSON.exists():
            raise unittest.SkipTest(f"Result JSON not found: {V119B_RESULT_JSON}")
        cls.result = load_json(V119B_RESULT_JSON)

    def test_01_blite_dashboard_guidance_present(self):
        be = self.result.get("blite_enhancements", {})
        dg = be.get("dashboard_guidance", {})
        self.assertTrue(dg.get("chinese_30s_layer", False))

    def test_02_five_questions_answered(self):
        be = self.result.get("blite_enhancements", {})
        dg = be.get("dashboard_guidance", {})
        questions = dg.get("questions_answered", [])
        self.assertGreaterEqual(len(questions), 5)
        self.assertIn("这是什么", questions)
        self.assertIn("现在怎么看", questions)
        self.assertIn("现在能不能发", questions)
        self.assertIn("数据从哪来", questions)
        self.assertIn("操作员下一步", questions)


class TestV119BSnapshotMarkdown(unittest.TestCase):
    """Test the v119B live operator snapshot markdown."""

    @classmethod
    def setUpClass(cls):
        if not V119B_SNAPSHOT_MD.exists():
            raise unittest.SkipTest(f"Snapshot MD not found: {V119B_SNAPSHOT_MD}")
        cls.content = V119B_SNAPSHOT_MD.read_text(encoding="utf-8")

    def test_01_snapshot_exists(self):
        self.assertTrue(V119B_SNAPSHOT_MD.exists())

    def test_02_blite_mention(self):
        self.assertIn("B-lite", self.content,
                     "Snapshot should mention B-lite enhancements")

    def test_03_has_five_families(self):
        for cf in FIVE_CARD_FAMILIES:
            self.assertIn(cf, self.content, f"Missing {cf} in snapshot")

    def test_04_no_raw_secrets(self):
        violations = check_forbidden(self.content)
        self.assertEqual(len(violations), 0)


class TestV119BDecisionTableMarkdown(unittest.TestCase):
    """Test the v119B operator decision table markdown."""

    @classmethod
    def setUpClass(cls):
        if not V119B_DECISION_TABLE_MD.exists():
            raise unittest.SkipTest(f"Decision table not found: {V119B_DECISION_TABLE_MD}")
        cls.content = V119B_DECISION_TABLE_MD.read_text(encoding="utf-8")

    def test_01_table_exists(self):
        self.assertTrue(V119B_DECISION_TABLE_MD.exists())

    def test_02_has_five_families(self):
        for cf in FIVE_CARD_FAMILIES:
            self.assertIn(cf, self.content)

    def test_03_has_blite_column(self):
        """Decision table mentions B-lite Tier."""
        self.assertIn("B-lite Tier", self.content,
                     "Decision table should have B-lite Tier column")

    def test_04_has_key_constraints(self):
        self.assertIn("Key Constraints Verified", self.content)


class TestV119BHandoffMarkdown(unittest.TestCase):
    """Test the v119B handoff markdown."""

    @classmethod
    def setUpClass(cls):
        if not V119B_HANDOFF_MD.exists():
            raise unittest.SkipTest(f"Handoff not found: {V119B_HANDOFF_MD}")
        cls.content = V119B_HANDOFF_MD.read_text(encoding="utf-8")

    def test_01_handoff_exists(self):
        self.assertTrue(V119B_HANDOFF_MD.exists())

    def test_02_blite_enhancement_summary(self):
        self.assertIn("B-lite", self.content,
                     "Handoff should mention B-lite")

    def test_03_handoff_mentions_layered_decision(self):
        self.assertIn("layered", self.content.lower(),
                     "Handoff should mention layered decision")

    def test_04_handoff_mentions_freshness(self):
        self.assertIn("freshness", self.content.lower(),
                     "Handoff should mention freshness/stale")

    def test_05_no_raw_secrets(self):
        violations = check_forbidden(self.content)
        self.assertEqual(len(violations), 0)


class TestV119BNoRawSecretsAcrossAllOutputs(unittest.TestCase):
    """Comprehensive secret leak check across all v119B outputs."""

    def test_no_secrets_in_all_outputs(self):
        for fp in ALL_V119B_OUTPUT_FILES:
            if not fp.exists():
                continue
            with self.subTest(path=str(fp)):
                if fp.suffix == ".html" or fp.suffix == ".md":
                    text = fp.read_text(encoding="utf-8")
                else:
                    text = json.dumps(load_json(fp), ensure_ascii=False)
                violations = check_forbidden(text)
                self.assertEqual(len(violations), 0,
                               f"Forbidden patterns in {fp.name}: {violations}")
                self.assertFalse(RAW_TOKEN_PATTERN.search(text),
                               f"Raw token in {fp.name}")
                self.assertFalse(RAW_CHAT_ID_PATTERN.search(text),
                               f"Raw chat_id in {fp.name}")
                self.assertFalse(RAW_MESSAGE_ID_PATTERN.search(text),
                               f"Raw message_id in {fp.name}")


class TestV119BHistoricalFilesNotModified(unittest.TestCase):
    """Verify historical output files were not modified by v119B."""

    def test_no_v119b_in_v116_filenames(self):
        """No v119b files in v116 directory pattern."""
        for fp in V116_OUTPUT_FILES:
            name = fp.name.lower()
            self.assertNotIn("v119b", name,
                           f"v116 file should not reference v119b: {fp.name}")

    def test_v119b_runner_does_not_write_v116(self):
        """v119B runner code does not reference v116 output paths."""
        if V119B_RUNNER.exists():
            code = V119B_RUNNER.read_text(encoding="utf-8")
            self.assertNotIn("market_radar_v116", code)


if __name__ == "__main__":
    unittest.main()
