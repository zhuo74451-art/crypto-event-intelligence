# market_radar_v112t_free_source_plan

**Version**: v1.12-t  
**Status**: plan-only — no live fetch, no API calls, no TG send  
**Generated**: 2026-06-05 03:44:00 UTC+8  
**Lane**: 1 (test-group delivery allowed)  

---

## 1. v112T Target

v112T is the **one-shot free source plan with stop conditions** for `multi_asset_market_sync` — the highest-scoring card type from the v112P live-source readiness audit (score: 18/18).

**What v112T does**:
- Define free data source candidates (CoinGecko Public REST, CoinCap Public REST)
- Define field mapping from raw source → normalized → v112Q threshold fields
- Define three-state stop conditions (CONTINUE / ABORT / DEGRADE_TO_MOCK)
- Define `LiveSourceResponse` schema for normalized live data
- Define `LiveToMockAdapter` conversion spec (live → v112R mock adapter input)
- Define rate limit / timeout / fallback strategy
- Define v112U execution prerequisites

**What v112T does NOT do**:
- ❌ Make real HTTP requests to CoinGecko or CoinCap
- ❌ Write a live fetcher
- ❌ Read API keys or credentials
- ❌ Send Telegram messages
- ❌ Start daemons or background processes
- ❌ Write production state
- ❌ Call external AI APIs

---

## 2. Why Plan-Only Now (Not Live Fetch)

| Reason | Detail |
|---|---|
| **No user confirmation for live fetch** | v112U requires explicit user confirmation before making real HTTP requests to external APIs. v112T obtains that confirmation by presenting the complete plan. |
| **Stop conditions must be defined first** | ABORT / DEGRADE / CONTINUE rules must be specified and reviewed before any live request, so the system knows when to stop. |
| **Schema contract must be stable** | The `LiveSourceResponse` schema defines the data contract. v112R adapter compatibility depends on this being correct. |
| **Rate limit strategy must be planned** | Free APIs have undocumented, variable rate limits. The fallback chain and timeout strategy must be designed before hitting real endpoints. |
| **OI data gap must be addressed** | Free sources don't provide open interest data. This affects v112Q threshold compliance. The degradation path must be designed. |
| **Safety first** | v112T inherits the project's safety-first approach: plan → validate → dry-run → review → (maybe) send. We are at step 2. |

---

## 3. Free Source Candidates

### Primary: CoinGecko Public REST API

| Property | Value |
|---|---|
| **Source ID** | `coingecko_public_rest` |
| **Base URL** | `https://api.coingecko.com/api/v3` |
| **Endpoints (planned)** | `/simple/price`, `/coins/markets` |
| **Cost** | Free (no key required) |
| **Rate Limit** | ~10-30 req/min (undocumented, varies) |
| **Timeout** | 15s per request |
| **Data Provided** | price_usd, price_change_pct (1h, 24h), volume, market_cap |
| **Data NOT Provided** | Open interest, funding rate, liquidation data |
| **Cache Behavior** | 30-60s cache on free tier |

### Fallback: CoinCap Public REST API

| Property | Value |
|---|---|
| **Source ID** | `coincap_public_rest` |
| **Base URL** | `https://api.coincap.io/v2` |
| **Endpoints (planned)** | `/assets`, `/assets/{id}` |
| **Cost** | Free (no key required) |
| **Rate Limit** | ~200 req/min (generous) |
| **Timeout** | 15s per request |
| **Data Provided** | price_usd, price_change_pct (24h only), volume_24h, market_cap |
| **Data NOT Provided** | 1h price change, open interest, funding rate |
| **Cache Behavior** | Real-time or near-real-time |

### Forbidden Sources (explicitly excluded)

| Source | Reason |
|---|---|
| CoinGecko Pro | Requires paid API key |
| CoinMarketCap | Requires API key (even free tier) |
| Glassnode | Requires paid API key |
| Any API-key source | Out of scope for free-source plan |
| WebSocket streams | Requires persistent connection (daemon) |

---

## 4. Field Mapping

### Source → Normalized → v112Q Threshold

```
CoinGecko /simple/price          CoinCap /v2/assets
        │                                │
        ▼                                ▼
  ┌──────────────────────────────────────────┐
  │       Normalized v112T Fields            │
  │  asset_id, symbol, price_usd,            │
  │  price_change_pct, volume_change_pct,    │
  │  open_interest_change_pct (nullable),    │
  │  last_updated_at, source_latency_ms      │
  └──────────────────────────────────────────┘
                     │
                     ▼
  ┌──────────────────────────────────────────┐
  │       v112Q Threshold Fields             │
  │  direction agreement (from price_change) │
  │  per-asset price filter (min 2.0%)       │
  │  secondary metric (volume or OI)         │
  │  timestamp skew (max 60s)                │
  │  leader detection                        │
  │  sector concentration                    │
  │  volume outlier                          │
  └──────────────────────────────────────────┘
```

### Known Gaps

| Gap | Impact | Mitigation |
|---|---|---|
| **No OI data** from free sources | `require_price_and_one_secondary_metric` can only use volume | DEGRADE_TO_MOCK if volume also missing |
| **No 1h change** from CoinCap | Shorter-term momentum unavailable from fallback | Use 24h change as primary; mark 1h as null |
| **CoinGecko cache lag** | Data may be 30-60s stale | Cross-validate with CoinCap real-time data; check timestamp skew |

Full mapping specification: `config/market_radar_v112t_free_source_mapping.json`

---

## 5. Three-State Stop Conditions

### ABORT (Hard Stop — No Output)

| # | Condition | Trigger |
|---|---|---|
| 1 | HTTP non-2xx | Any status code outside 200-204 |
| 2 | HTTP 429 | Rate limited |
| 3 | Request timeout | Single request > 15s |
| 4 | Total duration | All requests > 120s |
| 5 | JSON parse failure | Response body not valid JSON |
| 6 | Schema mismatch | Response doesn't match expected structure |
| 7 | Price divergence | CoinGecko vs CoinCap > 5% |
| 8 | Timestamp skew | Max inter-asset timestamp diff > 120s |
| 9 | Required fields missing | > 20% of required fields absent |

### DEGRADE_TO_MOCK (Degraded — Mock Output Only)

| # | Condition | Trigger |
|---|---|---|
| 1 | Partial asset failure | Some assets missing, success rate < 80% |
| 2 | Optional fields missing | open_interest_change_pct, source_latency_ms null |
| 3 | Threshold boundary | Any metric within ±10% of v112Q threshold |
| 4 | Source freshness degraded | last_updated_at > 120s from fetched_at |
| 5 | Multi-source uncertain | Only one source returned data |

### CONTINUE (Proceed — But Still Not Real Send)

| # | Condition | Trigger |
|---|---|---|
| 1 | All required fields complete | Every asset has all required fields |
| 2 | Price consensus | Cross-source price divergence < 2% |
| 3 | Timestamp consensus | Max timestamp diff < 60s |
| 4 | v112Q thresholds passed | All stricter thresholds satisfied |
| 5 | No abort/degrade triggered | Clean pass on all checks above |
| 6 | **eligible_for_real_send = false** | Policy constraint — always false |

Full stop conditions specification: `config/market_radar_v112t_stop_conditions.json`

---

## 6. Rate Limit / Timeout / Fallback Strategy

### Timeout Configuration

| Parameter | Value |
|---|---|
| Per-request timeout | 15,000 ms |
| Total duration limit | 120,000 ms |
| Retry on 429 | No (free tier — retries may be abuse) |
| Retry on timeout | No (automatic retries disabled) |

### Fallback Chain

```
1. CoinGecko /simple/price  ──success──▶  Process response
        │
        │ failure/timeout
        ▼
2. CoinCap /v2/assets       ──success──▶  Process response (degraded: single source)
        │
        │ failure/timeout
        ▼
3. ABORT — no data available
```

### Cross-Source Validation (when both succeed)

```
Both CoinGecko AND CoinCap return data for same asset:
  ├── Price divergence < 2%     → CONTINUE (consensus)
  ├── Price divergence 2-5%     → DEGRADE_TO_MOCK (minor divergence)
  └── Price divergence > 5%     → ABORT (major divergence)
```

---

## 7. LiveSourceResponse Schema Summary

The `LiveSourceResponse` schema (`schemas/market_radar_v112t_live_source_response_schema.json`) defines:

- **Top-level**: `source_name`, `fetched_at`, `request_mode`, `assets[]`, `validation_status`, `stop_decision`
- **Asset object**: `asset_id`, `symbol`, `price_usd`, `price_change_pct`, `volume_change_pct`, `open_interest_change_pct` (nullable), `last_updated_at`, `source_latency_ms` (nullable), `raw_source_fields`
- **Cross-source validation**: `cross_source_validation` object with divergence metrics
- **Safety**: `eligible_for_real_send` is `const: false`

---

## 8. LiveToMockAdapter Conversion Rules

The adapter (`schemas/market_radar_v112t_live_to_mock_adapter_spec.md`) defines:

1. **Stop decision gate**: ABORT → no conversion; DEGRADE → degraded conversion; CONTINUE → normal conversion (still eligible=false)
2. **Field mapping**: LiveSourceResponse fields → v112R adapter input fields
3. **v112Q threshold inheritance**: All stricter thresholds applied to converted data
4. **Source lineage**: Every asset carries its source provenance
5. **Deterministic IDs**: SHA256-based signal_id and payload_hash for idempotent replay
6. **Default eligible=false**: Enforced at schema level, adapter level, and runner level
7. **OI gap handling**: Missing OI → DEGRADE_TO_MOCK if volume also unavailable

---

## 9. v112U Execution Prerequisites

v112U (one-shot free source dry-run) requires ALL of the following:

### User Confirmation (BLOCKING)
- [ ] User has explicitly confirmed they want to proceed with a one-shot free-source dry-run
- [ ] User understands this will make real HTTP requests to `api.coingecko.com` and `api.coincap.io`
- [ ] User understands free-tier rate limits apply
- [ ] User understands no Telegram message will be sent

### Technical Prerequisites
- [ ] Network access to CoinGecko and CoinCap APIs from execution environment
- [ ] v112T plan approved (this document)
- [ ] All v112T config files validated
- [ ] v112S, v112R, v112Q tests passing
- [ ] v112T test passing

### Safety Constraints (MUST HOLD)
- [ ] `eligible_for_real_send` must remain `false`
- [ ] No production state write
- [ ] No TG send (even to test channel — v112U is read-only from network)
- [ ] No daemon, cron, or background process
- [ ] No external AI API calls
- [ ] Timeout enforcement: 15s per request, 120s total

### Output Constraints
- [ ] Results written ONLY to `results/` and `runs/`
- [ ] No modification of production state files
- [ ] No writing to `C:\Users\PC\Desktop\工作台\`

---

## 10. Why Real Send Is Still NOT Allowed

Even after v112T planning and v112U dry-run, real TG send remains blocked because:

1. **No OI data**: Free sources lack open interest data. Without OI, the `require_price_and_one_secondary_metric` check relies solely on volume, which is a weaker signal.
2. **No historical baseline**: `historical_baseline_required_before_real_send` is `true` in v112Q thresholds. We have not yet accumulated enough real-data history.
3. **No source reliability data**: We have zero samples of CoinGecko/CoinCap live data through our pipeline. Source behavior (uptime, latency, data quality) is unknown.
4. **No multi-cycle validation**: A single one-shot dry-run is not enough to validate the pipeline for production use.
5. **Manual review required**: The v112P audit requires `manual_review_required_before_send = true` for all card types.
6. **Safety policy**: The project's safety-first approach requires progressive validation: plan → mock → local dry-run → live dry-run → test channel → (maybe) production.

---

## 11. Files Generated by v112T

| File | Purpose |
|---|---|
| `config/market_radar_v112t_free_source_mapping.json` | Free source and field mapping config |
| `config/market_radar_v112t_stop_conditions.json` | Three-state stop conditions |
| `schemas/market_radar_v112t_live_source_response_schema.json` | Normalized live response JSON Schema |
| `schemas/market_radar_v112t_live_to_mock_adapter_spec.md` | Live-to-mock adapter conversion spec |
| `docs/market_radar_v112t_free_source_plan.md` | This document |
| `scripts/run_market_radar_v112t_one_shot_free_source_plan.py` | v112T runner |
| `scripts/test_market_radar_v112t_plan_validation.py` | v112T test suite |
| `results/market_radar_v112t_one_shot_free_source_plan_result.json` | Result JSON (generated by runner) |
| `runs/market_radar/v112t_one_shot_free_source_plan.md` | Run report |
| `runs/market_radar/v112t_one_shot_free_source_plan_handoff.md` | Handoff document |

---

## 12. Recommended Next Step

**v112U: one_shot_free_source_dry_run** — requires user explicit confirmation.

v112U will:
1. Ask user for confirmation to make real HTTP requests
2. Fetch data from CoinGecko and CoinCap free APIs
3. Apply v112T stop conditions
4. Convert live responses via LiveToMockAdapter
5. Run through v112R mock adapter
6. Run through v112S gate/preview integration
7. Produce preview cards with `eligible_for_real_send = false`
8. Write results to `results/` and `runs/` only

**v112U does NOT**: send TG, write production state, start daemons, or allow real send.
