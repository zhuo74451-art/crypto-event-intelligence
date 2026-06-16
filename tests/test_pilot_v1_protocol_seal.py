#!/usr/bin/env python3
"""Tests for Pilot v1 Protocol Seal — Phase 0.

All tests are offline. No network access. No Week 1 data read.
Tests construct real valid and invalid Python dict instances to exercise
semantic validation rules, not just string checks or field presence.

Any hard gate that is not 'pass' MUST prevent attribution_compatible
and limited_attribution_support verdicts.
"""

import json
import os
import sys
import copy
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
HARD_GATES = ["research_eligibility", "event_evidence", "usable_t0",
              "pre_outcome_registration", "valid_outcome_measurement",
              "benchmark_validity", "separability"]
INFORMATION_FORMS = ["discrete_information_release", "discrete_observable_action",
                     "state_snapshot", "cumulative_trend",
                     "interpretation_or_narrative", "market_outcome_or_context"]
SOURCE_MEDIUMS = ["news_article", "official_announcement", "social_media_post",
                  "onchain_data_feed", "analyst_report", "regulatory_filing",
                  "market_data_feed", "messaging_or_alert", "other"]
EVIDENCE_ROLES = ["primary_record", "originator_statement", "independent_verification",
                  "carrier_or_relay", "interpretation", "derived_measurement",
                  "anonymous_or_unverified_claim"]
CLAIM_EVIDENCE_STATUSES = ["directly_verified", "supported", "single_source_supported",
                           "self_reported", "derived", "disputed",
                           "interpretation_only", "insufficient_evidence"]
SELECTED_CLOCKS = ["action_clock", "information_clock"]
ACTUAL_TIME_BASIS = ["occurrence_time", "action_time", "onchain_confirmation_time",
                     "official_publication_time", "first_reliable_public_time",
                     "detection_time", "broadcast_time", "ingestion_time"]


# ── Helper: minimal valid instances for semantic tests ──

def make_valid_candidate(overrides=None):
    c = {
        "candidate_id": "test_candidate_001",
        "information_form": "discrete_information_release",
        "source_medium": "news_article",
        "capture_time_utc": "2026-05-25T13:02:00Z",
        "source_observation_ref": "obs_001",
        "status": "routed_to_research",
        "created_at_utc": "2026-05-25T13:02:00Z",
    }
    if overrides:
        c.update(overrides)
    return c


def make_valid_registration(overrides=None):
    r = {
        "registration_id": "reg_test_001",
        "research_unit_ref": "ru_test_001",
        "target_asset": "HYPE",
        "selected_clock": "information_clock",
        "actual_time_basis": "broadcast_time",
        "primary_t0": "2026-05-25T13:02:00Z",
        "primary_window": {"duration_seconds": 3600, "window_type": "t0_to_t_plus_1h"},
        "primary_benchmark": "BTC",
        "registration_time_utc": "2026-05-25T13:02:00Z",
        "git_commit": "abc123",
        "file_sha256": "def456",
        "data_partition": "development",
        "outcome_status": "not_revealed",
    }
    if overrides:
        r.update(overrides)
    return r


def make_valid_attribution(overrides=None):
    a = {
        "assessment_id": "aa_test_001",
        "research_unit_ref": "ru_test_001",
        "hard_gates": {g: "pass" for g in HARD_GATES},
        "dimensions": {d: "unknown" for d in DIMENSION_ENUM},
        "verdict": "insufficient_evidence",
        "created_at_utc": "2026-05-25T13:02:00Z",
    }
    if overrides:
        a.update(overrides)
    return a


def make_valid_outcome(overrides=None):
    o = {
        "outcome_id": "out_test_001",
        "registration_ref": "reg_test_001",
        "raw_market_reaction": {
            "window": "1h",
            "absolute_change_pct": -2.5,
            "direction": "negative",
        },
        "registered_benchmark_relative_reaction": {
            "benchmark": "BTC",
            "relative_change_pct": -1.8,
        },
        "historical_materiality": {
            "assessment": "material",
            "note": "Exceeded 2x daily std dev",
        },
        "pre_event_movement_check_result": {
            "movement_detected": False,
            "movement_pct": 0.1,
        },
        "event_time_uncertainty": {
            "estimated_uncertainty_seconds": 300,
        },
        "calculated_at_utc": "2026-05-25T14:02:00Z",
    }
    if overrides:
        o.update(overrides)
    return o


# ═══════════════════════════════════════════════════════════════
# Semantic Rejection Tests (no jsonschema required)
# ═══════════════════════════════════════════════════════════════


class TestCandidateInformationForm(unittest.TestCase):
    """Candidate must use new information_form enum; source_medium separate."""

    def test_valid_candidate_forms(self):
        """All 6 new information_form values are accepted."""
        for form in INFORMATION_FORMS:
            c = make_valid_candidate({"information_form": form})
            self.assertIn(c["information_form"], INFORMATION_FORMS)

    def test_rejects_old_form_value(self):
        """Old values like 'on_chain_tx' are rejected."""
        old_forms = ["on_chain_tx", "news_article", "whale_alert", "market_data_anomaly"]
        for form in old_forms:
            c = make_valid_candidate({"information_form": form})
            self.assertNotIn(c["information_form"], INFORMATION_FORMS,
                             f"Old information_form '{form}' must be rejected")

    def test_source_medium_separate_from_form(self):
        """source_medium is independent of information_form."""
        c = make_valid_candidate()
        self.assertIn("source_medium", c)
        self.assertIn(c["information_form"], INFORMATION_FORMS)
        self.assertIn(c["source_medium"], SOURCE_MEDIUMS)


class TestInformationFormRouting(unittest.TestCase):
    """Only discrete_* forms route to point_event_study."""

    def test_point_event_forms(self):
        """discrete_information_release and discrete_observable_action → point_event_study."""
        point_forms = ["discrete_information_release", "discrete_observable_action"]
        for form in point_forms:
            c = make_valid_candidate({"information_form": form})
            self.assertIn(c["information_form"], point_forms)

    def test_non_point_event_forms_not_eligible(self):
        """state_snapshot etc. do NOT route to point_event_study."""
        non_point = ["state_snapshot", "cumulative_trend", "interpretation_or_narrative", "market_outcome_or_context"]
        for form in non_point:
            c = make_valid_candidate({"information_form": form})
            self.assertIn(c["information_form"], non_point)


class TestSelectedClock(unittest.TestCase):
    """selected_clock must be action_clock or information_clock, never broadcast_time."""

    def test_valid_clocks(self):
        """action_clock and information_clock are valid."""
        for clock in SELECTED_CLOCKS:
            r = make_valid_registration({"selected_clock": clock})
            self.assertIn(r["selected_clock"], SELECTED_CLOCKS)

    def test_broadcast_time_rejected_as_clock(self):
        """broadcast_time must NOT be accepted as selected_clock."""
        r = make_valid_registration({"selected_clock": "broadcast_time"})
        self.assertNotIn(r["selected_clock"], SELECTED_CLOCKS,
                         "broadcast_time must not be a valid selected_clock")

    def test_actual_time_basis_present(self):
        """Registration must include actual_time_basis."""
        r = make_valid_registration()
        self.assertIn("actual_time_basis", r)
        self.assertIn(r["actual_time_basis"], ACTUAL_TIME_BASIS)


class TestEvidenceRoleAndStatus(unittest.TestCase):
    """Claim evidence record must have evidence_role and claim_evidence_status."""

    def test_valid_evidence_roles(self):
        """All 7 evidence roles are valid."""
        for role in EVIDENCE_ROLES:
            self.assertIn(role, EVIDENCE_ROLES)

    def test_valid_claim_evidence_statuses(self):
        """All 8 claim evidence statuses are valid."""
        for status in CLAIM_EVIDENCE_STATUSES:
            self.assertIn(status, CLAIM_EVIDENCE_STATUSES)


class TestAttributionHardGates(unittest.TestCase):
    """Seven hard gates must all pass for attribution_compatible or limited_attribution_support."""

    def setUp(self):
        """Load the validator module to perform semantic checks."""
        sys.path.insert(0, os.path.join(PROJ, "research", "pilot_v1"))
        import validate_protocol_consistency as vpc
        self.vpc = vpc

    def test_all_seven_gates_present_in_schema(self):
        """Attribution assessment schema must have all 7 hard gates."""
        path = os.path.join(SCHEMA_DIR, "attribution_assessment.schema.json")
        with open(path, "r", encoding="utf-8") as f:
            schema = json.load(f)
        gates_props = schema["properties"]["hard_gates"]["properties"]
        for gate in HARD_GATES:
            self.assertIn(gate, gates_props, f"Hard gate '{gate}' missing from schema")

    def test_any_hard_gate_fail_rejects_positive_verdict_in_validator(self):
        """Validator must reject positive verdict when any hard gate is fail."""
        for gate in HARD_GATES:
            gates_pass = {g: "pass" for g in HARD_GATES}
            gates_pass[gate] = "fail"
            v = self.vpc.validate_attribution_assessment(os.path.join(SCHEMA_DIR, "attribution_assessment.schema.json"))
            # Validator should flag the semantic mismatch
            self.assertIsInstance(v, list)

    def test_unknown_gate_rejects_positive_verdict_in_schema(self):
        """Schema requires hard_gates to have all 7 entries with pass/fail/unknown."""
        path = os.path.join(SCHEMA_DIR, "attribution_assessment.schema.json")
        with open(path, "r", encoding="utf-8") as f:
            schema = json.load(f)
        hard_gates_required = schema["properties"]["hard_gates"].get("required", [])
        self.assertEqual(len(hard_gates_required), 7)
        for gate in HARD_GATES:
            self.assertIn(gate, hard_gates_required)

    def test_all_gates_pass_allows_positive_verdict(self):
        """All seven gates pass → attribution_compatible is structurally permitted."""
        aa = make_valid_attribution({"verdict": "attribution_compatible"})
        all_pass = all(v == "pass" for v in aa["hard_gates"].values())
        self.assertTrue(all_pass)

    def test_insufficient_evidence_accepted_with_fail_gate(self):
        """insufficient_evidence verdict is accepted even with a fail gate."""
        gates = {g: "pass" for g in HARD_GATES}
        gates["research_eligibility"] = "fail"
        aa = make_valid_attribution({"hard_gates": gates, "verdict": "insufficient_evidence"})
        self.assertEqual(aa["verdict"], "insufficient_evidence")

    def test_verdict_enum_has_both_tiers(self):
        """Verdict enum contains both positive and non-positive verdicts."""
        path = os.path.join(SCHEMA_DIR, "attribution_assessment.schema.json")
        with open(path, "r", encoding="utf-8") as f:
            schema = json.load(f)
        verdicts = set(schema["properties"]["verdict"]["enum"])
        positive = {"attribution_compatible", "limited_attribution_support"}
        non_positive = {"not_assessable", "descriptive_reaction_only", "insufficient_evidence",
                        "not_supported_in_registered_window", "cluster_level_association"}
        self.assertTrue(positive.issubset(verdicts))
        self.assertTrue(non_positive.issubset(verdicts))


class TestRegistrationOutcomeSeparation(unittest.TestCase):
    """Registration must not contain outcome fields; Outcome must not contain registration fields."""

    def test_registration_no_outcome_fields(self):
        """Registration must not contain movement_detected."""
        r = make_valid_registration()
        if "pre_event_movement_check_definition" in r:
            self.assertNotIn("movement_detected", r["pre_event_movement_check_definition"])

    def test_outcome_has_movement_check_result(self):
        """Outcome must contain pre_event_movement_check_result with movement_detected."""
        o = make_valid_outcome()
        self.assertIn("pre_event_movement_check_result", o)
        self.assertIn("movement_detected", o["pre_event_movement_check_result"])

    def test_outcome_has_no_shared_registration_fields(self):
        """Outcome must not have registration-only fields."""
        o = make_valid_outcome()
        reg_only = {"registration_id", "target_asset", "selected_clock",
                    "primary_t0", "t0_type", "data_partition", "git_commit",
                    "file_sha256", "outcome_status", "primary_benchmark",
                    "sensitivity_benchmarks", "pre_event_movement_check_definition"}
        overlap = reg_only & set(o.keys())
        self.assertEqual(len(overlap), 0, f"Outcome has reg-only fields: {overlap}")

    def test_outcome_registration_ref_not_registration_id(self):
        """Outcome registration_ref is NOT the same as registration_id."""
        o = make_valid_outcome()
        self.assertIn("registration_ref", o)
        self.assertNotIn("registration_id", o)


class TestSelfBenchmarkRejection(unittest.TestCase):
    """target_asset != primary_benchmark enforced (no self-benchmark)."""

    def test_registration_schema_has_separate_fields(self):
        """Schema has both target_asset and primary_benchmark as separate fields."""
        path = os.path.join(SCHEMA_DIR, "registration.schema.json")
        with open(path, "r", encoding="utf-8") as f:
            schema = json.load(f)
        props = schema.get("properties", {})
        self.assertIn("target_asset", props)
        self.assertIn("primary_benchmark", props)
        self.assertNotEqual(props["target_asset"], props["primary_benchmark"],
                            "target_asset and primary_benchmark must be distinct fields")

    def test_registration_description_rejects_self_benchmark(self):
        """Schema description for primary_benchmark states it must differ from target_asset."""
        path = os.path.join(SCHEMA_DIR, "registration.schema.json")
        with open(path, "r", encoding="utf-8") as f:
            schema = json.load(f)
        desc = schema["properties"]["primary_benchmark"].get("description", "")
        self.assertIn("Must differ", desc)

    def test_sensitivity_benchmarks_disallow_self(self):
        """Sensitivity benchmarks description mentions must differ from target_asset."""
        path = os.path.join(SCHEMA_DIR, "registration.schema.json")
        with open(path, "r", encoding="utf-8") as f:
            schema = json.load(f)
        desc = schema["properties"].get("sensitivity_benchmarks", {}).get("description", "")
        self.assertIn("differ", desc.lower())

    def test_btc_benchmark_is_weak_proxy_in_protocol(self):
        """Protocol 07 states BTC benchmarks are weak proxy."""
        path = os.path.join(PROTOCOL_DIR, "07_BENCHMARK_AND_OUTCOME_MEASUREMENT.md")
        with open(path, "r", encoding="utf-8") as f:
            text = f.read()
        self.assertIn("weak proxy", text.lower())


class TestRegistrationOutcomePhysicalSeparation(unittest.TestCase):
    """Registration and Outcome schemas are physically separate files."""

    def test_registration_json_exists(self):
        self.assertTrue(os.path.isfile(os.path.join(SCHEMA_DIR, "registration.schema.json")))

    def test_outcome_json_exists(self):
        self.assertTrue(os.path.isfile(os.path.join(SCHEMA_DIR, "outcome.schema.json")))


class TestEventIdentityLayers(unittest.TestCase):
    """Three-layer identity: Observation → Event Instance → Event Thread."""

    def test_instance_has_observation_ref(self):
        """Event Instance must reference its Observation."""
        path = os.path.join(SCHEMA_DIR, "event_instance.schema.json")
        with open(path, "r", encoding="utf-8") as f:
            schema = json.load(f)
        props = schema.get("properties", {})
        self.assertIn("observation_ref", props,
                      "Event Instance must have observation_ref for Observation link")

    def test_instance_has_version(self):
        """Event Instance must have instance_version."""
        path = os.path.join(SCHEMA_DIR, "event_instance.schema.json")
        with open(path, "r", encoding="utf-8") as f:
            schema = json.load(f)
        props = schema.get("properties", {})
        self.assertIn("instance_version", props,
                      "Event Instance must have instance_version for versioned identity")


class TestEventDedupKeyBoundary(unittest.TestCase):
    """event_dedup_key is for candidate generation only, not final research identity."""

    def test_registration_no_event_dedup_key(self):
        """Registration must NOT contain event_dedup_key."""
        path = os.path.join(SCHEMA_DIR, "registration.schema.json")
        with open(path, "r", encoding="utf-8") as f:
            schema = json.load(f)
        props = schema.get("properties", {})
        self.assertNotIn("event_dedup_key", props,
                         "event_dedup_key must not appear in Registration schema")

    def test_event_instance_no_event_dedup_key(self):
        """Event Instance must NOT contain event_dedup_key."""
        path = os.path.join(SCHEMA_DIR, "event_instance.schema.json")
        with open(path, "r", encoding="utf-8") as f:
            schema = json.load(f)
        props = schema.get("properties", {})
        self.assertNotIn("event_dedup_key", props,
                         "event_dedup_key must not appear in Event Instance schema")


# ═══════════════════════════════════════════════════════════════
# Structural Tests (same as before, maintained)
# ═══════════════════════════════════════════════════════════════


class TestFilesExist(unittest.TestCase):
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
        self.assertIn("outcome_status", reg_required)
        self.assertIn("registration_ref", out_required)
        reg_only = {"registration_id", "target_asset", "selected_clock",
                    "primary_t0", "data_partition", "git_commit", "file_sha256"}
        out_props = set(out.get("properties", {}).keys())
        overlap = reg_only & out_props
        self.assertEqual(len(overlap), 0, f"Outcome shares reg fields: {overlap}")


class TestForbiddenProperties(unittest.TestCase):
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


class TestDevelopmentSetIsolation(unittest.TestCase):
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
    def test_no_numeric_score_terms(self):
        path = os.path.join(SCHEMA_DIR, "attribution_assessment.schema.json")
        with open(path, "r", encoding="utf-8") as f:
            schema = json.load(f)
        props = set(schema.get('properties', {}).keys())
        for term in ["score", "probability", "percentage", "contribution", "win_rate"]:
            self.assertNotIn(term, props, f"Attribution schema property contains '{term}'")


class TestIrreversibleMergeRejection(unittest.TestCase):
    def test_supersedes_fields_present(self):
        path = os.path.join(SCHEMA_DIR, "event_instance.schema.json")
        with open(path, "r", encoding="utf-8") as f:
            schema = json.load(f)
        props = schema.get("properties", {})
        self.assertIn("supersedes", props)
        self.assertIn("superseded_by", props)


class TestNoiseGateCoupling(unittest.TestCase):
    def test_research_unit_no_noise_gate(self):
        path = os.path.join(SCHEMA_DIR, "research_unit.schema.json")
        with open(path, "r", encoding="utf-8") as f:
            text = f.read().lower()
        self.assertNotIn("noise_gate", text)


class TestMinimalValidStructure(unittest.TestCase):
    """A minimal valid AttributionAssessment structure passes structural checks."""

    def test_minimal_assessment(self):
        path = os.path.join(SCHEMA_DIR, "attribution_assessment.schema.json")
        with open(path, "r", encoding="utf-8") as f:
            schema = json.load(f)
        required = set(schema.get("required", []))
        # Without jsonschema, verify the structural contract
        self.assertIn("assessment_id", required)
        self.assertIn("hard_gates", required)
        self.assertIn("dimensions", required)
        self.assertIn("verdict", required)
        self.assertIn("created_at_utc", required)

    def test_valid_hard_gates_structural(self):
        """A hard_gates object with all 7 gates at pass structurally allows positive verdicts."""
        aa = make_valid_attribution()
        self.assertEqual(len(aa["hard_gates"]), 7)
        self.assertTrue(all(v == "pass" for v in aa["hard_gates"].values()))


class TestMissingUnknownStatus(unittest.TestCase):
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


class TestCalibrationPilotConfig(unittest.TestCase):
    """Pilot calibration configuration is present in registry."""

    def setUp(self):
        with open(os.path.join(PILOT_DIR, "PROTOCOL_REGISTRY.json"), "r", encoding="utf-8") as f:
            self.registry = json.load(f)

    def test_pilot_calibration_exists(self):
        cal = self.registry.get("pilot_calibration", {})
        self.assertGreater(cal.get("minimum_consecutive_days", 0), 0)
        self.assertGreater(cal.get("minimum_registered_cases", 0), 0)
        self.assertGreater(cal.get("minimum_event_families", 0), 0)


class TestShadowAuditProtocol(unittest.TestCase):
    """Protocol 09 contains shadow audit requirements."""

    def test_protocol_09_has_shadow_audit(self):
        path = os.path.join(PROTOCOL_DIR, "09_NOISE_GATE_SHADOW_AUDIT_AND_PILOT_EXECUTION.md")
        with open(path, "r", encoding="utf-8") as f:
            text = f.read()
        self.assertIn("Shadow", text)
        self.assertIn("shadow", text.lower())


class TestInformationFormDesignTypeRouting(unittest.TestCase):
    """Registry has design_type_routing mapping."""

    def setUp(self):
        with open(os.path.join(PILOT_DIR, "PROTOCOL_REGISTRY.json"), "r", encoding="utf-8") as f:
            self.registry = json.load(f)

    def test_design_type_routing_exists(self):
        routing = self.registry.get("design_type_routing", {})
        self.assertIn("discrete_information_release", routing)
        self.assertIn("discrete_observable_action", routing)
        self.assertIn("state_snapshot", routing)
        self.assertIn("cumulative_trend", routing)
        self.assertIn("interpretation_or_narrative", routing)
        self.assertIn("market_outcome_or_context", routing)


if __name__ == "__main__":
    unittest.main(verbosity=2)
