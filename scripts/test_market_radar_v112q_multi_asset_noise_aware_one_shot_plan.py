"""Tests for v1.12-Q Multi-Asset Market Sync Noise-Aware One-Shot Plan.

Covers:
  - Runner executes successfully
  - All output files exist (result JSON, noise case results JSONL, report MD, handoff MD)
  - result JSON has correct fields and values (status=passed, dry_run_only=true, etc.)
  - Noise case results JSONL has 6 entries with all required fields
  - 6 noise case categories are covered
  - Specific case assertions (two_of_three blocked, volume spike blocked, timestamp skew blocked/degraded, leader driven blocked/downgraded)
  - No secret/key/token/cookie/password clear text in any output
  - No misleading "live API connected", "already sent", "production ready" language
  - Upstream tests (v112P, v112O, v112N, v112G) continue to pass

Usage:
    python scripts/test_market_radar_v112q_multi_asset_noise_aware_one_shot_plan.py
"""

from __future__ import annotations

import io
import json
import re
import subprocess
import sys
import unittest
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

# Fix Windows GBK encoding for emoji output
if sys.stdout.encoding != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

CN_TZ = timezone(timedelta(hours=8))

RESULT_JSON_PATH = ROOT / "results" / "market_radar_v112q_multi_asset_noise_aware_plan_result.json"
NOISE_RESULTS_JSONL_PATH = ROOT / "results" / "market_radar_v112q_multi_asset_noise_case_results.jsonl"
REPORT_MD_PATH = ROOT / "runs" / "market_radar" / "v112q_multi_asset_noise_aware_one_shot_plan.md"
HANDOFF_MD_PATH = ROOT / "runs" / "market_radar" / "v112q_multi_asset_noise_aware_one_shot_plan_handoff.md"
RUNNER_PATH = ROOT / "scripts" / "run_market_radar_v112q_multi_asset_noise_aware_one_shot_plan.py"

# Patterns that indicate real credential leaks
FORBIDDEN_PATTERNS = [
    r'\bsecret\s*[=:]\s*\S',
    r'\bsecret\s*key\b',
    r'\bsecret\s*token\b',
    r'\bapi[_\-]?secret\b',
    r'\bapi[_\-]?key\s*[=:]\s*\S',
    r'\bchat[_\-]?id\s*[=:]\s*\S',
    r'\bpassword\s*[=:]\s*\S',
    r'\bbearer\s+\S',
    r'\bauthorization\s*:\s*\S',
    r'\bx-api-key\s*[=:]\s*\S',
    r'\bcookie\s*[=:]\s*\S',
    r'[A-Za-z]:\\(?:Users|Program|Windows)',
    r'\btoken\s*[=:]\s*[a-zA-Z0-9_\-]{8,}',
    r'\bkey\s*[=:]\s*[a-zA-Z0-9_\-]{8,}',
]

MISLEADING_TERMS = [
    "已接入 live source",
    "live source connected",
    "production ready",
    "已发送",
    "正式发布",
    "real sent",
    "已推送",
    "已投递",
    "broadcast sent",
    "message delivered",
    "sent to channel",
    "已发布成功",
    "发送成功",
    "live API connected",
    "已接入 live API",
    "已真实发送",
]

REQUIRED_NOISE_CASES = [
    "clean_sync_should_pass",
    "two_of_three_direction_should_block",
    "single_asset_volume_spike_should_block",
    "timestamp_skew_should_block",
    "leader_driven_move_should_downgrade_or_block",
    "mixed_sector_should_flag_low_confidence",
]

REQUIRED_RESULT_FIELDS = [
    "version", "status", "dry_run_only", "live_ready", "real_tg_sent",
    "external_api_called", "external_ai_called", "daemon_started",
    "files_deleted", "debug_leak_count", "secret_leak_count",
    "candidate_card_type", "one_shot_plan_ready",
    "noise_injection_cases_total", "noise_injection_cases_passed",
    "stricter_thresholds_ready", "real_send_ready",
    "production_state_write_ready", "real_live_api_called",
    "recommended_second_candidate",
]

REQUIRED_CASE_RESULT_FIELDS = [
    "case_id", "expected_result", "actual_result", "passed", "reason",
    "direction_agreement", "timestamp_skew_seconds", "leader_driven",
    "confidence_level", "noise_vectors_triggered",
]


class TestV112QMultiAssetNoiseAwareOneShotPlan(unittest.TestCase):
    """Test suite for v112Q Multi-Asset Market Sync Noise-Aware One-Shot Plan."""

    @classmethod
    def setUpClass(cls):
        """Run the v112Q runner before all tests."""
        print(f"\n{'='*60}")
        print("Running v112Q Multi-Asset Market Sync Noise-Aware One-Shot Plan runner...")
        print(f"{'='*60}\n")

        result = subprocess.run(
            [sys.executable, str(RUNNER_PATH)],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=120,
        )

        cls.runner_exit_code = result.returncode
        cls.runner_stdout = result.stdout
        cls.runner_stderr = result.stderr

        if cls.runner_exit_code != 0:
            print(f"Runner stdout (last 2000 chars):\n{result.stdout[-2000:]}")
            print(f"Runner stderr (last 500 chars):\n{result.stderr[-500:]}")

        # Load result files for assertions
        cls.result_json = None
        cls.noise_results = []
        cls.report_text = ""
        cls.handoff_text = ""

        if RESULT_JSON_PATH.exists():
            with open(RESULT_JSON_PATH, "r", encoding="utf-8") as f:
                cls.result_json = json.load(f)

        if NOISE_RESULTS_JSONL_PATH.exists():
            with open(NOISE_RESULTS_JSONL_PATH, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        cls.noise_results.append(json.loads(line))

        if REPORT_MD_PATH.exists():
            with open(REPORT_MD_PATH, "r", encoding="utf-8") as f:
                cls.report_text = f.read()

        if HANDOFF_MD_PATH.exists():
            with open(HANDOFF_MD_PATH, "r", encoding="utf-8") as f:
                cls.handoff_text = f.read()

    # ── Runner execution ───────────────────────────────────────────────────────

    def test_001_runner_executes_successfully(self):
        """Runner should exit with code 0."""
        self.assertEqual(
            self.runner_exit_code, 0,
            f"Runner failed with exit code {self.runner_exit_code}. "
            f"stderr: {self.runner_stderr[-500:]}"
        )

    # ── Output file existence ──────────────────────────────────────────────────

    def test_002_result_json_exists(self):
        """Result JSON file should exist."""
        self.assertTrue(
            RESULT_JSON_PATH.exists(),
            f"Result JSON not found: {RESULT_JSON_PATH}"
        )

    def test_003_noise_results_jsonl_exists(self):
        """Noise case results JSONL should exist."""
        self.assertTrue(
            NOISE_RESULTS_JSONL_PATH.exists(),
            f"Noise results JSONL not found: {NOISE_RESULTS_JSONL_PATH}"
        )

    def test_004_report_md_exists(self):
        """Report MD should exist."""
        self.assertTrue(
            REPORT_MD_PATH.exists(),
            f"Report MD not found: {REPORT_MD_PATH}"
        )

    def test_005_handoff_md_exists(self):
        """Handoff MD should exist."""
        self.assertTrue(
            HANDOFF_MD_PATH.exists(),
            f"Handoff MD not found: {HANDOFF_MD_PATH}"
        )

    # ── Result JSON assertions ─────────────────────────────────────────────────

    def test_010_status_passed(self):
        """Result JSON: status should be 'passed'."""
        self.assertIsNotNone(self.result_json, "Result JSON is None")
        self.assertEqual(self.result_json.get("status"), "passed")

    def test_011_dry_run_only(self):
        """Result JSON: dry_run_only should be true."""
        self.assertTrue(self.result_json.get("dry_run_only"))

    def test_012_live_ready(self):
        """Result JSON: live_ready should be false."""
        self.assertFalse(self.result_json.get("live_ready"))

    def test_013_real_tg_sent(self):
        """Result JSON: real_tg_sent should be false."""
        self.assertFalse(self.result_json.get("real_tg_sent"))

    def test_014_external_api_called(self):
        """Result JSON: external_api_called should be false."""
        self.assertFalse(self.result_json.get("external_api_called"))

    def test_015_external_ai_called(self):
        """Result JSON: external_ai_called should be false."""
        self.assertFalse(self.result_json.get("external_ai_called"))

    def test_016_daemon_started(self):
        """Result JSON: daemon_started should be false."""
        self.assertFalse(self.result_json.get("daemon_started"))

    def test_017_files_deleted(self):
        """Result JSON: files_deleted should be false."""
        self.assertFalse(self.result_json.get("files_deleted"))

    def test_018_candidate_card_type(self):
        """Result JSON: candidate_card_type should be 'multi_asset_market_sync'."""
        self.assertEqual(
            self.result_json.get("candidate_card_type"),
            "multi_asset_market_sync"
        )

    def test_019_one_shot_plan_ready(self):
        """Result JSON: one_shot_plan_ready should be true."""
        self.assertTrue(self.result_json.get("one_shot_plan_ready"))

    def test_020_noise_injection_cases_total(self):
        """Result JSON: noise_injection_cases_total should be >= 6."""
        total = self.result_json.get("noise_injection_cases_total", 0)
        self.assertGreaterEqual(total, 6, f"Expected >=6 noise cases, got {total}")

    def test_021_noise_injection_cases_passed(self):
        """Result JSON: noise_injection_cases_passed should equal total."""
        total = self.result_json.get("noise_injection_cases_total", 0)
        passed = self.result_json.get("noise_injection_cases_passed", 0)
        self.assertEqual(passed, total,
                       f"Expected all {total} cases passed, got {passed}")

    def test_022_stricter_thresholds_ready(self):
        """Result JSON: stricter_thresholds_ready should be true."""
        self.assertTrue(self.result_json.get("stricter_thresholds_ready"))

    def test_023_real_live_api_called(self):
        """Result JSON: real_live_api_called should be false."""
        self.assertFalse(self.result_json.get("real_live_api_called"))

    def test_024_real_send_ready(self):
        """Result JSON: real_send_ready should be false."""
        self.assertFalse(self.result_json.get("real_send_ready"))

    def test_025_production_state_write_ready(self):
        """Result JSON: production_state_write_ready should be false."""
        self.assertFalse(self.result_json.get("production_state_write_ready"))

    def test_026_debug_leak_count_zero(self):
        """Result JSON: debug_leak_count should be 0."""
        self.assertEqual(self.result_json.get("debug_leak_count"), 0)

    def test_027_secret_leak_count_zero(self):
        """Result JSON: secret_leak_count should be 0."""
        self.assertEqual(self.result_json.get("secret_leak_count"), 0)

    def test_028_recommended_second_candidate(self):
        """Result JSON: recommended_second_candidate should be 'whale_position_alert'."""
        self.assertEqual(
            self.result_json.get("recommended_second_candidate"),
            "whale_position_alert"
        )

    def test_029_upstream_validated(self):
        """Result JSON: upstream_validated should be true."""
        self.assertTrue(self.result_json.get("upstream_validated"))

    def test_030_all_required_fields(self):
        """Result JSON should contain all required fields."""
        for field in REQUIRED_RESULT_FIELDS:
            self.assertIn(field, self.result_json,
                         f"Missing required field '{field}' in result JSON")

    # ── Noise case results assertions ──────────────────────────────────────────

    def test_040_six_noise_results(self):
        """Should have exactly 6 noise case results."""
        self.assertEqual(len(self.noise_results), 6,
                       f"Expected 6 noise case results, got {len(self.noise_results)}")

    def test_041_all_six_case_ids(self):
        """All 6 required noise case IDs should be present."""
        case_ids = {r.get("case_id") for r in self.noise_results}
        for case_id in REQUIRED_NOISE_CASES:
            self.assertIn(case_id, case_ids,
                         f"Missing noise case '{case_id}'")

    def test_042_all_cases_have_required_fields(self):
        """Each noise case result should have all required fields."""
        for r in self.noise_results:
            for field in REQUIRED_CASE_RESULT_FIELDS:
                self.assertIn(field, r,
                            f"Noise case '{r.get('case_id')}' missing field '{field}'")

    def test_043_clean_sync_should_pass(self):
        """clean_sync_should_pass: expected passed, actual passed."""
        r = self._find_case("clean_sync_should_pass")
        self.assertIsNotNone(r, "Case not found")
        self.assertEqual(r["expected_result"], "passed")
        self.assertEqual(r["actual_result"], "passed")
        self.assertTrue(r["passed"])
        self.assertEqual(r["confidence_level"], "high")

    def test_044_two_of_three_direction_should_block(self):
        """two_of_three_direction_should_block: must be blocked."""
        r = self._find_case("two_of_three_direction_should_block")
        self.assertIsNotNone(r, "Case not found")
        self.assertEqual(r["expected_result"], "blocked")
        self.assertEqual(r["actual_result"], "blocked",
                       f"Expected 'blocked' but got '{r['actual_result']}': {r.get('reason')}")
        self.assertTrue(r["passed"])
        # Direction agreement should be ~0.67 (2/3)
        self.assertAlmostEqual(r["direction_agreement"], 0.667, delta=0.01)

    def test_045_single_asset_volume_spike_should_block(self):
        """single_asset_volume_spike_should_block: must be blocked."""
        r = self._find_case("single_asset_volume_spike_should_block")
        self.assertIsNotNone(r, "Case not found")
        self.assertEqual(r["expected_result"], "blocked")
        self.assertEqual(r["actual_result"], "blocked",
                       f"Expected 'blocked' but got '{r['actual_result']}': {r.get('reason')}")
        self.assertTrue(r["passed"])
        self.assertIn("single_asset_volume_distortion", r["noise_vectors_triggered"])

    def test_046_timestamp_skew_should_block_or_degrade(self):
        """timestamp_skew_should_block: must be blocked or degraded."""
        r = self._find_case("timestamp_skew_should_block")
        self.assertIsNotNone(r, "Case not found")
        self.assertIn(r["actual_result"], ["blocked", "degraded"],
                    f"Expected 'blocked' or 'degraded' but got '{r['actual_result']}'")
        self.assertTrue(r["passed"])
        self.assertGreater(r["timestamp_skew_seconds"], 60,
                         f"Expected timestamp skew >60s, got {r['timestamp_skew_seconds']}s")

    def test_047_leader_driven_should_downgrade_or_block(self):
        """leader_driven_move_should_downgrade_or_block: must be blocked or downgraded."""
        r = self._find_case("leader_driven_move_should_downgrade_or_block")
        self.assertIsNotNone(r, "Case not found")
        self.assertIn(r["actual_result"], ["blocked", "downgraded"],
                    f"Expected 'blocked' or 'downgraded' but got '{r['actual_result']}'")
        self.assertTrue(r["passed"])
        self.assertTrue(r["leader_driven"],
                      f"Expected leader_driven=true, got {r['leader_driven']}")

    def test_048_mixed_sector_low_confidence(self):
        """mixed_sector_should_flag_low_confidence: should be low_confidence."""
        r = self._find_case("mixed_sector_should_flag_low_confidence")
        self.assertIsNotNone(r, "Case not found")
        self.assertTrue(r["passed"])
        self.assertEqual(r["confidence_level"], "low")
        self.assertIn("sector_dispersion", r["noise_vectors_triggered"])

    def test_049_clean_sync_no_noise_vectors(self):
        """clean_sync_should_pass should have no noise vectors triggered."""
        r = self._find_case("clean_sync_should_pass")
        self.assertIsNotNone(r, "Case not found")
        self.assertEqual(len(r["noise_vectors_triggered"]), 0)

    # ── Security assertions ────────────────────────────────────────────────────

    def _check_no_secret_patterns(self, text: str, label: str) -> None:
        """Check that text contains no real secret patterns."""
        text_lower = text.lower()
        for pattern in FORBIDDEN_PATTERNS:
            self.assertIsNone(
                re.search(pattern, text_lower),
                f"Secret pattern '{pattern}' matched in {label}"
            )

    def test_050_no_secrets_in_result_json(self):
        """Result JSON must not contain secret patterns."""
        if self.result_json is None:
            self.skipTest("Result JSON not loaded")
        values_text = " ".join(
            str(v) for v in self.result_json.values()
            if isinstance(v, (str, int, float, bool, list))
        )
        self._check_no_secret_patterns(values_text, "result JSON values")

    def test_051_no_secrets_in_noise_results(self):
        """Noise case results must not contain secret patterns."""
        for r in self.noise_results:
            text = json.dumps(r, ensure_ascii=False)
            self._check_no_secret_patterns(text, f"noise case {r.get('case_id')}")

    def test_052_no_secrets_in_report(self):
        """Report MD must not contain secret patterns."""
        self._check_no_secret_patterns(self.report_text, "report MD")

    def test_053_no_secrets_in_handoff(self):
        """Handoff MD must not contain secret patterns."""
        self._check_no_secret_patterns(self.handoff_text, "handoff MD")

    def _check_no_misleading(self, text: str, label: str) -> None:
        """Check text for misleading language."""
        text_lower = text.lower()
        for term in MISLEADING_TERMS:
            self.assertNotIn(
                term.lower(), text_lower,
                f"Misleading term '{term}' found in {label}"
            )

    def test_054_no_misleading_in_report(self):
        """Report must not contain misleading language."""
        self._check_no_misleading(self.report_text, "report MD")

    def test_055_no_misleading_in_handoff(self):
        """Handoff must not contain misleading language."""
        self._check_no_misleading(self.handoff_text, "handoff MD")

    def test_056_no_misleading_in_result_json(self):
        """Result JSON values must not contain misleading language."""
        if self.result_json is None:
            self.skipTest("Result JSON not loaded")
        values_text = " ".join(
            str(v) for v in self.result_json.values()
            if isinstance(v, (str, int, float, bool, list))
        )
        self._check_no_misleading(values_text, "result JSON values")

    # ── Content assertions ─────────────────────────────────────────────────────

    def test_060_runner_stdout_mentions_v112p(self):
        """Runner stdout should mention v112P validation."""
        self.assertIn("v112P", self.runner_stdout)

    def test_061_runner_stdout_mentions_v112o(self):
        """Runner stdout should mention v112O validation."""
        self.assertIn("v112O", self.runner_stdout)

    def test_062_runner_stdout_mentions_noise(self):
        """Runner stdout should mention noise cases."""
        self.assertIn("noise", self.runner_stdout.lower())

    def test_063_report_mentions_news_event_market_impact(self):
        """Report should explain why not news_event_market_impact."""
        self.assertIn("news_event_market_impact", self.report_text.lower())

    def test_064_report_mentions_signal_quality(self):
        """Report should mention signal quality / false positive gap."""
        found = "signal quality" in self.report_text.lower() or \
                "false positive" in self.report_text.lower() or \
                "false_positive" in self.report_text.lower()
        self.assertTrue(found, "Report should mention signal quality / false positive gap")

    def test_065_report_has_noise_table(self):
        """Report should contain a noise case results table."""
        self.assertIn("| # | Case ID | Expected | Actual | Passed |", self.report_text)

    def test_066_report_mentions_next_steps(self):
        """Report should contain next steps / v112R recommendation."""
        self.assertIn("v112R", self.report_text)

    def test_067_report_mentions_whale_position_alert(self):
        """Report should recommend whale_position_alert as second candidate."""
        self.assertIn("whale_position_alert", self.report_text.lower())

    def test_068_handoff_mentions_upstream_artifacts(self):
        """Handoff should list upstream artifacts read."""
        self.assertIn("v112P", self.handoff_text)
        self.assertIn("v112O", self.handoff_text)

    def test_069_handoff_has_safety_section(self):
        """Handoff should explicitly state what is NOT enabled."""
        handoff_lower = self.handoff_text.lower()
        self.assertIn("not called", handoff_lower)
        self.assertIn("not sent", handoff_lower)
        self.assertIn("not started", handoff_lower)

    # ── Idempotency / re-run stability ─────────────────────────────────────────

    def test_070_rerun_produces_same_result(self):
        """Re-running should produce the same result JSON key values."""
        # Second run
        result2 = subprocess.run(
            [sys.executable, str(RUNNER_PATH)],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=120,
        )
        self.assertEqual(result2.returncode, 0,
                       f"Re-run failed with exit code {result2.returncode}")

        if RESULT_JSON_PATH.exists():
            with open(RESULT_JSON_PATH, "r", encoding="utf-8") as f:
                result2_json = json.load(f)

            self.assertEqual(result2_json.get("status"), "passed")
            self.assertEqual(result2_json.get("candidate_card_type"), "multi_asset_market_sync")
            self.assertEqual(result2_json.get("one_shot_plan_ready"), True)
            self.assertEqual(result2_json.get("stricter_thresholds_ready"), True)
            self.assertEqual(result2_json.get("dry_run_only"), True)
            self.assertEqual(result2_json.get("live_ready"), False)
            self.assertEqual(result2_json.get("real_tg_sent"), False)
            self.assertEqual(result2_json.get("external_api_called"), False)
            self.assertEqual(result2_json.get("external_ai_called"), False)
            self.assertEqual(result2_json.get("real_send_ready"), False)
            self.assertEqual(result2_json.get("real_live_api_called"), False)
            self.assertEqual(result2_json.get("production_state_write_ready"), False)
            self.assertEqual(result2_json.get("debug_leak_count"), 0)
            self.assertEqual(result2_json.get("secret_leak_count"), 0)
            self.assertEqual(result2_json.get("recommended_second_candidate"), "whale_position_alert")
            self.assertGreaterEqual(result2_json.get("noise_injection_cases_total", 0), 6)
            self.assertEqual(
                result2_json.get("noise_injection_cases_total"),
                result2_json.get("noise_injection_cases_passed")
            )

        # Noise results should be unchanged
        if NOISE_RESULTS_JSONL_PATH.exists():
            results2 = []
            with open(NOISE_RESULTS_JSONL_PATH, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        results2.append(json.loads(line))

            self.assertEqual(len(results2), 6)

            # All cases should have the same actual_result
            results1_map = {r["case_id"]: r for r in self.noise_results}
            results2_map = {r["case_id"]: r for r in results2}
            for case_id in results1_map:
                self.assertIn(case_id, results2_map,
                            f"Case '{case_id}' missing in re-run")
                self.assertEqual(
                    results1_map[case_id]["actual_result"],
                    results2_map[case_id]["actual_result"],
                    f"Case '{case_id}': actual_result changed between runs"
                )
                self.assertEqual(
                    results1_map[case_id]["passed"],
                    results2_map[case_id]["passed"],
                    f"Case '{case_id}': passed changed between runs"
                )

    # ── Upstream test validation ───────────────────────────────────────────────

    def test_080_upstream_v112p_test_passes(self):
        """v112P test should still pass."""
        v112p_test = ROOT / "scripts" / "test_market_radar_v112p_live_source_readiness_audit.py"
        if not v112p_test.exists():
            self.skipTest(f"v112P test not found: {v112p_test}")
        result = subprocess.run(
            [sys.executable, str(v112p_test)],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=120,
        )
        self.assertEqual(result.returncode, 0,
                       f"v112P test failed with exit code {result.returncode}. "
                       f"stderr: {result.stderr[-500:]}")

    def test_081_upstream_v112o_test_passes(self):
        """v112O test should still pass."""
        v112o_test = ROOT / "scripts" / "test_market_radar_v112o_send_preview_pack.py"
        if not v112o_test.exists():
            self.skipTest(f"v112O test not found: {v112o_test}")
        result = subprocess.run(
            [sys.executable, str(v112o_test)],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=120,
        )
        self.assertEqual(result.returncode, 0,
                       f"v112O test failed with exit code {result.returncode}. "
                       f"stderr: {result.stderr[-500:]}")

    def test_082_upstream_v112n_test_passes(self):
        """v112N test should still pass."""
        v112n_test = ROOT / "scripts" / "test_market_radar_v112n_local_master_dryrun.py"
        if not v112n_test.exists():
            self.skipTest(f"v112N test not found: {v112n_test}")
        result = subprocess.run(
            [sys.executable, str(v112n_test)],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=120,
        )
        self.assertEqual(result.returncode, 0,
                       f"v112N test failed with exit code {result.returncode}. "
                       f"stderr: {result.stderr[-500:]}")

    def test_083_upstream_v112g_test_passes(self):
        """v112G test should still pass."""
        v112g_test = ROOT / "scripts" / "test_market_radar_multi_asset_sync_feed_v112g.py"
        if not v112g_test.exists():
            self.skipTest(f"v112G test not found: {v112g_test}")
        result = subprocess.run(
            [sys.executable, str(v112g_test)],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=120,
        )
        self.assertEqual(result.returncode, 0,
                       f"v112G test failed with exit code {result.returncode}. "
                       f"stderr: {result.stderr[-500:]}")

    # ── Specific mandatory assertions from task ────────────────────────────────

    def test_090_report_mentions_why_multi_asset(self):
        """Report must explain why multi_asset_market_sync was chosen."""
        report_lower = self.report_text.lower()
        self.assertTrue(
            "why v112q selected multi_asset_market_sync" in report_lower or
            "selected multi_asset" in report_lower,
            "Report should explain why multi_asset_market_sync was selected"
        )

    def test_091_report_mentions_why_not_news(self):
        """Report must explain why news_event_market_impact was NOT chosen."""
        report_lower = self.report_text.lower()
        self.assertTrue(
            "why not news" in report_lower.replace(" ", "") or
            "not news_event_market_impact" in report_lower.replace("_", "") or
            "not news" in report_lower.replace(".", ""),
            "Report should explain why news_event_market_impact was NOT selected"
        )

    def test_092_report_mentions_six_noise_risks(self):
        """Report should mention all 6 noise risk categories."""
        for case_id in REQUIRED_NOISE_CASES:
            # Check for case_id or its description
            self.assertIn(
                case_id, self.report_text,
                f"Report should contain noise case '{case_id}'"
            )

    def test_093_report_mentions_real_send_not_ready(self):
        """Report must mention why real send is NOT ready."""
        found = "not ready" in self.report_text.lower() or \
                "still not ready" in self.report_text.lower() or \
                "blockers remain" in self.report_text.lower() or \
                "Real Send Is Still NOT Ready" in self.report_text
        self.assertTrue(found, "Report should explain why real send is still not ready")

    def test_094_handoff_recommends_v112r(self):
        """Handoff should recommend v112R proceed."""
        found = "v112R" in self.handoff_text or "v112r" in self.handoff_text.lower()
        self.assertTrue(found, "Handoff should mention v112R recommendation")

    def test_095_no_live_api_in_outputs(self):
        """None of the outputs should claim live API was called."""
        combined = json.dumps(self.result_json, ensure_ascii=False) + \
                   json.dumps(self.noise_results, ensure_ascii=False) + \
                   self.report_text + self.handoff_text
        combined_lower = combined.lower()
        forbidden = ["real api data", "live api data fetched", "api call succeeded"]
        for term in forbidden:
            self.assertNotIn(term, combined_lower,
                           f"Forbidden phrase '{term}' found in outputs")

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _find_case(self, case_id: str) -> dict | None:
        """Find a noise case result by case_id."""
        for r in self.noise_results:
            if r.get("case_id") == case_id:
                return r
        return None


if __name__ == "__main__":
    unittest.main(verbosity=2)
