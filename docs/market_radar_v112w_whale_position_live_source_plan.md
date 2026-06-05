# v112W — Whale Position Alert Live Source Readiness Plan

**Version:** v1.12-w  
**Status:** Plan-only (no API calls, no TG send, no production state)  
**Generated:** 2026-06-05 04:13 UTC+8  
**Previous Candidate Frozen:** multi_asset_market_sync  
**Next Candidate Active:** whale_position_alert

---

## 1. Why Switch from multi_asset_market_sync to whale_position_alert

### multi_asset_market_sync — Current Frozen State

`multi_asset_market_sync` scored highest in the v112P live source readiness matrix (18/18),
and was selected as the first live-like candidate in v112Q–v112S. It successfully demonstrated:

- **Ingestion safety degradation** — v112U degraded gracefully when CoinCap failed.
- **Mock replay** — v112V produced degraded mock replay records proving the
  DEGRADE_TO_MOCK path.
- **Envelope compatibility** — v112S confirmed envelope/preview integration.

However, continued pursuit of `multi_asset_market_sync` as the first live source candidate
would sacrifice signal quality for these reasons:

| Gap | Impact |
|-----|--------|
| No free OI (open interest) source | Multi-asset sync requires OI data for credible correlation scoring. Free tier sources (Coinglass) need API keys or have limited coverage. |
| No free `volume_change_pct` source | Volume change is a core sync signal. Free exchange REST APIs provide raw volume but not normalized change percentages across assets. |
| Multi-source verification unstable | Multi-asset sync needs 3+ sources for credible cross-asset correlation. With free-tier volatility, verification is unreliable. |
| Higher data complexity | 12+ required fields across multiple sources — more failure points than single-source position data. |

**Freeze status: `mock-ready` / `degrade-safe`**

`multi_asset_market_sync` is frozen in a demonstrated-safe state:
- Mock replay works (v112V).
- Degradation path verified (DEGRADE_TO_MOCK → mock records).
- Envelope integration complete (v112H).
- Preview cards exist (v112O).
- No further development until a reliable free OI/volume source is identified.

### whale_position_alert — Why It's the Better Next Candidate

| Factor | whale_position_alert | multi_asset_market_sync |
|--------|---------------------|------------------------|
| Data source count | 1 primary (HyperLiquid) + 1 fallback (CoinGecko price) | 3+ required (price, OI, volume) |
| Required fields | 10 (8 from HL, 2 computed) | 12+ across multiple sources |
| Free source quality | HyperLiquid Info API — public, free, no key, well-documented | Coinglass free tier — rate-limited, may need key |
| One-shot feasibility | Single POST request per address, pure read-only | Multiple concurrent requests across APIs |
| Data reliability | HyperLiquid positions are on-chain deterministic | Cross-exchange OI/volume can diverge significantly |
| Address label availability | Labels in local state CSV (6 labeled addresses) | N/A |
| Existing infrastructure | watch_hyperliquid_positions.py, snapshot_hl_positions.py, hyperliquid_position_state.csv | mock adapters only |
| v112P readiness score | 16/18 (high) | 18/18 (high) |
| Real blocker | None — all fields available from free public endpoint | Missing OI + volume_change_pct sources |

## 2. whale_position_alert Current Foundation

### v112F — Local Feed

- **Script:** `scripts/market_radar_whale_position_feed_v112f.py`
- **Result:** `results/market_radar_v112f_whale_position_local_enrichment_result.json`
- **Status:** Complete. 6 valid signals, 2 blocked signals, 6 public cards.
- **Address labels:** 6 labels loaded from fixture.
- **Alert types:** position_opened, position_increased, position_reduced,
  high_leverage_risk, large_unrealized_loss.
- **Security:** All wallets use short form. No debug/secret leaks. No API calls.

### v112H — Unified Signal Envelope

- **Result:** `results/market_radar_v112h_unified_signal_envelope_result.json`
- **Status:** whale_position_alert has 3 envelopes in the unified system.
- **Envelope IDs:** sig-wpa-f71d2b1d, sig-wpa-1ae7a01d, sig-wpa-46d9d399.
- **Cardinality verified:** expected 3, actual 3.

### v112O — Send Preview Pack

- **Result:** `results/market_radar_v112o_send_preview_pack_result.json`
- **Status:** whale_position_alert has 2 preview cards in the eligible pack.
- **Distribution:** 2 whale_position_alert cards out of 9 total preview cards.
- **One whale card blocked:** sig-wpa-1ae7a01d — dedupe gate (already in prior state).

### Existing HyperLiquid Infrastructure

- **`scripts/watch_hyperliquid_positions.py`** — Full watcher with HyperLiquid API
  integration, position state management, CSV persistence. (NOT invoked in v112W.)
- **`scripts/snapshot_hl_positions.py`** — One-shot position snapshot script. (NOT invoked in v112W.)
- **`scripts/market_radar_free_sources.py`** — Free data source adapter with
  HyperLiquid POST helper (`_http_post`) to `https://api.hyperliquid.xyz/info`.
- **`data/hyperliquid_position_state.csv`** — Current position state with 12 rows,
  4 unique tracked addresses, entity labels.

## 3. HyperLiquid One-Shot Read-Only Plan

### Endpoint

```
POST https://api.hyperliquid.xyz/info
Content-Type: application/json
Body: {"type": "clearinghouseState", "user": "<tracked_address>"}
```

- **Method:** POST but read-only (no state mutation on HyperLiquid side).
- **Auth:** None required. Public endpoint.
- **Rate limit:** Burst limits exist but one-shot (4 addresses) is well within limits.
- **Timeout:** 10s per request.

### Tracked Addresses (from `data/hyperliquid_position_state.csv`)

| Address | Entity | Label Confidence |
|---------|--------|-----------------|
| 0x6c8512...fd84f6 | Matrixport Related | medium |
| 0x8def9f...392dae | loraclexyz | medium |
| 0x082e84...edca88 | Unknown HYPE Whale | low |
| 0x50b309...c9f20 | Unknown Hyperliquid Whale | low |

### Request Plan (per address)

1. POST `{"type": "clearinghouseState", "user": "<address>"}` to HyperLiquid Info API.
2. Parse `assetPositions[]` from response.
3. For each position, extract: coin, szi, entryPx, liquidationPx, unrealizedPnl,
   leverage, marginUsed, positionValue.
4. Fetch mark price from CoinGecko free API (fallback: use entry price).
5. Apply field normalization (see field mapping).
6. Enrich with address label (from local state or "Unknown Whale" fallback).
7. Compute position delta against previous state (if available).
8. Classify alert type (position_opened, position_increased, etc.).
9. Run stop conditions check (ABORT / DEGRADE_TO_MOCK / CONTINUE).
10. If CONTINUE or DEGRADE_TO_MOCK: produce v112F-compatible whale event.
11. Wrap in v112H envelope with eligible_for_real_send=false.
12. Generate v112O-compatible preview card (dry-run only).

## 4. Stop Conditions (Three-State Decision)

See `config/market_radar_v112w_hyperliquid_stop_conditions.json` for the full specification.

### Summary

| Decision | Trigger Examples | Action |
|----------|-----------------|--------|
| **ABORT** | HTTP non-2xx, timeout >10s, JSON parse error, schema mismatch, all addresses empty, >20% fields missing, rate limit, auth required, state write attempted | Stop immediately. No envelope. No preview. |
| **DEGRADE_TO_MOCK** | Partial address failure (≥50% ok), label missing/confidence low, liquidation_price null, previous_size unavailable, delta uncomputable, timestamp uncertain | Process with degraded flags. Set `degraded: true` in envelope. eligible_for_real_send=false. |
| **CONTINUE** | All required fields present, ≥1 active position, numeric parse ok, timestamp ok, label ok or fallback, adapter can produce event | Produce v112F-compatible event. eligible_for_real_send still false. |

### Critical Invariants (all modes)

- `eligible_for_real_send` is ALWAYS `false`.
- `production_state_write` is NEVER performed.
- `real_tg_sent` is ALWAYS `false`.
- No API key is EVER sent.
- No auth header is EVER sent.

## 5. Label Quality Audit

Based on `data/hyperliquid_position_state.csv` (12 rows, 4 unique addresses):

| Metric | Value |
|--------|-------|
| Tracked addresses total | 4 |
| Positions total | 12 |
| Labels total | 4 |
| High confidence labels | 0 |
| Medium confidence labels | 2 (Matrixport Related, loraclexyz) |
| Low confidence labels | 2 (Unknown HYPE Whale, Unknown Hyperliquid Whale) |
| Unknown labels | 0 (all addresses have labels) |
| Unknown label fallback ready | true |
| Label quality ready for one-shot plan | true |

**Conclusion:** Label quality is sufficient for a one-shot dry-run plan. The 2
low-confidence labels ("Unknown * Whale") are acceptable — they use the "Unknown Whale"
fallback which is explicitly handled in the adapter spec. No address is completely
unlabeled.

## 6. Field Mapping

See `config/market_radar_v112w_whale_position_field_mapping.json` for the full specification.

### Mapping Chain

```
HyperLiquid Raw → v112F Whale Adapter → v112H Envelope Payload
```

Key mappings:
- `assetPositions[].position.coin` → `asset` → `asset_symbol`
- `assetPositions[].position.szi` → `side` (+/−) → `position_direction`
- `assetPositions[].position.positionValue` → `position_size_usd`
- `assetPositions[].position.entryPx` → `entry_price`
- `assetPositions[].position.unrealizedPnl` → `unrealized_pnl_usd`
- `assetPositions[].position.leverage.value` → `leverage`
- `assetPositions[].position.liquidationPx` → `liquidation_price` (nullable)

## 7. Adapter Spec Summary

See `schemas/market_radar_v112w_hl_to_whale_adapter_spec.md` for the full specification.

Key design decisions:
- **Side from szi sign** — positive = long, negative = short.
- **Mark price from CoinGecko** — HyperLiquid response may not include it.
- **Unknown Whale fallback** — always available, always low confidence.
- **Deterministic IDs** — signal_id, dedupe_key, cooldown_key, payload_hash all
  computed from deterministic hash functions.
- **eligible_for_real_send = false** — enforced at adapter level and envelope level.
- **data_mode = "live_like_planned"** — distinct from "live" or "production".

## 8. v112X Execution Prerequisites

Before `v112X` (HyperLiquid one-shot read-only dry-run) can execute:

1. [ ] **User explicit confirmation required.**
2. [x] All v112W tests pass.
3. [x] Label quality audit shows `label_quality_ready_for_one_shot_plan: true`.
4. [x] Stop conditions config reviewed.
5. [x] Field mapping verified against expected HyperLiquid API response shape.
6. [x] No credentials, keys, or auth tokens read or sent.
7. [ ] v112X script will be a separate execution step (NOT part of v112W).

## 9. Why Still Cannot Send for Real

1. **No live HyperLiquid data has been fetched.** v112W is plan-only. All data is
   from local fixtures and state CSV snapshots.
2. **Adapter is specified but not exercised with real data.** The field mapping
   and transformation rules are documented but not battle-tested.
3. **Stop conditions are specified but not triggered.** We don't know which
   condition (ABORT, DEGRADE, or CONTINUE) would actually fire until we try.
4. **v112X confirmation gate.** The one-shot dry-run requires explicit user
   confirmation — it is a separate step with its own safety invariants.
5. **No TG delivery path is connected.** Even if live data were fetched and
   processed, the TG send path requires separate configuration and testing.

**Bottom line:** v112W is a readiness assessment and planning artifact. It answers
"can we proceed?" — it does not proceed. v112X is the step that proceeds, and it
requires user confirmation.

## 10. Generated Artifacts

| Artifact | Path | Purpose |
|----------|------|---------|
| Field mapping | `config/market_radar_v112w_whale_position_field_mapping.json` | HL → v112F → v112H field mapping |
| Stop conditions | `config/market_radar_v112w_hyperliquid_stop_conditions.json` | Three-state decision rules |
| Live response schema | `schemas/market_radar_v112w_hyperliquid_live_response_schema.json` | Expected response shape |
| Adapter spec | `schemas/market_radar_v112w_hl_to_whale_adapter_spec.md` | Transformation rules |
| Label audit | `results/market_radar_v112w_whale_label_quality_audit.json` | Label quality assessment |
| Plan result | `results/market_radar_v112w_whale_position_live_source_plan_result.json` | Execution result |
| Run report | `runs/market_radar/v112w_whale_position_live_source_plan.md` | This document (run copy) |
| Handoff | `runs/market_radar/v112w_whale_position_live_source_plan_handoff.md` | Handoff summary |
| Runner | `scripts/run_market_radar_v112w_whale_position_live_source_plan.py` | Plan execution |
| Tests | `scripts/test_market_radar_v112w_whale_position_live_source_plan.py` | Validation |
