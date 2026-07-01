# Autonomous Judgment Contract

**Status:** Active  
**Purpose:** define what the unattended market-cognition system decides, who owns each decision, and how uncertainty degrades without routine owner input.

## Authority levels

- **L0 — Rule Final:** identity, time, provenance, permission, duplication, future-data blocking, budgets, retries and stop constraints. Semantic models cannot override these decisions.
- **L1 — Bounded Semantic:** importance, mechanism, exposure, horizon, interpretation and risk. Every output must be structured and evidence-referenced.
- **L2 — Internal Arbitration:** selects an internal cognition action from an allowlist. It cannot create an external side effect.
- **L3 — Owner Governance:** project scope, new access, material budget expansion, public operation, irreversible action, or other authority expansion.

## Roles

1. **Evidence Gate:** validates identity, timestamps, hashes, provenance, fact permission, duplication, conflict and future leakage.
2. **Thesis Agent:** judges novelty, materiality, mechanism, exposure, horizon, thesis relationship and next evidence.
3. **Risk Agent:** attacks narrative absorption, label mismatch, time-scale error, priced-in assumptions, hidden premises and falsification conditions.
4. **Arbitration Agent:** chooses activate, observe, risk-only, mechanism-candidate, abstain, downgrade, invalidate, archive or reject.
5. **Lifecycle Agent:** maintains review intent, catalyst state, strengthening, weakening, expiry, invalidation, reopening and learning candidates.
6. **Resource Governor:** enforces active-thesis, retrieval, model-call, retry, review-frequency and loop limits.

## Complete judgment inventory

### Evidence and event

| ID | Judgment | Owner | Default when unresolved |
|---|---|---|---|
| J01 | Source identity and fact permission | Evidence Gate, L0 | Block or restrict |
| J02 | Time coherence and future-data risk | Evidence Gate, L0 | Isolate; no inference |
| J03 | Content integrity and provenance | Evidence Gate, L0 | Remove fact permission |
| J04 | Entity resolution and impersonation risk | Evidence Gate, L0 with bounded extraction help | Isolate candidate |
| J05 | New, update, duplicate or contradiction | Evidence Gate, L0 with bounded conflict help | Low-priority unresolved |
| J06 | New event, event revision, related event or separate event | Thesis Agent, L1 under deterministic compatibility rules | Keep separate |
| J07 | Confirmed, partial, disputed, unconfirmed or retracted event state | Thesis Agent, L1 | Unconfirmed |

### Meaning and exposure

| ID | Judgment | Owner | Default when unresolved |
|---|---|---|---|
| J08 | Real-world change versus repetition, commentary, marketing or price-only noise | Thesis Agent, L1 | Do not activate |
| J09 | Research materiality and expected machine-attention value | Thesis Agent, L1 | Low priority or reject |
| J10 | Defensible causal mechanism and missing links | Thesis Agent, L1 | No directional claim |
| J11 | Genuine asset, sector, protocol or market exposure and exposure type | Thesis Agent, L1 | Exposure unknown; no activation |
| J12 | Positive, negative, mixed or unclear effect by time horizon | Thesis Agent, L1 | Unclear |
| J13 | Prior expectation and surprise | Thesis Agent, L1 | Unavailable |
| J14 | Unpriced, partly priced, largely priced, possible overreaction or contradictory response | Thesis Agent challenged by Risk Agent, L1 | Unavailable; lower priority |
| J15 | Strongest counterevidence, alternative explanation, hidden assumption and falsification condition | Risk Agent, L1 | Candidate cannot activate |

### Portfolio and lifecycle

| ID | Judgment | Owner | Default when unresolved |
|---|---|---|---|
| J16 | Active-portfolio admission | Arbitration Agent, L2 | Abstain or reject |
| J17 | Attention priority: immediate, high, normal, low or dormant | Arbitration Agent under Resource Governor cap, L2 | Low |
| J18 | Next evidence, named catalyst, review trigger and review time | Lifecycle Agent, L2 | Time-box, then archive |
| J19 | Unchanged, strengthened, weakened, invalidated, expired, archived or reopen-candidate | Lifecycle Agent challenged by Risk Agent, L2 | Unchanged with lower priority |
| J20 | Whether a change is material enough to notify the owner | Arbitration Agent under rate limits, L2 | Silence and log |
| J21 | Whether an outcome creates a reusable learning or calibration candidate | Lifecycle Agent, L1 | No learning promotion |
| J22 | Whether the system reached a governance decision outside its authority | Resource Governor, L3 | Stop or continue in reduced scope |

## Admission contract

An active thesis requires all applicable gates:

1. valid identity;
2. real change or new independent evidence;
3. defensible mechanism;
4. genuine exposure;
5. sufficient evidence quality and fact permission;
6. future verification path;
7. expiry or invalidation condition;
8. acceptable manipulation, liquidity and data risk;
9. positive machine-attention value;
10. no duplicate active thesis.

Possible outcomes are `activate`, `observe_low_priority`, `risk_observation`, `mechanism_candidate`, `abstain` or `reject`.

## Normal unattended resolution

- missing evidence -> defer or abstain;
- agent disagreement -> preserve disagreement and reduce authority;
- malformed model output -> bounded retry, then deterministic fallback;
- repeated reviews with no change -> lengthen interval, then archive;
- exhausted budget -> stop new work and preserve state;
- source failure -> use an approved fallback or reduce scope;
- state corruption -> stop and recover from the last valid checkpoint;
- unresolved low-priority candidate -> expire without owner interruption.

## Owner interruption boundary

The owner is interrupted only for a declared governance exception or a material result:

- project boundary or authority expansion;
- new protected access or material cost expansion;
- public or production operation;
- irreversible action;
- serious security or privacy failure;
- repeated systemic failure beyond the recovery budget;
- creation, major revision or invalidation of a high-value thesis.

Routine ambiguity, importance, direction, follow-up and lifecycle questions stay inside the system.

## Minimum audit record

Every judgment records its ID, input references, rule or role version, output, evidence references, uncertainty, authority level, fallback use, timestamp and thesis revision ID.

## Acceptance test

- every normal-path decision has exactly one accountable owner;
- semantic roles cannot override L0 prohibitions;
- semantic outputs are structured and evidence-referenced;
- ordinary uncertainty does not require human input;
- L2 decisions cannot cause external side effects;
- every active thesis has next evidence, review, expiry and invalidation;
- every owner interruption maps to a declared material-change or governance rule.
