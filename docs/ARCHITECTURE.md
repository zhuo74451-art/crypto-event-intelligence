# Architecture

The canonical product direction is defined in `PROJECT_MAINLINE.md`. The active state and delivery sequence are defined in `project/CANONICAL_STATE.yaml` and `project/PROJECT_PLAN.md`.

This file records the accepted conceptual architecture only. Detailed engineering contracts remain open until the Autonomous Judgment Foundation discussion exits Stage 1.

## Accepted cognition path

```text
Approved sources and market data
  -> point-in-time evidence and source permission
  -> event identity and immutable revision history
  -> interpretive claims and causal mechanisms
  -> persistent theses
  -> asset and theme exposure
  -> horizon, priced-in state, risk, and disagreement
  -> attention state and resource allocation
  -> follow-up evidence and review scheduling
  -> strengthen, weaken, invalidate, archive, or reopen
  -> material-change summary or silence
  -> longitudinal shadow evaluation
```

The primary runtime object is a thesis portfolio with revisions, not a sequence of isolated Market Decision Packets.

## Responsibility layers

### Deterministic layer

Owns verifiable constraints:

- source identity and contract validation;
- published, effective, updated, first-seen, retrieved, assessment, revision, and review times;
- hashes, provenance, and evidence references;
- fact permission;
- duplication and explicit conflict detection;
- future-data leakage prevention;
- resource ceilings, retries, and stop rules;
- persistence, idempotency, recovery, and audit trails.

### Semantic judgment layer

Uses a small number of bounded roles:

1. **Thesis Agent** — importance, mechanism, exposure, horizon, and thesis creation or revision.
2. **Risk Agent** — counterevidence, narrative absorption, label mismatch, time-scale error, priced-in risk, and falsification.
3. **Arbitration Agent** — disagreement preservation and activate, observe, abstain, downgrade, or reject decisions.
4. **Lifecycle Agent** — attention state, catalyst tracking, review schedule, expiry, invalidation, archive, reopen, and lessons.
5. **Resource Governor** — active-thesis limits, retrieval budgets, model-call budgets, retries, and review frequency.

The Evidence Gate is primarily deterministic, with semantic assistance only for bounded extraction or conflict interpretation.

Every semantic role requires:

- structured inputs;
- structured outputs;
- explicit authority;
- evidence references;
- uncertainty representation;
- deterministic fallback;
- termination behavior.

## Core state objects

```text
EvidenceRecord
EventState
InterpretiveClaim
Thesis
ExposureLink
AttentionState
ReviewIntent
LifecycleRevision
GovernanceException
```

Exact schemas are not locked yet. Existing repository contracts are candidates for later retain, adapt, quarantine, remove, or missing classification.

## Autonomous discovery boundary

The system may discover new themes, theses, and asset observations when:

- the subject remains within crypto and directly related macro, policy, technology, security, liquidity, and infrastructure mechanisms;
- evidence comes from approved public or contracted sources;
- cost and machine-attention ceilings are respected;
- a causal mechanism, future evidence path, and exit condition are present;
- no new credential, paid interface, publishing, wallet, or trading authority is introduced.

Out-of-bound findings do not expand live scope and remain governance candidates only.

## Research path

```text
paper, report, official publication, or public trader material
  -> evidence-qualified research claim
  -> conflict, limitation, decay, and applicability review
  -> testable mechanism or strategy component
  -> historical out-of-sample evaluation
  -> longitudinal real-time shadow evaluation
  -> validated, rejected, stale, or retired component
```

Research and trader material may inform interpretation but cannot override evidence permission, risk review, or lifecycle controls.

## Acquisition boundary

QuickFlash remains a separate broad-recall acquisition provider. This repository consumes contracted exports and may independently gather direct official evidence, market state, expectations, research material, and historical outcomes. It does not duplicate the QuickFlash source registry.

External acquisition, retrieval, archiving, scheduling, and notification remain replaceable packages or services behind thin adapters.

## State and evidence rules

- evidence, events, interpretations, theses, and validated components remain separate;
- historical outcomes never enter point-in-time inference;
- future evidence is blocked from earlier decisions;
- price movement cannot substitute for a causal mechanism;
- popularity cannot substitute for materiality;
- missing inputs and disagreement remain visible;
- unsupported claims are narrowed, deferred, or rejected;
- insufficient evidence produces abstention;
- every active thesis has future evidence, review, expiry, and invalidation conditions;
- every material revision records what changed and why.

## Runtime modes

- **replay:** deterministic fixture or archived-evidence execution;
- **bounded unattended shadow:** approved real inputs, persistent thesis lifecycle, strict budgets, no external production side effects;
- **owner-facing operation:** material-change summaries, system health, and governance exceptions after shadow acceptance;
- **trading or public-advice operation:** not authorized.

Recurring unattended cognition is part of the intended product, but it may be activated only after the responsibility model, status and stop controls, budgets, recovery, and shadow acceptance exist. Paid interfaces, public publishing, wallet operations, copy trading, and order execution remain disabled by default.
