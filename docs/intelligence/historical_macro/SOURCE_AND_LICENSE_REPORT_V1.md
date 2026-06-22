# Source and License Report V1

## Data Sources Used

### 1. U.S. Bureau of Labor Statistics (BLS) — Public API v2

| Series | Family | License |
|--------|--------|---------|
| CUUR0000SA0 (CPI-U All Items) | us_cpi | Public Domain |
| CUUR0000SA0L1E (CPI-U Less Food & Energy) | us_core_cpi | Public Domain |
| CES0000000001 (Total Nonfarm) | us_nonfarm_payrolls | Public Domain |
| LNS14000000 (Unemployment Rate) | us_unemployment_rate | Public Domain |

**Access**: BLS Public API v2, no registration key required for historical data.
**License**: U.S. Government work — Public Domain. Free to use, reproduce, distribute.
**Terms**: https://www.bls.gov/developers/termsOfService.htm
**Rate Limit**: Free tier allows ~2 requests/second.

### 2. FRED (Federal Reserve Economic Data) — St. Louis Fed

| Series | Family | License |
|--------|--------|---------|
| CPIAUCSL | us_cpi | Public Domain |
| CPILFESL | us_core_cpi | Public Domain |
| PAYEMS | us_nonfarm_payrolls | Public Domain |
| UNRATE | us_unemployment_rate | Public Domain |
| PCEPILFE | us_core_pce | Public Domain |
| FEDFUNDS | us_fomc_rate_decision | Public Domain |

**Access**: FRED CSV download, no API key required for individual series.
**License**: Public Domain. Data is free to use.
**Terms**: https://fred.stlouisfed.org/legal/

## Sources Attempted but Not Yet Available

### Bureau of Economic Analysis (BEA)
- **Series**: PCEPILFE (Core PCE)
- **Status**: NIPA API requires registration key; public access limited
- **Workaround**: Core PCE data obtained via FRED (PCEPILFE series)

### Federal Reserve Board
- **Series**: FOMC rate decisions
- **Status**: Historical FOMC HTML pages have URL structure changes, needs update
- **Workaround**: FOMC rate data obtained via FRED (FEDFUNDS series)

## No Paid Sources Used

All data in this dataset is from free, public, government-operated sources.
No Bloomberg, Refinitiv, or other paid data sources have been used.

## Compliance

- No login credentials used
- No paywalls bypassed
- No personal accounts accessed
- All data is publicly available for research use
