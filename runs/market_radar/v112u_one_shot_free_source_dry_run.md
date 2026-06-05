# v112U One-Shot Free Source Dry-Run — Run Report

**Generated**: 2026-06-05 04:13:08 UTC+8
**Status**: degraded
**Stop Decision**: DEGRADE_TO_MOCK

## v112U Objective

Execute one-shot free source dry-run: make real HTTP GET requests to CoinGecko and CoinCap free public REST APIs, normalize the response to LiveSourceResponse schema, and apply v112T stop conditions to determine CONTINUE/ABORT/DEGRADE_TO_MOCK.

## Sources Requested

- **Primary**: CoinGecko Public REST — `/api/v3/simple/price`
  - Status: HTTP 200
  - Latency: 522ms
- **Fallback**: CoinCap Public REST — `/api/v2/assets`
  - Status: HTTP None
  - Latency: 189ms
  - Error: URL Error: [SSL: UNEXPECTED_EOF_WHILE_READING] EOF occurred in violation of protocol (_ssl.c:1006)

## Assets Requested

- BTC, ETH, SOL (3 assets)
- Assets returned: 3

## Price Data Retrieved

| Asset | Symbol | Price (USD) | 24h Change % | Source |
|-------|--------|-------------|--------------|--------|
| bitcoin | BTC | $63345.0 | -3.282308820606044 | coingecko_public_rest |
| ethereum | ETH | $1767.01 | -2.3544916476773388 | coingecko_public_rest |
| solana | SOL | $68.53 | -4.799514994608399 | coingecko_public_rest |

## Safety Checklist

| Constraint | Value |
|------------|-------|
| API Key Used | False |
| Authorization Header Used | False |
| Retry Attempted | False |
| TG Sent | False |
| Production State Write | False |
| Daemon Started | False |
| External AI Called | False |
| Files Deleted | False |
| Eligible For Real Send | False |

## Stop Decision

**Decision**: `DEGRADE_TO_MOCK`
**Reason**: 2 degrade rule(s) triggered

### DEGRADE Rules Triggered
- **DEGRADE_OPTIONAL_FIELDS_MISSING**: 6 optional field(s) missing across assets (OI, volume_change_pct unavailable from free sources)
- **DEGRADE_MULTI_SOURCE_UNCERTAIN**: Only primary source (CoinGecko) returned data; cross-validation impossible
### CONTINUE Rules Satisfied
- **CONTINUE_ALL_REQUIRED_COMPLETE**: All 5 required fields present for 3 assets
- **CONTINUE_ELIGIBLE_FALSE**: eligible_for_real_send = false (policy constraint, always enforced)

## Why Still NOT Eligible for Real Send

Even if CONTINUE, v112U policy mandates `eligible_for_real_send=false`. Reasons:

1. This is a dry-run only — no production infrastructure is connected
2. Only one or two free sources are used — insufficient for production redundancy
3. Open Interest data is missing from free sources (needed for v112Q secondary metric)
4. Free tier rate limits prevent reliable production operation
5. No historical baseline has been established (required by v112Q)
6. No TG formatting, send pipeline, or monitoring is connected

## Latency

- Total elapsed: 0.71s
- CoinGecko request latency: 522ms
- CoinCap request latency: 189ms

## Recommended Next Step

**v112v_live_response_to_mock_adapter_if_continue_else_mock_replay**

Since v112U returned DEGRADE_TO_MOCK, v112V should:
1. Run mock replay with the degradation reason documented
2. Consider whether stop condition thresholds need adjustment
3. Build mock replay explanation layer
