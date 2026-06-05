# Market Radar v1.16-I — Liquidation Pressure Proxy TG Test Send Report

**Generated**: 2026-06-05T13:07:20.808413+08:00
**Task ID**: 20260605_v116i_liquidation_pressure_real_free_api_tg_test_send_one_shot
**Run ID**: 20260605_124925

⚠️ **声明**: 本报告所有信号为清算压力代理信号（proxy），非真实逐笔清算数据。

---

## Executive Summary

| Field | Value |
|-------|-------|
| card_family | `liquidation_pressure` |
| audit_result | **blocked_gate_not_passed** |
| real_external_api_called | **True** |
| signals_admitted | **0/3** |
| TG test sent | **False** |
| secret_preflight_passed | **True** |
| quality_gate_any_passed | False |
| send_readiness_any_passed | False |
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
- **Endpoints used**:
  - `/api/v3/ticker/24hr` (spot)
  - `/fapi/v1/ticker/24hr` (futures)
  - `/fapi/v1/openInterest`
  - `/fapi/v1/openInterestHist`
  - `/fapi/v1/fundingRate`
  - `/futures/data/globalLongShortAccountRatio`
  - `/futures/data/takerlongshortRatio`
- **API key required**: No
- **Paid**: No (free public API)
- **Data type**: Liquidation pressure PROXY (保守代理指标，非真实逐笔清算数据)

---

## Assets Fetched

- **BTC** (BTCUSDT): price_chg=-0.59%, OI_chg=N/A, funding=+0.0013%, L/S=可用, taker=可用
- **ETH** (ETHUSDT): price_chg=-3.03%, OI_chg=N/A, funding=+0.0047%, L/S=可用, taker=可用
- **SOL** (SOLUSDT): price_chg=-3.38%, OI_chg=N/A, funding=-0.0097%, L/S=可用, taker=可用

---

## Liquidation Pressure Proxy Admission Results

| Asset | Price Chg | Score | Admitted | Type | Confirm Count | Direction |
|-------|-----------|-------|----------|------|---------------|-----------|
| BTC | -0.59% | 2.59 | False | None | 2 | long_liquidation_risk |
| ETH | -3.03% | 5.03 | False | None | 2 | long_liquidation_risk |
| SOL | -3.38% | 6.38 | False | None | 2 | long_liquidation_risk |

---

## Gate Results

### Quality Gate

| Asset | QG Passed | Blocked Reasons |
|-------|-----------|-----------------|
| BTC | False | ['missing_required_fields', 'admission_not_passed'] |
| ETH | False | ['missing_required_fields', 'admission_not_passed'] |
| SOL | False | ['missing_required_fields', 'admission_not_passed'] |

### Send-Readiness Gate

| Asset | SR Passed | TG Ready | Blocked Reasons |
|-------|-----------|----------|-----------------|
| BTC | False | False | ['quality_gate_not_passed', 'admission_not_passed'] |
| ETH | False | False | ['quality_gate_not_passed', 'admission_not_passed'] |
| SOL | False | False | ['quality_gate_not_passed', 'admission_not_passed'] |

---

## TG Send Attempts (v116I Redacted Proof)

| Asset | Attempted | Success | Msg ID Redacted | Blocked Reason |
|-------|-----------|---------|-----------------|----------------|
| BTC | N/A (not admitted) | N/A | N/A | admission_not_passed |
| ETH | N/A (not admitted) | N/A | N/A | admission_not_passed |
| SOL | N/A (not admitted) | N/A | N/A | admission_not_passed |

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
| proxy disclaimer present | True |
| not masquerading as real tape | True |

---

## Conclusion

**Audit result**: `blocked_gate_not_passed`

No assets reached liquidation pressure proxy admission thresholds. Gate blocked_gate_not_passed. No cards generated, no TG send attempted.

⚠️ **代理数据声明**: 本报告所有指标均为清算压力代理信号。
Binance REST API 不提供直接清算流数据。压力评分基于价格变动、OI变化、
资金费率、多空比和taker买卖比的复合代理估算。实际清算情况以交易所清算数据为准。
