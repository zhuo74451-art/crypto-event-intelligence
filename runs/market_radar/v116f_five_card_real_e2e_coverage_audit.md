# Market Radar v1.16-F — Five Card Real E2E Coverage Audit

**Generated**: 2026-06-05 12:22:33 UTC+8
**Version**: v1.16-F
**Task ID**: 20260605_v116f_five_card_real_e2e_coverage_audit_and_tg_evidence_ledger_local_only
**Run ID**: 20260605_113537

---

## Executive Summary

| Metric | Value |
|--------|-------|
| Card families audited | 5 |
| Fixture E2E passed | 5/5 |
| Real API + TG test sent | 1/5 |
| Production send ready | 0/5 |
| **Overall status** | **1_of_5_real_api_tg_test_sent_0_of_5_production_ready** |

**Conclusion**: 5/5 card families have passed fixture E2E. 1/5 have real API + TG test sent (multi_asset_market_sync via v116E). 0/5 are production send ready. The remaining 4 card families need real data pipeline integration before real E2E can be verified.

## Five Card Real E2E Coverage Matrix

| # | Card Family | Router | Fixture E2E | Real API | Card Gen | QG | Send Ready | TG Test Sent | TG Ready | Prod Ready | Real E2E Status |
|---|-------------|--------|-------------|----------|----------|----|------------|--------------|----------|------------|------------------|
| 1 | **Whale Position Alert** | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | `blocked_manual_evidence` |
| 2 | **Multi-Asset Market Sync** | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ | `real_free_api_tg_test_sent` |
| 3 | **Price/OI/Volume Anomaly** | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | `fixture_e2e_passed_real_not_started` |
| 4 | **Liquidation Pressure** | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | `fixture_e2e_passed_real_not_started` |
| 5 | **News Event Market Impact** | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | `fixture_e2e_passed_real_not_started` |

> **Key**: ✅ = true/passed, ❌ = false/not done

## Per-Family Real E2E Status Details

### Whale Position Alert (`whale_position_alert`)

- **Real E2E Status**: `blocked_manual_evidence`
- **Router Passed**: True
- **Fixture E2E Passed**: True
- **Real External API Called**: False
- **Real Card Generated**: False
- **Quality Gate Passed**: False
- **Send Readiness Passed**: False
- **TG Test Sent**: False
- **TG Test Group Ready**: False
- **Production Send Ready**: False
- **Current Blocker**: Real operator workbook has empty fields for all 4 addresses. Requires real operator evidence collection (v115O preflight) before gate rerun.
- **Next Action**: Complete real operator workbook (v115F) with address verification evidence, then rerun v115R submission validator and v115Q fixture E2E gates.
- **Evidence Sources**:
  - v116A: whale_position_alert_fixture_e2e_passed=true, real_e2e_passed=false
  - v115Q: fixture E2E gate replay 4/4 workflow-ready
  - v115R: real workbook submission blocked (empty fields)

### Multi-Asset Market Sync (`multi_asset_market_sync`)

- **Real E2E Status**: `real_free_api_tg_test_sent`
- **Router Passed**: True
- **Fixture E2E Passed**: True
- **Real External API Called**: True
- **Real Card Generated**: True
- **Quality Gate Passed**: True
- **Send Readiness Passed**: True
- **TG Test Sent**: True
- **TG Test Group Ready**: True
- **Production Send Ready**: False
- **Next Action**: Multi-asset market sync is the first card family to reach real_free_api_tg_test_sent. Next: validate TG delivery quality, then consider production readiness gate.
- **Evidence Sources**:
  - v116B: fixture_e2e_passed=true, 7/8 QG passed, 5/8 workflow-ready
  - v116E: real Binance free API (BTC/ETH/SOL), TG test group one-shot sent, message proof sha256:4fbb9cf6972a100c, quality_gate_passed=true, send_readiness_passed=true, secret_preflight_passed=true

### Price/OI/Volume Anomaly (`price_oi_volume_anomaly`)

- **Real E2E Status**: `fixture_e2e_passed_real_not_started`
- **Router Passed**: True
- **Fixture E2E Passed**: True
- **Real External API Called**: False
- **Real Card Generated**: False
- **Quality Gate Passed**: False
- **Send Readiness Passed**: False
- **TG Test Sent**: False
- **TG Test Group Ready**: False
- **Production Send Ready**: False
- **Current Blocker**: Fixtures from derivative analysis (not raw market data). Only 1/7 fixture records passed QG. Free API sources exist (Binance ticker/24hr, openInterest) but integration not built.
- **Next Action**: Build real data adapter using Binance free API ticker/24hr + openInterest. Rerun quality gate against real data. Expected risk: low QG pass rate from v116C precedent (1/7).
- **Evidence Sources**:
  - v116A: router_passed, fixture_preview
  - v116C: fixture_e2e_passed=true, QG=1/7, workflow_ready=1, real_e2e_passed_count=0

### Liquidation Pressure (`liquidation_pressure`)

- **Real E2E Status**: `fixture_e2e_passed_real_not_started`
- **Router Passed**: True
- **Fixture E2E Passed**: True
- **Real External API Called**: False
- **Real Card Generated**: False
- **Quality Gate Passed**: False
- **Send Readiness Passed**: False
- **TG Test Sent**: False
- **TG Test Group Ready**: False
- **Production Send Ready**: False
- **Current Blocker**: No real liquidation data pipeline. Free API sources exist (Binance liquidation order streams, Hyperliquid API) but integration not built.
- **Next Action**: Build real data adapter using free liquidation data sources. Rerun quality gate. v116C shows 3/5 QG passed on fixtures — better baseline than price_oi_volume_anomaly.
- **Evidence Sources**:
  - v116A: router_passed, fixture_preview
  - v116C: fixture_e2e_passed=true, QG=3/5, workflow_ready=3, real_e2e_passed_count=0

### News Event Market Impact (`news_event_market_impact`)

- **Real E2E Status**: `fixture_e2e_passed_real_not_started`
- **Router Passed**: True
- **Fixture E2E Passed**: True
- **Real External API Called**: False
- **Real Card Generated**: False
- **Quality Gate Passed**: False
- **Send Readiness Passed**: False
- **TG Test Sent**: False
- **TG Test Group Ready**: False
- **Production Send Ready**: False
- **Current Blocker**: News event data requires NLP/sentiment processing. Free API sources exist (CryptoPanic, RSS feeds) but pipeline involves text processing not purely numeric market data. Higher implementation complexity than price/liquidation cards.
- **Next Action**: Build real data adapter using free news API (CryptoPanic free tier). Highest fixture QG base: 5/7 passed in v116C. Defer until price_oi_volume_anomaly and liquidation_pressure real E2E complete, to reuse patterns.
- **Evidence Sources**:
  - v116A: router_passed, fixture_preview
  - v116C: fixture_e2e_passed=true, QG=5/7, workflow_ready=5, real_e2e_passed_count=0

## ⭐ multi_asset_market_sync — First Real E2E + TG Test Sent

This is the **only** card family that has completed real API + TG test send (v116E).

- Free Binance public API (no API key required)
- 3 assets fetched: BTCUSDT, ETHUSDT, SOLUSDT
- Market-wide risk-off sync detected (score=59.8, direction=down)
- Quality gate: PASSED
- Send readiness: PASSED
- Secret preflight: PASSED
- TG test group one-shot send: SUCCESS
- Message proof (redacted): `sha256:4fbb9cf6972a100c`
- **Production send ready: FALSE** (not yet approved)

## Safety Constraints (All Verified)

| Constraint | v116F Status |
|------------|-------------|
| external_api_called_this_run | false |
| tg_sent_this_run | false |
| prod_state_write | false |
| ai_model_called | false |
| credentials_read | false |
| files_deleted | false |
| historical_artifacts_modified | false |
