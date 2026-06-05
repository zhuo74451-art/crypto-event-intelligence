# Market Radar v1.17D — Price/OI/Volume Anomaly Real Card + TG One-Shot Report

**Generated**: 2026-06-05T16:32:39+08:00
**Run ID**: 20260605_163218
**Task ID**: 20260605_v117d_price_oi_volume_real_card_shared_pipeline_tg_one_shot

---

## Purpose

v117D proves that the **shared pipeline** works for a **second real card family**
(`price_oi_volume_anomaly`), not just `multi_asset_market_sync` (v117C).

Same pipeline chain:
```
PriceOIVolumeAnomalyFreeApiAdapter
  → NormalizedSignal
  → QualityGate:evaluate
  → CardRenderer:render
  → SendReadinessGate:evaluate
  → TGTestGroupSender:send (if allowed)
  → EvidenceLedger:record
```


## Safe Config Loader Probe

| Check | Result |
|-------|--------|
| scripts/load_local_secrets.ps1 found | ✅ |
| Load attempted | ✅ |
| Load method | `powershell_subprocess_dot_source` |
| Load success | ✅ |

### Post-Load Config Status

| Variable | Present | Length | SHA-256 Prefix |
|----------|---------|--------|----------------|
| TELEGRAM_BOT_TOKEN | ✅ | 46 | `d4fb60833e8c` |
| TELEGRAM_CHAT_ID | ✅ | 14 | `df017e9af8bf` |

**Config ready for TG send:** ✅ YES

---

## Binance Public API Status

| Check | Status |
|-------|--------|
| API called | ✅ |
| API success | ✅ |
| Assets scanned | 3 (BTCUSDT, ETHUSDT, SOLUSDT) |

### Endpoints Used

```
- binance_public_api:openInterest(BTCUSDT)
- binance_public_api:openInterest(ETHUSDT)
- binance_public_api:/api/v3/ticker/24hr
- binance_public_api:openInterest(SOLUSDT)
```

### Anomaly Detection Results

| Symbol | 24h Change | Volume OK | OI Available | Anomaly | Admission | Factors |
|--------|-----------|-----------|-------------|---------|-----------|---------|
| BTCUSDT | -0.99% | ✅ | ✅ | `normal` | ❌ | none |
| ETHUSDT | -5.62% | ✅ | ✅ | `notable` | ✅ | price_move_significant |
| SOLUSDT | -4.37% | ✅ | ✅ | `normal` | ❌ | price_move_significant |


### OI Errors (if any)

- None — all OI fetches succeeded or were N/A

### Anomaly Criteria

- **extreme**: |price_change| > 10% AND ≥2 confirmation factors
- **notable**: |price_change| > 5% AND ≥1 confirmation factor
- **normal**: below threshold
- Confirmation factors: price_move_significant (|Δ|>3%), volume_spike (vol>$5B), oi_elevated (OI>$1B)

## OI/Volume/Price Anomaly Status

- **Overall anomaly detected**: ✅ YES
- **Gate decision**: ✅ allow
- **Gate reason**: `Anomaly detected: notable on ETHUSDT`
- **Send outcome**: **SENT** — 1 price_oi_volume_anomaly card sent to TG test group

---

## Pipeline Result

| Stage | Result |
|-------|--------|
| Card Family | `price_oi_volume_anomaly` |
| Gate | ✅ allow |
| Send-Readiness | ✅ allow_test_group |
| Pipeline Passed | ✅ |

## TG Test Group Send

✅ **SENT** — 1 message delivered to TG test group (one-shot).

- Status: `sent`
- Target: `test_group`
- Production send: **False**
- One-shot: **True**
- Message proof: SHA-256 redacted (present: True)
- Token proof: SHA-256 redacted (present: True)
- Chat ID proof: SHA-256 redacted (present: True)
- Credentials printed: **False**

> v117D sent price_oi_volume_anomaly card to TG test group via shared pipeline.

---

## Shared Pipeline Verification

### v117D proves the shared pipeline for a second card family

| Check | v117C (multi_asset) | v117D (price_oi_volume) |
|-------|---------------------|-------------------------|
| Adapter | MultiAssetMarketSyncFreeApiAdapter | PriceOIVolumeAnomalyFreeApiAdapter |
| Real Binance API | ✅ | ✅ |
| Same shared pipeline | ✅ | ✅ |
| Same gate contract | ✅ | ✅ |
| Same renderer contract | ✅ | ✅ |
| Same sender contract | ✅ | ✅ |
| Same evidence ledger | ✅ | ✅ |
| card_family | multi_asset_market_sync | price_oi_volume_anomaly |

---

## Safety Verification

| Check | Status |
|-------|--------|
| External API called | ✅ |
| TG sent this run | ✅ 1 message |
| Production send | ❌ NEVER |
| X/Twitter send | ❌ NEVER |
| Credentials printed | ❌ NEVER |
| Daemon/loop started | ❌ NEVER |
| Files deleted | ❌ NEVER |
| v116 history modified | ❌ NEVER |
| Evidence ledger clean | ✅ |
| Preflight self-check | ✅ passed |

## Free API Data Source

- **Binance Public REST API** (`/api/v3/ticker/24hr`): BTC/ETH/SOL spot 24hr tickers
- **Binance Futures Public API** (`/fapi/v1/openInterest`): BTC/ETH/SOL perpetual futures open interest
- No API key required

## Secret Leak Risk Assessment

- ✅ Preflight JSON: self-checked, no raw token/chat_id patterns
- ✅ Result JSON: no raw token/chat_id/message_id
- ✅ Evidence ledger: SHA-256 proofs only
- ✅ Report: redacted proofs only
- ✅ Handoff: redacted proofs only
- ✅ Console output: only length/hash/prefix info

## Production Readiness

**0/5 — NOT FOR LIVE USE**

All minimum conditions remain unmet. Production send is NEVER enabled.

## Test Results Summary

| Test Suite | Expected | Actual | Tests |
|------------|----------|--------|-------|
| v117D tests | Pass | ✅ **85 passed** | 85 |
| v117C regression | Pass | ✅ **73 passed** | 73 |
| v117B regression | Pass | ✅ **63 passed** | 63 |
| v117 regression | Pass | ✅ **54 passed** | 54 |
| v116N regression | Pass | ✅ **97 passed** | 97 |
| **TOTAL** | **Pass** | ✅ **372 passed** | **372** |

All regression suites confirmed no historical files were deleted or modified.
