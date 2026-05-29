# Crypto Event Intelligence Project Plan

## Product Positioning

Crypto Event Intelligence is a Web3 event intelligence and research system.

The product goal is not to generate trading orders or buy/sell signals. The first goal is to create a high-quality event flow:

```text
raw Web3 news + first-party monitoring
-> relevance filtering
-> standardized intelligence publishing
-> local research records
-> event backtest and review
```

The product is primarily an intelligence platform. Price backtesting is a validation layer, not the product itself.

## Core Product Decision

Use path B as the main direction and path A as a support layer:

- Path A: event -> price prediction -> alpha signal.
- Path B: event -> intelligence filtering -> TG publishing + research record.

The current project should optimize for Path B first. Abnormal return is used to audit event value over time, not to directly decide real-time publishing.

## Current Engineering Status

The local pipeline already works:

- CSV / SQLite / Python on Windows.
- Real backend read-only export.
- Candidate import and time normalization.
- `symbol_map` enrichment.
- Binance price backfill and cache.
- BTC / ETH benchmark returns.
- Quality report.
- Suggested review decisions.
- Mature filtering and stratified auto50.
- Statistical validation.

v0.4.3 older500 result:

- 500 raw rows exported.
- 500 candidates generated.
- 234 suggested include, 1 fix, 265 exclude.
- 500 mature 72h candidates.
- Stratified auto50 selected 37.
- 37 backfill ok.
- 37 quality pass.

v0.5 result:

- No `event_type` bucket passed FDR correction on `abnormal_vs_btc`.
- Most buckets are below the default minimum sample threshold of 10.
- v0.4.3 descriptive winners remain exploratory.
- The null hypothesis remains the default.

## Key Problems

### Thin Samples

Most `event_type` buckets only contain 2-8 rows. This is not enough for statistical conclusions.

### Uninterpretable `other`

`other` performed well descriptively at 72h, but it mixes AVAX stablecoin, SOL RWA, Ethereum Foundation, BTC Saylor, and other unrelated stories. This is a taxonomy and entity extraction failure, not a valid event type.

### BTC / ETH Benchmark Pollution

BTC events often produce `abnormal_vs_btc = 0`. ETH events can have the same issue versus ETH. Benchmark assets must be handled separately.

### Missing Pre-Event Price-In Check

The system does not yet know whether price had already moved before publication. Without pre-event returns, the system cannot distinguish fresh information from stale news.

### Missing Event Deduplication

Multiple sources may report the same underlying event. Without event aggregation, source count and event uniqueness are both polluted.

### Regime Still Matters, But Not First

Regime Filter is important, but adding it before event relevance, entity quality, and deduplication will create overfit analysis on dirty data.

## Revised Roadmap

### v0.6: Event Intake Quality Layer

Goal: turn raw candidates into a cleaner research and publishing candidate pool.

Scope:

- Entity dictionary.
- Improved entity extraction.
- L1 / L2 event taxonomy.
- Event deduplication.
- Benchmark correction for BTC / ETH events.
- Real-time relevance scoring.
- Three-way publish decision.

Outputs:

```text
data/entity_dictionary.csv
data/event_candidates_v06_enriched.csv
data/event_candidates_v06_deduped.csv
data/event_candidates_v06_relevance_scored.csv
results/v06_relevance_filter_summary.csv
```

### v0.6.1: Larger Historical Dataset

Goal: expand sample size before deeper statistical claims.

Target:

- 5,000+ historical candidates if the backend has enough data.
- Versioned outputs.
- Holdout split.

### v0.6.2: Manual Ground Truth

Goal: create a small but reliable validation set.

Target:

- 200 manually reviewed events.
- Labels: `auto_publish`, `human_review`, `discard`.
- Notes on false positives and false negatives.

### v0.7: TG Intelligence Publisher

Goal: publish only high-quality intelligence candidates.

Initial mode:

- Generate local TG-style drafts first.
- Keep all drafts in `pending_review`.
- Review usefulness, factual correctness, asset attribution, and tone before any real group posting.
- No Telegram API connection in the pilot.
- No auto-send.
- `discard` never published.

Every published event must be saved to local CSV/SQLite for later backtesting.

v0.7 starts as a product smoke test, not a statistical claim. Backtest output is used to catch broken time, symbol, price, and attribution logic. It is not required to prove event-type alpha before the first private draft pilot.

Private pilot acceptance:

- 10-20 reviewed draft events are generated in a local queue.
- Reviewers can mark: useful, interesting but not actionable, noise, factual issue, asset issue, time issue.
- The daily review queue can be cleared in under 30 minutes.
- No draft contains buy/sell/long/short recommendation language.
- `auto_publish` remains disabled.

Current estimate:

- Local private draft MVP: 0-1 day.
- Operator-usable daily workflow: 1-2 days.
- Semi-automated TG posting MVP: 3-5 days after explicit approval to connect Telegram.
- First-party watcher MVP: 1-3 weeks after the monitored address/source list is fixed.

See `docs/MVP_TIMELINE.md`.

### v0.8: First-Party Watchers

Goal: generate first-party events before media reports.

Initial watcher scope should be narrow:

- Known whale addresses.
- CEX large inflow/outflow.
- Project/team wallets.
- Known exploit/hacker addresses.
- Stablecoin mint/burn or large exchange inflow if data is available.

Avoid broad on-chain indexing in this phase.

Watcher architecture:

- Watchers should emit structured alerts, not raw transaction dumps.
- Deterministic rules handle thresholds, known wallets, known exchanges, known contracts, and routine transfer templates.
- Claude is used only for novel, ambiguous, or high-impact alerts after rule filtering.
- Routine on-chain events should be log-only or discarded without LLM review.

### v0.9: Regime Filter

Goal: add market-state context after the event intake layer is cleaner.

Minimum features:

- BTC pre-event 24h / 72h return.
- BTC realized volatility.
- BTC drawdown from recent high.
- Above/below moving average.
- Risk-on / risk-off label.

### v1.0: Research-Grade Event Intelligence OS

Goal: maintain a complete event intelligence loop:

```text
collect -> filter -> publish -> record -> backtest -> review -> improve taxonomy
```

Minimum requirements:

- Versioned datasets.
- Stable event taxonomy.
- Holdout discipline.
- Published-event audit trail.
- Statistical validation report.
- Obsidian research notes.
- Reproducible commands.

## Real-Time vs Retrospective Scores

The system must keep two scores separate.

### `relevance_score_realtime`

Used for TG publishing. It may only use information available at event time:

- source quality.
- event type.
- entity quality.
- source count available then.
- timeliness.
- known market cap tier.
- manual allow/deny rules.

It must not use future 24h / 72h returns.

### `relevance_score_retrospective`

Used for internal research. It may include:

- realized abnormal returns.
- post-event price confirmation.
- quality outcomes.
- retrospective event grouping.

This score cannot drive real-time publishing.

## AI Review Cost Control

Claude is a scarce review tier.

The production path is:

```text
raw event -> local rules -> dedup -> cheap/local review tier -> Claude only for uncertain/audit rows
```

Do not send every raw event to Claude. See `docs/AI_COST_CONTROL_POLICY.md`.

## Publishing Decision

Use three states, not a binary decision:

```text
auto_publish
human_review
discard
```

Recommended rule:

- `auto_publish`: high certainty, clear asset/entity, high relevance, no deny rule.
- `human_review`: useful but ambiguous, multi-asset, medium certainty, or market-wide.
- `discard`: stale, generic, duplicate, missing asset, non-market content, unverified rumor.

## Suggested Scoring Fields

Use interpretable fields:

- `impact_score`
- `certainty_score`
- `timeliness_score`
- `entity_quality_score`
- `source_count_score`
- `price_corroboration_score`
- `relevance_score_realtime`
- `relevance_score_retrospective`
- `publish_decision`
- `discard_reason`

Do not let weighted averages override hard deny rules. Example:

- `certainty_score` too low -> `discard`.
- `missing_asset` and not `market_wide` -> `discard`.
- duplicate inside the same event cluster -> do not publish as a new event.

## Event Type Model

Use two levels:

- `event_type_l1`: stable high-level taxonomy.
- `event_type_l2`: more flexible subtype.

Initial L1 examples:

- whale_position
- institutional_flow
- exchange_listing
- hack_security
- regulation_macro
- token_supply
- network_upgrade
- project_business
- stablecoin_flow
- market_structure
- other_review

`other` should not be a final publishable type. Use `other_review` as a queue that requires taxonomy improvement.

## Benchmark Rules

Avoid self-benchmark pollution:

- BTC events should not be judged by `abnormal_vs_btc`.
- ETH events should not be judged by `abnormal_vs_eth`.
- Non-BTC/ETH token events can use BTC, ETH, or a blended benchmark.

Candidate benchmark policy:

```text
BTC event -> primary benchmark ETH or market basket
ETH event -> primary benchmark BTC or market basket
Other token event -> primary benchmark blended BTC/ETH
Market-wide event -> benchmark is not enough; evaluate separately
```

## Things To Cut For Now

- Full web UI.
- Notion integration.
- AI automatic classification as the core decision engine.
- Auto trading.
- Buy/sell/long/short signals.
- Broad on-chain indexing.
- Complex Regime Filter before v0.6 quality layer.
- Treating auto50 or any small bucket as alpha proof.

## Immediate Backlog

1. Create entity dictionary.
2. Enrich candidates with entities and L1/L2 taxonomy.
3. Deduplicate same underlying event by entity + event type + time window.
4. Add corrected benchmark policy.
5. Add real-time relevance scoring.
6. Add publish decision: `auto_publish`, `human_review`, `discard`.
7. Export summaries explaining what was discarded and why.
8. Only then prepare TG publishing.

## v0.6 Initial Implementation Status

Implemented:

- `data/entity_dictionary.csv`
- `scripts/enrich_event_entities.py`
- `scripts/deduplicate_event_candidates.py`
- `scripts/filter_research_relevant_events.py`
- `scripts/run_v06_event_intake_quality.py`
- `tradability_tier`
- `channel_route`
- `primary_discard_reason`
- `legal_enforcement`
- `onchain_data`

First run on older500 suggested candidates:

- total: 500
- clusters: 177
- auto_publish: 1
- human_review: 71
- discard: 428
- other_review: 217
- duplicate_non_primary: 323
- missing_entity: 212
- unsupported_asset: 8

Interpretation:

- Duplicate/syndicated content is a major issue.
- `other_review` remains too high and needs dictionary/taxonomy expansion.
- The conservative publishing gate is working: almost nothing is allowed to auto-publish.
- The next iteration should focus on reducing false positives in `human_review`.

v0.6.5 decision table:

```text
docs/V065_DECISION_TABLE.md
```

## v0.7 First-Hand Intelligence Layer

Direction source:

```text
docs/V07_FIRST_HAND_INTEL_PLAN.md
results/v07_claude_onchain_intel_strategy.md
```

v0.7 should not expand the news crawler. It should add a local first-hand watcher layer:

1. Curated watched address transfers.
2. Stablecoin mint/burn monitoring.
3. Structured alert normalization.
4. Conversion into the current event/backtest schema.
5. Daily local report of fired alerts.

First implementation targets:

- `data/watchlist_addresses.csv`
- `data/watcher_alerts_raw.csv`
- `data/watcher_events_raw.csv`
- `scripts/watch_eth_address_transfers.py`
- `scripts/watch_stablecoin_mint_burn.py`
- `scripts/normalize_watcher_alerts_to_events.py`
- `scripts/run_v07_first_hand_watchers.py`

Do not start v0.7 with broad chain indexing, Hyperliquid position tracking, mempool monitoring, Telegram auto-send, or trading integration.
