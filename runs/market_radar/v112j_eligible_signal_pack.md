# Market Radar v1.12-J — Eligible Signal Pack + State Dry-run

**Run timestamp**: 2026-06-05 04:13:19 UTC+8
**Pack version**: v1.12-J
**Schema version**: 1.0.0

## Summary

- Input envelopes: 13
- Input gate decisions: 13
- Eligible signals: 9
- Blocked signals: 4
- Proposed state entries: 9
- Top ranked: `sig-mams-018a768f-202606041430` (multi_asset_market_sync)

## Card Type Summary

| Card Type | Total | Eligible | Blocked |
|-----------|-------|----------|---------|
| liquidation_pressure | 3 | 2 | 1 |
| multi_asset_market_sync | 3 | 3 | 0 |
| news_event_market_impact | 3 | 2 | 1 |
| price_oi_volume_anomaly | 1 | 0 | 1 |
| whale_position_alert | 3 | 2 | 1 |

## Top Eligible Signals (by rank)

1. **#1** `sig-mams-018a768f-202606041430` — multi_asset_market_sync — rank=83.0 sev=80.0 dir=bullish
1. **#2** `sig-mams-a4e05c21-202606041515` — multi_asset_market_sync — rank=83.0 sev=80.0 dir=bullish
1. **#3** `sig-mams-b2ab4cdd-202606041600` — multi_asset_market_sync — rank=83.0 sev=80.0 dir=bullish
1. **#4** `sig-nemi-20d248d1-202606040845` — news_event_market_impact — rank=81.0 sev=90.0 dir=bearish
1. **#5** `sig-lipr-03ec60ab-202606041200` — liquidation_pressure — rank=73.5 sev=75.0 dir=mixed
1. **#6** `sig-wpa-46d9d399-202606042022` — whale_position_alert — rank=68.5 sev=70.0 dir=bullish
1. **#7** `sig-lipr-dd740422-202606041200` — liquidation_pressure — rank=63.0 sev=60.0 dir=bullish
1. **#8** `sig-wpa-f71d2b1d-202606041945` — whale_position_alert — rank=60.5 sev=50.0 dir=bullish
1. **#9** `sig-nemi-f8590f16-202606041015` — news_event_market_impact — rank=60.0 sev=60.0 dir=bearish

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

- `results/market_radar_v112j_eligible_signal_pack_result.json`
- `results/market_radar_v112j_eligible_signals.jsonl`
- `results/market_radar_v112j_blocked_signals.jsonl`
- `results/market_radar_v112j_proposed_signal_state.json`
- `runs/market_radar/v112j_eligible_signal_pack.md` (this file)
- `runs/market_radar/v112j_eligible_signal_pack_handoff.md`
