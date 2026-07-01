# Architecture

The canonical product direction is defined in `PROJECT_MAINLINE.md`. The active state and delivery sequence are defined in `project/CANONICAL_STATE.yaml` and `project/PROJECT_PLAN.md`.

## Active reasoning path

```text
Sources and market data
  -> source contracts and point-in-time evidence
  -> normalized observations
  -> event state and expectation gap
  -> market world state
  -> transmission and market confirmation
  -> executable strategy evaluations
  -> disagreement-preserving arbitration
  -> calibrated assessment or abstention
  -> Market Decision Packet
  -> historical and real-time shadow evaluation
```

## Research path

```text
paper, report, official publication, or public trader material
  -> research claim or strategy seed
  -> source, conflict, limitation, and decay review
  -> testable hypothesis
  -> strategy component candidate
  -> historical out-of-sample evaluation
  -> real-time shadow evaluation
  -> validated, rejected, stale, or retired component
```

## Acquisition boundary

QuickFlash is a separate broad-recall acquisition provider. This repository consumes its contracted exports and can independently gather direct official evidence, market state, expectations, research material, and historical outcomes. It does not duplicate the QuickFlash source registry.

External acquisition, retrieval, archiving, and notification remain replaceable packages or services behind thin adapters. Existing modules are retained only after `RETAIN`, `ADAPT`, `QUARANTINE`, or `REMOVE` review.

## State and evidence rules

- published, effective, updated, first-seen, retrieved, and assessment times remain distinct;
- historical outcomes never enter inference;
- future evidence is blocked from point-in-time decisions;
- facts, interpretations, hypotheses, strategy candidates, and validated components remain separate;
- source authority and fact permission affect what the system may claim;
- missing inputs and strategy disagreement remain visible;
- insufficient evidence produces abstention rather than fabricated confidence.

## Runtime modes

- **replay:** deterministic fixture or archived-evidence execution;
- **one-shot shadow:** real inputs, no production side effects, retained outputs for later evaluation;
- **production:** not authorized.

Recurring monitoring, paid interfaces, public publishing, wallet operations, and trade execution are disabled by default.
