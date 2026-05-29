# v0.6 Initial Scope: Event Intake Quality Layer

## Goal

v0.6 should clean and score event candidates before they enter research, publishing, or backtesting.

The goal is not to find alpha. The goal is to stop garbage events, ambiguous events, and duplicate events from polluting the intelligence stream.

## Why This Comes Before Regime Filter

Regime Filter is valuable, but current data still has:

- thin event_type samples.
- too many mixed `other` events.
- BTC/ETH benchmark pollution.
- duplicate/syndicated news.
- no pre-event price-in check.
- no formal publish eligibility.

Adding regime now would analyze dirty buckets and create overfit conclusions.

## v0.6 Deliverables

### 1. Entity Dictionary

Create:

```text
data/entity_dictionary.csv
```

Minimum fields:

```text
entity_id,entity_type,canonical_symbol,canonical_name,aliases,market_scope,notes
```

Examples:

- BTC / Bitcoin / 比特币
- ETH / Ethereum / 以太坊
- SOL / Solana / 索拉纳
- AVAX / Avalanche
- Saylor / MicroStrategy / Strategy
- SEC / CFTC / Fed
- Binance / Coinbase / OKX

### 2. Candidate Entity Enrichment

Create script:

```text
scripts/enrich_event_entities.py
```

Input:

```text
data/event_candidates_real_500_older_review_suggested.csv
```

Output:

```text
data/event_candidates_v06_enriched.csv
```

Add fields:

```text
detected_entities
primary_entity
primary_asset_symbol
entity_quality_score
entity_flags
event_type_l1
event_type_l2
```

### 3. Event Deduplication

Create script:

```text
scripts/deduplicate_event_candidates.py
```

Cluster by:

```text
primary_entity + event_type_l1 + time bucket
```

Initial window:

```text
2 hours
```

Add fields:

```text
event_cluster_id
is_cluster_primary
source_count
duplicate_count
cluster_titles
```

### 4. Benchmark Correction

Update backtest/analyze layer to support:

```text
primary_benchmark
primary_abnormal_return_1h
primary_abnormal_return_4h
primary_abnormal_return_24h
primary_abnormal_return_72h
```

Rules:

- BTC event -> benchmark ETH or blended market basket.
- ETH event -> benchmark BTC or blended market basket.
- Other token event -> blended BTC/ETH benchmark.
- Market-wide event -> separate evaluation, not single-token alpha.

### 5. Relevance Scoring

Create script:

```text
scripts/filter_research_relevant_events.py
```

Output:

```text
data/event_candidates_v06_relevance_scored.csv
results/v06_relevance_filter_summary.csv
```

Add fields:

```text
impact_score
certainty_score
timeliness_score
entity_quality_score
source_count_score
price_corroboration_score
relevance_score_realtime
relevance_score_retrospective
publish_decision
discard_reason
research_priority
```

## Hard Deny Rules

Any of these should force `discard` unless manually overridden:

- missing asset/entity and not market-wide.
- source confidence too low.
- stale event.
- duplicate non-primary event.
- generic market commentary.
- pure price recap with no new information.
- promotional/event marketing content.
- unsupported asset with no reliable price source.

## Publish Decision

Use:

```text
auto_publish
human_review
discard
```

Do not publish everything with a medium score.

Initial recommendation:

- `auto_publish`: only high certainty and high relevance.
- `human_review`: all useful but ambiguous items.
- `discard`: all low relevance or hard-deny items.

## TG Language Standard

Avoid:

- buy.
- sell.
- long.
- short.
- entry.
- stop loss.
- take profit.

Use:

- observation bias.
- impact strength.
- certainty.
- timeliness.
- risk note.
- research context.

Example:

```text
【链上观察】BTC 巨鲸地址出现大额转入交易所
资产：BTC
类型：whale_position
观察偏向：risk
影响强度：★★★★☆
确定性：★★★★☆
时效性：★★★★★
说明：该事件可能增加短期波动，需要结合市场状态继续观察。
声明：仅用于事件研究，不构成交易建议。
```

## v0.6 Exit Criteria

- `other` / `other_review` ratio decreases or becomes explainable.
- Duplicate events are clustered.
- Every candidate has a publish decision.
- Discard reasons are enumerable and countable.
- BTC/ETH benchmark pollution has a defined handling policy.
- TG publishing can be tested from `auto_publish` / `human_review` rows only.

## Initial Run Result

Input:

```text
data/event_candidates_real_500_older_review_suggested.csv
```

Command:

```powershell
python scripts/run_v06_event_intake_quality.py --input data/event_candidates_real_500_older_review_suggested.csv
```

Output:

```text
data/event_candidates_v06_enriched.csv
data/event_candidates_v06_deduped.csv
data/event_candidates_v06_relevance_scored.csv
results/v06_relevance_filter_summary.csv
```

First result:

- total: 500
- event clusters: 177
- auto_publish: 1
- human_review: 71
- discard: 428
- other_review: 217
- duplicate_non_primary: 323
- missing_entity: 212
- unsupported_asset: 8

Immediate follow-up:

- Improve dictionary coverage for project tokens and named entities.
- Tighten false positives in `human_review`.
- Review `other_review` and promote repeat patterns into L1/L2 taxonomy.
- Do not connect TG publishing until this review pass is cleaner.
