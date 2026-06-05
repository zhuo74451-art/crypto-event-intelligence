# v112V Degraded Live Response → Mock Replay with Explanation Layer — Run Report

**Generated**: 2026-06-05 05:11:53 UTC+8
**Version**: v1.12-v
**Status**: passed

## v112V Objective

Take v112U's DEGRADE_TO_MOCK live response and convert it into traceable mock replay records with a degradation explanation layer. This step makes ZERO external API calls — it reads only v112U's already-generated output files and transforms them for safe entry into the mock adapter / envelope / preview pipeline.

## What v112U Returned

- **Status**: `degraded`
- **Stop Decision**: `DEGRADE_TO_MOCK`
- **Source Count Attempted**: 2
- **Assets Requested**: 3
- **Real Live API Called**: True
- **TG Sent**: False
- **State Write Performed**: False
- **Total Elapsed**: 0.71s

### Price Data Retrieved from CoinGecko

| Asset | Symbol | Price (USD) | 24h Change % |
|-------|--------|-------------|--------------|
| bitcoin | BTC | $63345.0 | -3.282308820606044 |
| ethereum | ETH | $1767.01 | -2.3544916476773388 |
| solana | SOL | $68.53 | -4.799514994608399 |

## Why DEGRADE_TO_MOCK (Not Failure)

DEGRADE_TO_MOCK is the correct and expected safety behavior — it is NOT a failure. The v112T three-state stop condition system correctly identified that the data quality is insufficient for real send, but the data is NOT unusable. Here's why:

1. **CoinGecko succeeded** — All 3 assets (BTC, ETH, SOL) returned valid price data with HTTP 200.
2. **All 5 required fields present** — asset_id, symbol, price_usd, price_change_pct, last_updated_at for all 3 assets.
3. **CoinCap SSL failure is a transport issue**, not an API rejection — the endpoint may have been temporarily unreachable.
4. **No ABORT conditions triggered** — No HTTP errors, no JSON parse failures, no schema violations, no timeout.
5. **But cross-validation is impossible** with only one source — hence DEGRADE, not CONTINUE.
6. **OI and volume_change_pct are missing** from all free sources — this is a known capability gap, not a bug.

## How CoinCap Failure Was Handled

- CoinCap `/v2/assets` request failed with an SSL/TLS transport error.  
- The system did NOT retry (v112U safety boundary: `retry_enabled=false`).  
- The system did NOT attempt to harden the data to CONTINUE.  
- The system correctly triggered `DEGRADE_MULTI_SOURCE_UNCERTAIN`.  
- The CoinCap failure is preserved in the degradation explanation for audit traceability.  
- No new CoinCap request was made in v112V — this step is purely local.

## How OI / Volume Field Gaps Are Handled

- `open_interest_change_pct`: **null for all 3 assets** — no free public REST API provides OI data.  
- `volume_change_pct`: **null for all 3 assets** — CoinGecko `/simple/price` does not include volume.  
- These gaps triggered `DEGRADE_OPTIONAL_FIELDS_MISSING` (6 missing fields across 3 assets).  
- v112Q threshold `require_price_and_one_secondary_metric` cannot be satisfied without volume or OI.  
- Resolution options: (a) establish historical baseline for volume calculation, (b) switch to CoinGecko `/coins/markets` for raw volume, (c) add a paid OI source.  
- The gap is documented in the degradation explanation for downstream audit.

## Mock Replay Records Summary

- **Total records generated**: 3
- **Assets covered**: BTC, ETH, SOL

| Record ID | Asset | Price (USD) | 24h Change % | eligible_for_real_send | mock_replay_only | gate_status |
|-----------|-------|-------------|--------------|------------------------|------------------|-------------|
| mrp-v112v-31... | BTC | $63345.0 | -3.282308820606044 | False | True | degraded_mock_replay |
| mrp-v112v-f8... | ETH | $1767.01 | -2.3544916476773388 | False | True | degraded_mock_replay |
| mrp-v112v-8d... | SOL | $68.53 | -4.799514994608399 | False | True | degraded_mock_replay |

Every record has:
- `source_live_response` → traceable back to `market_radar_v112u_live_source_response.json`
- `degradation_reasons` → traceable back to `market_radar_v112u_stop_decision.json`
- `mock_replay_only=true` → not a real signal
- `eligible_for_real_send=false` → blocked from real send path
- `gate_status=degraded_mock_replay` → correct gate classification

## Why Still NOT Eligible for Real Send

Even after v112V processing, the signal is NOT eligible for real send. Reasons:

1. **All 3 records have `eligible_for_real_send=false`** — hardcoded policy, enforced at every pipeline level.
2. **`mock_replay_only=true`** — these are mock replay records, not real signal candidates.
3. **Only 1 of 2 requested sources returned data** — cross-validation impossible, confidence low.
4. **OI and volume data still missing** — `require_price_and_one_secondary_metric` cannot be satisfied.
5. **No historical baseline established** — required by v112Q before any real send.
6. **No TG send pipeline connected** — send infrastructure is not built.
7. **No production state infrastructure** — state tracking is not configured for production.

## Safety Checklist

| Constraint | Value |
|------------|-------|
| External API Called (this step) | False |
| Real Live API Called (this step) | False |
| External AI Called | False |
| TG Sent | False |
| Production State Write | False |
| Daemon Started | False |
| Retry Attempted | False |
| Files Deleted | False |
| Debug Leak Count | 0 |
| Secret Leak Count | 0 |
| Eligible For Real Send Count | 0 |

## Recommended Next Step

**v112w_degraded_mock_preview_explanation_or_gemini_direction_audit**

1. Run Gemini direction audit on the degradation explanation to determine:
   - Whether to continue fixing the free source route (add /coins/markets for volume, establish historical baseline)
   - Or whether to pivot to `whale_position_alert` as a second candidate card type that may be more viable with free sources
2. If continuing free source route: implement historical baseline, switch to /coins/markets, add volume calculation
3. If pivoting: run whale_position_alert dry-run to assess free-source viability for that card type
