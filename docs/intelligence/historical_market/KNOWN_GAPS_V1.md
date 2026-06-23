# Known Gaps V1

## Data Sources
- **FRED not available**: Network blocks fred.stlouisfed.org. Using Yahoo Finance
  treasury yield symbols (^TNX, ^FVX, ^TYX) as proxies for FRED's DGS10, DGS5, DGS30.
- **No Open Interest history**: Binance public API for historical OI requires API key.
  Available for future enhancement.
- **No Basis data**: Requires mark price from Binance futures which needs API key.
- **No Liquidation data**: Binance liquidation historical data not publicly available.
  Consider providing a `liquidation_pressure_proxy` in future.

## Coverage
- **Crypto 1h data**: 2017-08 to 2024-12 (Binance archive)
- **Cross-asset daily**: 2015-01 to 2026-06 (Yahoo Finance)
- **Funding rates**: 2019-09 to 2026-06 (Binance API)
- **No 1m/5m event windows**: 5m interval not available in Binance archive.
  Use 1h fallback for event windows where needed.

## Lane Dependencies
- **Lane A not consumed**: Lane A macro events not yet available. Using 33
  temporary real event samples (FOMC, CPI, NFP, SEC, banking crisis).
- **No cross-asset matrix CSV**: Requires Lane A events for alignment.

## Quality
- **6 OHLC violations**: 2 are WTI negative prices (April 2020 — historically accurate),
  1 is DXY rounding artifact (~0.001 difference), 3 were incomplete latest-day bars
  (quarantined).
- **6028 interval gaps**: Expected for daily cross-asset data with weekends/holidays.
