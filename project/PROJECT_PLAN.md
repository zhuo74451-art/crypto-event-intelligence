# Project Plan

## Planning rule

The project advances through one active delivery mode at a time. Internal checkpoints are not user delivery. New work must start from a base that contains the canonical fingerprint in `project/CANONICAL_STATE.yaml`.

## Phase 0 — Canonical state and environment cutover

**Delivery mode:** `MIGRATION_OR_RECOVERY`

### Result

`main` becomes the single recovery entry and the Mac becomes the only active execution environment.

### Work

1. integrate the state-only canonical documents into `main`;
2. complete Issue #21 on the old Windows checkout;
3. preserve local-only files through a migration manifest without committing secrets or generated state;
4. sync the Mac checkout to the final remote branch state;
5. use a supported project Python and authenticated Git tooling;
6. repair or classify the remaining cross-platform full-suite failures;
7. freeze the old computer for project development.

### Acceptance

- canonical documents are present on `main`;
- old-PC working tree is clean or contains only classified local-only material;
- Mac branch and remote branch match;
- one active execution environment remains;
- core suites pass on the Mac;
- remaining full-suite failures, if any, are explicitly classified and do not affect the active path;
- no secret or private local state enters Git.

### Stop conditions

- divergent Git history;
- unclassified old-PC files;
- missing credentials or data that cannot be recreated;
- Mac active path fails in product behavior rather than stale compatibility tests.

---

## Phase 1 — Internal Engineering V1 hardening

**Delivery mode:** `HARDENING`

### Result

One real one-shot program path consumes all approved input lanes and produces complete evidence, world-state, strategy, arbitration, packet, evaluation, and shadow artifacts.

### Required closure

1. runtime intake dispatch for standard observations, QuickFlash JSONL/SQLite, direct evidence, market state, expectations, research claims, and historical outcomes;
2. strict fact-permission, origin, hash, and future-leakage blocking;
3. real mapping from market and event inputs into all eight strategy evaluators;
4. research status, regime, priced-in state, source quality, contradictions, and missing domains used by arbitration;
5. explicit strategy disagreement and non-actionable eligible states;
6. separate always-neutral, price-only, and event-only baselines with stable event/outcome mapping;
7. complete machine-readable and Markdown shadow outputs;
8. all 12 acceptance cases running through the same integrated entrypoint with unconditional semantic assertions;
9. focused tests for every active lane and artifact;
10. accurate PR and documentation claims.

### Acceptance envelope

- `usable_now`: true for internal replay and one-shot shadow operation;
- `end_to_end_integrated`: true;
- `real_entrypoint_present`: true;
- `failure_handling_present`: true;
- `operator_actions_present`: run, inspect status, and stop;
- `recovery_or_rollback_present`: deterministic replay and clean rerun;
- `acceptance_evidence_present`: focused, integrated, and full-suite evidence;
- `canonical_state_updated`: true.

### Explicit non-claims

This phase does not prove production reliability, profitable strategies, or sufficient live-market coverage.

---

## Phase 2 — Real-data shadow experiment

**Delivery mode:** `DISCOVERY_EXPERIMENT`

### Hypothesis

The integrated system can improve internal market assessment quality over simple price-only and event-only baselines while preserving abstention under weak evidence.

### Design

- bounded duration: 14 calendar days or 100 eligible event cases, whichever occurs first;
- one-shot execution only unless recurring operation is separately approved;
- approved inputs: QuickFlash contract exports, direct official evidence, public market state, research claims, and recorded outcomes;
- no public publishing, trading, paid data, or wallet behavior;
- immutable run manifests and evidence references;
- all packets retained for later review.

### Primary measures

- evidence-permitted assessment coverage;
- abstention precision on weak-evidence cases;
- contradiction and invalidation recognition;
- priced-in classification quality;
- strategy eligibility precision;
- disagreement preservation;
- confidence calibration;
- missing-input and source-health rates;
- operator time per accepted packet;
- comparison against always-neutral, price-only, and event-only baselines.

### Decision rules

- **continue to hardening:** integrated system beats at least one meaningful baseline without increasing false confidence and retains useful abstention;
- **change:** evidence quality, mapping, or calibration fails but the core path remains useful;
- **stop or reduce scope:** strategy layer adds no decision value over simpler event and market assessment, or operator cost exceeds the value of outputs.

---

## Phase 3 — Trust calibration and usable operator workflow

**Delivery mode:** `USABLE_INCREMENT`

### Result

The owner can run one command or one approved UI action, inspect bounded evidence-backed packets, review follow-up requests, and recover from failure without manual repository surgery.

### Eligible work

- packet review surface or report bundle;
- evidence drill-down;
- comparison and calibration summaries;
- replay and backfill controls;
- clear status and stop actions;
- source and strategy health views.

### Deferred until evidence supports them

- daemonized monitoring;
- automatic publishing;
- public SaaS;
- trade or wallet execution;
- generalized multi-project platform abstractions.

## Current active node

Only Phase 0 is active. Phase 1 may be compiled after Phase 0 acceptance. Phase 2 begins only after strict Engineering V1 acceptance. Phase 3 begins only if the shadow experiment produces a useful decision delta.
