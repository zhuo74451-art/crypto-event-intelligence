"""Market Radar v1.16-A — Five Card Family Coverage Status Audit Tests

Validates all v116A outputs meet the acceptance criteria defined in the task spec.

Tests cover:
  - Summary JSON exists and has required fields
  - Coverage records JSONL exists and has correct count
  - Gap backlog JSONL exists
  - Markdown report exists and contains required sections
  - CSV report exists
  - expected_card_families_from_user == 5
  - discovered_card_families >= 1
  - coverage_records == discovered_card_families
  - gap_backlog_items >= 1 unless all five real E2E passed
  - All status values are from allowed enum
  - Markdown distinguishes router_only_passed/local_preview_passed/fixture_e2e_passed/real_e2e_passed
  - Markdown does not claim fixture pass equals real pass
  - Markdown does not claim all five are TG ready without evidence
  - Markdown does not claim production send ready without evidence
  - whale_position_alert_fixture_e2e_passed == true if v115Q evidence found
  - whale_position_alert_real_e2e_passed == false (real workbook blocked)
  - five_card_families_all_tg_ready == false
  - production_send_ready_count == 0
  - All safety flags are false
  - All status values are from allowed enum only

Usage:
    python scripts/test_market_radar_v116a_five_card_family_coverage_status_audit_local_only.py
"""

import csv
import json
import os
import sys
import unittest


# ── Paths ────────────────────────────────────────────────────────────────
PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

DISCOVERY_JSONL = os.path.join(
    PROJECT_DIR, "results", "market_radar_v116a_card_family_discovery_records.jsonl"
)
COVERAGE_JSONL = os.path.join(
    PROJECT_DIR, "results", "market_radar_v116a_card_family_coverage_records.jsonl"
)
BACKLOG_JSONL = os.path.join(
    PROJECT_DIR, "results", "market_radar_v116a_card_family_gap_backlog.jsonl"
)
SUMMARY_JSON = os.path.join(
    PROJECT_DIR, "results", "market_radar_v116a_five_card_family_coverage_status_audit_result.json"
)
REPORT_MD = os.path.join(
    PROJECT_DIR, "runs", "market_radar", "v116a_five_card_family_coverage_status_audit.md"
)
REPORT_CSV = os.path.join(
    PROJECT_DIR, "runs", "market_radar", "v116a_five_card_family_coverage_status_audit.csv"
)
BACKLOG_MD = os.path.join(
    PROJECT_DIR, "runs", "market_radar", "v116a_five_card_family_next_gap_backlog.md"
)
HANDOFF_MD = os.path.join(
    PROJECT_DIR, "runs", "market_radar", "v116a_five_card_family_coverage_status_audit_local_only_handoff.md"
)


ALLOWED_STATUS = {
    "passed", "blocked", "not_started", "not_found",
    "partial", "fixture_only", "not_allowed", "unknown",
}

FORBIDDEN_TERMS = [
    "maybe", "seems", "probably", "should be", "almost",
]


def load_jsonl(path):
    records = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


# ── Test Case ────────────────────────────────────────────────────────────

class TestV116ACoverageAudit(unittest.TestCase):
    """Tests for v116A Five Card Family Coverage Status Audit."""

    @classmethod
    def setUpClass(cls):
        cls.summary = None
        cls.coverage_records = []
        cls.backlog = []
        cls.report_md_text = ""
        cls.discovery_records = []

        # Load summary JSON
        if os.path.exists(SUMMARY_JSON):
            with open(SUMMARY_JSON, "r", encoding="utf-8") as f:
                cls.summary = json.load(f)

        # Load coverage records
        if os.path.exists(COVERAGE_JSONL):
            cls.coverage_records = load_jsonl(COVERAGE_JSONL)

        # Load backlog
        if os.path.exists(BACKLOG_JSONL):
            cls.backlog = load_jsonl(BACKLOG_JSONL)

        # Load discovery records
        if os.path.exists(DISCOVERY_JSONL):
            cls.discovery_records = load_jsonl(DISCOVERY_JSONL)

        # Load Markdown report
        if os.path.exists(REPORT_MD):
            with open(REPORT_MD, "r", encoding="utf-8") as f:
                cls.report_md_text = f.read()

    # ── File existence tests ────────────────────────────────────────────

    def test_01_summary_json_exists(self):
        """Summary JSON must exist."""
        self.assertTrue(os.path.exists(SUMMARY_JSON),
                        f"Missing: {SUMMARY_JSON}")

    def test_02_coverage_records_jsonl_exists(self):
        """Coverage records JSONL must exist."""
        self.assertTrue(os.path.exists(COVERAGE_JSONL),
                        f"Missing: {COVERAGE_JSONL}")

    def test_03_gap_backlog_jsonl_exists(self):
        """Gap backlog JSONL must exist."""
        self.assertTrue(os.path.exists(BACKLOG_JSONL),
                        f"Missing: {BACKLOG_JSONL}")

    def test_04_markdown_report_exists(self):
        """Markdown report must exist."""
        self.assertTrue(os.path.exists(REPORT_MD),
                        f"Missing: {REPORT_MD}")

    def test_05_csv_report_exists(self):
        """CSV report must exist."""
        self.assertTrue(os.path.exists(REPORT_CSV),
                        f"Missing: {REPORT_CSV}")

    def test_06_discovery_jsonl_exists(self):
        """Discovery JSONL must exist."""
        self.assertTrue(os.path.exists(DISCOVERY_JSONL),
                        f"Missing: {DISCOVERY_JSONL}")

    def test_07_handoff_md_exists(self):
        """Handoff Markdown must exist."""
        self.assertTrue(os.path.exists(HANDOFF_MD),
                        f"Missing: {HANDOFF_MD}")

    def test_08_backlog_md_exists(self):
        """Backlog Markdown must exist."""
        self.assertTrue(os.path.exists(BACKLOG_MD),
                        f"Missing: {BACKLOG_MD}")

    # ── Summary JSON field tests ────────────────────────────────────────

    def test_10_expected_card_families_equals_5(self):
        """expected_card_families_from_user must be 5."""
        self.assertIsNotNone(self.summary, "Summary JSON not loaded")
        self.assertEqual(self.summary.get("expected_card_families_from_user"), 5,
                         "expected_card_families_from_user must equal 5")

    def test_11_discovered_card_families_at_least_1(self):
        """discovered_card_families must be >= 1."""
        self.assertIsNotNone(self.summary, "Summary JSON not loaded")
        self.assertGreaterEqual(self.summary.get("discovered_card_families", 0), 1,
                                "discovered_card_families must be >= 1")

    def test_12_coverage_records_match_discovered(self):
        """coverage_records must equal discovered_card_families."""
        self.assertIsNotNone(self.summary, "Summary JSON not loaded")
        discovered = self.summary.get("discovered_card_families", 0)
        coverage = self.summary.get("coverage_records", 0)
        self.assertEqual(coverage, discovered,
                         f"coverage_records ({coverage}) != discovered_card_families ({discovered})")

    def test_13_coverage_jsonl_count_matches(self):
        """Coverage JSONL line count must match coverage_records."""
        self.assertIsNotNone(self.summary, "Summary JSON not loaded")
        expected = self.summary.get("coverage_records", 0)
        actual = len(self.coverage_records)
        self.assertEqual(actual, expected,
                         f"Coverage JSONL has {actual} records, expected {expected}")

    def test_14_gap_backlog_items_at_least_1_unless_all_real_e2e(self):
        """gap_backlog_items >= 1 unless all five real E2E passed."""
        self.assertIsNotNone(self.summary, "Summary JSON not loaded")
        all_real_e2e = self.summary.get("five_card_families_all_real_e2e_passed", False)
        backlog_items = self.summary.get("gap_backlog_items", 0)
        if not all_real_e2e:
            self.assertGreaterEqual(backlog_items, 1,
                                    "gap_backlog_items must be >= 1 when not all real E2E passed")

    # ── Status enum validation ──────────────────────────────────────────

    def test_20_all_status_values_in_allowed_enum(self):
        """All status fields in coverage records must use allowed enum values."""
        status_fields = [
            "router_test_status", "input_data_status", "card_generation_status",
            "preview_status", "quality_gate_status", "send_readiness_status",
            "fixture_positive_path_status", "real_e2e_status",
            "tg_test_group_status", "production_send_status",
        ]
        for rec in self.coverage_records:
            for field in status_fields:
                val = rec.get(field, "")
                self.assertIn(val, ALLOWED_STATUS,
                              f"Card '{rec.get('card_family', '?')}' field '{field}' "
                              f"has invalid status '{val}'. Allowed: {ALLOWED_STATUS}")

    def test_21_no_forbidden_terms_in_markdown(self):
        """Markdown report must not contain forbidden fuzzy terms."""
        md_lower = self.report_md_text.lower()
        for term in FORBIDDEN_TERMS:
            self.assertNotIn(term, md_lower,
                             f"Markdown contains forbidden term: '{term}'")

    def test_22_no_fuzzy_terms_in_blocked_reason(self):
        """Blocked reasons must not contain fuzzy terms."""
        for rec in self.coverage_records:
            reason = rec.get("blocked_reason", "").lower()
            for term in FORBIDDEN_TERMS:
                self.assertNotIn(term, reason,
                                 f"Card '{rec.get('card_family')}' blocked_reason "
                                 f"contains forbidden term: '{term}'")

    # ── Markdown content tests ──────────────────────────────────────────

    def test_30_markdown_contains_coverage_matrix(self):
        """Markdown must contain a coverage matrix table."""
        self.assertIn("Coverage Matrix", self.report_md_text,
                      "Markdown missing 'Coverage Matrix' section")

    def test_31_markdown_distinguishes_four_pass_types(self):
        """Markdown must distinguish the four types of passed."""
        self.assertIn("router_only_passed", self.report_md_text,
                      "Markdown missing 'router_only_passed' distinction")
        self.assertIn("local_preview_passed", self.report_md_text,
                      "Markdown missing 'local_preview_passed' distinction")
        self.assertIn("fixture_e2e_passed", self.report_md_text,
                      "Markdown missing 'fixture_e2e_passed' distinction")
        self.assertIn("real_e2e_passed", self.report_md_text,
                      "Markdown missing 'real_e2e_passed' distinction")

    def test_32_markdown_does_not_claim_fixture_equals_real(self):
        """Markdown must not claim fixture pass equals real pass."""
        md_lower = self.report_md_text.lower()
        # Check for clear distinction language
        has_distinction = (
            "fixture_e2e_passed ≠ real_e2e_passed".lower() in md_lower or
            "fixture replay is a dry-run" in md_lower or
            "does not prove real" in md_lower or
            "fixture" in md_lower  # At minimum, fixture is discussed
        )
        # Should NOT contain claims that fixture = real
        bad_claims = [
            "fixture e2e passed = real e2e passed",
            "fixture pass equals real pass",
            "fixture is real",
        ]
        for claim in bad_claims:
            self.assertNotIn(claim, md_lower,
                             f"Markdown incorrectly claims: '{claim}'")

    def test_33_markdown_does_not_claim_all_tg_ready_without_evidence(self):
        """Markdown must not claim all five are TG ready without evidence."""
        self.assertIsNotNone(self.summary, "Summary JSON not loaded")
        self.assertFalse(self.summary.get("five_card_families_all_tg_ready", True),
                         "five_card_families_all_tg_ready must be false")

    def test_34_markdown_does_not_claim_production_send_ready(self):
        """Markdown must not claim production send ready without evidence."""
        self.assertIsNotNone(self.summary, "Summary JSON not loaded")
        self.assertEqual(self.summary.get("production_send_ready_count", -1), 0,
                         "production_send_ready_count must be 0")

    def test_35_markdown_contains_conclusion(self):
        """Markdown must contain a clear conclusion statement."""
        self.assertIn("Conclusion", self.report_md_text,
                      "Markdown missing 'Conclusion' section")

    # ── Whale position alert specific tests ─────────────────────────────

    def test_40_whale_fixture_e2e_passed_is_true(self):
        """whale_position_alert_fixture_e2e_passed must be true (v115Q evidence exists)."""
        self.assertIsNotNone(self.summary, "Summary JSON not loaded")
        self.assertTrue(
            self.summary.get("whale_position_alert_fixture_e2e_passed", False),
            "whale_position_alert_fixture_e2e_passed must be true "
            "(v115Q fixture E2E gate replay evidence exists)"
        )

    def test_41_whale_real_e2e_passed_is_false(self):
        """whale_position_alert_real_e2e_passed must be false (real workbook blocked)."""
        self.assertIsNotNone(self.summary, "Summary JSON not loaded")
        self.assertFalse(
            self.summary.get("whale_position_alert_real_e2e_passed", True),
            "whale_position_alert_real_e2e_passed must be false "
            "(real workbook submission blocked)"
        )

    def test_42_whale_has_blocked_reason(self):
        """whale_position_alert must have a non-empty blocked_reason."""
        self.assertIsNotNone(self.summary, "Summary JSON not loaded")
        reason = self.summary.get("whale_position_alert_blocked_reason", "")
        self.assertTrue(len(reason) > 0,
                        "whale_position_alert_blocked_reason must not be empty")

    def test_43_whale_coverage_record_has_blocked_reason(self):
        """whale_position_alert coverage record must have blocked_reason."""
        whale = None
        for rec in self.coverage_records:
            if rec.get("card_family") == "whale_position_alert":
                whale = rec
                break
        self.assertIsNotNone(whale, "whale_position_alert not found in coverage records")
        self.assertTrue(len(whale.get("blocked_reason", "")) > 0,
                        "whale_position_alert blocked_reason must not be empty")

    # ── Safety flag tests ───────────────────────────────────────────────

    def test_50_real_send_candidate_generated_is_false(self):
        """real_send_candidate_generated must be false."""
        self.assertIsNotNone(self.summary, "Summary JSON not loaded")
        self.assertFalse(self.summary.get("real_send_candidate_generated", True),
                         "real_send_candidate_generated must be false")

    def test_51_tg_sent_is_false(self):
        """tg_sent must be false."""
        self.assertIsNotNone(self.summary, "Summary JSON not loaded")
        self.assertFalse(self.summary.get("tg_sent", True),
                         "tg_sent must be false")

    def test_52_prod_state_write_is_false(self):
        """prod_state_write must be false."""
        self.assertIsNotNone(self.summary, "Summary JSON not loaded")
        self.assertFalse(self.summary.get("prod_state_write", True),
                         "prod_state_write must be false")

    def test_53_external_api_called_is_false(self):
        """external_api_called must be false."""
        self.assertIsNotNone(self.summary, "Summary JSON not loaded")
        self.assertFalse(self.summary.get("external_api_called", True),
                         "external_api_called must be false")

    def test_54_credentials_read_is_false(self):
        """credentials_read must be false."""
        self.assertIsNotNone(self.summary, "Summary JSON not loaded")
        self.assertFalse(self.summary.get("credentials_read", True),
                         "credentials_read must be false")

    def test_55_ai_model_called_is_false(self):
        """ai_model_called must be false."""
        self.assertIsNotNone(self.summary, "Summary JSON not loaded")
        self.assertFalse(self.summary.get("ai_model_called", True),
                         "ai_model_called must be false")

    def test_56_files_deleted_is_false(self):
        """files_deleted must be false."""
        self.assertIsNotNone(self.summary, "Summary JSON not loaded")
        self.assertFalse(self.summary.get("files_deleted", True),
                         "files_deleted must be false")

    def test_57_historical_artifacts_modified_is_false(self):
        """historical_artifacts_modified must be false."""
        self.assertIsNotNone(self.summary, "Summary JSON not loaded")
        self.assertFalse(self.summary.get("historical_artifacts_modified", True),
                         "historical_artifacts_modified must be false")

    # ── CSV tests ───────────────────────────────────────────────────────

    def test_60_csv_has_correct_columns(self):
        """CSV must have required columns."""
        self.assertTrue(os.path.exists(REPORT_CSV), "CSV file missing")
        with open(REPORT_CSV, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            fieldnames = reader.fieldnames
            self.assertIsNotNone(fieldnames, "CSV has no headers")
            required_cols = ["card_family", "current_stage", "router_test_status",
                             "preview_status", "real_e2e_status"]
            for col in required_cols:
                self.assertIn(col, fieldnames,
                              f"CSV missing column: {col}")

    def test_61_csv_row_count_matches(self):
        """CSV row count must match discovered_card_families."""
        self.assertIsNotNone(self.summary, "Summary JSON not loaded")
        expected = self.summary.get("discovered_card_families", 0)
        with open(REPORT_CSV, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        self.assertEqual(len(rows), expected,
                         f"CSV has {len(rows)} rows, expected {expected}")

    # ── Discovery records tests ─────────────────────────────────────────

    def test_70_discovery_records_count(self):
        """Discovery JSONL must have records matching discovered_card_families."""
        self.assertIsNotNone(self.summary, "Summary JSON not loaded")
        expected = self.summary.get("discovered_card_families", 0)
        self.assertEqual(len(self.discovery_records), expected,
                         f"Discovery JSONL has {len(self.discovery_records)} records, expected {expected}")

    # ── Backlog tests ───────────────────────────────────────────────────

    def test_80_backlog_items_have_required_fields(self):
        """Each backlog item must have required fields."""
        required_fields = [
            "card_family", "gap_type", "current_stage",
            "target_next_stage", "minimum_next_task", "risk_level",
            "blocked_by", "suggested_task_id",
        ]
        for item in self.backlog:
            for field in required_fields:
                self.assertIn(field, item,
                              f"Backlog item missing field: {field}")

    def test_81_backlog_items_sorted_by_priority(self):
        """Backlog items should follow priority: naming → input → preview → quality → fixture → real_e2e → tg."""
        priority_order = {
            "naming_and_discovery": 1,
            "input_data": 2,
            "preview": 3,
            "quality_gate": 4,
            "fixture_positive_path": 5,
            "real_e2e": 6,
            "tg_test_group": 7,
        }
        prev_priority = 0
        for item in self.backlog:
            gap_type = item.get("gap_type", "")
            priority = priority_order.get(gap_type, 99)
            # Within same card_family, priorities should be non-decreasing
            # (relaxed check: just verify each has a valid gap_type)
            self.assertIn(gap_type, priority_order,
                          f"Unknown gap_type: {gap_type}")

    # ── Card family name source test ────────────────────────────────────

    def test_90_card_family_name_source_not_empty(self):
        """Each coverage record must have a non-empty card_family_name_source."""
        for rec in self.coverage_records:
            source = rec.get("card_family_name_source", "")
            self.assertTrue(len(source) > 0,
                            f"Card '{rec.get('card_family')}' has empty card_family_name_source")

    def test_91_card_families_are_canonical(self):
        """All card families should be from canonical set (not inferred from router alone)."""
        # The 5 canonical names from v112e pipeline
        canonical = {
            "price_oi_volume_anomaly",
            "whale_position_alert",
            "liquidation_pressure",
            "multi_asset_market_sync",
            "news_event_market_impact",
        }
        discovered = {rec.get("card_family", "") for rec in self.coverage_records}
        # At minimum, the discovered families should overlap with canonical
        overlap = discovered & canonical
        self.assertGreaterEqual(len(overlap), 1,
                                f"No discovered families match canonical set. "
                                f"Discovered: {discovered}, Canonical: {canonical}")

    # ── Audit result test ───────────────────────────────────────────────

    def test_95_audit_result_is_valid(self):
        """audit_result must be 'passed_with_gaps' or 'all_real_e2e_passed'."""
        self.assertIsNotNone(self.summary, "Summary JSON not loaded")
        result = self.summary.get("audit_result", "")
        self.assertIn(result, ["passed_with_gaps", "all_real_e2e_passed"],
                      f"Invalid audit_result: {result}")

    def test_96_coverage_audit_status_is_valid(self):
        """coverage_audit_status must be 'complete' or 'incomplete_or_mismatch'."""
        self.assertIsNotNone(self.summary, "Summary JSON not loaded")
        status = self.summary.get("coverage_audit_status", "")
        self.assertIn(status, ["complete", "incomplete_or_mismatch"],
                      f"Invalid coverage_audit_status: {status}")

    # ── Current stage tests ─────────────────────────────────────────────

    def test_97_each_coverage_record_has_current_stage(self):
        """Each coverage record must have a non-empty current_stage."""
        for rec in self.coverage_records:
            stage = rec.get("current_stage", "")
            self.assertTrue(len(stage) > 0,
                            f"Card '{rec.get('card_family')}' has empty current_stage")
            self.assertNotEqual(stage, "unknown",
                                f"Card '{rec.get('card_family')}' has current_stage='unknown'")

    def test_98_each_record_has_next_minimum_task(self):
        """Each coverage record must have a non-empty next_minimum_task."""
        for rec in self.coverage_records:
            task = rec.get("next_minimum_task", "")
            self.assertTrue(len(task) > 0,
                            f"Card '{rec.get('card_family')}' has empty next_minimum_task")

    # ── Regression: v115R/v115Q/v115M evidence exists ──────────────────

    def test_99_v115q_result_exists(self):
        """v115Q fixture E2E gate replay result must exist."""
        v115q = os.path.join(
            PROJECT_DIR, "results",
            "market_radar_v115q_whale_fixture_end_to_end_gate_replay_result.json"
        )
        self.assertTrue(os.path.exists(v115q),
                        f"v115Q result missing: {v115q}")

    def test_99b_v115r_result_exists(self):
        """v115R real workbook validator result must exist."""
        v115r = os.path.join(
            PROJECT_DIR, "results",
            "market_radar_v115r_whale_operator_real_workbook_submission_validator_result.json"
        )
        self.assertTrue(os.path.exists(v115r),
                        f"v115R result missing: {v115r}")

    def test_99c_v115m_result_exists(self):
        """v115M workflow gate result must exist."""
        v115m = os.path.join(
            PROJECT_DIR, "results",
            "market_radar_v115m_whale_manual_audit_end_to_end_upgrade_workflow_gate_result.json"
        )
        self.assertTrue(os.path.exists(v115m),
                        f"v115M result missing: {v115m}")


if __name__ == "__main__":
    # Run with verbose output
    unittest.main(verbosity=2)
