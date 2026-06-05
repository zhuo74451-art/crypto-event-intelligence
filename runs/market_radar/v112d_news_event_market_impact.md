# Market Radar v1.12-D — News Event Market Impact Local Feed 报告

**Generated**: 2026-06-04 22:32:39 UTC+8
**Version**: v1.12-D
**Mode**: news_event_market_impact_local_feed

---

## 概述

本报告执行 news_event_market_impact 本地新闻事件适配层的完整运行，
使用本地 fixture + 规则分类器 + public card 渲染，将 news_event_market_impact
从 missing 推进到 partial。

### 执行约束

| 约束 | 状态 |
|------|------|
| 外部 API 调用 | ❌ 未调用 |
| 外部 AI/LLM 调用 | ❌ 未调用 |
| TG 发送 | ❌ 未发送 |
| Daemon/Loop/Cron | ❌ 未启动 |
| Token/Key/Cookie 读取 | ❌ 未读取 |
| live_ready 标记 | ❌ false |

---

## Ready-to-Send Signal 统计

| 指标 | 值 |
|------|----|
| 总事件数 | 7 |
| Valid signals | 5 |
| Blocked signals | 2 |
| Public cards | 5 |
| Debug leaks | 0 |

---

## Valid Signals

### 1. news_001_etf_fund_flow

| 字段 | 值 |
|------|----|
| Category | etf_flow |
| Affected Assets | BTC |
| Impact Direction | bullish |
| Debug Leak Free | True |
| Public Card Length | 436 chars |

```
📊 新闻事件｜BlackRock Bitcoin ETF Sees $420M Inflows, Largest Single-Day Since March

🟢 市场影响方向：偏多

ETF类型事件，影响 BTC。

● 事件分类：ETF资金流向
● 受影响资产：BTC
● 来源：CoinDesk
● 发布时间：2026-06-04T14:30:00Z
● 交易相关性：高
● 是否已被定价：部分已定价

🔗 行情查看：[CoinGecko](https://www.coingecko.com/search?query=BTC) / [DexScreener](https://dexscreener.com/search?q=BTC)

📎 原文链接：https://www.coindesk.com/markets/2026/06/04/blackrock-bitcoin-etf-inflows

⚠️ 新闻事件可能已被市场定价，请独立判断，不构成交易建议。
```

### 2. news_002_regulation_policy

| 字段 | 值 |
|------|----|
| Category | regulation_policy |
| Affected Assets | DEFI, ETH |
| Impact Direction | bullish |
| Debug Leak Free | True |
| Public Card Length | 427 chars |

```
🏛️ 新闻事件｜EU Parliament Passes Stricter DeFi KYC Rules, Effective January 2027

🟢 市场影响方向：偏多

政策类型事件，影响 DEFI / ETH。

● 事件分类：监管政策
● 受影响资产：DEFI, ETH
● 来源：The Block
● 发布时间：2026-06-04T10:15:00Z
● 交易相关性：高
● 是否已被定价：未定价

🔗 行情查看：[CoinGecko](https://www.coingecko.com/search?query=DEFI) / [DexScreener](https://dexscreener.com/search?q=DEFI)

📎 原文链接：https://www.theblock.co/post/2026/06/04/eu-defi-kyc-rules

⚠️ 新闻事件可能已被市场定价，请独立判断，不构成交易建议。
```

### 3. news_003_security_exploit

| 字段 | 值 |
|------|----|
| Category | security_exploit |
| Affected Assets | ARB, ETH, USDC |
| Impact Direction | bearish |
| Debug Leak Free | True |
| Public Card Length | 454 chars |

```
🔒 新闻事件｜Arbitrum Bridge Exploit Drains $47M in ETH and USDC — Team Confirms Investigation

🔴 市场影响方向：偏空

安全类型事件，影响 ARB / ETH / USDC。

● 事件分类：安全事件
● 受影响资产：ARB, ETH, USDC
● 来源：PeckShield
● 发布时间：2026-06-04T08:45:00Z
● 交易相关性：高
● 是否已被定价：未定价

🔗 行情查看：[CoinGecko](https://www.coingecko.com/search?query=ARB) / [DexScreener](https://dexscreener.com/search?q=ARB)

📎 原文链接：https://twitter.com/PeckShieldAlert/status/1800000000000000001

⚠️ 新闻事件可能已被市场定价，请独立判断，不构成交易建议。
```

### 4. news_004_exchange_listing

| 字段 | 值 |
|------|----|
| Category | exchange_event |
| Affected Assets | BNB, HYPE, USDT |
| Impact Direction | bullish |
| Debug Leak Free | True |
| Public Card Length | 465 chars |

```
🏦 新闻事件｜Binance to List Hyperliquid (HYPE) with USDT Perpetual Contracts at 14:00 UTC

🟢 市场影响方向：偏多

上线类型事件，影响 BNB / HYPE / USDT。

● 事件分类：交易所事件
● 受影响资产：BNB, HYPE, USDT
● 来源：Binance
● 发布时间：2026-06-04T12:00:00Z
● 交易相关性：高
● 是否已被定价：部分已定价

🔗 行情查看：[CoinGecko](https://www.coingecko.com/search?query=BNB) / [DexScreener](https://dexscreener.com/search?q=BNB)

📎 原文链接：https://www.binance.com/en/support/announcement/hype-usdt-perpetual-listing

⚠️ 新闻事件可能已被市场定价，请独立判断，不构成交易建议。
```

### 5. news_005_macro_liquidity

| 字段 | 值 |
|------|----|
| Category | macro_liquidity |
| Affected Assets | BTC, DXY, ETH |
| Impact Direction | bullish |
| Debug Leak Free | True |
| Public Card Length | 472 chars |

```
🌍 新闻事件｜Fed Signals Rate Cut Likely in July as Inflation Cools to 2.4% — DXY Drops Below 100

🟢 市场影响方向：偏多

宏观类型事件，影响 BTC / DXY / ETH。

● 事件分类：宏观流动性
● 受影响资产：BTC, DXY, ETH
● 来源：Reuters
● 发布时间：2026-06-04T06:00:00Z
● 交易相关性：高
● 是否已被定价：未定价

🔗 行情查看：[CoinGecko](https://www.coingecko.com/search?query=BTC) / [DexScreener](https://dexscreener.com/search?q=BTC)

📎 原文链接：https://www.reuters.com/markets/rates-bonds/fed-signals-july-rate-cut-2026-06-04/

⚠️ 新闻事件可能已被市场定价，请独立判断，不构成交易建议。
```

---

## Blocked Signals

- **news_006_invalid_no_assets**: 交易相关性为「极低」；无法提取受影响资产；分类未知且无明确受影响资产 (category=unknown)
- **news_007_invalid_already_priced**: 交易相关性为「极低」；事件已被市场完全定价 (category=unknown)

---

## Readiness 矩阵变化

| 字段 | Before | After |
|------|--------|-------|
| news_event_market_impact | missing | partial |

### 固定卡片矩阵

| Card Type | Readiness |
|-----------|-----------|
| liquidation_pressure | ❌ missing |
| multi_asset_market_sync | ⚠️ partial |
| news_event_market_impact | ⚠️ partial |
| price_oi_volume_anomaly | ✅ ready |
| whale_position_alert | ⚠️ partial |

**Ready=1, Partial=3, Missing=1**

---

## 风险说明

1. 所有事件均为 fixture 样本，不代表真实市场事件。
2. 规则分类器基于关键词匹配，准确率有限，实盘需 NLP 增强。
3. affected_assets 提取基于名称映射和 ticker 正则，可能遗漏非主流资产。
4. impact_direction 判断基于分类默认值 + 简单情感词计数，不构成交易建议。
5. fixture 不标记为 live_ready=true，禁止进入真实发送管道。
