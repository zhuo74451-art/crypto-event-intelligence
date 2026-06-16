# Validation Report — w1_001

## Object Validator Results

| Object | File | Validator | Violations | Status |
|--------|------|-----------|------------|--------|
| Candidate | `01_candidate.json` | `validate_candidate_instance` | 0 | ✅ PASS |
| Research Unit | `02_research_unit.json` | `validate_research_unit_instance` | 0 | ✅ PASS |
| Event Instance | `03_event_instance.json` | `validate_event_instance_instance` | 0 | ✅ PASS |
| Claim-Evidence Record | `04_claim_evidence_record.json` | `validate_claim_evidence_instance` | 0 | ✅ PASS |
| Registration | `05_registration.json` | `validate_registration_instance` | 0 | ✅ PASS |
| Outcome | `06_outcome.json` | `validate_outcome_instance` | 0 | ✅ PASS |
| Interference Record | `07_interference_record.json` | `validate_interference_instance` | 0 | ✅ PASS |
| Attribution Assessment | `08_attribution_assessment.json` | `validate_attribution_instance` | 0 | ✅ PASS |

## Bundle Lifecycle Validation

| Lifecycle Stage | Expected | Actual | Status |
|-----------------|----------|--------|--------|
| `registered` | 0 violations | — | ✅ PASS |
| `outcome_revealed` | 0 violations | — | ✅ PASS |

## Partition Isolation

| Aggregate | Expected | Status |
|-----------|----------|--------|
| Calibration | Rejected (development) | ✅ |
| Holdout | Rejected (development) | ✅ |

## Bundle Consistency

| Check | Status |
|-------|--------|
| Unique IDs across all objects | ✅ |
| Reference chain: candidate→ru→registration→outcome | ✅ |
| Event instance→observation↔candidate ref | ✅ |
| Registration git_commit matches protocol commit | ✅ |
| Registration file_sha256 present | ✅ |
| Outcome benchmark matches registration primary_benchmark | ✅ |
| Outcome registration_ref matches registration_id | ✅ |
| Attribution research_unit_ref matches ru_id | ✅ |
| Interference research_unit_ref matches ru_id | ✅ |
