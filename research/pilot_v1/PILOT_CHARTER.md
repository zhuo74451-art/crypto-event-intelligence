# Pilot Charter v1

## Phase Identity

This is **Pilot Phase 0** (protocol seal). This numbering is distinct from the historical `NEXT_PHASE_PLAN_V1` which labeled its Phase 0 as "Freeze current raw data baseline." The new Pilot Phase 0 seals the protocol design.

## Authority

This Charter is the authoritative source for Pilot v1 design. It does NOT override or rewrite the sealed V1 historical dataset or its documentation.

## Additive Research Overlay

The Pilot research pipeline is an additive overlay on the existing system. It introduces new concepts (Research Unit, Registration, Outcome) that coexist with the existing Signal Spine pipeline. The overlay does not modify production semantics.

## Research Control Path

The Pilot research pipeline begins at the `Observation / Raw Event` level, NOT at the Legacy Noise Gate output. A Candidate may be eligible for research even if the Legacy Noise Gate would have rejected it, and vice versa.

## Intelligence Gate vs Research Eligibility Gate

These are strictly separate:

- **Intelligence Gate** (Legacy Noise Gate): Decides whether an observation should generate an event card for the existing pipeline.
- **Research Eligibility Gate**: Decides whether a Candidate should become a Research Unit for Pilot purposes. These are independent decisions.

## Data Partition Rules

| Partition | Contents | Pilot Statistics |
|-----------|----------|-----------------|
| Development | Week 1 five samples (w1_001–w1_005) | Excluded |
| Calibration | Future samples for protocol tuning | Separate from holdout |
| Holdout | Prospective evaluation set | Primary Pilot outcome |

## Outcome Status

At Phase 0, Outcome data is NOT computed or revealed. No Registration records contain Outcome data. No Attribution Assessments exist. The `outcome_status` field in Registration MUST be `not_revealed`.

## Pilot Success Criteria

Success is defined by process and evidence completeness, NOT by the presence of positive attribution results. A successful Pilot may show that most events are `insufficient_evidence` or `descriptive_reaction_only`.

## Prohibited Language

- Trading advice (buy/sell/long/short)
- Attribution probabilities or percentages
- Contribution percentages
- Event win rates
- Causal proof claims

## Naming Convention

The historical sealed V1 dataset uses `*_abnormal_return_*`. The new Pilot overlay uses `registered_benchmark_relative_reaction`. Old data is NOT modified. New Overlay data uses the new naming.

## Legacy Noise Gate

The Legacy Noise Gate's production semantics remain unchanged. Shadow audit may compare its outputs against Research Eligibility but must NOT create an automatic feedback loop.
