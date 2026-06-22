# Research Intelligence System V1

## Overview

This document describes the Research Intelligence Layer (Lane E) of the Crypto Event Intelligence system. It receives validated strategy results from Lanes A-D and produces structured research artifacts: claims, evidence graphs, conflict sets, questions, candidates, and dossiers.

## Architecture

```
Lane A (Macro Evidence)
  → Lane B (Market Data)
    → Lane C (Strategy Replay)
      → Lane D (Validation & Calibration)
        → Lane E (Research Intelligence)
```

## Core Components

### Contracts
- **ResearchClaimV1** — Structured claims with deterministic IDs, enumerated statuses, evidence linkage
- **EvidenceEdgeV1** — Directed edges linking claims to evidence sources with role (supporting/opposing)
- **ConflictSetV1** — Groups opposing claims without majority resolution
- **ResearchQuestionV1** — Open questions requiring additional data/validation
- **CandidateRecordV1** — Strategy candidates compiled from evidence
- **DecisionRecordV1** — Records of state changes with audit trail
- **ResearchDossierV1** — Comprehensive per-candidate research summary

### Engines
- **Claim Normalizer** — Deterministic claim key generation from structured components
- **Evidence Graph** — Directed graph with JSONL + SQLite persistence
- **Conflict Engine** — Detects direction, horizon, regime, and validation conflicts
- **Candidate Compiler** — Auto-proposes candidates from supported/contested claims

### Integration Layer
- **Producer Locks** — SHA-pinned producer artifact tracking
- **Compatibility Checker** — 16 checks per producer lane
- **Integration Gates** — 7-layer CI gate system
- **Internal Pipeline** — Deterministic, idempotent end-to-end runner

## Principles

1. No claim status may read "proven", "guaranteed", "certain", or "profitable"
2. No majority-vote conflict resolution
3. Opposing evidence preserved alongside supporting evidence
4. Failed experiments in retrievable layer, not hidden
5. Calibration required before probability expression
6. Historical correlation not presented as causal fact
7. In-sample results not extended to out-of-sample conclusions

## Current Status

- 47 tests passing
- Integration gates: 6/6 pass
- Pipeline: deterministic run IDs, idempotent
- Sample data: 10 claims, 12 evidence edges, 3 conflict sets, 10 candidates, 10 dossiers
- Lane A: 1,658 macro events available (manifest needs repair)
- Lanes B/C/D: Not yet available upstream
