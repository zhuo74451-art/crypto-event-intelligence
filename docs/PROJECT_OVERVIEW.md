# Crypto Event Intelligence — Project Overview

## The Problem

加密信息流中存在几个常见混淆：

1. **新闻多，不等于可研究事件多。** 大量消息是重复、过时、缺乏资产归属或只有情绪价值的噪音。
2. **事实、叙事、价格反应、因果归因常被混为一谈。** 一条新闻发布后价格变动，不代表该新闻导致了变动。
3. **同一市场时点可能存在多个事件。** 多个事件共享同一价格路径时，价格回填无法自动分配各自贡献。
4. **单一巨鲸仓位不等于方向信号。** 巨鲸可能在对冲、套利或管理其他敞口。
5. **播报时间不一定等于事件发生时间。** 当前多数样本缺少可靠 event_time，因此只能把 broadcast_time 作为可审计的 t0。

本项目的核心顺序是：**先保存事实，再过滤噪音，再记录价格反应，最后才讨论归因。** 当前归因层尚未实现。

## Product Positioning

**Event intelligence and research infrastructure.**

This is NOT:
- A prediction engine or automated strategy
- A trading signal service
- A production-ready causal attribution system
- A replacement for fundamental or technical analysis

This IS:
- A structured pipeline for ingesting crypto events, standardizing source observations, applying deterministic gates, and retaining evidence
- A reproducible dataset linking event facts to auditable price observations
- A foundation for future interference and attribution research

## System Architecture

```text
Layer 1: Adapter
  Input:  Raw source data, fixture data, public API data, RSS
  Output: NormalizedSignal

Layer 2: Observation
  Input:  NormalizedSignal
  Output: One source-specific normalized Observation

Layer 3: Deterministic Noise Gate
  Input:  Observation
  Output: Rule-level NoiseGateResult values and aggregate pass/downgrade/reject state

Layer 4: Signal Registry
  Input:  Gate-approved Observation
  Output: A persistent Signal, or a merge into an existing event-level Signal

Layer 5: Event Intelligence Mapper
  Input:  SignalSpineResult
  Output: 观察 / 风险提示 / 禁止 / 丢弃

Layer 6: Dry Run Renderer
  Input:  Decision and evidence
  Output: JSON, Markdown, Telegram-style preview; no production send

Layer 7: Price Provider
  Input:  Asset and requested timestamp
  Output: PriceSnapshot with provider, candle time, lag, precision, and status

Layer 8: Price Observation Bundle
  Input:  Asset and broadcast_time
  Output: Asset/BTC/ETH snapshots at t0, 1h, 4h, and 24h

Layer 9: Raw Research Dataset
  Input:  Event Samples, Unique Price Observations, Sample-to-Observation Links
  Output: Unified raw dataset with no attribution conclusion
```

## Key Design Decisions

### Why retain both raw and normalized fields?

原始字段保存来源语境和审计证据；标准化字段用于跨来源比较。标准化值不能覆盖原始事实。

### Why t0 = broadcast_time?

对当前五条样本，broadcast_time 是唯一稳定、可验证的时间锚点。实际事件时间缺失，因此 `event_time_utc=null`，并明确记录 `t0_basis="broadcast_time"`。这是一项数据可用性选择，不代表播报时间等同于事件真正进入市场的时间。

### Why HYPE uses 15m candles?

Hyperliquid `candleSnapshot` 支持包括 1m、15m 在内的多个周期，但只保留有限数量的近期 Candle。对 2026-05-25 的历史样本，1m 保留范围不足，因此选择 15m 以覆盖目标日期。15m 是**历史覆盖选择**，不是接口的最细粒度。系统使用 `nearest_candle_open`，并保存 signed lag；本样本为 -120 秒。

### Why BTC/ETH use 1m candles?

Binance 公共 Kline 接口可覆盖目标日期的 1m 数据。系统使用 `first_after_target`，最大允许偏差 120 秒；当前样本实际为 0 秒。

### Why w1_003 and w1_004 share a price observation?

两条事件事实不同：
- `w1_003`：Binance BTC 流入和潜在卖压分析
- `w1_004`：Strategy 暂停购买 BTC 并处理可转换债务

但两者观察资产都是 BTC，播报时间也同为 `2026-05-25T16:12:00Z`。因此它们共享同一个市场价格观察，避免重复请求和自相矛盾的数据；事件样本本身仍保持独立，因为事件身份、事实和类型不同。

### Why price response is not attribution?

价格变化可能来自同时发生的其他事件、宏观因素、流动性和市场结构。当前系统只记录相关时间窗口的反应，不分配因果贡献。

### Why explicit fixture and network separation?

Fixture 只在显式 fixture 模式中使用，用于离线测试和演示。Network 模式失败时返回 `unavailable` / `network_error`，**绝不静默改用 fixture**。当前系统不存在把 `fixture_fallback` 冒充实网结果的路径。

## Current Achievements

| Component | Reference | SHA |
|-----------|-----------|-----|
| Main baseline | Signal Spine RC1 | `9c28c9308e42ea8ef822f7eff8a20c4b0e827290` |
| Manifest v1.1 | Week 1 sample manifest | `1f332992b2938a355e43f566d8901f00d01d842c` |
| Price code | Provider/provenance/cache | `d7b908d868957e0165924598e6058fef27eb0b3d` |
| Price data | Final network observations | `7188a52dedb54955cd41b187821081e1945c8706` |
| Raw dataset integration | Week 1 unified dataset | `2d7974bfaf38079de369b020a94f99a0ad807cd9` |

## Maturity Assessment

| Dimension | Rating | Notes |
|-----------|--------|-------|
| Engineering completeness | High for a research baseline | Core one-shot pipeline, validators, provenance, and tests exist; no daemon or deployment layer |
| Data completeness | Low to moderate | Five samples are enough to expose contract issues, not enough for statistical conclusions |
| Research methodology | Early | Price alignment is auditable; attribution and interference protocols are not yet defined |
| Product usability | Low | CLI and repository artifacts only; no UI or operator workflow |
| Production readiness | Not ready | No continuous operation, monitoring, long-run reliability evidence, or production integration |

**Engineering completion does not equal product completion, and price correlation does not equal event causality.**
