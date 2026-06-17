# Week 1 — Sample Fact Manifest v1.1 (Corrected)

**Baseline Commit:** `9547b7062d7ab986288b35737623fc32c7dd1435`  
**Correction Commit:** `d142ec6`  
**Created:** 2026-06-16  
**Corrected:** 2026-06-16  
**Branch:** `workbench/week1-sample-manifest-v1`  
**File:** `research/week1_samples_v1.json`

---

## Corrections Applied (v1 → v1.1)

| # | Correction | Status |
|---|-----------|--------|
| 1 | Notion page IDs and URLs filled for all 5 samples | ✅ |
| 2 | `raw_summary` replaced with verbatim Notion original text | ✅ |
| 3 | Raw + normalized field separation (`_raw` / `_normalized`) | ✅ |
| 4 | `existing_*` fields marked as `deprecated_alias` | ✅ |
| 5 | `existing_ai_confidence_raw` added | ✅ |
| 6 | HYPE provider rationale corrected (15m is retention choice, not finest) | ✅ |
| 7 | Sample IDs unified to `w1_001`–`w1_005` (no secondary IDs) | ✅ |

---

## Purpose

Five manually selected real event samples from 2026-05-25 for week 1 post-event price backfill validation. These samples serve as the ground-truth dataset for the Signal Spine v1 price backfill module.

Each sample documents:
- The **broadcast time** (used as t0)
- The **Notion raw values** (preserved verbatim) and **normalized values** (derived via canonical mapping)
- The **source and quality** (honestly marked as single-source)
- The **price provider plan** (which API and interval to use)
- All **known limitations** (documented, not hidden)

---

## Sample Overview

| # | sample_id | title | asset | type | decision (raw) | direction (raw) |
|---|-----------|-------|-------|------|---------------|-----------------|
| 1 | w1_001 | Loracle HYPE空单浮亏扩大 | HYPE | 巨鲸/链上 | 观察 | 不确定 |
| 2 | w1_002 | 麻吉黄立成增持ETH多单 | ETH | 巨鲸/链上 | 仅风险提示 | 不确定 |
| 3 | w1_003 | Binance近10天BTC流入增加 | BTC | 巨鲸/链上 | 仅风险提示 | 利空 |
| 4 | w1_004 | Strategy暂停BTC购买 | BTC | ETF/机构 | 观察 | 利空 |
| 5 | w1_005 | WTI原油期货暴跌6% | WTI (→BTC/ETH) | 宏观数据 | 观察 | 不确定 |

---

## t0 Policy

All samples use **`broadcast_time_utc`** as t0.

`event_time_utc` is explicitly `null` for all samples because the actual event occurrence time is unknown — only the broadcast time is recorded.

| Field | Value | Rationale |
|-------|-------|-----------|
| `t0_basis` | `broadcast_time` | Only the broadcast timestamp is available |
| `event_time_utc` | `null` | Actual event time is not known |
| `event_time_status` | `unavailable` | Transparent admission of unknown |

---

## Normalization Mapping

Raw Notion values are preserved as `_raw` fields and mapped to canonical `_normalized` values via this deterministic mapping:

| Field | Raw (Notion) | Normalized |
|-------|-------------|------------|
| `news_quality` | `A 结构性` | `structural` |
| `news_quality` | `B 注意力` | `attention` |
| `trade_relevance` | `高` | `high` |
| `trade_relevance` | `中` | `medium` |
| `trade_relevance` | `低` | `low` |
| `decision` | `观察` | `observe` |
| `decision` | `仅风险提示` | `risk_tip` |
| `decision` | `禁止` | `block` |
| `decision` | `丢弃` | `discard` |
| `direction` | `利空` | `bearish` |
| `direction` | `不确定` | `uncertain` |
| `pump_risk` | `高` | `high` |
| `pump_risk` | `中` | `medium` |
| `pump_risk` | `低` | `low` |

---

## Price Provider Plan

| Asset | Provider | Interval | Rationale |
|-------|----------|----------|-----------|
| **HYPE** | Hyperliquid `candleSnapshot` | 15m | Not on Binance. Hyperliquid supports both 1m and 15m; 15m is chosen for retention-range coverage of historical data. `candleSnapshot` only provides a limited recent window. |
| **ETH** | Binance Kline | 1m | `ETHUSDT` pair, deep liquidity |
| **BTC** | Binance Kline | 1m | `BTCUSDT` pair, deep liquidity |
| **WTI** | — | — | Macro events: do NOT request WTI. Only backfill BTC and ETH benchmarks. |

---

## Raw Summary Verification

Each `raw_summary` is the verbatim Notion original text, not paraphrased:

| Sample | Verbatim Raw Summary |
|--------|---------------------|
| w1_001 | 知名交易员Loracle的HYPE空单浮亏扩大至约3146万美元，持仓规模约1.13亿美元，均价45.35美元，当前币价62.78美元，清算价89.17美元。 |
| w1_002 | 麻吉黄立成在HyperLiquid增持ETH多单921.47枚，持仓规模约1355.56万美元，均价2097.23美元，清算价2068.80美元。 |
| w1_003 | 分析师称Binance近10天BTC强劲流入，周均流入从378 BTC升至1190 BTC，5月18日单日流入超3600 BTC，储备量增加16000 BTC。 |
| w1_004 | Strategy本周暂停比特币购买，转而购入债券并计划回购近15亿美元可转换债务；Saylor提到未来可能小规模出售部分BTC。 |
| w1_005 | WTI原油期货日内暴跌6%，报90.80美元/桶。 |

---

## Notion Page References

| Sample | Notion Page ID | URL |
|--------|---------------|-----|
| w1_001 | `36b0246231d381ce899becc2bbb1ff7c` | https://app.notion.com/p/36b0246231d381ce899becc2bbb1ff7c |
| w1_002 | `36b0246231d3815ba165d11100396df5` | https://app.notion.com/p/36b0246231d3815ba165d11100396df5 |
| w1_003 | `36b0246231d381d29130d2ff58f3efee` | https://app.notion.com/p/36b0246231d381d29130d2ff58f3efee |
| w1_004 | `36b0246231d3810cb1e2d5cf7dceeb90` | https://app.notion.com/p/36b0246231d3810cb1e2d5cf7dceeb90 |
| w1_005 | `36b0246231d381faa258d757ca47da18` | https://app.notion.com/p/36b0246231d381faa258d757ca47da18 |

---

## Data Integrity Constraints

### What we DID NOT do

| Prohibited Action | Status | Evidence |
|------------------|--------|----------|
| Fabricate original publish time | ✅ Not done | All `event_time_utc` are `null`, status=`unavailable` |
| Fabricate second verification source | ✅ Not done | All `source_count` are honestly `1` |
| Pre-fill price data | ✅ Not done | Only provider plans are documented |
| Judge causality | ✅ Not done | `known_limitations` explicitly note no causal claims |
| Modify original Notion conclusion | ✅ Not done | `_raw` fields preserve verbatim Notion values; `_normalized` fields are derived via deterministic mapping |
| Hide unknown fields | ✅ Not done | All unknowns are `null`, `unavailable`, or documented |

---

## Field Reference

Every sample in `week1_samples_v1.json` contains these fields:

| Field | Type | Always Present | Description |
|-------|------|---------------|-------------|
| `sample_id` | string | ✅ | `w1_001` through `w1_005` |
| `notion_page_id` | string | ✅ | Notion page ID (all 5 filled) |
| `notion_page_url` | string | ✅ | Full Notion page URL |
| `title` | string | ✅ | Short event title |
| `raw_summary` | string | ✅ | Verbatim Notion original text |
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
| `existing_news_quality_raw` | string | ✅ | Original Notion value |
| `existing_news_quality_normalized` | string | ✅ | Mapped via canonical normalization |
| `existing_trade_relevance_raw` | string | ✅ | Original Notion value |
| `existing_trade_relevance_normalized` | string | ✅ | Mapped via canonical normalization |
| `existing_decision_raw` | string | ✅ | Original Notion value |
| `existing_decision_normalized` | string | ✅ | Mapped via canonical normalization |
| `existing_direction_raw` | string | ✅ | Original Notion value |
| `existing_direction_normalized` | string | ✅ | Mapped via canonical normalization |
| `existing_pump_risk_raw` | string | ✅ | Original Notion value |
| `existing_pump_risk_normalized` | string | ✅ | Mapped via canonical normalization |
| `existing_ai_confidence_raw` | int | ✅ | Original AI confidence score |
| `existing_news_quality` | object | ✅ | `deprecated_alias` — use `_normalized` |
| `existing_trade_relevance` | object | ✅ | `deprecated_alias` — use `_normalized` |
| `existing_decision` | object | ✅ | `deprecated_alias` — use `_normalized` |
| `existing_direction` | object | ✅ | `deprecated_alias` — use `_normalized` |
| `existing_pump_risk` | object | ✅ | `deprecated_alias` — use `_normalized` |
| `price_provider_plan` | string | ✅ | Which API and why |
| `price_interval_plan` | string | ✅ | Kline interval |
| `known_limitations` | string[] | ✅ | Documented caveats |
| `manual_review_notes` | string | ✅ | Free-text notes |

---

## Reading the JSON

```python
import json

with open("research/week1_samples_v1.json") as f:
    data = json.load(f)

print(f"Manifest v{data['manifest']['manifest_version']}: {data['manifest']['title']}")

for s in data["samples"]:
    print(f"  {s['sample_id']}: {s['title'][:30]}...")
    print(f"    raw_decision: {s['existing_decision_raw']}")
    print(f"    normalized_decision: {s['existing_decision_normalized']}")
    print(f"    notion: {s['notion_page_id']}")
```

Expected output:
```
Manifest v1.1: Week 1 — Signal Spine Sample Fact Manifest
  w1_001: Loracle HYPE空单浮亏扩大，持仓...
    raw_decision: 观察
    normalized_decision: observe
    notion: 36b0246231d381ce899becc2bbb1ff7c
  w1_002: 麻吉黄立成增持ETH多单921.47枚...
    raw_decision: 仅风险提示
    normalized_decision: risk_tip
    notion: 36b0246231d3815ba165d11100396df5
  ...
```
