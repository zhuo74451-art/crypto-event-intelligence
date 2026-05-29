# v0.7 First-Hand Intelligence Plan

Source: `results/v07_claude_onchain_intel_strategy.md`.

## Direction

The news pipeline is now a cleaned second-hand intake layer. v0.7 should add a first-hand structured alert layer, not more news scraping.

Core principle:

```text
raw chain/activity data -> deterministic watcher rules -> structured alert -> optional model review -> existing event/backtest pipeline
```

Do not send raw transaction streams to Claude. Claude reviews only filtered, structured, high-value or uncertain alerts.

## MVP Scope

Build a local-only watcher MVP in 3-7 days:

1. Watched address transfers on Ethereum.
2. Stablecoin mint/burn monitoring for USDT/USDC.
3. Hyperliquid large-position monitoring for curated accounts.
4. Optional Uniswap V3 liquidity snapshots for top pools after the first three are stable.

Do not start with:

- full-chain scanning
- mempool monitoring
- broad multi-chain indexing
- broad Hyperliquid account discovery
- options flow
- social sentiment
- dashboard/UI

## First Data Model

Use CSV first, SQLite second. Every watcher alert should be convertible into the existing `events_raw` shape.

Recommended raw alert fields:

```text
alert_id
observed_at_utc
observed_at_china
source_type
watcher_source
blockchain
tx_hash
block_number
primary_entity
primary_address
counterparty_entity
counterparty_address
asset_symbol
token_address
amount_native
amount_usd
metric_type
metric_value
metric_change_pct
event_type_l1
event_type_l2
risk_category
confidence
relevance_score
threshold_rule
dedupe_key
needs_model_review
model_review_reason
publish_route
raw_json
```

Recommended normalized event fields for backtest integration:

```text
event_id
event_time
title
content
source
asset_symbol
binance_spot_symbol
binance_futures_symbol
event_type
direction_hint
importance
raw_signal_type
watcher_source
entity_label
address
tx_hash
amount_usd
confidence
```

## Watcher Priority

| Priority | Watcher | Why |
|---|---|---|
| P0 | watched address transfers | highest signal-to-noise because targets are curated |
| P0 | stablecoin mint/burn | liquidity supply changes are simple and measurable |
| P1 | protocol treasury outflows | can reveal strategic/risk events before news |
| P1 | Hyperliquid positions | high-value derivatives structure signal when accounts are curated |
| P1 | DEX liquidity depth changes | useful for liquidity/rug/security risk, but noisier |
| P2 | CEX/market-structure aggregates | useful later, but data source quality/cost varies |
| P2 | broad Hyperliquid account discovery | valuable later, but needs position-tracking state and label QA |

## Initial Watchlist Categories

Start with 15-25 targets, not hundreds:

| Category | Count | Example target type |
|---|---:|---|
| Exchange hot wallets | 3-5 | Binance, Coinbase, OKX main hot wallets |
| Stablecoin treasuries | 2-3 | Tether, Circle |
| Protocol treasuries | 4-6 | Uniswap, Aave, Lido, MakerDAO, major L2 foundations |
| Known whale/entity wallets | 3-5 | curated non-exchange whales only |
| Bridge contracts | 2-3 | Wormhole, Stargate, major bridge contracts |
| Staking/system contracts | 1-3 | ETH2 deposit, Lido-related system flows |

Every address must have a label, category, chain, confidence, and threshold. Unknown whale discovery is not v0.7.

## First Thresholds

| Alert Type | First Threshold |
|---|---:|
| watched address transfer | `amount_usd >= 1,000,000` |
| exchange hot wallet flow | `amount_usd >= 5,000,000` |
| stablecoin mint | `amount_usd >= 50,000,000` |
| stablecoin burn | `amount_usd >= 100,000,000` |
| protocol treasury outflow | `amount_usd >= 2,000,000` or `>= 10% treasury estimate` |
| Hyperliquid perp position | `position_value_usd >= 10,000,000` for curated accounts |
| bridge net flow | `net_24h_usd >= 100,000,000` |
| DEX liquidity drop | pool size `>= 10,000,000` and depth drop `>= 20%` |

These are conservative starting gates. The point is useful alerts, not coverage.

## Noise Controls

Local deterministic filters before any model call:

- minimum USD threshold
- known watched address must be involved
- internal same-entity movement suppression
- duplicate suppression by address/token/amount/time window
- spam token blacklist
- stablecoin issuer whitelist
- Hyperliquid account must be explicitly listed in `data/hyperliquid_watchlist.csv`
- only top pools for liquidity monitoring
- no alert for routine exchange hot/cold wallet churn unless above threshold and net-flow context is meaningful

Target funnel:

```text
raw observations -> 50-200 filtered candidates/day -> 20-80 deduped alerts/day -> 5-15 model reviews/day -> 2-8 approved alerts/day
```

## Model Review Policy

Local rules decide obvious cases.

Escalate to Claude/small model only when:

- amount is high but address/entity context is ambiguous
- multiple related alerts cluster within a short window
- liquidity change is extreme
- event has conflicting news/context
- alert text requires careful risk-safe wording

Claude should output structured review only:

```text
review_decision
significance
risk_level
reason
suggested_alert_text
```

No trading recommendation language.

## Validation Loop

Backtest first-hand alerts differently from news:

1. Did the alert happen before related news?
2. Did it precede abnormal price/volume/volatility?
3. Was it unique or repeated noise?
4. Did similar alerts historically matter?

Useful first metrics:

```text
lead_time_to_news_hours
asset_return_1h/4h/24h
abnormal_vs_btc_1h/4h/24h
followup_news_exists
duplicate_cluster_size
signal_quality
```

v0.7 acceptance:

- watcher alerts can be generated from local scripts
- alerts are cached/deduped
- alerts can be converted to current event CSV format
- price backfill can run on watcher-derived events
- a daily Markdown report shows what fired and why
- no Telegram send and no trading integration

## Roadmap

### v0.7

Local first-hand watcher MVP:

- watched address CSV
- Ethereum transfer watcher
- stablecoin mint/burn watcher
- Hyperliquid large-position watcher
- normalized watcher alert CSV
- conversion to event candidates
- one local daily report

### v0.8

Signal quality and expansion:

- DEX liquidity snapshots
- protocol treasury watcher
- signal backtest loop
- model review only for high-value uncertain alerts
- source/entity reliability scoring

### v1.0

Operational intelligence feed:

- combined news + first-hand alert ranking
- cluster related news and watcher alerts
- risk-safe private Telegram publishing after approval gate
- stable watchlist maintenance workflow
- no trading or order execution
