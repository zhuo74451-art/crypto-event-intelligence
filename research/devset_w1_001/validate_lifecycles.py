#!/usr/bin/env python3
"""Separate lifecycle validation for registered and outcome_revealed stages."""
import json, os, sys

PROJ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(PROJ, "research", "pilot_v1"))
import validate_protocol_consistency as vpc

CASE_DIR = os.path.dirname(os.path.abspath(__file__))
OBJ_DIR = os.path.join(CASE_DIR, "objects")

def load_obj(name):
    with open(os.path.join(OBJ_DIR, name), "r", encoding="utf-8") as f:
        return json.load(f)

# Load all objects
candidate = load_obj("01_candidate.json")["candidate"]
research_unit = load_obj("02_research_unit.json")["research_unit"]
event_instance = load_obj("03_event_instance.json")["event_instance"]
claim_evidence = load_obj("04_claim_evidence_record.json")["claim_evidence_record"]
registration = load_obj("05_registration.json")["registration"]
outcome = load_obj("06_outcome.json")["outcome"]
interference = load_obj("07_interference_record.json")["interference_record"]
attribution = load_obj("08_attribution_assessment.json")["attribution_assessment"]

# Registered-stage bundle (no Outcome, no Attribution)
registered_bundle = {
    "candidate": candidate,
    "research_unit": research_unit,
    "registration": registration,
    "interference": interference,
    "event_instance": event_instance,
    "claim_evidence": claim_evidence,
}

full_bundle = {
    "candidate": candidate,
    "research_unit": research_unit,
    "registration": registration,
    "outcome": outcome,
    "interference": interference,
    "event_instance": event_instance,
    "claim_evidence": claim_evidence,
    "attribution": attribution,
}

all_pass = True

# Registered lifecycle
v = vpc.validate_research_bundle(registered_bundle, lifecycle_stage="registered")
status = "PASS (0 violations)" if len(v) == 0 else f"FAIL ({len(v)} violations)"
if len(v) > 0:
    all_pass = False
print(f"[{status}] Registered-stage bundle (no Outcome)")
for vi in v:
    print(f"       {vi}")

# Outcome-revealed lifecycle (with Attribution)
v2 = vpc.validate_research_bundle(full_bundle, lifecycle_stage="outcome_revealed")
status2 = "PASS (0 violations)" if len(v2) == 0 else f"FAIL ({len(v2)} violations)"
if len(v2) > 0:
    all_pass = False
print(f"[{status2}] Outcome-revealed bundle")
for vi in v2:
    print(f"       {vi}")

sys.exit(0 if all_pass else 1)
