# Market Radar v1.18A — Operator Digest Preview

**Generated**: 2026-06-05T17:19:48+08:00
**Run ID**: 20260605_171902
**Pipeline**: v1.18A

---

## Aggregated Three-Card Digest (TG Message Format)

```
📊 Market Radar v118A — Operator Digest

✅ 📰 News Event
   Source: free_public_source
   Gate: allow | Send: sent
   Signal: [high] other: Bitcoin plunges to near $62,000 as the AI trade unwinds, HYPE falls 14%
   Note: event_extraction: rule_based_keyword_matching — NO AI/model; not_causal_proof: event observed alongside market data, not
   ⚠ Observation only — not causal proof

⛔ 🔍 Price/OI/Vol Anomaly
   Source: free_public_api
   Gate: block | Send: blocked
   Signal: BTCUSDT: Δ-0.16% anomaly=normal; ETHUSDT: Δ-4.30% anomaly=normal; SOLUSDT: Δ-3.02% anomaly=normal

✅ 📊 Multi-Asset Sync
   Source: free_public_api
   Gate: allow | Send: sent
   Signal: BTCUSDT: -0.21%; ETHUSDT: -4.33%; SOLUSDT: -3.03% (All monitored assets showing bearish alignment (corr≈0.80))

---
Cards: 2/3 allowed through quality gate
Pipeline: v1.18A
Run ID: 20260605_171902
Production: FALSE | One-shot: TRUE | Test group only

⚠ All observations are NOT causal proof. Data from free public sources only.
⚠ 内部数据观察，不构成投资建议。Production Send = False。
```

---

## Card Details

| # | Card Family | Source | Gate | Top Signal | Send |
|---|------------|--------|------|------------|------|
| 1 | `news_event_market_impact` | free_public_source | ✅ allow | [high] other: Bitcoin plunges to near $62,000 as the AI trad | sent |
| 2 | `price_oi_volume_anomaly` | free_public_api | ⛔ block | BTCUSDT: Δ-0.16% anomaly=normal; ETHUSDT: Δ-4.30% anomaly=no | blocked |
| 3 | `multi_asset_market_sync` | free_public_api | ✅ allow | BTCUSDT: -0.21%; ETHUSDT: -4.33%; SOLUSDT: -3.03% (All monit | sent |

## Safety Verification

| Check | Status |
|-------|--------|
| Production send | ❌ NEVER False |
| X/Twitter send | ❌ NEVER False |
| TG messages sent | 1 (max 1) |
| Daemon/loop | ❌ NEVER False |
| AI model called | ❌ NEVER False |
| Credentials printed | ❌ NEVER False |

## News Event Observation Only

⚠ All news events are marked `observation_only=true` and `not_causal_proof=true`.
No deterministic causal language is present in the digest.

## Priority Order

1. 📰 News Event Market Impact (high intensity)
2. 🔍 Price/OI/Volume Anomaly
3. 📊 Multi-Asset Market Sync
