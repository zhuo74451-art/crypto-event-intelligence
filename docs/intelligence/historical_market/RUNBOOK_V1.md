# Lane B — Historical Market Data Factory Runbook V1

## Overview

This runbook describes how to build, verify, and maintain the historical market
data factory for lane B.

## Quick Start

```powershell
# Full pipeline
python scripts/intelligence/historical_market/run_lane_b_pipeline.py ^
    --start-date 2010-01-01 ^
    --crypto-start-date 2017-01-01 ^
    --resume

# Individual stages
python scripts/intelligence/historical_market/build_crypto_spot_history.py
python scripts/intelligence/historical_market/build_cross_asset_history.py
python scripts/intelligence/historical_market/build_crypto_derivatives_history.py
python scripts/intelligence/historical_market/build_market_index.py
```

## Verification

```powershell
# Tests
python -m pytest tests/intelligence/historical_market/ -q

# Audit
python scripts/intelligence/historical_market/audit_market_data.py
python scripts/intelligence/historical_market/audit_event_windows.py

# Coverage
python scripts/intelligence/historical_market/generate_coverage_report.py
```

## Data Sources

| Provider | Data | URL |
|----------|------|-----|
| Binance Archive | BTC/ETH spot OHLCV | https://data.binance.vision/ |
| Binance API | Funding rates | https://fapi.binance.com |
| FRED | US yields, VIX | https://fred.stlouisfed.org/ |
| Yahoo Finance | SP500, NASDAQ, Gold, DXY | https://query1.finance.yahoo.com/ |

## Output Structure

See INTEGRATION_MANIFEST.yaml for full artifact listing.
