# Claude Review Request: Telegram Readability Failure

You are reviewing a real Telegram-first crypto intelligence product.

Be blunt. Do not flatter us. The current output is already in a Telegram group and the user said it is messy, hard to read, and not useful enough. We need a deeper critique and a redesign direction before continuing.

## Product Goal

We are building a crypto event intelligence system for Telegram.

It is not:

- a trading bot
- a copy-trading product
- an auto execution system
- a directional trade-signal product

It is:

- a filtered crypto/Web3 event intelligence feed
- focused on first-hand and fast second-hand market-relevant events
- delivered mainly through Telegram
- meant for users who check markets during China-time active periods
- should help users quickly understand what deserves attention

The user wants:

- high readability
- Chinese-first output
- less noise
- less manual work
- more useful Web3/trader-aware filtering
- no explicit trading instruction

## Current v0.9 Direction

After your previous advice, we moved from full-card feed toward:

1. ranked market radar board
2. rare interrupt alerts
3. scheduled digests
4. detail cards for high-severity items only

We implemented a first board generator and sent it to Telegram. The result was bad.

## Current Board Output Example

The Telegram board roughly looked like this:

```text
📊 盘中市场雷达｜05-28 15:26 UTC+8

🐋 Hyperliquid 大额仓位
1. HYPE 空头 $104.8M | loraclexyz 0x8def...2dae | 均价 45.37 | 强平 90.13 | 浮盈亏 -$22.8M
2. HYPE 多头 $80.0M | Unknown HYPE Whale 0x082e...ca88 | 均价 38.68 | 强平 49.07 | 浮盈亏 $26.6M
3. ETH 多头 $79.6M | Matrixport Related 0x6c85...84f6 | 均价 2,265.44 | 强平 1,355.89 | 浮盈亏 -$11.0M
4. BTC 多头 $34.9M | Unknown Hyperliquid Whale 0xebe8...885f | 均价 76,687.80 | 强平 62,125.76 | 浮盈亏 -$1.6M
5. BTC 空头 $34.3M | loraclexyz 0x8def...2dae | 均价 75,280.10 | 强平 208,113.29 | 浮盈亏 $941.1K

🔓 解锁雷达
1. HOME $18.3M | 流通占比 7.50% | 05-29 08:00 UTC+8 | Core Contributors:$12,219,942; Early Backe...

⚖️ 多空拥挤
1. DOGE 多头拥挤 | 分数 62.8 | 大户仓位比 2.1321 | 主动买卖比 0.8625
2. SOL 多头拥挤 | 分数 58.2 | 大户仓位比 1.8386 | 主动买卖比 1.1907
3. XRP 多头拥挤 | 分数 49.8 | 大户仓位比 1.7061 | 主动买卖比 0.9944
...

💧 资金/稳定币流向
1. USDT 交易所净流 $504.8M | Binance | cex_netflow_in
2. BTC 稳定币流动 $97.0M | Tether | stablecoin_treasury_in
3. BTC 稳定币流动 $51.8M | Tether | stablecoin_treasury_in

阅读方式：优先看金额、占比、是否新变化、是否多源共振。
⚠️ 仅作市场结构与链上情报观察，不构成任何交易建议。
```

## Current Detail Card Example

The old-style single card still appears:

```text
⚡ 【合约】麻吉黄立成ETH多单止盈

📌 事件：麻吉黄立成在HyperLiquid平台上减持ETH多单2306枚，约合465万美元。当前持仓规模为101.42万美元，均价为2094.83美元，当前市价为1988.60美元，清算价为1947.98美元。该交易员曾因蓝筹NFT获利，但今年活...
🕘 北京时间：2026-05-28 15:28:44
📡 来源：HyperInsight
🔎 类型：合约
🔥 强度：★★★★★

📝 详情：麻吉黄立成在HyperLiquid平台上减持ETH多单2306枚，约合465万美元。当前持仓规模为101.42万美元，均价为2094.83美元，当前市价为1988.60美元，清算价为1947.98美元。该交易员曾因蓝筹NFT获利，但今年活跃后自10月起连遭巨额回撤，资金从过亿缩水至数十万美元。

🧠 解读：合约仓位或杠杆结构发生变化，需结合价格、资金费率和清算分布复核。

⚠️ 提示：仅作链上/市场结构观察与研究记录，不构成任何交易建议。
```

## User's Immediate Complaints

The user said:

- Too messy.
- Poor readability.
- Users do not know what "score" means.
- Event and detail repeat the same text.
- The interpretation is meaningless.
- It feels like raw data dumped into Telegram, not an intelligence product.

## Additional Problems We Suspect

Please evaluate these and add others:

1. The board is too dense for a Telegram bubble.
2. Long technical rows wrap badly on mobile/desktop Telegram.
3. Some sections mix incomparable signals.
4. "Score" is backend math, not user language.
5. Raw source labels like `cex_netflow_in` should not appear.
6. Entity names like `Unknown HYPE Whale 0x...` may be too noisy.
7. English allocation strings inside Chinese message feel unpolished.
8. Floating PnL on whale positions may mislead users or distract from the actual signal.
9. If everything is ranked, nothing feels important.
10. A board may need fewer sections or a different hierarchy.
11. Maybe Telegram should receive one compact headline plus separate detail thread messages.
12. Maybe the board should show only top 3 and put the rest in archive.
13. Maybe "why this matters" should be replaced by one concrete next-observation line.
14. Maybe all user-facing output needs an explicit template taxonomy.

## What We Need From You

Give a critical product/readability review and concrete redesign.

Please answer:

1. What is fundamentally wrong with the current board?
2. What is fundamentally wrong with the current detail card?
3. What should a Telegram market radar message look like on mobile?
4. Should we keep a single board, split into multiple small boards, or use digest + rare alert only?
5. Which fields should be hidden from users?
6. Which fields should be renamed into user language?
7. How many rows per section are reasonable?
8. Which sections should be shown in the main group, and which should be detail/archive only?
9. How should Hyperliquid positions be presented without looking like copy-trade bait?
10. How should long-short/funding/crowding data be presented without unexplained scores?
11. How should token unlocks be presented cleanly?
12. How should CEX/stablecoin flows be presented cleanly?
13. What should replace the current meaningless "解读" paragraph?
14. What are 3-5 concrete user-facing templates we should implement next?
15. Give a strict checklist for every Telegram message before sending.
16. What should we immediately stop sending?
17. What should the next 48 hours of engineering focus on?

Be specific. Give examples in Chinese where possible. Do not just agree with the user; identify deeper product problems and tradeoffs.
