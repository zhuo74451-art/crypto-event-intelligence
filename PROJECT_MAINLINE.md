# Crypto Market Cognition & Signal OS — Mainline Contract

This file defines the canonical product direction for `main`. Runtime and planning state are resolved through `project/CANONICAL_STATE.yaml` and the project files it references.

Earlier roadmaps, handoff packets, RC1 plans, phase plans, and product-positioning documents are historical unless explicitly reactivated by the canonical state.

## Product responsibility

Build an AI-first internal crypto market research and intelligence system that combines:

1. a multi-domain market world model;
2. point-in-time evidence and source health;
3. research claims, conflicts, and knowledge decay;
4. structured strategy distillation;
5. strategy eligibility and disagreement-preserving arbitration;
6. historical and real-time shadow validation;
7. calibrated assessments with explicit insufficient-evidence and abstention states.

The product does not execute trades, sign wallet actions, publish production recommendations, or enable recurring services by default.

## Canonical architecture

```text
Sources and market data
  -> source contracts and point-in-time evidence
  -> normalized observations
  -> event state and expectation gap
  -> market world state and research claims
  -> transmission and market confirmation
  -> executable strategy evaluations
  -> arbitration, calibration, and abstention
  -> evidence-backed Market Decision Packet
  -> historical and real-time shadow evaluation
```

## Repository treatment

Existing modules and Draft-branch components are engineering candidates. Each module must be classified as one of:

- retain;
- adapt;
- quarantine;
- remove.

Code presence, old release labels, local test counts, or historical documentation do not establish current acceptance on their own.

## Stable rules

1. New work follows this contract and the canonical state map.
2. Prefer mature packages, isolated services, and thin adapters for generic acquisition, storage, scheduling, notification, and retrieval.
3. Preserve published, effective, updated, first-seen, retrieved, and assessment times.
4. Separate facts, interpretations, hypotheses, candidate strategies, and validated components.
5. QuickFlash remains a separate broad-recall acquisition provider; this repository consumes contracted outputs and may collect direct evidence independently.
6. Require historical out-of-sample and real-time shadow evidence before strategy trust.
7. Keep explicit evidence-insufficient and abstention behavior.
8. Do not enable paid interfaces, recurring services, production publishing, wallet actions, or execution without explicit approval.
9. Return remote execution evidence before assigning the next implementation package.
10. Future work bases must contain the current canonical fingerprint.

## Current implementation state

### Accepted

- product identity and architecture;
- point-in-time evidence and source-health direction;
- explicit expectation, confirmation, arbitration, and abstention concepts;
- no-go boundaries above.

### Candidate

Draft PR #16 contains an internal cognition prototype, world-model structures, strategy components, arbitration, and decision-packet code. It is not accepted as strict Internal Engineering V1 until the remaining integrated intake, research, baseline, shadow-artifact, and semantic acceptance gaps close.

### Active business node

The current node is canonical-state integration and Windows-to-Mac responsibility cutover. The next node is Internal Engineering V1 Hardening. A bounded real-data shadow experiment follows only after strict hardening acceptance.

## Canonical documents

- `README.md`
- `PROJECT_MAINLINE.md`
- `project/CANONICAL_STATE.yaml`
- `project/PROJECT_BRAIN.md`
- `project/PROJECT_PLAN.md`
- `project/DISCUSSION_STATE.yaml`
- `project/DECISION_REGISTER.yaml`
- `project/LEARNING_QUEUE.yaml`
- `docs/ARCHITECTURE.md`
