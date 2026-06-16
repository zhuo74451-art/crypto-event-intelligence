# Development Set Summary — Week 1

## Overview

| Metric | Value |
|--------|-------|
| Total cases | 5 |
| Point-event eligible | 3 (w1_001, w1_002, w1_004) |
| Routed (non-point-event) | 2 (w1_003, w1_005) |
| Data insufficient | 0 |
| Batch validation | PASS (0 violations) |
| Protocol validator | PASS |
| Focused tests | 83/83 PASS |
| Full regression | 316/316 PASS |
| Sealed protocol modified | false |

## Case Details

### w1_001 — Loracle HYPE空单浮亏扩大

| Field | Value |
|-------|-------|
| Information form | discrete_observable_action |
| Source medium | onchain_data_feed |
| Routing | point_event_study |
| Objects created | All 8 |
| Target asset | HYPE |
| Selected clock | information_clock |
| Actual time basis | broadcast_time |
| Primary benchmark | BTC (weak proxy) |
| Price provider | Hyperliquid 15m candleSnapshot |
| Pre-event movement | -1.2087% (detected) |
| Raw 1h reaction | +1.1276% |
| Benchmark reaction (BTC) | -0.0616% |
| Relative reaction | +1.1892% |
| Hard gates | 3 pass / 4 unknown |
| Attribution verdict | insufficient_evidence |
| Unresolved P0/P1/P2 | 0/3/3 |
| Protocol friction | 5 items (see protocol_friction_log.md) |
| **Status** | ✅ Complete |

### w1_002 — 麻吉黄立成增持ETH多单

| Field | Value |
|-------|-------|
| Information form | discrete_observable_action |
| Source medium | onchain_data_feed |
| Routing | point_event_study |
| Objects created | All 8 |
| Target asset | ETH |
| Selected clock | information_clock |
| Actual time basis | broadcast_time |
| Primary benchmark | BTC |
| Price provider | Binance 1m klines (ETHUSDT) |
| Pre-event movement | +0.3779% (detected) |
| Raw 1h reaction | -0.2028% |
| Benchmark reaction (BTC) | -0.2279% |
| Relative reaction | +0.0251% |
| Hard gates | 3 pass / 4 unknown |
| Attribution verdict | insufficient_evidence |
| **Status** | ✅ Complete |

### w1_003 — Binance近10天BTC流入增加

| Field | Value |
|-------|-------|
| Information form | cumulative_trend + interpretation_or_narrative |
| Source medium | analyst_report |
| Routing | routed_to_other_design |
| Objects created | Candidate + Research Unit (context_only) + Event Instance + Claim-Evidence |
| Point-event study | ❌ Not eligible (cumulative trend + interpretation) |
| **Status** | ✅ Routed (no downstream objects) |

### w1_004 — Strategy暂停BTC购买

| Field | Value |
|-------|-------|
| Information form | discrete_information_release |
| Source medium | news_article |
| Routing | point_event_study |
| Objects created | All 8 |
| Target asset | BTC |
| Selected clock | information_clock |
| Actual time basis | broadcast_time |
| Primary benchmark | ETH (weak proxy — BTC target) |
| Price provider | Binance 1m klines (BTCUSDT) |
| Pre-event movement | -0.3474% (detected) |
| Raw 1h reaction | +0.1810% |
| Benchmark reaction (ETH) | +0.3666% |
| Relative reaction | -0.1856% |
| Hard gates | 3 pass / 4 unknown |
| Attribution verdict | insufficient_evidence |
| **Status** | ✅ Complete |

### w1_005 — WTI原油期货暴跌6%

| Field | Value |
|-------|-------|
| Information form | market_outcome_or_context |
| Source medium | market_data_feed |
| Routing | interference_context |
| Objects created | Candidate + Research Unit (context_only) + Event Instance + Claim-Evidence |
| Point-event study | ❌ Not eligible (market outcome/context — cannot study event-as-outcome) |
| **Status** | ✅ Routed (no downstream objects) |

## Hard Check Results

| Check | Count |
|-------|-------|
| Non-discrete point_event_study | 0 |
| Sentinel/placeholder values | 0 |
| Placeholder registration digests | 0 |
| Self-benchmark (target == benchmark) | 0 |
| Target in sensitivity benchmarks | 0 |
| Stale fact/doc conflicts | 0 |
| Fabricated sources | 0 |
| Silently dropped cases | 0 |
| Development → calibration leak | 0 |

## Sealed Protocol

Not modified. All objects created within sealed schema constraints.
