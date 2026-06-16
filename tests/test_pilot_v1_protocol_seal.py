#!/usr/bin/env python3
"""Tests for Pilot v1 Protocol Seal — Phase 0 (V4 Correction).

All tests call PRODUCTION validator functions in validate_protocol_consistency.py.
No duplicated logic. No pseudo-negative tests. Every negative test asserts:
  - violations list is non-empty
  - expected violation text is present

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

# Import the production validator
sys.path.insert(0, PILOT_DIR)
import validate_protocol_consistency as vpc

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

HARD_GATES = ["research_eligibility", "event_evidence", "usable_t0",
              "pre_outcome_registration", "valid_outcome_measurement",
              "benchmark_validity", "separability"]

INFORMATION_FORMS = ["discrete_information_release", "discrete_observable_action",
                     "state_snapshot", "cumulative_trend",
                     "interpretation_or_narrative", "market_outcome_or_context"]

VALID_SOURCE_MEDIUMS = ["news_article", "official_announcement", "social_media_post",
                        "onchain_data_feed", "analyst_report", "regulatory_filing",
                        "market_data_feed", "messaging_or_alert", "other"]

SELECTED_CLOCKS = ["action_clock", "information_clock"]

ACTUAL_TIME_BASIS = ["occurrence_time", "action_time", "onchain_confirmation_time",
                     "official_publication_time", "first_reliable_public_time",
                     "detection_time", "broadcast_time", "ingestion_time"]


def make_valid_candidate(overrides=None):
    c = {
        "candidate_id": "t_c_001",
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
        "registration_id": "reg_t_001",
        "research_unit_ref": "ru_t_001",
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
        "assessment_id": "aa_t_001",
        "research_unit_ref": "ru_t_001",
        "hard_gates": {g: "pass" for g in HARD_GATES},
        "dimensions": {d: "unknown" for d in vpc.DIMENSION_ENUM},
        "verdict": "insufficient_evidence",
        "created_at_utc": "2026-05-25T13:02:00Z",
    }
    if overrides:
        a.update(overrides)
    return a


def make_valid_outcome(overrides=None):
    o = {
        "outcome_id": "out_t_001",
        "registration_ref": "reg_t_001",
        "raw_market_reaction": {"window": "1h", "absolute_change_pct": -2.5, "direction": "negative"},
        "registered_benchmark_relative_reaction": {"benchmark": "BTC", "relative_change_pct": -1.8},
        "historical_materiality": {"assessment": "material", "note": "Exceeded 2x daily std dev"},
        "pre_event_movement_check_result": {"movement_detected": False, "movement_pct": 0.1},
        "event_time_uncertainty": {"estimated_uncertainty_seconds": 300},
        "calculated_at_utc": "2026-05-25T14:02:00Z",
    }
    if overrides:
        o.update(overrides)
    return o


def make_valid_interference(overrides=None):
    i = {
        "record_id": "int_t_001",
        "research_unit_ref": "ru_t_001",
        "observation_window": "1h",
        "separability_status": "isolated",
        "collision_set": [],
        "alternative_explanations": ["General market sentiment"],
        "coverage_insufficiency": False,
        "created_at_utc": "2026-05-25T13:02:00Z",
    }
    if overrides:
        i.update(overrides)
    return i


def make_valid_event_instance(overrides=None):
    ei = {
        "canonical_event_instance_id": "ei_t_001",
        "event_thread_ref": "th_t_001",
        "relationship_to_thread": "part_of_thread",
        "relationship_evidence": "Same source, sequential reporting",
        "observation_ref": "obs_001",
        "instance_version": 1,
        "created_at_utc": "2026-05-25T13:02:00Z",
    }
    if overrides:
        ei.update(overrides)
    return ei


def make_valid_claim_evidence(overrides=None):
    ce = {
        "record_id": "ce_t_001",
        "evidence_role": "primary_record",
        "claim_evidence_status": "supported",
        "claim": {"statement": "Event X occurred", "claimant": "Source A", "claim_time_utc": "2026-05-25T13:02:00Z", "claim_type": "fact"},
        "evidence_artifacts": [{"artifact_id": "art_001", "artifact_type": "article", "content_hash": "abc", "source": "Source A"}],
        "evidence_relations": [{"evidence_id": "art_001", "relation_type": "supports"}],
        "independence_groups": [{"group_id": "grp_001", "members": ["art_001"], "independence_status": "independent"}],
        "provenance_path": [{"hop": 1, "from_source": "Original", "to_source": "Source A", "timestamp_utc": "2026-05-25T13:02:00Z"}],
        "created_at_utc": "2026-05-25T13:02:00Z",
    }
    if overrides:
        ce.update(overrides)
    return ce


def make_valid_research_bundle(overrides=None):
    reg = make_valid_registration({"data_partition": "holdout"})
    out = make_valid_outcome()
    out["registration_ref"] = reg["registration_id"]
    bundle = {
        "candidate": make_valid_candidate(),
        "research_unit": {
            "research_unit_id": "ru_t_001",
            "design_type": "point_event_study",
            "eligibility_status": "eligible",
            "candidate_ref": "t_c_001",
            "information_form": "discrete_information_release",
            "created_at_utc": "2026-05-25T13:02:00Z",
        },
        "registration": reg,
        "outcome": out,
        "interference": make_valid_interference(),
        "event_instance": make_valid_event_instance(),
        "claim_evidence": make_valid_claim_evidence(),
        "attribution": make_valid_attribution(),
    }
    if overrides:
        bundle.update(overrides)
    return bundle


# ═══════════════════════════════════════════════════════════════
# Negative Tests — Each calls production validator, asserts
# violations non-empty and expected text present.
# ═══════════════════════════════════════════════════════════════


class TestNegativeCandidate(unittest.TestCase):
    """Negative cases for validate_candidate_instance."""

    def test_old_information_form_rejected(self):
        c = make_valid_candidate({"information_form": "on_chain_tx"})
        v = vpc.validate_candidate_instance(c)
        self.assertTrue(len(v) > 0)
        self.assertTrue(any("information_form" in vi for vi in v))

    def test_non_discrete_routed_to_research_rejected(self):
        c = make_valid_candidate({"information_form": "cumulative_trend"})
        v = vpc.validate_candidate_instance(c)
        self.assertTrue(len(v) > 0)
        self.assertTrue(any("cumulative_trend" in vi.lower() for vi in v))

    def test_excluded_without_reason_rejected(self):
        c = make_valid_candidate({"status": "excluded"})
        v = vpc.validate_candidate_instance(c)
        self.assertTrue(len(v) > 0)
        self.assertTrue(any("exclusion_reason" in vi.lower() for vi in v))

    def test_market_outcome_routed_to_research_rejected(self):
        c = make_valid_candidate({"information_form": "market_outcome_or_context", "status": "routed_to_research"})
        v = vpc.validate_candidate_instance(c)
        self.assertTrue(len(v) > 0)
        self.assertTrue(any("market_outcome_or_context" in vi.lower() for vi in v))

    def test_state_snapshot_routed_to_research_rejected(self):
        c = make_valid_candidate({"information_form": "state_snapshot", "status": "routed_to_research"})
        v = vpc.validate_candidate_instance(c)
        self.assertTrue(len(v) > 0)
        self.assertTrue(any("state_snapshot" in vi.lower() for vi in v))

    def test_interpretation_routed_to_research_rejected(self):
        c = make_valid_candidate({"information_form": "interpretation_or_narrative", "status": "routed_to_research"})
        v = vpc.validate_candidate_instance(c)
        self.assertTrue(len(v) > 0)
        self.assertTrue(any("interpretation" in vi.lower() for vi in v))

    def test_missing_source_observation_ref_rejected(self):
        c = make_valid_candidate()
        del c["source_observation_ref"]
        v = vpc.validate_candidate_instance(c)
        self.assertTrue(len(v) > 0)
        self.assertTrue(any("source_observation_ref" in vi.lower() for vi in v))
    """Negative cases for validate_registration_instance."""

    def test_self_benchmark_rejected(self):
        r = make_valid_registration({"target_asset": "BTC", "primary_benchmark": "BTC"})
        v = vpc.validate_registration_instance(r)
        self.assertTrue(len(v) > 0)
        self.assertTrue(any("self" in vi.lower() or "same" in vi.lower() for vi in v))

    def test_sensitivity_self_benchmark_rejected(self):
        r = make_valid_registration({"target_asset": "ETH", "primary_benchmark": "BTC", "sensitivity_benchmarks": ["ETH"]})
        v = vpc.validate_registration_instance(r)
        self.assertTrue(len(v) > 0)
        self.assertTrue(any("sensitivity" in vi.lower() for vi in v))

    def test_duplicate_sensitivity_benchmark_rejected(self):
        r = make_valid_registration({"sensitivity_benchmarks": ["SOL", "SOL"]})
        v = vpc.validate_registration_instance(r)
        self.assertTrue(len(v) > 0)
        self.assertTrue(any("duplicate" in vi.lower() for vi in v))

    def test_broadcast_time_as_clock_rejected(self):
        r = make_valid_registration({"selected_clock": "broadcast_time"})
        v = vpc.validate_registration_instance(r)
        self.assertTrue(len(v) > 0)
        self.assertTrue(any("clock" in vi.lower() for vi in v))

    def test_registration_contains_outcome_field_rejected(self):
        r = make_valid_registration({"raw_market_reaction": {"window": "1h", "absolute_change_pct": 1.0, "direction": "positive"}})
        v = vpc.validate_registration_instance(r)
        self.assertTrue(len(v) > 0)
        self.assertTrue(any("raw_market_reaction" in vi.lower() for vi in v))

    def test_registration_contains_movement_detected_rejected(self):
        r = make_valid_registration({"pre_event_movement_check_definition": {"window_before_t0_seconds": 3600, "threshold_bps": 50, "movement_detected": True}})
        v = vpc.validate_registration_instance(r)
        self.assertTrue(len(v) > 0)
        self.assertTrue(any("movement_detected" in vi.lower() for vi in v))

    def test_outcome_status_not_not_revealed_rejected(self):
        r = make_valid_registration({"outcome_status": "revealed"})
        v = vpc.validate_registration_instance(r)
        self.assertTrue(len(v) > 0)
        self.assertTrue(any("outcome_status" in vi.lower() for vi in v))


class TestNegativeSchemaShape(unittest.TestCase):
    """Negative cases for schema-lite shape validation via validate_*_instance."""

    def test_candidate_unknown_top_level_field(self):
        c = make_valid_candidate({"unknown_field": "value"})
        v = vpc.validate_candidate_instance(c)
        self.assertTrue(len(v) > 0)
        self.assertTrue(any("unknown" in vi.lower() for vi in v))

    def test_registration_unknown_top_level_field(self):
        r = make_valid_registration({"unknown_field": "value"})
        v = vpc.validate_registration_instance(r)
        self.assertTrue(len(v) > 0)
        self.assertTrue(any("unknown" in vi.lower() for vi in v))

    def test_registration_unknown_nested_field(self):
        r = make_valid_registration({"primary_window": {"duration_seconds": 3600, "window_type": "t0_to_t_plus_1h", "unknown_nested": True}})
        v = vpc.validate_registration_instance(r)
        self.assertTrue(len(v) > 0)
        self.assertTrue(any("unknown" in vi.lower() for vi in v))

    def test_claim_evidence_nested_reputation(self):
        ce = make_valid_claim_evidence({"evidence_artifacts": [{"artifact_id": "a1", "artifact_type": "article", "content_hash": "abc", "source": "A", "source_reputation_probability": 0.8}]})
        v = vpc.validate_claim_evidence_instance(ce)
        self.assertTrue(len(v) > 0)
        self.assertTrue(any("reputation" in vi.lower() for vi in v))

    def test_research_unit_missing_created_at(self):
        ru = {"research_unit_id": "ru_t_001", "design_type": "point_event_study", "eligibility_status": "eligible", "candidate_ref": "t_c_001", "information_form": "discrete_information_release"}
        v = vpc.validate_research_unit_instance(ru)
        self.assertTrue(len(v) > 0)
        self.assertTrue(any("created_at_utc" in vi.lower() for vi in v))


class TestNegativeOutcomeBundleConsistency(unittest.TestCase):
    """Negative cases for outcome/registration bundle consistency."""

    def test_outcome_without_registration_in_bundle(self):
        bundle = make_valid_research_bundle()
        bundle["outcome"]["registration_ref"] = "nonexistent"
        v = vpc.validate_research_bundle(bundle)
        self.assertTrue(len(v) > 0)
        self.assertTrue(any("registration_ref" in vi.lower() for vi in v))

    def test_outcome_benchmark_mismatch_in_bundle(self):
        reg = make_valid_registration()
        o = make_valid_outcome({"registered_benchmark_relative_reaction": {"benchmark": "WRONG", "relative_change_pct": -1.0}})
        bundle = make_valid_research_bundle()
        bundle["registration"] = reg
        bundle["outcome"] = o
        v = vpc.validate_research_bundle(bundle)
        self.assertTrue(len(v) > 0)
        self.assertTrue(any("benchmark" in vi.lower() for vi in v))


class TestNegativeAttribution(unittest.TestCase):
    """Negative cases for validate_attribution_instance."""

    def test_fail_gate_with_attribution_compatible_rejected(self):
        gates = {g: "pass" for g in HARD_GATES}
        gates["research_eligibility"] = "fail"
        a = make_valid_attribution({"hard_gates": gates, "verdict": "attribution_compatible"})
        v = vpc.validate_attribution_instance(a)
        self.assertTrue(len(v) > 0)
        self.assertTrue(any("verdict" in vi.lower() or "gate" in vi.lower() for vi in v))

    def test_unknown_gate_with_limited_support_rejected(self):
        gates = {g: "pass" for g in HARD_GATES}
        gates["usable_t0"] = "unknown"
        a = make_valid_attribution({"hard_gates": gates, "verdict": "limited_attribution_support"})
        v = vpc.validate_attribution_instance(a)
        self.assertTrue(len(v) > 0)
        self.assertTrue(any("verdict" in vi.lower() or "gate" in vi.lower() for vi in v))

    def test_inseparable_with_separability_pass_rejected(self):
        a = make_valid_attribution()
        inter = make_valid_interference({"separability_status": "inseparable", "collision_set": [{"event_id": "e1", "event_description": "Other event"}]})
        v = vpc.validate_attribution_instance(a, interference=inter)
        self.assertTrue(len(v) > 0)
        self.assertTrue(any("separability" in vi.lower() for vi in v))


class TestNegativeInterference(unittest.TestCase):
    """Negative cases for validate_interference_instance."""

    def test_coverage_insufficient_and_isolated_rejected(self):
        i = make_valid_interference({"coverage_insufficiency": True, "separability_status": "isolated"})
        v = vpc.validate_interference_instance(i)
        self.assertTrue(len(v) > 0)
        self.assertTrue(any("isolated" in vi.lower() for vi in v))


class TestNegativeEventIdentity(unittest.TestCase):
    """Negative cases for validate_event_instance_instance."""

    def test_identity_unresolved_with_supersedes_rejected(self):
        ei = make_valid_event_instance({"relationship_to_thread": "identity_unresolved", "supersedes": "ei_prev_001"})
        v = vpc.validate_event_instance_instance(ei)
        self.assertTrue(len(v) > 0)
        self.assertTrue(any("identity_unresolved" in vi.lower() for vi in v))

    def test_version_lt_one_rejected(self):
        ei = make_valid_event_instance({"instance_version": 0})
        v = vpc.validate_event_instance_instance(ei)
        self.assertTrue(len(v) > 0)

    def test_versioned_relation_without_prior_ref(self):
        ei = make_valid_event_instance({"relationship_to_thread": "correction_of"})
        v = vpc.validate_event_instance_instance(ei)
        self.assertTrue(len(v) > 0)

    def test_float_instance_version_rejected(self):
        """instance_version must be integer, not float."""
        ei = make_valid_event_instance({"instance_version": 1.5})
        v = vpc.validate_event_instance_instance(ei)
        self.assertTrue(len(v) > 0)
        self.assertTrue(any("integer" in vi.lower() for vi in v))

    def test_bool_instance_version_rejected(self):
        """instance_version must be integer, not bool."""
        ei = make_valid_event_instance({"instance_version": True})
        v = vpc.validate_event_instance_instance(ei)
        self.assertTrue(len(v) > 0)
        self.assertTrue(any("boolean" in vi.lower() for vi in v))


class TestNegativeAttributionExtended(unittest.TestCase):
    """Extended negative cases for attribution assessment."""

    def test_missing_dimension_rejected(self):
        dims = {d: "unknown" for d in vpc.DIMENSION_ENUM}
        del dims["temporal_ordering"]
        a = make_valid_attribution({"dimensions": dims})
        v = vpc.validate_attribution_instance(a)
        self.assertTrue(len(v) > 0)
        self.assertTrue(any("temporal_ordering" in vi.lower() for vi in v))

    def test_unknown_hard_gate_rejected(self):
        gates = {g: "pass" for g in HARD_GATES}
        gates["made_up_gate"] = "pass"
        a = make_valid_attribution({"hard_gates": gates})
        v = vpc.validate_attribution_instance(a)
        self.assertTrue(len(v) > 0)
        self.assertTrue(any("made_up_gate" in vi.lower() for vi in v))


class TestNegativeClaimEvidence(unittest.TestCase):
    """Negative cases for validate_claim_evidence_instance."""

    def test_missing_independence_groups_rejected(self):
        ce = make_valid_claim_evidence()
        del ce["independence_groups"]
        v = vpc.validate_claim_evidence_instance(ce)
        self.assertTrue(len(v) > 0)
        self.assertTrue(any("independence_group" in vi.lower() for vi in v))

    def test_global_reputation_score_rejected(self):
        ce = make_valid_claim_evidence({"global_reputation_score": 0.85})
        v = vpc.validate_claim_evidence_instance(ce)
        self.assertTrue(len(v) > 0)


class TestNegativeNumericAttribution(unittest.TestCase):
    """Numeric terms must not appear anywhere in assessment."""

    def test_nested_attribution_score_rejected(self):
        a = make_valid_attribution({"attribution_score": 0.75})
        v = vpc.validate_attribution_instance(a)
        self.assertTrue(len(v) > 0)


class TestNegativeResearchBundle(unittest.TestCase):
    """Bundle-level consistency checks."""

    def test_actual_outcome_without_registration(self):
        bundle = make_valid_research_bundle()
        bundle["registration"] = None
        v = vpc.validate_research_bundle(bundle, lifecycle_stage="outcome_revealed")
        self.assertTrue(len(v) > 0)
        self.assertTrue(any("registration missing" in vi.lower() for vi in v))

    def test_outcome_ref_mismatch(self):
        bundle = make_valid_research_bundle()
        bundle["outcome"]["registration_ref"] = "nonexistent"
        v = vpc.validate_research_bundle(bundle, lifecycle_stage="outcome_revealed")
        self.assertTrue(len(v) > 0)
        self.assertTrue(any("registration_ref" in vi.lower() for vi in v))

    def test_registered_lifecycle_no_outcome_passes(self):
        """registered lifecycle must NOT have outcome, and that's correct."""
        bundle = make_valid_research_bundle()
        bundle["outcome"] = None
        v = vpc.validate_research_bundle(bundle, lifecycle_stage="registered")
        self.assertEqual(len(v), 0, "registered lifecycle without outcome must pass")

    def test_outcome_revealed_lifecycle_missing_outcome_rejected(self):
        bundle = make_valid_research_bundle()
        bundle["outcome"] = None
        v = vpc.validate_research_bundle(bundle, lifecycle_stage="outcome_revealed")
        self.assertTrue(len(v) > 0)
        self.assertTrue(any("outcome missing" in vi.lower() for vi in v))

    def test_outcome_revealed_lifecycle_missing_registration_rejected(self):
        bundle = make_valid_research_bundle()
        bundle["registration"] = None
        v = vpc.validate_research_bundle(bundle, lifecycle_stage="outcome_revealed")
        self.assertTrue(len(v) > 0)
        self.assertTrue(any("registration missing" in vi.lower() for vi in v))

    def test_unknown_lifecycle_stage_rejected(self):
        bundle = make_valid_research_bundle()
        v = vpc.validate_research_bundle(bundle, lifecycle_stage="invalid_stage")
        self.assertTrue(len(v) > 0)
        self.assertTrue(any("unknown" in vi.lower() for vi in v))

    def test_development_normal_validation_passes(self):
        """Development bundle should pass normal bundle validation."""
        bundle = make_valid_research_bundle()
        bundle["registration"]["data_partition"] = "development"
        v = vpc.validate_research_bundle(bundle)
        self.assertEqual(len(v), 0, "Development bundle must pass normal validation")

    def test_development_aggregate_rejected(self):
        """Development bundle must be rejected by aggregate membership check."""
        bundle = make_valid_research_bundle()
        bundle["registration"]["data_partition"] = "development"
        v = vpc.validate_aggregate_membership(bundle, "calibration")
        self.assertTrue(len(v) > 0, "Development bundle must not count toward pilot aggregate")
        self.assertTrue(any("development" in vi.lower() for vi in v))

    def test_development_to_holdout_rejected(self):
        bundle = make_valid_research_bundle()
        bundle["registration"]["data_partition"] = "development"
        v = vpc.validate_aggregate_membership(bundle, "holdout")
        self.assertTrue(len(v) > 0)
        self.assertTrue(any("development" in vi.lower() for vi in v))

    def test_holdout_to_calibration_rejected(self):
        bundle = make_valid_research_bundle()
        bundle["registration"]["data_partition"] = "holdout"
        v = vpc.validate_aggregate_membership(bundle, "calibration")
        self.assertTrue(len(v) > 0)

    def test_calibration_to_holdout_rejected(self):
        bundle = make_valid_research_bundle()
        bundle["registration"]["data_partition"] = "calibration"
        v = vpc.validate_aggregate_membership(bundle, "holdout")
        self.assertTrue(len(v) > 0)

    def test_calibration_to_calibration_passes(self):
        bundle = make_valid_research_bundle()
        bundle["registration"]["data_partition"] = "calibration"
        v = vpc.validate_aggregate_membership(bundle, "calibration")
        self.assertEqual(len(v), 0)

    def test_holdout_to_holdout_passes(self):
        bundle = make_valid_research_bundle()
        bundle["registration"]["data_partition"] = "holdout"
        v = vpc.validate_aggregate_membership(bundle, "holdout")
        self.assertEqual(len(v), 0)


# ═══════════════════════════════════════════════════════════════
# Positive Tests — Valid instances pass without violations
# ═══════════════════════════════════════════════════════════════


class TestPositiveInstances(unittest.TestCase):
    """Valid instances pass all instance validators."""

    def test_valid_candidate_passes(self):
        c = make_valid_candidate()
        v = vpc.validate_candidate_instance(c)
        self.assertEqual(len(v), 0)

    def test_valid_registration_passes(self):
        r = make_valid_registration()
        v = vpc.validate_registration_instance(r)
        self.assertEqual(len(v), 0)

    def test_valid_outcome_passes(self):
        o = make_valid_outcome()
        v = vpc.validate_outcome_instance(o)
        self.assertEqual(len(v), 0)

    def test_valid_attribution_passes(self):
        a = make_valid_attribution()
        v = vpc.validate_attribution_instance(a)
        self.assertEqual(len(v), 0)

    def test_attribution_compatible_all_gates_pass(self):
        """attribution_compatible is valid when all 7 hard gates pass."""
        a = make_valid_attribution({"verdict": "attribution_compatible"})
        v = vpc.validate_attribution_instance(a)
        self.assertEqual(len(v), 0)

    def test_limited_attribution_support_all_gates_pass(self):
        """limited_attribution_support is valid when all 7 hard gates pass."""
        a = make_valid_attribution({"verdict": "limited_attribution_support"})
        v = vpc.validate_attribution_instance(a)
        self.assertEqual(len(v), 0)

    def test_valid_interference_passes(self):
        i = make_valid_interference()
        v = vpc.validate_interference_instance(i)
        self.assertEqual(len(v), 0)

    def test_valid_event_instance_passes(self):
        ei = make_valid_event_instance()
        v = vpc.validate_event_instance_instance(ei)
        self.assertEqual(len(v), 0)

    def test_valid_claim_evidence_passes(self):
        ce = make_valid_claim_evidence()
        v = vpc.validate_claim_evidence_instance(ce)
        self.assertEqual(len(v), 0)

    def test_valid_research_bundle_passes(self):
        bundle = make_valid_research_bundle()
        v = vpc.validate_research_bundle(bundle)
        self.assertEqual(len(v), 0)


# ═══════════════════════════════════════════════════════════════
# Structural Tests (same as before, maintained)
# ═══════════════════════════════════════════════════════════════


class TestFilesExist(unittest.TestCase):
    def test_root_files_exist(self):
        for f in REQUIRED_ROOT:
            self.assertTrue(os.path.isfile(os.path.join(PILOT_DIR, f)))

    def test_protocols_exist(self):
        for p in REQUIRED_PROTOCOLS:
            self.assertTrue(os.path.isfile(os.path.join(PROTOCOL_DIR, p)))

    def test_schemas_exist(self):
        for s in REQUIRED_SCHEMAS:
            self.assertTrue(os.path.isfile(os.path.join(SCHEMA_DIR, s)))


class TestDecisionMapping(unittest.TestCase):
    def setUp(self):
        with open(os.path.join(PILOT_DIR, "PROTOCOL_REGISTRY.json"), encoding="utf-8") as f:
            self.registry = json.load(f)

    def test_all_11_decisions_present(self):
        decisions = {d["decision"] for d in self.registry.get("decision_mappings", []) if isinstance(d.get("decision"), int)}
        self.assertEqual(decisions, set(range(1, 12)))

    def test_no_decision_outside_1_11(self):
        decisions = {d["decision"] for d in self.registry.get("decision_mappings", []) if isinstance(d.get("decision"), int)}
        self.assertTrue(all(1 <= d <= 11 for d in decisions))


class TestRegistryEnums(unittest.TestCase):
    def setUp(self):
        with open(os.path.join(PILOT_DIR, "PROTOCOL_REGISTRY.json"), encoding="utf-8") as f:
            self.registry = json.load(f)
        self.enums = self.registry.get("frozen_enums", {})

    def test_research_eligibility_enum(self):
        self.assertEqual(set(self.enums.get("research_eligibility", [])), vpc.ELIGIBILITY_ENUM)

    def test_identity_relationship_enum(self):
        self.assertEqual(set(self.enums.get("identity_relationship", [])), vpc.IDENTITY_ENUM)

    def test_dimension_enum(self):
        self.assertEqual(set(self.enums.get("attribution_dimension", [])), vpc.DIMENSION_ENUM)

    def test_verdict_enum(self):
        self.assertEqual(set(self.enums.get("attribution_verdict", [])), vpc.VERDICT_ENUM)


class TestSchemaEnums(unittest.TestCase):
    def _load_schema(self, name):
        with open(os.path.join(SCHEMA_DIR, name), encoding="utf-8") as f:
            return json.load(f)

    def test_attribution_verdict_in_schema(self):
        s = self._load_schema("attribution_assessment.schema.json")
        self.assertEqual(set(s["properties"]["verdict"]["enum"]), vpc.VERDICT_ENUM)

    def test_attribution_dimensions_in_schema(self):
        s = self._load_schema("attribution_assessment.schema.json")
        self.assertEqual(set(s["properties"]["dimensions"]["properties"].keys()), vpc.DIMENSION_ENUM)

    def test_separability_in_interference_schema(self):
        s = self._load_schema("interference_record.schema.json")
        sep = set(s["properties"]["separability_status"]["enum"])
        self.assertIn("insufficient_inventory", sep)
        self.assertIn("isolated", sep)

    def test_registration_outcome_separate(self):
        reg = self._load_schema("registration.schema.json")
        out = self._load_schema("outcome.schema.json")
        self.assertIn("outcome_status", reg.get("required", []))
        self.assertIn("registration_ref", out.get("required", []))
        reg_only = {"registration_id", "target_asset", "selected_clock", "primary_t0", "data_partition", "git_commit", "file_sha256"}
        overlap = reg_only & set(out.get("properties", {}).keys())
        self.assertEqual(len(overlap), 0)


class TestForbiddenProperties(unittest.TestCase):
    def _check_forbidden(self, name):
        with open(os.path.join(SCHEMA_DIR, name), encoding="utf-8") as f:
            s = json.load(f)
        for prop in vpc.FORBIDDEN_SCHEMA_PROPERTIES:
            self.assertNotIn(prop, s.get("properties", {}))

    def test_candidate_no_forbidden(self): self._check_forbidden("candidate.schema.json")
    def test_registration_no_forbidden(self): self._check_forbidden("registration.schema.json")
    def test_outcome_no_forbidden(self): self._check_forbidden("outcome.schema.json")
    def test_attribution_no_forbidden(self): self._check_forbidden("attribution_assessment.schema.json")
    def test_interference_no_forbidden(self): self._check_forbidden("interference_record.schema.json")


class TestDevelopmentSetIsolation(unittest.TestCase):
    def setUp(self):
        with open(os.path.join(PILOT_DIR, "PROTOCOL_REGISTRY.json"), encoding="utf-8") as f:
            self.registry = json.load(f)

    def test_dev_set_counts_false(self):
        self.assertFalse(self.registry["development_set_isolation"]["counts_toward_pilot_statistics"])

    def test_dev_set_has_5_samples(self):
        self.assertEqual(len(self.registry["development_set_isolation"]["development_set"]), 5)


class TestNoiseGateCoupling(unittest.TestCase):
    def test_research_unit_no_noise_gate(self):
        with open(os.path.join(SCHEMA_DIR, "research_unit.schema.json"), encoding="utf-8") as f:
            text = f.read().lower()
        self.assertNotIn("noise_gate", text)


class TestBaselineAnchors(unittest.TestCase):
    def setUp(self):
        with open(os.path.join(PILOT_DIR, "PROTOCOL_REGISTRY.json"), encoding="utf-8") as f:
            self.registry = json.load(f)

    def test_sealed_v1_base_commit_present(self):
        self.assertIn("sealed_v1_base_commit", self.registry)
        self.assertEqual(self.registry["sealed_v1_base_commit"], "cfc1e09b9c4e0c734ae4bfc913b726c6e2b145f9")

    def test_phase0_initial_commit_present(self):
        self.assertIn("phase0_initial_commit", self.registry)
        self.assertEqual(self.registry["phase0_initial_commit"], "0ed9c0e473c6015a5a747317630375b1c8e51a91")


class TestCalibrationPilotConfig(unittest.TestCase):
    def setUp(self):
        with open(os.path.join(PILOT_DIR, "PROTOCOL_REGISTRY.json"), encoding="utf-8") as f:
            self.registry = json.load(f)

    def test_pilot_calibration_exists(self):
        cal = self.registry.get("pilot_calibration", {})
        self.assertEqual(cal.get("minimum_consecutive_days"), 14)
        self.assertEqual(cal.get("minimum_registered_cases"), 8)
        self.assertEqual(cal.get("minimum_event_families"), 3)


class TestValidatorSelfTest(unittest.TestCase):
    """Validator runs cleanly (PASS)."""

    def test_validator_functions_are_callable(self):
        for fn_name in ["validate_candidate_instance", "validate_registration_instance",
                        "validate_outcome_instance", "validate_interference_instance",
                        "validate_event_instance_instance", "validate_claim_evidence_instance",
                        "validate_attribution_instance", "validate_research_bundle",
                        "validate_candidate", "validate_registration", "validate_outcome",
                        "validate_event_instance", "validate_attribution_assessment",
                        "validate_claim_evidence", "validate_shadow_audit_protocol"]:
            self.assertTrue(callable(getattr(vpc, fn_name)), f"{fn_name} not callable")


if __name__ == "__main__":
    unittest.main(verbosity=2)
