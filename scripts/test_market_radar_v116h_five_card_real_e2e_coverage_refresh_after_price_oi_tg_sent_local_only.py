"""Market Radar v1.16-H — Five Card Real E2E Coverage Refresh Tests

Validates all v116H outputs meet the acceptance criteria defined in the task spec.

Tests cover:
  - All v116H output files exist
  - Five card families all present, no duplicates
  - multi_asset_market_sync correctly marked as real API + TG test sent
  - price_oi_volume_anomaly correctly marked as real API + TG test sent (NEW in v116H)
  - whale, liquidation, news_event NOT incorrectly marked as tg_test_sent: true
  - production_send_ready ALL false
  - Summary: fixture_e2e=5, real_api_tg=2, prod_ready=0
  - Evidence ledger has exactly 3 entries, all redacted
  - Evidence ledger contains no raw token/chat_id/message_id
  - Next candidate decision file exists with recommendation + rationale
  - Safety flags all correct (external_api_called=false, tg_sent=false, etc.)

Usage:
    python scripts/test_market_radar_v116h_five_card_real_e2e_coverage_refresh_after_price_oi_tg_sent_local_only.py
"""

import json
import os
import re
import sys
import unittest


PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

AUDIT_JSON = os.path.join(
    PROJECT_DIR, "results",
    "market_radar_v116h_five_card_real_e2e_coverage_audit_result.json"
)
LEDGER_JSONL = os.path.join(
    PROJECT_DIR, "results",
    "market_radar_v116h_tg_test_send_evidence_ledger.jsonl"
)
REPORT_MD = os.path.join(
    PROJECT_DIR, "runs", "market_radar",
    "v116h_five_card_real_e2e_coverage_audit.md"
)
REPORT_CSV = os.path.join(
    PROJECT_DIR, "runs", "market_radar",
    "v116h_five_card_real_e2e_coverage_audit.csv"
)
CANDIDATE_MD = os.path.join(
    PROJECT_DIR, "runs", "market_radar",
    "v116h_next_real_e2e_candidate_decision.md"
)
HANDOFF_MD = os.path.join(
    PROJECT_DIR, "runs", "market_radar",
    "v116h_local_only_handoff.md"
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
    "asset",
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


class TestV116HCoverageAuditAndLedger(unittest.TestCase):
    """Tests for v116H five-card real E2E coverage refresh + TG evidence ledger."""

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
        self.assertTrue(os.path.exists(AUDIT_JSON), f"Missing: {AUDIT_JSON}")

    def test_02_ledger_jsonl_exists(self):
        self.assertTrue(os.path.exists(LEDGER_JSONL), f"Missing: {LEDGER_JSONL}")

    def test_03_report_md_exists(self):
        self.assertTrue(os.path.exists(REPORT_MD), f"Missing: {REPORT_MD}")

    def test_04_report_csv_exists(self):
        self.assertTrue(os.path.exists(REPORT_CSV), f"Missing: {REPORT_CSV}")

    def test_05_candidate_md_exists(self):
        self.assertTrue(os.path.exists(CANDIDATE_MD), f"Missing: {CANDIDATE_MD}")

    def test_06_handoff_md_exists(self):
        self.assertTrue(os.path.exists(HANDOFF_MD), f"Missing: {HANDOFF_MD}")

    # ══════════════════════════════════════════════════════════════════════
    # Card family coverage tests
    # ══════════════════════════════════════════════════════════════════════

    def test_10_five_card_families_present(self):
        self.assertIsNotNone(self.audit, "Audit JSON not loaded")
        found = {r["card_family"] for r in self.records}
        expected = set(CANONICAL_FAMILIES)
        self.assertEqual(found, expected)

    def test_11_no_duplicate_card_families(self):
        names = [r["card_family"] for r in self.records]
        self.assertEqual(len(names), len(set(names)))

    def test_12_card_family_count_is_5(self):
        self.assertIsNotNone(self.audit, "Audit JSON not loaded")
        self.assertEqual(self.audit.get("card_family_count"), 5)

    def test_13_fixture_e2e_passed_count_is_5(self):
        self.assertIsNotNone(self.audit, "Audit JSON not loaded")
        self.assertEqual(self.audit.get("fixture_e2e_passed_count"), 5)

    def test_14_real_api_tg_test_sent_count_is_2(self):
        """v116H: 2 families (multi_asset_market_sync + price_oi_volume_anomaly) at real API + TG sent."""
        self.assertIsNotNone(self.audit, "Audit JSON not loaded")
        self.assertEqual(self.audit.get("real_api_tg_test_sent_count"), 2)

    def test_15_production_send_ready_count_is_0(self):
        self.assertIsNotNone(self.audit, "Audit JSON not loaded")
        self.assertEqual(self.audit.get("production_send_ready_count"), 0)

    # ══════════════════════════════════════════════════════════════════════
    # multi_asset_market_sync specific tests
    # ══════════════════════════════════════════════════════════════════════

    def test_20_mams_real_external_api_called_true(self):
        mams = self._find_card("multi_asset_market_sync")
        self.assertTrue(mams["real_external_api_called"])

    def test_21_mams_real_card_generated_true(self):
        mams = self._find_card("multi_asset_market_sync")
        self.assertTrue(mams["real_card_generated"])

    def test_22_mams_quality_gate_passed_true(self):
        mams = self._find_card("multi_asset_market_sync")
        self.assertTrue(mams["quality_gate_passed"])

    def test_23_mams_send_readiness_passed_true(self):
        mams = self._find_card("multi_asset_market_sync")
        self.assertTrue(mams["send_readiness_passed"])

    def test_24_mams_tg_test_sent_true(self):
        mams = self._find_card("multi_asset_market_sync")
        self.assertTrue(mams["tg_test_sent"])

    def test_25_mams_tg_test_group_ready_true(self):
        mams = self._find_card("multi_asset_market_sync")
        self.assertTrue(mams["tg_test_group_ready"])

    def test_26_mams_real_e2e_status_correct(self):
        mams = self._find_card("multi_asset_market_sync")
        self.assertEqual(mams["real_e2e_status"], "real_free_api_tg_test_sent")

    def test_27_mams_production_send_ready_false(self):
        mams = self._find_card("multi_asset_market_sync")
        self.assertFalse(mams["production_send_ready"])

    # ══════════════════════════════════════════════════════════════════════
    # price_oi_volume_anomaly specific tests (NEW in v116H)
    # ══════════════════════════════════════════════════════════════════════

    def test_30_pova_real_external_api_called_true(self):
        """v116H: POVA must now have real_external_api_called: true (v116G completed)."""
        pova = self._find_card("price_oi_volume_anomaly")
        self.assertTrue(pova["real_external_api_called"])

    def test_31_pova_real_card_generated_true(self):
        pova = self._find_card("price_oi_volume_anomaly")
        self.assertTrue(pova["real_card_generated"])

    def test_32_pova_quality_gate_passed_true(self):
        pova = self._find_card("price_oi_volume_anomaly")
        self.assertTrue(pova["quality_gate_passed"])

    def test_33_pova_send_readiness_passed_true(self):
        pova = self._find_card("price_oi_volume_anomaly")
        self.assertTrue(pova["send_readiness_passed"])

    def test_34_pova_tg_test_sent_true(self):
        """v116H: POVA must now have tg_test_sent: true (v116G completed)."""
        pova = self._find_card("price_oi_volume_anomaly")
        self.assertTrue(pova["tg_test_sent"])

    def test_35_pova_tg_test_group_ready_true(self):
        pova = self._find_card("price_oi_volume_anomaly")
        self.assertTrue(pova["tg_test_group_ready"])

    def test_36_pova_real_e2e_status_correct(self):
        """v116H: POVA real_e2e_status must now be real_free_api_tg_test_sent."""
        pova = self._find_card("price_oi_volume_anomaly")
        self.assertEqual(pova["real_e2e_status"], "real_free_api_tg_test_sent")

    def test_37_pova_production_send_ready_false(self):
        pova = self._find_card("price_oi_volume_anomaly")
        self.assertFalse(pova["production_send_ready"])

    # ══════════════════════════════════════════════════════════════════════
    # Other three card families must NOT be tg_test_sent
    # ══════════════════════════════════════════════════════════════════════

    def test_40_whale_not_tg_test_sent(self):
        wpa = self._find_card("whale_position_alert")
        self.assertFalse(wpa["tg_test_sent"])

    def test_41_lipr_not_tg_test_sent(self):
        lipr = self._find_card("liquidation_pressure")
        self.assertFalse(lipr["tg_test_sent"])

    def test_42_nemi_not_tg_test_sent(self):
        nemi = self._find_card("news_event_market_impact")
        self.assertFalse(nemi["tg_test_sent"])

    # ══════════════════════════════════════════════════════════════════════
    # Status-specific tests for remaining 3 families
    # ══════════════════════════════════════════════════════════════════════

    def test_43_whale_status_blocked_manual_evidence(self):
        wpa = self._find_card("whale_position_alert")
        self.assertEqual(wpa["real_e2e_status"], "blocked_manual_evidence")

    def test_44_lipr_status_fixture_e2e_passed_real_not_started(self):
        lipr = self._find_card("liquidation_pressure")
        self.assertEqual(lipr["real_e2e_status"], "fixture_e2e_passed_real_not_started")

    def test_45_nemi_status_fixture_e2e_passed_real_not_started(self):
        nemi = self._find_card("news_event_market_impact")
        self.assertEqual(nemi["real_e2e_status"], "fixture_e2e_passed_real_not_started")

    # ══════════════════════════════════════════════════════════════════════
    # All production_send_ready must be False
    # ══════════════════════════════════════════════════════════════════════

    def test_50_all_production_send_ready_false(self):
        for r in self.records:
            self.assertFalse(r["production_send_ready"],
                             f"{r['card_family']} production_send_ready must be False")

    # ══════════════════════════════════════════════════════════════════════
    # Safety flag tests
    # ══════════════════════════════════════════════════════════════════════

    def test_60_external_api_called_this_run_false(self):
        self.assertIsNotNone(self.audit, "Audit JSON not loaded")
        self.assertFalse(self.audit.get("external_api_called_this_run", True))

    def test_61_tg_sent_this_run_false(self):
        self.assertIsNotNone(self.audit, "Audit JSON not loaded")
        self.assertFalse(self.audit.get("tg_sent_this_run", True))

    def test_62_prod_state_write_false(self):
        self.assertIsNotNone(self.audit, "Audit JSON not loaded")
        self.assertFalse(self.audit.get("prod_state_write", True))

    def test_63_ai_model_called_false(self):
        self.assertIsNotNone(self.audit, "Audit JSON not loaded")
        self.assertFalse(self.audit.get("ai_model_called", True))

    def test_64_daemon_or_loop_started_false(self):
        self.assertIsNotNone(self.audit, "Audit JSON not loaded")
        self.assertFalse(self.audit.get("daemon_or_loop_started", True))

    def test_65_files_deleted_false(self):
        self.assertIsNotNone(self.audit, "Audit JSON not loaded")
        self.assertFalse(self.audit.get("files_deleted", True))

    def test_66_historical_artifacts_modified_false(self):
        self.assertIsNotNone(self.audit, "Audit JSON not loaded")
        self.assertFalse(self.audit.get("historical_artifacts_modified", True))

    def test_67_credentials_read_false(self):
        self.assertIsNotNone(self.audit, "Audit JSON not loaded")
        self.assertFalse(self.audit.get("credentials_read", True))

    # ══════════════════════════════════════════════════════════════════════
    # Coverage record field tests
    # ══════════════════════════════════════════════════════════════════════

    def test_70_all_required_coverage_fields_present(self):
        for r in self.records:
            for field in REQUIRED_COVERAGE_FIELDS:
                self.assertIn(field, r,
                              f"Card '{r.get('card_family', '?')}' missing field: {field}")

    def test_71_whale_blocked_reason_not_empty(self):
        wpa = self._find_card("whale_position_alert")
        self.assertIsNotNone(wpa.get("current_blocker"))
        self.assertTrue(len(wpa["current_blocker"]) > 0)

    def test_72_mams_blocker_is_none(self):
        mams = self._find_card("multi_asset_market_sync")
        self.assertIsNone(mams.get("current_blocker"))

    def test_73_pova_blocker_is_none(self):
        """v116H: POVA should no longer have a blocker."""
        pova = self._find_card("price_oi_volume_anomaly")
        self.assertIsNone(pova.get("current_blocker"))

    # ══════════════════════════════════════════════════════════════════════
    # Fixture E2E vs Real E2E distinction
    # ══════════════════════════════════════════════════════════════════════

    def test_75_no_fixture_mistaken_for_real_e2e(self):
        for r in self.records:
            if not r["real_external_api_called"]:
                self.assertNotIn(r["real_e2e_status"],
                                 ["real_free_api_tg_test_sent", "real_e2e_passed"],
                                 f"{r['card_family']} has real_external_api_called=False "
                                 f"but real_e2e_status={r['real_e2e_status']}")

    def test_76_all_five_fixture_e2e_passed(self):
        for r in self.records:
            self.assertTrue(r["fixture_e2e_passed"],
                            f"{r['card_family']} fixture_e2e_passed must be True")

    # ══════════════════════════════════════════════════════════════════════
    # TG Evidence Ledger tests
    # ══════════════════════════════════════════════════════════════════════

    def test_80_ledger_has_exactly_3_entries(self):
        """v116H: must have exactly 3 entries (1 v116E + 2 v116G)."""
        self.assertEqual(len(self.ledger), 3,
                         f"Ledger must have 3 entries, got {len(self.ledger)}")

    def test_81_all_ledger_fields_present(self):
        for entry in self.ledger:
            for field in REQUIRED_LEDGER_FIELDS:
                self.assertIn(field, entry,
                              f"Ledger entry missing field: {field}")

    def test_82_ledger_target_type_is_test_group(self):
        for entry in self.ledger:
            self.assertEqual(entry.get("target_type"), "test_group")

    def test_83_ledger_one_shot_true(self):
        for entry in self.ledger:
            self.assertTrue(entry.get("one_shot"))

    def test_84_ledger_production_send_false(self):
        for entry in self.ledger:
            self.assertFalse(entry.get("production_send"))

    def test_85_ledger_credentials_printed_false(self):
        for entry in self.ledger:
            self.assertFalse(entry.get("credentials_printed"))

    def test_86_ledger_raw_secret_present_false(self):
        for entry in self.ledger:
            self.assertFalse(entry.get("raw_secret_present_in_outputs"))

    def test_87_no_raw_token_in_ledger(self):
        """No ledger field should contain an unredacted token/chat_id/message_id."""
        token_pattern = re.compile(r'\d{8,12}:[A-Za-z0-9_-]{30,}')

        for entry in self.ledger:
            entry_str = json.dumps(entry)
            self.assertIsNone(token_pattern.search(entry_str),
                              "Ledger contains unredacted token-like value")
            for field in ["message_id_redacted", "token_fingerprint_redacted", "chat_id_fingerprint_redacted"]:
                val = entry.get(field, "")
                self.assertTrue(val.startswith("sha256:") or val == "",
                                f"Field {field} not properly redacted: '{val[:40]}...'")

    def test_88_ledger_message_id_present_true(self):
        for entry in self.ledger:
            self.assertTrue(entry.get("message_id_present"))

    def test_89_ledger_card_families_correct(self):
        """Entry 1: multi_asset_market_sync, Entries 2-3: price_oi_volume_anomaly."""
        families = [e["card_family"] for e in self.ledger]
        self.assertEqual(families[0], "multi_asset_market_sync")
        self.assertEqual(families[1], "price_oi_volume_anomaly")
        self.assertEqual(families[2], "price_oi_volume_anomaly")

    def test_90_ledger_pova_has_assets(self):
        """POVA entries must have asset field set (ETH, SOL)."""
        pova_entries = [e for e in self.ledger if e["card_family"] == "price_oi_volume_anomaly"]
        self.assertEqual(len(pova_entries), 2)
        assets = {e["asset"] for e in pova_entries}
        self.assertEqual(assets, {"ETH", "SOL"})

    # ══════════════════════════════════════════════════════════════════════
    # Next candidate decision tests
    # ══════════════════════════════════════════════════════════════════════

    def test_95_candidate_md_contains_recommendation(self):
        self.assertIn("Recommend", self.candidate_md)

    def test_96_candidate_md_contains_rationale(self):
        self.assertIn("Rationale", self.candidate_md)

    def test_97_candidate_md_mentions_risk(self):
        self.assertIn("Risk", self.candidate_md)

    def test_98_candidate_md_mentions_liquidation_pressure(self):
        """Top candidate should be liquidation_pressure."""
        self.assertIn("liquidation_pressure", self.candidate_md.lower())

    def test_99_candidate_md_mentions_whale_blocked(self):
        self.assertIn("whale_position_alert", self.candidate_md.lower())

    def test_100_candidate_md_has_scoring_matrix(self):
        self.assertIn("Scoring Matrix", self.candidate_md)

    def test_101_candidate_md_mentions_pova_complete(self):
        """Should mention that price_oi_volume_anomaly is already done."""
        self.assertIn("price_oi_volume_anomaly", self.candidate_md.lower())

    # ══════════════════════════════════════════════════════════════════════
    # Markdown report content tests
    # ══════════════════════════════════════════════════════════════════════

    def test_105_md_contains_executive_summary(self):
        self.assertIn("Executive Summary", self.report_md)

    def test_106_md_contains_coverage_matrix(self):
        self.assertIn("Coverage Matrix", self.report_md)

    def test_107_md_contains_mams_highlight(self):
        self.assertIn("multi_asset_market_sync", self.report_md)

    def test_108_md_contains_pova_highlight(self):
        """v116H report must mention price_oi_volume_anomaly as real API + TG sent."""
        self.assertIn("price_oi_volume_anomaly", self.report_md)

    def test_109_md_contains_safety_constraints(self):
        self.assertIn("Safety Constraints", self.report_md)

    def test_110_md_states_2_of_5_real_api_tg_sent(self):
        """Report must state 2/5 at real API + TG sent."""
        self.assertIn("2/5", self.report_md)

    # ══════════════════════════════════════════════════════════════════════
    # CSV tests
    # ══════════════════════════════════════════════════════════════════════

    def test_115_csv_has_correct_columns(self):
        import csv
        with open(REPORT_CSV, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            fieldnames = reader.fieldnames
            self.assertIsNotNone(fieldnames)
            for col in ["card_family", "real_external_api_called", "tg_test_sent",
                        "production_send_ready", "real_e2e_status"]:
                self.assertIn(col, fieldnames)

    def test_116_csv_row_count_is_5(self):
        import csv
        with open(REPORT_CSV, "r", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        self.assertEqual(len(rows), 5)

    # ══════════════════════════════════════════════════════════════════════
    # Handoff tests
    # ══════════════════════════════════════════════════════════════════════

    def test_120_handoff_contains_coverage_summary(self):
        self.assertIn("Coverage Summary", self.handoff_md)

    def test_121_handoff_contains_safety_confirmation(self):
        self.assertIn("Safety Confirmation", self.handoff_md)

    def test_122_handoff_contains_unfinished_risks(self):
        self.assertIn("Unfinished Items", self.handoff_md)

    # ══════════════════════════════════════════════════════════════════════
    # Regression: historical artifacts not modified
    # ══════════════════════════════════════════════════════════════════════

    def test_130_v116a_result_still_exists(self):
        p = os.path.join(PROJECT_DIR, "results",
                         "market_radar_v116a_five_card_family_coverage_status_audit_result.json")
        self.assertTrue(os.path.exists(p), "v116A result must still exist")

    def test_131_v116c_result_still_exists(self):
        p = os.path.join(PROJECT_DIR, "results",
                         "market_radar_v116c_remaining_three_card_families_fixture_e2e_batch_replay_result.json")
        self.assertTrue(os.path.exists(p), "v116C result must still exist")

    def test_132_v116e_result_still_exists(self):
        p = os.path.join(PROJECT_DIR, "results",
                         "market_radar_v116e_real_free_api_multi_asset_tg_test_send_result.json")
        self.assertTrue(os.path.exists(p), "v116E result must still exist")

    def test_133_v116g_result_still_exists(self):
        p = os.path.join(PROJECT_DIR, "results",
                         "market_radar_v116g_price_oi_volume_anomaly_tg_test_send_result.json")
        self.assertTrue(os.path.exists(p), "v116G result must still exist")

    # ══════════════════════════════════════════════════════════════════════
    # Helpers
    # ══════════════════════════════════════════════════════════════════════

    def _find_card(self, card_family: str) -> dict:
        for r in self.records:
            if r["card_family"] == card_family:
                return r
        self.fail(f"Card family '{card_family}' not found in coverage records")


if __name__ == "__main__":
    unittest.main(verbosity=2)
