#!/usr/bin/env python3
"""Protocol Consistency Validator for Pilot v1 Phase 0.

Checks internal consistency of protocol documents, schemas, and registry.
Supports --check-git-boundary to verify no sealed files are modified.

Usage:
  python -X utf8 research/pilot_v1/validate_protocol_consistency.py
  python -X utf8 research/pilot_v1/validate_protocol_consistency.py --check-git-boundary --base 0ed9c0e473c6015a5a747317630375b1c8e51a91
"""

import json
import os
import sys
import argparse
import subprocess

PROJ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
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

FORBIDDEN_SCHEMA_PROPERTIES = [
    "abnormal_return", "attribution_score", "confidence_probability",
    "contribution_percentage", "win_rate", "buy_signal", "sell_signal",
    "long_signal", "short_signal", "action_recommendation",
]

ELIGIBILITY_ENUM = {"eligible", "conditionally_eligible", "context_only",
                    "routed_to_other_design", "ineligible", "insufficient_information"}
SEPARABILITY_ENUM = {"isolated", "minor_interference", "conditionally_separable",
                     "cluster_only", "inseparable", "insufficient_inventory"}
IDENTITY_ENUM = {"duplicate_report_of", "update_of", "correction_of", "reversal_of",
                 "follow_up_to", "part_of_thread", "related_not_same", "identity_unresolved"}
DIMENSION_ENUM = {"temporal_ordering", "temporal_proximity", "benchmark_relative_materiality",
                  "asset_specificity", "mechanism_consistency", "interference_and_separability",
                  "alternative_explanations", "robustness"}
VERDICT_ENUM = {"not_assessable", "descriptive_reaction_only", "insufficient_evidence",
                "attribution_compatible", "limited_attribution_support",
                "not_supported_in_registered_window", "cluster_level_association"}
HARD_GATE_ENUM = {"research_eligibility", "event_evidence", "usable_t0",
                  "pre_outcome_registration", "valid_outcome_measurement",
                  "benchmark_validity", "separability"}
HARD_GATE_VERDICT_ENUM = {"pass", "fail", "unknown"}
INFORMATION_FORM_ENUM = {"discrete_information_release", "discrete_observable_action",
                         "state_snapshot", "cumulative_trend",
                         "interpretation_or_narrative", "market_outcome_or_context"}
EVIDENCE_ROLE_ENUM = {"primary_record", "originator_statement", "independent_verification",
                      "carrier_or_relay", "interpretation", "derived_measurement",
                      "anonymous_or_unverified_claim"}
CLAIM_EVIDENCE_STATUS_ENUM = {"directly_verified", "supported", "single_source_supported",
                              "self_reported", "derived", "disputed",
                              "interpretation_only", "insufficient_evidence"}
SELECTED_CLOCK_ENUM = {"action_clock", "information_clock"}
ACTUAL_TIME_BASIS_ENUM = {"occurrence_time", "action_time", "onchain_confirmation_time",
                          "official_publication_time", "first_reliable_public_time",
                          "detection_time", "broadcast_time", "ingestion_time"}


def load_schema(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def check_file_exists(path: str) -> bool:
    return os.path.isfile(path)


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
    reg_only = {"registration_id", "research_unit_ref", "target_asset",
                "selected_clock", "primary_t0", "t0_type", "data_partition",
                "git_commit", "file_sha256", "outcome_status", "primary_benchmark",
                "sensitivity_benchmarks", "pre_event_movement_check_definition"}
    out_props = set(schema.get("properties", {}).keys())
    overlap = reg_only & out_props
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
