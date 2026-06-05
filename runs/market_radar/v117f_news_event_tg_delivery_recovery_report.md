# Market Radar v1.17F — News Event TG Delivery Recovery Report

**Generated**: 2026-06-05T17:06:33+08:00
**Run ID**: 20260605_170616
**Task ID**: 20260605_v117f_news_event_tg_delivery_recovery_and_source_stability
**Variant**: v117F (recovery + stability fixes)

---

## v117F Fixes Applied

| Fix | Status | Detail |
|-----|--------|--------|
| Market fetch-once caching | ✅ | Adapter fetch count: 1 (≤1 = no duplicates) |
| RSS XML parser warning | ✅ | `is not None` explicit checks — no element truth value |
| TG network failure classification | ✅ | Enhanced: granular types |
| Proxy env detection | ✅ | Boolean only — no address logging |

---

## News Event Public Source Status

| Check | Status |
|-------|--------|
| Sources attempted | 5 |
| Sources succeeded | 4 |
| Articles fetched | 165 |
| Events extracted | 50 |
| Event extracted (≥1) | ✅ |
| All sources unavailable | ✅ NO |

### Public Sources Used

| # | Source | Type |
|---|--------|------|
| | CoinDesk | ok |
| | Cointelegraph | ok |
| | Decrypt | ok |
| | Binance Announcements | ok |

### Event Details (if extracted)

| Field | Value |
|-------|-------|
| Source | CoinDesk |
| Title | Bitcoin plunges to near $62,000 as the AI trade unwinds, HYPE falls 14% |
| Event type | other |
| Intensity | high |
| Attribution risk | direct |
| Assets affected | BTC, HYPE, NEAR |
| URL proof | SHA-256 redacted |
| observation_only | **True** |
| not_causal_proof | **True** |

### Market Data (v117F: fetch-once cached)

| Check | Status |
|-------|--------|
| Binance market API called | ✅ |
| Market fetch attempted | ✅ |
| Adapter fetch count (total) | 1 |
| Duplicate fetch prevented | ✅ |
| Assets with market data | 8 |
| API key required | ❌ NO (free public REST) |
| XRP (XRPUSDT) | $1.13 | -2.56% |
| APT (APTUSDT) | $0.70 | -7.67% |
| NEAR (NEARUSDT) | $2.08 | -9.84% |
| BNB (BNBUSDT) | $587.67 | -1.95% |
| SOL (SOLUSDT) | $65.57 | -4.56% |
| ETH (ETHUSDT) | $1,670.05 | -5.30% |
| BTC (BTCUSDT) | $62,612.01 | -1.19% |
| ARB (ARBUSDT) | $0.08 | -5.54% |


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

### Proxy Environment Detection (v117F)

| Variable | Detected |
|----------|----------|
| HTTP_PROXY | ❌ NO |
| HTTPS_PROXY | ❌ NO |
| TELEGRAM_PROXY_URL | ❌ NO |
| ALL_PROXY | ❌ NO |

**Any proxy detected:** ❌ NO
**Note:** Only boolean presence is recorded — proxy addresses are NEVER logged.

---

## Pipeline Result

| Stage | Result |
|-------|--------|
| Card Family | `news_event_market_impact` |
| Gate | ✅ allow |
| Gate reason | `News event with high intensity accepted` |
| Send-Readiness | ✅ allow_test_group |
| Pipeline Passed | ✅ |
| Card observation_only | **True** |
| Card not_causal_proof | **True** |
| Run status | `sent` |

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

---

## v117F Safety Verification

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
| Result self-check | ✅ passed |
| observation_only | **True** |
| not_causal_proof | **True** |
| No deterministic causality | ✅ YES |
| No market API duplicate fetch | ✅ (fetch_count=1) |
| TG failure classification enhanced | ✅ YES |
| Proxy env boolean only | ✅ YES |
| No raw credentials in outputs | ✅ |

## v117F Test Results Summary

| Test Suite | Expected | Actual |
|------------|----------|--------|
| v117F new tests | Pass | (run) |
| v117E regression | Pass | (run) |
| v117D regression | Pass | (run) |
| v117C regression | Pass | (run) |
| v117B regression | Pass | (run) |
| v117 regression | Pass | (run) |
| v116N regression | Pass | (run) |

## v117E TG Timeout Root Cause Analysis

The v117E result (20260605_170616) showed TG NETWORK_TIMEOUT. Based on v117F enhanced diagnostics:

1. **Primary cause**: Python HTTP request to `api.telegram.org` timed out within 10s
2. **Proxy status**: Proxy env NOT detected
   If proxy is required in the network environment, the TG API call would fail without it.
3. **Resolution**: v117F captures exact failure class (N/A), proxy presence, and redacted host
4. **Recommendation**: If proxy is required, set HTTPS_PROXY environment variable; otherwise increase timeout or check network connectivity to api.telegram.org
