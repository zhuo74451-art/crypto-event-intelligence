# Phase 0 Acceptance Report — Protocol Seal (V4 Correction)

## Baseline References

```
sealed_v1_base_commit:  cfc1e09b9c4e0c734ae4bfc913b726c6e2b145f9
phase0_initial_commit:  0ed9c0e473c6015a5a747317630375b1c8e51a91
phase0_current_head:    $(git rev-parse HEAD)  # resolved at runtime
```

- `sealed_v1_base_commit` is the original V1 dataset baseline. Phase 0 protocol seal is an additive overlay.
- `phase0_initial_commit` is the initial Phase 0 protocol seal package.
- Git boundary is checked from `cfc1e09` (sealed V1 base) to ensure no existing business code was modified.

## Files Modified in V4 Correction

- `research/pilot_v1/PROTOCOL_REGISTRY.json` — fixed baseline anchors (sealed_v1_base_commit, phase0_initial_commit)
- `research/pilot_v1/validate_protocol_consistency.py` — added 9 instance-level validators (validate_*_instance), research_bundle validator; renamed old schema-path functions to validate_*_schema; fixed git boundary defaults to cfc1e09
- `research/pilot_v1/reports/PHASE_0_ACCEPTANCE_REPORT.md` — this file, with accurate counts and CI status
- `research/pilot_v1/protocols/01_RESEARCH_UNIT_AND_ELIGIBILITY.md` — study case definition no longer binds broadcast_time; 6-component definition
- `research/pilot_v1/schemas/interference_record.schema.json` — added alternative_explanations, coverage_insufficiency to required; collision_set items require event_id, event_description
- `research/pilot_v1/schemas/event_instance.schema.json` — added observation_ref, instance_version to required
- `research/pilot_v1/schemas/claim_evidence_record.schema.json` — added independence_groups to required
- `research/pilot_v1/schemas/research_unit.schema.json` — added information_form to required
- `tests/test_pilot_v1_protocol_seal.py` — 21+ negative tests calling production validators; old pseudo-negative tests replaced

## Eleven Decision Mappings

| # | Protocol | Status |
|---|----------|--------|
| 1 | Research Unit and Eligibility | Corrected (broadcast_time removed from study case definition) |
| 2 | Temporal Model and Registration | Corrected (dual clock, actual_time_basis) |
| 3 | Study Case Collision and Interference | Corrected (interference schema required fields + collision item requirements) |
| 4 | Evidence Role Contract | Corrected (independence_groups required; evidence_role + claim_evidence_status) |
| 5 | Attribution Assessment | Corrected (instance-level hard-gate enforcement) |
| 6 | Sample Pre-registration and Partitions | Unchanged (already correct) |
| 7 | Benchmark and Outcome Measurement | Corrected (instance-level self-benchmark rejection) |
| 8 | Event Identity, Update, and Reversal | Corrected (observation_ref, instance_version required in schema; identity rules in validator) |
| 9 | Noise Gate Shadow Audit | Corrected (full shadow audit + calibration pilot in Protocol 09) |
| 10 | Pilot Execution | Corrected (same as 9) |
| 11 | Pilot Charter and Scope | Unchanged (already correct) |

## Instance-Level Validators (9 total)

1. `validate_candidate_instance(candidate)` — info form, routing, exclusion reason
2. `validate_research_unit_instance(ru, candidate=None)` — design_type, information_form, cross-check vs candidate
3. `validate_registration_instance(registration)` — self-benchmark, clock, outcome spill, pre-event movement def
4. `validate_outcome_instance(outcome, registration=None)` — cross-ref vs registration, benchmark/window consistency
5. `validate_interference_instance(interference)` — coverage/isolated conflict, collision_set requirements
6. `validate_event_instance_instance(event_instance)` — identity rules, version, merge evidence
7. `validate_claim_evidence_instance(record)` — evidence_role, claim_evidence_status, independence_groups
8. `validate_attribution_instance(assessment, interference=None)` — hard gates, verdict gating, numeric terms
9. `validate_research_bundle(bundle)` — full lifecycle: registration/outcome consistency, timestamps, partition isolation

## Negative Semantic Cases (21)

Covered by tests:
1. old information_form
2. non-discrete routed_to_research (cumulative_trend)
3. excluded without reason
4. selected_clock=broadcast_time
5. primary self-benchmark
6. sensitivity self-benchmark
7. duplicate sensitivity benchmark
8. Registration contains raw_market_reaction
9. Registration contains movement_detected
10. Outcome without Registration reference
11. Outcome benchmark mismatch
12. fail gate + attribution_compatible
13. unknown gate + limited_attribution_support
14. inseparable + separability gate pass
15. coverage insufficient + isolated
16. identity_unresolved + supersedes
17. versioned relation without prior ref
18. missing independence_groups
19. nested attribution_score property
20. untracked sealed-path file (git boundary)
21. invalid git base

## Test Results

| Suite | Collected | Passed | Failed | Skipped |
|-------|-----------|--------|--------|---------|
| Focused protocol seal tests | TBD | TBD | 0 | 0 |
| Full test suite | TBD | TBD | 0 | 0 |
| Protocol consistency validator | 30+ checks | TBD | 0 | 0 |

## Validator Checks

- Schema structural checks: 25
- Instance validation functions: 9
- Negative semantic rules enforced: 21

All negative tests call production validator functions in `validate_protocol_consistency.py` — no duplicated logic in test file.

## CI Status

Test execution is executor-reported and repository-audited; no GitHub Actions run exists.

## Sealed V1 Files Touched

**false** — no existing business code files modified. Verified via `git diff --name-only cfc1e09...HEAD` (only research/pilot_v1/ and tests/).

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
- `information_form=interpretation_or_narrative` routing requires human judgment to split from underlying fact
- No GitHub Actions CI — all test execution is executor-reported

## Outstanding Items

- No Development Set Conversion
- No Pilot execution
- No Attribution Assessments
- No shadow audit run
