# Market Radar v1.18C — Operator Snapshot Preview (PLAIN TEXT)

**Generated**: 2026-06-05T17:56:45+08:00
**Run ID**: 20260605_175631
**Pipeline**: v1.18C
**TG Format**: PLAIN TEXT (HTML parse_mode DISABLED — v118C fix)

---

## v118B → v118C Fix Summary

- **v118B root cause**: TG HTML parse_mode rejected emoji/special chars:
  `Bad Request: can't parse entities: Unsupported start tag at byte offset 1046`
- **v118C fix**: parse_mode=PlainText — no HTML entity parsing, no parse errors
- **All card logic, gate thresholds, and overlay rules PRESERVED from v118B**

---

## Five-Card Operator Snapshot (TG Message Format — PLAIN TEXT)

```
Market Radar v118C -- Five-Card Operator Snapshot

[Active Signals]
  [Multi-Asset Sync]: BTCUSDT: -0.44%; ETHUSDT: -4.52%; SOLUSDT: -3.09% (All monitored assets showing bearish alignment (corr≈0.80))
  [News Event]: [high] other: Bitcoin plunges to near $62,000 as the AI trade unwinds, HYPE falls 14%
    Warning: Observation only / Not causal proof

[Blocked / Waiting for Conditions]
  [Price/OI Anomaly]: No asset passed admission threshold — insufficient anomaly signal strength
  [Liquidation]: Liquidation gate: blocked — calm market conditions (composite_score=0.35, threshold=0.60). Gate NOT 

[Manual Evidence Required]
  [Whale Position]: manual_attribution_evidence_required
    See v116N whale evidence checklist

--- Risk Notes ---
  * news_event_market_impact: event_extraction: rule_based_keyword_matching — NO AI/model; not_causal_proof: event observed alongside market data, not
  * liquidation_pressure: Liquidation gate explicitly maintained at threshold=0.60. Fixture composite_score=0.35 (< 0.60). Calm market flag=True. 
  * whale_position_alert: Whale tracking requires manual address attribution evidence. No free public API can provide reliable address ownership. 

---
Cards: 5 total | Active: 2 | Blocked: 2 | Manual: 1 | Skipped/Failed: 0
Pipeline: v1.18C
Run ID: 20260605_175631
Production: FALSE | One-shot: TRUE | Test group only
TG format: PLAIN TEXT (HTML parse_mode disabled -- v118C fix)

Warning: All observations are NOT causal proof. Data from free public sources only.
Warning: [Internal data observation, not investment advice]. Production Send = False.
```

---

## Card Status Overview

| # | Card Family | Status | Gate | Send Eligible | Source |
|---|------------|--------|------|---------------|--------|
| 1 | `news_event_market_impact` | ACTIVE | allow | Yes | free_public_source |
| 2 | `price_oi_volume_anomaly` | BLOCKED | block/manual | No | free_public_api |
| 3 | `multi_asset_market_sync` | ACTIVE | allow | Yes | free_public_api |
| 4 | `liquidation_pressure` | BLOCKED | block/manual | No | fixture_blocked_overlay |
| 5 | `whale_position_alert` | MANUAL_REQUIRED | block/manual | No | fixture_blocked_overlay |


## Blocked Overlay Verification

| Overlay | Status | Threshold Lowered? | Fake Signal? | v116N Rationale |
|---------|--------|--------------------|--------------|-----------------|
| liquidation_pressure | blocked | No | No | Yes |
| whale_position_alert | manual_required | N/A | No | Yes |

## TG Delivery Status (v118C — PLAIN TEXT)

| Check | Status |
|-------|--------|
| TG parse_mode | **PlainText** (HTML DISABLED) |
| TG delivery status | `sent` |
| Messages sent | 1 (max 1) |
| Production send | FALSE |
| HTML parse risk avoided | YES |

## Safety Verification

| Check | Status |
|-------|--------|
| Production send | NEVER False |
| X/Twitter send | NEVER False |
| TG messages sent | 1 (max 1) |
| Daemon/loop | NEVER False |
| AI model called | NEVER False |
| Credentials printed | NEVER False |
| HTML parse_mode | DISABLED (v118C fix) |

## News Event Guard

ALL news events are marked `observation_only=true` and `not_causal_proof=true`.
No deterministic causal language is present in the snapshot.
