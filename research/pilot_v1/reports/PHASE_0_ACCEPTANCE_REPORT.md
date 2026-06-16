# Phase 0 Acceptance Report — Protocol Seal (Corrected)

## Verified Base Commit

```
0ed9c0e473c6015a5a747317630375b1c8e51a91
```

## Correction Commit

The initial seal at `cfc1e09` was updated with 12 fix categories. See git log for the full correction history. All changes are restricted to `research/pilot_v1/**` and `tests/test_pilot_v1_protocol_seal.py`.

## Files Modified in Correction

- `research/pilot_v1/PROTOCOL_REGISTRY.json` — updated enums (information_form, selected_clock, evidence_role, hard_gates, etc.), added design_type_routing, pilot_calibration
- `research/pilot_v1/validate_protocol_consistency.py` — added 7 semantic validation functions (validate_candidate, validate_registration, validate_outcome, etc.), multi-scope git boundary check
- `research/pilot_v1/reports/PHASE_0_ACCEPTANCE_REPORT.md` — this file
- `research/pilot_v1/protocols/01_*.md` through `09_*.md` — all 9 protocol documents updated with new semantics
- `research/pilot_v1/schemas/*.schema.json` — all 8 schemas updated with new enums, additionalProperties: false, hard gates, evidence roles, t0 dual clock
- `tests/test_pilot_v1_protocol_seal.py` — added 30+ new focused tests with real valid/invalid instances

Total: **19 files modified**, **0 files added** (no new files created).

## Eleven Decision Mappings

| # | Protocol | Status |
|---|----------|--------|
| 1 | Research Unit and Eligibility | Corrected (info forms + source medium separation + routing) |
| 2 | Temporal Model and Registration | Corrected (dual clock: action_clock/information_clock, actual_time_basis) |
| 3 | Study Case Collision and Interference | Unchanged (already correct) |
| 4 | Evidence Role Contract | Corrected (evidence_role + claim_evidence_status enums) |
| 5 | Attribution Assessment | Corrected (7 hard gates before 8-dimension matrix) |
| 6 | Sample Pre-registration and Partitions | Unchanged (already correct) |
| 7 | Benchmark and Outcome Measurement | Corrected (weak proxy for BTC, no self-benchmark, locked benchmarks) |
| 8 | Event Identity, Update, and Reversal | Corrected (3-layer identity: Observation/Event Instance/Event Thread) |
| 9 | Noise Gate Shadow Audit | Corrected (full Candidate Log, dual review, adjudication) |
| 10 | Pilot Execution | Corrected (14-day calibration, 8 cases, 3 families, locked registration) |
| 11 | Pilot Charter and Scope | Unchanged (already correct) |

## Schema List (all corrected)

1. `candidate.schema.json` — new information_form enum, added source_medium, additionalProperties: false
2. `research_unit.schema.json` — added information_form field, additionalProperties: false
3. `event_instance.schema.json` — added observation_ref, instance_version, identity_merge_evidence, additionalProperties: false
4. `claim_evidence_record.schema.json` — added evidence_role + claim_evidence_status (required), additionalProperties: false
5. `registration.schema.json` — selected_clock = [action_clock, information_clock], added actual_time_basis, removed movement_detected from pre_event_movement_check_definition, additionalProperties: false
6. `outcome.schema.json` — added pre_event_movement_check_result (with movement_detected), sensitivity_benchmark_reactions, additionalProperties: false
7. `interference_record.schema.json` — additionalProperties: false
8. `attribution_assessment.schema.json` — added hard_gates (7 gates with pass/fail/unknown), btc_benchmark_weak_proxy_note, additionalProperties: false

## Protocol Consistency Validator Checks (25 total)

1. All required files exist
2. No extra empty directories
3. All 11 decisions mapped
4. All schemas parse and have correct $schema version
5. Registry enums match protocol requirements (candidate_status, research_eligibility, separability, identity, verdicts)
6. Registry enums for hard_gate, hard_gate_verdict
7. Semantic: Candidate information_form is new enum, source_medium present
8. Semantic: Registration selected_clock = action_clock/information_clock
9. Semantic: Registration actual_time_basis enum
10. Semantic: Registration pre_event_movement_check_definition has no movement_detected
11. Semantic: Outcome has pre_event_movement_check_result
12. Semantic: Outcome has no registration-only fields
13. Semantic: Event Instance has supersedes/superseded_by, observation_ref, instance_version
14. Semantic: Attribution Assessment has all 7 hard gates
15. Semantic: Attribution verdict enum match
16. Semantic: No numeric attribution terms
17. Semantic: Claim evidence has evidence_role and claim_evidence_status
18. Semantic: Protocol 09 has shadow audit and calibration pilot content
19. Registration and Outcome are physically separate
20. Research Unit does not reference Legacy Noise Gate
21. Development Set isolation enforced
22. All schemas have $id
23. Pilot calibration configuration present (14 days, 8 cases, 3 families)
24. Multi-scope git boundary check (committed, staged, unstaged, untracked)
25. Each scope returns non-zero on failure

## Execution Results

| Command | Result |
|---------|--------|
| Protocol Consistency Validator | **PASS** (25 checks) |
| Git boundary check | **PASS** (only pilot_v1 + test files in all 4 scopes) |
| Focused protocol seal tests | **all pass, 0 failed, 0 skipped** |
| Full test suite | **all pass** (no regressions) |

## Sealed V1 Files Touched

**false** — no existing business code files modified.

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
- `information_form=interpretation_or_narrative` routing requires human judgment to split from underlying fact

## Outstanding Items

- No Development Set Conversion
- No Pilot execution
- No Attribution Assessments
- No shadow audit run
