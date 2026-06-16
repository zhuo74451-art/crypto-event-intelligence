# Crypto Event Intelligence — Architecture

## Text Architecture Diagram

```
                    ┌──────────────────────────┐
                    │   Raw Source / Adapter    │
                    │  (free API / fixture /    │
                    │   RSS / Binance / HL)     │
                    └────────────┬─────────────┘
                                 │ NormalizedSignal
                    ┌────────────▼─────────────┐
                    │       Noise Gate          │
                    │  (quality / dedup /       │
                    │   intensity thresholds)   │
                    └────────────┬─────────────┘
                                 │ Approved Signal
                    ┌────────────▼─────────────┐
                    │    Signal Registry        │
                    │  (persistent, deduplicated│
                    │   with evidence ledger)   │
                    └────────────┬─────────────┘
                                 │ Registered Signal
                    ┌────────────▼─────────────┐
                    │ Event Intelligence Mapper │
                    │  (観察 / 风险提示 / 禁止   │
                    │   / 丢弃)                │
                    └────────────┬─────────────┘
                                 │ FinalDecision
                    ┌────────────▼─────────────┐
                    │    Dry Run Renderer       │
                    │  (JSON / MD / TG card)    │
                    └────────────┬─────────────┘
                    ┌────────────▼─────────────┐
                    │   Price Provider Layer    │
                    │  Binance(1m) / HL(15m)   │
                    │  SnapshotCache + Bundle   │
                    └────────────┬─────────────┘
                    ┌────────────▼─────────────┐
                    │   Raw Research Dataset    │
                    │  Event Samples × Price    │
                    │  Observations × Links     │
                    └────────────┬─────────────┘
                    ┌────────────▼─────────────┐
                    │   Future Attribution      │
                    │   Layer (not implemented) │
                    └──────────────────────────┘
```

## Core Modules and File Paths

| Module | Path | Purpose |
|--------|------|---------|
| Models | `market_radar/shared/models.py` | NormalizedSignal, RenderedCard, GateDecision, etc. |
| Adapter Contract | `market_radar/shared/adapter_contract.py` | SignalAdapter ABC, FixtureCatalog |
| Free API Adapters | `market_radar/shared/free_api_adapters.py` | Binance public REST, RSS news adapters |
| Gate Contract | `market_radar/shared/gate_contract.py` | QualityGate, SendReadinessGate |
| Sender Contract | `market_radar/shared/sender_contract.py` | TGTestGroupSender (dry-run safe) |
| Renderer Contract | `market_radar/shared/renderer_contract.py` | CardRenderer for 5 card families |
| Pipeline | `market_radar/shared/pipeline.py` | Shared pipeline orchestration |
| Event Intelligence | `market_radar/shared/event_intelligence_semantics.py` | Decision semantics (観察/风险提示/禁止/丢弃) |
| Dry Run Renderer | `market_radar/shared/dry_run_renderer.py` | Dry-run output (JSON/MD/TG card) |
| Price Backfill | `market_radar/shared/event_price_backfill.py` | Core backfill logic with max lag, fixture fallback |
| Price Provider | `market_radar/shared/price_provider_protocol.py` | Provider protocol, Binance/HL, SnapshotCache, router |
| Signal Registry | `market_radar/shared/signal_registry.py` | Persistent registry with backup/corruption recovery |
| Evidence Ledger | `market_radar/shared/evidence_ledger.py` | Redacted evidence records |

## Key Data Object Relationships

```
NormalizedSignal (one per source event)
  → Observation (standardized, may merge multiple signals)
    → Signal (persisted in Registry with dedup)
      → FinalDecision (from Event Intelligence Mapper)
        → WindowReturn × 3 (1h / 4h / 24h)
          → PriceSnapshot × 12 (asset/btc/eth × t0/1h/4h/24h)
```

## Signal vs Observation

- **Signal**: A normalized data point from one adapter at one time. Contains metrics, risk notes, source refs.
- **Observation**: A deduplicated, gate-approved event record ready for intelligence evaluation.

## Registry vs Evidence Ledger

- **Registry**: Persistent storage for Signal records. Handles serialization, backup, corruption recovery.
- **Evidence Ledger**: Redacted proof of pipeline execution (sha256 hashes, no raw credentials). For audit trails.

## Price Observation vs Event Sample

- **Event Sample**: A research unit describing one event fact (title, summary, tags, notion_id, broadcast_time).
- **Price Observation**: A set of 12 price snapshots + computed returns for one (asset, broadcast_time) pair.
- **Sample Link**: The join record connecting one sample to one observation. One sample can have multiple observations (e.g., WTI → BTC + ETH).

## Dedup Layers

1. **Adapter level**: fetch_on_once guard prevents duplicate API calls
2. **Registry level**: signal_id dedup prevents duplicate persistence
3. **Cache level**: SnapshotCache dedup prevents duplicate network requests within one run
4. **Observation level**: price_observation_key dedup shares identical observations across samples
5. **Dataset level**: unique_price_observations count reflects deduplicated observations

## Source Data Model

| Source | Type | Requires Key | Selection Policy | Precision |
|--------|------|-------------|-----------------|-----------|
| Binance public REST | 1m klines | No | first_after_target (max lag 120s) | 60s |
| Hyperliquid public Info API | 15m candles | No | nearest_candle_open (max lag 450s) | 900s |
| RSS feeds (CoinDesk, CT, etc.) | News articles | No | rule-based keyword matching | N/A |
| Fixture | Deterministic data | No | N/A (pre-built) | N/A |

## Decision and Data Flow Boundaries

```
                            ─── Data Boundary ───
Raw data sources  ───────▶  NormalizedSignal  ───────▶  Registry
                                                              │
                    ◀───────  Price Backfill  ◀──────── Price Provider
                                                              │
                            Raw Research Dataset ◀───────────┘
                                                              │
                    ─── Decision Boundary (Future) ───         │
                    Attribution Layer consumes dataset ────────┘
```

## Security Boundaries

- No private keys stored in repository
- No trading API endpoints configured
- Dry-run renderer never calls Telegram API
- Network mode never falls back to fixture
- All PriceSnapshots record exact data provenance
- Fixture data is explicitly labeled (never masquerades as real)
