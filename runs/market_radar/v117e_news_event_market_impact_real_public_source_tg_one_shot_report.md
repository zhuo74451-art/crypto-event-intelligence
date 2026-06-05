# Market Radar v1.17E — News Event Market Impact Report

**Generated**: 2026-06-05T16:47:17+08:00
**Run ID**: 20260605_164648
**Task ID**: 20260605_v117e_news_event_market_impact_real_public_source_tg_one_shot

---

## News Event Public Source Status

| Check | Status |
|-------|--------|
| Sources attempted | 5 |
| Sources succeeded | 1 |
| Articles fetched | 80 |
| Events extracted | 14 |
| Event extracted (≥1) | ✅ |
| All sources unavailable | ✅ NO |

### Public Sources Used

| # | Source | Type |
|---|--------|------|
| | Binance Announcements | ok |

### Event Details (if extracted)

| Field | Value |
|-------|-------|
| Source | Binance Announcements |
| Title | Introducing Genius Terminal (GENIUS) on Binance HODLer Airdrops! Earn GENIUS With Retroactive BNB Simple Earn Subscriptions |
| Event type | airdrop |
| Intensity | medium |
| Attribution risk | direct |
| Assets affected | BNB |
| URL proof | SHA-256 redacted |
| observation_only | **True** |
| not_causal_proof | **True** |

### Market Data

| Check | Status |
|-------|--------|
| Binance market API called | ❌ |
| Assets with market data | 0 |
| API key required | ❌ NO (free public REST) |


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

## Pipeline Result

| Stage | Result |
|-------|--------|
| Card Family | `news_event_market_impact` |
| Gate | ✅ allow |
| Gate reason | `News event with medium intensity accepted` |
| Send-Readiness | ✅ allow_test_group |
| Pipeline Passed | ✅ |
| Card observation_only | **True** |
| Card not_causal_proof | **True** |
| Run status | `pipeline_passed_but_tg_not_sent` |

## TG Test Group Send

❓ **UNKNOWN** — No TG result available.

---

## Safety Verification

| Check | Status |
|-------|--------|
| External API called | ✅ |
| TG sent this run | ❌ (or skipped) |
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

## Free Public Data Sources

- **CoinDesk RSS** (https://www.coindesk.com/arc/outboundfeeds/rss/)
- **Cointelegraph RSS** (https://cointelegraph.com/rss)
- **Decrypt RSS** (https://decrypt.co/feed)
- **The Block RSS** (https://www.theblock.co/rss)
- **Binance Announcements** (public JSON API, no key)
- **Binance Public REST API** (/api/v3/ticker/24hr) — BTC/ETH/SOL market data
- No API key required for any source
- Event extraction: rule-based keyword matching (NO AI/model)

## Test Results Summary

(To be filled after running tests)

| Test Suite | Expected | Actual |
|------------|----------|--------|
| v117E tests | Pass | (run) |
| v117D regression | Pass | (run) |
| v117C regression | Pass | (run) |
| v117B regression | Pass | (run) |
| v117 regression | Pass | (run) |
| v116N regression | Pass | (run) |
