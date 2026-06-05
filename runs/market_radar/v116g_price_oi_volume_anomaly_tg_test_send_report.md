# Market Radar v1.16-G — Price/OI/Volume Anomaly TG Test Send Report

**Generated**: 2026-06-05T12:32:11.794794+08:00
**Task ID**: 20260605_v116g_price_oi_volume_anomaly_real_free_api_tg_test_send_one_shot
**Run ID**: 20260605_121906

---

## Executive Summary

| Field | Value |
|-------|-------|
| card_family | `price_oi_volume_anomaly` |
| audit_result | **real_free_api_tg_test_sent** |
| real_external_api_called | **True** |
| signals_admitted | **2/3** |
| TG test sent | **True** |
| secret_preflight_passed | **True** |
| quality_gate_any_passed | True |
| send_readiness_any_passed | True |
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
- **Endpoints used**: `/api/v3/ticker/24hr`, `/fapi/v1/ticker/24hr`, `/fapi/v1/openInterest`, `/fapi/v1/openInterestHist`
- **API key required**: No
- **Paid**: No (free public API)

---

## Assets Fetched

- **BTC** (BTCUSDT): price_chg=-2.24%, OI_chg=N/A, OI_hist_avail=False
- **ETH** (ETHUSDT): price_chg=-4.44%, OI_chg=N/A, OI_hist_avail=False
- **SOL** (SOLUSDT): price_chg=-5.46%, OI_chg=N/A, OI_hist_avail=False

---

## Anomaly Admission Results

| Asset | Price Chg | Admitted | Anomaly Type | Confirm Factors | OI Missing |
|-------|-----------|----------|-------------|-----------------|------------|
| BTC | -2.24% | False | None | 2 | True |
| ETH | -4.44% | True | down_anomaly_confirmed | 2 | True |
| SOL | -5.46% | True | down_anomaly_confirmed | 1 | True |

---

## Gate Results

### Quality Gate

| Asset | QG Passed | Blocked Reasons |
|-------|-----------|-----------------|
| BTC | False | ['missing_required_fields', 'card_text_too_short_or_missing', 'admission_not_passed'] |
| ETH | True | [] |
| SOL | True | [] |

### Send-Readiness Gate

| Asset | SR Passed | TG Ready | Blocked Reasons |
|-------|-----------|----------|-----------------|
| BTC | False | False | ['quality_gate_not_passed', 'admission_not_passed'] |
| ETH | True | True | [] |
| SOL | True | True | [] |

---

## TG Send Attempts (v116G Redacted Proof)

| Asset | Attempted | Success | Msg ID Redacted | Blocked Reason |
|-------|-----------|---------|-----------------|----------------|
| BTC | N/A (not admitted) | N/A | N/A | admission_not_passed |
| ETH | True | True | sha256:3045ad039274b9fc | N/A |
| SOL | True | True | sha256:1070a982af22fe71 | N/A |

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

TG test group send **SUCCEEDED**. Anomaly card(s) delivered to test group (one-shot).
Redacted message proof: sha256:1070a982af22fe71
