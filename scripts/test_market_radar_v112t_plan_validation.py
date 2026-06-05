#!/usr/bin/env python3
"""
test_market_radar_v112t_plan_validation.py
===========================================
Validation test suite for v112T one-shot free source plan.

Tests that the v112T runner executes successfully and produces
all required artifacts with correct safety invariants.

No live API requests. No TG send. No daemon.
"""

import json
import os
import sys
import unittest

# ── Project root ──────────────────────────────────────────────────────────
PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(PROJECT_DIR)

RESULTS_DIR = os.path.join(PROJECT_DIR, "results")
CONFIG_DIR = os.path.join(PROJECT_DIR, "config")
SCHEMAS_DIR = os.path.join(PROJECT_DIR, "schemas")
DOCS_DIR = os.path.join(PROJECT_DIR, "docs")
RUNS_DIR = os.path.join(PROJECT_DIR, "runs", "market_radar")

V112T_RESULT = os.path.join(RESULTS_DIR, "market_radar_v112t_one_shot_free_source_plan_result.json")
V112T_RUN_REPORT = os.path.join(RUNS_DIR, "v112t_one_shot_free_source_plan.md")
V112T_HANDOFF = os.path.join(RUNS_DIR, "v112t_one_shot_free_source_plan_handoff.md")
V112T_FREE_SOURCE_MAPPING = os.path.join(CONFIG_DIR, "market_radar_v112t_free_source_mapping.json")
V112T_STOP_CONDITIONS = os.path.join(CONFIG_DIR, "market_radar_v112t_stop_conditions.json")
V112T_LIVE_SOURCE_SCHEMA = os.path.join(SCHEMAS_DIR, "market_radar_v112t_live_source_response_schema.json")
V112T_ADAPTER_SPEC = os.path.join(SCHEMAS_DIR, "market_radar_v112t_live_to_mock_adapter_spec.md")
V112T_DOCS_PLAN = os.path.join(DOCS_DIR, "market_radar_v112t_free_source_plan.md")


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


class TestV112TRunnerExecutable(unittest.TestCase):
    """Test that the v112T runner script executes successfully."""

    def test_runner_imports(self):
        """Runner module should be importable."""
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "run_market_radar_v112t",
            os.path.join(PROJECT_DIR, "scripts", "run_market_radar_v112t_one_shot_free_source_plan.py")
        )
        self.assertIsNotNone(spec, "Runner module spec should not be None")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        self.assertTrue(hasattr(mod, 'main'), "Runner should have main() function")

    def test_runner_main_returns_zero(self):
        """Runner main() should return exit code 0."""
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "run_market_radar_v112t",
            os.path.join(PROJECT_DIR, "scripts", "run_market_radar_v112t_one_shot_free_source_plan.py")
        )
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        exit_code = mod.main()
        self.assertEqual(exit_code, 0, f"Runner should return 0, got {exit_code}")


class TestV112TResultJSON(unittest.TestCase):
    """Test the result JSON file."""

    @classmethod
    def setUpClass(cls):
        if not os.path.exists(V112T_RESULT):
            raise unittest.SkipTest(f"Result file not found: {V112T_RESULT}")
        cls.result = load_json(V112T_RESULT)

    def test_result_exists(self):
        """Result JSON file should exist."""
        self.assertTrue(os.path.exists(V112T_RESULT), f"Result file missing: {V112T_RESULT}")

    def test_status_passed(self):
        """status should be 'passed'."""
        self.assertEqual(self.result.get("status"), "passed",
                         f"Expected status='passed', got '{self.result.get('status')}'")

    def test_version(self):
        """version should be 'v1.12-t'."""
        self.assertEqual(self.result.get("version"), "v1.12-t")

    def test_dry_run_only_true(self):
        """dry_run_only should be True."""
        self.assertTrue(self.result.get("dry_run_only"), "dry_run_only should be True")

    def test_plan_only_true(self):
        """plan_only should be True."""
        self.assertTrue(self.result.get("plan_only"), "plan_only should be True")

    def test_live_ready_false(self):
        """live_ready should be False."""
        self.assertFalse(self.result.get("live_ready"), "live_ready should be False")

    def test_real_live_api_called_false(self):
        """real_live_api_called should be False."""
        self.assertFalse(self.result.get("real_live_api_called"),
                         "real_live_api_called should be False")

    def test_real_tg_sent_false(self):
        """real_tg_sent should be False."""
        self.assertFalse(self.result.get("real_tg_sent"), "real_tg_sent should be False")

    def test_external_api_called_false(self):
        """external_api_called should be False."""
        self.assertFalse(self.result.get("external_api_called"),
                         "external_api_called should be False")

    def test_external_ai_called_false(self):
        """external_ai_called should be False."""
        self.assertFalse(self.result.get("external_ai_called"),
                         "external_ai_called should be False")

    def test_daemon_started_false(self):
        """daemon_started should be False."""
        self.assertFalse(self.result.get("daemon_started"), "daemon_started should be False")

    def test_files_deleted_false(self):
        """files_deleted should be False."""
        self.assertFalse(self.result.get("files_deleted"), "files_deleted should be False")

    def test_candidate_card_type(self):
        """candidate_card_type should be 'multi_asset_market_sync'."""
        self.assertEqual(self.result.get("candidate_card_type"), "multi_asset_market_sync")

    def test_free_source_plan_ready_true(self):
        """free_source_plan_ready should be True."""
        self.assertTrue(self.result.get("free_source_plan_ready"),
                        "free_source_plan_ready should be True")

    def test_stop_conditions_ready_true(self):
        """stop_conditions_ready should be True."""
        self.assertTrue(self.result.get("stop_conditions_ready"),
                        "stop_conditions_ready should be True")

    def test_field_mapping_ready_true(self):
        """field_mapping_ready should be True."""
        self.assertTrue(self.result.get("field_mapping_ready"),
                        "field_mapping_ready should be True")

    def test_live_source_response_schema_ready_true(self):
        """live_source_response_schema_ready should be True."""
        self.assertTrue(self.result.get("live_source_response_schema_ready"),
                        "live_source_response_schema_ready should be True")

    def test_live_to_mock_adapter_spec_ready_true(self):
        """live_to_mock_adapter_spec_ready should be True."""
        self.assertTrue(self.result.get("live_to_mock_adapter_spec_ready"),
                        "live_to_mock_adapter_spec_ready should be True")

    def test_decision_modes_contain_all_three(self):
        """decision_modes should contain CONTINUE, ABORT, DEGRADE_TO_MOCK."""
        modes = self.result.get("decision_modes", [])
        self.assertIn("CONTINUE", modes)
        self.assertIn("ABORT", modes)
        self.assertIn("DEGRADE_TO_MOCK", modes)

    def test_real_send_ready_false(self):
        """real_send_ready should be False."""
        self.assertFalse(self.result.get("real_send_ready"), "real_send_ready should be False")

    def test_production_state_write_ready_false(self):
        """production_state_write_ready should be False."""
        self.assertFalse(self.result.get("production_state_write_ready"),
                         "production_state_write_ready should be False")

    def test_v112u_requires_user_confirmation_true(self):
        """v112u_requires_user_confirmation should be True."""
        self.assertTrue(self.result.get("v112u_requires_user_confirmation"),
                        "v112u_requires_user_confirmation should be True")

    def test_recommended_next_step(self):
        """recommended_next_step should mention v112u and user confirmation."""
        next_step = self.result.get("recommended_next_step", "")
        self.assertIn("v112u", next_step.lower())
        self.assertIn("confirmation", next_step.lower())

    def test_debug_leak_count_zero(self):
        """debug_leak_count should be 0."""
        self.assertEqual(self.result.get("debug_leak_count"), 0)

    def test_secret_leak_count_zero(self):
        """secret_leak_count should be 0."""
        self.assertEqual(self.result.get("secret_leak_count"), 0)


class TestV112TArtifactFiles(unittest.TestCase):
    """Test that all required artifact files exist."""

    def test_free_source_mapping_json_exists(self):
        self.assertTrue(os.path.exists(V112T_FREE_SOURCE_MAPPING),
                        f"Missing: {V112T_FREE_SOURCE_MAPPING}")

    def test_stop_conditions_json_exists(self):
        self.assertTrue(os.path.exists(V112T_STOP_CONDITIONS),
                        f"Missing: {V112T_STOP_CONDITIONS}")

    def test_live_source_response_schema_exists(self):
        self.assertTrue(os.path.exists(V112T_LIVE_SOURCE_SCHEMA),
                        f"Missing: {V112T_LIVE_SOURCE_SCHEMA}")

    def test_adapter_spec_md_exists(self):
        self.assertTrue(os.path.exists(V112T_ADAPTER_SPEC),
                        f"Missing: {V112T_ADAPTER_SPEC}")

    def test_docs_plan_md_exists(self):
        self.assertTrue(os.path.exists(V112T_DOCS_PLAN),
                        f"Missing: {V112T_DOCS_PLAN}")

    def test_run_report_md_exists(self):
        self.assertTrue(os.path.exists(V112T_RUN_REPORT),
                        f"Missing: {V112T_RUN_REPORT}")

    def test_handoff_md_exists(self):
        self.assertTrue(os.path.exists(V112T_HANDOFF),
                        f"Missing: {V112T_HANDOFF}")


class TestV112TStopConditions(unittest.TestCase):
    """Test stop conditions JSON content."""

    @classmethod
    def setUpClass(cls):
        if not os.path.exists(V112T_STOP_CONDITIONS):
            raise unittest.SkipTest(f"Stop conditions file not found: {V112T_STOP_CONDITIONS}")
        cls.sc = load_json(V112T_STOP_CONDITIONS)

    def test_decision_order_correct(self):
        """Decision order should be ABORT, DEGRADE_TO_MOCK, CONTINUE."""
        order = self.sc.get("decision_order", [])
        self.assertEqual(order, ["ABORT", "DEGRADE_TO_MOCK", "CONTINUE"])

    def test_abort_has_http_429(self):
        """ABORT should include HTTP 429 condition."""
        abort_rules = self.sc.get("stop_conditions", {}).get("ABORT", {}).get("rules", [])
        has_429 = any("429" in r.get("condition", "") or "429" in r.get("id", "")
                      for r in abort_rules)
        self.assertTrue(has_429, "ABORT missing HTTP 429 condition")

    def test_abort_has_timeout(self):
        """ABORT should include request timeout condition."""
        abort_rules = self.sc.get("stop_conditions", {}).get("ABORT", {}).get("rules", [])
        has_timeout = any("timeout" in r.get("condition", "").lower() or
                          "TIMEOUT" in r.get("id", "")
                          for r in abort_rules)
        self.assertTrue(has_timeout, "ABORT missing timeout condition")

    def test_abort_has_schema_mismatch(self):
        """ABORT should include schema mismatch condition."""
        abort_rules = self.sc.get("stop_conditions", {}).get("ABORT", {}).get("rules", [])
        has_schema = any("schema" in r.get("condition", "").lower() or
                         "SCHEMA" in r.get("id", "")
                         for r in abort_rules)
        self.assertTrue(has_schema, "ABORT missing schema mismatch condition")

    def test_abort_has_timestamp_skew(self):
        """ABORT should include timestamp skew condition."""
        abort_rules = self.sc.get("stop_conditions", {}).get("ABORT", {}).get("rules", [])
        has_ts = any("timestamp" in r.get("condition", "").lower() or
                     "TIMESTAMP" in r.get("id", "")
                     for r in abort_rules)
        self.assertTrue(has_ts, "ABORT missing timestamp skew condition")

    def test_abort_has_price_divergence(self):
        """ABORT should include price divergence condition."""
        abort_rules = self.sc.get("stop_conditions", {}).get("ABORT", {}).get("rules", [])
        has_price = any("price" in r.get("condition", "").lower() or
                        "PRICE" in r.get("id", "")
                        for r in abort_rules)
        self.assertTrue(has_price, "ABORT missing price divergence condition")

    def test_degrade_has_optional_fields(self):
        """DEGRADE should include optional fields missing condition."""
        degrade_rules = self.sc.get("stop_conditions", {}).get("DEGRADE_TO_MOCK", {}).get("rules", [])
        has_optional = any("optional" in r.get("condition", "").lower() or
                           "OPTIONAL" in r.get("id", "")
                           for r in degrade_rules)
        self.assertTrue(has_optional, "DEGRADE missing optional fields condition")

    def test_degrade_has_threshold_boundary(self):
        """DEGRADE should include threshold boundary condition."""
        degrade_rules = self.sc.get("stop_conditions", {}).get("DEGRADE_TO_MOCK", {}).get("rules", [])
        has_boundary = any("threshold" in r.get("condition", "").lower() or
                           "boundary" in r.get("condition", "").lower() or
                           "BOUNDARY" in r.get("id", "")
                           for r in degrade_rules)
        self.assertTrue(has_boundary, "DEGRADE missing threshold boundary condition")

    def test_degrade_has_partial_asset_failure(self):
        """DEGRADE should include partial asset failure condition."""
        degrade_rules = self.sc.get("stop_conditions", {}).get("DEGRADE_TO_MOCK", {}).get("rules", [])
        has_partial = any("partial" in r.get("condition", "").lower() or
                          "PARTIAL" in r.get("id", "")
                          for r in degrade_rules)
        self.assertTrue(has_partial, "DEGRADE missing partial asset failure condition")

    def test_continue_has_eligible_false(self):
        """CONTINUE should still require eligible_for_real_send=false."""
        continue_rules = self.sc.get("stop_conditions", {}).get("CONTINUE", {}).get("rules", [])
        has_eligible_false = any(
            "eligible_for_real_send" in r.get("condition", "").lower() or
            "ELIGIBLE_FALSE" in r.get("id", "") or
            "eligible" in r.get("note", "").lower()
            for r in continue_rules
        )
        self.assertTrue(has_eligible_false,
                        "CONTINUE missing eligible_for_real_send=false constraint")


class TestV112TSchema(unittest.TestCase):
    """Test LiveSourceResponse schema content."""

    @classmethod
    def setUpClass(cls):
        if not os.path.exists(V112T_LIVE_SOURCE_SCHEMA):
            raise unittest.SkipTest(f"Schema file not found: {V112T_LIVE_SOURCE_SCHEMA}")
        cls.schema = load_json(V112T_LIVE_SOURCE_SCHEMA)

    def test_eligible_for_real_send_is_const_false(self):
        """eligible_for_real_send must be const: false."""
        eligible = (
            self.schema.get("properties", {})
            .get("eligible_for_real_send", {})
        )
        self.assertFalse(eligible.get("const"),
                         "eligible_for_real_send.const must be false")

    def test_request_mode_has_planned_one_shot(self):
        """request_mode enum must include planned_one_shot."""
        request_mode = (
            self.schema.get("properties", {})
            .get("request_mode", {})
            .get("enum", [])
        )
        self.assertIn("planned_one_shot", request_mode)

    def test_stop_decision_has_all_three_modes(self):
        """stop_decision enum must have CONTINUE, ABORT, DEGRADE_TO_MOCK."""
        stop_decision = (
            self.schema.get("properties", {})
            .get("stop_decision", {})
            .get("enum", [])
        )
        for mode in ["CONTINUE", "ABORT", "DEGRADE_TO_MOCK"]:
            self.assertIn(mode, stop_decision,
                          f"stop_decision enum missing {mode}")

    def test_asset_has_required_fields(self):
        """Asset must have asset_id, symbol, price_usd, price_change_pct, last_updated_at."""
        asset_required = (
            self.schema.get("properties", {})
            .get("assets", {})
            .get("items", {})
            .get("required", [])
        )
        for field in ["asset_id", "symbol", "price_usd", "price_change_pct", "last_updated_at"]:
            self.assertIn(field, asset_required, f"Asset missing required field: {field}")

    def test_open_interest_change_pct_nullable(self):
        """open_interest_change_pct should be nullable."""
        oi = (
            self.schema.get("properties", {})
            .get("assets", {})
            .get("items", {})
            .get("properties", {})
            .get("open_interest_change_pct", {})
        )
        self.assertTrue(oi.get("nullable"), "open_interest_change_pct should be nullable")


class TestV112TNoSecretLeaks(unittest.TestCase):
    """Test that no secrets, tokens, or credentials appear in output files."""

    SECRET_PATTERNS = [
        "api_key", "apikey", "api-key", "API_KEY",
        "token", "TOKEN", "Token",
        "secret", "SECRET", "Secret",
        "password", "PASSWORD", "Password",
        "cookie", "COOKIE", "Cookie",
        "bearer", "BEARER", "Bearer",
        "authorization", "AUTHORIZATION",
        "credential value", "api secret",
    ]

    # Known-safe metadata field names and descriptions that contain
    # words like "secret" or "api-key" but are reporting safety status,
    # not exposing actual secrets.
    SAFE_CONTEXTS = [
        "secret_leak_count",       # metadata field reporting zero leaks
        "debug_leak_count",        # metadata field reporting zero leaks
        "no api key",              # statement that no API key is used
        "any source requiring api key",  # forbidden sources list
        "any api-key source",      # forbidden sources list (with hyphen)
        "requires api key",        # stating a source's requirement
        "requires paid api key",   # stating a source's requirement
        "no secrets",              # header/section title
        "api key or credential",   # safety disclaimer
        "out of scope for free",   # forbidden sources context
    ]

    def _check_file_for_secrets(self, path, label):
        """Check a text file for secret patterns."""
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
                # Check if this match is in a safe context
                idx = content_lower.find(pattern.lower())
                context = content[max(0, idx - 30):idx + len(pattern) + 30]
                context_lower = context.lower()

                # Skip if any safe context phrase appears nearby
                is_safe = any(safe in context_lower for safe in self.SAFE_CONTEXTS)
                if not is_safe:
                    found.append(f"{label}: found '{pattern}' near: ...{context}...")
        return found

    def test_result_json_no_secrets(self):
        issues = self._check_file_for_secrets(V112T_RESULT, "result.json")
        self.assertEqual(len(issues), 0, f"Secrets found in result.json: {issues}")

    def test_run_report_no_secrets(self):
        issues = self._check_file_for_secrets(V112T_RUN_REPORT, "run_report.md")
        self.assertEqual(len(issues), 0, f"Secrets found in run report: {issues}")

    def test_handoff_no_secrets(self):
        issues = self._check_file_for_secrets(V112T_HANDOFF, "handoff.md")
        self.assertEqual(len(issues), 0, f"Secrets found in handoff: {issues}")

    def test_docs_no_secrets(self):
        issues = self._check_file_for_secrets(V112T_DOCS_PLAN, "docs_plan.md")
        self.assertEqual(len(issues), 0, f"Secrets found in docs: {issues}")

    def test_adapter_spec_no_secrets(self):
        issues = self._check_file_for_secrets(V112T_ADAPTER_SPEC, "adapter_spec.md")
        self.assertEqual(len(issues), 0, f"Secrets found in adapter spec: {issues}")


class TestV112TNoMisleadingClaims(unittest.TestCase):
    """Test that output files don't contain misleading claims about live/production state."""

    MISLEADING_PHRASES = [
        "已接入 live API",
        "已真实发送",
        "production ready",
        "live API connected",
        "real send enabled",
        "production state active",
        "live fetch ready",
        "real-time data streaming",
    ]

    def _check_file_for_misleading(self, path, label):
        """Check a text file for misleading phrases."""
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
        issues = self._check_file_for_misleading(V112T_RESULT, "result.json")
        self.assertEqual(len(issues), 0, f"Misleading claims in result.json: {issues}")

    def test_handoff_no_misleading(self):
        issues = self._check_file_for_misleading(V112T_HANDOFF, "handoff.md")
        self.assertEqual(len(issues), 0, f"Misleading claims in handoff: {issues}")

    def test_docs_no_misleading(self):
        issues = self._check_file_for_misleading(V112T_DOCS_PLAN, "docs_plan.md")
        self.assertEqual(len(issues), 0, f"Misleading claims in docs: {issues}")


class TestV112TDocsContent(unittest.TestCase):
    """Test the documentation content."""

    @classmethod
    def setUpClass(cls):
        if not os.path.exists(V112T_DOCS_PLAN):
            raise unittest.SkipTest(f"Docs file not found: {V112T_DOCS_PLAN}")
        with open(V112T_DOCS_PLAN, "r", encoding="utf-8") as f:
            cls.docs_content = f.read()

    def test_mentions_v112u_requires_confirmation(self):
        """Docs should explicitly state v112U requires user confirmation."""
        self.assertIn("confirmation", self.docs_content.lower(),
                      "Docs should mention user confirmation for v112U")

    def test_mentions_free_sources(self):
        """Docs should mention CoinGecko and CoinCap as free sources."""
        self.assertIn("CoinGecko", self.docs_content)
        self.assertIn("CoinCap", self.docs_content)

    def test_mentions_stop_conditions(self):
        """Docs should mention three-state stop conditions."""
        self.assertIn("ABORT", self.docs_content)
        self.assertIn("DEGRADE", self.docs_content)
        self.assertIn("CONTINUE", self.docs_content)

    def test_mentions_plan_only(self):
        """Docs should mention plan-only nature."""
        self.assertIn("plan-only", self.docs_content.lower())

    def test_mentions_no_live_fetch(self):
        """Docs should mention no live fetch is performed."""
        self.assertIn("no live", self.docs_content.lower())

    def test_mentions_eligible_for_real_send_false(self):
        """Docs should mention eligible_for_real_send=false."""
        self.assertIn("eligible_for_real_send", self.docs_content.lower())


if __name__ == "__main__":
    # Print header
    print("=" * 70)
    print("v112T Plan Validation Test Suite")
    print("=" * 70)
    print()

    # Run tests
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # Add test classes in order
    suite.addTests(loader.loadTestsFromTestCase(TestV112TRunnerExecutable))
    suite.addTests(loader.loadTestsFromTestCase(TestV112TResultJSON))
    suite.addTests(loader.loadTestsFromTestCase(TestV112TArtifactFiles))
    suite.addTests(loader.loadTestsFromTestCase(TestV112TStopConditions))
    suite.addTests(loader.loadTestsFromTestCase(TestV112TSchema))
    suite.addTests(loader.loadTestsFromTestCase(TestV112TNoSecretLeaks))
    suite.addTests(loader.loadTestsFromTestCase(TestV112TNoMisleadingClaims))
    suite.addTests(loader.loadTestsFromTestCase(TestV112TDocsContent))

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # Summary
    print("\n" + "=" * 70)
    print(f"Tests run: {result.testsRun}")
    print(f"Passed: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print("=" * 70)

    sys.exit(0 if result.wasSuccessful() else 1)
