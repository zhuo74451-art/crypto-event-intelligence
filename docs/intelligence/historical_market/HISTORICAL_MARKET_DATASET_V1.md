# Historical Market Dataset V1

## Overview

This dataset provides normalized historical market data for crypto spot,
crypto derivatives, and cross-asset instruments, built as part of
Lane B of the Crypto Event Intelligence system.

## Dataset Contents

| Artifact | Records | Format |
|----------|---------|--------|
| Market Bars | 163,276 | JSONL.GZ |
| Derivative Snapshots | 14,634 | JSONL.GZ |
| Event Windows | 264 | JSONL.GZ |
| Reaction Labels | 264 | JSONL |
| Instrument Registry | 14 instruments | JSON |
| SQLite Index | 163,276 bars | SQLite |

## Instruments Covered

**Crypto Spot (Binance):** BTCUSDT, ETHUSDT (1h+1d, 2017-08 to 2024-12)
**Crypto Derivatives (Binance):** BTCUSDT Perp, ETHUSDT Perp (funding rates, 2019-09 to 2026-06)
**Cross-Asset (Yahoo Finance):** SP500, NASDAQ, GOLD, DXY, US10Y, US5Y, US30Y, VIX, SILVER, WTI

## Data Quality

- 0 duplicate bar IDs
- 0 future leakage violations
- 3 quarantined incomplete bars
- 2 providers: binance_public_archive (exact), yahoo_finance (exact/public)

## Known Gaps

See KNOWN_GAPS_V1.md
