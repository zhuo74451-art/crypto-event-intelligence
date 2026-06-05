"""Market Radar v1.16-K — Five Card Real E2E Coverage Refresh Tests

Validates all v116K outputs meet the acceptance criteria defined in the task spec.

Tests cover:
  - All v116K output files exist
  - Five card families all present, no duplicates
  - multi_asset_market_sync marked as real API + TG test sent
  - price_oi_volume_anomaly marked as real API + TG test sent
  - news_event_market_impact marked as real public source + TG test sent
  - liquidation_pressure marked as real API attempted but gate blocked, tg_test_sent: false
  - whale_position_alert marked as manual evidence blocked, tg_test_sent: false
  - Summary: fixture_e2e=5, real_api_tg=3, real_api_blocked=1, manual_blocked=1, prod_ready=0
  - Evidence ledger has exactly 5 entries, all redacted
  - Evidence ledger contains no raw token/chat_id/message_id
  - Next candidate decision file recommends v116L milestone packaging
  - Safety flags all correct

Usage:
    python scripts/test_market_radar_v116k_five_card_real_e2e_coverage_refresh_after_news_event_tg_sent_local_only.py
"""

import json
import os
import re
import sys
import unittest


PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

AUDIT_JSON = os.path.join(
    PROJECT_DIR, "results",
    "market_radar_v116k_five_card_real_e2e_coverage_audit_result.json"
)
LEDGER_JSONL = os.path.join(
    PROJECT_DIR, "results",
    "market_radar_v116k_tg_test_send_evidence_ledger.jsonl"
)
REPORT_MD = os.path.join(
    PROJECT_DIR, "runs", "market_radar",
    "v116k_five_card_real_e2e_coverage_audit.md"
)
REPORT_CSV = os.path.join(
    PROJECT_DIR, "runs", "market_radar",
    "v116k_five_card_real_e2e_coverage_audit.csv"
)
CANDIDATE_MD = os.path.join(
    PROJECT_DIR, "runs", "market_radar",
    "v116k_next_real_e2e_candidate_decision.md"
)
HANDOFF_MD = os.path.join(
    PROJECT_DIR, "runs", "market_radar",
    "v116k_local_only_handoff.md"
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
    "real_public_source_called",
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


class TestV116KCoverageAuditAndLedger(unittest.TestCase):
    """Tests for v116K five-card real E2E coverage refresh + TG evidence ledger."""

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

    def test_14_real_api_or_public_source_tg_sent_count_is_3(self):
        """v116K: 3 families at real API/public source + TG test sent."""
        self.assertIsNotNone(self.audit, "Audit JSON not loaded")
        self.assertEqual(self.audit.get("real_api_or_public_source_tg_test_sent_count"), 3)

    def test_15_real_api_attempted_but_gate_blocked_count_is_1(self):
        self.assertIsNotNone(self.audit, "Audit JSON not loaded")
        self.assertEqual(self.audit.get("real_api_attempted_but_gate_blocked_count"), 1)

    def test_16_manual_evidence_blocked_count_is_1(self):
        self.assertIsNotNone(self.audit, "Audit JSON not loaded")
        self.assertEqual(self.audit.get("manual_evidence_blocked_count"), 1)

    def test_17_production_send_ready_count_is_0(self):
        self.assertIsNotNone(self.audit, "Audit JSON not loaded")
        self.assertEqual(self.audit.get("production_send_ready_count"), 0)

    # ══════════════════════════════════════════════════════════════════════
    # multi_asset_market_sync specific tests (unchanged from v116H)
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
    # price_oi_volume_anomaly specific tests (unchanged from v116H)
    # ══════════════════════════════════════════════════════════════════════

    def test_30_pova_real_external_api_called_true(self):
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
        pova = self._find_card("price_oi_volume_anomaly")
        self.assertTrue(pova["tg_test_sent"])

    def test_35_pova_tg_test_group_ready_true(self):
        pova = self._find_card("price_oi_volume_anomaly")
        self.assertTrue(pova["tg_test_group_ready"])

    def test_36_pova_real_e2e_status_correct(self):
        pova = self._find_card("price_oi_volume_anomaly")
        self.assertEqual(pova["real_e2e_status"], "real_free_api_tg_test_sent")

    def test_37_pova_production_send_ready_false(self):
        pova = self._find_card("price_oi_volume_anomaly")
        self.assertFalse(pova["production_send_ready"])

    # ══════════════════════════════════════════════════════════════════════
    # news_event_market_impact specific tests (NEW in v116K)
    # ══════════════════════════════════════════════════════════════════════

    def test_40_nemi_real_external_api_called_true(self):
        nemi = self._find_card("news_event_market_impact")
        self.assertTrue(nemi["real_external_api_called"])

    def test_41_nemi_real_public_source_called_true(self):
        nemi = self._find_card("news_event_market_impact")
        self.assertTrue(nemi.get("real_public_source_called", False))

    def test_42_nemi_real_card_generated_true(self):
        nemi = self._find_card("news_event_market_impact")
        self.assertTrue(nemi["real_card_generated"])

    def test_43_nemi_quality_gate_passed_true(self):
        nemi = self._find_card("news_event_market_impact")
        self.assertTrue(nemi["quality_gate_passed"])

    def test_44_nemi_send_readiness_passed_true(self):
        nemi = self._find_card("news_event_market_impact")
        self.assertTrue(nemi["send_readiness_passed"])

    def test_45_nemi_tg_test_sent_true(self):
        nemi = self._find_card("news_event_market_impact")
        self.assertTrue(nemi["tg_test_sent"])

    def test_46_nemi_tg_test_group_ready_true(self):
        nemi = self._find_card("news_event_market_impact")
        self.assertTrue(nemi["tg_test_group_ready"])

    def test_47_nemi_real_e2e_status_correct(self):
        nemi = self._find_card("news_event_market_impact")
        self.assertEqual(nemi["real_e2e_status"], "real_free_public_source_tg_test_sent")

    def test_48_nemi_production_send_ready_false(self):
        nemi = self._find_card("news_event_market_impact")
        self.assertFalse(nemi["production_send_ready"])

    def test_49_nemi_risk_disclaimer_mentioned(self):
        """NEMI next_action or evidence must reference the risk disclaimer."""
        nemi = self._find_card("news_event_market_impact")
        texts = [str(nemi.get("next_action", "")), str(nemi.get("evidence_sources", []))]
        combined = " ".join(texts)
        has_disclaimer = "风险" in combined or "不构成因果" in combined or "disclaimer" in combined.lower()
        self.assertTrue(has_disclaimer, "NEMI should reference risk disclaimer")

    # ══════════════════════════════════════════════════════════════════════
    # liquidation_pressure specific tests (NEW state in v116K)
    # ══════════════════════════════════════════════════════════════════════

    def test_50_lipr_real_external_api_called_true(self):
        """v116K: LIPR must have real_external_api_called: true (v116I completed)."""
        lipr = self._find_card("liquidation_pressure")
        self.assertTrue(lipr["real_external_api_called"])

    def test_51_lipr_real_card_generated_false(self):
        """v116K: LIPR cards generated but gate blocked — real_card_generated: false."""
        lipr = self._find_card("liquidation_pressure")
        self.assertFalse(lipr["real_card_generated"])

    def test_52_lipr_quality_gate_passed_false(self):
        lipr = self._find_card("liquidation_pressure")
        self.assertFalse(lipr["quality_gate_passed"])

    def test_53_lipr_send_readiness_passed_false(self):
        lipr = self._find_card("liquidation_pressure")
        self.assertFalse(lipr["send_readiness_passed"])

    def test_54_lipr_tg_test_sent_false(self):
        """CRITICAL: liquidation_pressure must NOT be tg_test_sent: true."""
        lipr = self._find_card("liquidation_pressure")
        self.assertFalse(lipr["tg_test_sent"],
                         "liquidation_pressure MUST NOT be marked tg_test_sent: true")

    def test_55_lipr_tg_test_group_ready_false(self):
        lipr = self._find_card("liquidation_pressure")
        self.assertFalse(lipr["tg_test_group_ready"])

    def test_56_lipr_real_e2e_status_correct(self):
        lipr = self._find_card("liquidation_pressure")
        self.assertEqual(lipr["real_e2e_status"], "blocked_gate_not_passed")

    def test_57_lipr_production_send_ready_false(self):
        lipr = self._find_card("liquidation_pressure")
        self.assertFalse(lipr["production_send_ready"])

    def test_58_lipr_blocker_mentions_calm_market(self):
        lipr = self._find_card("liquidation_pressure")
        blocker = str(lipr.get("current_blocker", "")).lower()
        self.assertTrue(
            any(kw in blocker for kw in ["calm", "threshold", "oi", "gate", "blocked", "admission"]),
            f"LIPR blocker should mention calm market / gate: '{blocker[:100]}...'"
        )

    # ══════════════════════════════════════════════════════════════════════
    # whale_position_alert specific tests (unchanged)
    # ══════════════════════════════════════════════════════════════════════

    def test_60_wpa_not_tg_test_sent(self):
        wpa = self._find_card("whale_position_alert")
        self.assertFalse(wpa["tg_test_sent"],
                         "whale_position_alert MUST NOT be marked tg_test_sent: true")

    def test_61_wpa_real_external_api_called_false(self):
        wpa = self._find_card("whale_position_alert")
        self.assertFalse(wpa["real_external_api_called"])

    def test_62_wpa_status_blocked_manual_evidence(self):
        wpa = self._find_card("whale_position_alert")
        self.assertEqual(wpa["real_e2e_status"], "blocked_manual_evidence")

    def test_63_wpa_production_send_ready_false(self):
        wpa = self._find_card("whale_position_alert")
        self.assertFalse(wpa["production_send_ready"])

    # ══════════════════════════════════════════════════════════════════════
    # All production_send_ready must be False
    # ══════════════════════════════════════════════════════════════════════

    def test_70_all_production_send_ready_false(self):
        for r in self.records:
            self.assertFalse(r["production_send_ready"],
                             f"{r['card_family']} production_send_ready must be False")

    # ══════════════════════════════════════════════════════════════════════
    # Safety flag tests
    # ══════════════════════════════════════════════════════════════════════

    def test_80_external_api_called_this_run_false(self):
        self.assertIsNotNone(self.audit, "Audit JSON not loaded")
        self.assertFalse(self.audit.get("external_api_called_this_run", True))

    def test_81_public_source_called_this_run_false(self):
        self.assertIsNotNone(self.audit, "Audit JSON not loaded")
        self.assertFalse(self.audit.get("public_source_called_this_run", True))

    def test_82_tg_sent_this_run_false(self):
        self.assertIsNotNone(self.audit, "Audit JSON not loaded")
        self.assertFalse(self.audit.get("tg_sent_this_run", True))

    def test_83_prod_state_write_false(self):
        self.assertIsNotNone(self.audit, "Audit JSON not loaded")
        self.assertFalse(self.audit.get("prod_state_write", True))

    def test_84_ai_model_called_false(self):
        self.assertIsNotNone(self.audit, "Audit JSON not loaded")
        self.assertFalse(self.audit.get("ai_model_called", True))

    def test_85_daemon_or_loop_started_false(self):
        self.assertIsNotNone(self.audit, "Audit JSON not loaded")
        self.assertFalse(self.audit.get("daemon_or_loop_started", True))

    def test_86_files_deleted_false(self):
        self.assertIsNotNone(self.audit, "Audit JSON not loaded")
        self.assertFalse(self.audit.get("files_deleted", True))

    def test_87_historical_artifacts_modified_false(self):
        self.assertIsNotNone(self.audit, "Audit JSON not loaded")
        self.assertFalse(self.audit.get("historical_artifacts_modified", True))

    # ══════════════════════════════════════════════════════════════════════
    # Coverage record field tests
    # ══════════════════════════════════════════════════════════════════════

    def test_90_all_required_coverage_fields_present(self):
        for r in self.records:
            for field in REQUIRED_COVERAGE_FIELDS:
                self.assertIn(field, r,
                              f"Card '{r.get('card_family', '?')}' missing field: {field}")

    def test_91_wpa_blocked_reason_not_empty(self):
        wpa = self._find_card("whale_position_alert")
        self.assertIsNotNone(wpa.get("current_blocker"))
        self.assertTrue(len(wpa["current_blocker"]) > 0)

    def test_92_mams_blocker_is_none(self):
        mams = self._find_card("multi_asset_market_sync")
        self.assertIsNone(mams.get("current_blocker"))

    def test_93_pova_blocker_is_none(self):
        pova = self._find_card("price_oi_volume_anomaly")
        self.assertIsNone(pova.get("current_blocker"))

    def test_94_nemi_blocker_is_none(self):
        """v116K: NEMI should no longer have a blocker."""
        nemi = self._find_card("news_event_market_impact")
        self.assertIsNone(nemi.get("current_blocker"))

    def test_95_lipr_blocker_not_none(self):
        """v116K: LIPR should have a blocker (calm market / gate)."""
        lipr = self._find_card("liquidation_pressure")
        self.assertIsNotNone(lipr.get("current_blocker"))
        self.assertTrue(len(lipr["current_blocker"]) > 0)

    # ══════════════════════════════════════════════════════════════════════
    # Fixture E2E vs Real E2E distinction
    # ══════════════════════════════════════════════════════════════════════

    def test_100_no_fixture_mistaken_for_real_e2e(self):
        for r in self.records:
            if not r["real_external_api_called"]:
                self.assertNotIn(r["real_e2e_status"],
                                 ["real_free_api_tg_test_sent",
                                  "real_free_public_source_tg_test_sent",
                                  "real_e2e_passed"],
                                 f"{r['card_family']} has real_external_api_called=False "
                                 f"but real_e2e_status={r['real_e2e_status']}")

    def test_101_all_five_fixture_e2e_passed(self):
        for r in self.records:
            self.assertTrue(r["fixture_e2e_passed"],
                            f"{r['card_family']} fixture_e2e_passed must be True")

    def test_102_lipr_not_mistaken_for_real_tg_sent(self):
        """Liquidation must not be mistakenly classified as TG sent."""
        lipr = self._find_card("liquidation_pressure")
        self.assertNotIn(lipr["real_e2e_status"],
                         ["real_free_api_tg_test_sent", "real_free_public_source_tg_test_sent"],
                         "liquidation_pressure MUST NOT have real E2E TG sent status")

    def test_103_whale_not_mistaken_for_real_e2e(self):
        """Whale must not be mistakenly classified as real E2E."""
        wpa = self._find_card("whale_position_alert")
        self.assertNotIn(wpa["real_e2e_status"],
                         ["real_free_api_tg_test_sent", "real_free_public_source_tg_test_sent"],
                         "whale_position_alert MUST NOT have real E2E TG sent status")

    # ══════════════════════════════════════════════════════════════════════
    # TG Evidence Ledger tests
    # ══════════════════════════════════════════════════════════════════════

    def test_110_ledger_has_exactly_5_entries(self):
        """v116K: must have exactly 5 entries (1 v116E + 2 v116G + 2 v116J)."""
        self.assertEqual(len(self.ledger), 5,
                         f"Ledger must have 5 entries, got {len(self.ledger)}")

    def test_111_all_ledger_fields_present(self):
        for entry in self.ledger:
            for field in REQUIRED_LEDGER_FIELDS:
                self.assertIn(field, entry,
                              f"Ledger entry missing field: {field}")

    def test_112_ledger_target_type_is_test_group(self):
        for entry in self.ledger:
            self.assertEqual(entry.get("target_type"), "test_group")

    def test_113_ledger_one_shot_true(self):
        for entry in self.ledger:
            self.assertTrue(entry.get("one_shot"))

    def test_114_ledger_tg_sent_true(self):
        for entry in self.ledger:
            self.assertTrue(entry.get("tg_sent"))

    def test_115_ledger_production_send_false(self):
        for entry in self.ledger:
            self.assertFalse(entry.get("production_send"))

    def test_116_ledger_credentials_printed_false(self):
        for entry in self.ledger:
            self.assertFalse(entry.get("credentials_printed"))

    def test_117_ledger_raw_secret_present_false(self):
        for entry in self.ledger:
            self.assertFalse(entry.get("raw_secret_present_in_outputs"))

    def test_118_ledger_message_id_present_true(self):
        for entry in self.ledger:
            self.assertTrue(entry.get("message_id_present"))

    def test_119_no_raw_token_in_ledger(self):
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

    def test_120_ledger_card_families_correct(self):
        """Entry 1: MAMS, Entries 2-3: POVA, Entries 4-5: NEMI."""
        families = [e["card_family"] for e in self.ledger]
        self.assertEqual(families[0], "multi_asset_market_sync", "Entry 1 must be multi_asset_market_sync")
        self.assertEqual(families[1], "price_oi_volume_anomaly", "Entry 2 must be price_oi_volume_anomaly")
        self.assertEqual(families[2], "price_oi_volume_anomaly", "Entry 3 must be price_oi_volume_anomaly")
        self.assertEqual(families[3], "news_event_market_impact", "Entry 4 must be news_event_market_impact")
        self.assertEqual(families[4], "news_event_market_impact", "Entry 5 must be news_event_market_impact")

    def test_121_ledger_pova_has_assets(self):
        """POVA entries must have asset field set (ETH, SOL)."""
        pova_entries = [e for e in self.ledger if e["card_family"] == "price_oi_volume_anomaly"]
        self.assertEqual(len(pova_entries), 2)
        assets = {e["asset"] for e in pova_entries}
        self.assertEqual(assets, {"ETH", "SOL"})

    def test_122_ledger_nemi_asset_is_none(self):
        """NEMI entries should not have specific assets."""
        nemi_entries = [e for e in self.ledger if e["card_family"] == "news_event_market_impact"]
        self.assertEqual(len(nemi_entries), 2)
        for entry in nemi_entries:
            self.assertIsNone(entry.get("asset"))

    # ══════════════════════════════════════════════════════════════════════
    # Next candidate decision tests
    # ══════════════════════════════════════════════════════════════════════

    def test_130_candidate_md_contains_recommendation(self):
        self.assertIn("Recommend", self.candidate_md)

    def test_131_candidate_md_contains_rationale(self):
        self.assertIn("Reasoning", self.candidate_md)

    def test_132_candidate_md_contains_risks(self):
        self.assertIn("Risk", self.candidate_md)

    def test_133_candidate_md_recommends_milestone_packaging(self):
        """v116K MUST recommend v116L milestone packaging, NOT force liquidation or bypass whale."""
        self.assertIn("v116L", self.candidate_md,
                      "Candidate decision must recommend v116L milestone packaging")

    def test_134_candidate_md_mentions_liquidation_as_future_rerun(self):
        self.assertTrue(
            any(kw in self.candidate_md.lower() for kw in
                ["future", "volatility", "rerun", "event-triggered", "calm market"]),
            "Candidate should mention liquidation as future volatility rerun"
        )

    def test_135_candidate_md_mentions_whale_manual_evidence(self):
        self.assertTrue(
            any(kw in self.candidate_md.lower() for kw in
                ["whale", "manual evidence", "manual_evidence"]),
            "Candidate must mention whale_position_alert and manual evidence"
        )

    def test_136_candidate_md_does_not_recommend_lowering_gate(self):
        """Must NOT recommend lowering liquidation gate threshold.
        The candidate may mention "not lowering" as an anti-recommendation,
        but must NOT contain a positive recommendation to lower the gate."""
        # Check that "lower threshold" does not appear as a positive recommendation
        # (it should only appear in context of "NOT lower")
        lower_text = self.candidate_md.lower()
        self.assertNotIn("lower threshold", lower_text)
        # Chinese: must not positively recommend lowering. "降低阈值" is acceptable
        # ONLY when preceded by negation like 不应/不要/不
        # Since the content legitimately says "不应降低阈值" (do NOT lower),
        # we verify there's no un-negated "降低阈值" recommendation.
        # Simple check: ensure every occurrence of "降低" is in a negative context
        import re
        # Find all sentences containing "降低" and ensure each is negated
        for line in self.candidate_md.split("\n"):
            if "降低" in line:
                # Must be in a "NOT lower" context
                has_negation = any(neg in line for neg in ["不应", "不要", "不", "NOT", "not", "避免"])
                self.assertTrue(has_negation,
                    f"Line with '降低' must be negated (do NOT recommend lowering): '{line[:120]}...'")

    def test_137_candidate_md_mentions_3_cards_sent(self):
        self.assertIn("3/5", self.candidate_md)

    def test_138_candidate_md_has_three_directions(self):
        """Should compare all three directions: liquidation, whale, packaging."""
        directions_found = 0
        if "liquidation_pressure" in self.candidate_md.lower():
            directions_found += 1
        if "whale" in self.candidate_md.lower() or "manual evidence" in self.candidate_md.lower():
            directions_found += 1
        if "milestone" in self.candidate_md.lower() or "packag" in self.candidate_md.lower():
            directions_found += 1
        self.assertGreaterEqual(directions_found, 3,
                                "Candidate decision should compare 3 directions")

    # ══════════════════════════════════════════════════════════════════════
    # Markdown report content tests
    # ══════════════════════════════════════════════════════════════════════

    def test_140_md_contains_executive_summary(self):
        self.assertIn("Executive Summary", self.report_md)

    def test_141_md_contains_coverage_matrix(self):
        self.assertIn("Coverage Matrix", self.report_md)

    def test_142_md_contains_mams_highlight(self):
        self.assertIn("multi_asset_market_sync", self.report_md)

    def test_143_md_contains_pova_highlight(self):
        self.assertIn("price_oi_volume_anomaly", self.report_md)

    def test_144_md_contains_nemi_highlight(self):
        """v116K report must mention news_event_market_impact."""
        self.assertIn("news_event_market_impact", self.report_md)

    def test_145_md_contains_lipr_gate_blocked_detail(self):
        """v116K report must describe liquidation gate blocked status."""
        self.assertIn("liquidation", self.report_md.lower())

    def test_146_md_states_3_of_5_real_e2e_tg_sent(self):
        """Report must state 3/5 at real API/public source + TG test sent."""
        self.assertIn("3/5", self.report_md)

    def test_147_md_contains_safety_constraints(self):
        self.assertIn("Safety Constraints", self.report_md)

    def test_148_md_contains_risk_disclaimer_reference(self):
        """Report should reference the NEMI risk disclaimer."""
        has_disclaimer = "不构成因果证明" in self.report_md or "disclaimer" in self.report_md.lower()
        self.assertTrue(has_disclaimer, "Report should mention risk disclaimer for NEMI cards")

    # ══════════════════════════════════════════════════════════════════════
    # CSV tests
    # ══════════════════════════════════════════════════════════════════════

    def test_150_csv_has_correct_columns(self):
        import csv as csv_mod
        with open(REPORT_CSV, "r", encoding="utf-8") as f:
            reader = csv_mod.DictReader(f)
            fieldnames = reader.fieldnames
            self.assertIsNotNone(fieldnames)
            for col in ["card_family", "real_external_api_called", "tg_test_sent",
                        "production_send_ready", "real_e2e_status"]:
                self.assertIn(col, fieldnames)

    def test_151_csv_row_count_is_5(self):
        import csv as csv_mod
        with open(REPORT_CSV, "r", encoding="utf-8") as f:
            rows = list(csv_mod.DictReader(f))
        self.assertEqual(len(rows), 5)

    # ══════════════════════════════════════════════════════════════════════
    # Handoff tests
    # ══════════════════════════════════════════════════════════════════════

    def test_160_handoff_contains_coverage_summary(self):
        self.assertIn("Coverage Summary", self.handoff_md)

    def test_161_handoff_contains_safety_confirmation(self):
        self.assertIn("Safety Confirmation", self.handoff_md)

    def test_162_handoff_contains_unfinished_items(self):
        self.assertIn("Unfinished Items", self.handoff_md)

    # ══════════════════════════════════════════════════════════════════════
    # Regression: historical artifacts not modified
    # ══════════════════════════════════════════════════════════════════════

    def test_170_v116a_result_still_exists(self):
        p = os.path.join(PROJECT_DIR, "results",
                         "market_radar_v116a_five_card_family_coverage_status_audit_result.json")
        self.assertTrue(os.path.exists(p), "v116A result must still exist")

    def test_171_v116c_result_still_exists(self):
        p = os.path.join(PROJECT_DIR, "results",
                         "market_radar_v116c_remaining_three_card_families_fixture_e2e_batch_replay_result.json")
        self.assertTrue(os.path.exists(p), "v116C result must still exist")

    def test_172_v116e_result_still_exists(self):
        p = os.path.join(PROJECT_DIR, "results",
                         "market_radar_v116e_real_free_api_multi_asset_tg_test_send_result.json")
        self.assertTrue(os.path.exists(p), "v116E result must still exist")

    def test_173_v116g_result_still_exists(self):
        p = os.path.join(PROJECT_DIR, "results",
                         "market_radar_v116g_price_oi_volume_anomaly_tg_test_send_result.json")
        self.assertTrue(os.path.exists(p), "v116G result must still exist")

    def test_174_v116i_result_still_exists(self):
        p = os.path.join(PROJECT_DIR, "results",
                         "market_radar_v116i_liquidation_pressure_tg_test_send_result.json")
        self.assertTrue(os.path.exists(p), "v116I result must still exist")

    def test_175_v116j_result_still_exists(self):
        p = os.path.join(PROJECT_DIR, "results",
                         "market_radar_v116j_news_event_market_impact_tg_test_send_result.json")
        self.assertTrue(os.path.exists(p), "v116J result must still exist")

    # ══════════════════════════════════════════════════════════════════════
    # Count summary validation (critical — must match acceptance criteria)
    # ══════════════════════════════════════════════════════════════════════

    def test_180_summary_counts_match_acceptance_criteria(self):
        """Acceptance: 5 fixture, 3 real TG sent, 1 gate blocked, 1 manual, 0 prod."""
        self.assertIsNotNone(self.audit, "Audit JSON not loaded")

        self.assertEqual(self.audit.get("fixture_e2e_passed_count"), 5,
                         "fixture_e2e_passed_count must be 5")
        self.assertEqual(self.audit.get("real_api_or_public_source_tg_test_sent_count"), 3,
                         "real_api_or_public_source_tg_test_sent_count must be 3")
        self.assertEqual(self.audit.get("real_api_attempted_but_gate_blocked_count"), 1,
                         "real_api_attempted_but_gate_blocked_count must be 1")
        self.assertEqual(self.audit.get("manual_evidence_blocked_count"), 1,
                         "manual_evidence_blocked_count must be 1")
        self.assertEqual(self.audit.get("production_send_ready_count"), 0,
                         "production_send_ready_count must be 0")

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
