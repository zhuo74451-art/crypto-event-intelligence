# Market Radar v1.19A — Live Operator Snapshot

**Generated**: 2026-06-05T18:31:38+08:00
**Run ID**: 20260605_183130
**Task ID**: 20260605_v119a_live_no_send_operator_one_shot_refresh_flow
**Pipeline**: v1.19A

---

## Live Data Sources Used

- ✅ **MultiAssetMarketSyncFreeApiAdapter**: status=ok
- ✅ **PriceOIVolumeAnomalyFreeApiAdapter**: status=ok
- ✅ **NewsEventMarketImpactFreePublicSourceAdapter**: status=ok
- ✅ **FixtureSignalAdapter(liquidation_pressure)**: status=ok
- ✅ **FixtureSignalAdapter(whale_position_alert)**: status=ok

## Five Card Family Live Operator Snapshot

### multi_asset_market_sync

- **Source**: live_binance_public_api
- **Gate Allowed**: True
- **Gate Reason**: Multi-asset data available for 3 assets
- **Card Title**: 📊 Market Sync: BTCUSDT/ETHUSDT/SOLUSDT
- **Production Status**: test_group_only
- **Observation Only**: False
- **Not Causal Proof**: False
- **TG Test Group Allowed**: True
- **Production Send Ready**: False

### price_oi_volume_anomaly

- **Source**: live_binance_public_api
- **Gate Allowed**: False
- **Gate Reason**: No asset passed admission threshold — insufficient anomaly signal strength
- **Card Title**: 🔍 Anomaly Scan: BTCUSDT
- **Production Status**: test_group_only
- **Observation Only**: False
- **Not Causal Proof**: False
- **TG Test Group Allowed**: False
- **Production Send Ready**: False

### news_event_market_impact

- **Source**: live_free_public_rss_and_binance
- **Gate Allowed**: True
- **Gate Reason**: News event with high intensity accepted
- **Card Title**: 📰 Event: Bitcoin plunges to near $62,000 as the AI trade unwinds, HYPE falls 14%
- **Production Status**: test_group_only
- **Observation Only**: True
- **Not Causal Proof**: True
- **TG Test Group Allowed**: True
- **Production Send Ready**: False

### liquidation_pressure

- **Source**: fixture
- **Gate Allowed**: False
- **Gate Reason**: Liquidation gate: blocked — calm market conditions (composite_score=0.35, threshold=0.60). Gate NOT lowered. This is a design-justified block, not a failure. Retry during high-volatility window.
- **Card Title**: 💥 Liquidation: BTCUSDT/ETHUSDT/SOLUSDT
- **Production Status**: test_group_only
- **Observation Only**: False
- **Not Causal Proof**: False
- **TG Test Group Allowed**: False
- **Production Send Ready**: False

### whale_position_alert

- **Source**: fixture
- **Gate Allowed**: False
- **Gate Reason**: Whale gate: blocked — manual evidence NOT provided. Address attribution requires human on-chain verification. Do NOT bypass manual evidence requirement. Gate correctly blocking automated-only signals.
- **Card Title**: 🐋 Whale Alert: Hyperliquid whale address tracking
- **Production Status**: test_group_only
- **Observation Only**: False
- **Not Causal Proof**: False
- **TG Test Group Allowed**: False
- **Production Send Ready**: False

---

## Adapter Diagnostics

### MultiAssetMarketSyncFreeApiAdapter
```
{
  "used": true,
  "status": "ok",
  "api_success": true,
  "assets_fetched": 3,
  "gate_allowed": true,
  "error": null
}
```

### PriceOIVolumeAnomalyFreeApiAdapter
```
{
  "used": true,
  "status": "ok",
  "api_success": true,
  "signals_count": 3,
  "gate_allowed": false,
  "error": null
}
```

### NewsEventMarketImpactFreePublicSourceAdapter
```
{
  "used": true,
  "status": "ok",
  "sources_succeeded": 4,
  "articles_fetched": 165,
  "events_found": 50,
  "api_success": true,
  "gate_allowed": true,
  "observation_only": true,
  "not_causal_proof": true,
  "error": null
}
```

### FixtureSignalAdapter(liquidation_pressure)
```
{
  "used": true,
  "status": "ok",
  "composite_score": 0.35,
  "threshold": 0.6,
  "calm_market": true,
  "gate_allowed": false,
  "threshold_not_lowered": true,
  "error": null
}
```

### FixtureSignalAdapter(whale_position_alert)
```
{
  "used": true,
  "status": "ok",
  "manual_evidence_provided": false,
  "gate_allowed": false,
  "manual_evidence_not_bypassed": true,
  "error": null
}
```
