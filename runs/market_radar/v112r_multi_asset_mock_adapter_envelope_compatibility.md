# Market Radar v1.12-R — Multi-Asset Mock Adapter → Envelope Compatibility

**Generated**: 2026-06-05 04:13:15 UTC+8
**Status**: passed
**Dry Run Only**: Yes

---

## 1. v112R Goal

Validate that v112Q noise-filtered multi_asset mock signals can be converted into v112H Unified Signal Envelopes with stable dedupe_key, cooldown_key, and payload_hash — without calling any live API, without TG send, and without production writes.

## 2. Upstream v112Q Artifacts Read

| Artifact | Path | Purpose |
|----------|------|---------|
| v112Q Result | `results/market_radar_v112q_multi_asset_noise_aware_plan_result.json` | Validated upstream state |
| v112Q Noise Case Results | `results/market_radar_v112q_multi_asset_noise_case_results.jsonl` | Source of per-case actual_result |
| v112Q Threshold Config | `config/market_radar_v112q_multi_asset_thresholds.json` | Stricter threshold rules |
| v112Q Noise Fixtures | `data/fixtures/market_radar_v112q_multi_asset_noise_cases.json` | Raw asset data for mock sync results |
| v112H Envelope Builder | `scripts/market_radar_signal_envelope_v112h.py` | Envelope construction and validation (read-only) |
| v112G Sync Feed | `scripts/market_radar_multi_asset_sync_feed_v112g.py` | Reference patterns (read-only) |

### Upstream Validation

- ✅ **v112Q_result_exists**: file found
- ✅ **v112Q_status_passed**: status=passed
- ✅ **v112Q_candidate_card_type_is_multi_asset_market_sync**: candidate_card_type=multi_asset_market_sync
- ✅ **v112Q_noise_cases_total_ge_6**: total=6
- ✅ **v112Q_all_noise_cases_passed**: passed=6, total=6
- ✅ **v112Q_stricter_thresholds_ready**: stricter_thresholds_ready=True
- ✅ **v112Q_dry_run_only**: dry_run_only=True
- ✅ **v112Q_real_live_api_called_false**: real_live_api_called=False
- ✅ **v112Q_real_tg_sent_false**: real_tg_sent=False
- ✅ **v112Q_external_api_called_false**: external_api_called=False
- ✅ **v112Q_external_ai_called_false**: external_ai_called=False
- ✅ **v112Q_daemon_started_false**: daemon_started=False

**Overall upstream valid**: ✅ YES

## 3. Noise Case → Envelope Classification

| # | Case ID | v112Q Actual | Envelope Allowed | Confidence | Eligible for Send | Reason |
|---|---------|-------------|-----------------|------------|-------------------|--------|
| 1 | clean_sync_should_pass | passed | ✅ | high | ✅ | None |
| 2 | two_of_three_direction_should_block | blocked | ❌ | medium | ❌ | actual_result_blocked_excluded_from_envelope |
| 3 | single_asset_volume_spike_should_block | blocked | ❌ | low | ❌ | actual_result_blocked_excluded_from_envelope |
| 4 | timestamp_skew_should_block | degraded | ❌ | low | ❌ | actual_result_degraded_excluded_from_envelope |
| 5 | leader_driven_move_should_downgrade_or_block | downgraded | ❌ | low | ❌ | actual_result_downgraded_excluded_from_envelope |
| 6 | mixed_sector_should_flag_low_confidence | low_confidence | ✅ | low | ❌ | low_confidence_case_envelope_without_send_candidate |

## 4. Envelope Compatibility Check

### Envelope 1: sig-mams-7500db63-202606050413

- **card_type**: multi_asset_market_sync
- **direction**: bullish
- **primary_assets**: BTC, ETH, SOL
- **dedupe_key**: `9338a55e54d7932f...`
- **cooldown_key**: `434d3fa3ea019205...`
- **payload_hash**: `a7b9744bc0c7b42b...`
- **mock_adapter**: True
- **dry_run_only**: True
- **eligible_for_send**: False
- **validation**: ✅ valid, errors=None
- **leak_scan**: debug_leaks=0, secret_leaks=0, clean=True

### Envelope 2: sig-mams-af736997-202606050413

- **card_type**: multi_asset_market_sync
- **direction**: bullish
- **primary_assets**: BTC, ARB, DOGE, USDT, OP
- **dedupe_key**: `63471c53d0c4cb23...`
- **cooldown_key**: `eb41fc92ae761241...`
- **payload_hash**: `abef0713acbc36fa...`
- **mock_adapter**: True
- **dry_run_only**: True
- **eligible_for_send**: False
- **validation**: ✅ valid, errors=None
- **leak_scan**: debug_leaks=0, secret_leaks=0, clean=True

## 5. Deterministic ID / Payload Hash Stability

| Check | Result |
|-------|--------|
| deterministic_ids | ✅ |
| payload_hashes_stable | ✅ |
| all_signal_ids_valid | ✅ |
| all_dedupe_keys_valid | ✅ |
| all_cooldown_keys_valid | ✅ |
| all_payload_hashes_valid | ✅ |

## 6. Why Real Send Is Still NOT Ready

Despite envelope compatibility being verified, the following blockers remain:

1. **Mock data only**: All testing uses fixture-based mock data. No real market data has been pulled from CoinGecko, CoinCap, or any exchange.
2. **No gate integration**: The v112I dedupe/cooldown gate and v112J eligible signal pack have not been tested with v112R envelopes.
3. **No historical baseline**: Required by v112Q config — a live data pull and baseline computation must precede any real send.
4. **Manual review gate**: Per v112P, manual_review_required remains true.
5. **Test channel rehearsal**: A rehearsal with the actual sender pipeline should precede any real send.
6. **dry_run_only=true**: All operations are explicitly marked as dry-run only.

## 7. Mock Envelope Count Explanation

The v112Q noise case results contain:
- **1 passed** case (`clean_sync_should_pass`)
- **1 low_confidence** case (`mixed_sector_should_flag_low_confidence`)
- **4 blocked/degraded/downgraded** cases (excluded from envelope)

Both passed and low_confidence cases produce envelopes, so `mock_envelope_count=2`. The low_confidence envelope has `eligible_for_send=false` — it exists for audit purposes but would not reach the send gate.

**No blocked/degraded/downgraded case was incorrectly marked as send candidate.**

## 8. Next Steps

### v112S: Mock Envelope → Gate / Preview Integration
- Feed v112R envelopes through v112I dedupe/cooldown gate
- Verify noise-filtered candidates pass gate correctly
- Verify blocked items are excluded at gate level
- Build a mock send preview pack from eligible envelopes

### v112T: One-Shot Live Pull + Baseline (future)
- Execute a single one-shot pull from free public APIs
- Establish historical sync frequency baseline
- Feed live data through v112Q → v112R pipeline

Do NOT directly recommend real TG send — the next step should be mock gate integration, not production delivery.

---

## Safety Declaration

| Constraint | Status |
|------------|--------|
| Live API called | ❌ No |
| TG message sent | ❌ No |
| Production state written | ❌ No |
| Daemon started | ❌ No |
| External AI called | ❌ No |
| Files deleted | ❌ No |
| Secrets/tokens/keys leaked | ❌ No (0 terms) |
| Debug terms leaked | ❌ No (0 terms) |
| Mock adapter only | ✅ Yes |
| Dry run only | ✅ Yes |

*Report generated by v112R runner on 2026-06-05 04:13:15 UTC+8*