# Crypto Event Intelligence: Telegram Product/Card Review Request

You are reviewing a real crypto intelligence product as a blunt product manager, market-structure thinker, and engineering advisor.

Do not flatter us. Do not assume our current direction is correct. If a feature is naive, noisy, overbuilt, underbuilt, or missing the point for real crypto users, say it directly.

We want you to use imagination and judgment. You are allowed to propose better structures than the ones we currently have. You are allowed to suggest things we did not ask for. The only requirement is that your advice should be concrete enough to implement.

## Product Goal

We are building a Telegram-first crypto event intelligence system.

The goal is not:

- not a trading bot
- not an execution system
- not auto order placement
- not explicit buy/sell/long/short instructions

The goal is:

- filter large amounts of Web3/crypto news and first-hand signals
- identify events that are plausibly useful to traders/researchers/operators
- publish high-signal Chinese Telegram alerts
- explain why the event matters without telling users what trade to take
- later evaluate alert usefulness through historical replay and post-alert follow-up

The intended user is a crypto trader/researcher/operator who watches Telegram during active China-time hours. They want fast, readable, filtered, contextual alerts. They will not reliably give feedback. Lack of reactions is not a useful metric.

The user's own product view:

- "Do not make me manually review 200 events one by one."
- "Users will not seriously give feedback in a TG group; designing around user feedback is naive."
- "The TG feed should be useful during daytime and high-frequency trading/checking periods."
- "The feed should not look like plain copied news."
- "It should feel like an intelligence radar: first-hand or fast second-hand events, clear category, reason, magnitude, and what to watch next."

## What Is Already Implemented

The project already has working local and server-side pieces:

- raw news normalization
- event candidate import
- symbol/entity/taxonomy enrichment
- candidate relevance scoring
- mature candidate filtering
- stratified auto-review sampling
- Binance price backfill
- BTC/ETH abnormal return calculation
- backfill quality validation
- price source validation
- time provenance auditing
- historical replay and post-alert follow-up
- first-hand watchers for curated Ethereum addresses and stablecoin treasury flows
- CEX netflow baseline from Etherscan transfers
- Hyperliquid large-position snapshots and state tracking
- CoinMarketCap public token-unlock API integration
- Binance USD-M long/short ratio snapshots for digest context
- Telegram live monitor with quality gates, token cooldown, source caps, and China-time send windows
- morning/noon/evening China-time digest framework

The realtime Telegram service is deployed on a server and active.

Recent live examples now visible in Telegram:

- ETH Hyperliquid large-position snapshot
- HYPE Hyperliquid large-position snapshot
- BTC Hyperliquid large-position snapshot
- HOME token unlock

Quality gates currently try to block low-quality microcap unlock spam, repeated token spam, and weak alerts. Current sources are now visible, but the product is still early and may be too backend-driven.

## Current TG Card Direction

Old/plain Telegram messages looked like copied text blocks. The user disliked this.

Current improved card direction is Chinese-first and source-specific, for example:

```text
⚡ 【稳定币流动】USDT 大额链上信号
━━━━━━━━━━━━
📌 事件：Tether 金库收到 5104.76 万美元 USDT
🕘 时间：2026-05-27 04:35:35 UTC+8
🏷 实体：Tether
🔎 类型：金库转入
💰 金额：5104.76 万美元
🔥 强度：★★★★☆
✅ 置信：中

🧠 解读：稳定币进入发行方金库，属于大额资金流动信号；需要继续观察后续是否出现增发、赎回或交易所流向。

🧾 复核：需要
原因：金额较大，需要结合上下文复核
🔗 交易：0x...

⚠️ 仅作链上情报与研究观察，不构成任何交易建议。
```

Another card class:

```text
⚡ 【链上仓位】HYPE 大额仓位信号
━━━━━━━━━━━━
📌 事件：某地址在 Hyperliquid 持有 HYPE 大额多头仓位
🕘 时间：2026-05-28 14:xx:xx UTC+8
🏷 实体：Hyperliquid
🔎 类型：大额仓位快照
💰 名义规模：...
🔥 强度：...
✅ 置信：...

🧠 解读：这不是交易指令，而是大额杠杆仓位状态；后续重点观察仓位是否突然增加/减少、接近清算、或与资金费率/价格异动共振。
```

Potential problem: even improved cards may still be too verbose, too uniform, not ranked enough, and not enough like a useful market radar.

## Screenshots From A Competing/Reference App

The user showed screenshots from a crypto app similar to Following. We cannot send you the images, but here is what they showed.

### Screen 1: Market Page

- Page title: 市场
- Section: 热门项目
- Tabs: X热议榜 / 涨幅榜 / 跌幅榜
- Each row shows:
  - token icon
  - rank
  - symbol
  - price
  - percentage move
  - number of KOLs discussing
  - small sparkline
- Section: 交易机会
- Tabs: 1h OI持仓异动 / 24h OI持仓异动
- Each row shows:
  - symbol
  - price
  - price change
  - contract OI value
  - OI change percentage

Product lesson:

- users understand rankings faster than individual alerts
- social heat + price/OI anomaly is a useful market radar layer
- rows are compact and comparable

### Screen 2: Security/Risk Detail

An example detailed risk event:

```text
【风险等级】 R1
【风险标签】 token被盗-外部协议
【涉及币种】 JOE
【核心事件】 JOE代币由于外部合约重入漏洞导致约119.6万枚被盗
【关键事实】
1. 漏洞根源为某函数中的单函数重入漏洞
2. 攻击者通过25次重入循环获利
3. 攻击合约地址和受影响代理合约地址
【发布时间】...
【新闻来源】...
```

Product lesson:

- security events need a risk-report template, not a generic news template
- fields should be structured: risk level, risk tag, affected asset, core event, key facts, source
- this is very readable even if long because every field has a job

### Screen 3: Intelligence Center Cards

Cards include:

- 资金异动 / 极端资金费率
- 代币解锁
- 量价异动

Each card contains:

- news/anomaly type
- monitoring information
- source/context
- asset symbol
- current price
- price percentage move
- sometimes a "go trade" button

We do NOT want explicit trade-action buttons, but the layout is useful:

- type
- monitoring fact
- source
- asset
- market context

### Screen 4: Hot Trend / Headline List

Section: 热点风向标

It shows:

- ranked hot headlines
- asset symbols highlighted in green
- KOL热议 tag
- heat number
- mix of regional/global items

Product lesson:

- not every useful item is a real-time interrupt
- some should be grouped into a hot-trend digest/list
- highlighting assets makes scanning easier

### Screen 5: Alpha Feed

It shows KOL/opinion snippets with:

- author
- recency
- text
- chart/image evidence
- related asset tag and price change

Product lesson:

- human/KOL interpretation can be a separate layer from raw event alerts
- raw event signals and commentary should not be mixed blindly

## Current Known Weaknesses

1. The live system is working, but sample size is still small.
2. Historical replay has been too BTC/macro-heavy.
3. Random news exports produce too much broad macro and benchmark pollution.
4. `other` buckets are hard to interpret.
5. BTC events can pollute abnormal_vs_btc; ETH events can pollute abnormal_vs_eth.
6. No mature market-regime filter yet.
7. Pre-event price-in checks are still incomplete.
8. Some current card templates may be too wordy for Telegram.
9. TG realtime stream may need ranked/digest products, not only individual pushes.
10. We do not yet have a strong definition of source usefulness beyond follow-up returns and basic quality gates.
11. Product may be drifting into "many scripts" instead of "one useful market radar."

## Current Product Hypothesis

The Telegram product should probably have multiple layers:

1. Realtime interrupt alerts:
   - rare
   - high confidence
   - strong magnitude
   - source-native first-hand signal

2. Watchlist/radar alerts:
   - useful but not urgent
   - can be rate-limited
   - can be grouped when many fire together

3. Scheduled digests:
   - morning: overnight important events
   - noon: morning market/chain changes
   - evening: day recap and what changed

4. Ranked market boards:
   - OI anomaly board
   - funding anomaly board
   - token unlock board
   - stablecoin/CEX netflow board
   - hot asset/KOL heat board if source exists

5. Deep detail cards:
   - security/hack reports
   - protocol exploit summaries
   - whale position context
   - major unlock context

We need your opinion on whether this is correct, incomplete, or wrong.

## What We Want From You

Give a serious product and architecture review. Be concrete. Do not give generic startup advice.

Please answer:

1. What is the strongest critique of the current product direction?
2. What should the TG product actually be: alert feed, radar board, digest product, or something else?
3. Which current pieces should be kept, cut, or deprioritized?
4. What should the information architecture be for Telegram?
5. What card templates should exist? Give concrete templates and field order.
6. Which events deserve realtime interrupt alerts vs digest-only handling?
7. How should alert severity/ranking work?
8. How should we avoid microcap garbage and false urgency?
9. What source classes should be prioritized next?
10. What source classes should be avoided for now?
11. How should we handle KOL/social heat without becoming a noise machine?
12. How should OI/funding/long-short/liquidation data be used?
13. How should token unlocks be ranked so they are useful?
14. How should Hyperliquid large-position alerts be presented so they are not misleading?
15. How should CEX netflow/stablecoin flow alerts be presented?
16. What should morning/noon/evening digests contain?
17. What metrics actually matter for this Telegram intelligence product?
18. What should be measured through historical replay, and what cannot be learned from historical replay?
19. Where should AI classification/rewrite be used, and where should deterministic rules be preferred?
20. What is the practical 7-day implementation plan?
21. What is the practical 30-day plan?
22. What should we explicitly not build yet?
23. What is the minimum product state where this is genuinely useful to a real crypto Telegram user?

Be direct and specific. If you think our current card style is still wrong, say what to replace it with. If you think we are over-indexing on backtests, say so. If you think we need a different mental model, give it.

