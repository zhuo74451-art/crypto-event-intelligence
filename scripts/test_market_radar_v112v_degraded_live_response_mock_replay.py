#!/usr/bin/env python3
"""
test_market_radar_v112v_degraded_live_response_mock_replay.py
===============================================================
Test suite for v112V degraded live response → mock replay with explanation layer.

Validates:
  - v112V runner is executable
  - All 5 output files exist
  - Result JSON has correct safety invariants (status=passed, mock_replay_only=true, etc.)
  - No external API calls, no TG sends, no daemon, no state writes, no retries
  - eligible_for_real_send_count == 0
  - Degradation explanation contains CoinCap failure and optional fields missing
  - Mock replay records cover BTC / ETH / SOL
  - Each record has eligible_for_real_send=false
  - No secrets, tokens, keys, passwords in output files
  - No misleading claims about production readiness
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

V112V_RESULT = os.path.join(RESULTS_DIR, "market_radar_v112v_degraded_mock_replay_result.json")
V112V_RECORDS = os.path.join(RESULTS_DIR, "market_radar_v112v_degraded_mock_replay_records.jsonl")
V112V_EXPLANATION = os.path.join(RESULTS_DIR, "market_radar_v112v_degradation_explanation.json")
V112V_RUN_REPORT = os.path.join(RUNS_DIR, "v112v_degraded_live_response_mock_replay.md")
V112V_HANDOFF = os.path.join(RUNS_DIR, "v112v_degraded_live_response_mock_replay_handoff.md")


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_jsonl(path):
    records = []
    if not os.path.exists(path):
        return records
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


# ═══════════════════════════════════════════════════════════════════════════
# Test: Runner executable
# ═══════════════════════════════════════════════════════════════════════════

class TestV112VRunnerExecutable(unittest.TestCase):
    """Test that the v112V runner script exists and is executable."""

    def test_runner_file_exists(self):
        runner_path = os.path.join(PROJECT_DIR, "scripts",
                                   "run_market_radar_v112v_degraded_live_response_mock_replay.py")
        self.assertTrue(os.path.exists(runner_path), f"Runner not found: {runner_path}")

    def test_runner_importable_and_has_main(self):
        import importlib.util
        runner_path = os.path.join(PROJECT_DIR, "scripts",
                                   "run_market_radar_v112v_degraded_live_response_mock_replay.py")
        spec = importlib.util.spec_from_file_location("run_market_radar_v112v", runner_path)
        self.assertIsNotNone(spec, "Runner module spec should not be None")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        self.assertTrue(hasattr(mod, 'main'), "Runner should have main() function")

    def test_runner_main_executes_successfully(self):
        import importlib.util
        runner_path = os.path.join(PROJECT_DIR, "scripts",
                                   "run_market_radar_v112v_degraded_live_response_mock_replay.py")
        spec = importlib.util.spec_from_file_location("run_market_radar_v112v", runner_path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        exit_code = mod.main()
        self.assertEqual(exit_code, 0, f"Runner should exit with 0, got {exit_code}")


# ═══════════════════════════════════════════════════════════════════════════
# Test: All output files exist
# ═══════════════════════════════════════════════════════════════════════════

class TestV112VArtifactFilesExist(unittest.TestCase):
    """Test that all 5 required v112V output files exist."""

    def test_result_json_exists(self):
        self.assertTrue(os.path.exists(V112V_RESULT),
                       f"Missing: {V112V_RESULT}")

    def test_mock_replay_records_jsonl_exists(self):
        self.assertTrue(os.path.exists(V112V_RECORDS),
                       f"Missing: {V112V_RECORDS}")

    def test_degradation_explanation_json_exists(self):
        self.assertTrue(os.path.exists(V112V_EXPLANATION),
                       f"Missing: {V112V_EXPLANATION}")

    def test_run_report_md_exists(self):
        self.assertTrue(os.path.exists(V112V_RUN_REPORT),
                       f"Missing: {V112V_RUN_REPORT}")

    def test_handoff_md_exists(self):
        self.assertTrue(os.path.exists(V112V_HANDOFF),
                       f"Missing: {V112V_HANDOFF}")

    def test_runner_script_exists(self):
        runner_path = os.path.join(PROJECT_DIR, "scripts",
                                   "run_market_radar_v112v_degraded_live_response_mock_replay.py")
        self.assertTrue(os.path.exists(runner_path), f"Missing: {runner_path}")


# ═══════════════════════════════════════════════════════════════════════════
# Test: Result JSON invariants
# ═══════════════════════════════════════════════════════════════════════════

class TestV112VResultJSON(unittest.TestCase):
    """Test the v112V result JSON invariants."""

    @classmethod
    def setUpClass(cls):
        if not os.path.exists(V112V_RESULT):
            raise unittest.SkipTest(f"Result file not found: {V112V_RESULT}")
        cls.result = load_json(V112V_RESULT)

    def test_version(self):
        self.assertEqual(self.result.get("version"), "v1.12-v")

    def test_status_passed(self):
        self.assertEqual(self.result.get("status"), "passed",
                        "v112V status should be 'passed' (mock replay successful)")

    def test_dry_run_only_true(self):
        self.assertTrue(self.result.get("dry_run_only"),
                       "dry_run_only must be true")

    def test_mock_replay_only_true(self):
        self.assertTrue(self.result.get("mock_replay_only"),
                       "mock_replay_only must be true")

    def test_live_ready_false(self):
        self.assertFalse(self.result.get("live_ready"),
                        "live_ready must be false")

    def test_real_live_api_called_in_this_step_false(self):
        self.assertFalse(self.result.get("real_live_api_called_in_this_step"),
                        "real_live_api_called_in_this_step must be false")

    def test_real_tg_sent_false(self):
        self.assertFalse(self.result.get("real_tg_sent"),
                        "real_tg_sent must be false")

    def test_external_api_called_in_this_step_false(self):
        self.assertFalse(self.result.get("external_api_called_in_this_step"),
                        "external_api_called_in_this_step must be false")

    def test_external_ai_called_false(self):
        self.assertFalse(self.result.get("external_ai_called"),
                        "external_ai_called must be false")

    def test_daemon_started_false(self):
        self.assertFalse(self.result.get("daemon_started"),
                        "daemon_started must be false")

    def test_files_deleted_false(self):
        self.assertFalse(self.result.get("files_deleted"),
                        "files_deleted must be false")

    def test_debug_leak_count_zero(self):
        self.assertEqual(self.result.get("debug_leak_count"), 0,
                        "debug_leak_count must be 0")

    def test_secret_leak_count_zero(self):
        self.assertEqual(self.result.get("secret_leak_count"), 0,
                        "secret_leak_count must be 0")

    def test_upstream_stop_decision_degrade_to_mock(self):
        self.assertEqual(self.result.get("upstream_v112u_stop_decision"), "DEGRADE_TO_MOCK")

    def test_degradation_explanation_ready_true(self):
        self.assertTrue(self.result.get("degradation_explanation_ready"),
                       "degradation_explanation_ready must be true")

    def test_mock_replay_records_count_3(self):
        self.assertEqual(self.result.get("mock_replay_records_count"), 3,
                        "mock_replay_records_count must be 3 (BTC, ETH, SOL)")

    def test_eligible_for_real_send_count_0(self):
        self.assertEqual(self.result.get("eligible_for_real_send_count"), 0,
                        "eligible_for_real_send_count must be 0")

    def test_real_send_ready_false(self):
        self.assertFalse(self.result.get("real_send_ready"),
                        "real_send_ready must be false")

    def test_production_state_write_ready_false(self):
        self.assertFalse(self.result.get("production_state_write_ready"),
                        "production_state_write_ready must be false")

    def test_state_write_performed_false(self):
        self.assertFalse(self.result.get("state_write_performed"),
                        "state_write_performed must be false")

    def test_retry_attempted_false(self):
        self.assertFalse(self.result.get("retry_attempted"),
                        "retry_attempted must be false")

    def test_recommended_next_step_contains_v112w(self):
        next_step = self.result.get("recommended_next_step", "")
        self.assertIn("v112w", next_step.lower(),
                     "recommended_next_step should reference v112w")


# ═══════════════════════════════════════════════════════════════════════════
# Test: Mock replay records (JSONL)
# ═══════════════════════════════════════════════════════════════════════════

class TestV112VMockReplayRecords(unittest.TestCase):
    """Test the mock replay records JSONL file."""

    @classmethod
    def setUpClass(cls):
        if not os.path.exists(V112V_RECORDS):
            raise unittest.SkipTest(f"Records file not found: {V112V_RECORDS}")
        cls.records = load_jsonl(V112V_RECORDS)

    def test_at_least_3_records(self):
        self.assertGreaterEqual(len(self.records), 3,
                               "Should have at least 3 records (BTC, ETH, SOL)")

    def test_btc_record_exists(self):
        symbols = [r.get("asset_data", {}).get("symbol", "") for r in self.records]
        self.assertIn("BTC", symbols, "Should have a BTC record")

    def test_eth_record_exists(self):
        symbols = [r.get("asset_data", {}).get("symbol", "") for r in self.records]
        self.assertIn("ETH", symbols, "Should have an ETH record")

    def test_sol_record_exists(self):
        symbols = [r.get("asset_data", {}).get("symbol", "") for r in self.records]
        self.assertIn("SOL", symbols, "Should have a SOL record")

    def test_each_record_has_source_live_response(self):
        for r in self.records:
            self.assertIn("source_live_response", r,
                         f"Record {r.get('record_id')} missing source_live_response")

    def test_each_record_has_degradation_reasons(self):
        for r in self.records:
            self.assertIn("degradation_reasons", r,
                         f"Record {r.get('record_id')} missing degradation_reasons")
            self.assertIsInstance(r["degradation_reasons"], list)

    def test_each_record_mock_replay_only_true(self):
        for r in self.records:
            self.assertTrue(r.get("mock_replay_only"),
                           f"Record {r.get('record_id')}: mock_replay_only must be true")

    def test_each_record_eligible_for_real_send_false(self):
        for r in self.records:
            self.assertFalse(r.get("eligible_for_real_send"),
                            f"Record {r.get('record_id')}: eligible_for_real_send must be false")

    def test_each_record_real_live_api_called_in_this_step_false(self):
        for r in self.records:
            self.assertFalse(r.get("real_live_api_called_in_this_step"),
                            f"Record {r.get('record_id')}: real_live_api_called_in_this_step must be false")

    def test_each_record_state_write_performed_false(self):
        for r in self.records:
            self.assertFalse(r.get("state_write_performed"),
                            f"Record {r.get('record_id')}: state_write_performed must be false")

    def test_each_record_degraded_true(self):
        for r in self.records:
            self.assertTrue(r.get("degraded"),
                           f"Record {r.get('record_id')}: degraded must be true")

    def test_each_record_gate_status_degraded_mock_replay(self):
        for r in self.records:
            self.assertEqual(r.get("gate_status"), "degraded_mock_replay",
                            f"Record {r.get('record_id')}: gate_status must be 'degraded_mock_replay'")

    def test_each_record_has_asset_data_with_price(self):
        for r in self.records:
            ad = r.get("asset_data", {})
            self.assertIsNotNone(ad.get("price_usd"),
                                f"Record {r.get('record_id')}: missing price_usd")
            self.assertIsNotNone(ad.get("symbol"),
                                f"Record {r.get('record_id')}: missing symbol")

    def test_each_record_has_mock_envelope_hint(self):
        for r in self.records:
            hint = r.get("mock_envelope_hint", {})
            self.assertTrue(hint.get("mock_replay_only"),
                           f"Record {r.get('record_id')}: mock_envelope_hint.mock_replay_only must be true")
            self.assertFalse(hint.get("eligible_for_real_send"),
                            f"Record {r.get('record_id')}: mock_envelope_hint.eligible_for_real_send must be false")
            self.assertTrue(hint.get("not_for_real_send_candidate"),
                           f"Record {r.get('record_id')}: mock_envelope_hint.not_for_real_send_candidate must be true")

    def test_each_record_has_step_version(self):
        for r in self.records:
            self.assertEqual(r.get("step_version"), "v1.12-v",
                            f"Record {r.get('record_id')}: step_version must be v1.12-v")


# ═══════════════════════════════════════════════════════════════════════════
# Test: Degradation explanation JSON
# ═══════════════════════════════════════════════════════════════════════════

class TestV112VDegradationExplanation(unittest.TestCase):
    """Test the degradation explanation JSON content."""

    @classmethod
    def setUpClass(cls):
        if not os.path.exists(V112V_EXPLANATION):
            raise unittest.SkipTest(f"Explanation file not found: {V112V_EXPLANATION}")
        cls.explanation = load_json(V112V_EXPLANATION)

    def test_version(self):
        self.assertEqual(self.explanation.get("version"), "v1.12-v")

    def test_upstream_stop_decision(self):
        self.assertEqual(self.explanation.get("upstream_v112u_stop_decision"), "DEGRADE_TO_MOCK")

    def test_contains_coincap_failure_mention(self):
        """Degradation explanation must mention CoinCap failure."""
        text = json.dumps(self.explanation).lower()
        self.assertTrue(
            "coincap" in text,
            "Degradation explanation must mention CoinCap"
        )

    def test_contains_optional_fields_missing(self):
        """Degradation explanation must mention optional fields missing."""
        text = json.dumps(self.explanation).lower()
        self.assertTrue(
            "optional" in text or "oi" in text or "volume" in text,
            "Degradation explanation must discuss optional field gaps (OI/volume)"
        )

    def test_contains_degradation_events(self):
        events = self.explanation.get("degradation_events", [])
        self.assertGreater(len(events), 0, "Must have degradation events")

    def test_has_summary(self):
        summary = self.explanation.get("summary", {})
        self.assertEqual(summary.get("primary_source"), "coingecko_public_rest")
        self.assertEqual(summary.get("fallback_source"), "coincap_public_rest")
        self.assertTrue(summary.get("degradation_is_not_failure"))

    def test_has_sources_requested(self):
        sources = self.explanation.get("sources_requested", {})
        self.assertIn("coingecko_public_rest", sources)
        self.assertIn("coincap_public_rest", sources)
        self.assertIn("success", sources["coingecko_public_rest"]["status"].lower())
        self.assertIn("fail", sources["coincap_public_rest"]["status"].lower())

    def test_has_why_sections(self):
        self.assertIn("why_degraded_not_aborted", self.explanation)
        self.assertIn("why_degraded_not_continued", self.explanation)
        self.assertIn("why_not_eligible_for_real_send", self.explanation)
        self.assertGreater(len(self.explanation["why_degraded_not_aborted"]), 50)
        self.assertGreater(len(self.explanation["why_degraded_not_continued"]), 50)

    def test_has_oi_volume_field_assessment(self):
        assessment = self.explanation.get("oi_volume_field_assessment", {})
        self.assertIn("oi_change_pct", assessment)
        self.assertIn("volume_change_pct", assessment)
        self.assertFalse(assessment["oi_change_pct"].get("available_from_free_sources"))

    def test_has_safety_affirmation(self):
        safety = self.explanation.get("safety_affirmation", {})
        self.assertTrue(safety.get("no_new_api_calls_made"))
        self.assertTrue(safety.get("no_coinbase_retry_attempted"))
        self.assertTrue(safety.get("no_real_tg_sent"))

    def test_has_asset_field_status(self):
        field_status = self.explanation.get("asset_field_status", [])
        self.assertEqual(len(field_status), 3, "Should cover all 3 assets")
        for fs in field_status:
            self.assertTrue(fs.get("price_available"))
            self.assertFalse(fs.get("oi_available"))

    def test_degradation_events_include_coingecko_success(self):
        events = self.explanation.get("degradation_events", [])
        cg_events = [e for e in events if "coingecko" in e.get("event", "").lower()]
        self.assertGreater(len(cg_events), 0, "Must have CoinGecko event")

    def test_degradation_events_include_coincap_failure(self):
        events = self.explanation.get("degradation_events", [])
        cc_events = [e for e in events if "coincap" in e.get("event", "").lower()]
        self.assertGreater(len(cc_events), 0, "Must have CoinCap failure event")

    def test_degradation_events_include_no_retry(self):
        events = self.explanation.get("degradation_events", [])
        retry_events = [e for e in events if "retry" in e.get("event", "").lower()]
        self.assertGreater(len(retry_events), 0, "Must document that no retry was attempted")


# ═══════════════════════════════════════════════════════════════════════════
# Test: No secret leaks in output files
# ═══════════════════════════════════════════════════════════════════════════

class TestV112VNoSecretLeaks(unittest.TestCase):
    """Test that no secrets, tokens, keys, or credentials appear in output files."""

    SECRET_PATTERNS = [
        "api_key", "apikey", "api-key",
        "token", "TOKEN",
        "secret", "SECRET",
        "password", "PASSWORD",
        "cookie", "COOKIE",
        "bearer", "BEARER",
        "authorization", "AUTHORIZATION",
        "credential value",
        "x-api-key:", "sk-", "-----BEGIN",
    ]

    SAFE_CONTEXTS = [
        "secret_leak_count",
        "secret leak count",
        "debug_leak_count",
        "debug leak count",
        "no api key",
        "no_api_key",
        "requires api key",
        "requires paid api key",
        "no secret",
        "api_key_used",
        "api_key_required",
        "authorization_header_used",
        "token/key/cookie/password",
        "any token",
        "no api keys",
        "not used",
        "no authorization",
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
        issues = self._check_file_for_secrets(V112V_RESULT, "result.json")
        self.assertEqual(len(issues), 0, f"Secrets in result.json: {issues}")

    def test_records_jsonl_no_secrets(self):
        issues = self._check_file_for_secrets(V112V_RECORDS, "records.jsonl")
        self.assertEqual(len(issues), 0, f"Secrets in records.jsonl: {issues}")

    def test_explanation_json_no_secrets(self):
        issues = self._check_file_for_secrets(V112V_EXPLANATION, "explanation.json")
        self.assertEqual(len(issues), 0, f"Secrets in explanation.json: {issues}")

    def test_run_report_no_secrets(self):
        issues = self._check_file_for_secrets(V112V_RUN_REPORT, "run_report.md")
        self.assertEqual(len(issues), 0, f"Secrets in run_report.md: {issues}")

    def test_handoff_no_secrets(self):
        issues = self._check_file_for_secrets(V112V_HANDOFF, "handoff.md")
        self.assertEqual(len(issues), 0, f"Secrets in handoff.md: {issues}")


# ═══════════════════════════════════════════════════════════════════════════
# Test: No misleading claims about production readiness
# ═══════════════════════════════════════════════════════════════════════════

class TestV112VNoMisleadingClaims(unittest.TestCase):
    """Test that output files don't contain misleading claims about production state."""

    MISLEADING_PHRASES = [
        "production ready",
        "已接入正式生产",
        "已真实发送",
        "real send enabled",
        "production state active",
        "live fetch ready",
        "ready for production",
        "eligible for real send: true",
        "eligible_for_real_send: true",
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
        content_lower = content.lower()
        for phrase in self.MISLEADING_PHRASES:
            if phrase.lower() in content_lower:
                idx = content_lower.find(phrase.lower())
                context = content[max(0, idx - 30):idx + len(phrase) + 30]
                found.append(f"{label}: found '{phrase}' near: ...{context}...")
        return found

    def test_result_no_misleading(self):
        issues = self._check_file_for_misleading(V112V_RESULT, "result.json")
        self.assertEqual(len(issues), 0, f"Misleading claims in result.json: {issues}")

    def test_records_no_misleading(self):
        issues = self._check_file_for_misleading(V112V_RECORDS, "records.jsonl")
        self.assertEqual(len(issues), 0, f"Misleading claims in records.jsonl: {issues}")

    def test_explanation_no_misleading(self):
        issues = self._check_file_for_misleading(V112V_EXPLANATION, "explanation.json")
        self.assertEqual(len(issues), 0, f"Misleading claims in explanation.json: {issues}")

    def test_run_report_no_misleading(self):
        issues = self._check_file_for_misleading(V112V_RUN_REPORT, "run_report.md")
        self.assertEqual(len(issues), 0, f"Misleading claims in run_report.md: {issues}")

    def test_handoff_no_misleading(self):
        issues = self._check_file_for_misleading(V112V_HANDOFF, "handoff.md")
        self.assertEqual(len(issues), 0, f"Misleading claims in handoff: {issues}")


# ═══════════════════════════════════════════════════════════════════════════
# Test: Run report content
# ═══════════════════════════════════════════════════════════════════════════

class TestV112VRunReportContent(unittest.TestCase):
    """Test the run report markdown content."""

    @classmethod
    def setUpClass(cls):
        if not os.path.exists(V112V_RUN_REPORT):
            raise unittest.SkipTest(f"Run report not found: {V112V_RUN_REPORT}")
        with open(V112V_RUN_REPORT, "r", encoding="utf-8") as f:
            cls.content = f.read()

    def test_mentions_v112v_objective(self):
        self.assertIn("v112V Objective", self.content,
                     "Run report should have v112V Objective section")

    def test_mentions_what_v112u_returned(self):
        self.assertIn("What v112U Returned", self.content,
                     "Run report should have 'What v112U Returned' section")

    def test_mentions_degrade_to_mock(self):
        self.assertIn("DEGRADE_TO_MOCK", self.content,
                     "Run report should mention DEGRADE_TO_MOCK")

    def test_mentions_why_degraded_not_failure(self):
        content_lower = self.content.lower()
        self.assertIn("degrade", content_lower,
                     "Run report should discuss degradation")

    def test_mentions_coincap_failure_handling(self):
        self.assertIn("CoinCap", self.content,
                     "Run report should mention how CoinCap failure was handled")

    def test_mentions_oi_volume_handling(self):
        content_lower = self.content.lower()
        self.assertTrue(
            "oi" in content_lower or "volume" in content_lower,
            "Run report should discuss OI/volume field handling"
        )

    def test_mentions_btc_eth_sol(self):
        content_upper = self.content.upper()
        for symbol in ["BTC", "ETH", "SOL"]:
            self.assertIn(symbol, content_upper,
                         f"Run report should mention {symbol}")

    def test_mentions_not_eligible_for_real_send(self):
        content_lower = self.content.lower()
        self.assertTrue(
            "not eligible" in content_lower or "eligible" in content_lower,
            "Run report should discuss eligibility"
        )

    def test_mentions_next_step(self):
        content_lower = self.content.lower()
        self.assertIn("v112w", content_lower,
                     "Run report should mention v112W next step")

    def test_mentions_safety_checklist(self):
        self.assertIn("Safety Checklist", self.content,
                     "Run report should have Safety Checklist section")


# ═══════════════════════════════════════════════════════════════════════════
# Test: Handoff content
# ═══════════════════════════════════════════════════════════════════════════

class TestV112VHandoffContent(unittest.TestCase):
    """Test the handoff markdown content."""

    @classmethod
    def setUpClass(cls):
        if not os.path.exists(V112V_HANDOFF):
            raise unittest.SkipTest(f"Handoff not found: {V112V_HANDOFF}")
        with open(V112V_HANDOFF, "r", encoding="utf-8") as f:
            cls.content = f.read()

    def test_mentions_what_was_done(self):
        self.assertIn("What v112V Did", self.content,
                     "Handoff should have 'What v112V Did' section")

    def test_mentions_files_read(self):
        self.assertIn("Files Read", self.content,
                     "Handoff should have 'Files Read' section")

    def test_mentions_files_generated(self):
        self.assertIn("Files Generated", self.content,
                     "Handoff should have 'Files Generated' section")

    def test_mentions_safety_posture(self):
        content_lower = self.content.lower()
        self.assertTrue(
            "safety posture" in content_lower or "still not enabled" in content_lower,
            "Handoff should discuss safety posture"
        )

    def test_mentions_degradation_rules(self):
        self.assertIn("Degradation Rules", self.content,
                     "Handoff should list degradation rules triggered")

    def test_mentions_next_step(self):
        content_lower = self.content.lower()
        self.assertIn("v112w", content_lower,
                     "Handoff should mention v112W next step")

    def test_mentions_no_live_api_retry(self):
        content_lower = self.content.lower()
        self.assertTrue(
            "disabled" in content_lower or "not attempted" in content_lower,
            "Handoff should indicate live API retry is not attempted"
        )

    def test_no_internal_token_leaks(self):
        leak_indicators = [
            "x-api-key:", "Bearer eyJ", "sk-", "-----BEGIN",
        ]
        for indicator in leak_indicators:
            self.assertNotIn(indicator, self.content,
                            f"Potential credential leak in handoff: {indicator}")


# ═══════════════════════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("=" * 70)
    print("v112V Degraded Live Response → Mock Replay Test Suite")
    print("=" * 70)
    print()

    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    suite.addTests(loader.loadTestsFromTestCase(TestV112VRunnerExecutable))
    suite.addTests(loader.loadTestsFromTestCase(TestV112VArtifactFilesExist))
    suite.addTests(loader.loadTestsFromTestCase(TestV112VResultJSON))
    suite.addTests(loader.loadTestsFromTestCase(TestV112VMockReplayRecords))
    suite.addTests(loader.loadTestsFromTestCase(TestV112VDegradationExplanation))
    suite.addTests(loader.loadTestsFromTestCase(TestV112VNoSecretLeaks))
    suite.addTests(loader.loadTestsFromTestCase(TestV112VNoMisleadingClaims))
    suite.addTests(loader.loadTestsFromTestCase(TestV112VRunReportContent))
    suite.addTests(loader.loadTestsFromTestCase(TestV112VHandoffContent))

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
