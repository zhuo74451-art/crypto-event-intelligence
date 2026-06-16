#!/usr/bin/env python3
"""Protocol Consistency Validator for Pilot v1 Phase 0.

Checks internal consistency of protocol documents, schemas, registry, and data instances.
Supports --check-git-boundary to verify no sealed files are modified.

This module provides two layers of validation:
  1. Schema-level validators (existing): check JSON schema files for semantic correctness.
  2. Instance-level validators (new): check Python dict instances for data integrity.

Usage:
  python -X utf8 research/pilot_v1/validate_protocol_consistency.py
  python -X utf8 research/pilot_v1/validate_protocol_consistency.py --check-git-boundary --base 0ed9c0e473c6015a5a747317630375b1c8e51a91
"""

import json
import os
import sys
import argparse
import subprocess
import math

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

PROJ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PILOT_DIR = os.path.join(PROJ, "research", "pilot_v1")
SCHEMA_DIR = os.path.join(PILOT_DIR, "schemas")
PROTOCOL_DIR = os.path.join(PILOT_DIR, "protocols")

# ---------------------------------------------------------------------------
# Required file lists
# ---------------------------------------------------------------------------

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

# ---------------------------------------------------------------------------
# Enums — core protocol enums (immutable constants)
# ---------------------------------------------------------------------------

ELIGIBILITY_ENUM = {
    "eligible", "conditionally_eligible", "context_only",
    "routed_to_other_design", "ineligible", "insufficient_information",
}

SEPARABILITY_ENUM = {
    "isolated", "minor_interference", "conditionally_separable",
    "cluster_only", "inseparable", "insufficient_inventory",
}

IDENTITY_ENUM = {
    "duplicate_report_of", "update_of", "correction_of", "reversal_of",
    "follow_up_to", "part_of_thread", "related_not_same", "identity_unresolved",
}

DIMENSION_ENUM = {
    "temporal_ordering", "temporal_proximity",
    "benchmark_relative_materiality", "asset_specificity",
    "mechanism_consistency", "interference_and_separability",
    "alternative_explanations", "robustness",
}

VERDICT_ENUM = {
    "not_assessable", "descriptive_reaction_only", "insufficient_evidence",
    "attribution_compatible", "limited_attribution_support",
    "not_supported_in_registered_window", "cluster_level_association",
}

HARD_GATE_ENUM = {
    "research_eligibility", "event_evidence", "usable_t0",
    "pre_outcome_registration", "valid_outcome_measurement",
    "benchmark_validity", "separability",
}

HARD_GATE_VERDICT_ENUM = {"pass", "fail", "unknown"}

INFORMATION_FORM_ENUM = {
    "discrete_information_release", "discrete_observable_action",
    "state_snapshot", "cumulative_trend",
    "interpretation_or_narrative", "market_outcome_or_context",
}

EVIDENCE_ROLE_ENUM = {
    "primary_record", "originator_statement", "independent_verification",
    "carrier_or_relay", "interpretation", "derived_measurement",
    "anonymous_or_unverified_claim",
}

CLAIM_EVIDENCE_STATUS_ENUM = {
    "directly_verified", "supported", "single_source_supported",
    "self_reported", "derived", "disputed",
    "interpretation_only", "insufficient_evidence",
}

SELECTED_CLOCK_ENUM = {"action_clock", "information_clock"}

ACTUAL_TIME_BASIS_ENUM = {
    "occurrence_time", "action_time", "onchain_confirmation_time",
    "official_publication_time", "first_reliable_public_time",
    "detection_time", "broadcast_time", "ingestion_time",
}

SOURCE_MEDIUM_ENUM = {
    "news_article", "official_announcement", "social_media_post",
    "onchain_data_feed", "analyst_report", "regulatory_filing",
    "market_data_feed", "messaging_or_alert", "other",
}

CANDIDATE_STATUS_ENUM = {
    "pending", "routed_to_research", "routed_to_other_design",
    "excluded", "insufficient_information",
}

DESIGN_TYPE_ENUM = {"point_event_study"}

DISCRETE_INFORMATION_FORMS = {"discrete_information_release", "discrete_observable_action"}

MERGE_LIKE_RELATIONSHIPS = {"duplicate_report_of", "update_of", "correction_of", "reversal_of"}

FORBIDDEN_SCHEMA_PROPERTIES = [
    "abnormal_return", "attribution_score", "confidence_probability",
    "contribution_percentage", "win_rate", "buy_signal", "sell_signal",
    "long_signal", "short_signal", "action_recommendation",
]

FORBIDDEN_NUMERIC_TERMS = {"score", "probability", "percentage", "contribution", "win_rate"}

TRADING_ADVICE_TERMS = {"buy_signal", "sell_signal", "long_signal", "short_signal", "action_recommendation"}

# Registration-only fields that must not appear in Outcome
REGISTRATION_ONLY_FIELDS = {
    "registration_id", "target_asset", "selected_clock", "primary_t0",
    "t0_type", "git_commit", "file_sha256", "outcome_status",
    "primary_benchmark", "sensitivity_benchmarks", "data_partition",
    "pre_event_movement_check_definition",
}

# Outcome-only fields that must not appear in Registration
OUTCOME_ONLY_FIELDS = {
    "raw_market_reaction", "registered_benchmark_relative_reaction",
    "historical_materiality", "pre_event_movement_check_result", "outcome_id",
}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def load_schema(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def check_file_exists(path: str) -> bool:
    return os.path.isfile(path)


def check_commit_exists(commit_hash: str) -> bool:
    """Return True if *commit_hash* exists in the git repository."""
    try:
        result = subprocess.run(
            ["git", "cat-file", "-e", commit_hash],
            cwd=PROJ, capture_output=True, text=True,
        )
        return result.returncode == 0
    except Exception:
        return False


def check_git_boundary(base_commit: str) -> list[str]:
    """Check git boundary: only research/pilot_v1/** and test file are allowed."""
    violations = []
    try:
        for scope_name, cmd in [
            ("base..HEAD committed diff", ["git", "diff", "--name-only", base_commit]),
            ("staged", ["git", "diff", "--name-only", "--cached"]),
            ("unstaged", ["git", "diff", "--name-only"]),
            ("untracked", ["git", "ls-files", "--others", "--exclude-standard"]),
        ]:
            result = subprocess.run(cmd, cwd=PROJ, capture_output=True, text=True)
            if result.returncode != 0:
                violations.append(f"Git boundary check failed for {scope_name}: {result.stderr.strip()}")
                continue
            raw = result.stdout.strip()
            if not raw:
                continue
            for line in raw.split("\n"):
                line = line.strip()
                if not line:
                    continue
                if line.startswith("research/pilot_v1/") or line == "tests/test_pilot_v1_protocol_seal.py":
                    continue
                violations.append(f"File outside allowed paths ({scope_name}): {line}")
    except Exception as e:
        violations.append(f"Git boundary check error: {e}")
    return violations


def validate_registry_enum(registry_enum: set, expected_enum: set, label: str) -> list[str]:
    violations = []
    if registry_enum != expected_enum:
        missing = expected_enum - registry_enum
        extra = registry_enum - expected_enum
        if missing:
            violations.append(f"Registry missing {label} values: {missing}")
        if extra:
            violations.append(f"Registry has extra {label} values: {extra}")
    return violations


def check_schema_forbidden_props(schema: dict, forbidden: set, path: str) -> list[str]:
    violations = []
    props = schema.get("properties", {})
    for prop in forbidden:
        if prop in props:
            violations.append(f"Forbidden property '{prop}' found in {path}")
    return violations


def _window_type_matches_outcome_window(window_type: str, outcome_window: str) -> bool:
    """Return True if a registration primary_window type is consistent with an outcome window value."""
    mapping = {
        "t0_to_t_plus_1h": "1h",
        "t0_to_t_plus_4h": "4h",
        "t0_to_t_plus_24h": "24h",
    }
    expected = mapping.get(window_type)
    if expected is not None:
        return expected == outcome_window
    # Custom windows are compatible with any valid outcome window identifier
    if window_type == "custom":
        return True
    return False


def _check_nested_forbidden_terms(
    obj, forbidden_terms: set, path: str = "", check_strings: bool = False,
) -> list[str]:
    """Recursively walk *obj* (dict, list, or scalar) looking for property names
    (and optionally string values) containing any term from *forbidden_terms*."""
    violations = []
    if isinstance(obj, dict):
        for key, value in obj.items():
            current_path = f"{path}.{key}" if path else key
            key_lower = key.lower()
            for term in forbidden_terms:
                if term in key_lower:
                    violations.append(
                        f"Forbidden term '{term}' found in property '{current_path}'"
                    )
            if check_strings and key == "notes" and isinstance(value, str):
                value_lower = value.lower()
                for term in forbidden_terms:
                    if term in value_lower:
                        violations.append(
                            f"Forbidden term '{term}' found in '{current_path}' value"
                        )
            violations.extend(
                _check_nested_forbidden_terms(value, forbidden_terms, current_path, check_strings)
            )
    elif isinstance(obj, list):
        for i, item in enumerate(obj):
            violations.extend(
                _check_nested_forbidden_terms(item, forbidden_terms, f"{path}[{i}]", check_strings)
            )
    return violations


# ---------------------------------------------------------------------------
# Schema-level validators (check JSON schema files, not instances)
# ---------------------------------------------------------------------------


def validate_candidate(schema_path: str) -> list[str]:
    """Semantic check: information_form enum, source_medium present, additionalProperties=false."""
    violations = []
    schema = load_schema(schema_path)
    info_form = set(schema.get("properties", {}).get("information_form", {}).get("enum", []))
    if info_form != INFORMATION_FORM_ENUM:
        violations.append(f"Candidate information_form enum mismatch: {info_form ^ INFORMATION_FORM_ENUM}")
    if "source_medium" not in schema.get("required", []):
        violations.append("Candidate missing 'source_medium' in required fields")
    source_medium = set(schema.get("properties", {}).get("source_medium", {}).get("enum", []))
    if not source_medium:
        violations.append("Candidate source_medium has empty enum")
    if schema.get("additionalProperties") is not False:
        violations.append("Candidate schema missing additionalProperties: false")
    return violations


def validate_registration(schema_path: str) -> list[str]:
    """Semantic check: selected_clock is action_clock/information_clock, actual_time_basis present, no movement_detected."""
    violations = []
    schema = load_schema(schema_path)
    clock_enum = set(schema.get("properties", {}).get("selected_clock", {}).get("enum", []))
    if clock_enum != SELECTED_CLOCK_ENUM:
        violations.append(f"Registration selected_clock must be action_clock/information_clock, got: {clock_enum}")
    if "actual_time_basis" not in schema.get("required", []):
        violations.append("Registration missing 'actual_time_basis' in required fields")
    time_basis = set(schema.get("properties", {}).get("actual_time_basis", {}).get("enum", []))
    if time_basis != ACTUAL_TIME_BASIS_ENUM:
        violations.append(f"Registration actual_time_basis enum mismatch: {time_basis ^ ACTUAL_TIME_BASIS_ENUM}")
    # pre_event_movement_check_definition must NOT have movement_detected
    pre = schema.get("properties", {}).get("pre_event_movement_check_definition", {})
    pre_props = pre.get("properties", {}) if isinstance(pre, dict) else {}
    if "movement_detected" in pre_props:
        violations.append("Registration pre_event_movement_check_definition must NOT contain movement_detected")
    if "actual_time_basis" not in str(schema.get("required", [])):
        violations.append("Registration missing actual_time_basis in required")
    if schema.get("additionalProperties") is not False:
        violations.append("Registration schema missing additionalProperties: false")
    return violations


def validate_outcome(schema_path: str) -> list[str]:
    """Semantic check: has pre_event_movement_check_result (movement_detected), no registration fields."""
    violations = []
    schema = load_schema(schema_path)
    if "pre_event_movement_check_result" not in schema.get("required", []):
        violations.append("Outcome missing 'pre_event_movement_check_result' in required")
    pre_result = schema.get("properties", {}).get("pre_event_movement_check_result", {})
    pre_props = pre_result.get("properties", {}) if isinstance(pre_result, dict) else {}
    if "movement_detected" not in pre_props:
        violations.append("Outcome pre_event_movement_check_result missing 'movement_detected'")
    if schema.get("additionalProperties") is not False:
        violations.append("Outcome schema missing additionalProperties: false")
    # No Registration-only fields in Outcome
    out_props = set(schema.get("properties", {}).keys())
    overlap = REGISTRATION_ONLY_FIELDS & out_props
    if overlap:
        violations.append(f"Outcome shares Registration-specific fields: {overlap}")
    return violations


def validate_event_instance(schema_path: str) -> list[str]:
    """Semantic check: supersedes/superseded_by, observation_ref, instance_version."""
    violations = []
    schema = load_schema(schema_path)
    ei_props = schema.get("properties", {})
    if "supersedes" not in ei_props:
        violations.append("Event instance missing 'supersedes' field (reversibility)")
    if "superseded_by" not in ei_props:
        violations.append("Event instance missing 'superseded_by' field (reversibility)")
    if "observation_ref" not in ei_props:
        violations.append("Event instance missing 'observation_ref' field (three-layer identity)")
    if "instance_version" not in ei_props:
        violations.append("Event instance missing 'instance_version' field (versioned identity)")
    if schema.get("additionalProperties") is not False:
        violations.append("Event instance schema missing additionalProperties: false")
    return violations


def validate_attribution_assessment(schema_path: str) -> list[str]:
    """Semantic check: has hard_gates (all 7 with pass/fail/unknown), no numeric terms."""
    violations = []
    schema = load_schema(schema_path)
    if "hard_gates" not in schema.get("required", []):
        violations.append("Attribution assessment missing 'hard_gates' in required")
    gates_props = schema.get("properties", {}).get("hard_gates", {}).get("properties", {})
    gate_names = set(gates_props.keys())
    if gate_names != HARD_GATE_ENUM:
        missing = HARD_GATE_ENUM - gate_names
        extra = gate_names - HARD_GATE_ENUM
        if missing:
            violations.append(f"Attribution hard_gates missing: {missing}")
        if extra:
            violations.append(f"Attribution hard_gates extra: {extra}")
    # Check verdict enum match
    verdict_enum = set(schema.get("properties", {}).get("verdict", {}).get("enum", []))
    if verdict_enum != VERDICT_ENUM:
        violations.append(f"Attribution verdict enum mismatch: {verdict_enum ^ VERDICT_ENUM}")
    # No numeric terms in property names
    aa_props = set(schema.get("properties", {}).keys())
    for term in ["score", "probability", "percentage", "contribution", "win_rate"]:
        if any(term in p for p in aa_props):
            violations.append(f"Attribution property contains numeric term: '{term}'")
    return violations


def validate_claim_evidence(schema_path: str) -> list[str]:
    """Semantic check: evidence_role and claim_evidence_status enums."""
    violations = []
    schema = load_schema(schema_path)
    role_enum = set(schema.get("properties", {}).get("evidence_role", {}).get("enum", []))
    if role_enum != EVIDENCE_ROLE_ENUM:
        violations.append(f"Claim evidence role enum mismatch: {role_enum ^ EVIDENCE_ROLE_ENUM}")
    status_enum = set(schema.get("properties", {}).get("claim_evidence_status", {}).get("enum", []))
    if status_enum != CLAIM_EVIDENCE_STATUS_ENUM:
        violations.append(f"Claim evidence status enum mismatch: {status_enum ^ CLAIM_EVIDENCE_STATUS_ENUM}")
    return violations


def validate_shadow_audit_protocol(protocol_path: str) -> list[str]:
    """Check Protocol 09 contains shadow audit and calibration pilot requirements."""
    violations = []
    try:
        with open(protocol_path, "r", encoding="utf-8") as f:
            text = f.read()
    except FileNotFoundError:
        violations.append(f"Protocol 09 file not found: {protocol_path}")
        return violations

    shadow_requirements = [
        "candidate log",
        "reviewer",
        "adjudication",
        "blind",
        "unknown",
        "manual_review",
    ]
    for req in shadow_requirements:
        if req not in text.lower() and req not in text:
            violations.append(f"Protocol 09 missing shadow audit requirement: '{req}'")

    pilot_requirements = [
        "14 consecutive natural",
        "8 registered",
        "pre-register",
        "extension",
        "event families",
        "SHA256",
        "git commit",
    ]
    for req in pilot_requirements:
        if req not in text:
            violations.append(f"Protocol 09 missing calibration pilot requirement: '{req}'")

    return violations


# ---------------------------------------------------------------------------
# Instance-level validators (check Python dict instances, not schema files)
# ---------------------------------------------------------------------------


def validate_candidate_instance(candidate: dict) -> list[str]:
    """Validate a Candidate dict instance for data integrity.

    Checks required fields, information_form validity, status/form consistency.
    """
    violations = []

    # -- Required fields --
    required_fields = [
        "candidate_id", "information_form", "source_medium",
        "capture_time_utc", "status", "created_at_utc",
    ]
    for field in required_fields:
        if field not in candidate or candidate.get(field) is None:
            violations.append(f"Candidate missing required field: '{field}'")
        elif isinstance(candidate.get(field), str) and candidate[field].strip() == "":
            violations.append(f"Candidate required field '{field}' is empty")

    # -- information_form enum check --
    info_form = candidate.get("information_form")
    if info_form is not None and info_form not in INFORMATION_FORM_ENUM:
        violations.append(
            f"Candidate information_form '{info_form}' not in INFORMATION_FORM_ENUM"
        )

    # -- source_medium enum check --
    source_medium = candidate.get("source_medium")
    if source_medium is not None and source_medium not in SOURCE_MEDIUM_ENUM:
        violations.append(
            f"Candidate source_medium '{source_medium}' not in SOURCE_MEDIUM_ENUM"
        )

    # -- status enum check --
    status = candidate.get("status")
    if status is not None and status not in CANDIDATE_STATUS_ENUM:
        violations.append(
            f"Candidate status '{status}' not in valid status enum"
        )

    # -- excluded/insufficient_information must have non-empty exclusion_reason --
    if status in ("excluded", "insufficient_information"):
        reason = candidate.get("exclusion_reason")
        if not reason or (isinstance(reason, str) and reason.strip() == ""):
            violations.append(
                f"Candidate status is '{status}' but exclusion_reason is missing or empty"
            )

    # -- cumulative_trend AND status=routed_to_research is a violation --
    if info_form == "cumulative_trend" and status == "routed_to_research":
        violations.append(
            "Candidate information_form='cumulative_trend' with status='routed_to_research': "
            "chartable trend cannot be studied as point event"
        )

    # -- market_outcome_or_context AND routed_to_research is a violation --
    if info_form == "market_outcome_or_context" and status == "routed_to_research":
        violations.append(
            "Candidate information_form='market_outcome_or_context' with status='routed_to_research': "
            "market outcome/context cannot be the studied event"
        )

    return violations


def validate_research_unit_instance(research_unit: dict, candidate: dict = None) -> list[str]:
    """Validate a Research Unit dict instance for data integrity.

    If *candidate* is provided, cross-checks information_form consistency.
    """
    violations = []

    # -- Required fields --
    required_fields = [
        "research_unit_id", "design_type", "eligibility_status",
        "candidate_ref", "information_form",
    ]
    for field in required_fields:
        if field not in research_unit or research_unit.get(field) is None:
            violations.append(f"Research Unit missing required field: '{field}'")
        elif isinstance(research_unit.get(field), str) and research_unit[field].strip() == "":
            violations.append(f"Research Unit required field '{field}' is empty")

    # -- candidate_ref must be non-empty --
    cref = research_unit.get("candidate_ref")
    if cref and isinstance(cref, str) and cref.strip() == "":
        violations.append("Research Unit candidate_ref must be non-empty")

    # -- design_type must be "point_event_study" --
    design_type = research_unit.get("design_type")
    if design_type is not None and design_type != "point_event_study":
        violations.append(
            f"Research Unit design_type must be 'point_event_study', got '{design_type}'"
        )

    # -- eligibility_status enum check --
    elig = research_unit.get("eligibility_status")
    if elig is not None and elig not in ELIGIBILITY_ENUM:
        violations.append(
            f"Research Unit eligibility_status '{elig}' not in ELIGIBILITY_ENUM"
        )

    # -- point_event_study paired with non-discrete information_form --
    #    The bypass condition is eligibility_status == "context_only".
    info_form = research_unit.get("information_form")
    if design_type == "point_event_study" and info_form is not None:
        if info_form not in DISCRETE_INFORMATION_FORMS:
            elig_status = research_unit.get("eligibility_status")
            if elig_status != "context_only":
                violations.append(
                    f"Research Unit point_event_study with non-discrete information_form "
                    f"'{info_form}' and eligibility_status '{elig_status}' "
                    f"(allowed only for context_only bypass)"
                )

    # -- If candidate provided: information_form mismatch --
    if candidate is not None:
        cand_form = candidate.get("information_form")
        if info_form is not None and cand_form is not None and info_form != cand_form:
            violations.append(
                f"Research Unit information_form '{info_form}' differs from "
                f"Candidate information_form '{cand_form}'"
            )

    return violations


def validate_registration_instance(registration: dict) -> list[str]:
    """Validate a Registration dict instance for data integrity.

    Checks self-benchmark, broadcast_time prohibition, outcome field leakage,
    required field presence, and temporal separation from outcome data.
    """
    violations = []

    # -- Required fields --
    required_fields = [
        "registration_id", "research_unit_ref", "target_asset",
        "selected_clock", "actual_time_basis", "primary_t0",
        "primary_window", "primary_benchmark", "registration_time_utc",
        "git_commit", "file_sha256", "data_partition", "outcome_status",
    ]
    for field in required_fields:
        if field not in registration or registration.get(field) is None:
            violations.append(f"Registration missing required field: '{field}'")
        elif isinstance(registration.get(field), str) and registration[field].strip() == "":
            violations.append(f"Registration required field '{field}' is empty")

    # -- target_asset == primary_benchmark → self-benchmark --
    target = registration.get("target_asset")
    primary_bm = registration.get("primary_benchmark")
    if target is not None and primary_bm is not None and target == primary_bm:
        violations.append(
            f"Registration target_asset '{target}' equals primary_benchmark "
            f"'{primary_bm}' (self-benchmark not allowed)"
        )

    # -- target_asset appears in sensitivity_benchmarks --
    sensitivity = registration.get("sensitivity_benchmarks")
    if isinstance(sensitivity, list) and target is not None:
        if target in sensitivity:
            violations.append(
                f"Registration target_asset '{target}' found in sensitivity_benchmarks"
            )

    # -- sensitivity_benchmarks has duplicates --
    if isinstance(sensitivity, list):
        seen = set()
        for bm in sensitivity:
            if bm in seen:
                violations.append(
                    f"Registration sensitivity_benchmarks contains duplicate: '{bm}'"
                )
            seen.add(bm)

    # -- selected_clock enum check --
    sel_clock = registration.get("selected_clock")
    if sel_clock is not None:
        if sel_clock not in SELECTED_CLOCK_ENUM:
            violations.append(
                f"Registration selected_clock '{sel_clock}' not in SELECTED_CLOCK_ENUM"
            )
        if sel_clock == "broadcast_time":
            violations.append(
                "Registration selected_clock is 'broadcast_time' — not a valid clock"
            )

    # -- actual_time_basis enum check --
    time_basis = registration.get("actual_time_basis")
    if time_basis is not None and time_basis not in ACTUAL_TIME_BASIS_ENUM:
        violations.append(
            f"Registration actual_time_basis '{time_basis}' not in ACTUAL_TIME_BASIS_ENUM"
        )

    # -- Registration contains Outcome fields --
    for ofield in OUTCOME_ONLY_FIELDS:
        if ofield in registration:
            violations.append(
                f"Registration contains Outcome-only field: '{ofield}'"
            )

    # -- pre_event_movement_check_definition must NOT contain movement_detected --
    pre_def = registration.get("pre_event_movement_check_definition")
    if isinstance(pre_def, dict):
        if "movement_detected" in pre_def:
            violations.append(
                "Registration pre_event_movement_check_definition contains 'movement_detected'"
            )

    # -- outcome_status must be "not_revealed" --
    outcome_status = registration.get("outcome_status")
    if outcome_status is not None and outcome_status != "not_revealed":
        violations.append(
            f"Registration outcome_status must be 'not_revealed', got '{outcome_status}'"
        )

    # -- primary_window is missing or has wrong type --
    pw = registration.get("primary_window")
    if pw is None:
        violations.append("Registration primary_window is missing")
    elif not isinstance(pw, dict):
        violations.append(
            f"Registration primary_window must be a dict, got {type(pw).__name__}"
        )

    return violations


def validate_outcome_instance(outcome: dict, registration: dict = None) -> list[str]:
    """Validate an Outcome dict instance for data integrity.

    If *registration* is provided, cross-checks registration_ref match,
    benchmark consistency, window consistency, and sensitivity benchmarks.
    """
    violations = []

    # -- Required fields --
    required_fields = [
        "outcome_id", "registration_ref", "raw_market_reaction",
        "registered_benchmark_relative_reaction", "historical_materiality",
        "pre_event_movement_check_result", "calculated_at_utc",
    ]
    for field in required_fields:
        if field not in outcome or outcome.get(field) is None:
            violations.append(f"Outcome missing required field: '{field}'")
        elif isinstance(outcome.get(field), str) and outcome[field].strip() == "":
            violations.append(f"Outcome required field '{field}' is empty")

    # -- Contains registration-only fields --
    for rfield in REGISTRATION_ONLY_FIELDS:
        if rfield in outcome:
            violations.append(
                f"Outcome contains Registration-only field: '{rfield}'"
            )

    # -- If registration provided: cross-checks --
    if registration is not None:
        # Outcome registration_ref must match registration registration_id
        out_reg_ref = outcome.get("registration_ref")
        reg_id = registration.get("registration_id")
        if out_reg_ref is not None and reg_id is not None and out_reg_ref != reg_id:
            violations.append(
                f"Outcome registration_ref '{out_reg_ref}' does not match "
                f"Registration registration_id '{reg_id}'"
            )

        # Outcome benchmark must match registration primary_benchmark
        out_bm = outcome.get("registered_benchmark_relative_reaction", {})
        if isinstance(out_bm, dict):
            out_benchmark = out_bm.get("benchmark")
            reg_pb = registration.get("primary_benchmark")
            if out_benchmark is not None and reg_pb is not None and out_benchmark != reg_pb:
                violations.append(
                    f"Outcome benchmark '{out_benchmark}' does not match "
                    f"Registration primary_benchmark '{reg_pb}'"
                )

        # Outcome window matches registration primary_window
        rm_reaction = outcome.get("raw_market_reaction", {})
        if isinstance(rm_reaction, dict):
            outcome_window = rm_reaction.get("window")
            reg_window = registration.get("primary_window", {})
            if isinstance(reg_window, dict):
                reg_window_type = reg_window.get("window_type")
                if outcome_window is not None and reg_window_type is not None:
                    if not _window_type_matches_outcome_window(reg_window_type, outcome_window):
                        violations.append(
                            f"Outcome raw_market_reaction window '{outcome_window}' does not match "
                            f"Registration primary_window type '{reg_window_type}'"
                        )

        # sensitivity_benchmark_reactions entries must reference a registered benchmark
        reg_sb = registration.get("sensitivity_benchmarks", [])
        if not isinstance(reg_sb, list):
            reg_sb = []
        sb_reactions = outcome.get("sensitivity_benchmark_reactions", [])
        if isinstance(sb_reactions, list):
            for entry in sb_reactions:
                bm = entry.get("benchmark")
                if bm is not None and bm not in reg_sb:
                    violations.append(
                        f"Outcome sensitivity_benchmark_reaction references benchmark "
                        f"'{bm}' not found in registration.sensitivity_benchmarks"
                    )

    return violations


def validate_interference_instance(interference: dict) -> list[str]:
    """Validate an Interference Record dict instance.

    Required fields, separability/coverage consistency, collision set integrity.
    """
    violations = []

    # -- Required fields --
    required_fields = [
        "record_id", "research_unit_ref", "observation_window",
        "separability_status", "collision_set",
        "alternative_explanations", "coverage_insufficiency",
    ]
    for field in required_fields:
        if field not in interference or interference.get(field) is None:
            violations.append(f"Interference record missing required field: '{field}'")
        elif isinstance(interference.get(field), str) and interference[field].strip() == "":
            violations.append(f"Interference record required field '{field}' is empty")

    # -- separability_status enum check --
    sep_status = interference.get("separability_status")
    if sep_status is not None and sep_status not in SEPARABILITY_ENUM:
        violations.append(
            f"Interference separability_status '{sep_status}' not in SEPARABILITY_ENUM"
        )

    # -- coverage_insufficiency must be boolean --
    cov_insuf = interference.get("coverage_insufficiency")
    if cov_insuf is not None and not isinstance(cov_insuf, bool):
        violations.append(
            f"Interference coverage_insufficiency must be boolean, got {type(cov_insuf).__name__}"
        )

    # -- coverage_insufficiency=true AND separability_status=isolated --
    if cov_insuf is True and sep_status == "isolated":
        violations.append(
            "Interference coverage_insufficiency=true is incompatible with "
            "separability_status='isolated'"
        )

    # -- isolated AND non-empty collision_set --
    collision_set = interference.get("collision_set", [])
    if isinstance(collision_set, list):
        if sep_status == "isolated" and len(collision_set) > 0:
            has_event_items = any(
                isinstance(item, dict) and item.get("event_id")
                for item in collision_set
            )
            if has_event_items:
                violations.append(
                    "Interference separability_status='isolated' but collision_set "
                    "contains event entries"
                )

        # -- collision_set items must have event_id and event_description --
        for i, item in enumerate(collision_set):
            if isinstance(item, dict):
                if "event_id" not in item:
                    violations.append(
                        f"Interference collision_set[{i}] missing 'event_id'"
                    )
                if "event_description" not in item:
                    violations.append(
                        f"Interference collision_set[{i}] missing 'event_description'"
                    )

    # -- alternative_explanations must be non-empty list --
    alt_exp = interference.get("alternative_explanations")
    if alt_exp is not None:
        if not isinstance(alt_exp, list):
            violations.append(
                "Interference alternative_explanations must be a list"
            )
        elif len(alt_exp) == 0:
            violations.append(
                "Interference alternative_explanations must be non-empty"
            )

    # -- cluster_only/inseparable/insufficient_inventory note --
    #    This is documented for cross-check with attribution (see validate_attribution_instance).
    #    A hard failure is handled when attribution with interference context is validated.
    if sep_status in ("cluster_only", "inseparable", "insufficient_inventory"):
        # This is an informational note — the attribution-level cross check enforces it.
        pass

    return violations


def validate_event_instance_instance(event_instance: dict) -> list[str]:
    """Validate an Event Instance dict for data integrity.

    Identity relationships, versioning, and thread consistency.
    """
    violations = []

    # -- Required fields --
    required_fields = [
        "canonical_event_instance_id", "event_thread_ref",
        "relationship_to_thread", "relationship_evidence",
        "observation_ref", "instance_version", "created_at_utc",
    ]
    for field in required_fields:
        if field not in event_instance or event_instance.get(field) is None:
            violations.append(f"Event Instance missing required field: '{field}'")
        elif isinstance(event_instance.get(field), str) and event_instance[field].strip() == "":
            violations.append(f"Event Instance required field '{field}' is empty")

    # -- relationship_to_thread enum check --
    rel = event_instance.get("relationship_to_thread")
    if rel is not None and rel not in IDENTITY_ENUM:
        violations.append(
            f"Event Instance relationship_to_thread '{rel}' not in IDENTITY_ENUM"
        )

    # -- instance_version < 1 --
    inst_ver = event_instance.get("instance_version")
    if inst_ver is not None and isinstance(inst_ver, (int, float)):
        if inst_ver < 1:
            violations.append(
                f"Event Instance instance_version must be >= 1, got {inst_ver}"
            )

    # -- identity_unresolved AND having supersedes or superseded_by --
    if rel == "identity_unresolved":
        if event_instance.get("supersedes") or event_instance.get("superseded_by"):
            violations.append(
                "Event Instance relationship_to_thread='identity_unresolved' must not "
                "have supersedes or superseded_by"
            )

    # -- merge-like relationship without identity_merge_evidence --
    if rel in MERGE_LIKE_RELATIONSHIPS:
        if not event_instance.get("identity_merge_evidence"):
            violations.append(
                f"Event Instance relationship_to_thread='{rel}' requires "
                "identity_merge_evidence"
            )

    # -- correction_of/reversal_of/update_of without supersedes or superseded_by --
    if rel in ("correction_of", "reversal_of", "update_of"):
        if not event_instance.get("supersedes") and not event_instance.get("superseded_by"):
            violations.append(
                f"Event Instance relationship_to_thread='{rel}' but neither "
                "supersedes nor superseded_by references the prior instance"
            )

    return violations


def validate_claim_evidence_instance(record: dict) -> list[str]:
    """Validate a Claim Evidence Record dict for data integrity.

    Evidence role, claim evidence status, independence groups, and forbidden terms.
    """
    violations = []

    # -- Required fields --
    required_fields = [
        "record_id", "claim", "evidence_artifacts", "evidence_relations",
        "evidence_role", "claim_evidence_status", "independence_groups",
        "provenance_path", "created_at_utc",
    ]
    for field in required_fields:
        if field not in record or record.get(field) is None:
            violations.append(f"Claim Evidence Record missing required field: '{field}'")
        elif isinstance(record.get(field), str) and record[field].strip() == "":
            violations.append(f"Claim Evidence Record required field '{field}' is empty")

    # -- evidence_role enum check --
    ev_role = record.get("evidence_role")
    if ev_role is not None and ev_role not in EVIDENCE_ROLE_ENUM:
        violations.append(
            f"Claim Evidence Record evidence_role '{ev_role}' not in EVIDENCE_ROLE_ENUM"
        )

    # -- claim_evidence_status enum check --
    ce_status = record.get("claim_evidence_status")
    if ce_status is not None and ce_status not in CLAIM_EVIDENCE_STATUS_ENUM:
        violations.append(
            f"Claim Evidence Record claim_evidence_status '{ce_status}' "
            "not in CLAIM_EVIDENCE_STATUS_ENUM"
        )

    # -- independence_groups entirely missing (already caught by required but double-check) --
    ind_groups = record.get("independence_groups")
    if ind_groups is None:
        violations.append("Claim Evidence Record missing independence_groups")
    elif isinstance(ind_groups, list):
        # each group must have independence_status
        for i, group in enumerate(ind_groups):
            if isinstance(group, dict):
                if "independence_status" not in group or not group.get("independence_status"):
                    violations.append(
                        f"Claim Evidence Record independence_groups[{i}] missing "
                        "independence_status"
                    )

    # -- Any property named "global_reputation_score" or "source_trust_score" --
    for term in ("global_reputation_score", "source_trust_score"):
        if term in record:
            violations.append(
                f"Claim Evidence Record contains forbidden property: '{term}'"
            )

    return violations


def validate_attribution_instance(assessment: dict, interference: dict = None) -> list[str]:
    """Validate an Attribution Assessment dict for data integrity.

    Hard gates, verdict consistency, forbidden numeric terms, and interference cross-check.
    """
    violations = []

    # -- Required fields --
    required_fields = [
        "assessment_id", "research_unit_ref", "hard_gates",
        "dimensions", "verdict", "created_at_utc",
    ]
    for field in required_fields:
        if field not in assessment or assessment.get(field) is None:
            violations.append(f"Attribution Assessment missing required field: '{field}'")
        elif isinstance(assessment.get(field), str) and assessment[field].strip() == "":
            violations.append(f"Attribution Assessment required field '{field}' is empty")

    # -- verdict enum check --
    verdict = assessment.get("verdict")
    if verdict is not None and verdict not in VERDICT_ENUM:
        violations.append(
            f"Attribution Assessment verdict '{verdict}' not in VERDICT_ENUM"
        )

    # -- Hard gates checks --
    hard_gates = assessment.get("hard_gates", {})
    if isinstance(hard_gates, dict):
        # Any hard gate missing
        for gate in HARD_GATE_ENUM:
            if gate not in hard_gates:
                violations.append(
                    f"Attribution Assessment hard_gates missing: '{gate}'"
                )
        # Any hard gate value not in {pass, fail, unknown}
        for gate, value in hard_gates.items():
            if gate in HARD_GATE_ENUM:
                if value not in HARD_GATE_VERDICT_ENUM:
                    violations.append(
                        f"Attribution Assessment hard_gates.{gate} value '{value}' "
                        "not in {pass, fail, unknown}"
                    )

        # verdict in {attribution_compatible, limited_attribution_support} AND any gate is fail/unknown
        if verdict in ("attribution_compatible", "limited_attribution_support"):
            failing_gates = [
                g for g, v in hard_gates.items()
                if v in ("fail", "unknown")
            ]
            if failing_gates:
                violations.append(
                    f"Attribution Assessment verdict '{verdict}' requires all hard gates "
                    f"to be 'pass', but the following are not: {failing_gates}"
                )

    # -- Single-case verdict exceeding frozen ceiling --
    #    Frozen ceiling: limited_attribution_support.
    #    attribution_compatible exceeds the ceiling.
    if verdict == "attribution_compatible":
        violations.append(
            "Attribution Assessment verdict 'attribution_compatible' exceeds "
            "the Pilot Phase 0 frozen ceiling of 'limited_attribution_support'"
        )

    # -- If interference provided: cross-check separability --
    if interference is not None:
        sep_status = interference.get("separability_status")
        if isinstance(hard_gates, dict):
            sep_gate = hard_gates.get("separability")
            if sep_status in ("cluster_only", "inseparable", "insufficient_inventory"):
                if sep_gate == "pass":
                    violations.append(
                        f"Attribution Assessment separability hard gate is 'pass' but "
                        f"interference separability_status is '{sep_status}'"
                    )

    # -- Any nested property named: score, probability, percentage, contribution, win_rate --
    violations.extend(
        _check_nested_forbidden_terms(assessment, FORBIDDEN_NUMERIC_TERMS)
    )

    # -- Any trading advice terms in property names or notes --
    violations.extend(
        _check_nested_forbidden_terms(assessment, TRADING_ADVICE_TERMS, check_strings=True)
    )

    return violations


def validate_research_bundle(bundle: dict) -> list[str]:
    """Validate a complete research bundle for cross-record consistency.

    A bundle is a dict containing: candidate, research_unit, registration, outcome,
    interference, event_instance, claim_evidence, attribution.

    Runs individual instance validators for each sub-record, then checks
    cross-record consistency.
    """
    violations = []

    # -- Extract instances --
    candidate = bundle.get("candidate", {})
    research_unit = bundle.get("research_unit", {})
    registration = bundle.get("registration", {})
    outcome = bundle.get("outcome", {})
    interference = bundle.get("interference", {})
    event_instance = bundle.get("event_instance", {})
    claim_evidence = bundle.get("claim_evidence", {})
    attribution = bundle.get("attribution", {})

    # -- Run individual validators --
    if candidate:
        violations.extend(
            f"[candidate] {v}" for v in validate_candidate_instance(candidate)
        )
    if research_unit:
        violations.extend(
            f"[research_unit] {v}"
            for v in validate_research_unit_instance(research_unit, candidate or None)
        )
    if registration:
        violations.extend(
            f"[registration] {v}" for v in validate_registration_instance(registration)
        )
    if outcome:
        violations.extend(
            f"[outcome] {v}" for v in validate_outcome_instance(outcome, registration or None)
        )
    if interference:
        violations.extend(
            f"[interference] {v}" for v in validate_interference_instance(interference)
        )
    if event_instance:
        violations.extend(
            f"[event_instance] {v}" for v in validate_event_instance_instance(event_instance)
        )
    if claim_evidence:
        violations.extend(
            f"[claim_evidence] {v}" for v in validate_claim_evidence_instance(claim_evidence)
        )
    if attribution:
        violations.extend(
            f"[attribution] {v}"
            for v in validate_attribution_instance(attribution, interference or None)
        )

    # -- Cross-record checks --

    # 1. Outcome registration_ref must match registration registration_id
    if outcome and registration:
        out_reg_ref = outcome.get("registration_ref")
        reg_id = registration.get("registration_id")
        if out_reg_ref and reg_id and out_reg_ref != reg_id:
            violations.append(
                "Bundle: outcome.registration_ref does not match "
                "registration.registration_id"
            )

    # 2. Registration must be created before Outcome
    if outcome and registration:
        reg_time = registration.get("registration_time_utc")
        out_time = outcome.get("calculated_at_utc")
        if reg_time and out_time and reg_time >= out_time:
            violations.append(
                "Bundle: registration_time_utc must be before calculated_at_utc "
                "(registration before outcome)"
            )

    # 3. Outcome benchmark matches registration primary_benchmark
    if outcome and registration:
        out_bm = outcome.get("registered_benchmark_relative_reaction", {})
        if isinstance(out_bm, dict):
            out_benchmark = out_bm.get("benchmark")
            reg_pb = registration.get("primary_benchmark")
            if out_benchmark and reg_pb and out_benchmark != reg_pb:
                violations.append(
                    "Bundle: outcome benchmark does not match registration primary_benchmark"
                )

    # 4. Outcome window matches registration primary_window
    if outcome and registration:
        rm_reaction = outcome.get("raw_market_reaction", {})
        if isinstance(rm_reaction, dict):
            outcome_window = rm_reaction.get("window")
            reg_window = registration.get("primary_window", {})
            if isinstance(reg_window, dict):
                reg_window_type = reg_window.get("window_type")
                if outcome_window and reg_window_type:
                    if not _window_type_matches_outcome_window(reg_window_type, outcome_window):
                        violations.append(
                            "Bundle: outcome raw_market_reaction window does not match "
                            "registration primary_window type"
                        )

    # 5. Outcome must NOT modify Registration parameters
    #    Check that outcome doesn't contain registration-only fields
    if outcome:
        for rfield in REGISTRATION_ONLY_FIELDS:
            if rfield in outcome:
                violations.append(
                    f"Bundle: outcome contains Registration-only field '{rfield}'"
                )

    # 6. Registration and Outcome must be physically separate dicts
    if outcome is not None and registration is not None:
        if id(outcome) == id(registration):
            violations.append(
                "Bundle: registration and outcome are the same object (shared reference)"
            )

    # 7. If data_partition='development', must not be counted toward Pilot aggregate
    if registration:
        dp = registration.get("data_partition")
        if dp == "development":
            violations.append(
                "Bundle: registration data_partition='development' — must not be "
                "counted toward Pilot aggregate statistics"
            )

    return violations


# ---------------------------------------------------------------------------
# main()
# ---------------------------------------------------------------------------


def main():
    parser = argparse.ArgumentParser(description="Protocol Consistency Validator v1")
    parser.add_argument("--check-git-boundary", action="store_true",
                        help="Check git boundary: only allowed paths modified")
    parser.add_argument("--base", type=str, default=None,
                        help="Base commit for git boundary check")
    args = parser.parse_args()

    violations = []

    # ── 1. Required files exist ──
    root_files = ["README.md", "PILOT_CHARTER.md", "PROTOCOL_REGISTRY.json",
                  "validate_protocol_consistency.py", "reports/PHASE_0_ACCEPTANCE_REPORT.md"]
    for f in root_files:
        if not check_file_exists(os.path.join(PILOT_DIR, f)):
            violations.append(f"Missing required file: research/pilot_v1/{f}")
    for p in REQUIRED_PROTOCOLS:
        if not check_file_exists(os.path.join(PROTOCOL_DIR, p)):
            violations.append(f"Missing required protocol: protocols/{p}")
    for s in REQUIRED_SCHEMAS:
        if not check_file_exists(os.path.join(SCHEMA_DIR, s)):
            violations.append(f"Missing required schema: schemas/{s}")

    # ── 2. No extra empty directories ──
    for dirpath, dirnames, filenames in os.walk(PILOT_DIR):
        # Skip __pycache__ and hidden directories
        dirnames[:] = [d for d in dirnames if not d.startswith("__") and not d.startswith(".")]
        if dirpath == PILOT_DIR:
            pass
        rel = os.path.relpath(dirpath, PILOT_DIR)
        if rel in ("protocols", "schemas", "reports"):
            continue
        if rel.startswith("."):
            continue
        if filenames:
            violations.append(f"Unexpected file in pilot_v1: {rel}/{filenames[0]}")

    # ── 3. Load registry ──
    registry_path = os.path.join(PILOT_DIR, "PROTOCOL_REGISTRY.json")
    registry = json.load(open(registry_path, "r", encoding="utf-8"))
    reg_enums = registry.get("frozen_enums", {})

    # ── 4. All 11 decisions mapped ──
    decisions = registry.get("decision_mappings", [])
    decision_numbers = {d["decision"] for d in decisions if isinstance(d.get("decision"), int)}
    expected_decisions = set(range(1, 12))
    if decision_numbers != expected_decisions:
        missing_d = expected_decisions - decision_numbers
        extra_d = decision_numbers - expected_decisions
        if missing_d:
            violations.append(f"Missing decision mappings: {sorted(missing_d)}")
        if extra_d:
            violations.append(f"Extra decision mappings: {sorted(extra_d)}")

    # ── 5. All schemas parse and have correct $schema ──
    for s in REQUIRED_SCHEMAS:
        schema_path = os.path.join(SCHEMA_DIR, s)
        try:
            schema = json.load(open(schema_path, "r", encoding="utf-8"))
            if schema.get("$schema") != "https://json-schema.org/draft/2020-12/schema":
                violations.append(f"{s}: $schema is not draft 2020-12")
            v = check_schema_forbidden_props(schema, FORBIDDEN_SCHEMA_PROPERTIES, s)
            violations.extend(v)
        except (json.JSONDecodeError, IOError) as e:
            violations.append(f"{s}: cannot parse: {e}")

    # ── 6. Registry enums consistency ──
    checks = [
        ("candidate_status", {"pending", "routed_to_research", "routed_to_other_design", "excluded", "insufficient_information"}),
        ("research_eligibility", ELIGIBILITY_ENUM),
        ("separability_status", SEPARABILITY_ENUM),
        ("identity_relationship", IDENTITY_ENUM),
        ("attribution_verdict", VERDICT_ENUM),
        ("hard_gate", HARD_GATE_ENUM),
        ("hard_gate_verdict", HARD_GATE_VERDICT_ENUM),
    ]
    for enum_name, expected in checks:
        actual = set(reg_enums.get(enum_name, []))
        v = validate_registry_enum(actual, expected, enum_name)
        violations.extend(v)

    # ── 7. Semantic schema validation ──
    violations.extend(validate_candidate(os.path.join(SCHEMA_DIR, "candidate.schema.json")))
    violations.extend(validate_registration(os.path.join(SCHEMA_DIR, "registration.schema.json")))
    violations.extend(validate_outcome(os.path.join(SCHEMA_DIR, "outcome.schema.json")))
    violations.extend(validate_event_instance(os.path.join(SCHEMA_DIR, "event_instance.schema.json")))
    violations.extend(validate_attribution_assessment(os.path.join(SCHEMA_DIR, "attribution_assessment.schema.json")))
    violations.extend(validate_claim_evidence(os.path.join(SCHEMA_DIR, "claim_evidence_record.schema.json")))
    violations.extend(validate_shadow_audit_protocol(os.path.join(PROTOCOL_DIR, "09_NOISE_GATE_SHADOW_AUDIT_AND_PILOT_EXECUTION.md")))

    # ── 8. Registration/Outcome separate ──
    reg_schema = load_schema(os.path.join(SCHEMA_DIR, "registration.schema.json"))
    out_schema = load_schema(os.path.join(SCHEMA_DIR, "outcome.schema.json"))
    if "outcome_status" not in reg_schema.get("required", []):
        violations.append("Registration missing 'outcome_status' in required fields")
    if "registration_ref" not in out_schema.get("required", []):
        violations.append("Outcome missing 'registration_ref' in required fields")

    # ── 9. Research Unit does not reference Legacy Noise Gate ──
    ru_schema = load_schema(os.path.join(SCHEMA_DIR, "research_unit.schema.json"))
    ru_text = json.dumps(ru_schema)
    for term in ["noise_gate", "noise_gate_result", "legacy_noise_gate_pass", "legacy_noise_gate_reject"]:
        if term in ru_text.lower():
            violations.append(f"Research Unit schema references Legacy Noise Gate: '{term}'")

    # ── 10. Development Set isolation ──
    dev_set = registry.get("development_set_isolation", {})
    if dev_set.get("counts_toward_pilot_statistics") is not False:
        violations.append("Development Set counts_toward_pilot_statistics must be false")
    if len(dev_set.get("development_set", [])) != 5:
        violations.append(f"Development Set size != 5: {len(dev_set.get('development_set', []))}")

    # ── 11. All schema IDs present ──
    for s in REQUIRED_SCHEMAS:
        schema_path = os.path.join(SCHEMA_DIR, s)
        schema = json.load(open(schema_path, "r", encoding="utf-8"))
        if not schema.get("$id"):
            violations.append(f"{s}: missing $id")

    # ── 12. Pilot calibration configuration ──
    calibration = registry.get("pilot_calibration", {})
    if calibration.get("minimum_consecutive_days") != 14:
        violations.append("Pilot calibration minimum_consecutive_days != 14")
    if calibration.get("minimum_registered_cases") != 8:
        violations.append("Pilot calibration minimum_registered_cases != 8")
    if calibration.get("minimum_event_families") != 3:
        violations.append("Pilot calibration minimum_event_families != 3")

    # ── 13. Git boundary check ──
    if args.check_git_boundary:
        if not args.base:
            violations.append("--check-git-boundary requires --base <commit>")
        else:
            gv = check_git_boundary(args.base)
            violations.extend(gv)

    # ── 14. Instance validators exist and are callable (self-test) ──
    instance_validator_names = [
        "validate_candidate_instance",
        "validate_research_unit_instance",
        "validate_registration_instance",
        "validate_outcome_instance",
        "validate_interference_instance",
        "validate_event_instance_instance",
        "validate_claim_evidence_instance",
        "validate_attribution_instance",
        "validate_research_bundle",
    ]
    module_globals = globals()
    for vname in instance_validator_names:
        if vname not in module_globals:
            violations.append(f"Instance validator '{vname}' not found in module")
        elif not callable(module_globals[vname]):
            violations.append(f"Instance validator '{vname}' is not callable")

    # ── 15. Registry must have sealed_v1_base_commit and phase0_initial_commit fields ──
    if "sealed_v1_base_commit" not in registry:
        violations.append("Registry missing 'sealed_v1_base_commit' field")
    if "phase0_initial_commit" not in registry:
        violations.append("Registry missing 'phase0_initial_commit' field")

    # ── 16. Verify required base commit exists in repository ──
    required_commit = "cfc1e09b9c4e0c734ae4bfc913b726c6e2b145f9"
    if not check_commit_exists(required_commit):
        violations.append(
            f"Git boundary base commit {required_commit} not found in repository"
        )

    if violations:
        print(f"Protocol consistency violations ({len(violations)}):")
        for v in violations:
            print(f"  [FAIL] {v}")
        sys.exit(1)
    else:
        print("[PASS] All protocol consistency checks passed")
        sys.exit(0)


if __name__ == "__main__":
    main()
