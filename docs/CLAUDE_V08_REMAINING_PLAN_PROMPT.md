# Crypto Event Intelligence: Remaining Plan Review

We are building a crypto event intelligence system, not a trading bot.

Current state:

- Historical/news pipeline works locally: raw news -> candidates -> AI/rule review -> event rows -> Binance price backfill -> BTC/ETH abnormal returns -> quality reports.
- Real-time Telegram group publishing is active for a small first-hand watcher feed.
- Existing server news pipeline has been formatted into richer Chinese Telegram cards.
- A separate first-hand watcher service is running on the server every 5 minutes.

Current first-hand sources:

- Watched Ethereum address ERC20 transfers.
- USDT/USDC treasury mint/burn.
- Curated Hyperliquid large positions.
- CEX wallet net-flow lite.
- Binance USD-M funding-rate anomalies.
- Aave V3 Ethereum lending liquidation events.

Current controls:

- Deterministic quality gate before Telegram send.
- Dedupe state before sending.
- China time for human-facing output.
- No buy/sell/long/short advice.
- No order execution.
- No Notion.

Recent behavior:

- CEX netflow produced live messages.
- Funding-rate watcher queried markets but produced no alerts under production thresholds.
- Aave V3 liquidation watcher saw raw logs but produced no publishable alerts under the 1M USD threshold.
- Hyperliquid position watcher is currently a strong source of TG items.

I want your direct project-manager review:

1. What should be the next 5-10 engineering priorities?
2. Which current source is likely highest ROI, and which source is likely noise?
3. What quality gates are still missing before scaling TG publishing?
4. Should we add DEX swap/liquidity monitoring now, or first improve the existing watcher feed?
5. How should we prevent Telegram from becoming noisy while still feeling real-time?
6. What should we measure daily to know whether this product is actually useful?
7. What should we explicitly not build yet?
8. What are the biggest architecture risks in this project right now?
9. What is the first version that would be good enough to show 10 real users?
10. Be blunt. Do not agree for politeness.

Keep the answer practical and opinionated.
