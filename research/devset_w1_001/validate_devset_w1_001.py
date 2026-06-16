#!/usr/bin/env python3
"""Validate the w1_001 Development Set case against production validators."""
import json, os, sys

PROJ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(PROJ, "research", "pilot_v1"))
import validate_protocol_consistency as vpc

CASE_DIR = os.path.dirname(os.path.abspath(__file__))
OBJ_DIR = os.path.join(CASE_DIR, "objects")

violations = []

def load_obj(name):
    with open(os.path.join(OBJ_DIR, name), "r", encoding="utf-8") as f:
        return json.load(f)

# ── Load all objects ──
candidate = load_obj("01_candidate.json")["candidate"]
research_unit = load_obj("02_research_unit.json")["research_unit"]
event_instance = load_obj("03_event_instance.json")["event_instance"]
claim_evidence = load_obj("04_claim_evidence_record.json")["claim_evidence_record"]
registration = load_obj("05_registration.json")["registration"]
outcome = load_obj("06_outcome.json")["outcome"]
interference = load_obj("07_interference_record.json")["interference_record"]
attribution = load_obj("08_attribution_assessment.json")["attribution_assessment"]

results = []

# ── Individual validators ──
for name, obj, validator, extra in [
    ("Candidate", candidate, vpc.validate_candidate_instance, None),
    ("Research Unit", research_unit, vpc.validate_research_unit_instance, None),
    ("Event Instance", event_instance, vpc.validate_event_instance_instance, None),
    ("Claim Evidence", claim_evidence, vpc.validate_claim_evidence_instance, None),
    ("Registration", registration, vpc.validate_registration_instance, None),
    ("Outcome", outcome, vpc.validate_outcome_instance, None),
    ("Interference", interference, vpc.validate_interference_instance, None),
    ("Attribution", attribution, vpc.validate_attribution_instance, None),
]:
    v = validator(obj) if extra is None else validator(obj, extra)
    status = "PASS" if len(v) == 0 else f"FAIL ({len(v)} violations)"
    results.append((name, status, v))
    violations.extend(v)

# ── Bundle validators ──
bundle = {
    "candidate": candidate,
    "research_unit": research_unit,
    "registration": registration,
    "outcome": outcome,
    "interference": interference,
    "event_instance": event_instance,
    "claim_evidence": claim_evidence,
    "attribution": attribution,
}

# Development Set has both Registration and Outcome, so lifecycle must be outcome_revealed.
# registered lifecycle (no outcome) is tested separately in unit tests.
v = vpc.validate_research_bundle(bundle, lifecycle_stage="outcome_revealed")
status = "PASS" if len(v) == 0 else f"FAIL ({len(v)} violations)"
results.append(("Bundle (outcome_revealed)", status, v))
violations.extend(v)

# ── Partition isolation ──
for partition in ["calibration", "holdout"]:
    v = vpc.validate_aggregate_membership(bundle, aggregate_partition=partition)
    status = "PASS" if len(v) > 0 else "FAIL (should reject development)"
    results.append((f"Aggregate ({partition})", status, v))

# ── Print results ──
print("=" * 60)
print(f"Validation Report — w1_001")
print("=" * 60)
for name, status, v in results:
    print(f"  [{status}] {name}")
    for vi in v:
        print(f"         {vi}")

print()
if len(violations) == 0:
    print("ALL VALIDATORS PASSED")
    sys.exit(0)
else:
    print(f"{len(violations)} TOTAL VIOLATIONS FOUND")
    sys.exit(1)
