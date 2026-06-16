# Crypto Event Intelligence — Architecture

## Text Architecture Diagram

```text
Raw Source / Adapter
        │
        ▼
NormalizedSignal
        │ from_normalized_signal()
        ▼
Observation
(source-specific fact + provenance + dual dedup keys)
        │
        ▼
Deterministic Noise Gate
(rule-level accept / downgrade / reject / not_evaluated)
        │
        ▼
Signal Orchestrator + Signal Registry
(create a new Signal or merge into an existing event-level Signal)
        │
        ▼
Event Intelligence Mapper
(观察 / 风险提示 / 禁止 / 丢弃)
        │
        ▼
Dry Run Renderer
(JSON / Markdown / Telegram-style preview; no production send)

Separate research path after event selection:

Event Sample + t0 policy
        │
        ▼
Price Provider Layer
(Binance 1m / Hyperliquid 15m)
        │
        ▼
SnapshotCache + PriceObservationBundle
(asset/BTC/ETH × t0/1h/4h/24h)
        │
        ▼
Raw Research Dataset
(samples × unique observations × links)
        │
        ▼
Future Attribution Layer
(not implemented)
```

## Core Modules and File Paths

| Module | Path | Purpose |
|--------|------|---------|
| Models | `market_radar/shared/models.py` | NormalizedSignal, Observation, Signal, lifecycle, gate result and shared pipeline models |
| Adapter Contract | `market_radar/shared/adapter_contract.py` | SignalAdapter contract and fixture catalog |
| Free API Adapters | `market_radar/shared/free_api_adapters.py` | Public Binance and RSS-based input adapters |
| Quality / Send Gates | `market_radar/shared/gate_contract.py` | Existing card-quality and send-readiness gates |
| Deterministic Noise Gate | `market_radar/shared/noise_gate.py` | Observation-level deterministic rule evaluation |
| Signal Orchestrator | `market_radar/shared/signal_orchestrator.py` | Gate aggregation and registry action |
| Signal Registry | `market_radar/shared/signal_registry.py` | Persistent Signal storage, event-level merge, backup and recovery |
| Event Intelligence Mapper | `market_radar/shared/event_intelligence_mapper.py` | Maps Signal Spine results to final event-intelligence semantics |
| Event Intelligence Semantics | `market_radar/shared/event_intelligence_semantics.py` | The four allowed decisions and safety validation |
| Pipeline | `market_radar/shared/pipeline.py` | Existing shared pipeline plus Signal Spine entry point |
| Renderer Contract | `market_radar/shared/renderer_contract.py` | Card rendering for existing card families |
| Dry Run Renderer | `market_radar/shared/dry_run_renderer.py` | JSON, Markdown and Telegram-style preview without production send |
| Sender Contract | `market_radar/shared/sender_contract.py` | Test-group sender with production restrictions |
| Evidence Ledger | `market_radar/shared/evidence_ledger.py` | Redacted execution evidence; not a replacement for Signal Registry |
| Price Backfill | `market_radar/shared/event_price_backfill.py` | Snapshot retrieval, maturity, max-lag and return primitives with explicit modes |
| Price Provider | `market_radar/shared/price_provider_protocol.py` | Binance/Hyperliquid routing, run-level cache, bundles and Week 1 result contract |
| Dataset Builder | `research/build_week1_raw_research_dataset_v1.py` | Offline deterministic assembly of Manifest and Price Results |
| Dataset Validators | `research/validate_*.py` | Fact, price-provenance and unified-dataset integrity checks |

## Key Data Object Relationships

```text
NormalizedSignal
  → Observation
      one source-specific observed event or data point
      carries observation_fingerprint and event_dedup_key
  → NoiseGateResult[]
  → Signal
      event-level, updatable registry artifact
      may contain multiple observation_ids and evidence links
  → SignalSpineResult
  → EventIntelligenceResult

Event Sample
  → Sample-to-Observation Link
  → Unique Price Observation
      t0 + 1h + 4h + 24h asset/BTC/ETH snapshots and returns
```

## Signal vs Observation

- **NormalizedSignal**: Adapter output. It is the compatibility contract used by the existing shared pipeline.
- **Observation**: A normalized, source-specific fact or data point. Different sources can create different Observations for the same underlying event.
- **Signal**: The event-level, updatable artifact stored in Signal Registry after gate processing. One Signal can aggregate multiple Observations and evidence links.

This project does **not** use “Signal” to mean a buy/sell instruction.

## Registry vs Evidence Ledger

- **Signal Registry** stores event-level Signal state, observation links, evidence, transitions and dedup mappings.
- **Evidence Ledger** stores redacted proof of pipeline execution. It is an execution log, not the canonical event-state database.

## Price Observation vs Event Sample

- **Event Sample**: One research event fact with title, raw summary, labels, source and broadcast time.
- **Price Observation**: The canonical price path for one provider/asset/timestamp/interval/policy tuple.
- **Sample Link**: Joins an event sample to a price observation. Multiple event samples may share one price observation, and one macro sample may link to multiple observed assets.

## Dedup Layers

1. **Observation fingerprint**: Source-specific identity for one reported observation.
2. **Event dedup key**: Source-agnostic event identity using normalized title, assets, event type and time bucket.
3. **Registry merge**: Multiple Observations with the same event key can be attached to one Signal; duplicate cards are suppressed.
4. **SnapshotCache**: Reuses identical provider/symbol/time/interval/policy requests during one price run.
5. **Price observation key**: Allows several sample links to share one canonical market observation.
6. **Dataset layer**: Stores unique price observations separately from sample links.

## Source and Selection Model

| Source | Requested Data | Requires Key | Selection Policy | Stored Precision |
|--------|----------------|--------------|------------------|------------------|
| Binance public REST | BTC/ETH 1m klines | No | first_after_target, max lag 120s | 60s |
| Hyperliquid public Info | HYPE 15m candles for historical coverage | No | nearest_candle_open, max absolute lag 450s | 900s |
| RSS / public sources | Event inputs | No | Adapter-specific parsing and rules | N/A |
| Explicit Fixture Mode | Deterministic test data | No | Pre-built fixture | Explicitly marked fixture |

Hyperliquid also supports other intervals, including 1m. Week 1 uses 15m because its finite recent-candle retention must cover the historical sample date.

## Decision and Research Boundaries

```text
Event-intelligence decision path:
source → observation → gate → registry → mapper → dry-run output

Research measurement path:
event sample → timestamp policy → price snapshots → raw returns → dataset

Not yet implemented:
raw dataset → interference analysis → attribution confidence → reviewed conclusion
```

The price layer does not feed a buy/sell decision, and the raw dataset does not assert causality.

## Security Boundaries

- No private keys or trading credentials are required.
- No exchange order endpoints are connected.
- Formal production sending remains blocked.
- Public network reads and explicit fixture mode are separated.
- Network failure returns an unavailable/error state; it never silently falls back to fixture.
- Every completed PriceSnapshot records provider source, requested time, actual candle time and lag.
- Attribution and trading actions are outside the current implementation.
