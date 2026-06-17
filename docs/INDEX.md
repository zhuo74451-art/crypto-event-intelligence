# File Index

## Core Runtime Code

| File | Purpose |
|------|---------|
| `market_radar/shared/models.py` | Shared data models (NormalizedSignal, RenderedCard, GateDecision) |
| `market_radar/shared/adapter_contract.py` | SignalAdapter contract + FixtureCatalog |
| `market_radar/shared/free_api_adapters.py` | Binance public REST + RSS news adapters |
| `market_radar/shared/gate_contract.py` | QualityGate + SendReadinessGate |
| `market_radar/shared/sender_contract.py` | TGTestGroupSender (dry-run safe) |
| `market_radar/shared/renderer_contract.py` | CardRenderer for 5 card families |
| `market_radar/shared/pipeline.py` | Shared pipeline orchestration |

## Signal Spine

| File | Purpose |
|------|---------|
| `market_radar/shared/event_intelligence_semantics.py` | Decision semantics (観察/风险提示/禁止/丢弃) |
| `market_radar/shared/dry_run_renderer.py` | Dry-run output (JSON/MD/TG card, never sends) |
| `market_radar/shared/signal_registry.py` | Persistent registry with backup recovery |
| `market_radar/shared/evidence_ledger.py` | Redacted evidence records |

## IO and Providers

| File | Purpose |
|------|---------|
| `market_radar/shared/event_price_backfill.py` | Core price backfill (1m/15m, max lag, fixture fallback) |
| `market_radar/shared/price_provider_protocol.py` | Provider protocol, Binance/HL, SnapshotCache, router |

## Tests

| File | Purpose |
|------|---------|
| `tests/test_signal_spine_io_v1.py` | Signal Spine IO verification (31 tests) |
| `tests/test_event_price_backfill_v1.py` | Price backfill data integrity (57 tests) |
| `tests/test_week1_price_providers_v1.py` | Provider protocol, cache, consistency (50 tests) |
| `tests/test_signal_spine_core.py` | Registry and core pipeline tests |
| `tests/test_signal_spine_integration.py` | Full pipeline integration tests |

## Fixtures

| File | Purpose |
|------|---------|
| `fixtures/event_high_quality.json` | High-quality market event sample |
| `fixtures/event_duplicate.json` | Duplicate event (same dedup key) |
| `fixtures/event_old_news_rehash.json` | Old news recycled |
| `fixtures/event_no_asset.json` | Event with no clear asset attribution |
| `fixtures/event_insufficient_source.json` | Single unverifiable source |
| `fixtures/event_pump_risk.json` | High pump/FOMO risk signal |
| `fixtures/event_missing_fields.json` | Missing critical data fields |
| `fixtures/real_binance_response_sample.json` | Sample Binance API response (no keys) |
| `fixtures/kline_fixture_full_24h.json` | Full 24h kline fixture (BTC/ETH/SOL) |
| `fixtures/kline_fixture_partial_1h.json` | Partial maturity (only 1h ready) |
| `fixtures/kline_fixture_unsupported.json` | Unsupported symbol scenarios |
| `fixtures/golden_multi_asset_market_sync.json` | Golden reference output |

## Manifest and Price Results

| File | Purpose |
|------|---------|
| `research/week1_samples_v1.json` | 5 event samples with tags, summaries, Notion IDs |
| `research/validate_manifest.py` | Manifest structural and content validator |
| `research/week1_price_backfill_raw_v1.json` | 6 price observations with full provenance |
| `research/week1_price_backfill_raw_v1.md` | Price results human-readable summary |
| `research/validate_week1_price_dataset.py` | Price dataset consistency validator |

## Raw Dataset

| File | Purpose |
|------|---------|
| `research/build_week1_raw_research_dataset_v1.py` | Unified dataset builder (reads both sources) |
| `research/validate_week1_raw_research_dataset_v1.py` | Dataset structure and content validator |
| `research/week1_raw_research_dataset_v1.json` | Week 1 unified research dataset |
| `docs/research/week1_raw_research_dataset_v1.md` | Dataset human-readable documentation |

## Scripts and Validators

| File | Purpose |
|------|---------|
| `scripts/run_signal_spine_v1_demo.py` | Signal Spine IO demo runner |
| `scripts/run_event_price_backfill_v1.py` | Price backfill demo runner |
| `scripts/run_week1_sample_backfill_v1.py` | Week 1 network backfill runner |
| `scripts/validate_release_docs_v1.py` | Release documentation integrity validator |

## Release Documentation

| File | Purpose |
|------|---------|
| `docs/releases/signal_spine_v1_rc1_acceptance.md` | Historical: Signal Spine RC1 acceptance |
| `docs/releases/week1_raw_research_dataset_v1_release.md` | Week 1 dataset release report |
| `docs/audits/signal_spine_v1_repo_audit.md` | Historical: Signal Spine repo audit |
| `docs/audits/week1_raw_research_dataset_v1_release_evidence.md` | Implementation-side release evidence |
| `docs/handoffs/EXTERNAL_AI_REVIEW_PACKET_V1.md` | AI review packet for external critique |
| `docs/roadmap/NEXT_PHASE_PLAN_V1.md` | Project roadmap (Phases 0-5) |

## Project Documentation

| File | Purpose |
|------|---------|
| `README.md` | Project overview, quick start, navigation |
| `docs/PROJECT_OVERVIEW.md` | Detailed project description and design decisions |
| `docs/ARCHITECTURE.md` | System architecture and data flow |
| `docs/INDEX.md` | This file — complete file index |
| `docs/PROJECT_STATUS.md` | Component-by-component status matrix |
| `CHANGELOG.md` | Release changelog |
