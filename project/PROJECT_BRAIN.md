# Project Brain

## Identity

**Crypto Market Cognition & Signal OS** is an internal research and intelligence system for the owner. It is responsible for turning time-bounded evidence into explainable market assessments. It is not an automated trading product, a wallet system, or an external SaaS.

## User result

The owner can submit a bounded batch of evidence and market-state inputs and receive an evidence-backed assessment that states:

- what happened and what remains uncertain;
- affected assets and time horizon;
- prior expectation and surprise;
- transmission path;
- market confirmation and priced-in state;
- eligible and rejected strategy components;
- disagreement, counter-explanations, expiry, and invalidation;
- calibrated confidence or explicit abstention.

## System shape

```text
Sources and market data
  -> source contracts and point-in-time evidence
  -> normalized observations
  -> event state and expectation gap
  -> market world state and research claims
  -> transmission and market confirmation
  -> executable strategy evaluations
  -> arbitration and abstention
  -> Market Decision Packet
  -> historical and real-time shadow evaluation
```

## Five systems

1. **Market World Model** — macro, policy, geopolitical, spot, derivatives, stablecoin, on-chain, DeFi, token supply, fundamentals, security, attention, and data quality.
2. **Research Intelligence** — papers, official reports, industry research, claim conflicts, decay, and testable hypotheses.
3. **Trader Strategy Distillation** — variables, triggers, confirmation, horizon, expiry, and invalidation without persona imitation.
4. **Strategy Registry & Arbitration** — versioned components, eligibility, disagreement preservation, and insufficient-evidence behavior.
5. **Evidence Acquisition** — official APIs, RSS, pages, snapshots, extraction, archiving, and source health through replaceable services and thin adapters.

## Product boundaries

The following are outside the current responsibility:

- order generation or execution;
- leverage, sizing, wallet, or signing actions;
- automated copying of traders;
- recurring daemon or scheduler activation without explicit approval;
- paid data or model interfaces without explicit approval;
- production publishing or public recommendations;
- duplication of the QuickFlash source registry.

## Current reality

The default branch contains the accepted product identity and the earlier acquisition foundation. Draft PR #16 contains a candidate cognition implementation with useful contracts, world-state components, executable strategy evaluators, arbitration, and packet code.

The candidate is **not** accepted as strict Internal Engineering V1. Remote audits still identify incomplete runtime intake dispatch, research integration, historical baselines, complete shadow artifacts, and semantic integrated-case proof. Local executor test receipts are supporting evidence, not independent acceptance.

The old Windows checkout has not yet completed its final checkpoint. The Mac checkout exists and passes the cognition and acquisition suites, but environment cutover and the full-suite compatibility repair are not yet sealed.

## Innovation surface

Local invention is limited to the combination that directly creates owner value:

- point-in-time event and expectation reasoning;
- market-world-state linkage;
- evidence-aware strategy eligibility;
- disagreement-preserving arbitration;
- evidence-backed packets with explicit abstention;
- historical and shadow trust calibration.

Acquisition connectors, scheduling, storage utilities, notification, and generic retrieval should prefer mature packages, services, or thin adapters.

## Evidence standard

A claim is accepted only at the level supported by evidence:

- code presence proves implementation presence;
- focused tests prove bounded deterministic behavior;
- integrated replay proves one controlled path;
- real-data shadow runs prove operational behavior over time;
- none of the above alone proves profitability or production trust.

## Current business node

Finish canonical-state integration and environment cutover. No new product feature work starts before:

1. this state-only change is integrated into `main`;
2. Issue #21 closes the old-PC checkpoint;
3. the Mac becomes the only active execution environment;
4. the next engineering base contains the canonical fingerprint.

## Next accepted delivery

After cutover, the next delivery is a **Hardening** package that closes the remaining Internal Engineering V1 gaps without expanding product scope. The following delivery is a bounded real-data shadow experiment with explicit continue/change/stop rules.
