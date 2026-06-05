"""Tests for v1.12-P Live Source Readiness Audit.

Covers:
  - Runner executes successfully
  - All output files exist (result JSON, matrix JSON, report MD, handoff MD)
  - result JSON has correct fields and values
  - Readiness matrix contains 5 card types with all required fields
  - Each card type has required_live_sources, required_fields, failure_modes,
    fallback_strategy, readiness_score, readiness_level
  - At least 1 card type supports one-shot experiment
  - No secret/key/token/cookie/password clear text in any output
  - No misleading "already sent" / "live source connected" / "production ready" language
  - v112N and v112O were validated as passed

Usage:
    python scripts/test_market_radar_v112p_live_source_readiness_audit.py
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

RESULT_JSON_PATH = ROOT / "results" / "market_radar_v112p_live_source_readiness_audit_result.json"
MATRIX_JSON_PATH = ROOT / "results" / "market_radar_v112p_live_source_matrix.json"
REPORT_MD_PATH = ROOT / "runs" / "market_radar" / "v112p_live_source_readiness_audit.md"
HANDOFF_MD_PATH = ROOT / "runs" / "market_radar" / "v112p_live_source_readiness_audit_handoff.md"
RUNNER_PATH = ROOT / "scripts" / "run_market_radar_v112p_live_source_readiness_audit.py"

REQUIRED_CARD_TYPES = [
    "price_oi_volume_anomaly",
    "whale_position_alert",
    "liquidation_pressure",
    "multi_asset_market_sync",
    "news_event_market_impact",
]

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
]


class TestV112PLiveSourceReadinessAudit(unittest.TestCase):
    """Test suite for v112P Live Source Readiness Audit."""

    @classmethod
    def setUpClass(cls):
        """Run the v112P runner before all tests."""
        print(f"\n{'='*60}")
        print("Running v112P Live Source Readiness Audit runner...")
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
        cls.matrix_json = None
        cls.matrix_entries = []
        cls.report_text = ""
        cls.handoff_text = ""

        if RESULT_JSON_PATH.exists():
            with open(RESULT_JSON_PATH, "r", encoding="utf-8") as f:
                cls.result_json = json.load(f)

        if MATRIX_JSON_PATH.exists():
            with open(MATRIX_JSON_PATH, "r", encoding="utf-8") as f:
                cls.matrix_json = json.load(f)
                cls.matrix_entries = cls.matrix_json.get("entries", [])

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

    def test_003_matrix_json_exists(self):
        """Matrix JSON file should exist."""
        self.assertTrue(
            MATRIX_JSON_PATH.exists(),
            f"Matrix JSON not found: {MATRIX_JSON_PATH}"
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

    def test_018_real_send_ready(self):
        """Result JSON: real_send_ready should be false."""
        self.assertFalse(self.result_json.get("real_send_ready"))

    def test_019_production_state_write_ready(self):
        """Result JSON: production_state_write_ready should be false."""
        self.assertFalse(self.result_json.get("production_state_write_ready"))

    def test_020_card_types_total(self):
        """Result JSON: card_types_total should be 5."""
        self.assertEqual(self.result_json.get("card_types_total"), 5)

    def test_021_readiness_matrix_ready(self):
        """Result JSON: readiness_matrix_ready should be true."""
        self.assertTrue(self.result_json.get("readiness_matrix_ready"))

    def test_022_debug_leak_count_zero(self):
        """Result JSON: debug_leak_count should be 0."""
        self.assertEqual(self.result_json.get("debug_leak_count"), 0)

    def test_023_secret_leak_count_zero(self):
        """Result JSON: secret_leak_count should be 0."""
        self.assertEqual(self.result_json.get("secret_leak_count"), 0)

    def test_024_manual_review_required(self):
        """Result JSON: manual_review_required_before_send should be true."""
        self.assertTrue(self.result_json.get("manual_review_required_before_send"))

    def test_025_has_recommended_candidate(self):
        """Result JSON: recommended_first_one_shot_candidate should not be empty."""
        rec = self.result_json.get("recommended_first_one_shot_candidate", "")
        self.assertTrue(rec, "Recommended candidate is empty")
        self.assertIn(rec, REQUIRED_CARD_TYPES,
                     f"Recommended candidate '{rec}' not in known card types")

    def test_026_one_shot_candidates_count(self):
        """Result JSON: one_shot_candidates_count should be >= 1."""
        count = self.result_json.get("one_shot_candidates_count", 0)
        self.assertGreaterEqual(count, 1,
                              f"Expected at least 1 one-shot candidate, got {count}")

    def test_027_v112n_validated(self):
        """Result JSON: v112n_validated should be true."""
        self.assertTrue(self.result_json.get("v112n_validated"))

    def test_028_v112o_validated(self):
        """Result JSON: v112o_validated should be true."""
        self.assertTrue(self.result_json.get("v112o_validated"))

    # ── Matrix assertions ─────────────────────────────────────────────────────

    def test_030_matrix_has_5_entries(self):
        """Matrix should contain exactly 5 entries."""
        self.assertEqual(len(self.matrix_entries), 5,
                       f"Expected 5 matrix entries, got {len(self.matrix_entries)}")

    def test_031_all_card_types_present(self):
        """All 5 required card types should be in the matrix."""
        matrix_types = {e.get("card_type") for e in self.matrix_entries}
        for ct in REQUIRED_CARD_TYPES:
            self.assertIn(ct, matrix_types,
                         f"Card type '{ct}' missing from readiness matrix")

    def _check_matrix_entry_fields(self, entry: dict, card_type: str):
        """Check that a matrix entry has all required fields."""
        required_string_fields = [
            "card_type", "current_status", "readiness_level", "next_step_recommendation",
        ]
        for field in required_string_fields:
            self.assertIn(field, entry, f"{card_type}: missing field '{field}'")
            self.assertTrue(isinstance(entry[field], str),
                          f"{card_type}: '{field}' should be string")

        required_list_fields = [
            "required_live_sources", "required_fields", "failure_modes", "fallback_strategy",
        ]
        for field in required_list_fields:
            self.assertIn(field, entry, f"{card_type}: missing field '{field}'")
            self.assertTrue(isinstance(entry[field], list),
                          f"{card_type}: '{field}' should be list")
            self.assertTrue(len(entry[field]) > 0,
                          f"{card_type}: '{field}' should not be empty")

        required_bool_fields = [
            "credential_required", "paid_api_likely_required",
            "websocket_required", "daemon_required",
            "one_shot_experiment_possible", "state_persistence_required",
            "manual_review_required_before_send", "real_send_allowed_now",
        ]
        for field in required_bool_fields:
            self.assertIn(field, entry, f"{card_type}: missing field '{field}'")
            self.assertTrue(isinstance(entry[field], bool),
                          f"{card_type}: '{field}' should be bool")

        required_int_fields = ["readiness_score"]
        for field in required_int_fields:
            self.assertIn(field, entry, f"{card_type}: missing field '{field}'")
            self.assertTrue(isinstance(entry[field], int),
                          f"{card_type}: '{field}' should be int")

        # Score should be in valid range (0-18)
        score = entry.get("readiness_score", -1)
        self.assertGreaterEqual(score, 0, f"{card_type}: readiness_score {score} < 0")
        self.assertLessEqual(score, 18, f"{card_type}: readiness_score {score} > 18")

        # Level should be one of low/medium/high
        level = entry.get("readiness_level", "")
        self.assertIn(level, ["low", "medium", "high"],
                     f"{card_type}: invalid readiness_level '{level}'")

        # Scoring breakdown should have 9 dimensions
        breakdown = entry.get("scoring_breakdown", {})
        self.assertEqual(len(breakdown), 9,
                       f"{card_type}: expected 9 scoring dimensions, got {len(breakdown)}")

    def test_032_price_oi_volume_anomaly_fields(self):
        """price_oi_volume_anomaly: all required fields present."""
        entry = next((e for e in self.matrix_entries
                     if e.get("card_type") == "price_oi_volume_anomaly"), None)
        self.assertIsNotNone(entry, "price_oi_volume_anomaly not found")
        self._check_matrix_entry_fields(entry, "price_oi_volume_anomaly")

    def test_033_whale_position_alert_fields(self):
        """whale_position_alert: all required fields present."""
        entry = next((e for e in self.matrix_entries
                     if e.get("card_type") == "whale_position_alert"), None)
        self.assertIsNotNone(entry, "whale_position_alert not found")
        self._check_matrix_entry_fields(entry, "whale_position_alert")

    def test_034_liquidation_pressure_fields(self):
        """liquidation_pressure: all required fields present."""
        entry = next((e for e in self.matrix_entries
                     if e.get("card_type") == "liquidation_pressure"), None)
        self.assertIsNotNone(entry, "liquidation_pressure not found")
        self._check_matrix_entry_fields(entry, "liquidation_pressure")

    def test_035_multi_asset_market_sync_fields(self):
        """multi_asset_market_sync: all required fields present."""
        entry = next((e for e in self.matrix_entries
                     if e.get("card_type") == "multi_asset_market_sync"), None)
        self.assertIsNotNone(entry, "multi_asset_market_sync not found")
        self._check_matrix_entry_fields(entry, "multi_asset_market_sync")

    def test_036_news_event_market_impact_fields(self):
        """news_event_market_impact: all required fields present."""
        entry = next((e for e in self.matrix_entries
                     if e.get("card_type") == "news_event_market_impact"), None)
        self.assertIsNotNone(entry, "news_event_market_impact not found")
        self._check_matrix_entry_fields(entry, "news_event_market_impact")

    def test_037_at_least_one_one_shot(self):
        """At least 1 card type should support one-shot experiment."""
        one_shot_count = sum(1 for e in self.matrix_entries
                           if e.get("one_shot_experiment_possible"))
        self.assertGreaterEqual(one_shot_count, 1,
                              f"Expected >=1 one-shot candidates, got {one_shot_count}")

    def test_038_no_real_send_allowed(self):
        """All card types should have real_send_allowed_now == False."""
        for entry in self.matrix_entries:
            ct = entry.get("card_type", "?")
            self.assertFalse(entry.get("real_send_allowed_now"),
                           f"{ct}: real_send_allowed_now should be False")

    def test_039_all_manual_review_required(self):
        """All card types should require manual review before send."""
        for entry in self.matrix_entries:
            ct = entry.get("card_type", "?")
            self.assertTrue(entry.get("manual_review_required_before_send"),
                          f"{ct}: manual_review_required_before_send should be True")

    def test_040_no_websocket_required(self):
        """No card type should require WebSocket at this stage."""
        for entry in self.matrix_entries:
            ct = entry.get("card_type", "?")
            self.assertFalse(entry.get("websocket_required"),
                           f"{ct}: websocket_required should be False")

    def test_041_no_daemon_required(self):
        """No card type should require daemon at this stage."""
        for entry in self.matrix_entries:
            ct = entry.get("card_type", "?")
            self.assertFalse(entry.get("daemon_required"),
                           f"{ct}: daemon_required should be False")

    def test_042_scores_are_deterministic(self):
        """Readiness scores should be calculated from scoring_breakdown."""
        for entry in self.matrix_entries:
            ct = entry.get("card_type", "?")
            breakdown = entry.get("scoring_breakdown", {})
            expected_score = sum(breakdown.values())
            actual_score = entry.get("readiness_score", -1)
            self.assertEqual(expected_score, actual_score,
                           f"{ct}: readiness_score {actual_score} != sum of breakdown {expected_score}")

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

    def test_051_no_secrets_in_matrix_json(self):
        """Matrix JSON must not contain secret patterns."""
        if self.matrix_json is None:
            self.skipTest("Matrix JSON not loaded")
        matrix_str = json.dumps(self.matrix_json, ensure_ascii=False)
        self._check_no_secret_patterns(matrix_str, "matrix JSON")

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

    def test_056_no_misleading_in_matrix(self):
        """Matrix entries must not contain misleading language."""
        for entry in self.matrix_entries:
            ct = entry.get("card_type", "?")
            text = json.dumps(entry, ensure_ascii=False)
            self._check_no_misleading(text, f"matrix entry '{ct}'")

    # ── Content assertions ─────────────────────────────────────────────────────

    def test_060_runner_output_mentions_v112n(self):
        """Runner stdout should mention v112N validation."""
        stdout = self.runner_stdout
        self.assertIn("v112N", stdout, "Runner output should mention v112N")

    def test_061_runner_output_mentions_v112o(self):
        """Runner stdout should mention v112O validation."""
        stdout = self.runner_stdout
        self.assertIn("v112O", stdout, "Runner output should mention v112O")

    def test_062_runner_output_mentions_recommended(self):
        """Runner stdout should mention recommended candidate."""
        stdout = self.runner_stdout
        self.assertIn("Recommended", stdout, "Runner output should mention recommended candidate")

    # ── Idempotency / re-run stability ─────────────────────────────────────────

    def test_070_rerun_produces_same_result(self):
        """Re-running should produce the same result JSON key values."""
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
            self.assertEqual(result2_json.get("card_types_total"), 5)
            self.assertEqual(result2_json.get("readiness_matrix_ready"), True)
            self.assertEqual(result2_json.get("dry_run_only"), True)
            self.assertEqual(result2_json.get("live_ready"), False)
            self.assertEqual(result2_json.get("real_tg_sent"), False)
            self.assertEqual(result2_json.get("external_api_called"), False)
            self.assertEqual(result2_json.get("external_ai_called"), False)
            self.assertEqual(result2_json.get("real_send_ready"), False)
            self.assertEqual(result2_json.get("production_state_write_ready"), False)
            self.assertEqual(result2_json.get("debug_leak_count"), 0)
            self.assertEqual(result2_json.get("secret_leak_count"), 0)

            # Recommended candidate should be the same
            self.assertEqual(
                self.result_json.get("recommended_first_one_shot_candidate"),
                result2_json.get("recommended_first_one_shot_candidate"),
                "Recommended candidate changed between runs"
            )

        # Matrix should have the same scores
        if MATRIX_JSON_PATH.exists():
            with open(MATRIX_JSON_PATH, "r", encoding="utf-8") as f:
                matrix2 = json.load(f)

            entries2 = matrix2.get("entries", [])
            scores1 = {e["card_type"]: e["readiness_score"] for e in self.matrix_entries}
            scores2 = {e["card_type"]: e["readiness_score"] for e in entries2}
            self.assertEqual(scores1, scores2,
                           f"Readiness scores changed between runs")


if __name__ == "__main__":
    unittest.main(verbosity=2)
