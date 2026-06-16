# Week 1 — Sample Fact Manifest v1

**Baseline Commit:** `9547b7062d7ab986288b35737623fc32c7dd1435`  
**Created:** 2026-06-16  
**Branch:** `workbench/week1-sample-manifest-v1`  
**File:** `research/week1_samples_v1.json`

---

## Purpose

Five manually selected real event samples from 2026-05-25 for week 1 post-event price backfill validation. These samples serve as the ground-truth dataset for the Signal Spine v1 price backfill module.

Each sample documents:
- The **broadcast time** (used as t0)
- The **source and quality** (honestly marked as single-source)
- The **existing human decision** (preserved, not modified)
- The **price provider plan** (which API and interval to use)
- All **known limitations** (documented, not hidden)

---

## Sample Overview

| # | sample_id | title | asset | type | decision | direction |
|---|-----------|-------|-------|------|----------|-----------|
| 1 | w1_001 | Loracle HYPE空单浮亏扩大 | HYPE | 巨鲸/链上 | 观察 | bearish |
| 2 | w1_002 | 麻吉黄立成增持ETH多单 | ETH | 巨鲸/链上 | 仅风险提示 | bullish |
| 3 | w1_003 | Binance近10天BTC流入增加 | BTC | 巨鲸/链上 | 仅风险提示 | bearish |
| 4 | w1_004 | Strategy暂停BTC购买 | BTC | ETF/机构 | 观察 | bearish |
| 5 | w1_005 | WTI原油期货暴跌6% | WTI → BTC/ETH | 宏观数据 | 观察 | neutral |

---

## t0 Policy

All samples use **`broadcast_time_utc`** as t0.

`event_time_utc` is explicitly `null` for all samples because the actual event occurrence time is unknown — only the broadcast time is recorded.

| Field | Value | Rationale |
|-------|-------|-----------|
| `t0_basis` | `broadcast_time` | Only the broadcast timestamp is available |
| `event_time_utc` | `null` | Actual event time is not known |
| `event_time_status` | `unavailable` | Transparent admission of unknown |

This means:
- **Whale position samples** (w1_001, w1_002): The actual position change may have occurred hours before broadcast
- **Trend analysis** (w1_003): The BTC inflow trend spans 10 days — t0 at broadcast time may not capture the trend's actual start
- **Company announcement** (w1_004): The company may have announced before the Chinese source picked it up
- **Macro event** (w1_005): WTI crude may have been falling for hours before the broadcast

These are documented in each sample's `known_limitations`.

---

## Price Provider Plan

| Asset | Provider | Interval | Notes |
|-------|----------|----------|-------|
| **HYPE** | Hyperliquid `candleSnapshot` | 15m | Not on Binance. Hyperliquid native API only. 15m is the finest available. |
| **ETH** | Binance Kline | 1m | `ETHUSDT` pair, standard endpoint |
| **BTC** | Binance Kline | 1m | `BTCUSDT` pair, standard endpoint |
| **WTI** | — | — | Macro events: do NOT request WTI. Only backfill BTC and ETH benchmarks. |

### Why HYPE uses 15m instead of 1m

HYPE is not listed on Binance. Hyperliquid's public `candleSnapshot` API endpoint provides OHLC data at 15m intervals (minimum). This means:
- t0 precision is **±7.5 minutes** vs **±30 seconds** for Binance 1m klines
- The wider window reduces sensitivity to short-term price movements
- If `candleSnapshot` is unavailable, candidates are DexScreener or Hyperliquid REST API

---

## Data Integrity Constraints

### What we DID NOT do

| Prohibited Action | Status | Evidence |
|------------------|--------|----------|
| Fabricate original publish time | ✅ Not done | All `event_time_utc` are `null` |
| Fabricate second verification source | ✅ Not done | All `source_count` are honestly `1` |
| Pre-fill price data | ✅ Not done | Only provider plans are documented |
| Judge causality | ✅ Not done | `known_limitations` explicitly note no causal claims |
| Modify original human conclusion | ✅ Not done | `existing_decision` preserves original values |
| Hide unknown fields | ✅ Not done | All unknowns are `null`, `unavailable`, or documented |

### Quality Summary

| Sample | source_count | event_time_status | news_quality | trade_relevance | Pump Risk |
|--------|-------------|-------------------|-------------|-----------------|-----------|
| w1_001 | 1 | unavailable | medium | medium | low |
| w1_002 | 1 | unavailable | medium | high | low |
| w1_003 | 1 | unavailable | low | high | low |
| w1_004 | 1 | unavailable | medium | high | low |
| w1_005 | 1 | unavailable | medium | medium | low |

---

## Field Reference

Every sample in `week1_samples_v1.json` contains these fields:

| Field | Type | Always Present | Description |
|-------|------|---------------|-------------|
| `sample_id` | string | ✅ | `w1_001` through `w1_005` |
| `notion_page_id` | string\|null | ✅ | `null` for now — not yet linked to Notion |
| `title` | string | ✅ | Short event title |
| `raw_summary` | string | ✅ | Original broadcast text (paraphrased) |
| `broadcast_time_utc` | string (ISO) | ✅ | t0 timestamp |
| `event_time_utc` | null | ✅ | Always `null` |
| `event_time_status` | string | ✅ | Always `"unavailable"` |
| `t0_basis` | string | ✅ | Always `"broadcast_time"` |
| `event_type` | string | ✅ | Category tag |
| `subject_asset` | string | ✅ | Primary asset |
| `observation_assets` | string[] | ✅ | Assets to observe |
| `benchmark_assets` | string[] | ✅ | Assets for benchmark returns |
| `source_label` | string | ✅ | Source attribution |
| `source_count` | integer | ✅ | Number of sources (honest) |
| `source_quality_status` | string | ✅ | Human quality note |
| `existing_news_quality` | string | ✅ | Preserved original value |
| `existing_trade_relevance` | string | ✅ | Preserved original value |
| `existing_decision` | string | ✅ | Preserved original value |
| `existing_direction` | string | ✅ | Preserved original value |
| `existing_pump_risk` | string | ✅ | Preserved original value |
| `price_provider_plan` | string | ✅ | Which API and why |
| `price_interval_plan` | string | ✅ | Kline interval |
| `known_limitations` | string[] | ✅ | Documented caveats |
| `manual_review_notes` | string | ✅ | Free-text notes |

---

## Reading the JSON

The JSON file is designed to be consumed programmatically:

```python
import json

with open("research/week1_samples_v1.json") as f:
    data = json.load(f)

print(f"Manifest: {data['manifest']['title']}")
print(f"Samples: {len(data['samples'])}")

for sample in data["samples"]:
    print(f"  {sample['sample_id']}: {sample['title']}")
    print(f"    t0: {sample['broadcast_time_utc']}")
    print(f"    asset={sample['subject_asset']}, decision={sample['existing_decision']}")
```

Expected output:
```
Manifest: Week 1 — Signal Spine Sample Fact Manifest
Samples: 5
  w1_001: Loracle HYPE空单浮亏扩大，持仓规模达1.13亿美元
    t0: 2026-05-25T13:02:00Z
    asset=HYPE, decision=观察
  w1_002: 麻吉黄立成增持ETH多单921.47枚，清算价接近现价
    t0: 2026-05-25T15:19:00Z
    asset=ETH, decision=仅风险提示
  w1_003: Binance近10天BTC流入显著增加，比特币面临卖出信号
    t0: 2026-05-25T16:12:00Z
    asset=BTC, decision=仅风险提示
  w1_004: Strategy本周暂停比特币购买，转而回购可转换债务
    t0: 2026-05-25T16:12:00Z
    asset=BTC, decision=观察
  w1_005: WTI原油期货日内暴跌6%
    t0: 2026-05-25T11:34:00Z
    asset=WTI, decision=观察
```
