# Crypto Market Cognition & Signal OS — Mainline Contract

The canonical state is `project/CANONICAL_STATE.yaml`.

## Responsibility

Build an unattended internal market-cognition operator that discovers, verifies, interprets and maintains a bounded portfolio of crypto-market theses.

Its first outcomes are autonomous research prioritization and autonomous watch-portfolio maintenance. It is not a trade-instruction, wallet, execution or public-advice product.

## Accepted cognition shape

```text
Approved Inputs
  -> Deterministic Evidence Gate
  -> Event and Candidate Builder
  -> Thesis Synthesis
  -> Risk Challenge
  -> Deterministic Arbitration
  -> Thesis Revision and Attention Action
  -> Durable Follow-up Review
  -> Material Notification or Silence
```

The two semantic passes are schema-bound responsibilities, not autonomous conversational agents. Deterministic rules own fact permission, lifecycle, resources and external effects.

## Accepted engineering foundation

Stage 2 and Stage 3 WP-01 are closed.

Accepted production route:

- Python 3.12 isolated runtime;
- Pydantic domain contracts;
- separate event and thesis state models;
- SQLAlchemy and Alembic with bidirectional schema parity;
- append-only immutable revisions and current projections;
- optimistic compare-and-swap;
- transactional table-driven 11-state thesis lifecycle;
- deterministic idempotency request fingerprints;
- minimal local SQLAlchemy durable-review ledger;
- point-in-time historical evidence contracts;
- frozen split, persisted identity and correction-chain controls;
- BLIND tuning exclusion;
- Pydantic AI as a future thin structured gateway;
- OpenTelemetry traces and metrics.

PR #28 is the accepted production foundation. Draft PR #16 remains unmerged and has no planning authority; it is only a component quarry and failure record.

DBOS remains deferred because the current route requires Postgres and has not justified that service boundary.

## Delivery strategy

The owner result is a complete internal production system, not a demo MVP.

`project/COMPLETE_ENGINEERING_DELIVERY_TRAIN.md` is authoritative. Internal packages are bounded and mergeable, but form one continuous delivery train. Historical evidence, point-in-time replay, blind evaluation and adversarial testing precede routine live validation.

Expected effort allocation:

- historical evidence, replay, blind evaluation and adversarial testing: 55–65%;
- cognition and lifecycle implementation: 25–35%;
- unattended live Shadow: 10–15%;
- routine owner real-time testing: approximately zero.

## Integration rule

`project/INTEGRATION_POLICY.md` is authoritative.

Executor work is produced on a bounded branch and Draft PR. GPT independently inspects the exact remote Head, diff, tests, artifacts and runtime evidence, then directly merges a candidate that is demonstrably better than current `main` and has no accepted regression or governance-boundary change.

The executor never self-merges. The reviewed Head is protected during merge, and remote `main` is verified afterward.

## Stable rules

1. Accepted decisions are synchronized to `main` in the same cycle.
2. Validated improvements are directly merged under the integration policy.
3. QuickFlash remains a separate broad-recall provider.
4. Evidence, events, interpretations and theses remain separate.
5. Point-in-time integrity and future-data blocking are mandatory.
6. Semantic roles cannot override deterministic prohibitions.
7. Ordinary uncertainty remains inside the system through narrowing, abstention, delay, downgrade or archive.
8. Longitudinal Shadow evidence is required before autonomous judgment is trusted.
9. Historical replay and blind evaluation precede routine live validation.
10. Internal work packages are not separate MVP deliveries.
11. The first runtime uses the minimal local SQLAlchemy ledger; DBOS is reopened only by evidence.
12. No trading, wallet, public publication or hidden daemon enters the active path.
13. Outcome labels remain separate from evidence inputs and input hashes.
14. Event identities and correction chains may not cross frozen dataset splits.
15. BLIND cases, identities, chains and outcomes may not enter tuning paths.

## Current business node

Run **Stage 3 Work Package 02 — Historical Evidence and Point-in-Time Data Factory**.

Build at least 1,500 qualified historical cases across six event families and multiple regimes using public read-only sources, deterministic rebuilds, strict future-leakage blocking, frozen BUILD / DEVELOPMENT / BLIND splits and separate outcome artifacts.

WP-02 may not call a semantic model, tune prompts, score cognition quality, run a daemon, start live Shadow, create public effects or modify PR #16.
