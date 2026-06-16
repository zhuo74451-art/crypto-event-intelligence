#!/usr/bin/env python3
"""Protocol Consistency Validator for Pilot v1 Phase 0.

Checks internal consistency of protocol documents, schemas, and registry.
Supports --check-git-boundary to verify no sealed files are modified.

Usage:
  python -X utf8 research/pilot_v1/validate_protocol_consistency.py
  python -X utf8 research/pilot_v1/validate_protocol_consistency.py --check-git-boundary --base cfc1e09b9c4e0c734ae4bfc913b726c6e2b145f9
"""

import json
import os
import sys
import argparse

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

# Expected enum values from frozen protocol
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


def load_schema(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def check_file_exists(path: str) -> bool:
    return os.path.isfile(path)


def check_git_boundary(base_commit: str) -> list[str]:
    """Check git boundary: only research/pilot_v1/** and test file are allowed."""
    violations = []
    try:
        import subprocess
        # Check for any diff outside allowed paths
        cmd = ["git", "diff", "--name-only", base_commit]
        result = subprocess.run(cmd, cwd=PROJ, capture_output=True, text=True)
        for line in result.stdout.strip().split("\n"):
            if not line:
                continue
            if not (line.startswith("research/pilot_v1/") or line == "tests/test_pilot_v1_protocol_seal.py"):
                violations.append(f"File outside allowed paths modified: {line}")
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
    """Check schema property names only (not descriptions) for forbidden terms."""
    violations = []
    props = schema.get("properties", {})
    for prop in forbidden:
        if prop in props:
            violations.append(f"Forbidden property '{prop}' found in {path}")
    return violations


def main():
    parser = argparse.ArgumentParser(description="Protocol Consistency Validator v1")
    parser.add_argument("--check-git-boundary", action="store_true",
                        help="Check git boundary: only allowed paths modified")
    parser.add_argument("--base", type=str, default=None,
                        help="Base commit for git boundary check")
    args = parser.parse_args()

    violations = []

    # 1. Required files exist
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

    # 2. No extra empty directories
    for dirpath, dirnames, filenames in os.walk(PILOT_DIR):
        if dirpath == PILOT_DIR:
            # Root should have proper files
            pass
        rel = os.path.relpath(dirpath, PILOT_DIR)
        if rel in ("protocols", "schemas", "reports"):
            continue
        if rel.startswith("."):
            continue
        if filenames:
            violations.append(f"Unexpected file in pilot_v1: {rel}/{filenames[0]}")

    # 3. Load registry
    registry_path = os.path.join(PILOT_DIR, "PROTOCOL_REGISTRY.json")
    registry = json.load(open(registry_path, "r", encoding="utf-8"))
    reg_enums = registry.get("frozen_enums", {})

    # 4. All 11 decisions mapped
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

    # 5. All schemas parse and have correct $schema
    for s in REQUIRED_SCHEMAS:
        schema_path = os.path.join(SCHEMA_DIR, s)
        try:
            schema = json.load(open(schema_path, "r", encoding="utf-8"))
            if schema.get("$schema") != "https://json-schema.org/draft/2020-12/schema":
                violations.append(f"{s}: $schema is not draft 2020-12")
            # Check forbidden properties
            v = check_schema_forbidden_props(schema, FORBIDDEN_SCHEMA_PROPERTIES, s)
            violations.extend(v)
        except (json.JSONDecodeError, IOError) as e:
            violations.append(f"{s}: cannot parse: {e}")

    # 6. Registry enums vs schema enums consistency (spot-check key enums)
    candidate_status = set(reg_enums.get("candidate_status", []))
    expected_candidate_status = {"pending", "routed_to_research", "routed_to_other_design",
                                  "excluded", "insufficient_information"}
    v = validate_registry_enum(candidate_status, expected_candidate_status, "candidate_status")
    violations.extend(v)

    research_elig = set(reg_enums.get("research_eligibility", []))
    v = validate_registry_enum(research_elig, ELIGIBILITY_ENUM, "research_eligibility")
    violations.extend(v)

    separability = set(reg_enums.get("separability_status", []))
    v = validate_registry_enum(separability, SEPARABILITY_ENUM, "separability_status")
    violations.extend(v)

    identity_rel = set(reg_enums.get("identity_relationship", []))
    v = validate_registry_enum(identity_rel, IDENTITY_ENUM, "identity_relationship")
    violations.extend(v)

    verdicts = set(reg_enums.get("attribution_verdict", []))
    v = validate_registry_enum(verdicts, VERDICT_ENUM, "attribution_verdict")
    violations.extend(v)

    # 7. Check Registration and Outcome are separate files
    reg_schema = load_schema(os.path.join(SCHEMA_DIR, "registration.schema.json"))
    out_schema = load_schema(os.path.join(SCHEMA_DIR, "outcome.schema.json"))
    reg_required = set(reg_schema.get("required", []))
    out_required = set(out_schema.get("required", []))
    # Registration must have outcome_status=not_revealed
    if "outcome_status" not in reg_required:
        violations.append("Registration missing 'outcome_status' in required fields")
    # Outcome must have registration_ref (not inline)
    if "registration_ref" not in out_required:
        violations.append("Outcome missing 'registration_ref' in required fields")
    # No overlap of Registration-only fields in Outcome
    reg_only_fields = {"registration_id", "research_unit_ref", "target_asset",
                        "selected_clock", "primary_t0", "t0_type", "data_partition",
                        "outcome_status", "git_commit", "file_sha256"}
    out_props = set(out_schema.get("properties", {}).keys())
    overlap = reg_only_fields & out_props
    if overlap:
        violations.append(f"Outcome shares Registration-specific fields: {overlap}")

    # 8. Research Unit does not reference Legacy Noise Gate
    ru_schema = load_schema(os.path.join(SCHEMA_DIR, "research_unit.schema.json"))
    ru_text = json.dumps(ru_schema)
    for term in ["noise_gate", "noise_gate_result", "legacy_noise_gate_pass", "legacy_noise_gate_reject"]:
        if term in ru_text.lower():
            violations.append(f"Research Unit schema references Legacy Noise Gate: '{term}'")

    # 9. Development Set isolation
    dev_set = registry.get("development_set_isolation", {})
    if dev_set.get("counts_toward_pilot_statistics") is not False:
        violations.append("Development Set counts_toward_pilot_statistics must be false")
    if len(dev_set.get("development_set", [])) != 5:
        violations.append(f"Development Set size != 5: {len(dev_set.get('development_set', []))}")

    # 10. Attribution Assessment schema checks
    aa_schema = load_schema(os.path.join(SCHEMA_DIR, "attribution_assessment.schema.json"))
    aa_dims = aa_schema.get("properties", {}).get("dimensions", {}).get("properties", {})
    aa_dim_names = set(aa_dims.keys())
    if aa_dim_names != DIMENSION_ENUM:
        missing_dims = DIMENSION_ENUM - aa_dim_names
        extra_dims = aa_dim_names - DIMENSION_ENUM
        if missing_dims:
            violations.append(f"Attribution missing dimensions: {missing_dims}")
        if extra_dims:
            violations.append(f"Attribution extra dimensions: {extra_dims}")

    aa_verdicts = aa_schema.get("properties", {}).get("verdict", {}).get("enum", [])
    if set(aa_verdicts) != VERDICT_ENUM:
        violations.append("Attribution verdict enum mismatch")

    # 11. self-benchmark rejection check in registration schema
    reg_text = json.dumps(reg_schema)
    if "self_benchmark" not in reg_text.lower() and "${primary_benchmark}" not in reg_text:
        violations.append("Registration schema missing self-benchmark rejection logic")

    # 12. No numeric attribution scores in AA schema property names
    aa_props = set(aa_schema.get("properties", {}).keys())
    for term in ["score", "probability", "percentage", "contribution", "win_rate"]:
        if any(term in p for p in aa_props):
            violations.append(f"Attribution assessment property contains numeric term: '{term}'")

    # 13. Irreversible identity merge check
    ei_schema = load_schema(os.path.join(SCHEMA_DIR, "event_instance.schema.json"))
    ei_props = ei_schema.get("properties", {})
    if "supersedes" not in ei_props:
        violations.append("Event instance missing 'supersedes' field (reversibility)")
    if "superseded_by" not in ei_props:
        violations.append("Event instance missing 'superseded_by' field (reversibility)")

    # 14. Check all schema IDs are present
    for s in REQUIRED_SCHEMAS:
        schema_path = os.path.join(SCHEMA_DIR, s)
        schema = json.load(open(schema_path, "r", encoding="utf-8"))
        if not schema.get("$id"):
            violations.append(f"{s}: missing $id")

    # Git boundary check
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
