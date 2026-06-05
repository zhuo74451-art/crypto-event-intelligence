# Market Radar v1.12-K — State Replay + Idempotency Validation

**Run timestamp**: 2026-06-05 04:13:19 UTC+8
**Version**: v1.12-K
**Gate library**: v1.12-I
**Replay mode**: Canonical

## Summary

- Input envelopes: 13
- First-pass eligible: 9
- Replay decisions: 13
- Replay passed: 4
- Replay blocked dedupe: 9
- Replay blocked cooldown: 0
- First-pass eligible reblocked: 9/9
- Idempotency passed: **True**
- Unexpected repass signal IDs: []
- Prior state source: `results/market_radar_v112l_canonical_prior_state.json`

## Replay Gate Decisions

| # | Signal ID | Card Type | Gate Status | Eligible? |
|---|-----------|-----------|-------------|-----------|
| 1 | `sig-pova-cf3a0c25-202606042000` | price_oi_volume_anomaly | pass | ✓ |
| 2 | `sig-wpa-f71d2b1d-202606041945` | whale_position_alert | blocked_dedupe (1st-pass eligible) | ✗ |
| 3 | `sig-wpa-1ae7a01d-202606042010` | whale_position_alert | pass | ✓ |
| 4 | `sig-wpa-46d9d399-202606042022` | whale_position_alert | blocked_dedupe (1st-pass eligible) | ✗ |
| 5 | `sig-lipr-a94980e2-202606041200` | liquidation_pressure | pass | ✓ |
| 6 | `sig-lipr-dd740422-202606041200` | liquidation_pressure | blocked_dedupe (1st-pass eligible) | ✗ |
| 7 | `sig-lipr-03ec60ab-202606041200` | liquidation_pressure | blocked_dedupe (1st-pass eligible) | ✗ |
| 8 | `sig-mams-018a768f-202606041430` | multi_asset_market_sync | blocked_dedupe (1st-pass eligible) | ✗ |
| 9 | `sig-mams-a4e05c21-202606041515` | multi_asset_market_sync | blocked_dedupe (1st-pass eligible) | ✗ |
| 10 | `sig-mams-b2ab4cdd-202606041600` | multi_asset_market_sync | blocked_dedupe (1st-pass eligible) | ✗ |
| 11 | `sig-nemi-d3dbfd91-202606041430` | news_event_market_impact | pass | ✓ |
| 12 | `sig-nemi-f8590f16-202606041015` | news_event_market_impact | blocked_dedupe (1st-pass eligible) | ✗ |
| 13 | `sig-nemi-20d248d1-202606040845` | news_event_market_impact | blocked_dedupe (1st-pass eligible) | ✗ |

## First-Pass Eligible Signal Replay Analysis

| # | Signal ID | First Pass | Replay | Reblocked? |
|---|-----------|------------|--------|------------|
| 1 | `sig-wpa-f71d2b1d-202606041945` | pass | blocked_dedupe | ✓ |
| 2 | `sig-wpa-46d9d399-202606042022` | pass | blocked_dedupe | ✓ |
| 3 | `sig-lipr-dd740422-202606041200` | pass | blocked_dedupe | ✓ |
| 4 | `sig-lipr-03ec60ab-202606041200` | pass | blocked_dedupe | ✓ |
| 5 | `sig-mams-018a768f-202606041430` | pass | blocked_dedupe | ✓ |
| 6 | `sig-mams-a4e05c21-202606041515` | pass | blocked_dedupe | ✓ |
| 7 | `sig-mams-b2ab4cdd-202606041600` | pass | blocked_dedupe | ✓ |
| 8 | `sig-nemi-f8590f16-202606041015` | pass | blocked_dedupe | ✓ |
| 9 | `sig-nemi-20d248d1-202606040845` | pass | blocked_dedupe | ✓ |

## Card Type Summary

| Card Type | Total | Pass | Dedupe | Cooldown |
|-----------|-------|------|--------|----------|
| liquidation_pressure | 3 | 1 | 2 | 0 |
| multi_asset_market_sync | 3 | 0 | 3 | 0 |
| news_event_market_impact | 3 | 1 | 2 | 0 |
| price_oi_volume_anomaly | 1 | 1 | 0 | 0 |
| whale_position_alert | 3 | 1 | 2 | 0 |

## Safety Flags

- `real_tg_sent`: False
- `external_api_called`: False
- `external_ai_called`: False
- `daemon_started`: False
- `live_ready`: False
- `dry_run_only`: True
- `production_send_allowed`: False

## Leak Scan

- Debug leaks: 0
- Secret leaks: 0
- Full wallet leak: False

## Output Files

- `results/market_radar_v112k_state_replay_idempotency_result.json`
- `results/market_radar_v112k_replay_gate_decisions.jsonl`
- `runs/market_radar/v112k_state_replay_idempotency.md` (this file)
- `runs/market_radar/v112k_state_replay_idempotency_handoff.md`

## Pipeline Verification

```
adapter output
  -> v112h signal envelope (13 envelopes)
  -> v112i dedupe/cooldown gate (1st pass: 9 eligible, 4 blocked)
  -> v112j eligible signal pack + proposed state dry-run
  -> v112k state replay (Canonical mode)  <-- you are here
```

### Idempotency Proof

- The prior state contains dedupe entries for all 9 first-pass eligible signals.
- Running the same 13 envelopes through the gate with this state as prior
  results in all 9 eligible signals being blocked by dedupe.
- This proves: if this state were committed to live state,
  the next gate evaluation would correctly deduplicate these signals.

### Canonical Replay Verification

- Replay mode: **canonical_state_replay**
- Prior state source: v112l canonical prior state (no synthetic keys)
- All 9 first-pass eligible signals reblocked
- unexpected_repass_signal_ids: []
- canonical_idempotency_passed: **True**

### Repass Analysis

The following 4 signal(s) passed in the replay:

- `sig-pova-cf3a0c25-202606042000` — reasons: no active dedupe or cooldown block — signal passes
  - NOT in first-pass eligible set (was originally blocked)
  - Cooldown expired between runs — expected behavior
- `sig-wpa-1ae7a01d-202606042010` — reasons: no active dedupe or cooldown block — signal passes
  - NOT in first-pass eligible set (was originally blocked)
  - Cooldown expired between runs — expected behavior
- `sig-lipr-a94980e2-202606041200` — reasons: no active dedupe or cooldown block — signal passes
  - NOT in first-pass eligible set (was originally blocked)
  - Cooldown expired between runs — expected behavior
- `sig-nemi-d3dbfd91-202606041430` — reasons: no active dedupe or cooldown block — signal passes
  - NOT in first-pass eligible set (was originally blocked)
  - Cooldown expired between runs — expected behavior

---
*Generated by v1.12-K at 2026-06-05 04:13:19 UTC+8*