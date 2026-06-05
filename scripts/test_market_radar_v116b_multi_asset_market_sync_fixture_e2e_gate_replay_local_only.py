"""Market Radar v1.16-B — Multi-Asset Market Sync Fixture E2E Gate Replay Tests

Validates all v116B outputs meet the acceptance criteria defined in the task spec.

Tests cover:
  - Summary JSON exists and has required fields
  - All JSONL outputs exist
  - Markdown report exists
  - CSV report exists
  - card_family == multi_asset_market_sync
  - router_passed == true
  - local_preview_passed == true
  - fixture_input_records >= 1
  - fixture_quality_gate_records == fixture_input_records
  - fixture_send_readiness_records == fixture_input_records
  - fixture_workflow_replay_decisions == fixture_input_records
  - fixture_quality_gate_passed_count >= 1
  - fixture_send_readiness_passed_count >= 1
  - fixture_workflow_ready_count >= 1
  - fixture_e2e_passed == true
  - real_e2e_passed == false
  - tg_test_group_ready == false
  - production_send_ready == false
  - send_candidate_generated == false
  - real_send_candidate_generated == false
  - Markdown contains fixture E2E passed
  - Markdown does not claim real E2E passed
  - Markdown does not claim TG ready
  - Markdown does not claim production send ready
  - Markdown distinguishes fixture_e2e_passed and real_e2e_passed
  - All safety flags are false

Usage:
    python scripts/test_market_radar_v116b_multi_asset_market_sync_fixture_e2e_gate_replay_local_only.py
"""

import json
import os
import sys
import unittest


# ── Paths ────────────────────────────────────────────────────────────────
PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

SUMMARY_JSON = os.path.join(
    PROJECT_DIR, "results", "market_radar_v116b_multi_asset_fixture_e2e_gate_replay_result.json"
)
FIXTURE_INPUT_JSONL = os.path.join(
    PROJECT_DIR, "results", "market_radar_v116b_multi_asset_fixture_input_records.jsonl"
)
QUALITY_GATE_JSONL = os.path.join(
    PROJECT_DIR, "results", "market_radar_v116b_multi_asset_fixture_quality_gate_records.jsonl"
)
SEND_READINESS_JSONL = os.path.join(
    PROJECT_DIR, "results", "market_radar_v116b_multi_asset_fixture_send_readiness_records.jsonl"
)
WORKFLOW_REPLAY_JSONL = os.path.join(
    PROJECT_DIR, "results", "market_radar_v116b_multi_asset_fixture_workflow_replay_decisions.jsonl"
)
REPORT_MD = os.path.join(
    PROJECT_DIR, "runs", "market_radar", "v116b_multi_asset_market_sync_fixture_e2e_gate_replay.md"
)
REPORT_CSV = os.path.join(
    PROJECT_DIR, "runs", "market_radar", "v116b_multi_asset_market_sync_fixture_e2e_gate_replay.csv"
)
HANDOFF_MD = os.path.join(
    PROJECT_DIR, "runs", "market_radar", "v116b_multi_asset_market_sync_fixture_e2e_gate_replay_local_only_handoff.md"
)


def load_jsonl(path):
    records = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


# ── Test Case ────────────────────────────────────────────────────────────

class TestV116BFixtureE2EGateReplay(unittest.TestCase):
    """Tests for v116B Multi-Asset Market Sync Fixture E2E Gate Replay."""

    @classmethod
    def setUpClass(cls):
        cls.summary = None
        cls.fixture_inputs = []
        cls.quality_gates = []
        cls.send_readiness = []
        cls.workflow_replays = []
        cls.report_md_text = ""

        # Load summary JSON
        if os.path.exists(SUMMARY_JSON):
            with open(SUMMARY_JSON, "r", encoding="utf-8") as f:
                cls.summary = json.load(f)

        # Load JSONL files
        if os.path.exists(FIXTURE_INPUT_JSONL):
            cls.fixture_inputs = load_jsonl(FIXTURE_INPUT_JSONL)
        if os.path.exists(QUALITY_GATE_JSONL):
            cls.quality_gates = load_jsonl(QUALITY_GATE_JSONL)
        if os.path.exists(SEND_READINESS_JSONL):
            cls.send_readiness = load_jsonl(SEND_READINESS_JSONL)
        if os.path.exists(WORKFLOW_REPLAY_JSONL):
            cls.workflow_replays = load_jsonl(WORKFLOW_REPLAY_JSONL)

        # Load Markdown report
        if os.path.exists(REPORT_MD):
            with open(REPORT_MD, "r", encoding="utf-8") as f:
                cls.report_md_text = f.read()

    # ── File existence tests ────────────────────────────────────────────

    def test_01_summary_json_exists(self):
        """Summary JSON must exist."""
        self.assertTrue(os.path.exists(SUMMARY_JSON),
                        f"Missing: {SUMMARY_JSON}")

    def test_02_fixture_input_jsonl_exists(self):
        """Fixture input records JSONL must exist."""
        self.assertTrue(os.path.exists(FIXTURE_INPUT_JSONL),
                        f"Missing: {FIXTURE_INPUT_JSONL}")

    def test_03_quality_gate_jsonl_exists(self):
        """Quality gate records JSONL must exist."""
        self.assertTrue(os.path.exists(QUALITY_GATE_JSONL),
                        f"Missing: {QUALITY_GATE_JSONL}")

    def test_04_send_readiness_jsonl_exists(self):
        """Send readiness records JSONL must exist."""
        self.assertTrue(os.path.exists(SEND_READINESS_JSONL),
                        f"Missing: {SEND_READINESS_JSONL}")

    def test_05_workflow_replay_jsonl_exists(self):
        """Workflow replay decisions JSONL must exist."""
        self.assertTrue(os.path.exists(WORKFLOW_REPLAY_JSONL),
                        f"Missing: {WORKFLOW_REPLAY_JSONL}")

    def test_06_markdown_report_exists(self):
        """Markdown report must exist."""
        self.assertTrue(os.path.exists(REPORT_MD),
                        f"Missing: {REPORT_MD}")

    def test_07_csv_report_exists(self):
        """CSV report must exist."""
        self.assertTrue(os.path.exists(REPORT_CSV),
                        f"Missing: {REPORT_CSV}")

    def test_08_handoff_md_exists(self):
        """Handoff Markdown must exist."""
        self.assertTrue(os.path.exists(HANDOFF_MD),
                        f"Missing: {HANDOFF_MD}")

    # ── Summary JSON field tests ────────────────────────────────────────

    def test_10_card_family_is_multi_asset_market_sync(self):
        """card_family must be multi_asset_market_sync."""
        self.assertIsNotNone(self.summary, "Summary JSON not loaded")
        self.assertEqual(self.summary.get("card_family"), "multi_asset_market_sync",
                         "card_family must be 'multi_asset_market_sync'")

    def test_11_router_passed_is_true(self):
        """router_passed must be true."""
        self.assertIsNotNone(self.summary, "Summary JSON not loaded")
        self.assertTrue(self.summary.get("router_passed", False),
                        "router_passed must be true")

    def test_12_local_preview_passed_is_true(self):
        """local_preview_passed must be true."""
        self.assertIsNotNone(self.summary, "Summary JSON not loaded")
        self.assertTrue(self.summary.get("local_preview_passed", False),
                        "local_preview_passed must be true")

    def test_13_fixture_input_records_at_least_1(self):
        """fixture_input_records must be >= 1."""
        self.assertIsNotNone(self.summary, "Summary JSON not loaded")
        self.assertGreaterEqual(self.summary.get("fixture_input_records", 0), 1,
                                "fixture_input_records must be >= 1")

    # ── Record count consistency tests ──────────────────────────────────

    def test_14_fixture_input_jsonl_count_matches(self):
        """Fixture input JSONL count must match summary."""
        self.assertIsNotNone(self.summary, "Summary JSON not loaded")
        expected = self.summary.get("fixture_input_records", 0)
        actual = len(self.fixture_inputs)
        self.assertEqual(actual, expected,
                         f"Fixture input JSONL has {actual} records, expected {expected}")

    def test_15_quality_gate_count_matches_input(self):
        """Quality gate records count must equal fixture input records count."""
        self.assertEqual(len(self.quality_gates), len(self.fixture_inputs),
                         f"Quality gate ({len(self.quality_gates)}) != fixture inputs ({len(self.fixture_inputs)})")

    def test_16_send_readiness_count_matches_input(self):
        """Send readiness records count must equal fixture input records count."""
        self.assertEqual(len(self.send_readiness), len(self.fixture_inputs),
                         f"Send readiness ({len(self.send_readiness)}) != fixture inputs ({len(self.fixture_inputs)})")

    def test_17_workflow_replay_count_matches_input(self):
        """Workflow replay decisions count must equal fixture input records count."""
        self.assertEqual(len(self.workflow_replays), len(self.fixture_inputs),
                         f"Workflow replay ({len(self.workflow_replays)}) != fixture inputs ({len(self.fixture_inputs)})")

    def test_18_summary_counts_match(self):
        """Summary JSONL counts must match actual counts."""
        self.assertIsNotNone(self.summary, "Summary JSON not loaded")
        self.assertEqual(self.summary.get("fixture_quality_gate_records", 0), len(self.quality_gates))
        self.assertEqual(self.summary.get("fixture_send_readiness_records", 0), len(self.send_readiness))
        self.assertEqual(self.summary.get("fixture_workflow_replay_decisions", 0), len(self.workflow_replays))

    # ── Quality gate count tests ────────────────────────────────────────

    def test_20_quality_gate_passed_at_least_1(self):
        """fixture_quality_gate_passed_count must be >= 1."""
        self.assertIsNotNone(self.summary, "Summary JSON not loaded")
        self.assertGreaterEqual(self.summary.get("fixture_quality_gate_passed_count", 0), 1,
                                "fixture_quality_gate_passed_count must be >= 1")

    def test_21_send_readiness_passed_at_least_1(self):
        """fixture_send_readiness_passed_count must be >= 1."""
        self.assertIsNotNone(self.summary, "Summary JSON not loaded")
        self.assertGreaterEqual(self.summary.get("fixture_send_readiness_passed_count", 0), 1,
                                "fixture_send_readiness_passed_count must be >= 1")

    def test_22_workflow_ready_at_least_1(self):
        """fixture_workflow_ready_count must be >= 1."""
        self.assertIsNotNone(self.summary, "Summary JSON not loaded")
        self.assertGreaterEqual(self.summary.get("fixture_workflow_ready_count", 0), 1,
                                "fixture_workflow_ready_count must be >= 1")

    # ── E2E pass/fail state tests ───────────────────────────────────────

    def test_23_fixture_e2e_passed_is_true(self):
        """fixture_e2e_passed must be true."""
        self.assertIsNotNone(self.summary, "Summary JSON not loaded")
        self.assertTrue(self.summary.get("fixture_e2e_passed", False),
                        "fixture_e2e_passed must be true")

    def test_24_real_e2e_passed_is_false(self):
        """real_e2e_passed must be false."""
        self.assertIsNotNone(self.summary, "Summary JSON not loaded")
        self.assertFalse(self.summary.get("real_e2e_passed", True),
                         "real_e2e_passed must be false")

    # ── Send state tests (all must be false) ────────────────────────────

    def test_25_tg_test_group_ready_is_false(self):
        """tg_test_group_ready must be false."""
        self.assertIsNotNone(self.summary, "Summary JSON not loaded")
        self.assertFalse(self.summary.get("tg_test_group_ready", True),
                         "tg_test_group_ready must be false")

    def test_26_production_send_ready_is_false(self):
        """production_send_ready must be false."""
        self.assertIsNotNone(self.summary, "Summary JSON not loaded")
        self.assertFalse(self.summary.get("production_send_ready", True),
                         "production_send_ready must be false")

    def test_27_send_candidate_generated_is_false(self):
        """send_candidate_generated must be false."""
        self.assertIsNotNone(self.summary, "Summary JSON not loaded")
        self.assertFalse(self.summary.get("send_candidate_generated", True),
                         "send_candidate_generated must be false")

    def test_28_real_send_candidate_generated_is_false(self):
        """real_send_candidate_generated must be false."""
        self.assertIsNotNone(self.summary, "Summary JSON not loaded")
        self.assertFalse(self.summary.get("real_send_candidate_generated", True),
                         "real_send_candidate_generated must be false")

    # ── Safety flag tests ───────────────────────────────────────────────

    def test_30_tg_sent_is_false(self):
        """tg_sent must be false."""
        self.assertIsNotNone(self.summary, "Summary JSON not loaded")
        self.assertFalse(self.summary.get("tg_sent", True),
                         "tg_sent must be false")

    def test_31_prod_state_write_is_false(self):
        """prod_state_write must be false."""
        self.assertIsNotNone(self.summary, "Summary JSON not loaded")
        self.assertFalse(self.summary.get("prod_state_write", True),
                         "prod_state_write must be false")

    def test_32_external_api_called_is_false(self):
        """external_api_called must be false."""
        self.assertIsNotNone(self.summary, "Summary JSON not loaded")
        self.assertFalse(self.summary.get("external_api_called", True),
                         "external_api_called must be false")

    def test_33_credentials_read_is_false(self):
        """credentials_read must be false."""
        self.assertIsNotNone(self.summary, "Summary JSON not loaded")
        self.assertFalse(self.summary.get("credentials_read", True),
                         "credentials_read must be false")

    def test_34_ai_model_called_is_false(self):
        """ai_model_called must be false."""
        self.assertIsNotNone(self.summary, "Summary JSON not loaded")
        self.assertFalse(self.summary.get("ai_model_called", True),
                         "ai_model_called must be false")

    def test_35_files_deleted_is_false(self):
        """files_deleted must be false."""
        self.assertIsNotNone(self.summary, "Summary JSON not loaded")
        self.assertFalse(self.summary.get("files_deleted", True),
                         "files_deleted must be false")

    def test_36_historical_artifacts_modified_is_false(self):
        """historical_artifacts_modified must be false."""
        self.assertIsNotNone(self.summary, "Summary JSON not loaded")
        self.assertFalse(self.summary.get("historical_artifacts_modified", True),
                         "historical_artifacts_modified must be false")

    # ── Audit result test ───────────────────────────────────────────────

    def test_37_audit_result_is_fixture_e2e_passed(self):
        """audit_result must be 'fixture_e2e_passed_real_e2e_not_started'."""
        self.assertIsNotNone(self.summary, "Summary JSON not loaded")
        self.assertEqual(self.summary.get("audit_result"), "fixture_e2e_passed_real_e2e_not_started",
                         "audit_result must be 'fixture_e2e_passed_real_e2e_not_started'")

    # ── Markdown content tests ──────────────────────────────────────────

    def test_40_markdown_contains_fixture_e2e_passed(self):
        """Markdown must mention fixture E2E passed."""
        self.assertIn("fixture", self.report_md_text.lower(),
                      "Markdown must reference fixture E2E")
        has_passed_ref = (
            "fixture e2e gate replay" in self.report_md_text.lower() or
            "fixture e2e passed" in self.report_md_text.lower() or
            "✅ passed" in self.report_md_text.lower() or
            "✅ yes" in self.report_md_text.lower()
        )
        self.assertTrue(has_passed_ref,
                        "Markdown must indicate fixture E2E passed")

    def test_41_markdown_does_not_claim_real_e2e_passed(self):
        """Markdown must not claim real E2E is passed."""
        md_lower = self.report_md_text.lower()
        # Should NOT contain claims that real E2E has passed
        bad_claims = [
            "real e2e passed: ✅",
            "real e2e passed = true",
        ]
        for claim in bad_claims:
            self.assertNotIn(claim, md_lower,
                            f"Markdown incorrectly claims: '{claim}'")

    def test_42_markdown_does_not_claim_tg_ready(self):
        """Markdown must not claim TG test group is ready."""
        md_lower = self.report_md_text.lower()
        bad_claims = [
            "tg test group ready",
            "tg test group: ✅",
            "tg ready: yes",
        ]
        for claim in bad_claims:
            self.assertNotIn(claim, md_lower,
                            f"Markdown incorrectly claims TG ready: '{claim}'")

    def test_43_markdown_does_not_claim_production_send_ready(self):
        """Markdown must not claim production send is ready."""
        md_lower = self.report_md_text.lower()
        bad_claims = [
            "production send ready: ✅",
            "production send: ✅",
            "production_send_ready: true",
        ]
        for claim in bad_claims:
            self.assertNotIn(claim, md_lower,
                            f"Markdown incorrectly claims production send ready: '{claim}'")

    def test_44_markdown_distinguishes_fixture_and_real_e2e(self):
        """Markdown must distinguish fixture_e2e_passed from real_e2e_passed."""
        md_lower = self.report_md_text.lower()
        has_distinction = (
            "fixture" in md_lower and "real" in md_lower and
            ("≠" in md_lower or "not" in md_lower or "does not" in md_lower)
        )
        self.assertTrue(has_distinction,
                        "Markdown must distinguish fixture E2E from real E2E")

    # ── Fixture input record quality tests ──────────────────────────────

    def test_50_fixture_inputs_have_required_fields(self):
        """Each fixture input record must have all required fields."""
        required_fields = [
            "card_family", "fixture_record_id", "source_evidence_file",
            "assets_involved", "market_sync_signal_type", "signal_summary",
            "supporting_metrics", "preview_payload_hash", "fixture_only",
            "not_real_send_candidate_warning",
        ]
        for rec in self.fixture_inputs:
            for field in required_fields:
                self.assertIn(field, rec,
                              f"Fixture input '{rec.get('fixture_record_id', '?')}' missing field: {field}")

    def test_51_fixture_inputs_all_have_fixture_only_true(self):
        """All fixture input records must have fixture_only = true."""
        for rec in self.fixture_inputs:
            self.assertTrue(rec.get("fixture_only", False),
                            f"Record '{rec.get('fixture_record_id')}' fixture_only must be true")

    # ── Quality gate record tests ───────────────────────────────────────

    def test_52_quality_gate_records_have_required_fields(self):
        """Each quality gate record must have all required fields."""
        required_fields = [
            "card_family", "fixture_record_id", "quality_gate_passed",
            "required_fields_present", "assets_count_valid",
            "signal_summary_present", "supporting_metrics_present",
            "no_forbidden_claims", "no_direct_trading_advice",
            "no_fake_real_e2e_claim", "blocked_reasons", "fixture_only",
        ]
        for rec in self.quality_gates:
            for field in required_fields:
                self.assertIn(field, rec,
                              f"Quality gate '{rec.get('fixture_record_id', '?')}' missing field: {field}")

    # ── Send readiness record tests ─────────────────────────────────────

    def test_53_send_readiness_records_have_required_fields(self):
        """Each send readiness record must have all required fields."""
        required_fields = [
            "card_family", "fixture_record_id", "send_readiness_replay_passed",
            "tg_test_group_ready", "production_send_ready",
            "send_candidate_generated", "allowed_for_fixture_workflow_replay",
            "blocked_reasons", "fixture_only",
        ]
        for rec in self.send_readiness:
            for field in required_fields:
                self.assertIn(field, rec,
                              f"Send readiness '{rec.get('fixture_record_id', '?')}' missing field: {field}")

    def test_54_send_readiness_all_tg_false(self):
        """All send readiness records must have tg_test_group_ready = false."""
        for rec in self.send_readiness:
            self.assertFalse(rec.get("tg_test_group_ready", True),
                             f"Record '{rec.get('fixture_record_id')}' tg_test_group_ready must be false")

    def test_55_send_readiness_all_production_false(self):
        """All send readiness records must have production_send_ready = false."""
        for rec in self.send_readiness:
            self.assertFalse(rec.get("production_send_ready", True),
                             f"Record '{rec.get('fixture_record_id')}' production_send_ready must be false")

    # ── Workflow replay record tests ────────────────────────────────────

    def test_56_workflow_replay_records_have_required_fields(self):
        """Each workflow replay record must have all required fields."""
        required_fields = [
            "card_family", "fixture_record_id", "input_replay_ready",
            "card_generation_replay_ready", "quality_gate_replay_passed",
            "send_readiness_replay_passed", "fixture_workflow_ready",
            "fixture_e2e_passed", "real_e2e_passed",
            "tg_test_group_ready", "production_send_ready",
            "fixture_only", "not_real_e2e_warning",
        ]
        for rec in self.workflow_replays:
            for field in required_fields:
                self.assertIn(field, rec,
                              f"Workflow replay '{rec.get('fixture_record_id', '?')}' missing field: {field}")

    def test_57_workflow_replays_all_real_e2e_false(self):
        """All workflow replay records must have real_e2e_passed = false."""
        for rec in self.workflow_replays:
            self.assertFalse(rec.get("real_e2e_passed", True),
                             f"Record '{rec.get('fixture_record_id')}' real_e2e_passed must be false")

    # ── CSV tests ───────────────────────────────────────────────────────

    def test_58_csv_has_correct_rows(self):
        """CSV row count must match fixture input records."""
        import csv
        with open(REPORT_CSV, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        self.assertEqual(len(rows), len(self.fixture_inputs),
                         f"CSV has {len(rows)} rows, expected {len(self.fixture_inputs)}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
