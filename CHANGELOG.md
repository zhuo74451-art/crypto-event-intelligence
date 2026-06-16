# Changelog

## v1.0.0 — Week 1 Raw Research Dataset (2026-06-16)

### Added
- Project documentation package: README, overview, architecture, index, status
- Release evidence report for Week 1 dataset
- Implementation-side audit evidence matrix
- External AI review packet with targeted critique questions
- Roadmap with Phases 0–5 and explicit non-goals
- Documentation integrity validator (`scripts/validate_release_docs_v1.py`)
- Historical document superseded banners

### Fixed
- Price observation key SHA updated to actual GitHub value
- README reflects current capabilities truthfully

### Known Limitations
- 5 samples only — insufficient for statistical conclusions
- Attribution layer not yet implemented
- No daemon, no Notion sync, no production send
- Real-time price refresh requires network mode

---

## v0.9.0 — Week 1 Raw Research Dataset (2026-06-16)

### Added
- Unified research dataset from Manifest + Price Results
- 5 event samples, 5 unique price observations, 6 sample links
- Dataset builder (`build_week1_raw_research_dataset_v1.py`)
- Dataset validator (`validate_week1_raw_research_dataset_v1.py`)

### Known Limitations
- Build requires both source files present in `research/`
- No attribution score calculated

---

## v0.8.0 — Price Provider / Cache / Consistency (2026-06-15)

### Added
- Run-level SnapshotCache for deduplicating network requests
- PriceObservationBundle (12 snapshots per observation)
- price_observation_key for shared observations (w1_003/w1_004)
- Consistency validator with 15 checks

### Fixed
- t0_basis now always literal "broadcast_time" string
- Selection metadata preserved in bundle info fields
- Zero-value handling (0 is not None)

---

## v0.7.0 — Price Backfill RC (2026-06-15)

### Added
- Hyperliquid CandleProvider (15m, nearest-candle-open)
- PriceDataProvider protocol
- BinanceProvider (1m, first-after-target)
- ProviderRouter for HYPE→HL, BTC/ETH→Binance
- Max price lag (120s Binance, 450s HL)
- return_decimal / return_percent consistent naming

### Fixed
- Fixture timestamp consistency (1781524800000 ↔ 2026-06-15T12:00:00Z)
- Network mode never falls back to fixture
- Injected clock for deterministic partial maturity tests

---

## v0.6.0 — Signal Spine v1 RC1 (2026-06-14)

### Added
- SignalAdapter contract and FreeApiAdapters (Binance, RSS)
- QualityGate and SendReadinessGate contracts
- Event intelligence semantics (観察/风险提示/禁止/丢弃)
- Dry-run renderer (JSON/MD/TG card, never sends)
- 5 card families: multi_asset, price_oi_volume, news_event, liquidation, whale
- Fixture/Network/Degraded source model
- Core pipeline with registry and evidence ledger
- 183 tests
