# Market Radar v1.17 — Shared Pipeline Design

**Generated**: 2026-06-05T15:53:17+08:00
**Run ID**: 20260605_155249
**Pipeline**: Adapter → Quality Gate → Renderer → Send-Readiness Gate → TG Test Sender → Evidence Ledger

---

## Architecture

```
┌──────────┐    ┌──────────────┐    ┌──────────┐    ┌───────────────────┐    ┌──────────────┐    ┌─────────────────┐
│ Adapter  │───→│ Quality Gate │───→│ Renderer │───→│ Send-Readiness    │───→│ TG Test      │───→│ Evidence Ledger │
│          │    │              │    │          │    │ Gate              │    │ Group Sender │    │                 │
└──────────┘    └──────────────┘    └──────────┘    └───────────────────┘    └──────────────┘    └─────────────────┘
     │                │                  │                   │                      │                    │
     ▼                ▼                  ▼                   ▼                      ▼                    ▼
NormalizedSignal  GateDecision     RenderedCard    SendReadinessDecision    TGTestSendResult    EvidenceRecord
```

## Shared Package Structure

```
market_radar/shared/
  __init__.py          — Package exports
  models.py            — Data models (CardFamily, NormalizedSignal, etc.)
  adapter_contract.py  — Adapter interface + fixtures for 5 card families
  free_api_adapters.py  — Real free API adapters (Binance public REST)
  gate_contract.py     — QualityGate + SendReadinessGate
  renderer_contract.py — CardRenderer for all 5 card types
  sender_contract.py   — TGTestGroupSender (redacted output)
  evidence_ledger.py   — EvidenceLedger (sha256 proofs)
  pipeline.py          — SharedPipeline orchestrator
```

## Five Card Families

| # | Card Family | Fixture | Real API | Gate Behavior |
|---|-------------|---------|----------|---------------|
| 1 | multi_asset_market_sync | ✅ | ✅ Binance public | allow if ≥2 assets |
| 2 | price_oi_volume_anomaly | ✅ | ✅ Binance spot+OI | allow if admission passed |
| 3 | news_event_market_impact | ✅ | fixture only | allow if intensity ≥ medium |
| 4 | liquidation_pressure | ✅ | blocked (calm market) | block unless volatile |
| 5 | whale_position_alert | ✅ | blocked (manual evidence) | block unless evidence provided |

## Safety Constraints (Always Active)

- Production send ready: **ALWAYS False**
- Formal channel/group send: **ALWAYS blocked**
- X/Twitter send: **ALWAYS blocked**
- Daemon/cron/loop: **ALWAYS blocked**
- Liquidation gate: **NOT lowered**
- Whale manual evidence: **NOT bypassed**
- All outputs: **No raw token/chat_id/message_id**
