#!/usr/bin/env python3
"""
test_market_radar_v112y_whale_degraded_mock_replay.py
=======================================================
Test suite for v112Y whale degraded mock replay with label explanation.

Validates:
  - v112Y runner is executable (exit code 0)
  - All 4 output files exist (result JSON, replay JSONL, run report, handoff)
  - Result JSON has correct safety invariants
  - external_api_called=false, tg_sent=false, prod_state_write=false
  - eligible_for_real_send_count == 0
  - All replay records have eligible_for_real_send=false
  - All replay records have label_confidence
  - All low label confidence records have explanation
  - All null liquidation_price records have note
  - All records have delta_unavailable explanation
  - All records have local timestamp explanation
  - No real_send_candidate=true anywhere
  - No degraded replay masquerading as live passed
  - No external API calls, no TG sent, no prod state write
  - No daemon, no watcher, no credentials read
  - No files deleted
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

V112Y_RESULT = os.path.join(RESULTS_DIR, "market_radar_v112y_whale_degraded_mock_replay_result.json")
V112Y_RECORDS = os.path.join(RESULTS_DIR, "market_radar_v112y_whale_degraded_replay_records.jsonl")
V112Y_RUN_REPORT = os.path.join(RUNS_DIR, "v112y_whale_degraded_mock_replay.md")
V112Y_HANDOFF = os.path.join(RUNS_DIR, "v112y_whale_degraded_mock_replay_handoff.md")


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

class TestRunnerExecutable(unittest.TestCase):
    """Test that the v112Y runner script exists, imports, and exits with 0."""

    def test_runner_file_exists(self):
        runner_path = os.path.join(PROJECT_DIR, "scripts",
                                   "run_market_radar_v112y_whale_degraded_mock_replay.py")
        self.assertTrue(os.path.exists(runner_path), f"Runner not found: {runner_path}")

    def test_runner_main_executes_successfully(self):
        import importlib.util
        runner_path = os.path.join(PROJECT_DIR, "scripts",
                                   "run_market_radar_v112y_whale_degraded_mock_replay.py")
        spec = importlib.util.spec_from_file_location("run_market_radar_v112y", runner_path)
        self.assertIsNotNone(spec, "Runner module spec should not be None")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        self.assertTrue(hasattr(mod, 'main'), "Runner should have main() function")
        exit_code = mod.main()
        self.assertEqual(exit_code, 0, f"Runner should exit with 0, got {exit_code}")


# ═══════════════════════════════════════════════════════════════════════════
# Test: All output files exist
# ═══════════════════════════════════════════════════════════════════════════

class TestArtifactFilesExist(unittest.TestCase):
    """Test that all required v112Y output files exist."""

    def test_result_json_exists(self):
        self.assertTrue(os.path.exists(V112Y_RESULT),
                       f"Missing: {V112Y_RESULT}")

    def test_replay_jsonl_exists(self):
        self.assertTrue(os.path.exists(V112Y_RECORDS),
                       f"Missing: {V112Y_RECORDS}")

    def test_run_report_md_exists(self):
        self.assertTrue(os.path.exists(V112Y_RUN_REPORT),
                       f"Missing: {V112Y_RUN_REPORT}")

    def test_handoff_md_exists(self):
        self.assertTrue(os.path.exists(V112Y_HANDOFF),
                       f"Missing: {V112Y_HANDOFF}")

    def test_runner_script_exists(self):
        runner_path = os.path.join(PROJECT_DIR, "scripts",
                                   "run_market_radar_v112y_whale_degraded_mock_replay.py")
        self.assertTrue(os.path.exists(runner_path), f"Missing: {runner_path}")


# ═══════════════════════════════════════════════════════════════════════════
# Test: Result JSON invariants
# ═══════════════════════════════════════════════════════════════════════════

class TestResultJSON(unittest.TestCase):
    """Test the v112Y result JSON invariants per the task-specified schema."""

    @classmethod
    def setUpClass(cls):
        if not os.path.exists(V112Y_RESULT):
            raise unittest.SkipTest(f"Result file not found: {V112Y_RESULT}")
        cls.result = load_json(V112Y_RESULT)

    def test_version_is_v112Y(self):
        self.assertEqual(self.result.get("version"), "v112Y")

    def test_status_passed(self):
        self.assertEqual(self.result.get("status"), "passed")

    def test_input_stop_decision_degrade_to_mock(self):
        self.assertEqual(self.result.get("input_stop_decision"), "DEGRADE_TO_MOCK")

    def test_external_api_called_false(self):
        self.assertFalse(self.result.get("external_api_called"),
                        "external_api_called must be false")

    def test_mock_replay_only_true(self):
        self.assertTrue(self.result.get("mock_replay_only"),
                       "mock_replay_only must be true")

    def test_degraded_replay_built_true(self):
        self.assertTrue(self.result.get("degraded_replay_built"),
                       "degraded_replay_built must be true")

    def test_positions_loaded(self):
        self.assertGreater(self.result.get("positions_loaded", 0), 0,
                          "positions_loaded must be > 0")

    def test_replay_records_written(self):
        self.assertGreater(self.result.get("replay_records_written", 0), 0,
                          "replay_records_written must be > 0")

    def test_eligible_for_real_send_count_zero(self):
        self.assertEqual(self.result.get("eligible_for_real_send_count"), 0,
                        "eligible_for_real_send_count must be 0")

    def test_tg_sent_false(self):
        self.assertFalse(self.result.get("tg_sent"),
                        "tg_sent must be false")

    def test_prod_state_write_false(self):
        self.assertFalse(self.result.get("prod_state_write"),
                        "prod_state_write must be false")

    def test_daemon_started_false(self):
        self.assertFalse(self.result.get("daemon_started"),
                        "daemon_started must be false")

    def test_watcher_started_false(self):
        self.assertFalse(self.result.get("watcher_started"),
                        "watcher_started must be false")

    def test_credentials_read_false(self):
        self.assertFalse(self.result.get("credentials_read"),
                        "credentials_read must be false")

    def test_files_deleted_false(self):
        self.assertFalse(self.result.get("files_deleted"),
                        "files_deleted must be false")

    def test_api_key_used_false(self):
        self.assertFalse(self.result.get("api_key_used"),
                        "api_key_used must be false")

    def test_retry_count_zero(self):
        self.assertEqual(self.result.get("retry_count"), 0,
                        "retry_count must be 0")

    def test_label_confidence_distribution_exists(self):
        dist = self.result.get("label_confidence_distribution", {})
        self.assertIn("high", dist)
        self.assertIn("medium", dist)
        self.assertIn("low", dist)
        self.assertEqual(dist.get("high"), 0, "High confidence labels should be 0")

    def test_null_liquidation_price_count_exists(self):
        self.assertIsNotNone(self.result.get("null_liquidation_price_count"))

    def test_delta_unavailable_count_exists(self):
        self.assertIsNotNone(self.result.get("delta_unavailable_count"))

    def test_local_timestamp_only_count_exists(self):
        self.assertIsNotNone(self.result.get("local_timestamp_only_count"))

    def test_quality_flags_summary_exists(self):
        flags = self.result.get("quality_flags_summary", {})
        self.assertIsInstance(flags, dict)
        self.assertGreater(len(flags), 0, "quality_flags_summary must not be empty")

    def test_next_step_contains_v112Z(self):
        next_step = self.result.get("next_step", "")
        self.assertIn("v112Z", next_step,
                     "next_step should reference v112Z")


# ═══════════════════════════════════════════════════════════════════════════
# Test: Replay records (JSONL)
# ═══════════════════════════════════════════════════════════════════════════

class TestReplayRecords(unittest.TestCase):
    """Test the degraded replay records JSONL file."""

    @classmethod
    def setUpClass(cls):
        if not os.path.exists(V112Y_RECORDS):
            raise unittest.SkipTest(f"Records file not found: {V112Y_RECORDS}")
        cls.records = load_jsonl(V112Y_RECORDS)

    def test_has_records(self):
        self.assertGreater(len(self.records), 0,
                          "Should have at least 1 replay record")

    def test_all_records_have_version(self):
        for r in self.records:
            self.assertEqual(r.get("version"), "v112Y",
                           f"Record {r.get('record_id', '?')}: version must be v112Y")

    def test_all_records_have_record_type(self):
        for r in self.records:
            self.assertEqual(r.get("record_type"), "whale_position_alert_degraded_replay",
                           f"Record {r.get('record_id', '?')}: wrong record_type")

    def test_all_records_eligible_for_real_send_false(self):
        for r in self.records:
            self.assertFalse(r.get("eligible_for_real_send"),
                           f"Record {r.get('record_id', '?')}: eligible_for_real_send must be false")

    def test_all_records_mock_replay_only_true(self):
        for r in self.records:
            self.assertTrue(r.get("mock_replay_only"),
                          f"Record {r.get('record_id', '?')}: mock_replay_only must be true")

    def test_all_records_degraded_true(self):
        for r in self.records:
            self.assertTrue(r.get("degraded"),
                          f"Record {r.get('record_id', '?')}: degraded must be true")

    def test_all_records_have_label_confidence(self):
        for r in self.records:
            conf = r.get("label_confidence")
            self.assertIsNotNone(conf,
                               f"Record {r.get('record_id', '?')}: missing label_confidence")
            self.assertIn(conf, ["high", "medium", "low", "unknown"],
                        f"Record {r.get('record_id', '?')}: invalid label_confidence '{conf}'")

    def test_all_records_have_label_explanation(self):
        for r in self.records:
            explanation = r.get("label_explanation", "")
            self.assertIsNotNone(explanation,
                               f"Record {r.get('record_id', '?')}: missing label_explanation")
            self.assertGreater(len(explanation), 20,
                             f"Record {r.get('record_id', '?')}: label_explanation too short")

    def test_all_low_confidence_have_explanation(self):
        """All low-confidence label records must explain why."""
        for r in self.records:
            if r.get("label_confidence") == "low":
                explanation = r.get("label_explanation", "")
                self.assertGreater(len(explanation), 30,
                                 f"Record {r.get('record_id', '?')}: low confidence needs detailed explanation")

    def test_all_null_liquidation_price_have_note(self):
        """All records with null liquidation_price must have note."""
        for r in self.records:
            if r.get("liquidation_price") is None:
                note = r.get("liquidation_price_note", "")
                self.assertIsNotNone(note,
                                   f"Record {r.get('record_id', '?')}: null liq price missing note")
                self.assertGreater(len(note), 10,
                                 f"Record {r.get('record_id', '?')}: liquidation_price_note too short")

    def test_all_records_have_delta_status(self):
        for r in self.records:
            self.assertEqual(r.get("delta_status"), "unavailable_one_shot_no_previous_position",
                           f"Record {r.get('record_id', '?')}: delta_status must be 'unavailable_one_shot_no_previous_position'")

    def test_all_records_have_delta_explanation(self):
        for r in self.records:
            explanation = r.get("delta_explanation", "")
            self.assertIsNotNone(explanation,
                               f"Record {r.get('record_id', '?')}: missing delta_explanation")
            self.assertGreater(len(explanation), 20,
                             f"Record {r.get('record_id', '?')}: delta_explanation too short")

    def test_all_records_have_timestamp_status_local(self):
        for r in self.records:
            self.assertEqual(r.get("timestamp_status"), "local_observed_at_no_hl_server_timestamp",
                           f"Record {r.get('record_id', '?')}: timestamp_status must be 'local_observed_at_no_hl_server_timestamp'")

    def test_all_records_have_timestamp_explanation(self):
        for r in self.records:
            explanation = r.get("timestamp_explanation", "")
            self.assertIsNotNone(explanation,
                               f"Record {r.get('record_id', '?')}: missing timestamp_explanation")
            self.assertGreater(len(explanation), 20,
                             f"Record {r.get('record_id', '?')}: timestamp_explanation too short")

    def test_all_records_have_quality_flags(self):
        for r in self.records:
            flags = r.get("quality_flags", [])
            self.assertIsInstance(flags, list,
                                f"Record {r.get('record_id', '?')}: quality_flags must be list")
            self.assertGreater(len(flags), 0,
                             f"Record {r.get('record_id', '?')}: quality_flags must not be empty")

    def test_all_records_have_degrade_reasons(self):
        for r in self.records:
            reasons = r.get("degrade_reasons", [])
            self.assertIsInstance(reasons, list,
                                f"Record {r.get('record_id', '?')}: degrade_reasons must be list")
            self.assertGreater(len(reasons), 0,
                             f"Record {r.get('record_id', '?')}: degrade_reasons must not be empty")

    def test_no_record_has_real_send_candidate_true(self):
        """No record may contain real_send_candidate=true."""
        for r in self.records:
            candidate = r.get("real_send_candidate")
            self.assertIsNone(candidate,
                            f"Record {r.get('record_id', '?')}: real_send_candidate should not exist")

    def test_all_records_have_address(self):
        for r in self.records:
            addr = r.get("address", "")
            self.assertTrue(addr.startswith("0x"),
                          f"Record {r.get('record_id', '?')}: address must start with 0x")

    def test_all_records_have_asset(self):
        for r in self.records:
            asset = r.get("asset", "")
            self.assertGreater(len(asset), 0,
                             f"Record {r.get('record_id', '?')}: asset must not be empty")

    def test_all_records_have_side(self):
        for r in self.records:
            side = r.get("side", "")
            self.assertIn(side, ["long", "short", "unknown"],
                        f"Record {r.get('record_id', '?')}: side must be long/short/unknown")


# ═══════════════════════════════════════════════════════════════════════════
# Test: No misleading claims / safety violations in output files
# ═══════════════════════════════════════════════════════════════════════════

class TestNoMisleadingClaims(unittest.TestCase):
    """Test that output files don't contain misleading production claims."""

    FORBIDDEN_PHRASES = [
        "eligible for real send: true",
        "eligible_for_real_send: true",
        "real_send_candidate: true",
        "live passed",
        "live_passed",
        "production ready",
        "已接入正式生产",
        "已真实发送",
        "real send enabled",
        "production state active",
        "live fetch ready",
        "ready for production",
        "production state written",
        "Production state written",
        "real_tg_sent: true",
        "real_tg_sent: True",
    ]

    def _check_file(self, path, label):
        if not os.path.exists(path):
            return []
        try:
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
        except Exception:
            return []
        found = []
        content_lower = content.lower()
        for phrase in self.FORBIDDEN_PHRASES:
            if phrase.lower() in content_lower:
                idx = content_lower.find(phrase.lower())
                context = content[max(0, idx - 30):idx + len(phrase) + 30]
                found.append(f"{label}: '{phrase}' near: ...{context}...")
        return found

    def test_result_json_no_misleading(self):
        issues = self._check_file(V112Y_RESULT, "result.json")
        self.assertEqual(len(issues), 0, f"Misleading claims in result.json: {issues}")

    def test_records_jsonl_no_misleading(self):
        issues = self._check_file(V112Y_RECORDS, "records.jsonl")
        self.assertEqual(len(issues), 0, f"Misleading claims in records.jsonl: {issues}")

    def test_run_report_no_misleading(self):
        issues = self._check_file(V112Y_RUN_REPORT, "run_report.md")
        self.assertEqual(len(issues), 0, f"Misleading claims in run_report.md: {issues}")

    def test_handoff_no_misleading(self):
        issues = self._check_file(V112Y_HANDOFF, "handoff.md")
        self.assertEqual(len(issues), 0, f"Misleading claims in handoff: {issues}")


# ═══════════════════════════════════════════════════════════════════════════
# Test: No secret leaks in output files
# ═══════════════════════════════════════════════════════════════════════════

class TestNoSecretLeaks(unittest.TestCase):
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
        "debug_leak_count",
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
        "credentials_read",
        "no .env",
    ]

    def _check_file(self, path, label):
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
        issues = self._check_file(V112Y_RESULT, "result.json")
        self.assertEqual(len(issues), 0, f"Secrets in result.json: {issues}")

    def test_records_jsonl_no_secrets(self):
        issues = self._check_file(V112Y_RECORDS, "records.jsonl")
        self.assertEqual(len(issues), 0, f"Secrets in records.jsonl: {issues}")

    def test_run_report_no_secrets(self):
        issues = self._check_file(V112Y_RUN_REPORT, "run_report.md")
        self.assertEqual(len(issues), 0, f"Secrets in run_report.md: {issues}")

    def test_handoff_no_secrets(self):
        issues = self._check_file(V112Y_HANDOFF, "handoff.md")
        self.assertEqual(len(issues), 0, f"Secrets in handoff: {issues}")


# ═══════════════════════════════════════════════════════════════════════════
# Test: Run report content
# ═══════════════════════════════════════════════════════════════════════════

class TestRunReportContent(unittest.TestCase):
    """Test the v112Y run report markdown content."""

    @classmethod
    def setUpClass(cls):
        if not os.path.exists(V112Y_RUN_REPORT):
            raise unittest.SkipTest(f"Run report not found: {V112Y_RUN_REPORT}")
        with open(V112Y_RUN_REPORT, "r", encoding="utf-8") as f:
            cls.content = f.read()

    def test_mentions_DEGRADE_TO_MOCK(self):
        self.assertIn("DEGRADE_TO_MOCK", self.content,
                     "Run report should mention DEGRADE_TO_MOCK")

    def test_mentions_label_confidence(self):
        content_lower = self.content.lower()
        self.assertIn("label confidence", content_lower,
                     "Run report should discuss label confidence")

    def test_mentions_liquidation_price(self):
        content_lower = self.content.lower()
        self.assertIn("liquidation", content_lower,
                     "Run report should discuss liquidation price")

    def test_mentions_delta_unavailable(self):
        content_lower = self.content.lower()
        self.assertIn("delta", content_lower,
                     "Run report should discuss delta unavailability")

    def test_mentions_local_timestamp(self):
        content_lower = self.content.lower()
        self.assertIn("timestamp", content_lower,
                     "Run report should discuss timestamp")

    def test_mentions_eligible_for_real_send(self):
        content_lower = self.content.lower()
        self.assertIn("eligible", content_lower,
                     "Run report should discuss eligibility")

    def test_mentions_next_step_v112Z(self):
        content_lower = self.content.lower()
        self.assertIn("v112z", content_lower,
                     "Run report should mention v112Z next step")

    def test_mentions_safety(self):
        self.assertIn("Safety", self.content,
                     "Run report should have Safety Checklist section")


# ═══════════════════════════════════════════════════════════════════════════
# Test: Handoff content
# ═══════════════════════════════════════════════════════════════════════════

class TestHandoffContent(unittest.TestCase):
    """Test the v112Y handoff markdown content."""

    @classmethod
    def setUpClass(cls):
        if not os.path.exists(V112Y_HANDOFF):
            raise unittest.SkipTest(f"Handoff not found: {V112Y_HANDOFF}")
        with open(V112Y_HANDOFF, "r", encoding="utf-8") as f:
            cls.content = f.read()

    def test_mentions_what_was_done(self):
        self.assertIn("What v112Y Did", self.content,
                     "Handoff should have 'What v112Y Did' section")

    def test_mentions_files_read(self):
        self.assertIn("Files Read", self.content,
                     "Handoff should have 'Files Read' section")

    def test_mentions_files_generated(self):
        self.assertIn("Files Generated", self.content,
                     "Handoff should have 'Files Generated' section")

    def test_mentions_safety_invariant(self):
        self.assertIn("Safety Invariant", self.content,
                     "Handoff should have Safety Invariant section")

    def test_mentions_next_step(self):
        content_lower = self.content.lower()
        self.assertIn("v112z", content_lower,
                     "Handoff should mention v112Z next step")

    def test_mentions_DEGRADE_TO_MOCK(self):
        self.assertIn("DEGRADE_TO_MOCK", self.content,
                     "Handoff should mention DEGRADE_TO_MOCK")

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
    print("v112Y Whale Degraded Mock Replay Test Suite")
    print("=" * 70)
    print()

    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    suite.addTests(loader.loadTestsFromTestCase(TestRunnerExecutable))
    suite.addTests(loader.loadTestsFromTestCase(TestArtifactFilesExist))
    suite.addTests(loader.loadTestsFromTestCase(TestResultJSON))
    suite.addTests(loader.loadTestsFromTestCase(TestReplayRecords))
    suite.addTests(loader.loadTestsFromTestCase(TestNoMisleadingClaims))
    suite.addTests(loader.loadTestsFromTestCase(TestNoSecretLeaks))
    suite.addTests(loader.loadTestsFromTestCase(TestRunReportContent))
    suite.addTests(loader.loadTestsFromTestCase(TestHandoffContent))

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
