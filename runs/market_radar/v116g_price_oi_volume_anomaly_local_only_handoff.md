# Market Radar v1.16-G — Handoff: Price/OI/Volume Anomaly Real Free API TG Test Send

**Generated**: 2026-06-05T12:32:11.795687+08:00
**Task ID**: 20260605_v116g_price_oi_volume_anomaly_real_free_api_tg_test_send_one_shot
**Run ID**: 20260605_121906
**Status**: done
**result_source**: claude_code_executor
**executor_lane**: 1
**project_label**: market_radar

---

## Result Summary

| Metric | Value |
|--------|-------|
| card_family | `price_oi_volume_anomaly` |
| audit_result | `real_free_api_tg_test_sent` |
| real_external_api_called | **True** |
| real_free_api_tg_test_sent | **True** |
| secret_preflight_passed | **True** |
| signals_generated | 3 |
| signals_admitted | 2 |
| api_key_required | False |
| fixture_only | False |
| production_send_ready | False |
| prod_state_write | False |
| ai_model_called | False |
| daemon_or_loop_started | False |
| files_deleted | False |

---

## v116G Safe Secret Preflight

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

| Asset | Price Chg | Admitted | Anomaly Type | OI Missing |
|-------|-----------|----------|-------------|------------|
| BTC | -2.24% | False | None | True |
| ETH | -4.44% | True | down_anomaly_confirmed | True |
| SOL | -5.46% | True | down_anomaly_confirmed | True |

---

## Files Produced

- `C:\Users\PC\Desktop\Projects\事件情报系统\results\market_radar_v116g_price_oi_volume_anomaly_raw_snapshots.json`
- `C:\Users\PC\Desktop\Projects\事件情报系统\results\market_radar_v116g_price_oi_volume_anomaly_signal_records.jsonl`
- `C:\Users\PC\Desktop\Projects\事件情报系统\results\market_radar_v116g_price_oi_volume_anomaly_card_records.jsonl`
- `C:\Users\PC\Desktop\Projects\事件情报系统\results\market_radar_v116g_price_oi_volume_anomaly_quality_gate_records.jsonl`
- `C:\Users\PC\Desktop\Projects\事件情报系统\results\market_radar_v116g_price_oi_volume_anomaly_send_readiness_records.jsonl`
- `C:\Users\PC\Desktop\Projects\事件情报系统\results\market_radar_v116g_price_oi_volume_anomaly_tg_send_attempts.jsonl`
- `C:\Users\PC\Desktop\Projects\事件情报系统\results\market_radar_v116g_price_oi_volume_anomaly_tg_test_send_result.json`
- `C:\Users\PC\Desktop\Projects\事件情报系统\runs\market_radar\v116g_price_oi_volume_anomaly_card_preview.md`
- `C:\Users\PC\Desktop\Projects\事件情报系统\runs\market_radar\v116g_price_oi_volume_anomaly_tg_test_send_report.md`
- `C:\Users\PC\Desktop\Projects\事件情报系统\runs\market_radar\v116g_price_oi_volume_anomaly_local_only_handoff.md`

---

## Blocked Reason (if any)

N/A — TG test send succeeded

---

## TG Send Proof (redacted — v116G standard)

message_id_present: True
message_id_redacted: sha256:1070a982af22fe71
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
- [PASS] Conservative anomaly admission rules applied

---

## Unfinished Items / Risks

1. This is a ONE-SHOT test. No continuous monitoring or automated resend.
2. OI change % relies on 5-minute historical comparison from Binance OI history endpoint; may be noisy.
3. OI history endpoint may return insufficient data points for some assets; handled via fallback.
4. Volume confirmation uses spot quote volume threshold; may not capture futures-specific volume anomalies.
5. TG test group send depends on environment variables set by load_local_secrets.ps1.
6. Conservative admission thresholds (4%/5%) may miss moderate but meaningful anomalies.
7. No multi-timeframe analysis; only 24h window currently evaluated.
