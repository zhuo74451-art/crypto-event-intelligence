# Design Decisions V1

## Why Not a Universal Total Score

Many intelligence systems reduce multi-dimensional evidence to a single score (e.g., "78/100 bullish"). This loses:

- Which dimensions are missing or conflicting
- The time horizon of the assessment
- The calibration quality of the confidence
- The alternative explanations

V1 deliberately avoids any universal score formula. Each dimension (evidence, regime, expectation gap, strategy, arbitration) produces structured output independently. Aggregation is explicit and preserves conflicts.

## Why Not Personality Voting

Strategy instances are not personas. Arbitration does not count votes. Multiple strategies from the same origin (same trader, same paper, same upstream profile) are considered related — they do not provide independent confirmation. Arbitration rules check correlation, evidence independence, and calibration quality, not popularity.

## Why Calibration Requires an Artifact

A confidence statement without calibration evidence is indistinguishable from guessing. V1 enforces:

- `calibrated_probability` requires a `CalibrationArtifactRef` with method, validation period, sample size, out-of-sample flag, and metric summary.
- Without these, the system cannot output calibrated probabilities.
- `uncalibrated_score` is allowed but must be marked `production_probability: false`.
- `qualitative` confidence (low/medium/high) is allowed for early-stage hypotheses but must state its basis.

## Why Multi-Time-Scale Assessments Are Separate

Short-term bullish and medium-term bearish are not contradictions — they are different judgments across different horizons. V1's Market Assessment Builder produces one assessment per time horizon, each with its own direction, evidence, confidence, and invalidation conditions. This prevents false consolidation.

## Why Revision Does Not Overwrite History

Event revisions are append-only transitions. When an event is revised (e.g., a correction is published), the system records the revision as a new transition with the time it was first seen. Later queries for `as_of_time` can reconstruct what was known at any point. Revisions never modify past state entries.

## Why Core Does Not Do I/O

- `contracts/` and `engines/` explicitly forbid network requests, file writes, environment reads, database connections, global state, implicit time, random ID generation, and LLM calls.
- All time and ID dependencies are injected via explicit parameters.
- This keeps the core testable, deterministic, and serializable.

## Choice of Data Modeling Approach

Decision: Use standard library `dataclasses` + `Enum` + `Decimal` + explicit validators.

Rationale:
- The existing codebase (`market_radar/shared/models.py`) uses `dataclasses` extensively, not Pydantic.
- Adding Pydantic would be a heavy new dependency for what is essentially validation logic.
- `dataclasses` with `__post_init__` validators provide sufficient type safety.
- JSON Schema is exported deterministically from models via a custom export script.
- This avoids maintaining two separate truth sources (Python models and JSON Schema).

If the project later adopts Pydantic across the board, contracts can be migrated. For V1, `dataclasses` is the correct choice for consistency with the existing codebase.

## Existing Code Adopted

- `market_radar/shared/models.py`: Observation, NormalizedSignal, SignalStatus, EvidenceLink — used as input types for legacy adapters
- `market_radar/shared/signal_registry.py`: SignalRegistry — used as source for legacy adapter
- `market_radar/shared/evidence_ledger.py`: EvidenceLedger — examined for legacy adapter design
- `market_radar/shared/event_intelligence_mapper.py`: Event intelligence mapping patterns

## Existing Code Rejected

- Old direction scores (`bullish/bearish` as simple strings without evidence) — not used in new contracts
- Old `confidence` field as uncalibrated score — mapped with loss warning in adapter
- Old `GateDecision` and `GateVerdict` — replaced by explicit Evidence state machine
- Old `NoiseGateResult` — replaced by structured Evidence Bundle
- Old `SignalStatus` lifecycle — replaced by richer Strategy Instance lifecycle
- Old `ObservationStatus` — replaced by Evidence State transitions

## Schema Export Strategy

JSON Schema files under `schemas/intelligence/v1/` are exported from Python models via `scripts/export_intelligence_schemas.py`. The `--check` flag reports drift without modifying files. This ensures Python models remain the single source of truth.
