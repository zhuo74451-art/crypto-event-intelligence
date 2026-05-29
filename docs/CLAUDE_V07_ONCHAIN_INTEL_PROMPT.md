# Crypto Event Intelligence v0.7 Direction Check

We have a local Crypto Event Intelligence pipeline working:

- real news export/import
- candidate extraction
- entity/taxonomy enrichment
- local relevance filtering
- TG-style private draft generation
- Claude-assisted draft review for uncertain/high-value items
- Binance price backfill
- BTC/ETH abnormal return backtest
- quality gates and Project OS docs

The current system is mostly based on scraped/news/TG-style fast news. It can produce a small approved private-pilot queue, but this is still mostly second-hand information.

Now we need the next layer: first-hand intelligence.

Question:

What should v0.7 build next so this becomes a real Web3 intelligence product rather than just a cleaned news forwarder?

Think like a tough product/engineering lead. Do not be polite if the current direction is weak.

We want actionable intelligence, not trading signals:

- no buy/sell/long/short recommendations
- no exchange order APIs
- no auto trading
- no Notion
- local CSV/SQLite/Python first
- Telegram publishing can come later, but do not focus on UI

The user’s intended product:

- Filter large volumes of Web3/crypto news into items actually useful for market research.
- Send relevant intelligence to a private/group channel with risk-safe language.
- Add first-hand monitoring, such as important on-chain addresses, whale positions, protocol/security incidents, DEX/liquidity changes, and market-structure signals.
- Avoid huge manual labeling. Use local deterministic filters first, cheap model/Claude only for uncertain/high-value cases.
- Build an early version that creates visible value quickly.

Please answer concretely:

1. What first-hand intelligence sources should we prioritize after the news pipeline is working?
2. Which sources are high value but too expensive/noisy for v0.7?
3. What is the correct MVP scope for v0.7 in 3-7 days?
4. What data model should first-hand alerts use so they can join the existing event/backtest pipeline?
5. Should we start with watched addresses, protocol metrics, DEX liquidity, CEX market structure, Hyperliquid positions, stablecoin mint/burn, or something else?
6. How should we avoid drowning in on-chain noise?
7. What should be local rules vs Claude/model judgment?
8. What should the first 20 watchlist targets be, by category rather than exact addresses if necessary?
9. What thresholds should trigger an alert in the first version?
10. What backtest/research loop should validate whether these first-hand alerts are useful?
11. What should we explicitly not build yet?
12. Give a ruthless roadmap: v0.7, v0.8, v1.0.

Output should be implementation-oriented. Prefer tables, schemas, and concrete acceptance criteria.
