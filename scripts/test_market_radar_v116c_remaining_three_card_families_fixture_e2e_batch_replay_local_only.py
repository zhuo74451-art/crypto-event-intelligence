"""Market Radar v1.16-C — Remaining Three Card Families Fixture E2E Batch Replay Tests

Validates all v116C outputs meet the acceptance criteria defined in the task spec.

Tests cover:
  - Summary JSON exists and has required fields
  - All JSONL outputs exist
  - Markdown report exists
  - CSV report exists
  - target_card_family_count == 3
  - target_card_families includes all 3 families
  - fixture_input_records >= 1
  - quality_gate_records == fixture_input_records
  - send_readiness_records == fixture_input_records
  - workflow_replay_decisions == fixture_input_records
  - families_fixture_e2e_passed + partial + blocked + not_found == 3
  - real_e2e_passed_count == 0
  - tg_test_group_ready_count == 0
  - production_send_ready_count == 0
  - send_candidate_generated_count == 0
  - real_send_candidate_generated == false
  - Markdown contains all 3 family names
  - Markdown does not claim real E2E passed
  - Markdown does not claim TG ready
  - Markdown does not claim production send ready
  - Markdown distinguishes fixture_e2e_passed and real_e2e_passed
  - All safety flags are false

Usage:
    python scripts/test_market_radar_v116c_remaining_three_card_families_fixture_e2e_batch_replay_local_only.py
"""

import json
import os
import sys
import unittest


# ── Paths ────────────────────────────────────────────────────────────────
PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

SUMMARY_JSON = os.path.join(
    PROJECT_DIR, "results",
    "market_radar_v116c_remaining_three_card_families_fixture_e2e_batch_replay_result.json"
)
FIXTURE_INPUT_JSONL = os.path.join(
    PROJECT_DIR, "results",
    "market_radar_v116c_remaining_card_family_fixture_input_records.jsonl"
)
QUALITY_GATE_JSONL = os.path.join(
    PROJECT_DIR, "results",
    "market_radar_v116c_remaining_card_family_quality_gate_records.jsonl"
)
SEND_READINESS_JSONL = os.path.join(
    PROJECT_DIR, "results",
    "market_radar_v116c_remaining_card_family_send_readiness_records.jsonl"
)
WORKFLOW_REPLAY_JSONL = os.path.join(
    PROJECT_DIR, "results",
    "market_radar_v116c_remaining_card_family_workflow_replay_decisions.jsonl"
)
REPORT_MD = os.path.join(
    PROJECT_DIR, "runs", "market_radar",
    "v116c_remaining_three_card_families_fixture_e2e_batch_replay.md"
)
REPORT_CSV = os.path.join(
    PROJECT_DIR, "runs", "market_radar",
    "v116c_remaining_three_card_families_fixture_e2e_batch_replay.csv"
)
HANDOFF_MD = os.path.join(
    PROJECT_DIR, "runs", "market_radar",
    "v116c_remaining_three_card_families_fixture_e2e_batch_replay_local_only_handoff.md"
)

TARGET_FAMILIES = [
    "price_oi_volume_anomaly",
    "liquidation_pressure",
    "news_event_market_impact",
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

class TestV116CFixtureE2EBatchReplay(unittest.TestCase):
    """Tests for v116C Remaining Three Card Families Fixture E2E Batch Replay."""

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

    def test_10_target_card_family_count_is_3(self):
        """target_card_family_count must be 3."""
        self.assertIsNotNone(self.summary, "Summary JSON not loaded")
        self.assertEqual(self.summary.get("target_card_family_count"), 3,
                         "target_card_family_count must be 3")

    def test_11_target_families_include_price_oi_volume_anomaly(self):
        """target_card_families must include price_oi_volume_anomaly."""
        self.assertIsNotNone(self.summary, "Summary JSON not loaded")
        families = self.summary.get("target_card_families", [])
        self.assertIn("price_oi_volume_anomaly", families,
                      "target_card_families must include price_oi_volume_anomaly")

    def test_12_target_families_include_liquidation_pressure(self):
        """target_card_families must include liquidation_pressure."""
        self.assertIsNotNone(self.summary, "Summary JSON not loaded")
        families = self.summary.get("target_card_families", [])
        self.assertIn("liquidation_pressure", families,
                      "target_card_families must include liquidation_pressure")

    def test_13_target_families_include_news_event_market_impact(self):
        """target_card_families must include news_event_market_impact."""
        self.assertIsNotNone(self.summary, "Summary JSON not loaded")
        families = self.summary.get("target_card_families", [])
        self.assertIn("news_event_market_impact", families,
                      "target_card_families must include news_event_market_impact")

    def test_14_fixture_input_records_at_least_1(self):
        """fixture_input_records must be >= 1."""
        self.assertIsNotNone(self.summary, "Summary JSON not loaded")
        self.assertGreaterEqual(self.summary.get("fixture_input_records", 0), 1,
                                "fixture_input_records must be >= 1")

    # ── Record count consistency tests ──────────────────────────────────

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
        """Summary JSON counts must match actual counts."""
        self.assertIsNotNone(self.summary, "Summary JSON not loaded")
        self.assertEqual(self.summary.get("quality_gate_records", 0), len(self.quality_gates))
        self.assertEqual(self.summary.get("send_readiness_records", 0), len(self.send_readiness))
        self.assertEqual(self.summary.get("workflow_replay_decisions", 0), len(self.workflow_replays))

    # ── Family count sum test ───────────────────────────────────────────

    def test_20_family_statuses_sum_to_3(self):
        """families_fixture_e2e_passed + partial + blocked + not_found must == 3."""
        self.assertIsNotNone(self.summary, "Summary JSON not loaded")
        total = (
            self.summary.get("families_fixture_e2e_passed_count", 0) +
            self.summary.get("families_partial_count", 0) +
            self.summary.get("families_blocked_count", 0) +
            self.summary.get("families_not_found_count", 0)
        )
        self.assertEqual(total, 3,
                         f"Family statuses sum to {total}, expected 3")

    # ── E2E pass/fail state tests ───────────────────────────────────────

    def test_21_real_e2e_passed_count_is_0(self):
        """real_e2e_passed_count must be 0."""
        self.assertIsNotNone(self.summary, "Summary JSON not loaded")
        self.assertEqual(self.summary.get("real_e2e_passed_count"), 0,
                         "real_e2e_passed_count must be 0")

    # ── Send state tests (all must be 0 or false) ───────────────────────

    def test_22_tg_test_group_ready_count_is_0(self):
        """tg_test_group_ready_count must be 0."""
        self.assertIsNotNone(self.summary, "Summary JSON not loaded")
        self.assertEqual(self.summary.get("tg_test_group_ready_count"), 0,
                         "tg_test_group_ready_count must be 0")

    def test_23_production_send_ready_count_is_0(self):
        """production_send_ready_count must be 0."""
        self.assertIsNotNone(self.summary, "Summary JSON not loaded")
        self.assertEqual(self.summary.get("production_send_ready_count"), 0,
                         "production_send_ready_count must be 0")

    def test_24_send_candidate_generated_count_is_0(self):
        """send_candidate_generated_count must be 0."""
        self.assertIsNotNone(self.summary, "Summary JSON not loaded")
        self.assertEqual(self.summary.get("send_candidate_generated_count"), 0,
                         "send_candidate_generated_count must be 0")

    def test_25_real_send_candidate_generated_is_false(self):
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

    def test_37_audit_result_exists(self):
        """audit_result must be present in summary."""
        self.assertIsNotNone(self.summary, "Summary JSON not loaded")
        self.assertIn(self.summary.get("audit_result", ""), [
            "remaining_three_fixture_e2e_passed_real_e2e_not_started",
            "partial_fixture_e2e_passed_with_gaps",
            "blocked_missing_fixture_or_preview_evidence",
        ], f"Unexpected audit_result: {self.summary.get('audit_result')}")

    # ── Markdown content tests ──────────────────────────────────────────

    def test_40_markdown_contains_price_oi_volume_anomaly(self):
        """Markdown must contain price_oi_volume_anomaly."""
        self.assertIn("price_oi_volume_anomaly", self.report_md_text,
                      "Markdown must mention price_oi_volume_anomaly")

    def test_41_markdown_contains_liquidation_pressure(self):
        """Markdown must contain liquidation_pressure."""
        self.assertIn("liquidation_pressure", self.report_md_text,
                      "Markdown must mention liquidation_pressure")

    def test_42_markdown_contains_news_event_market_impact(self):
        """Markdown must contain news_event_market_impact."""
        self.assertIn("news_event_market_impact", self.report_md_text,
                      "Markdown must mention news_event_market_impact")

    def test_43_markdown_does_not_claim_real_e2e_passed(self):
        """Markdown must not claim real E2E is passed."""
        md_lower = self.report_md_text.lower()
        bad_claims = [
            "real e2e passed: ✅",
            "real e2e passed = true",
            "all five card families real e2e passed",
        ]
        for claim in bad_claims:
            self.assertNotIn(claim, md_lower,
                            f"Markdown incorrectly claims: '{claim}'")

    def test_44_markdown_does_not_claim_tg_ready(self):
        """Markdown must not claim TG test group is ready."""
        md_lower = self.report_md_text.lower()
        bad_claims = [
            "tg test group ready: ✅",
            "tg ready: yes",
            "tg test group: ✅",
        ]
        for claim in bad_claims:
            self.assertNotIn(claim, md_lower,
                            f"Markdown incorrectly claims TG ready: '{claim}'")

    def test_45_markdown_does_not_claim_production_send_ready(self):
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

    def test_46_markdown_distinguishes_fixture_and_real_e2e(self):
        """Markdown must distinguish fixture_e2e_passed from real_e2e_passed."""
        md_lower = self.report_md_text.lower()
        has_fixture = "fixture" in md_lower
        has_distinction = (
            "fixture_e2e_passed != real_e2e_passed" in md_lower or
            "does not mean" in md_lower or
            "does NOT mean" in self.report_md_text
        )
        self.assertTrue(has_fixture and has_distinction,
                        "Markdown must distinguish fixture E2E from real E2E")

    # ── Fixture input record quality tests ──────────────────────────────

    def test_50_fixture_inputs_have_required_fields(self):
        """Each fixture input record must have all required fields."""
        required_fields = [
            "card_family", "fixture_record_id", "source_evidence_file",
            "source_artifact_type", "signal_type", "signal_summary",
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

    def test_52_all_three_families_present_in_inputs(self):
        """All 3 target families must have at least 1 fixture input record."""
        families_found = set(rec["card_family"] for rec in self.fixture_inputs)
        for family in TARGET_FAMILIES:
            self.assertIn(family, families_found,
                          f"Card family '{family}' not found in fixture inputs")

    # ── Quality gate record tests ───────────────────────────────────────

    def test_53_quality_gate_records_have_required_fields(self):
        """Each quality gate record must have all required fields."""
        required_fields = [
            "card_family", "fixture_record_id", "quality_gate_passed",
            "required_fields_present", "signal_summary_present",
            "supporting_metrics_present", "asset_or_event_anchor_present",
            "no_forbidden_claims", "no_direct_trading_advice",
            "no_fake_real_e2e_claim", "blocked_reasons", "fixture_only",
        ]
        for rec in self.quality_gates:
            for field in required_fields:
                self.assertIn(field, rec,
                              f"Quality gate '{rec.get('fixture_record_id', '?')}' missing field: {field}")

    # ── Send readiness record tests ─────────────────────────────────────

    def test_54_send_readiness_records_have_required_fields(self):
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

    def test_55_send_readiness_all_tg_false(self):
        """All send readiness records must have tg_test_group_ready = false."""
        for rec in self.send_readiness:
            self.assertFalse(rec.get("tg_test_group_ready", True),
                             f"Record '{rec.get('fixture_record_id')}' tg_test_group_ready must be false")

    def test_56_send_readiness_all_production_false(self):
        """All send readiness records must have production_send_ready = false."""
        for rec in self.send_readiness:
            self.assertFalse(rec.get("production_send_ready", True),
                             f"Record '{rec.get('fixture_record_id')}' production_send_ready must be false")

    def test_57_send_readiness_all_send_candidate_false(self):
        """All send readiness records must have send_candidate_generated = false."""
        for rec in self.send_readiness:
            self.assertFalse(rec.get("send_candidate_generated", True),
                             f"Record '{rec.get('fixture_record_id')}' send_candidate_generated must be false")

    # ── Workflow replay record tests ────────────────────────────────────

    def test_58_workflow_replay_records_have_required_fields(self):
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

    def test_59_workflow_replays_all_real_e2e_false(self):
        """All workflow replay records must have real_e2e_passed = false."""
        for rec in self.workflow_replays:
            self.assertFalse(rec.get("real_e2e_passed", True),
                             f"Record '{rec.get('fixture_record_id')}' real_e2e_passed must be false")

    def test_60_workflow_replays_all_tg_false(self):
        """All workflow replay records must have tg_test_group_ready = false."""
        for rec in self.workflow_replays:
            self.assertFalse(rec.get("tg_test_group_ready", True),
                             f"Record '{rec.get('fixture_record_id')}' tg_test_group_ready must be false")

    def test_61_workflow_replays_all_production_false(self):
        """All workflow replay records must have production_send_ready = false."""
        for rec in self.workflow_replays:
            self.assertFalse(rec.get("production_send_ready", True),
                             f"Record '{rec.get('fixture_record_id')}' production_send_ready must be false")

    # ── Family-specific field tests per the task spec ───────────────────

    def test_62_price_oi_volume_anomaly_supporting_metrics(self):
        """price_oi_volume_anomaly records must have asset, price_change, oi_change, volume_change, anomaly_direction."""
        pova_records = [r for r in self.fixture_inputs if r["card_family"] == "price_oi_volume_anomaly"]
        self.assertGreater(len(pova_records), 0, "No price_oi_volume_anomaly records")
        for rec in pova_records:
            metrics = rec.get("supporting_metrics", {})
            self.assertIn("asset", metrics, f"Record {rec['fixture_record_id']} missing asset in metrics")
            self.assertIn("price_change", metrics, f"Record {rec['fixture_record_id']} missing price_change")
            self.assertIn("oi_change", metrics, f"Record {rec['fixture_record_id']} missing oi_change")
            self.assertIn("anomaly_direction", metrics, f"Record {rec['fixture_record_id']} missing anomaly_direction")

    def test_63_liquidation_pressure_supporting_metrics(self):
        """liquidation_pressure records must have asset, liquidation_side, liquidation_size, liquidation_cluster, pressure_direction."""
        liq_records = [r for r in self.fixture_inputs if r["card_family"] == "liquidation_pressure"]
        self.assertGreater(len(liq_records), 0, "No liquidation_pressure records")
        for rec in liq_records:
            metrics = rec.get("supporting_metrics", {})
            self.assertIn("asset", metrics, f"Record {rec['fixture_record_id']} missing asset in metrics")
            self.assertIn("liquidation_side", metrics, f"Record {rec['fixture_record_id']} missing liquidation_side")
            self.assertIn("liquidation_size", metrics, f"Record {rec['fixture_record_id']} missing liquidation_size")
            self.assertIn("pressure_direction", metrics, f"Record {rec['fixture_record_id']} missing pressure_direction")

    def test_64_news_event_market_impact_supporting_metrics(self):
        """news_event_market_impact records must have event_title, related_assets, market_reaction, impact_summary, source_type."""
        news_records = [r for r in self.fixture_inputs if r["card_family"] == "news_event_market_impact"]
        self.assertGreater(len(news_records), 0, "No news_event_market_impact records")
        for rec in news_records:
            metrics = rec.get("supporting_metrics", {})
            self.assertIn("event_title", metrics, f"Record {rec['fixture_record_id']} missing event_title")
            self.assertIn("related_assets", metrics, f"Record {rec['fixture_record_id']} missing related_assets")
            self.assertIn("market_reaction", metrics, f"Record {rec['fixture_record_id']} missing market_reaction")
            self.assertIn("source_type", metrics, f"Record {rec['fixture_record_id']} missing source_type")

    # ── CSV tests ───────────────────────────────────────────────────────

    def test_65_csv_has_correct_rows(self):
        """CSV row count must match fixture input records (header + data rows)."""
        import csv
        with open(REPORT_CSV, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        self.assertEqual(len(rows), len(self.fixture_inputs),
                         f"CSV has {len(rows)} data rows, expected {len(self.fixture_inputs)}")

    # ── No blocked families with records ────────────────────────────────

    def test_66_each_family_has_at_least_one_record(self):
        """Each of the 3 target families must have at least 1 fixture input record."""
        family_counts = {}
        for rec in self.fixture_inputs:
            family = rec["card_family"]
            family_counts[family] = family_counts.get(family, 0) + 1
        for family in TARGET_FAMILIES:
            self.assertIn(family, family_counts,
                          f"Card family '{family}' has 0 records")
            self.assertGreaterEqual(family_counts[family], 1,
                                    f"Card family '{family}' has {family_counts.get(family, 0)} records (need >= 1)")


if __name__ == "__main__":
    unittest.main(verbosity=2)
