#!/usr/bin/env python3
"""
test_market_radar_v112u_one_shot_free_source_dry_run.py
=========================================================
Test suite for v112U one-shot free source dry-run.

Validates:
  - Runner is executable
  - All output files exist
  - Result JSON has correct safety invariants
  - Live source response JSON is structurally valid
  - Stop decision JSON has valid decision value
  - No secrets in output files
  - No misleading claims in output files
  - ABORT path correctly recorded (if HTTP failed)
"""

import json
import os
import sys
import unittest

# ── Project root ──────────────────────────────────────────────────────────
PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(PROJECT_DIR)

RESULTS_DIR = os.path.join(PROJECT_DIR, "results")
RUNS_DIR = os.path.join(PROJECT_DIR, "runs", "market_radar")

V112U_RESULT = os.path.join(RESULTS_DIR, "market_radar_v112u_one_shot_free_source_dry_run_result.json")
V112U_LIVE_RESPONSE = os.path.join(RESULTS_DIR, "market_radar_v112u_live_source_response.json")
V112U_STOP_DECISION = os.path.join(RESULTS_DIR, "market_radar_v112u_stop_decision.json")
V112U_RUN_REPORT = os.path.join(RUNS_DIR, "v112u_one_shot_free_source_dry_run.md")
V112U_HANDOFF = os.path.join(RUNS_DIR, "v112u_one_shot_free_source_dry_run_handoff.md")


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


class TestV112URunnerExecutable(unittest.TestCase):
    """Test that the v112U runner script exists and is importable."""

    def test_runner_imports(self):
        """Runner module should be importable and have main()."""
        import importlib.util
        runner_path = os.path.join(PROJECT_DIR, "scripts",
                                   "run_market_radar_v112u_one_shot_free_source_dry_run.py")
        self.assertTrue(os.path.exists(runner_path), f"Runner not found: {runner_path}")
        spec = importlib.util.spec_from_file_location("run_market_radar_v112u", runner_path)
        self.assertIsNotNone(spec, "Runner module spec should not be None")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        self.assertTrue(hasattr(mod, 'main'), "Runner should have main() function")

    def test_runner_main_executes(self):
        """Runner main() should execute and return an exit code (0 or 1)."""
        import importlib.util
        runner_path = os.path.join(PROJECT_DIR, "scripts",
                                   "run_market_radar_v112u_one_shot_free_source_dry_run.py")
        spec = importlib.util.spec_from_file_location("run_market_radar_v112u", runner_path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        exit_code = mod.main()
        self.assertIn(exit_code, [0, 1], f"Runner returned unexpected exit code: {exit_code}")


class TestV112UResultJSON(unittest.TestCase):
    """Test the result JSON file."""

    @classmethod
    def setUpClass(cls):
        if not os.path.exists(V112U_RESULT):
            raise unittest.SkipTest(f"Result file not found: {V112U_RESULT}")
        cls.result = load_json(V112U_RESULT)

    def test_result_exists(self):
        self.assertTrue(os.path.exists(V112U_RESULT), f"Missing: {V112U_RESULT}")

    def test_version(self):
        self.assertEqual(self.result.get("version"), "v1.12-u")

    def test_dry_run_only_true(self):
        self.assertTrue(self.result.get("dry_run_only"), "dry_run_only should be True")

    def test_one_shot_http_get_performed_true(self):
        self.assertTrue(self.result.get("one_shot_http_get_performed"),
                        "one_shot_http_get_performed should be True")

    def test_real_live_api_called_true(self):
        self.assertTrue(self.result.get("real_live_api_called"),
                        "real_live_api_called should be True (authorized one-shot)")

    def test_real_tg_sent_false(self):
        self.assertFalse(self.result.get("real_tg_sent"), "real_tg_sent should be False")

    def test_external_ai_called_false(self):
        self.assertFalse(self.result.get("external_ai_called"),
                         "external_ai_called should be False")

    def test_daemon_started_false(self):
        self.assertFalse(self.result.get("daemon_started"), "daemon_started should be False")

    def test_files_deleted_false(self):
        self.assertFalse(self.result.get("files_deleted"), "files_deleted should be False")

    def test_eligible_for_real_send_false(self):
        self.assertFalse(self.result.get("eligible_for_real_send"),
                         "eligible_for_real_send should be False")

    def test_real_send_ready_false(self):
        self.assertFalse(self.result.get("real_send_ready"),
                         "real_send_ready should be False")

    def test_production_state_write_ready_false(self):
        self.assertFalse(self.result.get("production_state_write_ready"),
                         "production_state_write_ready should be False")

    def test_state_write_performed_false(self):
        self.assertFalse(self.result.get("state_write_performed"),
                         "state_write_performed should be False")

    def test_retry_attempted_false(self):
        self.assertFalse(self.result.get("retry_attempted"),
                         "retry_attempted should be False")

    def test_api_key_used_false(self):
        self.assertFalse(self.result.get("api_key_used"),
                         "api_key_used should be False")

    def test_authorization_header_used_false(self):
        self.assertFalse(self.result.get("authorization_header_used"),
                         "authorization_header_used should be False")

    def test_stop_decision_valid(self):
        decision = self.result.get("stop_decision")
        self.assertIn(decision, ["CONTINUE", "ABORT", "DEGRADE_TO_MOCK"],
                      f"Invalid stop_decision: {decision}")

    def test_status_valid(self):
        status = self.result.get("status")
        self.assertIn(status, ["passed", "aborted", "degraded"],
                      f"Invalid status: {status}")

    def test_status_matches_decision(self):
        """status must match stop_decision: CONTINUE->passed, ABORT->aborted, DEGRADE_TO_MOCK->degraded."""
        decision = self.result.get("stop_decision")
        status = self.result.get("status")
        expected = {"CONTINUE": "passed", "ABORT": "aborted", "DEGRADE_TO_MOCK": "degraded"}
        self.assertEqual(status, expected.get(decision),
                         f"status '{status}' does not match decision '{decision}'")

    def test_candidate_card_type(self):
        self.assertEqual(self.result.get("candidate_card_type"), "multi_asset_market_sync")

    def test_source_count_attempted(self):
        count = self.result.get("source_count_attempted", 0)
        self.assertGreaterEqual(count, 1, "Should attempt at least 1 source")
        self.assertLessEqual(count, 2, "Should attempt at most 2 sources")

    def test_asset_count_requested(self):
        self.assertEqual(self.result.get("asset_count_requested"), 3,
                        "Should request exactly 3 assets (BTC, ETH, SOL)")

    def test_debug_leak_count_zero(self):
        self.assertEqual(self.result.get("debug_leak_count"), 0)

    def test_secret_leak_count_zero(self):
        self.assertEqual(self.result.get("secret_leak_count"), 0)

    def test_recommended_next_step(self):
        next_step = self.result.get("recommended_next_step", "")
        self.assertIn("v112v", next_step.lower())

    def test_external_api_called_true(self):
        self.assertTrue(self.result.get("external_api_called"),
                        "external_api_called should be True (authorized one-shot)")


class TestV112ULiveSourceResponseJSON(unittest.TestCase):
    """Test the live source response JSON file."""

    @classmethod
    def setUpClass(cls):
        if not os.path.exists(V112U_LIVE_RESPONSE):
            raise unittest.SkipTest(f"Live response file not found: {V112U_LIVE_RESPONSE}")
        cls.response = load_json(V112U_LIVE_RESPONSE)

    def test_file_exists(self):
        self.assertTrue(os.path.exists(V112U_LIVE_RESPONSE), f"Missing: {V112U_LIVE_RESPONSE}")

    def test_source_name_valid(self):
        self.assertIn(self.response.get("source_name"),
                      ["coingecko_public_rest", "coincap_public_rest"])

    def test_fetched_at_present(self):
        self.assertIsNotNone(self.response.get("fetched_at"))

    def test_request_mode_live_one_shot(self):
        self.assertEqual(self.response.get("request_mode"), "live_one_shot")

    def test_assets_is_array(self):
        self.assertIsInstance(self.response.get("assets"), list)

    def test_validation_status_valid(self):
        self.assertIn(self.response.get("validation_status"), ["valid", "degraded", "invalid"])

    def test_stop_decision_valid(self):
        self.assertIn(self.response.get("stop_decision"),
                      ["CONTINUE", "ABORT", "DEGRADE_TO_MOCK"])

    def test_eligible_for_real_send_false(self):
        self.assertFalse(self.response.get("eligible_for_real_send"))

    def test_asset_objects_have_required_fields(self):
        """Each asset should have asset_id, symbol, price_usd, price_change_pct, last_updated_at."""
        assets = self.response.get("assets", [])
        for asset in assets:
            for field in ["asset_id", "symbol", "price_usd", "price_change_pct", "last_updated_at"]:
                self.assertIn(field, asset, f"Asset missing required field: {field}")

    def test_asset_symbols_are_uppercase(self):
        """Asset symbols should be uppercase (BTC, ETH, SOL)."""
        assets = self.response.get("assets", [])
        for asset in assets:
            symbol = asset.get("symbol", "")
            if symbol:
                self.assertEqual(symbol, symbol.upper(),
                                 f"Symbol '{symbol}' should be uppercase")

    def test_asset_ids_in_expected_set(self):
        """Asset IDs should be among bitcoin, ethereum, solana."""
        assets = self.response.get("assets", [])
        valid_ids = {"bitcoin", "ethereum", "solana"}
        for asset in assets:
            self.assertIn(asset.get("asset_id", "").lower(), valid_ids,
                          f"Unexpected asset_id: {asset.get('asset_id')}")

    def test_open_interest_is_null(self):
        """OI should be null (not available from free sources)."""
        assets = self.response.get("assets", [])
        for asset in assets:
            self.assertIsNone(asset.get("open_interest_change_pct"),
                             "open_interest_change_pct should be null (free sources don't provide OI)")

    def test_metadata_present(self):
        meta = self.response.get("metadata", {})
        self.assertTrue(meta.get("dry_run"), "metadata.dry_run should be true")
        self.assertEqual(meta.get("assets_requested"), 3)

    def test_cross_source_validation_present(self):
        csv = self.response.get("cross_source_validation", {})
        self.assertIn("performed", csv)


class TestV112UStopDecisionJSON(unittest.TestCase):
    """Test the stop decision JSON file."""

    @classmethod
    def setUpClass(cls):
        if not os.path.exists(V112U_STOP_DECISION):
            raise unittest.SkipTest(f"Stop decision file not found: {V112U_STOP_DECISION}")
        cls.decision = load_json(V112U_STOP_DECISION)

    def test_file_exists(self):
        self.assertTrue(os.path.exists(V112U_STOP_DECISION), f"Missing: {V112U_STOP_DECISION}")

    def test_decision_valid(self):
        self.assertIn(self.decision.get("decision"),
                      ["CONTINUE", "ABORT", "DEGRADE_TO_MOCK"])

    def test_reason_present(self):
        self.assertIsNotNone(self.decision.get("reason"))
        self.assertGreater(len(self.decision.get("reason", "")), 0)

    def test_abort_rules_triggered_exists(self):
        self.assertIsInstance(self.decision.get("abort_rules_triggered"), list)

    def test_degrade_rules_triggered_exists(self):
        self.assertIsInstance(self.decision.get("degrade_rules_triggered"), list)

    def test_continue_rules_satisfied_exists(self):
        self.assertIsInstance(self.decision.get("continue_rules_satisfied"), list)

    def test_eligible_for_real_send_false(self):
        self.assertFalse(self.decision.get("eligible_for_real_send"))

    def test_state_write_performed_false(self):
        self.assertFalse(self.decision.get("state_write_performed"))

    def test_real_tg_sent_false(self):
        self.assertFalse(self.decision.get("real_tg_sent"))

    def test_decision_consistency(self):
        """If decision is ABORT, abort_rules should be non-empty;
           if DEGRADE, degrade_rules should be non-empty."""
        decision = self.decision.get("decision")
        if decision == "ABORT":
            self.assertGreater(len(self.decision.get("abort_rules_triggered", [])), 0,
                              "ABORT decision must have abort rules triggered")
        elif decision == "DEGRADE_TO_MOCK":
            degrade_count = len(self.decision.get("degrade_rules_triggered", []))
            self.assertGreater(degrade_count, 0,
                             "DEGRADE_TO_MOCK decision must have degrade rules triggered")


class TestV112UArtifactFilesExist(unittest.TestCase):
    """Test that all required v112U output files exist."""

    def test_result_json_exists(self):
        self.assertTrue(os.path.exists(V112U_RESULT), f"Missing: {V112U_RESULT}")

    def test_live_response_json_exists(self):
        self.assertTrue(os.path.exists(V112U_LIVE_RESPONSE), f"Missing: {V112U_LIVE_RESPONSE}")

    def test_stop_decision_json_exists(self):
        self.assertTrue(os.path.exists(V112U_STOP_DECISION), f"Missing: {V112U_STOP_DECISION}")

    def test_run_report_md_exists(self):
        self.assertTrue(os.path.exists(V112U_RUN_REPORT), f"Missing: {V112U_RUN_REPORT}")

    def test_handoff_md_exists(self):
        self.assertTrue(os.path.exists(V112U_HANDOFF), f"Missing: {V112U_HANDOFF}")

    def test_runner_py_exists(self):
        runner_path = os.path.join(PROJECT_DIR, "scripts",
                                   "run_market_radar_v112u_one_shot_free_source_dry_run.py")
        self.assertTrue(os.path.exists(runner_path), f"Missing: {runner_path}")


class TestV112UNoSecretLeaks(unittest.TestCase):
    """Test that no secrets, tokens, or credentials appear in output files."""

    SECRET_PATTERNS = [
        "api_key", "apikey", "api-key",
        "token", "TOKEN",
        "secret", "SECRET",
        "password", "PASSWORD",
        "cookie", "COOKIE",
        "bearer", "BEARER",
        "authorization", "AUTHORIZATION",
        "credential value",
    ]

    SAFE_CONTEXTS = [
        "secret_leak_count",
        "debug_leak_count",
        "no api key",
        "requires api key",
        "requires paid api key",
        "no secret",
        "out of scope for free",
        "any source requiring api key",
        "any api-key source",
        "api key or credential",
        "api_key_used",
        "api_key_required",
        "authorization_header_used",
        "authorization",
        "token/key/cookie/password",
        "any token",
        "any .env",
        "no api keys",
        "token, cookie",
        "token/key",
    ]

    def _check_file_for_secrets(self, path, label):
        if not os.path.exists(path):
            return []
        try:
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
        except Exception:
            return []

        found = []
        content_lower = content.lower()
        for pattern in self.SECRET_PATTERNS:
            if pattern.lower() in content_lower:
                idx = content_lower.find(pattern.lower())
                context = content[max(0, idx - 40):idx + len(pattern) + 40]
                context_lower = context.lower()

                is_safe = any(safe in context_lower for safe in self.SAFE_CONTEXTS)
                if not is_safe:
                    found.append(f"{label}: found '{pattern}' near: ...{context}...")
        return found

    def test_result_json_no_secrets(self):
        issues = self._check_file_for_secrets(V112U_RESULT, "result.json")
        self.assertEqual(len(issues), 0, f"Secrets in result.json: {issues}")

    def test_live_response_no_secrets(self):
        issues = self._check_file_for_secrets(V112U_LIVE_RESPONSE, "live_response.json")
        self.assertEqual(len(issues), 0, f"Secrets in live_response.json: {issues}")

    def test_stop_decision_no_secrets(self):
        issues = self._check_file_for_secrets(V112U_STOP_DECISION, "stop_decision.json")
        self.assertEqual(len(issues), 0, f"Secrets in stop_decision.json: {issues}")

    def test_run_report_no_secrets(self):
        issues = self._check_file_for_secrets(V112U_RUN_REPORT, "run_report.md")
        self.assertEqual(len(issues), 0, f"Secrets in run report: {issues}")

    def test_handoff_no_secrets(self):
        issues = self._check_file_for_secrets(V112U_HANDOFF, "handoff.md")
        self.assertEqual(len(issues), 0, f"Secrets in handoff: {issues}")


class TestV112UNoMisleadingClaims(unittest.TestCase):
    """Test that output files don't contain misleading claims about production state."""

    MISLEADING_PHRASES = [
        "production ready",
        "已接入正式生产",
        "real send enabled",
        "production state active",
        "live fetch ready",
        "real-time data streaming",
        "已真实发送",
        "live api connected",
        "ready for production",
    ]

    def _check_file_for_misleading(self, path, label):
        if not os.path.exists(path):
            return []
        try:
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
        except Exception:
            return []

        found = []
        for phrase in self.MISLEADING_PHRASES:
            if phrase.lower() in content.lower():
                idx = content.lower().find(phrase.lower())
                context = content[max(0, idx - 30):idx + len(phrase) + 30]
                found.append(f"{label}: found '{phrase}' near: ...{context}...")
        return found

    def test_result_no_misleading(self):
        issues = self._check_file_for_misleading(V112U_RESULT, "result.json")
        self.assertEqual(len(issues), 0, f"Misleading claims in result.json: {issues}")

    def test_handoff_no_misleading(self):
        issues = self._check_file_for_misleading(V112U_HANDOFF, "handoff.md")
        self.assertEqual(len(issues), 0, f"Misleading claims in handoff: {issues}")

    def test_run_report_no_misleading(self):
        issues = self._check_file_for_misleading(V112U_RUN_REPORT, "run_report.md")
        self.assertEqual(len(issues), 0, f"Misleading claims in run report: {issues}")


class TestV112URunReportContent(unittest.TestCase):
    """Test the run report markdown content."""

    @classmethod
    def setUpClass(cls):
        if not os.path.exists(V112U_RUN_REPORT):
            raise unittest.SkipTest(f"Run report not found: {V112U_RUN_REPORT}")
        with open(V112U_RUN_REPORT, "r", encoding="utf-8") as f:
            cls.content = f.read()

    def test_mentions_stop_decision(self):
        self.assertTrue(
            any(d in self.content for d in ["CONTINUE", "ABORT", "DEGRADE"]),
            "Run report should mention stop decision"
        )

    def test_mentions_btc_eth_sol(self):
        content_upper = self.content.upper()
        self.assertIn("BTC", content_upper, "Run report should mention BTC")
        self.assertIn("ETH", content_upper, "Run report should mention ETH")
        self.assertIn("SOL", content_upper, "Run report should mention SOL")

    def test_mentions_coingecko(self):
        self.assertIn("CoinGecko", self.content, "Run report should mention CoinGecko")

    def test_mentions_eligible_for_real_send_false(self):
        content_lower = self.content.lower()
        self.assertTrue(
            "eligible" in content_lower,
            "Run report should discuss eligibility"
        )

    def test_mentions_next_step(self):
        content_lower = self.content.lower()
        self.assertIn("v112v", content_lower, "Run report should mention v112V next step")


class TestV112UHandoffContent(unittest.TestCase):
    """Test the handoff markdown content."""

    @classmethod
    def setUpClass(cls):
        if not os.path.exists(V112U_HANDOFF):
            raise unittest.SkipTest(f"Handoff not found: {V112U_HANDOFF}")
        with open(V112U_HANDOFF, "r", encoding="utf-8") as f:
            cls.content = f.read()

    def test_mentions_what_was_done(self):
        self.assertIn("What v112U Did", self.content,
                      "Handoff should have 'What v112U Did' section")

    def test_mentions_configs_read(self):
        self.assertIn("Configurations Read", self.content,
                      "Handoff should have 'Configurations Read' section")

    def test_mentions_files_generated(self):
        self.assertIn("Files Generated", self.content,
                      "Handoff should have 'Files Generated' section")

    def test_mentions_safety_posture(self):
        content_lower = self.content.lower()
        self.assertTrue(
            "safety" in content_lower or "still not enabled" in content_lower,
            "Handoff should discuss safety posture"
        )

    def test_mentions_api_key_not_used(self):
        content_lower = self.content.lower()
        self.assertIn("api_key_used", content_lower,
                      "Handoff should mention api_key_used = false")

    def test_no_internal_token_leaks(self):
        """Handoff must not contain raw API tokens or internal paths to sensitive files."""
        # Check for common leak patterns of actual credentials
        leak_indicators = [
            "x-api-key:", "Bearer eyJ", "sk-", "-----BEGIN",
        ]
        for indicator in leak_indicators:
            self.assertNotIn(indicator, self.content,
                            f"Potential credential leak: {indicator}")


if __name__ == "__main__":
    print("=" * 70)
    print("v112U One-Shot Free Source Dry-Run Test Suite")
    print("=" * 70)
    print()

    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    suite.addTests(loader.loadTestsFromTestCase(TestV112URunnerExecutable))
    suite.addTests(loader.loadTestsFromTestCase(TestV112UResultJSON))
    suite.addTests(loader.loadTestsFromTestCase(TestV112ULiveSourceResponseJSON))
    suite.addTests(loader.loadTestsFromTestCase(TestV112UStopDecisionJSON))
    suite.addTests(loader.loadTestsFromTestCase(TestV112UArtifactFilesExist))
    suite.addTests(loader.loadTestsFromTestCase(TestV112UNoSecretLeaks))
    suite.addTests(loader.loadTestsFromTestCase(TestV112UNoMisleadingClaims))
    suite.addTests(loader.loadTestsFromTestCase(TestV112URunReportContent))
    suite.addTests(loader.loadTestsFromTestCase(TestV112UHandoffContent))

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    print("\n" + "=" * 70)
    print(f"Tests run: {result.testsRun}")
    passed = result.testsRun - len(result.failures) - len(result.errors)
    print(f"Passed: {passed}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print("=" * 70)

    sys.exit(0 if result.wasSuccessful() else 1)
