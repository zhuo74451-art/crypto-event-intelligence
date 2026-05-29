# Crypto Event Intelligence: Project Review Request

You are reviewing a real project as a blunt product/engineering advisor.

Please do not flatter the team. Give direct, critical, useful advice. If the direction is wrong, say so. If something is overbuilt, underbuilt, or based on a weak assumption, call it out.

## What This Project Is

We are building a crypto event intelligence system.

The goal is not to build a trading bot, not an execution system, and not a directional trade-instruction generator. The goal is to turn fast crypto/news/on-chain events into useful intelligence that can be published to a Telegram group and later evaluated through historical replay and post-alert follow-up.

The intended user is a crypto trader/researcher/operator who watches Telegram during active hours and wants fast, readable, filtered, contextual alerts. The system should reduce noise and surface events that are more likely to be worth attention.

Important user perspective:

- Users will not reliably reply or react to Telegram messages.
- A user may read an alert, think about it, check charts, act privately, or ignore it. We should not assume lack of feedback means lack of value.
- Timing and convenience matter. For example, scheduled digests should cover China-time daytime and high-attention trading periods, not follow rigid artificial rules.
- Telegram messages must be easy to scan, visually readable, Chinese-first where appropriate, and should explain why an event matters without telling users what trade to take.

## Current System State

The project has working local pipelines for:

- Raw news normalization.
- Event candidate import.
- Symbol/entity/taxonomy enrichment.
- Candidate relevance scoring.
- Mature candidate filtering.
- Stratified auto-review sampling.
- Binance price backfill.
- BTC/ETH abnormal return calculation.
- Backfill quality validation.
- Price source validation.
- Time provenance auditing.
- Historical replay.
- First-hand watcher alerts for curated Ethereum addresses and stablecoin mint/burn.
- Watcher alert normalization into the event/backtest and Telegram draft schemas.
- Telegram live monitor with quality gates, rate limits, and China-time send windows.
- Scheduled China-time morning/noon/evening digests.
- CEX netflow rolling baseline context.
- Hyperliquid large-position state-change tracking.
- Binance USD-M long/short ratio snapshots for digest context.

The realtime Telegram service is deployed on a server and active.

Recent quality loop:

- TG quality loop passed.
- It now uses sent-state metadata, 4h/24h follow-up, and source usefulness reporting.
- Realtime Telegram replies/reactions have been removed from the core quality loop because users will not reliably provide clean feedback.
- Current live sent-state is still small: 8 sent alerts, 3 sources, 3 computable 4h follow-up rows, 0 computable 24h follow-up rows.

Historical replay:

- Broad replay: 200 selected rows, 200 price backfill ok, 200 quality pass.
- Conservative replay: 120 selected rows, 120 price backfill ok, 120 quality pass.
- Non-BTC single-asset replay mode was added to remove BTC/ETH benchmark pollution and macro pollution.
- Non-BTC single-asset usable sample from older500 was only 1 row.
- Diagnosis: the older500 exported news sample is dominated by BTC, macro, and multi-asset stories. It is not enough for serious single-asset event-type conclusions.
- A benchmark-aware report was added:
  - BTC rows use abnormal_vs_eth.
  - non-BTC rows use abnormal_vs_btc.
  - This is only an interim fix for BTC benchmark self-comparison.

Older500 candidate distribution after base eligibility:

- total input rows: 500
- base eligible rows: 219
- asset counts: BTC 162, ADA 23, ETH 16, BNB 7, DOGE 4, SOL 3, XRP 3, AVAX 1
- scope counts: market_wide 139, multi_asset 40, single_asset 40
- event types: macro 160, hack_security 20, other 18, network_upgrade 6, institutional_flow 5, halving 4, token_unlock 4, staking_governance 2
- non-BTC base rows: 41
- non-BTC single-asset rows: 8
- non-BTC single-asset rows with meaningful event types after filtering: only 1 token_unlock XRP row

Current product direction:

- Live TG alerting exists.
- The team now thinks relying on user feedback/reactions as a primary metric is naive.
- We need a better quality loop based on:
  - historical replay
  - 4h/24h/72h post-alert follow-up
  - source-level usefulness
  - source concentration/noise
  - whether alerts are timely, readable, and convenient for real users

Current suspected issues:

- Historical samples are too BTC/macro-heavy.
- `other` and broad macro buckets are not very interpretable.
- BTC events can pollute abnormal_vs_btc analysis.
- There is no mature regime filter yet.
- There is no pre-event price-in check yet.
- The live TG product may still be too infrastructure-heavy and not enough user-experience/product-first.
- We need more first-hand intelligence sources, not just recycled second-hand news.

## What We Want From You

Give a complete project review and next-step plan.

Please cover:

1. The strongest critique of the current direction.
2. What should be kept, cut, or deprioritized.
3. Whether historical replay should be expanded by more random news export, targeted asset/event queries, or first-hand watcher history.
4. How to handle BTC/macro domination in replay.
5. How to build a better source-quality loop without relying on user reactions.
6. What first-hand intelligence sources should be prioritized next.
7. How the TG feed should feel from the user's perspective:
   - timing
   - frequency
   - digest vs realtime
   - message format
   - Chinese readability
   - what is useful vs annoying
8. Whether morning/noon/evening digests are sensible, and what each should contain.
9. What metrics actually matter for a Telegram intelligence product.
10. What the next 7 days should focus on.
11. What the next 30 days should focus on.
12. What not to build yet.
13. Where AI review/classification should be used, and how to control cost.
14. How to tell if the project has reached a useful first version.

Be concrete. Give implementation-level advice where possible. Do not give generic startup advice. Assume the team can write Python scripts, run local CSV/SQLite pipelines, deploy a server-side Telegram monitor, and call public APIs.

Output as a structured plan with clear priorities and hard tradeoffs.
