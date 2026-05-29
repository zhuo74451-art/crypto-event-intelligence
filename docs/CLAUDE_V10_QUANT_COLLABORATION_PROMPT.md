# Crypto Event Intelligence: Ask Claude For Product, Quant, And System Planning

You are acting as a blunt external product/quant research advisor. Please do not flatter the project. Point out weak assumptions, false precision, bad product decisions, missing data, and places where we are likely fooling ourselves.

## What We Are Building

We are building a crypto event intelligence system.

It is not an auto-trading bot. It is not a trade signal service. It should not send buy/sell/long/short instructions. The practical goal is:

- collect potentially market-relevant crypto events and first-hand signals,
- structure them into analyzable event records,
- publish the most useful real-time market intelligence to a Telegram group in readable Chinese,
- backtest historical events against price moves after publication,
- learn which sources, event types, and features are actually useful.

The system should eventually answer:

> After this event or signal is published, does the related asset show statistically meaningful excess return or volatility over 1h / 4h / 24h / 72h, relative to BTC / ETH / market regime?

## Current Implemented System

### Historical Research Pipeline

We have a local CSV / SQLite / Python pipeline:

1. raw news export
2. normalize raw news
3. import into event candidates
4. entity and event-type enrichment
5. relevance scoring
6. suggested review / auto selection
7. mature event filtering
8. Binance price backfill
9. BTC / ETH abnormal return calculation
10. data quality report
11. historical replay findings

It already supports:

- UTC / China-time normalization,
- Excel serial time parsing,
- symbol mapping,
- Binance spot/futures kline backfill,
- SQLite price cache,
- event quality validation,
- event type aggregation,
- benchmark-aware adjustment for BTC-heavy samples,
- historical sample replay.

Known research weaknesses:

- event_type buckets are still thin and noisy,
- the `other` bucket is not explainable,
- BTC events vs BTC benchmark can flatten abnormal return,
- regime filtering is missing,
- pre-event price-in checking is incomplete,
- historical source data has many noisy or irrelevant rows,
- “sample count” is still far from enough for strong statistical claims.

### Live / Telegram Intelligence Pipeline

We also have a live Telegram intelligence pilot:

- first-hand-ish watchers for curated Ethereum addresses and stablecoin activity,
- Hyperliquid large position / whale position snapshots,
- CEX netflow / stablecoin flow context,
- Binance long-short ratio / crowding snapshots,
- token unlock calendar context,
- morning/noon/evening digests,
- intraday market radar every roughly 1 hour during active periods,
- Chinese Telegram formatting,
- repeat suppression for static items,
- price context from Binance where available,
- empty-board skip logic.

Current v0.9 product direction:

- Main Telegram group should receive compact ranked radar boards and rare high-importance interrupts.
- It should not receive raw database dumps, long tables, backend labels, raw scores, repeated facts, or generic interpretation paragraphs.
- We recently redesigned cards toward concise Chinese summaries:

Example direction:

```text
15:49 盘中雷达

优先关注
• HOME 明日 08:00 解锁 18.6M，占流通 7.5%，主要释放给团队/贡献者

结构信号
• loraclexyz 持有 HYPE 空头 $104.8M，浮亏 $22.8M，静态大仓位

仅供市场观察，不构成交易建议。
```

User feedback:

- This is more readable than raw alert cards, but still too thin.
- Intraday radar should have more effective content every 1-2 hours, including recent active signals, on-chain information, whale movement, market indicators, and price context.
- Priority should be active position changes, then static large positions.
- Avoid repeated static facts; token unlocks should appear in morning/evening reports or at most one intraday radar item unless urgent.
- Users care about daytime active hours and practical readability, not rigid academic rules.

## Theoretical Target System Effect

The ideal system is not “more alerts”. It should become an intelligence loop:

1. Collect structured events from news, Telegram/X sources, on-chain watchers, CEX/stablecoin flows, derivatives data, unlocks, and whale positioning.
2. Rank events by expected informational value, not by how exciting the headline sounds.
3. Publish only readable, compact, context-rich intelligence to Telegram.
4. Automatically evaluate every published item after 1h / 4h / 24h / 72h.
5. Learn source usefulness and event-type usefulness from outcomes.
6. Adjust thresholds, repeat suppression, and category priority from evidence.
7. Build a clean event feature store that a quant person can inspect and test.

The best version of the system might include:

- event-time and source-time provenance,
- pre-event price-in check,
- regime filter,
- volatility-adjusted abnormal return,
- benchmark-aware logic for BTC/ETH events,
- source usefulness report,
- entity usefulness report,
- alert postmortem,
- event feature schema,
- quant-facing dataset export,
- rules + AI-assisted classification where it clearly reduces noise,
- live alerts that are sparse, explainable, and verifiable.

## Current Question

We want your honest advice on how to improve the system and how to talk with a quant collaborator.

Please answer deeply and practically. Do not restrict yourself to our current implementation. Be creative, but keep the recommendations grounded enough to build.

## What We Need From You

Please provide:

1. Brutal diagnosis: what is fundamentally right, what is fundamentally weak, and what is likely fake progress.
2. What the system should become in 30 / 60 / 90 days.
3. What should be built next before adding more sources.
4. Which data sources or first-hand signals are actually worth adding, and which are distractions.
5. How to turn Telegram posts into a measurable product loop.
6. How to design event features so that historical backtests become meaningful.
7. How to handle regime, price-in, benchmark, volatility, and BTC/ETH pollution.
8. How much AI classification should be used versus deterministic rules.
9. How to control cost if AI is used for event filtering or explanation.
10. What a quant collaborator can realistically help with.
11. What exact questions we should ask the quant collaborator in our first serious conversation.
12. What datasets, files, and metrics we should prepare before that conversation.
13. How to judge whether the Telegram product is valuable from the user perspective without relying on users giving feedback.
14. What not to build.
15. A concrete prioritized implementation backlog.

Important: give real opinions. If some idea is naive, say so. If a metric is misleading, say so. If the system is likely to overfit, say so. If the right next step is boring data plumbing, say that too.
