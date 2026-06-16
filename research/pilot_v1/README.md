# Pilot v1 — Protocol Seal Package

## 11 Decision Mapping

| # | Decision | Protocol |
|---|----------|----------|
| 1 | Research Unit composition and eligibility criteria | [01](protocols/01_RESEARCH_UNIT_AND_ELIGIBILITY.md) |
| 2 | Temporal model, t0 policy, and pre-registration requirements | [02](protocols/02_TEMPORAL_MODEL_AND_REGISTRATION.md) |
| 3 | Study case collision, interference, and separability | [03](protocols/03_STUDY_CASE_COLLISION_AND_INTERFERENCE.md) |
| 4 | Evidence role contract (claim, artifact, provenance, independence) | [04](protocols/04_EVIDENCE_ROLE_CONTRACT.md) |
| 5 | Attribution assessment dimensions and verdicts | [05](protocols/05_ATTRIBUTION_ASSESSMENT.md) |
| 6 | Sample pre-registration, partitions, and Development Set isolation | [06](protocols/06_SAMPLE_PREREGISTRATION_AND_PARTITIONS.md) |
| 7 | Benchmark and outcome measurement (separate from Registration) | [07](protocols/07_BENCHMARK_AND_OUTCOME_MEASUREMENT.md) |
| 8 | Event identity, versioning, update, and reversal model | [08](protocols/08_EVENT_IDENTITY_UPDATE_AND_REVERSAL.md) |
| 9 | Legacy Noise Gate shadow audit (observational only) | [09](protocols/09_NOISE_GATE_SHADOW_AUDIT_AND_PILOT_EXECUTION.md) |
| 10 | Pilot execution sequencing and prohibitions | [09](protocols/09_NOISE_GATE_SHADOW_AUDIT_AND_PILOT_EXECUTION.md) |
| 11 | Pilot scope, non-goals, and additive overlay design | [PILOT_CHARTER.md](PILOT_CHARTER.md) |

## Files

| File | Purpose |
|------|---------|
| `PILOT_CHARTER.md` | Charter, scope, non-goals, and overlay design (Decision 11) |
| `PROTOCOL_REGISTRY.json` | Machine-readable term registry with all frozen enums |
| `validate_protocol_consistency.py` | Protocol Consistency Validator |
| `reports/PHASE_0_ACCEPTANCE_REPORT.md` | Phase 0 acceptance report |
| `protocols/01_*.md` through `09_*.md` | 9 protocol documents (Decisions 1–10) |
| `schemas/*.schema.json` | 8 JSON Schema Draft 2020-12 objects |

## Status

Phase 0: Protocol Seal — Complete. No Development Set conversion. No Pilot execution started.
