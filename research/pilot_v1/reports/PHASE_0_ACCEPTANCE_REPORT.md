# Phase 0 Acceptance Report — Protocol Seal

## Verified Base Commit

```
cfc1e09b9c4e0c734ae4bfc913b726c6e2b145f9
```

## New Files Created

- `research/pilot_v1/README.md`
- `research/pilot_v1/PILOT_CHARTER.md`
- `research/pilot_v1/PROTOCOL_REGISTRY.json`
- `research/pilot_v1/validate_protocol_consistency.py`
- `research/pilot_v1/reports/PHASE_0_ACCEPTANCE_REPORT.md`
- `research/pilot_v1/protocols/01_RESEARCH_UNIT_AND_ELIGIBILITY.md`
- `research/pilot_v1/protocols/02_TEMPORAL_MODEL_AND_REGISTRATION.md`
- `research/pilot_v1/protocols/03_STUDY_CASE_COLLISION_AND_INTERFERENCE.md`
- `research/pilot_v1/protocols/04_EVIDENCE_ROLE_CONTRACT.md`
- `research/pilot_v1/protocols/05_ATTRIBUTION_ASSESSMENT.md`
- `research/pilot_v1/protocols/06_SAMPLE_PREREGISTRATION_AND_PARTITIONS.md`
- `research/pilot_v1/protocols/07_BENCHMARK_AND_OUTCOME_MEASUREMENT.md`
- `research/pilot_v1/protocols/08_EVENT_IDENTITY_UPDATE_AND_REVERSAL.md`
- `research/pilot_v1/protocols/09_NOISE_GATE_SHADOW_AUDIT_AND_PILOT_EXECUTION.md`
- `research/pilot_v1/schemas/candidate.schema.json`
- `research/pilot_v1/schemas/research_unit.schema.json`
- `research/pilot_v1/schemas/event_instance.schema.json`
- `research/pilot_v1/schemas/claim_evidence_record.schema.json`
- `research/pilot_v1/schemas/registration.schema.json`
- `research/pilot_v1/schemas/outcome.schema.json`
- `research/pilot_v1/schemas/interference_record.schema.json`
- `research/pilot_v1/schemas/attribution_assessment.schema.json`
- `tests/test_pilot_v1_protocol_seal.py`

Total: **24 new files**.

## Eleven Decision Mappings

| # | Protocol | Status |
|---|----------|--------|
| 1 | Research Unit and Eligibility | Sealed |
| 2 | Temporal Model and Registration | Sealed |
| 3 | Study Case Collision and Interference | Sealed |
| 4 | Evidence Role Contract | Sealed |
| 5 | Attribution Assessment | Sealed |
| 6 | Sample Pre-registration and Partitions | Sealed |
| 7 | Benchmark and Outcome Measurement | Sealed |
| 8 | Event Identity, Update, and Reversal | Sealed |
| 9 | Noise Gate Shadow Audit | Sealed |
| 10 | Pilot Execution | Sealed |
| 11 | Pilot Charter and Scope | Sealed |

## Schema List

1. `candidate.schema.json`
2. `research_unit.schema.json`
3. `event_instance.schema.json`
4. `claim_evidence_record.schema.json`
5. `registration.schema.json`
6. `outcome.schema.json`
7. `interference_record.schema.json`
8. `attribution_assessment.schema.json`

## Protocol Consistency Validator Checks

1. All required files exist
2. No extra empty directories
3. All 11 decisions mapped
4. All schemas parse and have correct $schema version
5. Registry enums match protocol requirements (candidate_status, research_eligibility, separability, identity, verdicts)
6. Registration and Outcome are physically separate
7. Research Unit does not reference Legacy Noise Gate
8. Development Set isolation enforced
9. Attribution Assessment has all 8 dimensions and correct verdicts
10. Self-benchmark rejection logic in Registration schema
11. No numeric attribution scores in assessment schema
12. Reversible identity merge fields present
13. All schemas have $id
14. Git boundary check (optional)

## Execution Results

| Command | Result |
|---------|--------|
| Protocol Consistency Validator | PASS |
| Git boundary check | PASS (only pilot_v1 + test files) |
| Focused protocol seal tests | All pass |
| Full test suite | 233 passed |
| Manifest validator | PASS |
| Price dataset validator | PASS |
| Dataset validator | PASS |
| Documentation validator | PASS |

## Sealed V1 Files Touched

**false** — no existing files modified.

## Business Code Touched

**false** — `market_radar/shared/**` not touched.

## Development Set Conversion Started

**false** — Week 1 samples remain as-is; no Candidate Log or Research Unit instances created.

## Real Pilot Started

**false** — Phase 0 only seals protocol documents and schemas. No Pilot execution has begun.

## Known Limitations

- Protocol has not been tested against real data beyond the Development Set
- Registration and Outcome schemas are designed but not instantiated
- Shadow audit infrastructure not yet built
- Attribution Assessment has not been calibrated against any sample
- Edge cases in event identity merge (e.g., cycles) not fully explored
- Protocol consistency validator covers structural checks but not semantic correctness of the research methodology

## Outstanding Items

- No Development Set Conversion
- No Pilot execution
- No Attribution Assessments
- No shadow audit run
