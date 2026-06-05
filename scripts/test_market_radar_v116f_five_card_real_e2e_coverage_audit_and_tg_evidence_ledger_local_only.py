"""Market Radar v1.16-F — Five Card Real E2E Coverage Audit + TG Evidence Ledger Tests

Validates all v116F outputs meet the acceptance criteria defined in the task spec.

Tests cover:
  - All v116F output files exist
  - Five card families all present, no duplicates
  - multi_asset_market_sync correctly marked as real API + TG test sent
  - Other 4 families NOT incorrectly marked as tg_test_sent: true
  - production_send_ready ALL false
  - prod_state_write is false
  - external_api_called this run is false (v116F reads history only)
  - tg_sent_this_run is false (v116F does not re-send)
  - Evidence ledger contains no raw token/chat_id/message_id
  - Audit does not mistake fixture E2E for real E2E
  - Next candidate decision file exists with recommendation + rationale

Usage:
    python scripts/test_market_radar_v116f_five_card_real_e2e_coverage_audit_and_tg_evidence_ledger_local_only.py
"""

import json
import os
import sys
import unittest


# ── Paths ──────────────────────────────────────────────────────────────────
PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

AUDIT_JSON = os.path.join(
    PROJECT_DIR, "results",
    "market_radar_v116f_five_card_real_e2e_coverage_audit_result.json"
)
LEDGER_JSONL = os.path.join(
    PROJECT_DIR, "results",
    "market_radar_v116f_tg_test_send_evidence_ledger.jsonl"
)
REPORT_MD = os.path.join(
    PROJECT_DIR, "runs", "market_radar",
    "v116f_five_card_real_e2e_coverage_audit.md"
)
REPORT_CSV = os.path.join(
    PROJECT_DIR, "runs", "market_radar",
    "v116f_five_card_real_e2e_coverage_audit.csv"
)
CANDIDATE_MD = os.path.join(
    PROJECT_DIR, "runs", "market_radar",
    "v116f_next_real_e2e_candidate_decision.md"
)
HANDOFF_MD = os.path.join(
    PROJECT_DIR, "runs", "market_radar",
    "v116f_local_only_handoff.md"
)

CANONICAL_FAMILIES = [
    "whale_position_alert",
    "multi_asset_market_sync",
    "price_oi_volume_anomaly",
    "liquidation_pressure",
    "news_event_market_impact",
]

REQUIRED_COVERAGE_FIELDS = [
    "card_family",
    "router_passed",
    "fixture_e2e_passed",
    "real_external_api_called",
    "real_card_generated",
    "quality_gate_passed",
    "send_readiness_passed",
    "tg_test_sent",
    "tg_test_group_ready",
    "production_send_ready",
    "real_e2e_status",
    "current_blocker",
    "next_action",
]

REQUIRED_LEDGER_FIELDS = [
    "card_family",
    "source_task_id",
    "source_result_file",
    "target_type",
    "one_shot",
    "tg_sent",
    "message_id_present",
    "message_id_redacted",
    "token_fingerprint_redacted",
    "chat_id_fingerprint_redacted",
    "production_send",
    "credentials_printed",
    "raw_secret_present_in_outputs",
]


def load_jsonl(path):
    records = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


# ── Test Case ──────────────────────────────────────────────────────────────

class TestV116FCoverageAuditAndLedger(unittest.TestCase):
    """Tests for v116F five-card real E2E coverage audit + TG evidence ledger."""

    @classmethod
    def setUpClass(cls):
        cls.audit = None
        cls.records = []
        cls.ledger = []
        cls.report_md = ""
        cls.candidate_md = ""
        cls.handoff_md = ""

        if os.path.exists(AUDIT_JSON):
            with open(AUDIT_JSON, "r", encoding="utf-8") as f:
                cls.audit = json.load(f)
            cls.records = cls.audit.get("coverage_records", [])

        if os.path.exists(LEDGER_JSONL):
            cls.ledger = load_jsonl(LEDGER_JSONL)

        if os.path.exists(REPORT_MD):
            with open(REPORT_MD, "r", encoding="utf-8") as f:
                cls.report_md = f.read()

        if os.path.exists(CANDIDATE_MD):
            with open(CANDIDATE_MD, "r", encoding="utf-8") as f:
                cls.candidate_md = f.read()

        if os.path.exists(HANDOFF_MD):
            with open(HANDOFF_MD, "r", encoding="utf-8") as f:
                cls.handoff_md = f.read()

    # ══════════════════════════════════════════════════════════════════════
    # File existence tests
    # ══════════════════════════════════════════════════════════════════════

    def test_01_audit_json_exists(self):
        """v116F audit result JSON must exist."""
        self.assertTrue(os.path.exists(AUDIT_JSON),
                        f"Missing: {AUDIT_JSON}")

    def test_02_ledger_jsonl_exists(self):
        """v116F TG evidence ledger JSONL must exist."""
        self.assertTrue(os.path.exists(LEDGER_JSONL),
                        f"Missing: {LEDGER_JSONL}")

    def test_03_report_md_exists(self):
        """v116F coverage audit Markdown must exist."""
        self.assertTrue(os.path.exists(REPORT_MD),
                        f"Missing: {REPORT_MD}")

    def test_04_report_csv_exists(self):
        """v116F coverage audit CSV must exist."""
        self.assertTrue(os.path.exists(REPORT_CSV),
                        f"Missing: {REPORT_CSV}")

    def test_05_candidate_md_exists(self):
        """v116F next candidate decision Markdown must exist."""
        self.assertTrue(os.path.exists(CANDIDATE_MD),
                        f"Missing: {CANDIDATE_MD}")

    def test_06_handoff_md_exists(self):
        """v116F handoff Markdown must exist."""
        self.assertTrue(os.path.exists(HANDOFF_MD),
                        f"Missing: {HANDOFF_MD}")

    # ══════════════════════════════════════════════════════════════════════
    # Card family coverage tests
    # ══════════════════════════════════════════════════════════════════════

    def test_10_five_card_families_present(self):
        """All 5 canonical card families must be present."""
        self.assertIsNotNone(self.audit, "Audit JSON not loaded")
        found = {r["card_family"] for r in self.records}
        expected = set(CANONICAL_FAMILIES)
        self.assertEqual(found, expected,
                         f"Card families mismatch: found={found}, expected={expected}")

    def test_11_no_duplicate_card_families(self):
        """No duplicate card family entries."""
        names = [r["card_family"] for r in self.records]
        self.assertEqual(len(names), len(set(names)),
                         f"Duplicate card families found: {names}")

    def test_12_card_family_count_is_5(self):
        """Exactly 5 card families in coverage records."""
        self.assertIsNotNone(self.audit, "Audit JSON not loaded")
        self.assertEqual(self.audit.get("card_family_count"), 5,
                         "card_family_count must be 5")

    def test_13_fixture_e2e_passed_count_is_5(self):
        """All 5 families must have fixture_e2e_passed_count = 5."""
        self.assertIsNotNone(self.audit, "Audit JSON not loaded")
        self.assertEqual(self.audit.get("fixture_e2e_passed_count"), 5,
                         "fixture_e2e_passed_count must be 5")

    def test_14_real_api_tg_test_sent_count_is_1(self):
        """Exactly 1 family (multi_asset_market_sync) has real API + TG test sent."""
        self.assertIsNotNone(self.audit, "Audit JSON not loaded")
        self.assertEqual(self.audit.get("real_api_tg_test_sent_count"), 1,
                         "real_api_tg_test_sent_count must be 1")

    def test_15_production_send_ready_count_is_0(self):
        """No family is production send ready."""
        self.assertIsNotNone(self.audit, "Audit JSON not loaded")
        self.assertEqual(self.audit.get("production_send_ready_count"), 0,
                         "production_send_ready_count must be 0")

    # ══════════════════════════════════════════════════════════════════════
    # multi_asset_market_sync specific tests
    # ══════════════════════════════════════════════════════════════════════

    def test_20_mams_real_external_api_called_true(self):
        """multi_asset_market_sync must have real_external_api_called: true."""
        mams = self._find_card("multi_asset_market_sync")
        self.assertTrue(mams["real_external_api_called"],
                        "MAMS real_external_api_called must be True")

    def test_21_mams_real_card_generated_true(self):
        """multi_asset_market_sync must have real_card_generated: true."""
        mams = self._find_card("multi_asset_market_sync")
        self.assertTrue(mams["real_card_generated"],
                        "MAMS real_card_generated must be True")

    def test_22_mams_quality_gate_passed_true(self):
        """multi_asset_market_sync must have quality_gate_passed: true."""
        mams = self._find_card("multi_asset_market_sync")
        self.assertTrue(mams["quality_gate_passed"],
                        "MAMS quality_gate_passed must be True")

    def test_23_mams_send_readiness_passed_true(self):
        """multi_asset_market_sync must have send_readiness_passed: true."""
        mams = self._find_card("multi_asset_market_sync")
        self.assertTrue(mams["send_readiness_passed"],
                        "MAMS send_readiness_passed must be True")

    def test_24_mams_tg_test_sent_true(self):
        """multi_asset_market_sync must have tg_test_sent: true."""
        mams = self._find_card("multi_asset_market_sync")
        self.assertTrue(mams["tg_test_sent"],
                        "MAMS tg_test_sent must be True")

    def test_25_mams_tg_test_group_ready_true(self):
        """multi_asset_market_sync must have tg_test_group_ready: true."""
        mams = self._find_card("multi_asset_market_sync")
        self.assertTrue(mams["tg_test_group_ready"],
                        "MAMS tg_test_group_ready must be True")

    def test_26_mams_real_e2e_status_correct(self):
        """multi_asset_market_sync real_e2e_status must be real_free_api_tg_test_sent."""
        mams = self._find_card("multi_asset_market_sync")
        self.assertEqual(mams["real_e2e_status"], "real_free_api_tg_test_sent",
                         f"MAMS real_e2e_status={mams['real_e2e_status']}")

    def test_27_mams_production_send_ready_false(self):
        """multi_asset_market_sync production_send_ready must be False."""
        mams = self._find_card("multi_asset_market_sync")
        self.assertFalse(mams["production_send_ready"],
                         "MAMS production_send_ready must be False")

    # ══════════════════════════════════════════════════════════════════════
    # Other four card families must NOT be tg_test_sent
    # ══════════════════════════════════════════════════════════════════════

    def test_30_whale_not_tg_test_sent(self):
        """whale_position_alert must NOT have tg_test_sent: true."""
        wpa = self._find_card("whale_position_alert")
        self.assertFalse(wpa["tg_test_sent"],
                         "whale_position_alert tg_test_sent must be False")

    def test_31_pova_not_tg_test_sent(self):
        """price_oi_volume_anomaly must NOT have tg_test_sent: true."""
        pova = self._find_card("price_oi_volume_anomaly")
        self.assertFalse(pova["tg_test_sent"],
                         "price_oi_volume_anomaly tg_test_sent must be False")

    def test_32_lipr_not_tg_test_sent(self):
        """liquidation_pressure must NOT have tg_test_sent: true."""
        lipr = self._find_card("liquidation_pressure")
        self.assertFalse(lipr["tg_test_sent"],
                         "liquidation_pressure tg_test_sent must be False")

    def test_33_nemi_not_tg_test_sent(self):
        """news_event_market_impact must NOT have tg_test_sent: true."""
        nemi = self._find_card("news_event_market_impact")
        self.assertFalse(nemi["tg_test_sent"],
                         "news_event_market_impact tg_test_sent must be False")

    # ══════════════════════════════════════════════════════════════════════
    # All production_send_ready must be False
    # ══════════════════════════════════════════════════════════════════════

    def test_35_all_production_send_ready_false(self):
        """Every card family must have production_send_ready: false."""
        for r in self.records:
            self.assertFalse(r["production_send_ready"],
                             f"{r['card_family']} production_send_ready must be False")

    # ══════════════════════════════════════════════════════════════════════
    # Safety flag tests
    # ══════════════════════════════════════════════════════════════════════

    def test_40_external_api_called_this_run_false(self):
        """v116F must not have called external API."""
        self.assertIsNotNone(self.audit, "Audit JSON not loaded")
        self.assertFalse(self.audit.get("external_api_called_this_run", True),
                         "external_api_called_this_run must be False")

    def test_41_tg_sent_this_run_false(self):
        """v116F must not have sent TG messages."""
        self.assertIsNotNone(self.audit, "Audit JSON not loaded")
        self.assertFalse(self.audit.get("tg_sent_this_run", True),
                         "tg_sent_this_run must be False")

    def test_42_prod_state_write_false(self):
        """prod_state_write must be False."""
        self.assertIsNotNone(self.audit, "Audit JSON not loaded")
        self.assertFalse(self.audit.get("prod_state_write", True),
                         "prod_state_write must be False")

    def test_43_ai_model_called_false(self):
        """ai_model_called must be False."""
        self.assertIsNotNone(self.audit, "Audit JSON not loaded")
        self.assertFalse(self.audit.get("ai_model_called", True),
                         "ai_model_called must be False")

    def test_44_files_deleted_false(self):
        """files_deleted must be False."""
        self.assertIsNotNone(self.audit, "Audit JSON not loaded")
        self.assertFalse(self.audit.get("files_deleted", True),
                         "files_deleted must be False")

    def test_45_historical_artifacts_modified_false(self):
        """historical_artifacts_modified must be False."""
        self.assertIsNotNone(self.audit, "Audit JSON not loaded")
        self.assertFalse(self.audit.get("historical_artifacts_modified", True),
                         "historical_artifacts_modified must be False")

    def test_46_credentials_read_false(self):
        """credentials_read must be False."""
        self.assertIsNotNone(self.audit, "Audit JSON not loaded")
        self.assertFalse(self.audit.get("credentials_read", True),
                         "credentials_read must be False")

    # ══════════════════════════════════════════════════════════════════════
    # Coverage record field tests
    # ══════════════════════════════════════════════════════════════════════

    def test_50_all_required_coverage_fields_present(self):
        """Every coverage record must have all required fields."""
        for r in self.records:
            for field in REQUIRED_COVERAGE_FIELDS:
                self.assertIn(field, r,
                              f"Card '{r.get('card_family', '?')}' missing field: {field}")

    def test_51_whale_blocked_reason_not_empty(self):
        """whale_position_alert must have a non-null current_blocker."""
        wpa = self._find_card("whale_position_alert")
        self.assertIsNotNone(wpa.get("current_blocker"),
                             "whale_position_alert current_blocker must not be None/null")
        self.assertTrue(len(wpa["current_blocker"]) > 0,
                        "whale_position_alert current_blocker must not be empty")

    def test_52_mams_blocker_is_none(self):
        """multi_asset_market_sync current_blocker must be None (not blocked)."""
        mams = self._find_card("multi_asset_market_sync")
        self.assertIsNone(mams.get("current_blocker"),
                          "MAMS current_blocker must be None")

    # ══════════════════════════════════════════════════════════════════════
    # Fixture E2E vs Real E2E distinction
    # ══════════════════════════════════════════════════════════════════════

    def test_55_no_fixture_mistaken_for_real_e2e(self):
        """No card with real_external_api_called=False should have real_e2e_status suggesting real E2E."""
        for r in self.records:
            if not r["real_external_api_called"]:
                self.assertNotIn(r["real_e2e_status"],
                                 ["real_free_api_tg_test_sent", "real_e2e_passed"],
                                 f"{r['card_family']} has real_external_api_called=False "
                                 f"but real_e2e_status={r['real_e2e_status']}")

    def test_56_all_fixture_e2e_passed_except_mams_not_real(self):
        """All 4 non-MAMS families must have fixture_e2e_passed=True but real_e2e_status != real."""
        for r in self.records:
            if r["card_family"] != "multi_asset_market_sync":
                self.assertTrue(r["fixture_e2e_passed"],
                                f"{r['card_family']} fixture_e2e_passed must be True")
                self.assertNotEqual(r["real_e2e_status"], "real_free_api_tg_test_sent",
                                    f"{r['card_family']} must not have real_e2e_status=real_free_api_tg_test_sent")

    # ══════════════════════════════════════════════════════════════════════
    # TG Evidence Ledger tests
    # ══════════════════════════════════════════════════════════════════════

    def test_60_ledger_has_entries(self):
        """Evidence ledger must have at least 1 entry."""
        self.assertGreaterEqual(len(self.ledger), 1,
                                "Ledger must have at least 1 entry")

    def test_61_all_ledger_fields_present(self):
        """Every ledger entry must have all required fields."""
        for entry in self.ledger:
            for field in REQUIRED_LEDGER_FIELDS:
                self.assertIn(field, entry,
                              f"Ledger entry missing field: {field}")

    def test_62_ledger_target_type_is_test_group(self):
        """All ledger entries must have target_type: test_group."""
        for entry in self.ledger:
            self.assertEqual(entry.get("target_type"), "test_group",
                             f"target_type must be test_group, got: {entry.get('target_type')}")

    def test_63_ledger_one_shot_true(self):
        """All ledger entries must have one_shot: true."""
        for entry in self.ledger:
            self.assertTrue(entry.get("one_shot"),
                            "one_shot must be True")

    def test_64_ledger_production_send_false(self):
        """All ledger entries must have production_send: false."""
        for entry in self.ledger:
            self.assertFalse(entry.get("production_send"),
                             "production_send must be False")

    def test_65_ledger_credentials_printed_false(self):
        """All ledger entries must have credentials_printed: false."""
        for entry in self.ledger:
            self.assertFalse(entry.get("credentials_printed"),
                             "credentials_printed must be False")

    def test_66_ledger_raw_secret_present_false(self):
        """All ledger entries must have raw_secret_present_in_outputs: false."""
        for entry in self.ledger:
            self.assertFalse(entry.get("raw_secret_present_in_outputs"),
                             "raw_secret_present_in_outputs must be False")

    def test_67_no_raw_token_in_ledger(self):
        """No ledger field should contain an unredacted token/chat_id/message_id."""
        # Raw tokens typically match patterns like "123456:ABCDEF..." or numeric chat IDs
        import re
        token_pattern = re.compile(r'\d{8,12}:[A-Za-z0-9_-]{30,}')
        chat_id_pattern = re.compile(r'^-?\d{8,}$')
        message_id_pattern = re.compile(r'^\d{3,}$')

        for entry in self.ledger:
            entry_str = json.dumps(entry)
            self.assertIsNone(token_pattern.search(entry_str),
                              f"Ledger contains unredacted token-like value")
            # message_id_redacted and chat_id_fingerprint_redacted are OK if they start with sha256:
            for field in ["message_id_redacted", "token_fingerprint_redacted", "chat_id_fingerprint_redacted"]:
                val = entry.get(field, "")
                self.assertTrue(val.startswith("sha256:") or val == "",
                                f"Field {field} not properly redacted: '{val[:40]}...'")

    def test_68_ledger_message_id_present_true(self):
        """All ledger entries must have message_id_present: true (TG send succeeded)."""
        for entry in self.ledger:
            self.assertTrue(entry.get("message_id_present"),
                            "message_id_present must be True (TG send was successful)")

    def test_69_ledger_card_family_is_mams(self):
        """All ledger entries must reference multi_asset_market_sync."""
        for entry in self.ledger:
            self.assertEqual(entry.get("card_family"), "multi_asset_market_sync",
                             "Ledger card_family must be multi_asset_market_sync")

    # ══════════════════════════════════════════════════════════════════════
    # Next candidate decision tests
    # ══════════════════════════════════════════════════════════════════════

    def test_80_candidate_md_contains_recommendation(self):
        """Candidate decision MD must contain a recommendation."""
        self.assertIn("Recommended", self.candidate_md,
                      "Candidate MD missing 'Recommended' section")

    def test_81_candidate_md_contains_rationale(self):
        """Candidate decision MD must contain rationale/reasoning."""
        self.assertIn("Rationale", self.candidate_md,
                      "Candidate MD missing 'Rationale' section")

    def test_82_candidate_md_mentions_risk(self):
        """Candidate decision MD must discuss data quality risk for the recommended candidate."""
        self.assertIn("Risk", self.candidate_md,
                      "Candidate MD missing risk discussion")

    def test_83_candidate_md_mentions_whale_blocked(self):
        """Candidate decision MD must explain why whale_position_alert is excluded."""
        self.assertIn("whale_position_alert", self.candidate_md.lower(),
                      "Candidate MD must mention whale_position_alert")

    def test_84_candidate_md_has_scoring_matrix(self):
        """Candidate decision MD must have a scoring matrix table."""
        self.assertIn("Scoring Matrix", self.candidate_md,
                      "Candidate MD missing 'Scoring Matrix' section")

    # ══════════════════════════════════════════════════════════════════════
    # Markdown report content tests
    # ══════════════════════════════════════════════════════════════════════

    def test_90_md_contains_executive_summary(self):
        """Coverage MD must have an executive summary."""
        self.assertIn("Executive Summary", self.report_md,
                      "Report MD missing 'Executive Summary'")

    def test_91_md_contains_coverage_matrix(self):
        """Coverage MD must have a coverage matrix table."""
        self.assertIn("Coverage Matrix", self.report_md,
                      "Report MD missing 'Coverage Matrix'")

    def test_92_md_contains_mams_highlight(self):
        """Coverage MD must highlight multi_asset_market_sync as first real E2E."""
        self.assertIn("multi_asset_market_sync", self.report_md,
                      "Report MD must mention multi_asset_market_sync")
        self.assertIn("real_free_api_tg_test_sent", self.report_md,
                      "Report MD must mention real_free_api_tg_test_sent status")

    def test_93_md_contains_safety_constraints(self):
        """Coverage MD must list safety constraints."""
        self.assertIn("Safety Constraints", self.report_md,
                      "Report MD missing 'Safety Constraints'")

    def test_94_md_does_not_claim_production_ready(self):
        """Coverage MD must NOT claim any card is production ready."""
        # production_send_ready should appear as ❌ or False
        self.assertIn("0/5", self.report_md,
                      "Report MD should state 0/5 production send ready")

    # ══════════════════════════════════════════════════════════════════════
    # CSV tests
    # ══════════════════════════════════════════════════════════════════════

    def test_95_csv_has_correct_columns(self):
        """CSV must have required columns."""
        import csv
        with open(REPORT_CSV, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            fieldnames = reader.fieldnames
            self.assertIsNotNone(fieldnames, "CSV has no headers")
            for col in ["card_family", "real_external_api_called", "tg_test_sent",
                        "production_send_ready", "real_e2e_status"]:
                self.assertIn(col, fieldnames, f"CSV missing column: {col}")

    def test_96_csv_row_count_is_5(self):
        """CSV must have exactly 5 rows (one per card family)."""
        import csv
        with open(REPORT_CSV, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        self.assertEqual(len(rows), 5,
                         f"CSV has {len(rows)} rows, expected 5")

    # ══════════════════════════════════════════════════════════════════════
    # Handoff tests
    # ══════════════════════════════════════════════════════════════════════

    def test_97_handoff_contains_coverage_summary(self):
        """Handoff MD must contain five-card coverage summary."""
        self.assertIn("Coverage Summary", self.handoff_md,
                      "Handoff MD missing 'Coverage Summary'")

    def test_98_handoff_contains_safety_confirmation(self):
        """Handoff MD must contain safety confirmation."""
        self.assertIn("Safety Confirmation", self.handoff_md,
                      "Handoff MD missing 'Safety Confirmation'")

    def test_99_handoff_contains_unfinished_risks(self):
        """Handoff MD must contain unfinished items/risks."""
        self.assertIn("Unfinished Items", self.handoff_md,
                      "Handoff MD missing 'Unfinished Items'")

    # ══════════════════════════════════════════════════════════════════════
    # Regression: historical artifacts not modified
    # ══════════════════════════════════════════════════════════════════════

    def test_100_v116a_result_still_exists(self):
        """v116A result must still exist (not deleted)."""
        v116a = os.path.join(PROJECT_DIR, "results",
                             "market_radar_v116a_five_card_family_coverage_status_audit_result.json")
        self.assertTrue(os.path.exists(v116a), "v116A result must still exist")

    def test_101_v116b_result_still_exists(self):
        """v116B result must still exist (not deleted)."""
        v116b = os.path.join(PROJECT_DIR, "results",
                             "market_radar_v116b_multi_asset_fixture_e2e_gate_replay_result.json")
        self.assertTrue(os.path.exists(v116b), "v116B result must still exist")

    def test_102_v116c_result_still_exists(self):
        """v116C result must still exist (not deleted)."""
        v116c = os.path.join(PROJECT_DIR, "results",
                             "market_radar_v116c_remaining_three_card_families_fixture_e2e_batch_replay_result.json")
        self.assertTrue(os.path.exists(v116c), "v116C result must still exist")

    def test_103_v116e_result_still_exists(self):
        """v116E result must still exist (not deleted)."""
        v116e = os.path.join(PROJECT_DIR, "results",
                             "market_radar_v116e_real_free_api_multi_asset_tg_test_send_result.json")
        self.assertTrue(os.path.exists(v116e), "v116E result must still exist")

    # ══════════════════════════════════════════════════════════════════════
    # Helpers
    # ══════════════════════════════════════════════════════════════════════

    def _find_card(self, card_family: str) -> dict:
        """Find a coverage record by card_family."""
        for r in self.records:
            if r["card_family"] == card_family:
                return r
        self.fail(f"Card family '{card_family}' not found in coverage records")


if __name__ == "__main__":
    unittest.main(verbosity=2)
