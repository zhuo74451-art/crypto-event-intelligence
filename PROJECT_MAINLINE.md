# Crypto Market Cognition & Signal OS — Mainline Contract

## Authority

This file is the canonical product-direction contract for `main`.

It supersedes every earlier roadmap, handoff packet, RC1 plan, personal-use release plan, phase plan, and product-positioning document in this repository. Historical release evidence may remain for audit purposes, but it has no planning authority.

When code, tests, reports, branches, pull requests, or old documentation conflict with this contract, this contract wins until it is explicitly replaced on `main`.

## Product Definition

Build an AI-first crypto market cognition and effective-signal system that:

1. maintains a multi-domain model of the crypto market;
2. identifies material changes in news, policy, macro, market structure, positioning, on-chain activity, fundamentals, attention, and narrative;
3. distils reusable decision methods from strong traders, research papers, official reports, and high-quality industry research;
4. evaluates each candidate signal through evidence, expectation gap, transmission path, market confirmation, crowding, time horizon, historical reliability, and invalidation conditions;
5. outputs a small number of evidence-backed market-impact judgements and risk/observation guidance.

The product may express directional market impact, volatility risk, relative strength, crowding, or conditions to wait for. It does not place orders, sign transactions, operate wallets, promise returns, or provide unqualified buy/sell instructions.

## Canonical Output

Every production-grade judgement must support:

- `direction`: bullish / bearish / volatility_up / neutral / insufficient_evidence;
- `assets_or_sectors`;
- `time_horizon`;
- `event_state`;
- `evidence_summary`;
- `expectation_gap`;
- `transmission_path`;
- `market_confirmation`;
- `priced_in_estimate`;
- `crowding_state`;
- `alternative_explanations`;
- `invalidation_conditions`;
- calibrated `confidence`;
- source and point-in-time provenance.

`INSUFFICIENT_EVIDENCE` is a valid and necessary result.

## Five Core Subsystems

### 1. Market World Model

Covers macro/liquidity, cross-asset regime, regulation, geopolitics, spot and derivatives microstructure, stablecoins, on-chain actors, DeFi mechanisms, token supply, fundamentals, security dependencies, attention, narrative, and data quality.

### 2. Research Intelligence & Cognitive Coverage

Maintains research claim cards, conflicting evidence, knowledge decay, unexplained events, canonical research corpus, and candidate hypotheses. A paper or article does not become production truth without validation.

### 3. Trader Strategy Distillation & Strategy Registry

Converts public trader material into structured strategy seeds, then into testable hypotheses. It does not create personality-roleplay agents or accept self-reported performance as proof.

### 4. Signal Arbitration & Calibration

Combines relevant strategies by regime, horizon, evidence quality, and historical reliability. It does not use simple majority voting or one opaque universal score.

### 5. Evidence Acquisition & Source Health

Uses replaceable adapters and services for official APIs, RSS, page-change detection, structured crawling, academic discovery, content extraction, evidence archiving, and notifications. Acquisition is infrastructure, not the product brain.

## Existing Repository Treatment

The current repository is an engineering substrate, not a product definition.

Existing event normalization, registry, deduplication, price backfill, run history, audit, market readers, whale-domain code, rendering, and operator utilities are retained only when they support the new mainline. Every module is subject to one of four decisions:

- `RETAIN`: directly supports the new contract;
- `ADAPT`: useful substrate but semantics must change;
- `QUARANTINE`: preserve temporarily while evidence is gathered;
- `DELETE`: old-direction code, duplicated implementation, or unjustified complexity.

Passing old tests or appearing in an old release report is not sufficient reason to retain a component.

## Development Rules

1. New work lands against the current `main` contract, not against historical phases.
2. Prefer mature open-source packages, isolated services, and thin adapters over custom infrastructure.
3. Preserve point-in-time evidence and five timestamps: published, effective, updated, first-seen, retrieved.
4. Separate facts, interpretations, hypotheses, and validated strategy components.
5. No strategy claim enters production without historical out-of-sample testing and real-time shadow evidence.
6. Technical indicators are supporting market-state features unless incremental value is proven.
7. No daemon, cron, systemd service, paid API, production send, or long-running monitor is enabled without explicit approval.
8. Each execution round returns evidence before the next execution task is assigned.

## Current Implementation Boundary

The immediate implementation target is a read-only, one-shot acquisition and evidence pilot for:

- SEC / EDGAR;
- Congress.gov and Federal Register;
- Federal Reserve / FRED / BLS / BEA;
- GitHub Releases and Security Advisories;
- Trafilatura extraction;
- changedetection.io integration contract;
- ArchiveBox evidence contract;
- Apprise notification contract.

The pilot produces normalized observations and source-health evidence only. It does not produce trading recommendations or enable recurring monitoring.

## Canonical Supporting Contracts

- `research/intelligence/foundations/FOUNDATION_ADOPTION_MATRIX_V1.yaml`
- `market_radar/acquisition/contracts/SOURCE_ACQUISITION_CONTRACT_V1.yaml`
- `market_radar/acquisition/contracts/source_contract.schema.json`
- `market_radar/acquisition/contracts/normalized_observation.schema.json`
- `docs/PROJECT_OVERVIEW.md`
- `docs/ARCHITECTURE.md`
- `docs/PROJECT_STATUS.md`

## Historical Material Policy

Historical release and audit evidence may be used to verify what existed at an earlier commit. It must not be used to infer the current roadmap, acceptance criteria, product identity, or next action.