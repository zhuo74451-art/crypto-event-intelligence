# Market Radar v1.16-D — TG Test Send Report

**Generated**: 2026-06-05T11:48:50.334452+08:00
**Task ID**: 20260605_v116d_real_free_api_multi_asset_tg_test_send_one_shot
**Run ID**: 20260605_113537

---

## Executive Summary

| Field | Value |
|-------|-------|
| card_family | `multi_asset_market_sync` |
| audit_result | **real_free_api_card_ready_tg_blocked_missing_sender** |
| real_external_api_called | **True** |
| TG test sent | **False** |
| quality_gate_passed | True |
| send_readiness_passed | False |
| TG sender available | False |

---

## API Source

- **Source**: Binance public REST endpoints
- **Endpoints used**: `/api/v3/ticker/24hr`, `/fapi/v1/ticker/24hr`, `/fapi/v1/fundingRate`, `/fapi/v1/openInterest`, `/fapi/v1/openInterestHist`
- **API key required**: No
- **Paid**: No (free public API)

---

## Assets Fetched

- **BTC** (BTCUSDT): price_chg=-2.45%, OI_chg=+0.00%, funding=0.0013%
- **ETH** (ETHUSDT): price_chg=-4.14%, OI_chg=+0.00%, funding=0.0047%
- **SOL** (SOLUSDT): price_chg=-6.10%, OI_chg=+0.00%, funding=-0.0097%

---

## Gate Results

### Quality Gate

| Check | Result |
|-------|--------|
| required_fields_present | True |
| assets_count_valid | True |
| card_text_present | True |
| no_forbidden_terms | True |
| no_trading_advice | True |
| api_source_ok | True |
| **quality_gate_passed** | **True** |

### Send-Readiness Gate

| Check | Result |
|-------|--------|
| tg_sender_available | False |
| bot_token_configured | False |
| chat_id_configured | False |
| signal_valid | True |
| quality_gate_passed | True |
| **send_readiness_passed** | **False** |

Blocked reasons: ['tg_bot_token_not_configured', 'tg_chat_id_not_configured']

---

## TG Send Attempt

| Field | Value |
|-------|-------|
| attempted | False |
| success | False |
| message_id | None |
| target_type | test_group (NOT production channel) |
| blocked_reason | send_readiness_not_passed |

---

## Safety Confirmation

| Constraint | Status |
|------------|--------|
| real_external_api_called | True |
| fixture_only | False |
| production_send_ready | False |
| prod_state_write | False |
| ai_model_called | False |
| credentials_printed | False |
| daemon_or_loop_started | False |
| files_deleted | False |
| TG target is test group | True |
| TG target is channel | False |
| api_key_required | False |
| one_shot (not loop) | True |

---

## Conclusion

**Audit result**: `real_free_api_card_ready_tg_blocked_missing_sender`

Card was generated and passed all gates, but TG send was **blocked** because: send_readiness_not_passed. Card content is ready for manual review.
