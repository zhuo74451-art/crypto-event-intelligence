# Lane B Execution Log

## 2026-12-01 22:00 UTC — Bootstrap

- Created worktree from sealed SHA 5a5ca58253479403f65ec726016d1ca9b91703d1
- Branch: feat/overnight-lane-b-historical-market-cross-asset-v1
- Created docs/execution/lane_b/EXECUTION_STATE.yaml
- Created docs/execution/lane_b/INTEGRATION_MANIFEST.yaml
- Created this log file
- Working tree clean, SHA verified

Next: Begin P0 — contracts, schemas, providers

## 2026-06-23 UTC — P0-P4 Complete

### P0: Contracts, Providers, Minimum Data
- 6 JSON schemas created
- 6 typed Python contracts (MarketBarV1, DerivativeSnapshotV1, InstrumentRegistryV1, EventMarketWindowV1, MarketReactionLabelV1, SourceSnapshotV1)
- 5 provider modules (base, crypto_archive, crypto_public_api, fred_csv, public_cross_asset, proxy_registry)
- Minimal real data: 134,438 crypto bars (BTC+ETH 1h+1d) + 28,838 cross-asset bars

### P1: Continuous Market Data
- Crypto hourly: 129,050 rows (BTC+ETH from 2017-08 to 2024-12)
- Crypto daily: 5,388 rows
- Cross-asset: 28,838 rows across 10 instruments
- Total bars: 163,276
- 14 instruments in registry
- Note: FRED blocked by network; used Yahoo Finance treasury yields (^TNX, ^FVX, ^TYX, ^VIX) as proxies

### P1: Derivatives History
- Binance funding rates: BTCUSDT (7,434) + ETHUSDT (7,200) = 14,634 records
- Covers 2019-09 to 2026-06

### P2: Event Windows & Labels
- 33 temporary real event samples (FOMC, CPI, NFP, SEC etf, SVB)
- 264 event windows built (33 events × 8 instruments)
- 264 reaction labels with 7 multi-horizon returns each
- Uses 5m/15m/1h/1d intervals for crypto, 1d for cross-asset

### P3: Quality Audit
- 0 duplicate bar IDs
- 0 future leakage violations
- 3 WTI negative-price bars (April 2020 oil crash — historically accurate, not errors)
- 3 incomplete latest-day bars quarantined

### P4: Tests & Docs
- 120 tests passing (contracts, IDs, validation, timezone, providers, idempotency, event windows, labels)
- SQLite index built with 163,276 bars
- Coverage report generated

### Known Gaps
- FRED not available (network blocked); Yahoo Finance yields used as proxies
- No open interest or basis data yet (Binance endpoints need API key)
- Lane A events not yet consumed (using 33 temporary samples)
- Cross-asset matrix CSV not yet generated (needs Lane A events)

Next: Commit and push all work.

## 2026-06-23 UTC — Pilot V2 Complete

### Lane A Lock
- 12 verified events consumed from Lane A (6 families x 2)
- Artifact hash: ba93cce3 (manifest recorded e3d26291 — manifest recording error)
- PRODUCER_LOCK.yaml documented both hashes and discrepancy note

### Pilot V2 Outputs
- 24 event-asset windows (12 events x 2 crypto assets)
- 72 reaction labels (12 events x 2 assets x 3 horizons: 1h/4h/24h)
- 120 cross-asset context rows (12 events x 10 series) — daily context only
- 24 funding context rows (12 events x 2 assets)
- 4 SQLite tables with indexes

### Integrity
- 0 future leakage violations
- 0 temporary event IDs
- 0 duplicate label IDs
- 0 one-minute or five-minute precision claims
- Max alignment error: ≤ 60 minutes (1h bars)

### Tests
- 165 passing (120 original + 45 new pilot tests)
- 0 new failures

### Next
- Lane C can consume pilot outputs
- Full historical macro alignment deferred until Lane A full coverage
