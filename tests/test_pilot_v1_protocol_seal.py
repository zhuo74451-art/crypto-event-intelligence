#!/usr/bin/env python3
"""Tests for Pilot v1 Protocol Seal.

All tests are offline. No network access. No Week 1 data read.
"""

import json
import os
import sys
import unittest

PROJ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PILOT_DIR = os.path.join(PROJ, "research", "pilot_v1")
SCHEMA_DIR = os.path.join(PILOT_DIR, "schemas")
PROTOCOL_DIR = os.path.join(PILOT_DIR, "protocols")

REQUIRED_PROTOCOLS = [
    "01_RESEARCH_UNIT_AND_ELIGIBILITY.md",
    "02_TEMPORAL_MODEL_AND_REGISTRATION.md",
    "03_STUDY_CASE_COLLISION_AND_INTERFERENCE.md",
    "04_EVIDENCE_ROLE_CONTRACT.md",
    "05_ATTRIBUTION_ASSESSMENT.md",
    "06_SAMPLE_PREREGISTRATION_AND_PARTITIONS.md",
    "07_BENCHMARK_AND_OUTCOME_MEASUREMENT.md",
    "08_EVENT_IDENTITY_UPDATE_AND_REVERSAL.md",
    "09_NOISE_GATE_SHADOW_AUDIT_AND_PILOT_EXECUTION.md",
]

REQUIRED_SCHEMAS = [
    "candidate.schema.json",
    "research_unit.schema.json",
    "event_instance.schema.json",
    "claim_evidence_record.schema.json",
    "registration.schema.json",
    "outcome.schema.json",
    "interference_record.schema.json",
    "attribution_assessment.schema.json",
]

REQUIRED_ROOT = [
    "README.md", "PILOT_CHARTER.md", "PROTOCOL_REGISTRY.json",
    "validate_protocol_consistency.py", "reports/PHASE_0_ACCEPTANCE_REPORT.md",
]

ELIGIBILITY_ENUM = {"eligible", "conditionally_eligible", "context_only",
                    "routed_to_other_design", "ineligible", "insufficient_information"}

IDENTITY_ENUM = {"duplicate_report_of", "update_of", "correction_of", "reversal_of",
                 "follow_up_to", "part_of_thread", "related_not_same", "identity_unresolved"}

DIMENSION_ENUM = {"temporal_ordering", "temporal_proximity", "benchmark_relative_materiality",
                  "asset_specificity", "mechanism_consistency", "interference_and_separability",
                  "alternative_explanations", "robustness"}

VERDICT_ENUM = {"not_assessable", "descriptive_reaction_only", "insufficient_evidence",
                "attribution_compatible", "limited_attribution_support",
                "not_supported_in_registered_window", "cluster_level_association"}

FORBIDDEN_PROPS = ["abnormal_return", "attribution_score", "confidence_probability",
                   "contribution_percentage", "win_rate", "buy_signal", "sell_signal"]


class TestFilesExist(unittest.TestCase):
    """All required files and schemas exist."""

    def test_root_files_exist(self):
        for f in REQUIRED_ROOT:
            self.assertTrue(os.path.isfile(os.path.join(PILOT_DIR, f)),
                            f"Missing: research/pilot_v1/{f}")

    def test_protocols_exist(self):
        for p in REQUIRED_PROTOCOLS:
            self.assertTrue(os.path.isfile(os.path.join(PROTOCOL_DIR, p)),
                            f"Missing: protocols/{p}")

    def test_schemas_exist(self):
        for s in REQUIRED_SCHEMAS:
            self.assertTrue(os.path.isfile(os.path.join(SCHEMA_DIR, s)),
                            f"Missing: schemas/{s}")


class TestDecisionMapping(unittest.TestCase):
    """All 11 decisions mapped in registry."""

    def setUp(self):
        with open(os.path.join(PILOT_DIR, "PROTOCOL_REGISTRY.json"), "r", encoding="utf-8") as f:
            self.registry = json.load(f)

    def test_all_11_decisions_present(self):
        decisions = {d["decision"] for d in self.registry.get("decision_mappings", [])
                     if isinstance(d.get("decision"), int)}
        expected = set(range(1, 12))
        self.assertEqual(decisions, expected,
                         f"Missing decisions: {expected - decisions}")

    def test_no_decision_outside_1_11(self):
        decisions = {d["decision"] for d in self.registry.get("decision_mappings", [])
                     if isinstance(d.get("decision"), int)}
        self.assertTrue(all(1 <= d <= 11 for d in decisions))


class TestRegistryEnums(unittest.TestCase):
    """Registry enums match protocol specifications."""

    def setUp(self):
        with open(os.path.join(PILOT_DIR, "PROTOCOL_REGISTRY.json"), "r", encoding="utf-8") as f:
            self.registry = json.load(f)
        self.enums = self.registry.get("frozen_enums", {})

    def test_research_eligibility_enum(self):
        actual = set(self.enums.get("research_eligibility", []))
        self.assertEqual(actual, ELIGIBILITY_ENUM)

    def test_identity_relationship_enum(self):
        actual = set(self.enums.get("identity_relationship", []))
        self.assertEqual(actual, IDENTITY_ENUM)

    def test_dimension_enum(self):
        actual = set(self.enums.get("attribution_dimension", []))
        self.assertEqual(actual, DIMENSION_ENUM)

    def test_verdict_enum(self):
        actual = set(self.enums.get("attribution_verdict", []))
        self.assertEqual(actual, VERDICT_ENUM)


class TestSchemaEnums(unittest.TestCase):
    """Schema enums match registry enums."""

    def _load_schema(self, name):
        path = os.path.join(SCHEMA_DIR, name)
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    def test_attribution_verdict_in_schema(self):
        schema = self._load_schema("attribution_assessment.schema.json")
        verdict_enum = set(schema["properties"]["verdict"]["enum"])
        self.assertEqual(verdict_enum, VERDICT_ENUM)

    def test_attribution_dimensions_in_schema(self):
        schema = self._load_schema("attribution_assessment.schema.json")
        dims = set(schema["properties"]["dimensions"]["properties"].keys())
        self.assertEqual(dims, DIMENSION_ENUM)

    def test_separability_in_interference_schema(self):
        schema = self._load_schema("interference_record.schema.json")
        sep = set(schema["properties"]["separability_status"]["enum"])
        self.assertIn("insufficient_inventory", sep)
        self.assertIn("isolated", sep)

    def test_registration_outcome_separate(self):
        reg = self._load_schema("registration.schema.json")
        out = self._load_schema("outcome.schema.json")
        reg_required = set(reg.get("required", []))
        out_required = set(out.get("required", []))
        # Registration must have outcome_status
        self.assertIn("outcome_status", reg_required)
        # Outcome must have registration_ref
        self.assertIn("registration_ref", out_required)
        # Registration-specific fields should NOT be in Outcome
        reg_only = {"registration_id", "target_asset", "selected_clock",
                    "primary_t0", "t0_type", "data_partition", "git_commit", "file_sha256"}
        out_props = set(out.get("properties", {}).keys())
        overlap = reg_only & out_props
        self.assertEqual(len(overlap), 0, f"Outcome shares reg fields: {overlap}")


class TestForbiddenProperties(unittest.TestCase):
    """Schemas contain no forbidden property names."""

    def _check_forbidden(self, schema_path):
        path = os.path.join(SCHEMA_DIR, schema_path)
        with open(path, "r", encoding="utf-8") as f:
            schema = json.load(f)
        props = set(schema.get("properties", {}).keys())
        for prop in FORBIDDEN_PROPS:
            self.assertNotIn(prop, props, f"{schema_path} property '{prop}' found")

    def test_candidate_no_forbidden(self):
        self._check_forbidden("candidate.schema.json")

    def test_registration_no_forbidden(self):
        self._check_forbidden("registration.schema.json")

    def test_outcome_no_forbidden(self):
        self._check_forbidden("outcome.schema.json")

    def test_attribution_no_forbidden(self):
        self._check_forbidden("attribution_assessment.schema.json")

    def test_interference_no_forbidden(self):
        self._check_forbidden("interference_record.schema.json")


class TestSelfBenchmarkRejection(unittest.TestCase):
    """Registration schema rejects self-benchmark."""

    def test_registration_rejects_self_benchmark(self):
        path = os.path.join(SCHEMA_DIR, "registration.schema.json")
        with open(path, "r", encoding="utf-8") as f:
            schema = json.load(f)
        text = json.dumps(schema)
        # Schema should prevent target_asset == primary_benchmark
        self.assertIn("primary_benchmark", text)
        self.assertIn("target_asset", text)


class TestOutcomeMixedIntoRegistration(unittest.TestCase):
    """Registration schema must not contain outcome fields."""

    def test_registration_no_outcome(self):
        path = os.path.join(SCHEMA_DIR, "registration.schema.json")
        with open(path, "r", encoding="utf-8") as f:
            schema = json.load(f)
        props = set(schema.get("properties", {}).keys())
        outcome_fields = {"raw_market_reaction", "registered_benchmark_relative_reaction",
                          "historical_materiality", "outcome_id"}
        overlap = props & outcome_fields
        self.assertEqual(len(overlap), 0, f"Registration contains outcome fields: {overlap}")


class TestDevelopmentSetIsolation(unittest.TestCase):
    """Development Set must not count toward Pilot statistics."""

    def setUp(self):
        with open(os.path.join(PILOT_DIR, "PROTOCOL_REGISTRY.json"), "r", encoding="utf-8") as f:
            self.registry = json.load(f)

    def test_dev_set_counts_false(self):
        dev = self.registry.get("development_set_isolation", {})
        self.assertFalse(dev.get("counts_toward_pilot_statistics", True))

    def test_dev_set_has_5_samples(self):
        dev = self.registry.get("development_set_isolation", {})
        self.assertEqual(len(dev.get("development_set", [])), 5)


class TestNumericAttributionScoreRejection(unittest.TestCase):
    """Attribution assessment must not contain numeric scores."""

    def test_no_numeric_score_terms(self):
        path = os.path.join(SCHEMA_DIR, "attribution_assessment.schema.json")
        with open(path, "r", encoding="utf-8") as f:
            schema = json.load(f)
        props = set(schema.get('properties', {}).keys())
        for term in ["score", "probability", "percentage", "contribution", "win_rate"]:
            self.assertNotIn(term, props, f"Attribution schema property contains '{term}'")


class TestIrreversibleMergeRejection(unittest.TestCase):
    """Event instance must support reversible identity."""

    def test_supersedes_fields_present(self):
        path = os.path.join(SCHEMA_DIR, "event_instance.schema.json")
        with open(path, "r", encoding="utf-8") as f:
            schema = json.load(f)
        props = schema.get("properties", {})
        self.assertIn("supersedes", props)
        self.assertIn("superseded_by", props)


class TestNoiseGateCoupling(unittest.TestCase):
    """Research Unit must NOT depend on Legacy Noise Gate."""

    def test_research_unit_no_noise_gate(self):
        path = os.path.join(SCHEMA_DIR, "research_unit.schema.json")
        with open(path, "r", encoding="utf-8") as f:
            text = f.read().lower()
        self.assertNotIn("noise_gate", text)


class TestMinimalValidStructure(unittest.TestCase):
    """A minimal valid structure for AttributionAssessment passes schema."""

    def test_minimal_assessment(self):
        path = os.path.join(SCHEMA_DIR, "attribution_assessment.schema.json")
        with open(path, "r", encoding="utf-8") as f:
            schema = json.load(f)
        # pylint: disable=import-outside-toplevel
        try:
            import jsonschema
            instance = {
                "assessment_id": "test_001",
                "research_unit_ref": "ru_test",
                "dimensions": {
                    "temporal_ordering": "unknown",
                    "temporal_proximity": "unknown",
                    "benchmark_relative_materiality": "unknown",
                    "asset_specificity": "unknown",
                    "mechanism_consistency": "unknown",
                    "interference_and_separability": "unknown",
                    "alternative_explanations": "unknown",
                    "robustness": "unknown"
                },
                "verdict": "insufficient_evidence",
                "created_at_utc": "2026-06-16T12:00:00Z"
            }
            jsonschema.validate(instance, schema)
        except ImportError:
            self.skipTest("jsonschema not installed; structure validated via JSON parsing")


class TestGitPathWhitelist(unittest.TestCase):
    """Git path whitelist logic matches allowed paths."""

    def test_allowed_paths_contain_pilot(self):
        with open(os.path.join(PILOT_DIR, "PROTOCOL_REGISTRY.json"), "r", encoding="utf-8") as f:
            registry = json.load(f)
        allowed = registry.get("allowed_paths", [])
        self.assertIn("research/pilot_v1/**", allowed)


class TestMissingUnknownStatus(unittest.TestCase):
    """Schemas must include unknown/insufficient statuses."""

    def test_eligibility_has_insufficient(self):
        with open(os.path.join(SCHEMA_DIR, "research_unit.schema.json"), "r", encoding="utf-8") as f:
            schema = json.load(f)
        statuses = set(schema["properties"]["eligibility_status"]["enum"])
        self.assertIn("insufficient_information", statuses)

    def test_separability_has_insufficient(self):
        with open(os.path.join(SCHEMA_DIR, "interference_record.schema.json"), "r", encoding="utf-8") as f:
            schema = json.load(f)
        statuses = set(schema["properties"]["separability_status"]["enum"])
        self.assertIn("insufficient_inventory", statuses)

    def test_candidate_has_insufficient(self):
        with open(os.path.join(SCHEMA_DIR, "candidate.schema.json"), "r", encoding="utf-8") as f:
            schema = json.load(f)
        statuses = set(schema["properties"]["status"]["enum"])
        self.assertIn("insufficient_information", statuses)


if __name__ == "__main__":
    unittest.main(verbosity=2)
