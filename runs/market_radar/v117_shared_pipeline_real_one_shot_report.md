# Market Radar v1.17 — Real One-Shot Report

**Generated**: 2026-06-05T15:53:17+08:00
**Run ID**: 20260605_155249

---

## Real Free API Results

| Card Family | API Success | Gate | TG Status | Passed |
|-------------|-------------|------|-----------|--------|

| multi_asset_market_sync | ✅ | ✅ allow | skipped | ✅ |
| price_oi_volume_anomaly | ✅ | ✅ allow | skipped | ✅ |


## TG Test Group Send

⚠ **Skipped** — 2 attempt(s) skipped.
Reason: TG safe config not available (TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID not set in environment).
This is expected and NOT a pipeline failure.


## Safety Verification

| Check | Status |
|-------|--------|
| External API called | ✅ |
| TG sent this run | ❌ |
| Production send | ❌ NEVER |
| Credentials printed | ❌ NEVER |
| Daemon/loop started | ❌ NEVER |
| Files deleted | ❌ NEVER |
| Evidence ledger clean | ✅ |

## Free API Data Sources

- **Binance Public REST API** (`/api/v3/ticker/24hr`): BTC/ETH/SOL 24hr ticker data
- **Binance Futures Public API** (`/fapi/v1/openInterest`): Open interest data
- No API key required for any endpoint
