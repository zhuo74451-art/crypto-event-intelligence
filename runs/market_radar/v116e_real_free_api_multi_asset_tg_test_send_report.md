# Market Radar v1.16-E — TG Test Send Report

**Generated**: 2026-06-05T11:59:27.049839+08:00
**Task ID**: 20260605_v116e_real_free_api_multi_asset_tg_test_send_rerun_with_safe_secret_preflight_one_shot
**Run ID**: 20260605_113537

---

## Executive Summary

| Field | Value |
|-------|-------|
| card_family | `multi_asset_market_sync` |
| audit_result | **real_free_api_tg_test_sent** |
| real_external_api_called | **True** |
| TG test sent | **True** |
| secret_preflight_passed | **True** |
| quality_gate_passed | True |
| send_readiness_passed | True |
| TG sender available | True |

---

## Safe Secret Preflight

| Check | Result |
|-------|--------|
| preflight_run | True |
| telegram_bot_token_present | True |
| telegram_chat_id_present | True |
| preflight_passed | True |
| values_printed | False |
| values_logged | False |
| values_in_output | False |

---

## API Source

- **Source**: Binance public REST endpoints
- **Endpoints used**: `/api/v3/ticker/24hr`, `/fapi/v1/ticker/24hr`, `/fapi/v1/fundingRate`, `/fapi/v1/openInterest`, `/fapi/v1/openInterestHist`
- **API key required**: No
- **Paid**: No (free public API)

---

## Assets Fetched

- **BTC** (BTCUSDT): price_chg=-2.51%, OI_chg=+0.00%, funding=0.0013%
- **ETH** (ETHUSDT): price_chg=-4.37%, OI_chg=+0.00%, funding=0.0047%
- **SOL** (SOLUSDT): price_chg=-6.21%, OI_chg=+0.00%, funding=-0.0097%

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
| secret_preflight_passed | True |
| tg_sender_available | True |
| bot_token_configured | True |
| chat_id_configured | True |
| signal_valid | True |
| quality_gate_passed | True |
| **send_readiness_passed** | **True** |

---

## TG Send Attempt (v116E Redacted Proof)

| Field | Value |
|-------|-------|
| attempted | True |
| success | True |
| message_id_present | True |
| message_id_redacted | sha256:4fbb9cf6972a100c |
| target_type | test_group (NOT production channel) |
| one_shot | True |
| production_send | False |
| blocked_reason | N/A |

---

## Safety Confirmation

| Constraint | Status |
|------------|--------|
| secret_preflight_run | True |
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
| token in outputs | False (redacted proof only) |
| chat_id in outputs | False (redacted proof only) |

---

## Conclusion

**Audit result**: `real_free_api_tg_test_sent`

TG test group send **SUCCEEDED**. Card delivered to test group (one-shot).
Redacted message proof: sha256:4fbb9cf6972a100c
