"""Test V3 audit evidence is committed and passes checks."""
import json, os

AUDIT_JSON = "data/intelligence/strategy_replay/pilot_v2/pilot_integrity_audit_v3.json"
AUDIT_MD = "data/intelligence/strategy_replay/pilot_v2/pilot_integrity_audit_v3.md"


class TestAuditEvidenceCommitted:

    def test_audit_json_exists(self):
        assert os.path.exists(AUDIT_JSON), f"{AUDIT_JSON} not found"

    def test_audit_md_exists(self):
        assert os.path.exists(AUDIT_MD), f"{AUDIT_MD} not found"

    def load_audit(self):
        with open(AUDIT_JSON) as f:
            return json.load(f)

    def test_audit_verdict_pass(self):
        audit = self.load_audit()
        assert audit.get("overall_verdict") == "pass"

    def test_audit_all_exit_codes_zero(self):
        audit = self.load_audit()
        assert audit["leakage_audit"]["process_exit_code"] == 0
        assert audit["abstention_audit"]["process_exit_code"] == 0
        assert audit["kernel_package_audit"]["process_exit_code"] == 0

    def test_audit_total_violations_zero(self):
        audit = self.load_audit()
        total = audit["leakage_audit"]["violation_count"]
        total += audit["abstention_audit"]["violation_count"]
        total += audit["kernel_package_audit"]["violation_count"]
        assert total == 0, f"Total violations: {total}"

    def test_audit_artifact_hash_basis_correct(self):
        audit = self.load_audit()
        expected = "da98a83fc8072f1411749412d159b34c77937b19"
        assert audit.get("artifact_hash_basis_commit") == expected

    def test_hypothesis_lineage_ok(self):
        audit = self.load_audit()
        assert audit["hypothesis_lineage"]["total"] == 32
        assert audit["hypothesis_lineage"]["missing_fields"] == 0

    def test_kernel_packages_ok(self):
        audit = self.load_audit()
        kp = audit["kernel_packages"]
        assert kp["total"] == 16
        assert kp["packages_with_duplicate_hypothesis"] == 0
        assert kp["packages_missing_4h"] == 0
        assert kp["packages_missing_24h"] == 0

    def test_outcome_lineage_ok(self):
        audit = self.load_audit()
        ol = audit["outcome_lineage"]
        assert ol["total"] == 32
        assert ol["missing_signal_window_ref"] == 0
        assert ol["missing_target_window_ref"] == 0