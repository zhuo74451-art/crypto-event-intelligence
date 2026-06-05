# Market Radar v1.19B — Live Operator Snapshot (B-lite)

**Generated**: 2026-06-05T18:48:37+08:00
**Run ID**: 20260605_184831
**Task ID**: 20260605_v119b_signal_quality_b_lite_and_dashboard_guidance
**Pipeline**: v1.19B

---

## B-Lite Quality Enhancements Active

- ✅ price_oi_volume_anomaly: layered decision (reject/watch/accept) with B-lite mild-watch tier
- ✅ news_event_market_impact: freshness/stale tagging + entity normalization
- ✅ Dashboard: Chinese 30-second guidance layer
- ✅ OI $0.0B detection and explanation

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
- **Observation Only**: False
- **Not Causal Proof**: False

### price_oi_volume_anomaly

- **Source**: live_binance_public_api
- **Gate Allowed**: False
- **Gate Reason**: No asset passed admission threshold — insufficient anomaly signal strength
- **Card Title**: 🔍 Anomaly Scan: BTCUSDT
- **Observation Only**: False
- **Not Causal Proof**: False

### news_event_market_impact

- **Source**: live_free_public_rss_and_binance
- **Gate Allowed**: True
- **Gate Reason**: News event with high intensity accepted
- **Card Title**: 📰 Event: Bitcoin plunges to near $62,000 as the AI trade unwinds, HYPE falls 14%
- **Observation Only**: True
- **Not Causal Proof**: True

### liquidation_pressure

- **Source**: fixture
- **Gate Allowed**: False
- **Gate Reason**: Liquidation gate: blocked — calm market conditions (composite_score=0.35, threshold=0.60). Gate NOT lowered. This is a design-justified block, not a failure. Retry during high-volatility window.
- **Card Title**: 💥 Liquidation: BTCUSDT/ETHUSDT/SOLUSDT
- **Observation Only**: False
- **Not Causal Proof**: False

### whale_position_alert

- **Source**: fixture
- **Gate Allowed**: False
- **Gate Reason**: Whale gate: blocked — manual evidence NOT provided. Address attribution requires human on-chain verification. Do NOT bypass manual evidence requirement. Gate correctly blocking automated-only signals.
- **Card Title**: 🐋 Whale Alert: Hyperliquid whale address tracking
- **Observation Only**: False
- **Not Causal Proof**: False

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
  "events_found": 51,
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
