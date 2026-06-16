# Crypto Event Intelligence — Project Overview

## The Problem

加密信息流中存在几个常见混淆：

1. **新闻多，不等于可交易事件多。** 大量消息是重复、过时或无资产归属的噪音。
2. **事实、叙事、价格反应、因果归因常被混为一谈。** 一条新闻发布后价格变动，不一定由该新闻导致。
3. **同一市场时点可能有多个事件。** BTC 同时出现 ETF 新闻和巨鲸转移，不能自动归因给其中之一。
4. **单一巨鲸仓位不等于方向信号。** 巨鲸可能在做对冲或套利，而非方向性押注。
5. **原始播报时间不一定等于事件发生时间。** 链上交易发生在区块时间，新闻发布在记者编写时间，两者可能相差数小时。

本项目的核心任务是：**先整理事实，再观察价格反应，最后才讨论归因。** 归因层尚未实现。

## Product Positioning

**Event intelligence and research infrastructure.**

This is NOT:
- A prediction engine or automated strategy
- A trading signal service
- A fully productionized causal attribution system
- A replacement for fundamental or technical analysis

This IS:
- A structured pipeline for ingesting crypto events, filtering noise, standardizing observations, and recording price reactions
- A reproducible, evidence-based research dataset
- A foundation for future attribution research

## System Architecture

Each layer's responsibility and data flow:

```
Layer 1: Adapter
  Input:  Raw data (fixture dict, Binance API, Hyperliquid API, RSS feeds)
  Output: NormalizedSignal
  
Layer 2: Observation
  Input:  NormalizedSignal
  Output: Observation (standardized event record)
  
Layer 3: Noise Gate
  Input:  Observation
  Output: GatedDecision (allow / block)
  
Layer 4: Signal Registry
  Input:  Approved observations
  Output: Persistent, deduplicated Signal records
  
Layer 5: Event Intelligence Mapper
  Input:  Signal
  Output: FinalDecision (观察 / 风险提示 / 禁止 / 丢弃)
  
Layer 6: Dry Run Renderer
  Input:  FinalDecision + NormalizedSignal
  Output: JSON + Markdown + Telegram-style card (never sent)
  
Layer 7: Price Provider
  Input:  Asset + timestamp
  Output: PriceSnapshot (with provenance)
  
Layer 8: Price Observation Bundle
  Input:  Asset + broadcast_time
  Output: 12 snapshots (asset/btc/eth × t0/1h/4h/24h)
  
Layer 9: Raw Research Dataset
  Input:  Event Samples + Price Observations
  Output: Unified research dataset (no attribution)
```

## Key Design Decisions

### Why retain both raw and normalized fields?

原始标签反映来源语境，标准化标签便于跨来源对比。两者并存不冲突。

### Why t0 = broadcast_time?

事件播报时间是唯一可验证的外部时间锚点。事件真实发生时间（event_time_utc）在多数来源中缺失，设为 null。

### Why HYPE uses 15m candles?

Hyperliquid 公开历史数据仅提供 15m 粒度。精度 900 秒，选择 nearest_candle_open 策略，最大滞后 450 秒。

### Why BTC/ETH use 1m candles?

Binance 免费公开 API 提供 1m Kline。选择 first_after_target 策略，最大滞后 120 秒。

### Why w1_003 / w1_004 share a price observation?

两个事件样本（w1_003：Binance 转入 10K BTC；w1_004：Strategy 发行可转债）发生在同一 BTC 市场时点 2026-05-25T16:12:00Z，共用同一个价格观察。事件样本不合并，因为它们的 subject 不同。

### Why price response ≠ attribution?

价格变动可能是该事件导致，也可能是同时发生的其他事件、宏观因素或市场噪音导致。当前数据集仅记录价格反应，不做因果归因。 attribution layer 尚未实现。

### Why explicit fixture vs. network separation?

Fixture 模式使用预置确定性数据，用于测试和演示。Network 模式使用真实 API 数据，不会在失败时静默回退到 fixture。这是审计关键：数据来源必须可追溯。

### Why no silent fallback?

如果网络失败时自动使用 fixture，测试者无法区分真实结果和测试数据。所有降级模式都明确标记 source=fixture_fallback 或 source=network_error。

## Current Achievements

| Component | Commit | SHA |
|-----------|--------|-----|
| Main baseline | signal-spine-v1-rc1 | `9c28c9308e42ea8ef822f7eff8a20c4b0e827290` |
| Manifest v1.1 | week1-sample-manifest-v1 | `1f332992b2938a355e43f566d8901f00d01d842c` |
| Price code | week1-price-providers-v1 | `d7b908d868957e0165924598e6058fef27eb0b3d` |
| Price data | week1-price-providers-v1 | `7188a52dedb54955cd41b187821081e1945c8706` |
| Raw dataset integration | week1-raw-dataset-v1 | `2d7974bfaf38079de369b020a94f99a0ad807cd9` |

## Maturity Assessment

| Dimension | Rating | Notes |
|-----------|--------|-------|
| Engineering completeness | ⚠️ High for pipeline, low for daemon | Core pipeline solid; daemon/deploy not implemented |
| Data completeness | ⚠️ Moderate | 5 samples sufficient for protocol design, not for statistics |
| Research methodology | ⚠️ Early | Price backfill is sound; attribution methodology not yet designed |
| Product usability | ❌ Low | CLI only; no UI, no dashboard, no API |
| Production readiness | ❌ Not ready | No daemon, no monitoring, no error recovery, no Notion sync |

Engineering completion ≠ product completion. 管道完整不意味着系统可以投入生产。
