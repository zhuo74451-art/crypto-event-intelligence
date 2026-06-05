# Market Radar v1.17B — Shared Pipeline TG One-Shot Report

**Generated**: 2026-06-05T16:06:01+08:00
**Run ID**: 20260605_160558
**Task ID**: 20260605_v117b_shared_pipeline_tg_test_group_one_shot_safe_config

---

## Binance Real API Status

| Check | Status |
|-------|--------|
| API called | ✅ |
| API success | ✅ |
| Assets retrieved | 3 |

### Asset Details

| Symbol | Price OK | 24h Change % | Volume OK |
|--------|----------|-------------|-----------|
| BTCUSDT | ✅ | -1.52% | ✅ |
| ETHUSDT | ✅ | -6.07% | ✅ |
| SOLUSDT | ✅ | -5.09% | ✅ |

---

## Pipeline Result

| Stage | Result |
|-------|--------|
| Card Family | `multi_asset_market_sync` |
| Gate | ✅ allow |
| Send-Readiness | ✅ allow_test_group |
| Pipeline Passed | ✅ |

## TG Test Group Send

⚠ **SKIPPED** — TG test group send not attempted.

- Status: `skipped`
- Reason: `tg_test_send_skipped_missing_safe_config: TELEGRAM_BOT_TOKEN and/or TELEGRAM_CHAT_ID not set`
- This is expected and NOT a pipeline failure.
- Test group send requires TELEGRAM_BOT_TOKEN + TELEGRAM_CHAT_ID env vars.

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

## Free API Data Source

- **Binance Public REST API** (`/api/v3/ticker/24hr`): BTC/ETH/SOL 24hr ticker data
- No API key required
