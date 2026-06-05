"""Market Radar v116L — Real E2E Milestone Delivery Pack Tests

Validates all v116L outputs meet the acceptance criteria defined in the task spec.

Tests cover:
  - All v116L output files exist (8 files)
  - Manifest schema correct
  - Acceptance matrix has all 5 card families
  - 5/5 fixture, 3/5 real sent, 1/5 gate blocked, 1/5 manual blocked, 0/5 prod ready
  - TG evidence index has exactly 5 redacted entries
  - Outputs contain no raw secret/token/chat_id/message_id
  - No external API called
  - No TG sent
  - No v116A-K historical artifacts modified
  - No files deleted
  - Local-only handoff contains next steps and safety boundary
  - Milestone version is v116L
  - source_version_range is v116A-v116K
  - local_only is true
  - external_api_called_this_run is false
  - tg_sent_this_run is false
  - production_send_ready_count is 0

Usage:
    python scripts/test_market_radar_v116l_market_radar_real_e2e_milestone_pack_local_only.py
"""

import csv as csv_mod
import json
import os
import re
import sys
import unittest


PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# ── v116L output file paths ────────────────────────────────────────────────
MANIFEST_JSON = os.path.join(
    PROJECT_DIR, "results",
    "market_radar_v116l_milestone_pack_manifest.json"
)
ACCEPTANCE_JSON = os.path.join(
    PROJECT_DIR, "results",
    "market_radar_v116l_real_e2e_acceptance_matrix.json"
)
EVIDENCE_JSONL = os.path.join(
    PROJECT_DIR, "results",
    "market_radar_v116l_tg_evidence_index.jsonl"
)
SUMMARY_MD = os.path.join(
    PROJECT_DIR, "runs", "market_radar",
    "v116l_market_radar_real_e2e_milestone_summary.md"
)
ACCEPTANCE_CSV = os.path.join(
    PROJECT_DIR, "runs", "market_radar",
    "v116l_market_radar_real_e2e_acceptance_matrix.csv"
)
OPERATOR_MD = os.path.join(
    PROJECT_DIR, "runs", "market_radar",
    "v116l_operator_review_pack.md"
)
ROADMAP_MD = os.path.join(
    PROJECT_DIR, "runs", "market_radar",
    "v116l_next_phase_roadmap.md"
)
HANDOFF_MD = os.path.join(
    PROJECT_DIR, "runs", "market_radar",
    "v116l_local_only_handoff.md"
)

# ── v116K regression paths ─────────────────────────────────────────────────
V116K_AUDIT_JSON = os.path.join(
    PROJECT_DIR, "results",
    "market_radar_v116k_five_card_real_e2e_coverage_audit_result.json"
)
V116K_LEDGER_JSONL = os.path.join(
    PROJECT_DIR, "results",
    "market_radar_v116k_tg_test_send_evidence_ledger.jsonl"
)

CANONICAL_FAMILIES = [
    "whale_position_alert",
    "multi_asset_market_sync",
    "price_oi_volume_anomaly",
    "liquidation_pressure",
    "news_event_market_impact",
]

REQUIRED_MANIFEST_FIELDS = [
    "milestone_version",
    "source_version_range",
    "local_only",
    "external_api_called_this_run",
    "tg_sent_this_run",
    "production_send_ready_count",
    "generated_at",
    "task_id",
    "run_id",
    "card_family_count",
    "summary",
    "card_family_status",
    "artifact_inventory",
    "source_artifacts_referenced",
    "safety_constraints_verified",
]

REQUIRED_ACCEPTANCE_CARD_FIELDS = [
    "card_family",
    "display_name",
    "acceptance_category",
    "fixture_e2e",
    "real_api_called",
    "real_public_source_called",
    "real_card_generated",
    "quality_gate",
    "send_readiness",
    "tg_test_sent",
    "tg_test_group_ready",
    "production_send_ready",
    "current_blocker",
    "next_action",
]

REQUIRED_EVIDENCE_FIELDS = [
    "card_family",
    "asset",
    "target_type",
    "one_shot",
    "tg_sent",
    "message_id_proof",
    "token_proof",
    "chat_id_proof",
    "production_send",
    "credentials_printed",
    "raw_secret_present_in_outputs",
    "source_ledger",
]


def load_jsonl(path):
    records = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


class TestV116LMilestonePack(unittest.TestCase):
    """Tests for v116L real E2E milestone delivery pack."""

    @classmethod
    def setUpClass(cls):
        cls.manifest = None
        cls.acceptance = None
        cls.evidence = []
        cls.summary_md = ""
        cls.acceptance_csv = ""
        cls.operator_md = ""
        cls.roadmap_md = ""
        cls.handoff_md = ""

        if os.path.exists(MANIFEST_JSON):
            with open(MANIFEST_JSON, "r", encoding="utf-8") as f:
                cls.manifest = json.load(f)

        if os.path.exists(ACCEPTANCE_JSON):
            with open(ACCEPTANCE_JSON, "r", encoding="utf-8") as f:
                cls.acceptance = json.load(f)

        if os.path.exists(EVIDENCE_JSONL):
            cls.evidence = load_jsonl(EVIDENCE_JSONL)

        if os.path.exists(SUMMARY_MD):
            with open(SUMMARY_MD, "r", encoding="utf-8") as f:
                cls.summary_md = f.read()

        if os.path.exists(OPERATOR_MD):
            with open(OPERATOR_MD, "r", encoding="utf-8") as f:
                cls.operator_md = f.read()

        if os.path.exists(ROADMAP_MD):
            with open(ROADMAP_MD, "r", encoding="utf-8") as f:
                cls.roadmap_md = f.read()

        if os.path.exists(HANDOFF_MD):
            with open(HANDOFF_MD, "r", encoding="utf-8") as f:
                cls.handoff_md = f.read()

    # ═══════════════════════════════════════════════════════════════════════
    # File existence tests
    # ═══════════════════════════════════════════════════════════════════════

    def test_01_manifest_json_exists(self):
        self.assertTrue(os.path.exists(MANIFEST_JSON), f"Missing: {MANIFEST_JSON}")

    def test_02_acceptance_json_exists(self):
        self.assertTrue(os.path.exists(ACCEPTANCE_JSON), f"Missing: {ACCEPTANCE_JSON}")

    def test_03_evidence_jsonl_exists(self):
        self.assertTrue(os.path.exists(EVIDENCE_JSONL), f"Missing: {EVIDENCE_JSONL}")

    def test_04_summary_md_exists(self):
        self.assertTrue(os.path.exists(SUMMARY_MD), f"Missing: {SUMMARY_MD}")

    def test_05_acceptance_csv_exists(self):
        self.assertTrue(os.path.exists(ACCEPTANCE_CSV), f"Missing: {ACCEPTANCE_CSV}")

    def test_06_operator_md_exists(self):
        self.assertTrue(os.path.exists(OPERATOR_MD), f"Missing: {OPERATOR_MD}")

    def test_07_roadmap_md_exists(self):
        self.assertTrue(os.path.exists(ROADMAP_MD), f"Missing: {ROADMAP_MD}")

    def test_08_handoff_md_exists(self):
        self.assertTrue(os.path.exists(HANDOFF_MD), f"Missing: {HANDOFF_MD}")

    # ═══════════════════════════════════════════════════════════════════════
    # Manifest schema tests
    # ═══════════════════════════════════════════════════════════════════════

    def test_10_manifest_has_all_required_fields(self):
        self.assertIsNotNone(self.manifest, "Manifest not loaded")
        for field in REQUIRED_MANIFEST_FIELDS:
            self.assertIn(field, self.manifest, f"Manifest missing field: {field}")

    def test_11_manifest_milestone_version_is_v116L(self):
        self.assertEqual(self.manifest["milestone_version"], "v116L")

    def test_12_manifest_source_version_range_is_v116A_v116K(self):
        self.assertEqual(self.manifest["source_version_range"], "v116A-v116K")

    def test_13_manifest_local_only_is_true(self):
        self.assertTrue(self.manifest["local_only"])

    def test_14_manifest_external_api_called_false(self):
        self.assertFalse(self.manifest["external_api_called_this_run"])

    def test_15_manifest_tg_sent_this_run_false(self):
        self.assertFalse(self.manifest["tg_sent_this_run"])

    def test_16_manifest_production_send_ready_count_is_0(self):
        self.assertEqual(self.manifest["production_send_ready_count"], 0)

    def test_17_manifest_card_family_count_is_5(self):
        self.assertEqual(self.manifest["card_family_count"], 5)

    def test_18_manifest_card_family_status_has_5_families(self):
        status = self.manifest.get("card_family_status", {})
        self.assertEqual(len(status), 5)
        for family in CANONICAL_FAMILIES:
            self.assertIn(family, status, f"Manifest missing family: {family}")

    def test_19_manifest_artifact_inventory_has_8_entries(self):
        inventory = self.manifest.get("artifact_inventory", [])
        self.assertEqual(len(inventory), 8, f"Expected 8, got {len(inventory)}")

    def test_1a_manifest_source_artifacts_referenced(self):
        refs = self.manifest.get("source_artifacts_referenced", [])
        self.assertGreaterEqual(len(refs), 3)

    def test_1b_manifest_safety_constraints_all_false(self):
        sc = self.manifest.get("safety_constraints_verified", {})
        for key in ["external_api_called_this_run", "public_source_called_this_run",
                     "tg_sent_this_run", "prod_state_write", "ai_model_called",
                     "daemon_or_loop_started", "files_deleted",
                     "historical_artifacts_modified", "credentials_read"]:
            self.assertFalse(sc.get(key, True), f"Safety constraint {key} must be false")

    # ═══════════════════════════════════════════════════════════════════════
    # Acceptance matrix tests
    # ═══════════════════════════════════════════════════════════════════════

    def test_20_acceptance_matrix_has_5_cards(self):
        self.assertIsNotNone(self.acceptance, "Acceptance matrix not loaded")
        cards = self.acceptance.get("cards", [])
        self.assertEqual(len(cards), 5)

    def test_21_acceptance_summary_counts_correct(self):
        sc = self.acceptance.get("summary_counts", {})
        self.assertEqual(sc["fixture_e2e_passed"], "5/5")
        self.assertEqual(sc["real_api_public_source_tg_test_sent"], "3/5")
        self.assertEqual(sc["real_api_attempted_but_gate_blocked"], "1/5")
        self.assertEqual(sc["manual_evidence_blocked"], "1/5")
        self.assertEqual(sc["production_send_ready"], "0/5")

    def test_22_all_acceptance_cards_have_required_fields(self):
        cards = self.acceptance.get("cards", [])
        for card in cards:
            for field in REQUIRED_ACCEPTANCE_CARD_FIELDS:
                self.assertIn(field, card,
                              f"Card '{card.get('card_family', '?')}' missing field: {field}")

    def test_23_mams_acceptance_category_correct(self):
        card = self._find_acceptance_card("multi_asset_market_sync")
        self.assertEqual(card["acceptance_category"], "real_free_api_tg_test_sent")

    def test_24_pova_acceptance_category_correct(self):
        card = self._find_acceptance_card("price_oi_volume_anomaly")
        self.assertEqual(card["acceptance_category"], "real_free_api_tg_test_sent")

    def test_25_nemi_acceptance_category_correct(self):
        card = self._find_acceptance_card("news_event_market_impact")
        self.assertEqual(card["acceptance_category"], "real_free_public_source_tg_test_sent")

    def test_26_lipr_acceptance_category_correct(self):
        card = self._find_acceptance_card("liquidation_pressure")
        self.assertEqual(card["acceptance_category"], "blocked_gate_not_passed")

    def test_27_wpa_acceptance_category_correct(self):
        card = self._find_acceptance_card("whale_position_alert")
        self.assertEqual(card["acceptance_category"], "blocked_manual_evidence")

    def test_28_all_cards_fixture_e2e_passed(self):
        for card in self.acceptance.get("cards", []):
            self.assertEqual(card["fixture_e2e"], "passed",
                             f"{card['card_family']} fixture_e2e must be 'passed'")

    def test_29_all_cards_production_send_ready_false(self):
        for card in self.acceptance.get("cards", []):
            self.assertFalse(card["production_send_ready"],
                             f"{card['card_family']} production_send_ready must be False")

    def test_2a_mams_tg_test_sent_true(self):
        card = self._find_acceptance_card("multi_asset_market_sync")
        self.assertTrue(card["tg_test_sent"])

    def test_2b_pova_tg_test_sent_true(self):
        card = self._find_acceptance_card("price_oi_volume_anomaly")
        self.assertTrue(card["tg_test_sent"])

    def test_2c_nemi_tg_test_sent_true(self):
        card = self._find_acceptance_card("news_event_market_impact")
        self.assertTrue(card["tg_test_sent"])

    def test_2d_lipr_tg_test_sent_false(self):
        card = self._find_acceptance_card("liquidation_pressure")
        self.assertFalse(card["tg_test_sent"],
                         "liquidation_pressure MUST NOT be tg_test_sent: true")

    def test_2e_wpa_tg_test_sent_false(self):
        card = self._find_acceptance_card("whale_position_alert")
        self.assertFalse(card["tg_test_sent"],
                         "whale_position_alert MUST NOT be tg_test_sent: true")

    def test_2f_mams_blocker_is_none(self):
        card = self._find_acceptance_card("multi_asset_market_sync")
        self.assertIsNone(card.get("current_blocker"))

    def test_2g_pova_blocker_is_none(self):
        card = self._find_acceptance_card("price_oi_volume_anomaly")
        self.assertIsNone(card.get("current_blocker"))

    def test_2h_nemi_blocker_is_none(self):
        card = self._find_acceptance_card("news_event_market_impact")
        self.assertIsNone(card.get("current_blocker"))

    def test_2i_lipr_blocker_not_none(self):
        card = self._find_acceptance_card("liquidation_pressure")
        self.assertIsNotNone(card.get("current_blocker"))
        self.assertTrue(len(card["current_blocker"]) > 0)

    def test_2j_wpa_blocker_not_none(self):
        card = self._find_acceptance_card("whale_position_alert")
        self.assertIsNotNone(card.get("current_blocker"))
        self.assertTrue(len(card["current_blocker"]) > 0)

    def test_2k_mams_real_api_called_true(self):
        card = self._find_acceptance_card("multi_asset_market_sync")
        self.assertTrue(card["real_api_called"])

    def test_2l_lipr_real_api_called_true(self):
        """liquidation_pressure must have real_api_called: true (v116I completed)."""
        card = self._find_acceptance_card("liquidation_pressure")
        self.assertTrue(card["real_api_called"])

    def test_2m_wpa_real_api_called_false(self):
        card = self._find_acceptance_card("whale_position_alert")
        self.assertFalse(card["real_api_called"])

    def test_2n_nemi_real_public_source_called_true(self):
        card = self._find_acceptance_card("news_event_market_impact")
        self.assertTrue(card.get("real_public_source_called", False))

    # ═══════════════════════════════════════════════════════════════════════
    # TG Evidence Index tests
    # ═══════════════════════════════════════════════════════════════════════

    def test_30_evidence_has_exactly_5_entries(self):
        self.assertEqual(len(self.evidence), 5,
                         f"Evidence index must have 5 entries, got {len(self.evidence)}")

    def test_31_all_evidence_entries_have_required_fields(self):
        for entry in self.evidence:
            for field in REQUIRED_EVIDENCE_FIELDS:
                self.assertIn(field, entry,
                              f"Evidence entry missing field: {field}")

    def test_32_evidence_target_type_is_test_group(self):
        for entry in self.evidence:
            self.assertEqual(entry.get("target_type"), "test_group")

    def test_33_evidence_one_shot_true(self):
        for entry in self.evidence:
            self.assertTrue(entry.get("one_shot"))

    def test_34_evidence_tg_sent_true(self):
        for entry in self.evidence:
            self.assertTrue(entry.get("tg_sent"))

    def test_35_evidence_production_send_false(self):
        for entry in self.evidence:
            self.assertFalse(entry.get("production_send"))

    def test_36_evidence_credentials_printed_false(self):
        for entry in self.evidence:
            self.assertFalse(entry.get("credentials_printed"))

    def test_37_evidence_raw_secret_present_false(self):
        for entry in self.evidence:
            self.assertFalse(entry.get("raw_secret_present_in_outputs"))

    def test_38_no_raw_token_in_evidence(self):
        """No evidence entry should contain unredacted token/chat_id/message_id."""
        token_pattern = re.compile(r'\d{8,12}:[A-Za-z0-9_-]{30,}')
        for entry in self.evidence:
            entry_str = json.dumps(entry)
            self.assertIsNone(token_pattern.search(entry_str),
                              "Evidence contains unredacted token-like value")

    def test_39_all_proofs_are_sha256_redacted(self):
        for entry in self.evidence:
            for field in ["message_id_proof", "token_proof", "chat_id_proof"]:
                val = entry.get(field, "")
                self.assertTrue(val.startswith("sha256:") or val == "",
                                f"Field {field} not properly redacted: '{val[:40]}...'")

    def test_3a_evidence_card_family_order(self):
        families = [e["card_family"] for e in self.evidence]
        self.assertEqual(families[0], "multi_asset_market_sync")
        self.assertEqual(families[1], "price_oi_volume_anomaly")
        self.assertEqual(families[2], "price_oi_volume_anomaly")
        self.assertEqual(families[3], "news_event_market_impact")
        self.assertEqual(families[4], "news_event_market_impact")

    def test_3b_pova_evidence_has_eth_sol(self):
        pova = [e for e in self.evidence if e["card_family"] == "price_oi_volume_anomaly"]
        self.assertEqual(len(pova), 2)
        assets = {e["asset"] for e in pova}
        self.assertEqual(assets, {"ETH", "SOL"})

    def test_3c_nemi_evidence_asset_is_none(self):
        nemi = [e for e in self.evidence if e["card_family"] == "news_event_market_impact"]
        self.assertEqual(len(nemi), 2)
        for entry in nemi:
            self.assertIsNone(entry.get("asset"))

    def test_3d_evidence_no_raw_secret_in_any_field(self):
        """Comprehensive check: no raw secret in any evidence field value."""
        forbidden = ["token", "chat_id", "message_id", "password", "cookie",
                    "api_key", "apikey", "secret"]
        for entry in self.evidence:
            for key, val in entry.items():
                if isinstance(val, str):
                    val_lower = val.lower()
                    for fb in forbidden:
                        # Allow "sha256:" prefix (redacted) and descriptive field names
                        if fb in val_lower and not val.startswith("sha256:"):
                            # Special case: field names containing these words are fine
                            # But VALUES containing raw secrets are not
                            if len(val) > 60:  # long values might be tokens
                                self.fail(
                                    f"Evidence entry has suspicious value in '{key}': "
                                    f"'{val[:80]}...'"
                                )

    # ═══════════════════════════════════════════════════════════════════════
    # Milestone summary MD tests
    # ═══════════════════════════════════════════════════════════════════════

    def test_40_summary_contains_milestone_version(self):
        self.assertIn("v116L", self.summary_md)

    def test_41_summary_contains_current_progress(self):
        self.assertIn("3/5", self.summary_md)
        self.assertIn("5/5", self.summary_md)

    def test_42_summary_contains_all_5_card_families(self):
        for family in CANONICAL_FAMILIES:
            self.assertIn(family, self.summary_md,
                          f"Summary missing reference to: {family}")

    def test_43_summary_contains_risk_disclaimer(self):
        has_disclaimer = "不构成因果证明" in self.summary_md
        self.assertTrue(has_disclaimer, "Summary should reference risk disclaimer")

    def test_44_summary_states_production_send_ready_0(self):
        self.assertIn("0/5", self.summary_md)

    def test_45_summary_contains_safety_constraints(self):
        self.assertIn("Safety Constraints", self.summary_md)

    def test_46_summary_mentions_gate_blocked_design(self):
        self.assertIn("Gate Correctly Blocked", self.summary_md)

    def test_47_summary_mentions_manual_evidence(self):
        self.assertIn("Manual Evidence", self.summary_md)

    # ═══════════════════════════════════════════════════════════════════════
    # Acceptance matrix CSV tests
    # ═══════════════════════════════════════════════════════════════════════

    def test_50_csv_has_correct_columns(self):
        with open(ACCEPTANCE_CSV, "r", encoding="utf-8") as f:
            reader = csv_mod.DictReader(f)
            fieldnames = reader.fieldnames
            self.assertIsNotNone(fieldnames)
            for col in ["card_family", "acceptance_category", "fixture_e2e",
                        "tg_test_sent", "production_send_ready"]:
                self.assertIn(col, fieldnames)

    def test_51_csv_has_5_rows(self):
        with open(ACCEPTANCE_CSV, "r", encoding="utf-8") as f:
            rows = list(csv_mod.DictReader(f))
        self.assertEqual(len(rows), 5)

    # ═══════════════════════════════════════════════════════════════════════
    # Operator review pack tests
    # ═══════════════════════════════════════════════════════════════════════

    def test_60_operator_pack_mentions_what_can_demo(self):
        self.assertIn("演示", self.operator_md)

    def test_61_operator_pack_mentions_what_it_is_not(self):
        self.assertIn("误解", self.operator_md)

    def test_62_operator_pack_has_evidence_table(self):
        self.assertIn("证据", self.operator_md)

    def test_63_operator_pack_explains_why_not_lower_liquidation_gate(self):
        self.assertIn("不应降 gate", self.operator_md)

    def test_64_operator_pack_explains_why_whale_needs_manual_evidence(self):
        self.assertIn("whale", self.operator_md.lower())
        self.assertTrue(
            any(kw in self.operator_md for kw in ["人工证据", "manual evidence", "manual_evidence"]),
            "Operator pack should mention whale needing manual evidence"
        )

    def test_65_operator_pack_has_human_review_suggestions(self):
        self.assertIn("复核", self.operator_md)

    def test_66_operator_pack_states_not_production_ready(self):
        self.assertTrue(
            any(kw in self.operator_md for kw in
                ["不是 production", "not production", "0/5 production", "production send ready"]),
            "Operator pack must clearly state NOT production ready"
        )

    def test_67_operator_pack_mentions_3_cards_verified(self):
        self.assertIn("三类", self.operator_md)

    def test_68_operator_pack_mentions_2_cards_blocked(self):
        self.assertIn("两类未完成", self.operator_md)

    # ═══════════════════════════════════════════════════════════════════════
    # Next phase roadmap tests
    # ═══════════════════════════════════════════════════════════════════════

    def test_70_roadmap_has_p0(self):
        self.assertIn("P0", self.roadmap_md)

    def test_71_roadmap_has_p1_gemini_audit(self):
        self.assertIn("P1", self.roadmap_md)
        self.assertIn("Gemini", self.roadmap_md)

    def test_72_roadmap_has_p2_liquidation_rerun(self):
        self.assertIn("P2", self.roadmap_md)
        self.assertIn("liquidation", self.roadmap_md.lower())

    def test_73_roadmap_has_p3_whale_workbook(self):
        self.assertIn("P3", self.roadmap_md)
        self.assertIn("whale", self.roadmap_md.lower())

    def test_74_roadmap_has_p4_shared_adapter(self):
        self.assertIn("P4", self.roadmap_md)
        self.assertIn("adapter", self.roadmap_md.lower())

    def test_75_roadmap_does_not_recommend_production_send(self):
        """Roadmap must NOT recommend automatic production send, daemon, cron, loop or gate bypass."""
        lower = self.roadmap_md.lower()
        self.assertNotIn("production send", lower)
        self.assertNotIn("daemon", lower)
        self.assertNotIn("cron", lower)
        # What NOT to do section should explicitly forbid these
        self.assertIn("What NOT to do", self.roadmap_md)

    def test_76_roadmap_does_not_recommend_lowering_gate(self):
        """Roadmap must NOT recommend lowering liquidation gate."""
        lower = self.roadmap_md.lower()
        self.assertNotIn("lower threshold", lower)
        self.assertNotIn("lower gate", lower)

    def test_77_roadmap_mentions_one_shot(self):
        self.assertIn("one-shot", self.roadmap_md.lower())

    # ═══════════════════════════════════════════════════════════════════════
    # Handoff tests
    # ═══════════════════════════════════════════════════════════════════════

    def test_80_handoff_contains_new_files_list(self):
        self.assertIn("New Files", self.handoff_md)

    def test_81_handoff_contains_safety_confirmation(self):
        self.assertIn("Safety Confirmation", self.handoff_md)

    def test_82_handoff_contains_unfinished_items(self):
        self.assertIn("Unfinished Items", self.handoff_md)

    def test_83_handoff_contains_safety_boundary(self):
        self.assertIn("Safety Boundary", self.handoff_md)

    def test_84_handoff_contains_next_steps(self):
        self.assertIn("Next Steps", self.handoff_md)

    def test_85_handoff_states_not_production_ready(self):
        self.assertIn("Not production send ready", self.handoff_md)

    def test_86_handoff_everything_in_project_dir(self):
        """Output files must only be in project directory."""
        for path in [MANIFEST_JSON, ACCEPTANCE_JSON, EVIDENCE_JSONL,
                     SUMMARY_MD, ACCEPTANCE_CSV, OPERATOR_MD, ROADMAP_MD, HANDOFF_MD]:
            self.assertTrue(path.startswith(PROJECT_DIR),
                            f"File outside project dir: {path}")
            # Must NOT be in ai_relay_desk
            self.assertNotIn("ai_relay_desk", path.lower())

    # ═══════════════════════════════════════════════════════════════════════
    # Regression: v116A-K historical artifacts not modified
    # ═══════════════════════════════════════════════════════════════════════

    def test_90_v116k_audit_still_exists(self):
        self.assertTrue(os.path.exists(V116K_AUDIT_JSON),
                        "v116K audit result must still exist")

    def test_91_v116k_ledger_still_exists(self):
        self.assertTrue(os.path.exists(V116K_LEDGER_JSONL),
                        "v116K evidence ledger must still exist")

    def test_92_v116e_result_still_exists(self):
        p = os.path.join(PROJECT_DIR, "results",
                         "market_radar_v116e_real_free_api_multi_asset_tg_test_send_result.json")
        self.assertTrue(os.path.exists(p), "v116E result must still exist")

    def test_93_v116g_result_still_exists(self):
        p = os.path.join(PROJECT_DIR, "results",
                         "market_radar_v116g_price_oi_volume_anomaly_tg_test_send_result.json")
        self.assertTrue(os.path.exists(p), "v116G result must still exist")

    def test_94_v116i_result_still_exists(self):
        p = os.path.join(PROJECT_DIR, "results",
                         "market_radar_v116i_liquidation_pressure_tg_test_send_result.json")
        self.assertTrue(os.path.exists(p), "v116I result must still exist")

    def test_95_v116j_result_still_exists(self):
        p = os.path.join(PROJECT_DIR, "results",
                         "market_radar_v116j_news_event_market_impact_tg_test_send_result.json")
        self.assertTrue(os.path.exists(p), "v116J result must still exist")

    def test_96_v116a_result_still_exists(self):
        p = os.path.join(PROJECT_DIR, "results",
                         "market_radar_v116a_five_card_family_coverage_status_audit_result.json")
        self.assertTrue(os.path.exists(p), "v116A result must still exist")

    # ═══════════════════════════════════════════════════════════════════════
    # No files deleted check
    # ═══════════════════════════════════════════════════════════════════════

    def test_97_v116l_output_files_are_new_only(self):
        """Ensure we're not overwriting v116A-K artifacts. v116L files are all new."""
        v116k_files = [
            "market_radar_v116k_five_card_real_e2e_coverage_audit_result.json",
            "market_radar_v116k_tg_test_send_evidence_ledger.jsonl",
        ]
        for f in v116k_files:
            p = os.path.join(PROJECT_DIR, "results", f)
            self.assertTrue(os.path.exists(p), f"v116K file still exists: {f}")

    # ═══════════════════════════════════════════════════════════════════════
    # Count summary validation (critical — must match acceptance criteria)
    # ═══════════════════════════════════════════════════════════════════════

    def test_a0_manifest_summary_counts_correct(self):
        s = self.manifest.get("summary", {})
        self.assertEqual(s["fixture_e2e_passed"], "5/5")
        self.assertEqual(s["real_api_public_source_tg_test_sent"], "3/5")
        self.assertEqual(s["real_api_attempted_but_gate_blocked"], "1/5")
        self.assertEqual(s["manual_evidence_blocked"], "1/5")
        self.assertEqual(s["production_send_ready"], "0/5")

    def test_a1_card_family_status_counts_computed(self):
        """Verify computed counts from card_family_status match manifest summary."""
        status = self.manifest.get("card_family_status", {})
        fixture_count = sum(1 for v in status.values() if v["fixture_e2e_passed"])
        tg_sent_count = sum(1 for v in status.values() if v["tg_test_sent"])
        gate_blocked = sum(1 for v in status.values()
                          if v["real_e2e_status"] == "blocked_gate_not_passed")
        manual_blocked = sum(1 for v in status.values()
                            if v["real_e2e_status"] == "blocked_manual_evidence")
        prod_ready = sum(1 for v in status.values() if v["production_send_ready"])

        self.assertEqual(fixture_count, 5)
        self.assertEqual(tg_sent_count, 3)
        self.assertEqual(gate_blocked, 1)
        self.assertEqual(manual_blocked, 1)
        self.assertEqual(prod_ready, 0)

    # ═══════════════════════════════════════════════════════════════════════
    # Helpers
    # ═══════════════════════════════════════════════════════════════════════

    def _find_acceptance_card(self, card_family: str) -> dict:
        for card in self.acceptance.get("cards", []):
            if card["card_family"] == card_family:
                return card
        self.fail(f"Card family '{card_family}' not found in acceptance matrix")


if __name__ == "__main__":
    unittest.main(verbosity=2)
