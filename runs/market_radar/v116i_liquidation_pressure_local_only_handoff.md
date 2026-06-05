# Market Radar v1.16-I — Handoff: Liquidation Pressure Proxy Real Free API TG Test Send

**Generated**: 2026-06-05T13:07:20.809223+08:00
**Task ID**: 20260605_v116i_liquidation_pressure_real_free_api_tg_test_send_one_shot
**Run ID**: 20260605_124925
**Status**: partial
**result_source**: claude_code_executor
**executor_lane**: 1
**project_label**: market_radar

---

## Result Summary

| Metric | Value |
|--------|-------|
| card_family | `liquidation_pressure` |
| audit_result | `blocked_gate_not_passed` |
| real_external_api_called | **True** |
| real_free_api_tg_test_sent | **False** |
| secret_preflight_passed | **True** |
| signals_generated | 3 |
| signals_admitted | 0 |
| api_key_required | False |
| fixture_only | False |
| production_send_ready | False |
| prod_state_write | False |
| ai_model_called | False |
| daemon_or_loop_started | False |
| files_deleted | False |
| proxy_disclaimer | True (清算压力代理信号) |

---

## v116I Safe Secret Preflight

| Check | Value |
|-------|-------|
| preflight_run | True |
| telegram_bot_token_present | True |
| telegram_chat_id_present | True |
| preflight_passed | True |
| raw values printed | False |
| raw values in any output | False |

---

## Admission Details

| Asset | Price Chg | Score | Admitted | Type | Confirm Count |
|-------|-----------|-------|----------|------|---------------|
| BTC | -0.59% | 2.59 | False | None | 2 |
| ETH | -3.03% | 5.03 | False | None | 2 |
| SOL | -3.38% | 6.38 | False | None | 2 |

---

## Data Availability

| Asset | Funding | L/S Ratio | Taker B/S | OI History | Limitations |
|-------|---------|-----------|-----------|------------|-------------|
| BTC | True | True | True | False | 1 |
| ETH | True | True | True | False | 1 |
| SOL | True | True | True | False | 1 |

---

## Files Produced

- `C:\Users\PC\Desktop\Projects\事件情报系统\results\market_radar_v116i_liquidation_pressure_raw_snapshots.json`
- `C:\Users\PC\Desktop\Projects\事件情报系统\results\market_radar_v116i_liquidation_pressure_signal_records.jsonl`
- `C:\Users\PC\Desktop\Projects\事件情报系统\results\market_radar_v116i_liquidation_pressure_card_records.jsonl`
- `C:\Users\PC\Desktop\Projects\事件情报系统\results\market_radar_v116i_liquidation_pressure_quality_gate_records.jsonl`
- `C:\Users\PC\Desktop\Projects\事件情报系统\results\market_radar_v116i_liquidation_pressure_send_readiness_records.jsonl`
- `C:\Users\PC\Desktop\Projects\事件情报系统\results\market_radar_v116i_liquidation_pressure_tg_send_attempts.jsonl`
- `C:\Users\PC\Desktop\Projects\事件情报系统\results\market_radar_v116i_liquidation_pressure_tg_test_send_result.json`
- `C:\Users\PC\Desktop\Projects\事件情报系统\runs\market_radar\v116i_liquidation_pressure_card_preview.md`
- `C:\Users\PC\Desktop\Projects\事件情报系统\runs\market_radar\v116i_liquidation_pressure_tg_test_send_report.md`
- `C:\Users\PC\Desktop\Projects\事件情报系统\runs\market_radar\v116i_liquidation_pressure_local_only_handoff.md`

---

## Blocked Reason (if any)

None

---

## TG Send Proof (redacted — v116I standard)

message_id_present: False
message_id_redacted: None
token_in_output: False
chat_id_in_output: False

---

## Safety Confirmation

- [PASS] Secret preflight executed — boolean only, no raw values
- [PASS] No production channel send
- [PASS] No production state written
- [PASS] No AI/model called
- [PASS] No paid API called
- [PASS] No credentials printed to output
- [PASS] No files deleted
- [PASS] No daemon/loop started
- [PASS] One-shot execution only
- [PASS] TG target is test group, not channel
- [PASS] Only redacted message proof recorded
- [PASS] Conservative liquidation pressure proxy admission rules applied
- [PASS] Cards explicitly state liquidation pressure proxy (清算压力代理信号)
- [PASS] No masquerading as real liquidation tape data

---

## Unfinished Items / Risks

1. This is a ONE-SHOT test. No continuous monitoring or automated resend.
2. Liquidation pressure is a PROXY — Binance REST does not provide direct liquidation order data.
3. Long/short ratio endpoint and taker buy/sell ratio endpoint may be unavailable on some Binance API versions; handled via fallback.
4. OI change % relies on 5-minute historical comparison from Binance OI history endpoint; may be noisy.
5. Funding rate extreme thresholds are conservative; may miss moderate funding stress.
6. Proxy pressure score is a composite of up to 4 indicators; missing indicators reduce score but still allow admission with sufficient price move.
7. TG test group send depends on environment variables set by load_local_secrets.ps1.
8. During calm market periods, liquidation pressure proxy signals may not meet admission thresholds.
9. Cross-exchange liquidation data (e.g., Hyperliquid API) not integrated in this version.
10. Cards correctly identify as proxy signals — downstream consumers must not misinterpret as real liquidation tape.
