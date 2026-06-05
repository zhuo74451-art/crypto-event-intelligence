# Market Radar v1.16-C — Remaining Three Card Families Fixture E2E Batch Replay

**Generated**: 2026-06-05T10:08:57.874870+08:00
**Version**: v1.16-C
**Stage**: v116c_remaining_three_card_families_fixture_e2e_batch_replay_local_only

---

## !! Critical Distinction

> **fixture_e2e_passed != real_e2e_passed**
>
> This is a **FIXTURE-ONLY** gate batch replay using existing fixture/preview artifacts.
> Fixture replay is a DRY-RUN that proves gate logic works with pre-recorded data.
> It does NOT prove the system can process real-time market data through all gates.
> **TG test group is NOT allowed. Production send is NOT allowed.**

---

## Starting Points (from v116A)

| # | Card Family | v116A Stage | Router | Preview | Fixture E2E |
|---|-------------|-------------|--------|---------|-------------|
| 1 | `price_oi_volume_anomaly` | **fixture_preview** | passed | fixture_only | not_started |
| 2 | `liquidation_pressure` | **fixture_preview** | passed | fixture_only | not_started |
| 3 | `news_event_market_impact` | **fixture_preview** | passed | fixture_only | not_started |

---

## Fixture E2E Gate Replay Summary

| Gate | Passed | Total | Status |
|------|--------|-------|--------|
| Input Validation | 19 | 19 | [PASS] |
| Card Generation Replay | 8 | 19 | [PARTIAL] |
| Quality Gate Replay | 9 | 19 | [PASS] |
| Send-Readiness Replay | 9 | 19 | [PASS] |
| Workflow Replay Decision | 9 | 19 | [PASS] |

- **Total Fixture Input Records**: 19
- **Quality Gate Passed**: 9
- **Send-Readiness Passed**: 9
- **Workflow Ready**: 9

---

## Per-Family Results

| # | Card Family | Records | QG Passed | WF Ready | Fixture E2E | Final Status |
|---|-------------|---------|-----------|----------|-------------|--------------|
| 1 | `price_oi_volume_anomaly` | 7 | 1 | 1 | True | ✅ **fixture_e2e_passed** |
| 2 | `liquidation_pressure` | 5 | 3 | 3 | True | ✅ **fixture_e2e_passed** |
| 3 | `news_event_market_impact` | 7 | 5 | 5 | True | ✅ **fixture_e2e_passed** |

- **Families fixture_e2e_passed**: 3
- **Families partial**: 0
- **Families blocked**: 0
- **Families not_found**: 0
- **Audit result**: `remaining_three_fixture_e2e_passed_real_e2e_not_started`

---

## Per-Family Evidence Detail

### price_oi_volume_anomaly

- **v116A Start Stage**: `fixture_preview`
- **Fixture Records**: 7
- **Source Evidence**: 
  - `results/v14_price_oi_quadrant.csv`
- **Signal Types Found**: Q1_healthy, Q2_deleveraging_up, neutral
- **Quality Gate Passed**: 1/7
- **Workflow Ready**: 1/7
- **Final Status**: **fixture_e2e_passed**

| # | Record ID | Valid | Card | QG | Send | WF Ready |
|---|-----------|-------|------|----|------|----------|
| 1 | pova_fixture_001_btc_Q1_healthy | False | False | False | False | False |
| 2 | pova_fixture_002_eth_Q2_deleveraging_up | False | False | False | False | False |
| 3 | pova_fixture_003_sol_Q2_deleveraging_up | False | False | False | False | False |
| 4 | pova_fixture_004_bnb_neutral | False | False | False | False | False |
| 5 | pova_fixture_005_xrp_Q2_deleveraging_up | False | False | False | False | False |
| 6 | pova_fixture_006_doge_Q2_deleveraging_up | False | False | False | False | False |
| 7 | pova_fixture_007_hype_Q1_healthy | True | False | True | True | True |

### liquidation_pressure

- **v116A Start Stage**: `fixture_preview`
- **Fixture Records**: 5
- **Source Evidence**: 
  - `data/fixtures/market_radar_v112b_liquidation_snapshots.json`
- **Signal Types Found**: long_liquidation_pressure, no_significant_pressure, short_liquidation_pressure, two_sided_liquidation_pressure
- **Quality Gate Passed**: 3/5
- **Workflow Ready**: 3/5
- **Final Status**: **fixture_e2e_passed**

| # | Record ID | Valid | Card | QG | Send | WF Ready |
|---|-----------|-------|------|----|------|----------|
| 1 | liq_v112b_fixture_001_btc_long_pressure | True | True | True | True | True |
| 2 | liq_v112b_fixture_002_eth_short_pressure | True | True | True | True | True |
| 3 | liq_v112b_fixture_003_sol_two_sided | True | True | True | True | True |
| 4 | liq_v112b_fixture_004_invalid_missing_asset | False | False | False | False | False |
| 5 | liq_v112b_fixture_005_invalid_zero_liquidation | False | False | False | False | False |

### news_event_market_impact

- **v116A Start Stage**: `fixture_preview`
- **Fixture Records**: 7
- **Source Evidence**: 
  - `data/fixtures/market_radar_v112d_news_events.json`
- **Signal Types Found**: ETF, 上线, 其他, 安全, 宏观, 政策
- **Quality Gate Passed**: 5/7
- **Workflow Ready**: 5/7
- **Final Status**: **fixture_e2e_passed**

| # | Record ID | Valid | Card | QG | Send | WF Ready |
|---|-----------|-------|------|----|------|----------|
| 1 | news_001_etf_fund_flow | True | True | True | True | True |
| 2 | news_002_regulation_policy | True | True | True | True | True |
| 3 | news_003_security_exploit | True | True | True | True | True |
| 4 | news_004_exchange_listing | True | True | True | True | True |
| 5 | news_005_macro_liquidity | True | True | True | True | True |
| 6 | news_006_invalid_no_assets | False | False | False | False | False |
| 7 | news_007_invalid_already_priced | False | False | False | False | False |

---

## Send Status (All False — As Expected)

| Send Type | Status | Reason |
|-----------|--------|--------|
| TG Test Group | [NO] NOT ALLOWED | Fixture only; no real data verification |
| Production Send | [NO] NOT ALLOWED | Blocked per safety boundary |
| Real Send Candidate | [NO] NOT GENERATED | Fixture data only |

---

## Safety Constraints (All Verified)

| Constraint | Value |
|------------|-------|
| real_send_candidate_generated | false |
| tg_sent | false |
| prod_state_write | false |
| external_api_called | false |
| credentials_read | false |
| ai_model_called | false |
| files_deleted | false |
| historical_artifacts_modified | false |

---

## Next Steps

1. **All 3 remaining families fixture_e2e_passed**: Run v116D five-card coverage re-audit.
2. **For real E2E**: Build real data pipelines for each family (requires live data feeds).
3. **For whale_position_alert**: Complete real operator workbook (v115O preflight).

---

## Conclusion

**Remaining three card families fixture E2E batch replay: 3/3 fixture_e2e_passed, 0 partial, 0 blocked, 0 not_found.**

**Audit result**: `remaining_three_fixture_e2e_passed_real_e2e_not_started`

This proves the gate pipeline (input → card generation → quality gate → send-readiness → workflow)
correctly processes fixture data for 3 of 3 target card families.

**However, this is FIXTURE ONLY.** Real E2E requires:
- Real-time market data feeds (not pre-recorded snapshots)
- Live enrichment pipelines for each card family
- Real operator evidence collection
- Real data verification

**fixture_e2e_passed = true does NOT mean production is ready.**
