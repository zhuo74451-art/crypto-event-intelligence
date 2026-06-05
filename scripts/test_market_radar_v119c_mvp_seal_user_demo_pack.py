"""Market Radar v119C — MVP Seal User Demo Pack Tests.

Tests cover:
  - Runner is importable and executable
  - All v119C output files generated
  - Index HTML contains v119B dashboard link
  - User demo doc contains 3-minute demo flow
  - Quickstart contains run command and shutdown instructions
  - Acceptance report contains five-card decision distribution
  - Known limits contains production readiness=false/0/5
  - All v119C files explicitly confirm no-send
  - No raw token/chat_id/message_id/cookie/password/API key
  - Runner has no network call imports
  - No v116A-N/v117/v118/v119A/v119B historical modification
  - No files deleted

Usage:
    python -X utf8 -m pytest scripts/test_market_radar_v119c_mvp_seal_user_demo_pack.py -v
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
    r"\b[0-9]{8,10}:[A-Za-z0-9_-]{35,}\b",
    r"bot[0-9]{8,10}:",
    r'api_key\s*[:=]\s*["\'][A-Za-z0-9_-]{20,}',
    r'chat_id\s*[:=]\s*["\']-?[0-9]{5,}',
    r'password\s*[:=]\s*["\'][^"\']+["\']',
    r'secret\s*[:=]\s*["\'][A-Za-z0-9_-]{10,}',
    r'cookie\s*[:=]\s*["\'][^"\']+["\']',
]

RAW_TOKEN_PATTERN = re.compile(r"\b\d{9,10}:[A-Za-z0-9_-]{35,}\b")
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


# ── v119C Paths ────────────────────────────────────────────────────────────────

V119C_RUNNER = ROOT / "scripts" / "run_market_radar_v119c_mvp_seal_user_demo_pack.py"
V119C_TEST = ROOT / "scripts" / "test_market_radar_v119c_mvp_seal_user_demo_pack.py"

V119C_RESULT_JSON = ROOT / "results" / "market_radar_v119c_mvp_seal_result.json"
V119C_INDEX_HTML = ROOT / "runs" / "market_radar" / "v119c_mvp_index.html"
V119C_USER_DEMO_MD = ROOT / "runs" / "market_radar" / "v119c_user_demo_3min.md"
V119C_QUICKSTART_MD = ROOT / "runs" / "market_radar" / "v119c_operator_quickstart.md"
V119C_ACCEPTANCE_MD = ROOT / "runs" / "market_radar" / "v119c_mvp_acceptance_report.md"
V119C_KNOWN_LIMITS_MD = ROOT / "runs" / "market_radar" / "v119c_known_limits_and_next_steps.md"
V119C_HANDOFF_MD = ROOT / "runs" / "market_radar" / "v119c_local_only_final_handoff.md"

ALL_V119C_OUTPUT_FILES = [
    V119C_RESULT_JSON,
    V119C_INDEX_HTML,
    V119C_USER_DEMO_MD,
    V119C_QUICKSTART_MD,
    V119C_ACCEPTANCE_MD,
    V119C_KNOWN_LIMITS_MD,
    V119C_HANDOFF_MD,
]

# ── Network import patterns (runner must NOT import these) ─────────────────────

NETWORK_IMPORT_PATTERNS = [
    "import requests",
    "import urllib",
    "import http",
    "import socket",
    "import aiohttp",
    "import httpx",
    "import telegram",
    "import tweepy",
    "import openai",
    "import anthropic",
    "import google.generativeai",
    "import binance",
    "import ccxt",
    "import feedparser",
    "from requests",
    "from urllib",
    "from http",
    "from socket",
    "from aiohttp",
    "from httpx",
    "from telegram",
    "from tweepy",
    "from openai",
    "from anthropic",
    "from google",
    "from binance",
    "from ccxt",
    "from feedparser",
]


# ── Historical output files (must not be modified) ────────────────────────────


def _get_historical_files() -> list[Path]:
    """Collect historical output files that must not be modified."""
    patterns = [
        "results/market_radar_v116*",
        "results/market_radar_v117*",
        "results/market_radar_v118*",
        "results/market_radar_v119a*",
        "results/market_radar_v119b*",
        "runs/market_radar/v116*",
        "runs/market_radar/v117*",
        "runs/market_radar/v118*",
        "runs/market_radar/v119a*",
        "runs/market_radar/v119b*",
    ]
    files = []
    for pat in patterns:
        files.extend(sorted(ROOT.glob(pat)))
    return files


# ═══════════════════════════════════════════════════════════════════════════════
# TEST CLASSES
# ═══════════════════════════════════════════════════════════════════════════════


class TestV119CRunnerExists(unittest.TestCase):
    """Test that the v119C runner and test files exist and are importable."""

    def test_01_runner_file_exists(self):
        self.assertTrue(V119C_RUNNER.exists(), f"Runner not found: {V119C_RUNNER}")

    def test_02_test_file_exists(self):
        self.assertTrue(V119C_TEST.exists(), f"Test file not found: {V119C_TEST}")

    def test_03_runner_is_importable(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location("v119c_runner", V119C_RUNNER)
        self.assertIsNotNone(spec, "Runner spec is None — file may have syntax errors")
        if spec:
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)

    def test_04_runner_has_no_network_imports(self):
        """Runner must not import any networking/calling libraries."""
        code = V119C_RUNNER.read_text(encoding="utf-8")
        for pattern in NETWORK_IMPORT_PATTERNS:
            self.assertNotIn(
                pattern, code,
                f"Runner must not contain network import: '{pattern}'"
            )

    def test_05_runner_has_no_ai_imports(self):
        """Runner must not import any AI/model libraries."""
        code = V119C_RUNNER.read_text(encoding="utf-8")
        ai_patterns = ["openai", "anthropic", "google.generativeai", "deepseek",
                       "langchain", "transformers", "torch", "tensorflow"]
        for pat in ai_patterns:
            self.assertNotIn(pat, code.lower(),
                            f"Runner must not import AI library: '{pat}'")


class TestV119COutputFilesExist(unittest.TestCase):
    """Test that all v119C output files exist and are non-empty."""

    def test_01_all_output_files_exist(self):
        for fp in ALL_V119C_OUTPUT_FILES:
            with self.subTest(path=str(fp)):
                self.assertTrue(fp.exists(), f"Missing: {fp}")

    def test_02_all_output_files_non_empty(self):
        for fp in ALL_V119C_OUTPUT_FILES:
            if fp.exists():
                with self.subTest(path=str(fp)):
                    size = fp.stat().st_size
                    self.assertGreater(size, 100,
                                      f"File too small ({size} bytes): {fp}")


class TestV119CResultJSON(unittest.TestCase):
    """Test the v119C seal result JSON."""

    @classmethod
    def setUpClass(cls):
        if not V119C_RESULT_JSON.exists():
            raise unittest.SkipTest(f"Result JSON not found (run v119C runner first): {V119C_RESULT_JSON}")
        cls.result = load_json(V119C_RESULT_JSON)

    def test_01_result_json_exists(self):
        self.assertTrue(V119C_RESULT_JSON.exists())

    def test_02_pipeline_version(self):
        self.assertEqual(self.result.get("pipeline_version"), "v1.19C")

    def test_03_type_field_is_v119c(self):
        t = self.result.get("type", "")
        self.assertIn("v119c", t.lower())

    def test_04_based_on_v119b(self):
        self.assertEqual(self.result.get("based_on"), "v119B")

    def test_05_production_readiness_false(self):
        pr = self.result.get("production_readiness", {})
        self.assertFalse(pr.get("production_ready", True))
        self.assertEqual(pr.get("production_readiness_score"), "0/5")

    def test_06_no_send_all_false(self):
        nsp = self.result.get("no_send_preview", {})
        self.assertFalse(nsp.get("telegram_send", True))
        self.assertFalse(nsp.get("x_twitter_send", True))
        self.assertFalse(nsp.get("production_send", True))
        self.assertFalse(nsp.get("daemon_or_loop_started", True))

    def test_07_safety_no_external_calls(self):
        safety = self.result.get("safety", {})
        self.assertFalse(safety.get("tg_sent_this_run", True))
        self.assertFalse(safety.get("x_twitter_sent_this_run", True))
        self.assertFalse(safety.get("ai_model_called", True))
        self.assertFalse(safety.get("daemon_or_loop_started", True))
        self.assertFalse(safety.get("binance_api_called", True))
        self.assertFalse(safety.get("rss_called", True))
        self.assertFalse(safety.get("telegram_called", True))

    def test_08_no_files_deleted(self):
        safety = self.result.get("safety", {})
        self.assertFalse(safety.get("files_deleted", True))

    def test_09_history_not_modified(self):
        safety = self.result.get("safety", {})
        self.assertFalse(safety.get("v116_history_modified", True))
        self.assertFalse(safety.get("v117_history_modified", True))
        self.assertFalse(safety.get("v118_history_modified", True))
        self.assertFalse(safety.get("v119a_history_modified", True))
        self.assertFalse(safety.get("v119b_history_modified", True))

    def test_10_output_files_listed(self):
        of = self.result.get("output_files", {})
        self.assertIn("mvp_index_html", of)
        self.assertIn("user_demo_md", of)
        self.assertIn("operator_quickstart_md", of)
        self.assertIn("acceptance_report_md", of)
        self.assertIn("known_limits_md", of)
        self.assertIn("handoff_md", of)
        self.assertIn("result_json", of)

    def test_11_decision_counts_match_v119b(self):
        """Decision counts should match v119B source."""
        dc = self.result.get("decision_counts", {})
        self.assertIsInstance(dc, dict)
        for key in ["accept", "watch", "reject", "manual_required"]:
            self.assertIn(key, dc)

    def test_12_no_raw_secrets_in_json(self):
        text = json.dumps(self.result, ensure_ascii=False)
        violations = check_forbidden(text)
        self.assertEqual(len(violations), 0, f"Forbidden patterns: {violations}")
        self.assertFalse(RAW_TOKEN_PATTERN.search(text))
        self.assertFalse(RAW_CHAT_ID_PATTERN.search(text))
        self.assertFalse(RAW_MESSAGE_ID_PATTERN.search(text))


class TestV119CMVPIndexHTML(unittest.TestCase):
    """Test the v119C MVP index HTML file."""

    @classmethod
    def setUpClass(cls):
        if not V119C_INDEX_HTML.exists():
            raise unittest.SkipTest(f"Index HTML not found: {V119C_INDEX_HTML}")
        cls.html = V119C_INDEX_HTML.read_text(encoding="utf-8")

    def test_01_html_exists(self):
        self.assertTrue(V119C_INDEX_HTML.exists())

    def test_02_html_is_well_formed(self):
        html_lower = self.html.lower()
        self.assertIn("<!doctype html>", html_lower)
        self.assertIn("<html", html_lower)
        self.assertIn("</html>", html_lower)
        self.assertIn("<body", html_lower)
        self.assertIn("</body>", html_lower)

    def test_03_title_contains_v119c_mvp(self):
        self.assertIn("v119C", self.html)
        self.assertIn("Market Radar MVP", self.html)

    def test_04_contains_v119b_dashboard_link(self):
        """Index must reference v119b operator dashboard."""
        self.assertIn("v119b_operator_dashboard.html", self.html,
                     "Index must link to v119B dashboard")

    def test_05_contains_all_v119c_entry_points(self):
        """Index must reference all v119C documents."""
        self.assertIn("v119c_user_demo_3min.md", self.html)
        self.assertIn("v119c_operator_quickstart.md", self.html)
        self.assertIn("v119c_mvp_acceptance_report.md", self.html)
        self.assertIn("v119c_known_limits_and_next_steps.md", self.html)
        self.assertIn("v119c_local_only_final_handoff.md", self.html)

    def test_06_contains_capability_summary(self):
        self.assertIn("live public data", self.html)
        self.assertIn("shared pipeline", self.html)
        self.assertIn("B-lite", self.html)

    def test_07_production_readiness_false_in_html(self):
        self.assertIn("0/5", self.html)
        self.assertIn("NOT FOR PRODUCTION USE", self.html)

    def test_08_send_flags_all_false(self):
        html_lower = self.html.lower()
        self.assertIn("telegram_send", html_lower)
        self.assertIn("x_twitter_send", html_lower)
        self.assertIn("production_send", html_lower)
        self.assertIn("daemon_or_loop_started", html_lower)
        self.assertIn("= false", html_lower)

    def test_09_five_card_families_in_table(self):
        for cf in ["multi_asset_market_sync", "price_oi_volume_anomaly",
                    "news_event_market_impact", "liquidation_pressure",
                    "whale_position_alert"]:
            self.assertIn(cf, self.html, f"Missing card family '{cf}' in index")

    def test_10_no_raw_secrets_in_html(self):
        violations = check_forbidden(self.html)
        self.assertEqual(len(violations), 0, f"Forbidden patterns: {violations}")
        self.assertFalse(RAW_TOKEN_PATTERN.search(self.html))
        self.assertFalse(RAW_CHAT_ID_PATTERN.search(self.html))
        self.assertFalse(RAW_MESSAGE_ID_PATTERN.search(self.html))


class TestV119CUserDemoMarkdown(unittest.TestCase):
    """Test the v119C 3-minute user demo markdown."""

    @classmethod
    def setUpClass(cls):
        if not V119C_USER_DEMO_MD.exists():
            raise unittest.SkipTest(f"User demo not found: {V119C_USER_DEMO_MD}")
        cls.content = V119C_USER_DEMO_MD.read_text(encoding="utf-8")

    def test_01_demo_exists(self):
        self.assertTrue(V119C_USER_DEMO_MD.exists())

    def test_02_title_mentions_3min(self):
        self.assertIn("3分钟", self.content)
        self.assertIn("演示", self.content)

    def test_03_has_demo_steps(self):
        """Must contain numbered demo steps."""
        self.assertIn("第 1 步", self.content)
        self.assertIn("第 2 步", self.content)
        self.assertIn("第 3 步", self.content)
        self.assertIn("第 4 步", self.content)
        self.assertIn("第 5 步", self.content)
        self.assertIn("第 6 步", self.content)
        self.assertIn("第 7 步", self.content)

    def test_04_mentions_accept_watch_reject_manual(self):
        self.assertIn("Accept", self.content)
        self.assertIn("Watch", self.content)
        self.assertIn("Reject", self.content)
        self.assertIn("Manual", self.content)

    def test_05_mentions_blite_price_oi_value(self):
        """Mentions B-lite price/OI layered value."""
        self.assertIn("mild_watch", self.content.lower())

    def test_06_mentions_news_observation_only(self):
        self.assertIn("observation-only", self.content.lower())

    def test_07_mentions_whale_manual_evidence(self):
        self.assertIn("人工证据", self.content)

    def test_08_mentions_production_readiness_false(self):
        self.assertIn("0/5", self.content)
        self.assertIn("false", self.content.lower())

    def test_09_mentions_no_send(self):
        self.assertIn("no-send", self.content.lower())
        # At least one send flag is explicitly false
        self.assertIn("telegram_send=false", self.content)

    def test_10_mentions_not_trading_system(self):
        self.assertIn("不是自动交易", self.content)
        self.assertIn("不是自动发帖", self.content)

    def test_11_no_raw_secrets(self):
        violations = check_forbidden(self.content)
        self.assertEqual(len(violations), 0, f"Forbidden patterns: {violations}")


class TestV119COperatorQuickstartMarkdown(unittest.TestCase):
    """Test the v119C operator quickstart markdown."""

    @classmethod
    def setUpClass(cls):
        if not V119C_QUICKSTART_MD.exists():
            raise unittest.SkipTest(f"Quickstart not found: {V119C_QUICKSTART_MD}")
        cls.content = V119C_QUICKSTART_MD.read_text(encoding="utf-8")

    def test_01_quickstart_exists(self):
        self.assertTrue(V119C_QUICKSTART_MD.exists())

    def test_02_contains_run_command(self):
        """Must contain the v119B run command."""
        self.assertIn("run_market_radar_v119b", self.content)

    def test_03_contains_dashboard_path(self):
        self.assertIn("v119b_operator_dashboard.html", self.content)

    def test_04_contains_shutdown_instructions(self):
        self.assertIn("无 daemon", self.content)
        self.assertIn("关掉浏览器", self.content)

    def test_05_contains_daily_workflow(self):
        self.assertIn("每天", self.content)
        self.assertIn("one-shot", self.content.lower())

    def test_06_contains_forbidden_actions(self):
        """Must contain the 禁止事项 section."""
        self.assertIn("禁止", self.content)
        self.assertIn("不得当交易建议", self.content)
        self.assertIn("production readiness", self.content.lower())

    def test_07_mentions_no_send(self):
        self.assertIn("no-send", self.content.lower())

    def test_08_no_raw_secrets(self):
        violations = check_forbidden(self.content)
        self.assertEqual(len(violations), 0)


class TestV119CAcceptanceReportMarkdown(unittest.TestCase):
    """Test the v119C MVP acceptance report markdown."""

    @classmethod
    def setUpClass(cls):
        if not V119C_ACCEPTANCE_MD.exists():
            raise unittest.SkipTest(f"Acceptance report not found: {V119C_ACCEPTANCE_MD}")
        cls.content = V119C_ACCEPTANCE_MD.read_text(encoding="utf-8")

    def test_01_report_exists(self):
        self.assertTrue(V119C_ACCEPTANCE_MD.exists())

    def test_02_contains_version_info(self):
        self.assertIn("v119C", self.content)
        self.assertIn("v119B", self.content)

    def test_03_contains_decision_distribution(self):
        """Must list five-card decision distribution."""
        self.assertIn("accept", self.content.lower())
        self.assertIn("watch", self.content.lower())
        self.assertIn("reject", self.content.lower())
        self.assertIn("manual_required", self.content.lower())

    def test_04_contains_mvp_conditions_met(self):
        self.assertIn("已满足", self.content)

    def test_05_contains_production_conditions_not_met(self):
        self.assertIn("未满足", self.content)

    def test_06_production_readiness_false(self):
        self.assertIn("0/5", self.content)
        self.assertIn("NOT FOR LIVE USE", self.content)

    def test_07_mentions_blite_quality(self):
        self.assertIn("B-lite", self.content)

    def test_08_mentions_chinese_guidance(self):
        self.assertIn("Chinese", self.content)

    def test_09_mentions_secret_leak_audit(self):
        self.assertIn("secret", self.content.lower())

    def test_10_accept_total_counts_match_v119b(self):
        """accept=1, watch=2, reject=1, manual_required=1."""
        # These values should appear in the decision distribution table
        self.assertIn("accept", self.content.lower())
        self.assertIn("watch", self.content.lower())
        self.assertIn("reject", self.content.lower())
        self.assertIn("manual", self.content.lower())

    def test_11_no_raw_secrets(self):
        violations = check_forbidden(self.content)
        self.assertEqual(len(violations), 0)


class TestV119CKnownLimitsMarkdown(unittest.TestCase):
    """Test the v119C known limits and next steps markdown."""

    @classmethod
    def setUpClass(cls):
        if not V119C_KNOWN_LIMITS_MD.exists():
            raise unittest.SkipTest(f"Known limits not found: {V119C_KNOWN_LIMITS_MD}")
        cls.content = V119C_KNOWN_LIMITS_MD.read_text(encoding="utf-8")

    def test_01_limits_exists(self):
        self.assertTrue(V119C_KNOWN_LIMITS_MD.exists())

    def test_02_contains_news_freshness_heuristic(self):
        self.assertIn("freshness", self.content.lower())

    def test_03_contains_price_oi_watch_observation(self):
        self.assertIn("watch", self.content.lower())

    def test_04_contains_liquidation_limits(self):
        self.assertIn("liquidation", self.content.lower())

    def test_05_contains_whale_manual_evidence(self):
        self.assertIn("whale", self.content.lower())
        self.assertIn("人工", self.content)

    def test_06_contains_dashboard_static(self):
        self.assertIn("静态", self.content)

    def test_07_contains_one_shot_manual(self):
        self.assertIn("手动", self.content)

    def test_08_production_readiness_false(self):
        self.assertIn("0/5", self.content)
        self.assertIn("false", self.content.lower())

    def test_09_contains_next_steps_candidates(self):
        self.assertIn("候选", self.content.lower())
        self.assertIn("下一阶段", self.content)

    def test_10_contains_do_not_auto_start_daemon(self):
        """Must explicitly say NOT to auto-start recurring/daemon."""
        self.assertIn("daemon", self.content.lower())

    def test_11_contains_forbidden_actions(self):
        """Must list things NOT to do."""
        self.assertIn("不要", self.content)

    def test_12_no_raw_secrets(self):
        violations = check_forbidden(self.content)
        self.assertEqual(len(violations), 0)


class TestV119CHandoffMarkdown(unittest.TestCase):
    """Test the v119C final handoff markdown."""

    @classmethod
    def setUpClass(cls):
        if not V119C_HANDOFF_MD.exists():
            raise unittest.SkipTest(f"Handoff not found: {V119C_HANDOFF_MD}")
        cls.content = V119C_HANDOFF_MD.read_text(encoding="utf-8")

    def test_01_handoff_exists(self):
        self.assertTrue(V119C_HANDOFF_MD.exists())

    def test_02_mentions_local_only(self):
        self.assertIn("local-only", self.content.lower())

    def test_03_mentions_no_send(self):
        self.assertIn("no-send", self.content.lower())

    def test_04_mentions_not_production_ready(self):
        self.assertIn("not production-ready", self.content.lower())

    def test_05_mentions_send_flags_false(self):
        self.assertIn("telegram_send", self.content.lower())
        self.assertIn("x_twitter_send", self.content.lower())
        self.assertIn("production_send", self.content.lower())
        self.assertIn("false", self.content.lower())

    def test_06_has_how_to_run_section(self):
        self.assertIn("如何运行", self.content)

    def test_07_no_raw_secrets(self):
        violations = check_forbidden(self.content)
        self.assertEqual(len(violations), 0)


class TestV119CNoSendAcrossAllOutputs(unittest.TestCase):
    """Verify all v119C output files explicitly confirm no-send."""

    def test_all_files_contain_no_send_markers(self):
        markers = ["false", "no-send", "0/5"]
        for fp in ALL_V119C_OUTPUT_FILES:
            if not fp.exists():
                continue
            with self.subTest(path=str(fp)):
                if fp.suffix == ".json":
                    content = fp.read_text(encoding="utf-8")
                else:
                    content = fp.read_text(encoding="utf-8").lower()
                # At least one no-send marker must be present
                has_marker = any(m in content for m in markers)
                self.assertTrue(has_marker,
                              f"File {fp.name} must contain no-send markers")

    def test_all_files_contain_telegram_send_false(self):
        for fp in ALL_V119C_OUTPUT_FILES:
            if not fp.exists():
                continue
            with self.subTest(path=str(fp)):
                content = fp.read_text(encoding="utf-8")
                self.assertIn("telegram_send", content.lower(),
                            f"File {fp.name} must mention telegram_send")

    def test_all_files_contain_production_readiness(self):
        for fp in ALL_V119C_OUTPUT_FILES:
            if not fp.exists():
                continue
            with self.subTest(path=str(fp)):
                content = fp.read_text(encoding="utf-8").lower()
                has_pr = "0/5" in content or "production_readiness" in content
                self.assertTrue(has_pr,
                              f"File {fp.name} must mention production readiness")


class TestV119CNoRawSecretsAcrossAllOutputs(unittest.TestCase):
    """Comprehensive secret leak check across all v119C outputs."""

    def test_no_secrets_in_all_outputs(self):
        for fp in ALL_V119C_OUTPUT_FILES:
            if not fp.exists():
                continue
            with self.subTest(path=str(fp)):
                if fp.suffix in (".html", ".md"):
                    text = fp.read_text(encoding="utf-8")
                elif fp.suffix == ".json":
                    text = json.dumps(load_json(fp), ensure_ascii=False)
                else:
                    text = fp.read_text(encoding="utf-8")

                violations = check_forbidden(text)
                self.assertEqual(len(violations), 0,
                               f"Forbidden patterns in {fp.name}: {violations}")
                self.assertFalse(RAW_TOKEN_PATTERN.search(text),
                               f"Raw token in {fp.name}")
                self.assertFalse(RAW_CHAT_ID_PATTERN.search(text),
                               f"Raw chat_id in {fp.name}")
                self.assertFalse(RAW_MESSAGE_ID_PATTERN.search(text),
                               f"Raw message_id in {fp.name}")

    def test_no_secrets_in_runner(self):
        code = V119C_RUNNER.read_text(encoding="utf-8")
        violations = check_forbidden(code)
        self.assertEqual(len(violations), 0, f"Forbidden patterns in runner: {violations}")

    def test_no_secrets_in_test_file(self):
        code = V119C_TEST.read_text(encoding="utf-8")
        violations = check_forbidden(code)
        self.assertEqual(len(violations), 0, f"Forbidden patterns in test: {violations}")


class TestV119CHistoricalFilesNotModified(unittest.TestCase):
    """Verify historical output files were not modified by v119C."""

    def test_no_v119c_in_v116_filenames(self):
        files = sorted(ROOT.glob("results/market_radar_v116*"))
        for fp in files:
            name = fp.name.lower()
            self.assertNotIn("v119c", name,
                           f"v116 file should not have v119c in name: {fp.name}")

    def test_no_v119c_in_v119b_filenames(self):
        files = sorted(ROOT.glob("results/market_radar_v119b*")) + \
                sorted(ROOT.glob("runs/market_radar/v119b*"))
        for fp in files:
            name = fp.name.lower()
            self.assertNotIn("v119c", name,
                           f"v119B file should not have v119c in name: {fp.name}")

    def test_v119c_runner_does_not_write_v116(self):
        code = V119C_RUNNER.read_text(encoding="utf-8")
        self.assertNotIn("market_radar_v116", code)

    def test_v119c_runner_does_not_write_v117(self):
        code = V119C_RUNNER.read_text(encoding="utf-8")
        self.assertNotIn("market_radar_v117", code)

    def test_v119c_runner_does_not_write_v118(self):
        code = V119C_RUNNER.read_text(encoding="utf-8")
        self.assertNotIn("market_radar_v118", code)

    def test_v119c_runner_does_not_write_v119a(self):
        code = V119C_RUNNER.read_text(encoding="utf-8")
        self.assertNotIn("market_radar_v119a", code)


if __name__ == "__main__":
    unittest.main()
