# Market Radar v1.18B — Operator Snapshot Preview

**Generated**: 2026-06-05T17:34:28+08:00
**Run ID**: 20260605_173357
**Pipeline**: v1.18B

---

## Five-Card Operator Snapshot (TG Message Format)

```
Market Radar v118B — Five-Card Operator Snapshot

🟢 Active Signals
  📊 Multi-Asset Sync: BTCUSDT: +0.24%; ETHUSDT: -3.61%; SOLUSDT: -2.52% (BTC strength + alt weakness — possible risk-off r
  📰 News Event: [high] other: Bitcoin plunges to near $62,000 as the AI trade unwinds, HYPE falls 14%
    ⚠ Observation only / Not causal proof

🔴 Blocked / Waiting for Conditions
  🔍 Price/OI Anomaly: No asset passed admission threshold — insufficient anomaly signal strength
  💥 Liquidation: Liquidation gate: blocked — calm market conditions (composite_score=0.35, thresh

🟡 Manual Evidence Required
  🐋 Whale Position: manual_attribution_evidence_required
    See v116N whale evidence checklist

--- Risk Notes ---
  • news_event_market_impact: event_extraction: rule_based_keyword_matching — NO AI/model; not_causal_proof: event observed alongs
  • liquidation_pressure: Liquidation gate explicitly maintained at threshold=0.60. Fixture composite_score=0.35 (< 0.60). Cal
  • whale_position_alert: Whale tracking requires manual address attribution evidence. No free public API can provide reliable

---
Cards: 5 total | Active: 2 | Blocked: 2 | Manual: 1 | Skipped/Failed: 0
Pipeline: v1.18B
Run ID: 20260605_173357
Production: FALSE | One-shot: TRUE | Test group only

⚠ All observations are NOT causal proof. Data from free public sources only.
⚠ 内部数据观察，不构成投资建议。Production Send = False。
```

---

## Card Status Overview

| # | Card Family | Status | Gate | Send Eligible | Source |
|---|------------|--------|------|---------------|--------|
| 1 | `news_event_market_impact` | ✅ active | block/manual | Yes | free_public_source |
| 2 | `price_oi_volume_anomaly` | ⛔ blocked | block/manual | No | free_public_api |
| 3 | `multi_asset_market_sync` | ✅ active | allow | Yes | free_public_api |
| 4 | `liquidation_pressure` | ⛔ blocked | block/manual | No | fixture_blocked_overlay |
| 5 | `whale_position_alert` | 🟡 manual_required | block/manual | No | fixture_blocked_overlay |


## Blocked Overlay Verification

| Overlay | Status | Threshold Lowered? | Fake Signal? | v116N Rationale |
|---------|--------|--------------------|--------------|-----------------|
| liquidation_pressure | blocked | No | No | Yes |
| whale_position_alert | manual_required | N/A | No | Yes |

## Safety Verification

| Check | Status |
|-------|--------|
| Production send | ❌ NEVER False |
| X/Twitter send | ❌ NEVER False |
| TG messages sent | 0 (max 1) |
| Daemon/loop | ❌ NEVER False |
| AI model called | ❌ NEVER False |
| Credentials printed | ❌ NEVER False |

## News Event Guard

⚠ All news events are marked `observation_only=true` and `not_causal_proof=true`.
No deterministic causal language is present in the snapshot.
