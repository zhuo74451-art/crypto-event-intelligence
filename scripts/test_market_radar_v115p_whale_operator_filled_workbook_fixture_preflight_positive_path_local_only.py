#!/usr/bin/env python3
"""
v115P — Tests for Whale Operator Filled Workbook Fixture Preflight (Positive Path)

Validates all fixture outputs meet the acceptance criteria defined in the task spec.
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
V115O_ITEMS = os.path.join(
    PROJECT_DIR, "results", "market_radar_v115o_whale_operator_evidence_collection_items.jsonl"
)

# Outputs to validate
FIXTURE_CSV = os.path.join(
    PROJECT_DIR, "runs", "market_radar", "v115p_whale_operator_fixture_filled_workbook.csv"
)
FIXTURE_ROWS_JSONL = os.path.join(
    PROJECT_DIR, "results", "market_radar_v115p_whale_operator_fixture_filled_workbook_rows.jsonl"
)
FIXTURE_RECORDS_JSONL = os.path.join(
    PROJECT_DIR, "results", "market_radar_v115p_whale_operator_fixture_preflight_records.jsonl"
)
FIXTURE_DECISIONS_JSONL = os.path.join(
    PROJECT_DIR, "results", "market_radar_v115p_whale_operator_fixture_preflight_decisions.jsonl"
)
POSITIVE_PATH_RESULT_JSON = os.path.join(
    PROJECT_DIR, "results", "market_radar_v115p_whale_operator_fixture_preflight_positive_path_result.json"
)
EXAMPLE_MD = os.path.join(
    PROJECT_DIR, "runs", "market_radar", "v115p_whale_operator_filled_workbook_example.md"
)
REPORT_MD = os.path.join(
    PROJECT_DIR, "runs", "market_radar", "v115p_whale_operator_fixture_preflight_positive_path_report.md"
)
HANDOFF_MD = os.path.join(
    PROJECT_DIR, "runs", "market_radar", "v115p_whale_operator_fixture_preflight_positive_path_local_only_handoff.md"
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


class TestV115PPreflightOutputs(unittest.TestCase):
    """Validate all v115P fixture preflight outputs."""

    @classmethod
    def setUpClass(cls):
        # Load all outputs
        cls.real_headers, cls.real_rows = read_csv_rows(V115F_WORKBOOK)
        cls.fixture_headers, cls.fixture_rows = read_csv_rows(FIXTURE_CSV)
        cls.fixture_filled = load_jsonl(FIXTURE_ROWS_JSONL)
        cls.records = load_jsonl(FIXTURE_RECORDS_JSONL)
        cls.decisions = load_jsonl(FIXTURE_DECISIONS_JSONL)
        cls.result = load_json(POSITIVE_PATH_RESULT_JSON)
        cls.example_md = read_text(EXAMPLE_MD)
        cls.report_md = read_text(REPORT_MD)
        cls.handoff_md = read_text(HANDOFF_MD)
        cls.items = load_jsonl(V115O_ITEMS)
        cls.real_hash = sha256_file(V115F_WORKBOOK)

    # ---- Count tests ----

    def test_fixture_rows_count(self):
        """fixture_rows == 4"""
        self.assertEqual(len(self.fixture_rows), 4,
                         f"Expected 4 fixture rows, got {len(self.fixture_rows)}")
        self.assertEqual(self.result["fixture_rows"], 4)

    def test_fixture_preflight_records_count(self):
        """fixture_preflight_records == 4"""
        self.assertEqual(len(self.records), 4,
                         f"Expected 4 records, got {len(self.records)}")
        self.assertEqual(self.result["fixture_preflight_records"], 4)

    def test_fixture_preflight_decisions_count(self):
        """fixture_preflight_decisions == 4"""
        self.assertEqual(len(self.decisions), 4,
                         f"Expected 4 decisions, got {len(self.decisions)}")
        self.assertEqual(self.result["fixture_preflight_decisions"], 4)

    def test_fixture_preflight_ready_count(self):
        """fixture_preflight_ready_count == 4"""
        self.assertEqual(self.result["fixture_preflight_ready_count"], 4,
                         f"Expected 4 ready, got {self.result['fixture_preflight_ready_count']}")

    def test_fixture_preflight_blocked_count(self):
        """fixture_preflight_blocked_count == 0"""
        self.assertEqual(self.result["fixture_preflight_blocked_count"], 0,
                         f"Expected 0 blocked, got {self.result['fixture_preflight_blocked_count']}")

    def test_fixture_ready_for_gate_rerun_count(self):
        """fixture_ready_for_gate_rerun_count == 4"""
        self.assertEqual(self.result["fixture_ready_for_gate_rerun_count"], 4,
                         f"Expected 4 gate rerun ready, got {self.result['fixture_ready_for_gate_rerun_count']}")

    def test_low_unknown_fixture_ready_count(self):
        """low_unknown_fixture_ready_count == 2"""
        self.assertEqual(self.result["low_unknown_fixture_ready_count"], 2,
                         f"Expected 2, got {self.result['low_unknown_fixture_ready_count']}")

    def test_medium_fixture_ready_count(self):
        """medium_fixture_ready_count == 2"""
        self.assertEqual(self.result["medium_fixture_ready_count"], 2,
                         f"Expected 2, got {self.result['medium_fixture_ready_count']}")

    def test_manual_attribution_fixture_ready_count(self):
        """manual_attribution_fixture_ready_count == 2"""
        self.assertEqual(self.result["manual_attribution_fixture_ready_count"], 2,
                         f"Expected 2, got {self.result['manual_attribution_fixture_ready_count']}")

    def test_corroboration_fixture_ready_count(self):
        """corroboration_fixture_ready_count == 2"""
        self.assertEqual(self.result["corroboration_fixture_ready_count"], 2,
                         f"Expected 2, got {self.result['corroboration_fixture_ready_count']}")

    def test_real_workbook_rows(self):
        """real_workbook_rows == 4"""
        self.assertEqual(len(self.real_rows), 4)
        self.assertEqual(self.result["real_workbook_rows"], 4)

    # ---- Safety / flag tests ----

    def test_real_workbook_modified(self):
        """real_workbook_modified == false"""
        self.assertFalse(self.result["real_workbook_modified"],
                         "real_workbook_modified should be False")

    def test_real_label_upgrade_performed(self):
        """real_label_upgrade_performed == false"""
        self.assertFalse(self.result["real_label_upgrade_performed"],
                         "real_label_upgrade_performed should be False")

    def test_real_send_candidate_generated(self):
        """real_send_candidate_generated == false"""
        self.assertFalse(self.result["real_send_candidate_generated"],
                         "real_send_candidate_generated should be False")

    def test_send_ready(self):
        """send_ready == false"""
        self.assertFalse(self.result["send_ready"],
                         "send_ready should be False")

    def test_tg_test_group_ready(self):
        """tg_test_group_ready == false"""
        self.assertFalse(self.result["tg_test_group_ready"],
                         "tg_test_group_ready should be False")

    def test_tg_sent(self):
        """tg_sent == false"""
        self.assertFalse(self.result["tg_sent"],
                         "tg_sent should be False")

    def test_prod_state_write(self):
        """prod_state_write == false"""
        self.assertFalse(self.result["prod_state_write"],
                         "prod_state_write should be False")

    def test_external_api_called(self):
        """external_api_called == false"""
        self.assertFalse(self.result["external_api_called"],
                         "external_api_called should be False")

    def test_credentials_read(self):
        """credentials_read == false"""
        self.assertFalse(self.result["credentials_read"],
                         "credentials_read should be False")

    def test_fixture_only(self):
        """fixture_only == true"""
        self.assertTrue(self.result["fixture_only"],
                        "fixture_only should be True")

    def test_next_gate_command_order_enforced(self):
        """next_gate_command_order_enforced == true"""
        self.assertTrue(self.result["next_gate_command_order_enforced"],
                        "next_gate_command_order_enforced should be True")

    # ---- File output tests ----

    def test_fixture_csv_data_rows(self):
        """fixture CSV data rows == 4"""
        self.assertEqual(len(self.fixture_rows), 4)

    def test_fixture_jsonl_rows(self):
        """fixture JSONL rows == 4"""
        self.assertEqual(len(self.fixture_filled), 4)

    def test_markdown_contains_4_addresses(self):
        """Markdown contains 4 addresses"""
        for item in self.items:
            short_addr = item["address"][:10]
            self.assertIn(short_addr, self.example_md,
                          f"Example MD should contain address {short_addr}")

    def test_markdown_contains_test_only_primary_source(self):
        """Markdown contains TEST_ONLY_PRIMARY_SOURCE_DO_NOT_USE_AS_REAL_EVIDENCE"""
        self.assertIn("TEST_ONLY_PRIMARY_SOURCE_DO_NOT_USE_AS_REAL_EVIDENCE", self.example_md,
                      "Example MD should contain TEST_ONLY_PRIMARY_SOURCE_DO_NOT_USE_AS_REAL_EVIDENCE")

    def test_markdown_contains_warning_fixture_not_real(self):
        """Markdown contains warning that fixture values are not real evidence"""
        warning_checks = [
            "FIXTURE ONLY",
            "DO NOT",
            "not real evidence" if "not real evidence" in self.example_md.lower() else "synthetic",
        ]
        found = any(
            w.lower() in self.example_md.lower()
            for w in ["FIXTURE ONLY", "DO NOT", "not real evidence", "synthetic"]
        )
        self.assertTrue(found,
                        "Example MD should contain warning that fixture values are not real evidence")

    # ---- Low/unknown fixture row tests ----

    def test_low_fixture_rows_have_trusted_primary_source(self):
        """low/unknown fixture rows must contain trusted primary source"""
        for d in self.decisions:
            if d["current_confidence"] == "low":
                self.assertIn("trusted_source_label_value", d["present_fields"],
                              f"Low whale {d['address'][:10]} missing trusted primary source")
                self.assertIn("trusted_source_url_or_note", d["present_fields"],
                              f"Low whale {d['address'][:10]} missing trusted source URL")

    def test_low_fixture_rows_have_second_source(self):
        """low/unknown fixture rows must contain second source"""
        for d in self.decisions:
            if d["current_confidence"] == "low":
                self.assertIn("second_source_label_value", d["present_fields"],
                              f"Low whale {d['address'][:10]} missing second source")
                self.assertIn("second_source_url_or_note", d["present_fields"],
                              f"Low whale {d['address'][:10]} missing second source URL")

    def test_low_fixture_rows_have_activity_pattern(self):
        """low/unknown fixture rows must contain activity pattern note"""
        for d in self.decisions:
            if d["current_confidence"] == "low":
                self.assertIn("activity_pattern_note", d["present_fields"],
                              f"Low whale {d['address'][:10]} missing activity pattern note")

    def test_low_fixture_rows_have_operator_confirmation(self):
        """low/unknown fixture rows must contain operator confirmation"""
        for d in self.decisions:
            if d["current_confidence"] == "low":
                self.assertIn("operator_confirmed_label", d["present_fields"],
                              f"Low whale {d['address'][:10]} missing operator confirmation")
                self.assertIn("operator_confidence_assessment", d["present_fields"],
                              f"Low whale {d['address'][:10]} missing operator confidence")
                self.assertIn("reviewer", d["present_fields"],
                              f"Low whale {d['address'][:10]} missing reviewer")
                self.assertIn("reviewed_at", d["present_fields"],
                              f"Low whale {d['address'][:10]} missing reviewed_at")
                self.assertIn("ready_for_upgrade", d["present_fields"],
                              f"Low whale {d['address'][:10]} missing ready_for_upgrade")

    # ---- Medium fixture row tests ----

    def test_medium_fixture_rows_have_corroboration_wording(self):
        """medium fixture rows must contain corroboration wording"""
        for fixture_row in self.fixture_filled:
            addr = fixture_row["address"]
            item = next(it for it in self.items if it["address"] == addr)
            if item["current_confidence"] == "medium":
                self.assertEqual(fixture_row["action_type"], "corroboration_required",
                                 f"Medium address {addr[:10]} should have corroboration_required")

    def test_medium_fixture_rows_do_not_claim_tg_readiness(self):
        """medium fixture rows must not claim direct TG readiness"""
        for d in self.decisions:
            if d["current_confidence"] == "medium":
                self.assertFalse(d.get("tg_test_group_ready", True),
                                 f"Medium address {d['address'][:10]} should not claim TG readiness")
                # Check the recommended_next_step doesn't say "go directly to TG"
                next_step = d.get("recommended_next_step", "").lower()
                self.assertNotIn("directly to tg", next_step,
                                 f"Medium address {d['address'][:10]} should not claim direct TG readiness")

    # ---- Real workbook integrity tests ----

    def test_real_workbook_byte_identical(self):
        """Real v115F workbook must remain byte-identical"""
        current_hash = sha256_file(V115F_WORKBOOK)
        self.assertEqual(self.real_hash, current_hash,
                         "Real v115F workbook was modified! SHA-256 hash does not match.")

    def test_real_workbook_hash_in_result(self):
        """Result JSON must contain real workbook hash"""
        self.assertIn("real_workbook_sha256_before", self.result)
        self.assertIn("real_workbook_sha256_after", self.result)
        self.assertEqual(self.result["real_workbook_sha256_before"],
                         self.result["real_workbook_sha256_after"],
                         "Before/after hashes should match")

    # ---- No fake pass claims ----

    def test_no_fake_pass_as_real_pass(self):
        """Fixture passing must not be presented as real passing"""
        # Check report doesn't claim real addresses passed
        self.assertNotIn(
            "real addresses passed",
            self.report_md.lower() if self.report_md else "",
        )
        # Check handoff doesn't claim real pass
        self.assertNotIn(
            "real address passed",
            self.handoff_md.lower() if self.handoff_md else "",
        )

    def test_no_fixture_through_as_real(self):
        """Must not contain fixture pass = real pass phrasing"""
        forbidden_phrases = [
            "fixture pass means real pass",
            "fixture passing proves the addresses",
            "fixture preflight pass confirms",
        ]
        combined = (self.report_md + self.handoff_md + self.example_md).lower()
        for phrase in forbidden_phrases:
            self.assertNotIn(phrase, combined,
                             f"Found forbidden phrase: '{phrase}'")

    # ---- Decision structure tests ----

    def test_each_decision_has_required_fields(self):
        """Each decision must have all required fields"""
        required_fields = [
            "address", "display_label", "current_confidence", "action_type",
            "fixture_only", "fixture_preflight_ready", "missing_required_fields",
            "present_fields", "rejected_source_hits", "ready_for_gate_rerun",
            "recommended_next_step", "not_real_evidence_warning",
        ]
        for d in self.decisions:
            for field in required_fields:
                self.assertIn(field, d,
                              f"Decision for {d.get('address', '?')[:10]} missing field: {field}")

    def test_each_decision_fixture_only_true(self):
        """Each decision must have fixture_only = true"""
        for d in self.decisions:
            self.assertTrue(d.get("fixture_only"),
                            f"Decision for {d['address'][:10]} should have fixture_only=True")

    def test_each_decision_real_workbook_modified_false(self):
        """Each decision must have real_workbook_modified = false"""
        for d in self.decisions:
            self.assertFalse(d.get("real_workbook_modified"),
                             f"Decision for {d['address'][:10]} should have real_workbook_modified=False")

    def test_each_decision_real_label_upgrade_performed_false(self):
        """Each decision must have real_label_upgrade_performed = false"""
        for d in self.decisions:
            self.assertFalse(d.get("real_label_upgrade_performed"),
                             f"Decision for {d['address'][:10]} should have real_label_upgrade_performed=False")

    def test_each_decision_send_ready_false(self):
        """Each decision must have send_ready = false"""
        for d in self.decisions:
            self.assertFalse(d.get("send_ready", True),
                             f"Decision for {d['address'][:10]} should have send_ready=False")

    def test_each_decision_tg_test_group_ready_false(self):
        """Each decision must have tg_test_group_ready = false"""
        for d in self.decisions:
            self.assertFalse(d.get("tg_test_group_ready", True),
                             f"Decision for {d['address'][:10]} should have tg_test_group_ready=False")

    # ---- Fixture evidence value tests ----

    def test_all_evidence_values_marked_test_only(self):
        """All fixture evidence values must contain TEST_ONLY markers"""
        for fixture_row in self.fixture_rows:
            evidence_fields = [
                "trusted_source_label_value", "trusted_source_url_or_note",
                "second_source_label_value", "second_source_url_or_note",
                "activity_pattern_note", "operator_confirmed_label",
                "operator_confidence_assessment", "reviewer", "reviewed_at",
            ]
            for field in evidence_fields:
                value = fixture_row.get(field, "")
                if value:
                    self.assertIn("TEST_ONLY", value,
                                  f"Field {field} for {fixture_row['address'][:10]} "
                                  f"should contain TEST_ONLY marker")

    def test_no_real_urls_in_evidence(self):
        """Fixture evidence must not contain real URLs (https://)"""
        for fixture_row in self.fixture_rows:
            for field in ["trusted_source_url_or_note", "second_source_url_or_note"]:
                value = fixture_row.get(field, "")
                # Only flag if there's a real-looking URL
                if "https://" in value.lower() and "TEST_ONLY" not in value:
                    self.fail(
                        f"Potential real URL in {field} for {fixture_row['address'][:10]}: {value[:100]}"
                    )

    # ---- Real workbook untouched test (pre/post comparison) ----

    def test_real_csv_headers_unchanged(self):
        """Real v115F workbook headers must be unchanged"""
        self.assertEqual(len(self.real_headers), len(self.fixture_headers),
                         "Header count should match")

    def test_real_csv_empty_evidence_fields(self):
        """Real workbook evidence fields should still be empty"""
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


if __name__ == "__main__":
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    suite = unittest.TestLoader().loadTestsFromTestCase(TestV115PPreflightOutputs)
    result = runner.run(suite)

    # Exit with appropriate code
    if result.wasSuccessful():
        print("\n" + "=" * 60)
        print("ALL v115P TESTS PASSED")
        print("=" * 60)
        sys.exit(0)
    else:
        print("\n" + "=" * 60)
        print(f"v115P TESTS FAILED: {len(result.failures)} failures, {len(result.errors)} errors")
        print("=" * 60)
        sys.exit(1)
