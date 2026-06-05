# Market Radar v1.12-E — All Fixed Card Local Dry-Run Pipeline Report

**Generated**: 2026-06-05 04:13:18 UTC+8
**Version**: v1.12-E
**Run ID**: 20260604_202718

---

## 概述

本报告证明 5 类固定卡片可以被统一入口 (`run_market_radar_v112e_all_fixed_card_local_pipeline.py`)
稳定产出，不是各自孤立通过，而是作为统一 pipeline 完成 dry-run 聚合。

所有卡片均使用本地 fixture 数据，未调用外部 API、未发送 TG、未启动 daemon。

## 固定卡片矩阵

| # | Card Type | Display Name | Readiness | Public Preview | Gate Tested | Live Ready |
|---|-----------|-------------|-----------|---------------|-------------|------------|
| 1 | `price_oi_volume_anomaly` | 多因子价格异动卡 | ✅ ready | ⚠️ fallback | ✅ | ❌ (fixture) |
| 2 | `whale_position_alert` | 巨鲸仓位警报卡 | ⚠️ partial | ✅ | ✅ | ❌ (fixture) |
| 3 | `liquidation_pressure` | 清算压力预警卡 | ⚠️ partial | ✅ | ✅ | ❌ (fixture) |
| 4 | `multi_asset_market_sync` | 多资产共振卡 | ⚠️ partial | ✅ | ✅ | ❌ (fixture) |
| 5 | `news_event_market_impact` | 新闻事件影响卡 | ⚠️ partial | ✅ | ✅ | ❌ (fixture) |

**计数**: Ready=1, Partial=4, Missing=0

---

## Public Preview 总数

- **public_preview_total**: 5
- **debug_leak_count**: 0
- **secret_leak_count**: 0

---

## ✅ 多因子价格异动卡 (`price_oi_volume_anomaly`)

### Readiness: ready

- **Public preview available**: False
- **Fallback preview available**: True
- **Gate tested**: True
- **Live ready**: False
- **Debug leaks**: 0
- **Secret leaks**: 0

### Output Summary

price_oi_volume_anomaly — READY: 0 public preview(s), schema complete, gate tested, fixture samples available. Monitoring gaps: OI/Volume delta real-time tracking, funding rate historical baseline, cross-exchange data consistency check.

---

## ⚠️ 巨鲸仓位警报卡 (`whale_position_alert`)

### Readiness: partial

- **Public preview available**: True
- **Fallback preview available**: False
- **Gate tested**: True
- **Live ready**: False
- **Debug leaks**: 0
- **Secret leaks**: 0

### Output Summary

whale_position_alert — PARTIAL (v112f enrichment active): 6 real public preview(s) from v112f local enrichment, 6 valid signals. fallback_preview=false. Address labels + historical position sequence available (local fixture). Missing: live data source, multi-address aggregation, real-time liquidation alerts.

### Missing Capabilities

- multi-address aggregation analysis (correlated address cluster detection)
- liquidation alert real-time push (trigger when < 5% from liquidation price)
- live Hyperliquid API data source (current: v112f local fixture enrichment)
- address label coverage for all on-chain wallets (current: 6 labels from fixture)

### Public Preview Sample

```
🟢 巨鲸仓位警报｜BTC 多头 新开仓位

🏷️ 地址标签：Smart Money Alpha
📌 钱包地址：`0x7a9f...6b8c`

● 资产：BTC
● 方向：多头
● 持仓规模：$5.20M
● 杠杆倍数：5.0x
● 仓位变化：+$5.20M
● 开仓均价：$87,200.50
● 当前价格：$88,650.00
● 未实现盈亏：+$86.80K（+1.7%）
● 清算价格：$69,800.00（距清算 21.3%）

📢 警报类型：新开仓位
💡 触发原因：仓位增加 $5.20M；大额持仓 $5.20M
🕐 观测时间：2026-06-04T19:45:00+08:00

🔗 行情查看：CoinGecko / DexScreener

⚠️ 仅供观察，不构成交易建议。巨鲸行为不保证方向正确性。
```

---

## ⚠️ 清算压力预警卡 (`liquidation_pressure`)

### Readiness: partial

- **Public preview available**: True
- **Fallback preview available**: False
- **Gate tested**: True
- **Live ready**: False
- **Debug leaks**: 0
- **Secret leaks**: 0

### Output Summary

liquidation_pressure — PARTIAL: 3 public preview(s) from 5 fixture snapshots, 3 valid signals. live_ready=false. Missing: real-time liquidation data source, liquidation heatmap, historical liquidation baseline.

### Public Preview Sample

```
⚠️ 清算压力｜BTC

一句话：BTC 下方多头清算压力升高，近1h 多头清算 $18.50M，下方清算密集区 $0.00，若价格继续回落可能放大短线波动。

● 当前价格：$63,500.00
● 近 1h 多头清算：$18.50M
● 近 1h 空头清算：$3.20M
● 近 24h 多头清算：$125.00M
● 近 24h 空头清算：$28.00M
● 未平仓合约：$18.50B
● 24h 成交量：$42.00B
● 观察窗口：1-4 小时

💡 触发原因：BTC 下方多头清算压力升高，近1h 多头清算 $18.50M，下方清算密集区 $0.00，若价格继续回落可能放大短线波动。

⚠️ 仅供观察，不构成交易建议。
```

---

## ⚠️ 多资产共振卡 (`multi_asset_market_sync`)

### Readiness: partial

- **Public preview available**: True
- **Fallback preview available**: False
- **Gate tested**: True
- **Live ready**: False
- **Debug leaks**: 0
- **Secret leaks**: 0

### Output Summary

multi_asset_market_sync — PARTIAL (v112g local correlation active): 5 real public preview(s) from v112g local correlation feed, 5 valid signals, 3 blocked. fallback_preview=false. Synchronized move score + direction agreement + sector/basket detection available (local fixture). Missing: live data source, real-time correlation matrix.

### Missing Capabilities

- real-time cross-asset correlation matrix (current: v112g local fixture correlation)
- live price data pipeline (current: v112g fixture snapshots)
- sector/track auto-expansion (DeFi, Meme, AI, RWA beyond current L1/L2/exchange/stablecoin)
- resonance strength decay tracking (signal persistence validation post-emission)
- intraday multi-snapshot comparison (distinguish intraday noise from trend resonance)

### Public Preview Sample

```
📈 多资产共振｜市场普涨共振 3个资产

一句话：检测到Layer 1板块3个资产同步上涨，平均涨跌幅+5.4%，同步异动得分92分（强烈），成交量放大96%，OI变化+8.5%。

● 共振类型：市场普涨共振
● 方向：同步上涨
● 主要资产：SOL、BTC、ETH
● 观测窗口：30分钟
● 平均涨跌幅：+5.37%
● 平均成交量变化：+96.0%
● 平均OI变化：+8.50%
● 同步异动得分：92/100
● 总清算金额：$165.00M
● 板块：Layer 1

🕐 观测时间：2026-06-04T14:30:00+08:00

🔗 行情查看：CoinGecko / DexScreener（BTC）

💡 触发原因：检测到Layer 1板块3个资产同步上涨，平均涨跌幅+5.4%，同步异动得分92分（强烈），成交量放大96%，OI变化+8.5%。

⚠️ 共振不代表趋势延续，可能为短期情绪驱动，不构成交易建议。
```

---

## ⚠️ 新闻事件影响卡 (`news_event_market_impact`)

### Readiness: partial

- **Public preview available**: True
- **Fallback preview available**: False
- **Gate tested**: True
- **Live ready**: False
- **Debug leaks**: 0
- **Secret leaks**: 0

### Output Summary

news_event_market_impact — PARTIAL: 5 public preview(s) from 7 fixture events, 5 valid signals. live_ready=false. Missing: live news RSS/API pipeline, auto event classification (NLP), auto affected-assets extraction, pricing model.

### Public Preview Sample

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

---

## Unfinished Items / Risks

- liquidation_pressure: 缺少实时清算数据源（当前仅 fixture）
- news_event_market_impact: 缺少实时新闻 RSS/API 接入管道（当前仅 fixture）
- whale_position_alert: 缺少地址标签自动标注和历史仓位序列追踪
- multi_asset_market_sync: 缺少跨资产实时相关性矩阵自动检测
- price_oi_volume_anomaly: OI/Volume delta 实时追踪待增强

---

## 执行约束确认

| 约束 | 状态 |
|------|------|
| real_tg_sent | false |
| external_api_called | false |
| external_ai_called | false |
| daemon_started | false |
| live_ready | false |
| debug_leak_count | 0 |
| secret_leak_count | 0 |
| token/key/cookie read | false |
| files_deleted | false |
