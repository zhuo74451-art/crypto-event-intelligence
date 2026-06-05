# Market Radar v1.17D — Price/OI/Volume Anomaly Real Card + TG One-Shot Handoff

**Generated**: 2026-06-05T16:32:39+08:00
**Run ID**: 20260605_163218
**Task ID**: 20260605_v117d_price_oi_volume_real_card_shared_pipeline_tg_one_shot

---

## What Was Done

1. **Probed** for safe config loaders (filesystem only, no file reading)
   - `scripts/load_local_secrets.ps1`: ✅ found
   - `config/local_secrets.ps1`: checked via probe only (NEVER read by Python)

2. **Loaded** TG credentials safely via PowerShell subprocess
   - Method: `powershell_subprocess_dot_source`
   - Success: **True**
   - Post-load config_ready: **True**

3. **Called** Binance public REST API for BTC/ETH/SOL:
   - Spot 24hr tickers: /api/v3/ticker/24hr
   - Futures OI: fapi/v1/openInterest (per symbol)
   - API success: **✅**
   - Assets scanned: **3**

4. **Ran** shared pipeline (price_oi_volume_anomaly)
   - Adapter: PriceOIVolumeAnomalyFreeApiAdapter
   - Gate: ✅ allow
   - Gate reason: `Anomaly detected: notable on ETHUSDT`
   - Pipeline passed: **True**

5. **Attempted** TG test group one-shot send
   - TG sent: ✅ 1 message
   - TG skipped (missing config): 0
   - TG blocked (gate): 0
   - Production send: **False** (never)

6. **Verified** evidence ledger: ✅ clean

## Shared Pipeline Multi-Card-Family Proof

v117D proves that the v117 shared pipeline correctly handles **two distinct card families**:

| Aspect | v117C | v117D |
|--------|-------|-------|
| Card family | multi_asset_market_sync | price_oi_volume_anomaly |
| Adapter class | MultiAssetMarketSyncFreeApiAdapter | PriceOIVolumeAnomalyFreeApiAdapter |
| Binance endpoints | /api/v3/ticker/24hr | /api/v3/ticker/24hr + fapi/v1/openInterest |
| Gate logic | ≥2 assets with data | admission_passed on at least 1 asset |
| Renderer | _render_multi_asset | _render_price_oi |
| Same pipeline code? | ✅ Yes | ✅ Yes |
| Same sender? | ✅ Yes | ✅ Yes |
| Same ledger? | ✅ Yes | ✅ Yes |

## OI/Volume/Price Anomaly Details

| Symbol | 24h Δ% | Anomaly | Admission | Factors |
|--------|--------|---------|-----------|---------|
| BTCUSDT | -0.99% | `normal` | ❌ | none |
| ETHUSDT | -5.62% | `notable` | ✅ | price_move_significant |
| SOLUSDT | -4.37% | `normal` | ❌ | price_move_significant |

## New Files Created

| File | Type |
|------|------|
| `scripts/run_market_radar_v117d_price_oi_volume_real_card_tg_one_shot.py` | Runner |
| `scripts/test_market_radar_v117d_price_oi_volume_real_card_tg_one_shot.py` | Tests |
| `results/market_radar_v117d_price_oi_volume_preflight.json` | Config preflight |
| `results/market_radar_v117d_price_oi_volume_tg_one_shot_result.json` | Result |
| `results/market_radar_v117d_price_oi_volume_evidence_ledger.jsonl` | Evidence ledger |
| `runs/market_radar/v117d_price_oi_volume_real_card_tg_one_shot_report.md` | Report |
| `runs/market_radar/v117d_local_only_handoff.md` | Handoff |

## Safety Confirmation

| Constraint | Status |
|------------|--------|
| external_api_called_this_run | True |
| tg_sent_this_run | True |
| prod_state_write | False |
| ai_model_called | False |
| daemon_or_loop_started | False |
| files_deleted | False |
| credentials_printed | False |
| x_twitter_send | False |
| v116_history_modified | False |

## No Raw Secrets Verification

- ✅ Preflight JSON: self-checked, no raw token/chat_id patterns
- ✅ Result JSON: no raw token/chat_id/message_id
- ✅ Evidence ledger: SHA-256 proofs only
- ✅ Report: redacted proofs only
- ✅ Handoff: redacted proofs only
- ✅ Console output: only length/hash/prefix info

## Production Ready Status

**0/5 — NOT FOR LIVE USE**

## Next Steps

1. Run v117D tests: `python -X utf8 -m pytest scripts/test_market_radar_v117d_price_oi_volume_real_card_tg_one_shot.py -v`
2. Run v117C regression: `python -X utf8 -m pytest scripts/test_market_radar_v117c_safe_tg_config_loader_real_test_group_rerun.py -v`
3. Run v117B regression: `python -X utf8 -m pytest scripts/test_market_radar_v117b_shared_pipeline_tg_test_group_one_shot.py -v`
4. Run v117 regression: `python -X utf8 -m pytest scripts/test_market_radar_v117_shared_pipeline_real_one_shot.py -v`
5. Run v116N regression: `python -X utf8 -m pytest scripts/test_market_radar_v116n_user_acceptance_overlay_pack_local_only.py -v`
6. If anomaly detected + TG config loaded: verify message arrived in TG test group
