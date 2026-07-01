# Project Brain

## Identity

**Crypto Market Cognition & Signal OS** is an autonomous internal market-cognition operator for the owner. It continuously discovers, verifies, interprets, prioritizes, updates, weakens, invalidates, and archives crypto-market theses and their affected assets.

It is not a copy-trading product, order-advice service, wallet system, public recommendation service, or external SaaS.

## Owner role

The owner is not part of the daily judgment loop. The owner retains only governance and exception authority:

- product and coverage boundaries;
- credentials and permissions;
- cost ceilings;
- production and publishing approval;
- wallet and trading prohibition or approval;
- stop, recovery, and major scope-change decisions.

Ordinary uncertainty must not be returned to the owner. The system handles it through evidence collection, abstention, delayed review, downgrade, invalidation, or archive.

## Primary result

The system autonomously maintains a bounded **thesis portfolio** rather than merely producing isolated reports.

For each active thesis it maintains:

- verified event and evidence state;
- interpretive claim and causal mechanism;
- affected assets and exposure type;
- time horizon;
- prior expectation and surprise;
- market confirmation and priced-in state;
- supporting and opposing evidence;
- uncertainty and fact-permission limits;
- attention priority;
- next evidence or catalyst;
- expiry and invalidation conditions;
- complete revision history.

## First user outcomes

1. Decide which new information deserves further research and continued machine attention.
2. Decide which assets, sectors, mechanisms, or themes enter the autonomous watch portfolio.
3. Notify the owner only when a high-value thesis is created, materially changes, fails, or the system reaches a governance exception.

The first product responsibility is **market judgment**. Trading action support remains outside the current scope.

## Core business objects

```text
Evidence
  -> Event
  -> Interpretive Claim
  -> Thesis
  -> Asset and theme exposure
  -> Attention State
  -> Lifecycle revision
```

Events are entry facts. Themes and theses persist across events. Assets are exposure objects, not the primary unit of reasoning. Attention state is the main operating result.

## Autonomous judgment responsibilities

The system or its bounded agents decide:

- whether evidence is authentic and sufficient;
- whether an item is new, duplicate, conflicting, or an update;
- whether an event deserves research;
- whether to create, update, link, weaken, invalidate, or archive a thesis;
- which assets and mechanisms are affected;
- whether the effect is positive, negative, mixed, or unclear;
- the relevant time horizon;
- whether the market is unpriced, partly priced, or largely priced;
- thesis priority and machine-attention budget;
- what evidence to gather next;
- when to review again;
- whether disagreement requires abstention.

The system must also judge whether it has the right to make a claim. Lack of qualification results in abstention or reduced scope, not fabricated certainty.

## Limited autonomous discovery

The system may discover and create new themes, theses, and asset observations without prior owner listing when all conditions hold:

- the subject remains inside crypto markets and directly related macro, policy, technology, security, liquidity, and infrastructure mechanisms;
- evidence comes from legal public sources or already approved providers;
- the cost and attention budgets remain inside configured limits;
- the thesis has an explicit mechanism, future evidence path, and exit condition;
- the discovery does not enable trading, publishing, paid interfaces, or new credentials.

Out-of-bound discoveries are retained only as candidates for later governance review.

## Agent responsibility model

Do not create a large free-form multi-agent society. Prefer deterministic code for verifiable rules and a small number of bounded semantic roles:

1. **Evidence Gate** — identity, timestamps, hashes, provenance, permissions, duplication, conflict, and leakage.
2. **Thesis Agent** — importance, mechanism, exposure, horizon, thesis creation or update, and next evidence.
3. **Risk Agent** — narrative absorption, label mismatch, time-scale errors, priced-in risk, counterevidence, and falsification.
4. **Arbitration Agent** — preserves disagreement and chooses activate, observe, abstain, downgrade, or reject.
5. **Lifecycle Agent** — updates priority, catalysts, review schedule, expiry, invalidation, archive, and lessons.
6. **Resource Governor** — caps active theses, evidence retrieval, model calls, retries, and review frequency.

Each role must have structured inputs, structured outputs, authority limits, and deterministic fallback behavior.

## Risk constitution

Risk is part of the decision, not a final disclaimer. Every active thesis must address:

- fact risk;
- interpretation risk;
- market and crowding risk;
- time-horizon risk;
- asset-exposure mismatch;
- priced-in risk;
- behavioral misuse risk;
- explicit invalidation evidence.

A correct market mechanism does not imply an immediate trade. A price move does not prove the causal explanation. Popularity does not prove materiality.

## Product boundaries

Outside current responsibility:

- buy or sell instructions;
- entry, exit, leverage, sizing, or return promises;
- wallet, signing, or order execution;
- copying a trader or imitating a persona;
- public recommendations or production publishing;
- unapproved paid data or model interfaces;
- unlimited discovery, unlimited model calls, or uncontrolled background loops;
- duplication of the QuickFlash source registry.

## Current reality

`main` contains the accepted product responsibility. Draft PR #16 contains a candidate cognition implementation with useful evidence, event, world-state, strategy, arbitration, and packet components.

The branch is not the current product definition and is not accepted as strict Internal Engineering V1. It will be audited later against the autonomous thesis-portfolio responsibility. Reuse, adaptation, quarantine, or removal will be decided module by module after the foundation discussion is complete.

The Mac environment is operational enough for project discussion and future execution. Remaining migration hygiene does not block product thinking.

## Evidence standard

- code presence proves implementation presence only;
- focused tests prove bounded deterministic behavior;
- integrated replay proves a controlled path;
- unattended shadow operation proves runtime behavior;
- longitudinal thesis revisions show whether the system changes its mind correctly;
- baseline comparison and owner outcome review show whether autonomy creates value;
- none of these alone proves profitability or justifies trading automation.

## Current business node

Define the autonomous judgment foundation before auditing or upgrading existing code:

1. exact judgment inventory;
2. agent and deterministic-rule responsibility split;
3. thesis and attention lifecycle;
4. autonomous discovery boundaries;
5. evidence, uncertainty, and risk rules;
6. machine-attention and cost budgets;
7. governance exceptions and stop behavior.

Only after these are locked should the existing repository be reviewed for retain, adapt, quarantine, or remove decisions.
