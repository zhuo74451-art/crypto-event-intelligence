# Phase 0 — Final Protocol Seal

## Baseline References

```
sealed_v1_base_commit:       cfc1e09b9c4e0c734ae4bfc913b726c6e2b145f9
phase0_initial_commit:       0ed9c0e473c6015a5a747317630375b1c8e51a91
validation_parent_commit:    d9f1bda1cc923d825a65665bd3dcd1abd4b9c363
phase0_current_head:         $(git rev-parse HEAD)
```

- `sealed_v1_base_commit` is the original V1 dataset baseline. Phase 0 protocol seal is an additive overlay.
- `phase0_initial_commit` is the initial Phase 0 protocol seal package.
- `validation_parent_commit` was the last state audited by LEFT executor before finalization.
- All git boundary checks are performed from `cfc1e09` (sealed V1 base) to ensure no existing business code was modified.
- Phase 0 went through 7 correction iterations (V1 through V7). All prior intermediate audit reports by LEFT executor refer to `d9f1bda`.

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

## Schema List (8 files, all sealed)

1. `candidate.schema.json`
2. `research_unit.schema.json`
3. `event_instance.schema.json`
4. `claim_evidence_record.schema.json`
5. `registration.schema.json`
6. `outcome.schema.json`
7. `interference_record.schema.json`
8. `attribution_assessment.schema.json`

## Test Collection Audit

| Metric | Value |
|--------|-------|
| Classes | 21 |
| Duplicate class names | 0 |
| Duplicate test method names | 0 |
| Declared test_* methods | 83 |
| pytest collected (focused) | 83 |
| Lost tests | 0 |

## Test Results (Default Windows Encoding)

| Suite | Collected | Passed | Failed | Skipped |
|-------|-----------|--------|--------|---------|
| Focused protocol seal tests | 83 | 83 | 0 | 0 |
| Full test suite | 316 | 316 | 0 | 0 |

## Test Results (UTF-8 Mode)

Same as above — 83/83 focused, 316/316 full. No encoding dependency. All `open()` calls explicit `encoding="utf-8"`.

## Protocol Consistency Validator Checks

| Check | Count |
|-------|-------|
| Schema structural checks | 25 |
| Instance validation functions | 9 |
| Semantic schema validators | 7 |
| Git boundary scopes | 4 |
| **Total checks** | **30+** |

## Negative Semantic Cases

25+ negative cases, each calling a production validator function and asserting:
- violations list is non-empty
- expected error text is present

All negative tests use production `validate_protocol_consistency.py` functions — no duplicated logic.

## Instance Validators (9 functions)

1. `validate_candidate_instance(candidate)` — shape + routing + exclusion
2. `validate_research_unit_instance(ru, candidate=None)` — shape + design + form routing
3. `validate_registration_instance(registration)` — shape + self-benchmark + clock + outcome spill
4. `validate_outcome_instance(outcome, registration=None)` — shape + cross-ref
5. `validate_interference_instance(interference)` — shape + coverage/separability
6. `validate_event_instance_instance(event_instance)` — shape + identity + versioning
7. `validate_claim_evidence_instance(record)` — shape + evidence roles + independence
8. `validate_attribution_instance(assessment, interference=None)` — shape + hard gates + forbidden terms
9. `validate_research_bundle(bundle, lifecycle_stage)` — lifecycle stages + partition isolation + bundle consistency

All instance validators call `_schema_lint()` which loads the corresponding JSON Schema and runs shape validation (required fields, additionalProperties=false, type checks, enum checks, nested object validation) using a standard-library schema-lite engine. No jsonschema dependency.

## Schema-Lite Shape Validator

`validate_instance_against_schema_shape(instance, schema, path)` supports:
- object.properties + object.required + additionalProperties=false
- array.items
- enum
- type (object/array/string/integer/number/boolean)
- Nested objects and arrays
- Bool/integer distinction (`_get_json_type`)

## t0_type Resolution

`frozen_enums.t0_type` was removed from active enums and moved to `legacy_compatibility`:
- `status: "not_active_in_pilot_v1"`
- `superseded_by: "selected_clock + actual_time_basis"`
- `must_not_be_serialized_into_new_registration: true`

## Git Boundary

Checked from `cfc1e09b9c4e0c734ae4bfc913b726c6e2b145f9` across all 4 scopes:
- base..HEAD committed diff
- staged
- unstaged
- untracked

**Result:** PASS — only `research/pilot_v1/**` and `tests/test_pilot_v1_protocol_seal.py` modified.

## Sealed V1 Files Touched

**false** — no existing business code files modified. Verified via `git diff --name-only cfc1e09...HEAD`.

## Business Code Touched

**false** — `market_radar/shared/**` not touched.

## Development Set Conversion Started

**false** — Week 1 samples remain as-is; no Candidate Log or Research Unit instances created.

## Real Pilot Started

**false** — Phase 0 only seals protocol documents and schemas. No Pilot execution has begun.

## CI Status

Test execution is executor-reported and repository-audited; no GitHub Actions run exists.

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
