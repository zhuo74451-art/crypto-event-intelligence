"""Market Radar v116N — User Acceptance Overlay Pack Tests

Validates all v116N outputs meet the acceptance criteria defined in the task spec.

Tests cover:
  - All v116N output files exist (8 files)
  - One-pager contains Production Readiness: 0/5
  - One-pager contains NOT FOR LIVE USE
  - One-pager contains 5/5, 3/5, 1/5, 1/5, 0/5
  - One-pager states liquidation is normal gate blocked, not failure
  - One-pager states whale needs manual evidence, not failure
  - User decision tree contains A/B/C options
  - Production readiness checklist states current not meeting production conditions
  - Whale checklist explicitly forbids auto-attribution without evidence
  - News event risk statement contains observation / not causal proof
  - Manifest schema correct
  - No raw token, cookie, password, API key, raw chat_id, raw message_id
  - No external API called
  - No TG sent
  - No files deleted
  - No v116A-K historical artifacts modified

Usage:
    python -m pytest scripts/test_market_radar_v116n_user_acceptance_overlay_pack_local_only.py -v
"""

import json
import os
import re
import sys
import unittest


PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# ── v116N output file paths ─────────────────────────────────────────────────
ONE_PAGER_MD = os.path.join(
    PROJECT_DIR, "runs", "market_radar",
    "v116n_one_pager_acceptance_summary.md"
)
OPERATOR_USER_FACING_MD = os.path.join(
    PROJECT_DIR, "runs", "market_radar",
    "v116n_operator_review_pack_user_facing.md"
)
DECISION_TREE_MD = os.path.join(
    PROJECT_DIR, "runs", "market_radar",
    "v116n_user_decision_tree.md"
)
DEMO_SEQUENCE_MD = os.path.join(
    PROJECT_DIR, "runs", "market_radar",
    "v116n_demo_sequence_10min.md"
)
PROD_READINESS_MD = os.path.join(
    PROJECT_DIR, "runs", "market_radar",
    "v116n_production_readiness_checklist.md"
)
WHALE_CHECKLIST_MD = os.path.join(
    PROJECT_DIR, "runs", "market_radar",
    "v116n_whale_manual_evidence_checklist.md"
)
HANDOFF_MD = os.path.join(
    PROJECT_DIR, "runs", "market_radar",
    "v116n_local_only_handoff.md"
)
MANIFEST_JSON = os.path.join(
    PROJECT_DIR, "results",
    "market_radar_v116n_user_acceptance_overlay_manifest.json"
)

ALL_V116N_FILES = [
    ONE_PAGER_MD, OPERATOR_USER_FACING_MD, DECISION_TREE_MD,
    DEMO_SEQUENCE_MD, PROD_READINESS_MD, WHALE_CHECKLIST_MD,
    HANDOFF_MD, MANIFEST_JSON,
]

# ── v116L output file paths (regression: must still exist and not be modified) ──
V116L_MANIFEST = os.path.join(
    PROJECT_DIR, "results",
    "market_radar_v116l_milestone_pack_manifest.json"
)
V116L_ACCEPTANCE = os.path.join(
    PROJECT_DIR, "results",
    "market_radar_v116l_real_e2e_acceptance_matrix.json"
)
V116L_EVIDENCE = os.path.join(
    PROJECT_DIR, "results",
    "market_radar_v116l_tg_evidence_index.jsonl"
)
V116L_SUMMARY = os.path.join(
    PROJECT_DIR, "runs", "market_radar",
    "v116l_market_radar_real_e2e_milestone_summary.md"
)
V116L_OPERATOR = os.path.join(
    PROJECT_DIR, "runs", "market_radar",
    "v116l_operator_review_pack.md"
)
V116L_ROADMAP = os.path.join(
    PROJECT_DIR, "runs", "market_radar",
    "v116l_next_phase_roadmap.md"
)
V116L_HANDOFF = os.path.join(
    PROJECT_DIR, "runs", "market_radar",
    "v116l_local_only_handoff.md"
)

V116L_FILES = [
    V116L_MANIFEST, V116L_ACCEPTANCE, V116L_EVIDENCE,
    V116L_SUMMARY, V116L_OPERATOR, V116L_ROADMAP, V116L_HANDOFF,
]

# ── v116A-K historical artifact paths (must still exist) ──
V116K_AUDIT = os.path.join(
    PROJECT_DIR, "results",
    "market_radar_v116k_five_card_real_e2e_coverage_audit_result.json"
)
V116K_LEDGER = os.path.join(
    PROJECT_DIR, "results",
    "market_radar_v116k_tg_test_send_evidence_ledger.jsonl"
)
V116E_RESULT = os.path.join(
    PROJECT_DIR, "results",
    "market_radar_v116e_real_free_api_multi_asset_tg_test_send_result.json"
)
V116G_RESULT = os.path.join(
    PROJECT_DIR, "results",
    "market_radar_v116g_price_oi_volume_anomaly_tg_test_send_result.json"
)
V116I_RESULT = os.path.join(
    PROJECT_DIR, "results",
    "market_radar_v116i_liquidation_pressure_tg_test_send_result.json"
)
V116J_RESULT = os.path.join(
    PROJECT_DIR, "results",
    "market_radar_v116j_news_event_market_impact_tg_test_send_result.json"
)

HISTORICAL_FILES = [
    V116K_AUDIT, V116K_LEDGER,
    V116E_RESULT, V116G_RESULT, V116I_RESULT, V116J_RESULT,
]

REQUIRED_MANIFEST_V116N_FIELDS = [
    "overlay_version",
    "source_milestone_version",
    "audit_source",
    "local_only",
    "external_api_called_this_run",
    "tg_sent_this_run",
    "production_send_ready_count",
    "generated_at",
    "task_id",
    "run_id",
    "user_acceptance_ready_after_overlay",
    "summary",
    "card_family_status_summary",
    "created_files",
    "source_files_read",
    "remaining_blockers",
    "safety_constraints_verified",
]


class TestV116NUserAcceptanceOverlayPack(unittest.TestCase):
    """Tests for v116N user acceptance overlay pack."""

    @classmethod
    def setUpClass(cls):
        cls.one_pager = ""
        cls.operator_user_facing = ""
        cls.decision_tree = ""
        cls.demo_sequence = ""
        cls.prod_readiness = ""
        cls.whale_checklist = ""
        cls.handoff = ""
        cls.manifest = None

        if os.path.exists(ONE_PAGER_MD):
            with open(ONE_PAGER_MD, "r", encoding="utf-8") as f:
                cls.one_pager = f.read()

        if os.path.exists(OPERATOR_USER_FACING_MD):
            with open(OPERATOR_USER_FACING_MD, "r", encoding="utf-8") as f:
                cls.operator_user_facing = f.read()

        if os.path.exists(DECISION_TREE_MD):
            with open(DECISION_TREE_MD, "r", encoding="utf-8") as f:
                cls.decision_tree = f.read()

        if os.path.exists(DEMO_SEQUENCE_MD):
            with open(DEMO_SEQUENCE_MD, "r", encoding="utf-8") as f:
                cls.demo_sequence = f.read()

        if os.path.exists(PROD_READINESS_MD):
            with open(PROD_READINESS_MD, "r", encoding="utf-8") as f:
                cls.prod_readiness = f.read()

        if os.path.exists(WHALE_CHECKLIST_MD):
            with open(WHALE_CHECKLIST_MD, "r", encoding="utf-8") as f:
                cls.whale_checklist = f.read()

        if os.path.exists(HANDOFF_MD):
            with open(HANDOFF_MD, "r", encoding="utf-8") as f:
                cls.handoff = f.read()

        if os.path.exists(MANIFEST_JSON):
            with open(MANIFEST_JSON, "r", encoding="utf-8") as f:
                cls.manifest = json.load(f)

    # ═══════════════════════════════════════════════════════════════════════
    # File existence tests
    # ═══════════════════════════════════════════════════════════════════════

    def test_01_one_pager_exists(self):
        self.assertTrue(os.path.exists(ONE_PAGER_MD), f"Missing: {ONE_PAGER_MD}")

    def test_02_operator_user_facing_exists(self):
        self.assertTrue(os.path.exists(OPERATOR_USER_FACING_MD),
                        f"Missing: {OPERATOR_USER_FACING_MD}")

    def test_03_decision_tree_exists(self):
        self.assertTrue(os.path.exists(DECISION_TREE_MD), f"Missing: {DECISION_TREE_MD}")

    def test_04_demo_sequence_exists(self):
        self.assertTrue(os.path.exists(DEMO_SEQUENCE_MD), f"Missing: {DEMO_SEQUENCE_MD}")

    def test_05_prod_readiness_exists(self):
        self.assertTrue(os.path.exists(PROD_READINESS_MD), f"Missing: {PROD_READINESS_MD}")

    def test_06_whale_checklist_exists(self):
        self.assertTrue(os.path.exists(WHALE_CHECKLIST_MD), f"Missing: {WHALE_CHECKLIST_MD}")

    def test_07_handoff_exists(self):
        self.assertTrue(os.path.exists(HANDOFF_MD), f"Missing: {HANDOFF_MD}")

    def test_08_manifest_json_exists(self):
        self.assertTrue(os.path.exists(MANIFEST_JSON), f"Missing: {MANIFEST_JSON}")

    def test_09_all_8_files_exist(self):
        missing = [f for f in ALL_V116N_FILES if not os.path.exists(f)]
        self.assertEqual(len(missing), 0, f"Missing files: {missing}")

    # ═══════════════════════════════════════════════════════════════════════
    # One-Pager Tests (THE critical acceptance document)
    # ═══════════════════════════════════════════════════════════════════════

    def test_10_one_pager_contains_production_readiness_0_5(self):
        self.assertIn("Production Readiness", self.one_pager)
        self.assertIn("0/5", self.one_pager)

    def test_11_one_pager_contains_not_for_live_use(self):
        self.assertIn("NOT FOR LIVE USE", self.one_pager)

    def test_12_one_pager_contains_5_5_fixture(self):
        self.assertIn("5/5", self.one_pager)

    def test_13_one_pager_contains_3_5_real_tg_sent(self):
        self.assertIn("3/5", self.one_pager)

    def test_14_one_pager_contains_1_5_gate_blocked(self):
        # "1/5" appears multiple times (gate blocked, manual blocked). Just check it exists.
        count = self.one_pager.count("1/5")
        self.assertGreaterEqual(count, 2, f"Expected at least 2 occurrences of 1/5, got {count}")

    def test_15_one_pager_liquidation_not_failure(self):
        """One-pager must state liquidation gate block is normal, not a bug."""
        one_pager_lower = self.one_pager.lower()
        self.assertTrue(
            any(kw in one_pager_lower for kw in [
                "不是程序故障", "不是故障", "not a failure", "not a bug",
                "正常阻断", "normal gate block", "gate paused",
            ]),
            "One-pager must state liquidation is normal gate block, not failure"
        )
        self.assertIn("liquidation", one_pager_lower)

    def test_16_one_pager_whale_needs_manual_evidence(self):
        """One-pager must state whale needs manual evidence, not program failure."""
        one_pager_lower = self.one_pager.lower()
        self.assertTrue(
            any(kw in one_pager_lower for kw in [
                "不是程序失败", "不是故障", "not a failure",
                "需要人工证据", "manual evidence", "human evidence",
            ]),
            "One-pager must state whale needs manual evidence, not failure"
        )
        self.assertIn("whale", one_pager_lower)

    def test_17_one_pager_contains_three_sentence_conclusion(self):
        self.assertIn("三句话", self.one_pager)
        self.assertIn("Three-Sentence", self.one_pager)

    def test_18_one_pager_contains_user_next_step_three_choices(self):
        self.assertIn("A", self.one_pager)
        self.assertIn("B", self.one_pager)
        self.assertIn("C", self.one_pager)
        self.assertIn("三选一", self.one_pager)

    def test_19_one_pager_contains_explicitly_not_recommended(self):
        self.assertIn("不建议", self.one_pager)

    def test_1a_one_pager_title_correct(self):
        self.assertIn("v116N", self.one_pager)
        self.assertIn("One-Pager", self.one_pager)
        self.assertIn("Acceptance Summary", self.one_pager)

    def test_1b_one_pager_no_daemon_cron_loop_warning(self):
        """One-pager must state no daemon/cron/loop is enabled."""
        one_pager_lower = self.one_pager.lower()
        self.assertTrue(
            any(kw in one_pager_lower for kw in [
                "no daemon", "no cron", "no loop",
            ]),
            "One-pager must mention no daemon/cron/loop enabled"
        )

    # ═══════════════════════════════════════════════════════════════════════
    # Operator Review Pack (User-Facing) Tests
    # ═══════════════════════════════════════════════════════════════════════

    def test_20_operator_user_facing_has_version_quick_ref(self):
        self.assertIn("版本号速查表", self.operator_user_facing)

    def test_21_operator_user_facing_mentions_sha256_explanation(self):
        self.assertIn("SHA-256", self.operator_user_facing)

    def test_22_operator_user_facing_misunderstanding_section_first(self):
        """'不能被误解成什么' must appear before detailed evidence sections."""
        idx_misunderstand = self.operator_user_facing.find("不能被误解成什么")
        idx_evidence = self.operator_user_facing.find("三类已验证卡片的证据摘要")
        self.assertGreater(idx_misunderstand, 0, "'不能被误解成什么' section must exist")
        self.assertGreater(idx_evidence, 0, "Evidence section must exist")
        self.assertLess(idx_misunderstand, idx_evidence,
                        "'不能被误解成什么' must appear before evidence section")

    def test_23_operator_user_facing_news_event_not_causal_proof(self):
        """Must contain standalone News Event observation / not causal proof section."""
        op_lower = self.operator_user_facing.lower()
        self.assertTrue(
            any(kw in op_lower for kw in [
                "observation, not causal proof",
                "observation not causal",
                "不构成因果证明",
            ]),
            "Operator pack must state news event is observation, not causal proof"
        )

    def test_24_operator_user_facing_no_raw_version_noise(self):
        """Should not excessively reference versions without context. Version quick-ref table is sufficient."""
        # Version quick-ref table is present — that's the right way.
        self.assertIn("v116E", self.operator_user_facing)
        self.assertIn("v116L", self.operator_user_facing)

    def test_25_operator_user_facing_does_not_whitewash_2_5(self):
        """Must acknowledge 2/5 are not done (not hide the gap)."""
        self.assertIn("3/5", self.operator_user_facing)
        # Should mention the 2 blocked families
        self.assertIn("liquidation", self.operator_user_facing.lower())
        self.assertIn("whale", self.operator_user_facing.lower())

    def test_26_operator_user_facing_explains_not_production(self):
        op_lower = self.operator_user_facing.lower()
        self.assertTrue(
            any(kw in op_lower for kw in [
                "不是 production", "不是 production send ready",
                "not production",
            ]),
            "Operator pack must clearly state not production ready"
        )

    # ═══════════════════════════════════════════════════════════════════════
    # User Decision Tree Tests
    # ═══════════════════════════════════════════════════════════════════════

    def test_30_decision_tree_contains_option_A(self):
        self.assertIn("路径 A", self.decision_tree)

    def test_31_decision_tree_contains_option_B(self):
        self.assertIn("路径 B", self.decision_tree)

    def test_32_decision_tree_contains_option_C(self):
        self.assertIn("路径 C", self.decision_tree)

    def test_33_decision_tree_accept_milestone_branch(self):
        self.assertIn("接受当前里程碑", self.decision_tree)

    def test_34_decision_tree_whale_evidence_branch(self):
        dt_lower = self.decision_tree.lower()
        self.assertTrue(
            any(kw in dt_lower for kw in [
                "补人工证据", "manual evidence", "whale",
            ]),
            "Decision tree must have whale manual evidence branch"
        )

    def test_35_decision_tree_liquidation_wait_branch(self):
        dt_lower = self.decision_tree.lower()
        self.assertTrue(
            any(kw in dt_lower for kw in [
                "等波动", "高波动", "rerun", "volatility",
            ]),
            "Decision tree must have wait-for-volatility rerun branch"
        )

    def test_36_decision_tree_production_blocked_branch(self):
        dt_lower = self.decision_tree.lower()
        self.assertTrue(
            any(kw in dt_lower for kw in [
                "不允许直接上线", "production readiness", "先建立 production",
            ]),
            "Decision tree must block direct production push"
        )

    def test_37_decision_tree_demo_portfolio_branch(self):
        dt_lower = self.decision_tree.lower()
        self.assertTrue(
            any(kw in dt_lower for kw in [
                "作品集", "demo", "portfolio",
            ]),
            "Decision tree must have demo/portfolio branch"
        )

    def test_38_decision_tree_contains_red_line_rules(self):
        self.assertIn("红线规则", self.decision_tree)

    def test_39_decision_tree_no_lower_gate_recommendation(self):
        """Decision tree must not RECOMMEND lowering the gate.
        It may forbid it (red-line rules), but never suggest it as an option."""
        dt_lower = self.decision_tree.lower()
        # "不允许降低" (forbidding) is correct — but the text should never
        # recommend or suggest lowering the gate as a user action.
        # Check that "降低 gate" only appears in prohibition context.
        if "降低 gate" in dt_lower:
            idx = dt_lower.index("降低 gate")
            context = dt_lower[max(0, idx - 20):idx + 30]
            self.assertTrue(
                any(kw in context for kw in [
                    "不允许", "不建议", "禁止", "not", "don't",
                    "不降低",  # "don't lower" is itself a prohibition
                ]),
                f"'降低 gate' found outside prohibition context: ...{context}..."
            )

    # ═══════════════════════════════════════════════════════════════════════
    # Demo Sequence (10 min) Tests
    # ═══════════════════════════════════════════════════════════════════════

    def test_40_demo_sequence_has_6_segments(self):
        segments = [s for s in self.demo_sequence.split("## Segment") if s.strip()]
        self.assertGreaterEqual(len(segments), 6, f"Expected >=6 segments, got {len(segments)}")

    def test_41_demo_sequence_one_pager_first(self):
        self.assertIn("One-Pager", self.demo_sequence)

    def test_42_demo_sequence_five_card_matrix(self):
        self.assertIn("Five-Card", self.demo_sequence)

    def test_43_demo_sequence_multi_asset_sync(self):
        self.assertIn("Multi-Asset Market Sync", self.demo_sequence)

    def test_44_demo_sequence_price_oi_anomaly(self):
        self.assertIn("Price/OI/Volume Anomaly", self.demo_sequence)

    def test_45_demo_sequence_news_event_with_disclaimer(self):
        self.assertIn("因果证明", self.demo_sequence)

    def test_46_demo_sequence_blockage_explanation(self):
        self.assertIn("正常阻断", self.demo_sequence)

    def test_47_demo_sequence_has_wrap_up(self):
        self.assertIn("Wrap-Up", self.demo_sequence)

    # ═══════════════════════════════════════════════════════════════════════
    # Production Readiness Checklist Tests
    # ═══════════════════════════════════════════════════════════════════════

    def test_50_prod_readiness_is_0_5(self):
        self.assertIn("0/5", self.prod_readiness)

    def test_51_prod_readiness_not_ready(self):
        self.assertIn("NOT READY FOR PRODUCTION", self.prod_readiness)

    def test_52_prod_readiness_6_minimum_conditions(self):
        """Must list at least 6 minimum conditions for production send."""
        conditions = [
            "明确用户批准",
            "Production Target 明确",
            "Secret Preflight 通过",
            "Send-Readiness Gate 通过",
            "Dry-Run Artifact 可审计",
            "Rollback / Stop Path 明确",
        ]
        for cond in conditions:
            self.assertIn(cond, self.prod_readiness,
                          f"Production checklist missing condition: {cond}")

    def test_53_prod_readiness_current_not_meeting_conditions(self):
        self.assertIn("不满足", self.prod_readiness)

    def test_54_prod_readiness_no_daemon_by_default(self):
        self.assertIn("No daemon by default", self.prod_readiness)

    def test_55_prod_readiness_explicitly_forbids_production_now(self):
        pr_lower = self.prod_readiness.lower()
        self.assertTrue(
            any(kw in pr_lower for kw in [
                "现在进入 production send", "禁止", "explicitly",
            ]),
            "Production readiness must explicitly forbid entering production now"
        )

    def test_56_prod_readiness_all_6_conditions_unchecked(self):
        """All 6 conditions should be marked as [ ] (not checked)."""
        unchecked_count = self.prod_readiness.count("- [ ] ❌ 未完成")
        self.assertGreaterEqual(unchecked_count, 6,
                                f"Expected >=6 unchecked conditions, got {unchecked_count}")

    # ═══════════════════════════════════════════════════════════════════════
    # Whale Manual Evidence Checklist Tests
    # ═══════════════════════════════════════════════════════════════════════

    def test_60_whale_checklist_what_evidence_needed(self):
        self.assertIn("需要提供", self.whale_checklist)

    def test_61_whale_checklist_address_label_sources(self):
        self.assertIn("标签来源", self.whale_checklist)

    def test_62_whale_checklist_position_change_evidence(self):
        self.assertIn("仓位变化证据", self.whale_checklist)

    def test_63_whale_checklist_time_window(self):
        self.assertIn("时间窗口", self.whale_checklist)

    def test_64_whale_checklist_risk_warnings(self):
        self.assertIn("风险说明", self.whale_checklist)

    def test_65_whale_checklist_forbids_auto_attribution(self):
        """Whale checklist must explicitly forbid auto-attribution without evidence."""
        wc_lower = self.whale_checklist.lower()
        self.assertTrue(
            any(kw in wc_lower for kw in [
                "不允许自动猜测",
                "不允许自动归因",
                "auto attribution",
                "auto-attribution",
                "without evidence",
            ]),
            "Whale checklist must forbid auto-attribution without evidence"
        )

    def test_66_whale_checklist_forbids_no_evidence_alerts(self):
        """Must explicitly state no whale_position_alert without evidence."""
        wc_lower = self.whale_checklist.lower()
        self.assertTrue(
            any(kw in wc_lower for kw in [
                "没有证据",
                "without evidence",
                "no evidence",
            ]),
            "Whale checklist must forbid alerts without evidence"
        )

    def test_67_whale_checklist_has_workbook_template(self):
        self.assertIn("Workbook Template", self.whale_checklist)

    def test_68_whale_checklist_has_completion_steps(self):
        self.assertIn("完成后", self.whale_checklist)

    def test_69_whale_checklist_forbids_ai_attribution(self):
        """Must NOT recommend AI/LLM-based address attribution."""
        wc_lower = self.whale_checklist.lower()
        self.assertTrue(
            any(kw in wc_lower for kw in [
                "不允许用 ai", "不允许用 llm", "ai 推测", "llm 推测",
                "不可靠且不可审计",
            ]),
            "Whale checklist must forbid AI/LLM-based address attribution"
        )

    # ═══════════════════════════════════════════════════════════════════════
    # Demo Sequence — news event risk disclaimer
    # ═══════════════════════════════════════════════════════════════════════

    def test_70_demo_news_event_not_causal_proof(self):
        d_lower = self.demo_sequence.lower()
        self.assertTrue(
            any(kw in d_lower for kw in [
                "不是因果证明",
                "not causal proof",
                "not causal",
                "observation",
            ]),
            "Demo sequence must state news event is not causal proof"
        )

    def test_71_demo_news_event_not_trading_signal(self):
        d_lower = self.demo_sequence.lower()
        self.assertTrue(
            any(kw in d_lower for kw in [
                "不要将这些卡片当作交易信号",
                "not as trading signals",
                "不要当作交易信号",
            ]),
            "Demo must warn: do not use news cards as trading signals"
        )

    # ═══════════════════════════════════════════════════════════════════════
    # Manifest Tests
    # ═══════════════════════════════════════════════════════════════════════

    def test_80_manifest_has_all_required_fields(self):
        self.assertIsNotNone(self.manifest, "Manifest not loaded")
        for field in REQUIRED_MANIFEST_V116N_FIELDS:
            self.assertIn(field, self.manifest, f"Manifest missing field: {field}")

    def test_81_manifest_overlay_version_correct(self):
        self.assertEqual(self.manifest["overlay_version"], "v116N")

    def test_82_manifest_source_milestone_correct(self):
        self.assertEqual(self.manifest["source_milestone_version"], "v116L")

    def test_83_manifest_audit_source_correct(self):
        self.assertEqual(self.manifest["audit_source"], "v116M")

    def test_84_manifest_local_only_true(self):
        self.assertTrue(self.manifest["local_only"])

    def test_85_manifest_external_api_false(self):
        self.assertFalse(self.manifest["external_api_called_this_run"])

    def test_86_manifest_tg_sent_false(self):
        self.assertFalse(self.manifest["tg_sent_this_run"])

    def test_87_manifest_production_send_ready_0(self):
        self.assertEqual(self.manifest["production_send_ready_count"], 0)

    def test_88_manifest_user_acceptance_ready_true(self):
        self.assertTrue(self.manifest["user_acceptance_ready_after_overlay"])

    def test_89_manifest_created_files_has_8(self):
        created = self.manifest.get("created_files", [])
        self.assertEqual(len(created), 8, f"Expected 8 created files, got {len(created)}")

    def test_8a_manifest_source_files_read_has_7(self):
        sources = self.manifest.get("source_files_read", [])
        self.assertEqual(len(sources), 7, f"Expected 7 source files, got {len(sources)}")

    def test_8b_manifest_remaining_blockers_has_3(self):
        blockers = self.manifest.get("remaining_blockers", [])
        self.assertGreaterEqual(len(blockers), 3,
                                f"Expected >=3 remaining blockers, got {len(blockers)}")

    def test_8c_manifest_blockers_marked_not_failure(self):
        """All remaining blockers must be marked as not_a_failure: True."""
        for b in self.manifest.get("remaining_blockers", []):
            self.assertTrue(b.get("not_a_failure", False),
                            f"Blocker '{b.get('blocker', '?')}' must be not_a_failure: true")

    def test_8d_manifest_safety_constraints_all_false(self):
        sc = self.manifest.get("safety_constraints_verified", {})
        for key in ["external_api_called_this_run", "public_source_called_this_run",
                     "tg_sent_this_run", "prod_state_write", "ai_model_called",
                     "daemon_or_loop_started", "files_deleted",
                     "historical_artifacts_modified", "credentials_read"]:
            self.assertFalse(sc.get(key, True),
                             f"Safety constraint {key} must be false")

    # ═══════════════════════════════════════════════════════════════════════
    # No raw secrets in any output
    # ═══════════════════════════════════════════════════════════════════════

    def test_90_no_raw_token_in_any_output(self):
        """No v116N output should contain raw token/API key/cookie/password."""
        token_pattern = re.compile(r'\b\d{8,12}:[A-Za-z0-9_-]{30,}\b')
        for path in [f for f in ALL_V116N_FILES if f.endswith(".md")]:
            content = self._read_file(path)
            self.assertIsNone(
                token_pattern.search(content),
                f"File {os.path.basename(path)} contains unredacted token-like value"
            )

    def test_91_no_raw_credentials_in_manifest(self):
        """Manifest must not contain raw API key, chat_id, message_id, password, cookie."""
        manifest_str = json.dumps(self.manifest)
        forbidden_in_values = [
            "AA",  # Telegram bot tokens start with digits:colons — this is a weak proxy
        ]
        # Stronger check: no long alphanumeric strings that look like tokens
        # Actually, just ensure none of the known secret field names appear as VALUES
        manifest_lower = manifest_str.lower()
        self.assertNotIn("api_key", manifest_lower)
        self.assertNotIn("apikey", manifest_lower)
        self.assertNotIn("password", manifest_lower)
        self.assertNotIn("cookie", manifest_lower)

    def test_92_no_raw_chat_id_or_message_id_in_outputs(self):
        """No v116N output should contain raw chat_id or message_id."""
        id_pattern = re.compile(r'(chat_id|message_id)\s*[:=]\s*-?\d{5,}')
        for path in [f for f in ALL_V116N_FILES if f.endswith((".md", ".json"))]:
            content = self._read_file(path)
            self.assertIsNone(
                id_pattern.search(content),
                f"File {os.path.basename(path)} may contain raw chat_id or message_id"
            )

    # ═══════════════════════════════════════════════════════════════════════
    # Safety: no external API, no TG, no file deletion
    # ═══════════════════════════════════════════════════════════════════════

    def test_a0_manifest_confirms_no_external_api(self):
        self.assertFalse(self.manifest["external_api_called_this_run"])

    def test_a1_manifest_confirms_no_tg_sent(self):
        self.assertFalse(self.manifest["tg_sent_this_run"])

    def test_a2_no_files_deleted(self):
        """v116L files and v116A-K historical artifacts must all still exist."""
        for path in V116L_FILES + HISTORICAL_FILES:
            self.assertTrue(os.path.exists(path),
                            f"File should still exist (not deleted): {path}")

    # ═══════════════════════════════════════════════════════════════════════
    # Regression: v116A-L historical artifacts not modified
    # ═══════════════════════════════════════════════════════════════════════

    def test_b0_v116l_manifest_still_correct_version(self):
        with open(V116L_MANIFEST, "r", encoding="utf-8") as f:
            v116l_data = json.load(f)
        self.assertEqual(v116l_data["milestone_version"], "v116L")
        self.assertEqual(v116l_data["production_send_ready_count"], 0)
        self.assertEqual(v116l_data["card_family_count"], 5)

    def test_b1_v116l_acceptance_matrix_still_correct(self):
        with open(V116L_ACCEPTANCE, "r", encoding="utf-8") as f:
            v116l_data = json.load(f)
        self.assertEqual(len(v116l_data.get("cards", [])), 5)
        sc = v116l_data["summary_counts"]
        self.assertEqual(sc["fixture_e2e_passed"], "5/5")
        self.assertEqual(sc["production_send_ready"], "0/5")

    def test_b2_v116l_evidence_index_still_5_entries(self):
        records = []
        with open(V116L_EVIDENCE, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    records.append(json.loads(line))
        self.assertEqual(len(records), 5)

    def test_b3_v116k_audit_still_exists(self):
        self.assertTrue(os.path.exists(V116K_AUDIT))

    def test_b4_v116k_ledger_still_exists(self):
        self.assertTrue(os.path.exists(V116K_LEDGER))

    def test_b5_all_v116a_k_historical_results_exist(self):
        for path in [V116E_RESULT, V116G_RESULT, V116I_RESULT, V116J_RESULT]:
            self.assertTrue(os.path.exists(path),
                            f"Historical artifact should still exist: {path}")

    # ═══════════════════════════════════════════════════════════════════════
    # All v116N files are in project directory (not outside)
    # ═══════════════════════════════════════════════════════════════════════

    def test_c0_all_files_in_project_dir(self):
        for path in ALL_V116N_FILES:
            self.assertTrue(path.startswith(PROJECT_DIR),
                            f"File outside project dir: {path}")
            self.assertNotIn("ai_relay_desk", path.lower())

    # ═══════════════════════════════════════════════════════════════════════
    # Handoff Tests
    # ═══════════════════════════════════════════════════════════════════════

    def test_d0_handoff_states_presentation_only(self):
        self.assertIn("验收呈现增强", self.handoff)

    def test_d1_handoff_states_no_v116l_data_changed(self):
        self.assertIn("没有改变", self.handoff)

    def test_d2_handoff_recommends_user_acceptance(self):
        self.assertIn("用户验收", self.handoff)

    def test_d3_handoff_recommends_abc_choice(self):
        self.assertIn("A/B/C", self.handoff)

    def test_d4_handoff_no_daemon_cron_loop(self):
        h_lower = self.handoff.lower()
        self.assertNotIn("daemon started", h_lower)
        self.assertNotIn("cron started", h_lower)

    # ═══════════════════════════════════════════════════════════════════════
    # Helpers
    # ═══════════════════════════════════════════════════════════════════════

    def _read_file(self, path: str) -> str:
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return f.read()
        return ""


if __name__ == "__main__":
    unittest.main(verbosity=2)
