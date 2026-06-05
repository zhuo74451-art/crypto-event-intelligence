# Market Radar v1.17C — Safe TG Config Loader + TG Re-run Report

**Generated**: 2026-06-05T16:20:47+08:00
**Run ID**: 20260605_162029
**Task ID**: 20260605_v117c_safe_tg_config_loader_real_test_group_rerun

---

## v117B Why Skipped

v117B checked `os.environ.get("TELEGRAM_BOT_TOKEN")` and `os.environ.get("TELEGRAM_CHAT_ID")`
in a fresh Python process. Neither was set → TG send was truthfully skipped with status
`skipped` and reason `tg_test_send_skipped_missing_safe_config`.

v117C fixes this by actively probing for and loading TG credentials from the project's
canonical safe loader chain (`scripts/load_local_secrets.ps1` → `config/local_secrets.ps1`)
via a PowerShell subprocess — the same pattern used by `send_local_news_flow_preview_to_tg.py`.


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

## Binance Real API Status

| Check | Status |
|-------|--------|
| API called | ✅ |
| API success | ✅ |
| Assets retrieved | 3 |

### Asset Details

| Symbol | Price OK | 24h Change % | Volume OK |
|--------|----------|-------------|-----------|
| BTCUSDT | ✅ | -1.17% | ✅ |
| ETHUSDT | ✅ | -5.79% | ✅ |
| SOLUSDT | ✅ | -4.43% | ✅ |

---

## Pipeline Result

| Stage | Result |
|-------|--------|
| Card Family | `multi_asset_market_sync` |
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

> v117C successfully loaded TG config via PowerShell subprocess
> (powershell_subprocess_dot_source) and sent 1 test message.

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

- **Binance Public REST API** (`/api/v3/ticker/24hr`): BTC/ETH/SOL 24hr ticker data
- No API key required

## Test Results Summary

(To be filled after running tests)

| Test Suite | Expected | Actual |
|------------|----------|--------|
| v117C tests | Pass | (run) |
| v117B regression | Pass | (run) |
| v117 regression | Pass | (run) |
| v116N regression | Pass | (run) |
