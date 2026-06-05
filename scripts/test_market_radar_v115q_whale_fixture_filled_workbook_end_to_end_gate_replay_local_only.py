#!/usr/bin/env python3
"""
v115Q — Tests for Whale Fixture Filled Workbook End-to-End Gate Replay (Local Only)

Validates all v115Q outputs meet the acceptance criteria defined in the task spec.
"""

import csv
import hashlib
import json
import os
import sys
import unittest


# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Inputs
V115F_WORKBOOK = os.path.join(
    PROJECT_DIR, "runs", "market_radar", "v115f_whale_address_audit_operator_workbook.csv"
)
V115P_FIXTURE_CSV = os.path.join(
    PROJECT_DIR, "runs", "market_radar", "v115p_whale_operator_fixture_filled_workbook.csv"
)

# v115Q outputs to validate
INTAKE_REPLAY_JSONL = os.path.join(
    PROJECT_DIR, "results", "market_radar_v115q_whale_fixture_intake_replay_records.jsonl"
)
SCORING_REPLAY_JSONL = os.path.join(
    PROJECT_DIR, "results", "market_radar_v115q_whale_fixture_scoring_replay_records.jsonl"
)
ADJUDICATION_REPLAY_JSONL = os.path.join(
    PROJECT_DIR, "results", "market_radar_v115q_whale_fixture_adjudication_replay_records.jsonl"
)
WORKFLOW_REPLAY_JSONL = os.path.join(
    PROJECT_DIR, "results", "market_radar_v115q_whale_fixture_workflow_replay_decisions.jsonl"
)
RESULT_JSON = os.path.join(
    PROJECT_DIR, "results", "market_radar_v115q_whale_fixture_end_to_end_gate_replay_result.json"
)
REPORT_MD = os.path.join(
    PROJECT_DIR, "runs", "market_radar", "v115q_whale_fixture_filled_workbook_end_to_end_gate_replay.md"
)
REPORT_CSV = os.path.join(
    PROJECT_DIR, "runs", "market_radar", "v115q_whale_fixture_filled_workbook_end_to_end_gate_replay.csv"
)
HANDOFF_MD = os.path.join(
    PROJECT_DIR, "runs", "market_radar", "v115q_whale_fixture_filled_workbook_end_to_end_gate_replay_local_only_handoff.md"
)


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            chunk = f.read(65536)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def load_jsonl(path):
    rows = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def read_csv_rows(path):
    with open(path, "r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        return reader.fieldnames, [row for row in reader]


def read_text(path):
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


class TestV115QGateReplayOutputs(unittest.TestCase):
    """Validate all v115Q end-to-end gate replay outputs."""

    @classmethod
    def setUpClass(cls):
        # Load all outputs
        cls.real_headers, cls.real_rows = read_csv_rows(V115F_WORKBOOK)
        cls.fixture_headers, cls.fixture_rows = read_csv_rows(V115P_FIXTURE_CSV)
        cls.intake_records = load_jsonl(INTAKE_REPLAY_JSONL)
        cls.scoring_records = load_jsonl(SCORING_REPLAY_JSONL)
        cls.adj_records = load_jsonl(ADJUDICATION_REPLAY_JSONL)
        cls.wf_records = load_jsonl(WORKFLOW_REPLAY_JSONL)
        cls.result = load_json(RESULT_JSON)
        cls.report_md = read_text(REPORT_MD)
        cls.report_csv_headers, cls.report_csv_rows = read_csv_rows(REPORT_CSV)
        cls.handoff_md = read_text(HANDOFF_MD)
        cls.real_hash_before = cls.result["real_workbook_sha256_before"]
        cls.real_hash_after = cls.result["real_workbook_sha256_after"]
        cls.current_real_hash = sha256_file(V115F_WORKBOOK)

    # ════════════════════════════════════════════════════════════════════
    # Count tests
    # ════════════════════════════════════════════════════════════════════

    def test_fixture_rows_4(self):
        """fixture_rows == 4"""
        self.assertEqual(len(self.fixture_rows), 4,
                         f"Expected 4 fixture rows, got {len(self.fixture_rows)}")
        self.assertEqual(self.result["fixture_rows"], 4)

    def test_intake_replay_records_4(self):
        """fixture_intake_replay_records == 4"""
        self.assertEqual(len(self.intake_records), 4,
                         f"Expected 4 intake records, got {len(self.intake_records)}")
        self.assertEqual(self.result["fixture_intake_replay_records"], 4)

    def test_scoring_replay_records_4(self):
        """fixture_scoring_replay_records == 4"""
        self.assertEqual(len(self.scoring_records), 4,
                         f"Expected 4 scoring records, got {len(self.scoring_records)}")
        self.assertEqual(self.result["fixture_scoring_replay_records"], 4)

    def test_adjudication_replay_records_4(self):
        """fixture_adjudication_replay_records == 4"""
        self.assertEqual(len(self.adj_records), 4,
                         f"Expected 4 adj records, got {len(self.adj_records)}")
        self.assertEqual(self.result["fixture_adjudication_replay_records"], 4)

    def test_workflow_replay_decisions_4(self):
        """fixture_workflow_replay_decisions == 4"""
        self.assertEqual(len(self.wf_records), 4,
                         f"Expected 4 wf decisions, got {len(self.wf_records)}")
        self.assertEqual(self.result["fixture_workflow_replay_decisions"], 4)

    def test_intake_ready_count_4(self):
        """fixture_intake_ready_count == 4"""
        self.assertEqual(self.result["fixture_intake_ready_count"], 4,
                         f"Expected 4, got {self.result['fixture_intake_ready_count']}")

    def test_scoring_passed_count_4(self):
        """fixture_scoring_passed_count == 4"""
        self.assertEqual(self.result["fixture_scoring_passed_count"], 4,
                         f"Expected 4, got {self.result['fixture_scoring_passed_count']}")

    def test_adjudication_ready_count_4(self):
        """fixture_adjudication_ready_count == 4"""
        self.assertEqual(self.result["fixture_adjudication_ready_count"], 4,
                         f"Expected 4, got {self.result['fixture_adjudication_ready_count']}")

    def test_workflow_ready_count_4(self):
        """fixture_workflow_ready_count == 4"""
        self.assertEqual(self.result["fixture_workflow_ready_count"], 4,
                         f"Expected 4, got {self.result['fixture_workflow_ready_count']}")

    def test_upgrade_preview_allowed_count_4(self):
        """fixture_upgrade_preview_allowed_count == 4"""
        self.assertEqual(self.result["fixture_upgrade_preview_allowed_count"], 4,
                         f"Expected 4, got {self.result['fixture_upgrade_preview_allowed_count']}")

    def test_low_unknown_workflow_ready_2(self):
        """low_unknown_fixture_workflow_ready_count == 2"""
        self.assertEqual(self.result["low_unknown_fixture_workflow_ready_count"], 2,
                         f"Expected 2, got {self.result['low_unknown_fixture_workflow_ready_count']}")

    def test_medium_workflow_ready_2(self):
        """medium_fixture_workflow_ready_count == 2"""
        self.assertEqual(self.result["medium_fixture_workflow_ready_count"], 2,
                         f"Expected 2, got {self.result['medium_fixture_workflow_ready_count']}")

    def test_manual_attribution_ready_2(self):
        """manual_attribution_fixture_ready_count == 2"""
        self.assertEqual(self.result["manual_attribution_fixture_ready_count"], 2,
                         f"Expected 2, got {self.result['manual_attribution_fixture_ready_count']}")

    def test_corroboration_ready_2(self):
        """corroboration_fixture_ready_count == 2"""
        self.assertEqual(self.result["corroboration_fixture_ready_count"], 2,
                         f"Expected 2, got {self.result['corroboration_fixture_ready_count']}")

    def test_real_workbook_rows_4(self):
        """real_workbook_rows == 4"""
        self.assertEqual(len(self.real_rows), 4)
        self.assertEqual(self.result["real_workbook_rows"], 4)

    # ════════════════════════════════════════════════════════════════════
    # Safety / flag tests
    # ════════════════════════════════════════════════════════════════════

    def test_real_workbook_sha256_match(self):
        """real_workbook_sha256_before == real_workbook_sha256_after"""
        self.assertEqual(self.real_hash_before, self.real_hash_after,
                         "SHA-256 before/after must match (workbook unchanged)")

    def test_real_workbook_sha256_current(self):
        """Current real workbook hash must match stored hash"""
        self.assertEqual(self.current_real_hash, self.real_hash_before,
                         "Real workbook has been modified since v115Q run")

    def test_real_workbook_modified_false(self):
        """real_workbook_modified == false"""
        self.assertFalse(self.result["real_workbook_modified"],
                         "real_workbook_modified should be False")

    def test_real_label_upgrade_performed_false(self):
        """real_label_upgrade_performed == false"""
        self.assertFalse(self.result["real_label_upgrade_performed"],
                         "Real label upgrade should be False")

    def test_real_send_candidate_generated_false(self):
        """real_send_candidate_generated == false"""
        self.assertFalse(self.result["real_send_candidate_generated"],
                         "Real send candidate should be False")

    def test_send_ready_false(self):
        """send_ready == false"""
        self.assertFalse(self.result["send_ready"],
                         "send_ready should be False")

    def test_tg_test_group_ready_false(self):
        """tg_test_group_ready == false"""
        self.assertFalse(self.result["tg_test_group_ready"],
                         "tg_test_group_ready should be False")

    def test_tg_sent_false(self):
        """tg_sent == false"""
        self.assertFalse(self.result["tg_sent"],
                         "tg_sent should be False")

    def test_prod_state_write_false(self):
        """prod_state_write == false"""
        self.assertFalse(self.result["prod_state_write"],
                         "prod_state_write should be False")

    def test_external_api_called_false(self):
        """external_api_called == false"""
        self.assertFalse(self.result["external_api_called"],
                         "external_api_called should be False")

    def test_credentials_read_false(self):
        """credentials_read == false"""
        self.assertFalse(self.result["credentials_read"],
                         "credentials_read should be False")

    def test_fixture_only_true(self):
        """fixture_only == true"""
        self.assertTrue(self.result["fixture_only"],
                        "fixture_only should be True")

    def test_next_gate_command_order_enforced_true(self):
        """next_gate_command_order_enforced == true"""
        self.assertTrue(self.result["next_gate_command_order_enforced"],
                        "next_gate_command_order_enforced should be True")

    # ════════════════════════════════════════════════════════════════════
    # JSONL file row count tests
    # ════════════════════════════════════════════════════════════════════

    def test_intake_jsonl_rows_4(self):
        """JSONL intake replay rows == 4"""
        self.assertEqual(len(self.intake_records), 4,
                         f"Expected 4 intake JSONL rows, got {len(self.intake_records)}")

    def test_scoring_jsonl_rows_4(self):
        """JSONL scoring replay rows == 4"""
        self.assertEqual(len(self.scoring_records), 4,
                         f"Expected 4 scoring JSONL rows, got {len(self.scoring_records)}")

    def test_adjudication_jsonl_rows_4(self):
        """JSONL adjudication replay rows == 4"""
        self.assertEqual(len(self.adj_records), 4,
                         f"Expected 4 adj JSONL rows, got {len(self.adj_records)}")

    def test_workflow_jsonl_rows_4(self):
        """JSONL workflow replay rows == 4"""
        self.assertEqual(len(self.wf_records), 4,
                         f"Expected 4 wf JSONL rows, got {len(self.wf_records)}")

    # ════════════════════════════════════════════════════════════════════
    # CSV tests
    # ════════════════════════════════════════════════════════════════════

    def test_csv_data_rows_4(self):
        """CSV data rows == 4"""
        self.assertEqual(len(self.report_csv_rows), 4,
                         f"Expected 4 CSV data rows, got {len(self.report_csv_rows)}")

    # ════════════════════════════════════════════════════════════════════
    # Markdown tests
    # ════════════════════════════════════════════════════════════════════

    def test_markdown_contains_4_addresses(self):
        """Markdown contains 4 addresses"""
        for row in self.fixture_rows:
            short_addr = row["address"][:10]
            self.assertIn(short_addr, self.report_md,
                          f"Report MD should contain address {short_addr}")

    def test_markdown_contains_fixture_only_warning(self):
        """Markdown contains fixture-only warning"""
        report_lower = self.report_md.lower()
        found = any(phrase in report_lower for phrase in [
            "fixture only", "fixture-only", "test_only",
            "not real", "does not mean",
        ])
        self.assertTrue(found, "Report MD should contain fixture-only warnings")

    # ════════════════════════════════════════════════════════════════════
    # Low/unknown whale replay tests
    # ════════════════════════════════════════════════════════════════════

    def test_low_fixture_manual_attribution_required(self):
        """Low/unknown replay rows must require manual attribution"""
        for i, row in enumerate(self.fixture_rows):
            if row.get("current_confidence") == "low":
                wf = self.wf_records[i]
                self.assertTrue(wf.get("manual_attribution_replay_ready"),
                                f"Low whale {row['address'][:10]} must have manual_attribution_replay_ready=true")
                self.assertEqual(wf.get("action_type_replay", ""), "manual_attribution_required",
                                 f"Low whale {row['address'][:10]} should have action_type_replay=manual_attribution_required")

    def test_low_fixture_must_have_trusted_primary(self):
        """Low/unknown must have trusted_primary_source"""
        for i, intake in enumerate(self.intake_records):
            if self.fixture_rows[i].get("current_confidence") == "low":
                self.assertIn("trusted_source_label_value", intake.get("present_fields", []),
                              f"Low whale intake missing trusted primary source")

    def test_low_fixture_must_have_second_source(self):
        """Low/unknown must have independent_second_source_or_cross_source"""
        for i, intake in enumerate(self.intake_records):
            if self.fixture_rows[i].get("current_confidence") == "low":
                self.assertIn("second_source_label_value", intake.get("present_fields", []),
                              f"Low whale intake missing second source")

    def test_low_fixture_must_have_activity_pattern(self):
        """Low/unknown must have activity_pattern_note"""
        for i, intake in enumerate(self.intake_records):
            if self.fixture_rows[i].get("current_confidence") == "low":
                self.assertIn("activity_pattern_note", intake.get("present_fields", []),
                              f"Low whale intake missing activity pattern")

    def test_low_fixture_must_have_operator_confirmation(self):
        """Low/unknown must have operator_confirmation"""
        for i, intake in enumerate(self.intake_records):
            if self.fixture_rows[i].get("current_confidence") == "low":
                self.assertIn("operator_confirmed_label", intake.get("present_fields", []),
                              f"Low whale intake missing operator confirmation")
                self.assertIn("operator_confidence_assessment", intake.get("present_fields", []),
                              f"Low whale intake missing operator confidence")

    # ════════════════════════════════════════════════════════════════════
    # Medium confidence replay tests
    # ════════════════════════════════════════════════════════════════════

    def test_medium_fixture_corroboration_required(self):
        """Medium replay rows must require corroboration"""
        for i, row in enumerate(self.fixture_rows):
            if row.get("current_confidence") == "medium":
                wf = self.wf_records[i]
                self.assertTrue(wf.get("corroboration_replay_ready"),
                                f"Medium address {row['address'][:10]} must have corroboration_replay_ready=true")
                self.assertEqual(wf.get("action_type_replay", ""), "corroboration_required",
                                 f"Medium address {row['address'][:10]} should have action_type_replay=corroboration_required")

    def test_medium_fixture_must_not_claim_direct_tg(self):
        """Medium must_not_claim_direct_tg_test_group_ready == true"""
        for i, row in enumerate(self.fixture_rows):
            if row.get("current_confidence") == "medium":
                wf = self.wf_records[i]
                self.assertTrue(wf.get("must_not_claim_direct_tg_test_group_ready"),
                                f"Medium address {row['address'][:10]} must have must_not_claim_direct_tg_test_group_ready=true")

    def test_medium_fixture_must_have_existing_label_or_trusted_primary(self):
        """Medium must have existing_label_source_or_trusted_primary_source"""
        for i, intake in enumerate(self.intake_records):
            if self.fixture_rows[i].get("current_confidence") == "medium":
                self.assertIn("trusted_source_label_value", intake.get("present_fields", []),
                              f"Medium address intake missing trusted source")

    # ════════════════════════════════════════════════════════════════════
    # Per-record safety field tests
    # ════════════════════════════════════════════════════════════════════

    def test_each_intake_record_fixture_only(self):
        """Each intake record must have fixture_only = true"""
        for r in self.intake_records:
            self.assertTrue(r.get("fixture_only"),
                            f"Intake record for {r['address'][:10]} should have fixture_only=True")

    def test_each_intake_record_safety_flags(self):
        """Each intake record must have all safety flags false"""
        for r in self.intake_records:
            self.assertFalse(r.get("real_workbook_modified"),
                             f"Intake record for {r['address'][:10]}: real_workbook_modified should be False")
            self.assertFalse(r.get("real_label_upgrade_performed"),
                             f"Intake record for {r['address'][:10]}: real_label_upgrade_performed should be False")
            self.assertFalse(r.get("send_ready"),
                             f"Intake record for {r['address'][:10]}: send_ready should be False")
            self.assertFalse(r.get("tg_test_group_ready"),
                             f"Intake record for {r['address'][:10]}: tg_test_group_ready should be False")
            self.assertFalse(r.get("external_api_called"),
                             f"Intake record for {r['address'][:10]}: external_api_called should be False")
            self.assertFalse(r.get("credentials_read"),
                             f"Intake record for {r['address'][:10]}: credentials_read should be False")

    def test_each_scoring_record_fixture_only(self):
        """Each scoring record must have fixture_only = true"""
        for r in self.scoring_records:
            self.assertTrue(r.get("fixture_only"),
                            f"Scoring record for {r['address'][:10]} should have fixture_only=True")

    def test_each_adj_record_fixture_only(self):
        """Each adjudication record must have fixture_only = true"""
        for r in self.adj_records:
            self.assertTrue(r.get("fixture_only"),
                            f"Adj record for {r['address'][:10]} should have fixture_only=True")

    def test_each_wf_record_fixture_only(self):
        """Each workflow record must have fixture_only = true"""
        for r in self.wf_records:
            self.assertTrue(r.get("fixture_only"),
                            f"WF record for {r['address'][:10]} should have fixture_only=True")

    def test_each_wf_record_real_label_upgrade_performed_false(self):
        """Each workflow record must have real_label_upgrade_performed = false"""
        for r in self.wf_records:
            self.assertFalse(r.get("real_label_upgrade_performed"),
                             f"WF record for {r['address'][:10]}: real_label_upgrade_performed should be False")

    def test_each_wf_record_send_ready_false(self):
        """Each workflow record must have send_ready = false"""
        for r in self.wf_records:
            self.assertFalse(r.get("send_ready"),
                             f"WF record for {r['address'][:10]}: send_ready should be False")

    def test_each_wf_record_tg_test_group_ready_false(self):
        """Each workflow record must have tg_test_group_ready = false"""
        for r in self.wf_records:
            self.assertFalse(r.get("tg_test_group_ready"),
                             f"WF record for {r['address'][:10]}: tg_test_group_ready should be False")

    def test_each_wf_record_tg_sent_false(self):
        """Each workflow record must have tg_sent = false"""
        for r in self.wf_records:
            self.assertFalse(r.get("tg_sent"),
                             f"WF record for {r['address'][:10]}: tg_sent should be False")

    def test_each_wf_record_prod_state_write_false(self):
        """Each workflow record must have prod_state_write = false"""
        for r in self.wf_records:
            self.assertFalse(r.get("prod_state_write"),
                             f"WF record for {r['address'][:10]}: prod_state_write should be False")

    def test_each_wf_record_external_api_called_false(self):
        """Each workflow record must have external_api_called = false"""
        for r in self.wf_records:
            self.assertFalse(r.get("external_api_called"),
                             f"WF record for {r['address'][:10]}: external_api_called should be False")

    def test_each_wf_record_credentials_read_false(self):
        """Each workflow record must have credentials_read = false"""
        for r in self.wf_records:
            self.assertFalse(r.get("credentials_read"),
                             f"WF record for {r['address'][:10]}: credentials_read should be False")

    # ════════════════════════════════════════════════════════════════════
    # No fake pass / synthetic claims tests
    # ════════════════════════════════════════════════════════════════════

    def test_no_fake_pass_as_real_pass_in_report(self):
        """Fixture replay pass must not be presented as real pass"""
        report_lower = self.report_md.lower()
        forbidden = [
            "fixture pass means real pass",
            "fixture passing proves the addresses",
            "real addresses passed",
            "real address passed",
        ]
        for phrase in forbidden:
            self.assertNotIn(phrase, report_lower,
                             f"Report contains forbidden phrase: '{phrase}'")

    def test_no_fixture_pass_equals_real_in_handoff(self):
        """Handoff must not claim fixture pass equals real pass"""
        handoff_lower = self.handoff_md.lower()
        forbidden = [
            "fixture replay pass = real",
            "fixture replay pass equals",
        ]
        for phrase in forbidden:
            self.assertNotIn(phrase, handoff_lower,
                             f"Handoff contains forbidden phrase: '{phrase}'")

    def test_report_contains_safety_warnings(self):
        """Report must contain explicit fixture-only warnings"""
        text = self.report_md + self.handoff_md
        combined = text.lower()
        warnings = [
            "fixture only",
            "not real",
        ]
        for w in warnings:
            self.assertIn(w, combined, f"Must contain '{w}' warning")

    # ════════════════════════════════════════════════════════════════════
    # Real workbook integrity tests
    # ════════════════════════════════════════════════════════════════════

    def test_real_workbook_still_byte_identical(self):
        """Real v115F workbook must remain byte-identical"""
        self.assertEqual(self.current_real_hash, self.real_hash_before,
                         "Real v115F workbook was modified!")

    def test_real_workbook_evidence_fields_still_empty(self):
        """Real workbook evidence fields must still be empty"""
        for row in self.real_rows:
            for field in [
                "trusted_source_label_value", "trusted_source_url_or_note",
                "second_source_label_value", "second_source_url_or_note",
                "activity_pattern_note", "operator_confirmed_label",
                "operator_confidence_assessment", "reviewer", "reviewed_at",
            ]:
                value = (row.get(field) or "").strip()
                self.assertEqual(value, "",
                                 f"Real workbook field {field} for {row['address'][:10]} "
                                 f"should be empty, got: {value[:50]}")

    # ════════════════════════════════════════════════════════════════════
    # Gate replay sequence order test
    # ════════════════════════════════════════════════════════════════════

    def test_gate_replay_order_enforced(self):
        """Gate replay order must be enforced in output metadata"""
        self.assertTrue(self.result.get("next_gate_command_order_enforced"),
                        "next_gate_command_order_enforced should be True")

    def test_all_4_gates_produced_output(self):
        """All 4 gates must have produced output"""
        self.assertTrue(os.path.exists(INTAKE_REPLAY_JSONL))
        self.assertTrue(os.path.exists(SCORING_REPLAY_JSONL))
        self.assertTrue(os.path.exists(ADJUDICATION_REPLAY_JSONL))
        self.assertTrue(os.path.exists(WORKFLOW_REPLAY_JSONL))

    # ════════════════════════════════════════════════════════════════════
    # Scoring detail tests
    # ════════════════════════════════════════════════════════════════════

    def test_all_scoring_records_passed_9_of_9(self):
        """All scoring records should have evidence_score >= 9"""
        for r in self.scoring_records:
            if r["scoring_replay_passed"]:
                self.assertGreaterEqual(r.get("evidence_score_replay", 0), 9,
                                        f"Scoring for {r['address'][:10]} should have score >= 9")

    def test_all_scoring_records_hc_passed(self):
        """All scoring records should have all HC requirements passed"""
        for r in self.scoring_records:
            if r["scoring_replay_passed"]:
                self.assertEqual(len(r.get("hc_requirements_failed", [])), 0,
                                 f"Scoring for {r['address'][:10]} should have 0 failed HC reqs")
                self.assertEqual(len(r.get("hc_requirements_passed", [])), 9,
                                 f"Scoring for {r['address'][:10]} should have 9 passed HC reqs")

    # ════════════════════════════════════════════════════════════════════
    # CSV field tests
    # ════════════════════════════════════════════════════════════════════

    def test_csv_contains_required_columns(self):
        """CSV must contain all required columns"""
        required = [
            "address", "display_label", "current_confidence", "action_type",
            "intake_replay_ready", "scoring_replay_passed",
            "adjudication_replay_ready", "workflow_replay_ready",
            "upgrade_preview_replay_allowed", "fixture_only",
            "real_workbook_modified", "real_label_upgrade_performed",
            "real_send_candidate_generated", "send_ready",
            "tg_test_group_ready", "tg_sent",
        ]
        for col in required:
            self.assertIn(col, self.report_csv_headers,
                          f"CSV missing column: {col}")

    def test_csv_all_safety_flags_false(self):
        """CSV all safety flags must be false"""
        for row in self.report_csv_rows:
            self.assertEqual(row.get("real_workbook_modified", ""), "false")
            self.assertEqual(row.get("real_label_upgrade_performed", ""), "false")
            self.assertEqual(row.get("send_ready", ""), "false")
            self.assertEqual(row.get("tg_test_group_ready", ""), "false")
            self.assertEqual(row.get("fixture_only", ""), "true")

    # ════════════════════════════════════════════════════════════════════
    # Low/unknown must not claim real attribution
    # ════════════════════════════════════════════════════════════════════

    def test_low_replay_not_claim_real_attribution(self):
        """Low/unknown replay rows must not claim real attribution"""
        for i, wf in enumerate(self.wf_records):
            if self.fixture_rows[i].get("current_confidence") == "low":
                # real_label_upgrade_performed must be false
                self.assertFalse(wf.get("real_label_upgrade_performed"),
                                 f"Low wf record should have real_label_upgrade_performed=false")
                # Check replay_warning doesn't claim real attribution
                warning = wf.get("replay_warning", "").lower()
                # Should contain fixture/not-real language
                fixture_terms = ["fixture", "not real", "test_only", "no real"]
                has_warning = any(t in warning for t in fixture_terms)
                self.assertTrue(has_warning,
                                f"Low wf record warning should contain fixture-only language: {warning[:100]}")

    def test_medium_replay_not_claim_direct_tg_ready(self):
        """Medium replay rows must not claim direct TG readiness"""
        for i, wf in enumerate(self.wf_records):
            if self.fixture_rows[i].get("current_confidence") == "medium":
                # tg_test_group_ready must be false
                self.assertFalse(wf.get("tg_test_group_ready"),
                                 f"Medium wf record should have tg_test_group_ready=false")
                # replay_warning must not claim TG is ready
                warning = wf.get("replay_warning", "").lower()
                self.assertNotIn("tg test group ready", warning,
                                 f"Medium wf record should not claim TG test group ready")


if __name__ == "__main__":
    runner = unittest.TextTestRunner(verbosity=2)
    suite = unittest.TestLoader().loadTestsFromTestCase(TestV115QGateReplayOutputs)
    result = runner.run(suite)

    if result.wasSuccessful():
        print("\n" + "=" * 60)
        print("ALL v115Q TESTS PASSED")
        print("=" * 60)
        sys.exit(0)
    else:
        print("\n" + "=" * 60)
        print(f"v115Q TESTS FAILED: {len(result.failures)} failures, {len(result.errors)} errors")
        print("=" * 60)
        sys.exit(1)
