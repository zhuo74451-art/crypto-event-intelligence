# Market Radar v1.17 — Fixture Pipeline Report

**Generated**: 2026-06-05T15:53:17+08:00
**Run ID**: 20260605_155249

---

## Results Summary

| Card Family | Gate | TG Status | Passed |
|-------------|------|-----------|--------|

| multi_asset_market_sync | ✅ allow | skipped | ✅ |
| price_oi_volume_anomaly | ✅ allow | skipped | ✅ |
| news_event_market_impact | ✅ allow | skipped | ✅ |
| liquidation_pressure | ⛔ block | blocked | ⛔ |
| whale_position_alert | ⛔ block | blocked | ⛔ |


## Counts

- Total: 5
- Passed: 3
- Blocked: 2
- Error: 0

## Gate Details


### multi_asset_market_sync

- **Allow**: True
- **Reason**: Multi-asset data available for 3 assets


### price_oi_volume_anomaly

- **Allow**: True
- **Reason**: Admission passed for ETHUSDT


### news_event_market_impact

- **Allow**: True
- **Reason**: News event with high intensity accepted


### liquidation_pressure

- **Allow**: False
- **Reason**: Liquidation gate: blocked — calm market conditions (composite_score=0.35, threshold=0.60). Gate NOT lowered. This is a design-justified block, not a failure. Retry during high-volatility window.


### whale_position_alert

- **Allow**: False
- **Reason**: Whale gate: blocked — manual evidence NOT provided. Address attribution requires human on-chain verification. Do NOT bypass manual evidence requirement. Gate correctly blocking automated-only signals.


## Blocked Cases — Design-Justified

### liquidation_pressure — Gate Block (Normal)
- The fixture uses calm_market=true and composite_score=0.35 < threshold=0.60
- This is a DESIGN-JUSTIFIED block, not a pipeline failure
- Liquidation pressure is an event-triggered card — DO NOT lower the gate

### whale_position_alert — Manual Evidence Block (Normal)
- The fixture has manual_evidence_provided=false
- Whale alerts require human on-chain attribution — DO NOT bypass
- This is a DESIGN-JUSTIFIED block, not a pipeline failure
