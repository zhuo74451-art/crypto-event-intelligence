# v112Y Whale Degraded Mock Replay — Handoff

**Generated**: 2026-06-05 05:36:28 UTC+8
**Version**: v112Y
**Status**: passed

## What v112Y Did

1. Read v112X HyperLiquid live response (4 addresses, 10 positions, all HTTP 200)
2. Read v112X stop decision (confirmed: DEGRADE_TO_MOCK, 12 degradation reasons)
3. Read v112W label quality audit (2 medium, 2 low, 0 high confidence labels)
4. Read v112W field mapping config and adapter spec (reference only)
5. Flattened 10 positions from 4 address responses
6. Generated 10 degraded replay records with comprehensive explanations:
   - Label confidence explanation for each address
   - Null liquidation_price note for each affected position
   - Delta unavailable explanation (one-shot, no previous history)
   - Local timestamp only explanation (no HL server timestamp)
   - Quality flags: degraded_label_confidence, liquidation_price_missing,
     delta_unavailable, local_timestamp_only
7. All records tagged: mock_replay_only=true, eligible_for_real_send=false, degraded=true
8. Generated result JSON, replay JSONL, run report, and handoff markdown

## Files Read

| File | Purpose |
|------|---------|
| `results/market_radar_v112x_hyperliquid_live_response.json` | v112X real HL response (4 addresses, 10 positions) |
| `results/market_radar_v112x_hyperliquid_stop_decision.json` | v112X DEGRADE_TO_MOCK decision (12 reasons) |
| `results/market_radar_v112w_whale_label_quality_audit.json` | v112W label quality audit (confidence distribution) |
| `config/market_radar_v112w_whale_position_field_mapping.json` | v112W field mapping (reference) |
| `schemas/market_radar_v112w_hl_to_whale_adapter_spec.md` | v112W adapter spec (reference) |

## Files Generated

| File | Description |
|------|-------------|
| `scripts/run_market_radar_v112y_whale_degraded_mock_replay.py` | v112Y runner (this script) |
| `scripts/test_market_radar_v112y_whale_degraded_mock_replay.py` | v112Y test suite |
| `results/market_radar_v112y_whale_degraded_mock_replay_result.json` | v112Y result summary |
| `results/market_radar_v112y_whale_degraded_replay_records.jsonl` | 10 degraded replay records |
| `runs/market_radar/v112y_whale_degraded_mock_replay.md` | Run report |
| `runs/market_radar/v112y_whale_degraded_mock_replay_handoff.md` | Handoff (this file) |

## Replay Records Summary

- **Positions loaded**: 10
- **Replay records written**: 10
- **Unique addresses**: 4
- **Addresses**: 0x082e843a431aef031264dc232693dd710aedca88, 0x50b309f78e774a756a2230e1769729094cac9f20, 0x6c8512516ce5669d35113a11ca8b8de322fd84f6, 0x8def9f50456c6c4e37fa5d3d57f108ed23992dae

## Label Confidence Summary

- **High**: 0
- **Medium**: 8
- **Low**: 2

**All labels are medium or low confidence.** No high-confidence institutional labels (Arkham/Nansen/onchain confirmed) exist in the current data. Medium-confidence labels come from HyperLiquid observer heuristics. Low-confidence labels are unknown whale fallbacks.

## Degraded Reasons Summary

| Quality Flag | Count |
|--------------|-------|
| degraded_label_confidence | 10 |
| delta_unavailable | 10 |
| liquidation_price_missing | 7 |
| local_timestamp_only | 10 |

- **Null liquidation_price**: 7 positions
- **Delta unavailable**: 10 positions (all — one-shot observation)
- **Local timestamp only**: 10 positions (all — no HL server timestamp)

## Safety Invariant Status

| Invariant | Status |
|-----------|--------|
| external_api_called | PASS (zero external HTTP requests) |
| tg_sent | PASS (no TG messages) |
| prod_state_write | PASS (prod_state_write=false, no state file modified) |
| daemon_started | PASS (no daemon/watcher/cron/loop) |
| watcher_started | PASS (no watcher started) |
| credentials_read | PASS (no .env, token, cookie, password, API key read) |
| files_deleted | PASS (no files deleted) |
| eligible_for_real_send_count == 0 | PASS (all 10 records have eligible_for_real_send=false) |
| all_records_have_label_confidence | PASS (all 10 records have label_confidence field) |
| all_null_liq_have_note | PASS (all null liquidation_price have explanation note) |
| all_delta_unavailable_explained | PASS (all records explain delta unavailability) |
| all_local_timestamp_explained | PASS (all records explain timestamp source) |
| no_real_send_candidate | PASS (no record has real_send_candidate=true) |
| degraded_replay_not_masquerading_as_live | PASS (degraded=true, not pretending to be live) |
| v112x_stop_decision_confirmed | PASS (DEGRADE_TO_MOCK confirmed) |

## Recommended Next Step

**v112Z — Degraded Whale Envelope Compatibility**

1. Feed these degraded replay records into the v112H envelope adapter to verify envelope compatibility.
2. Verify that the envelope layer correctly handles degraded whale records with null liquidation_price, missing delta, and low-confidence labels.
3. Generate preview cards from the degraded records to assess public card quality.
4. Do NOT enter the TG send path.
5. Do NOT write production state.
6. Consider whether additional label enrichment could upgrade confidence before any future real-send consideration.
7. The adapter/envelope/preview pipeline should gracefully handle all degradation flags documented in this replay.

## Safety Affirmation

- `external_api_called`: **false** (zero external HTTP requests)
- `api_key_used`: **false**
- `tg_sent`: **false**
- `prod_state_write`: **false**
- `daemon_started`: **false**
- `watcher_started`: **false**
- `credentials_read`: **false**
- `files_deleted`: **false**
- `eligible_for_real_send_count`: **0**
- `mock_replay_only`: **true**
- `degraded_replay_built`: **true**
- `input_stop_decision`: **DEGRADE_TO_MOCK**
