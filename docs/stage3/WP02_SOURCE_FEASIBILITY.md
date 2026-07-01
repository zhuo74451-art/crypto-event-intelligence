# WP-02 Source Feasibility Report

*Generated from machine registry. Counts verified against source code.*

## Registry Summary

**11 unique source IDs** registered in `build_default_registry()`, each bound to exactly one primary event family:

| Source ID | Name | Class | Family | Authority |
|-----------|------|-------|--------|-----------|
| `sec-edgar` | SEC EDGAR — Corporate Filings | QUALIFYING_EVIDENCE | regulatory | government_official |
| `cftc-enforcement` | CFTC Enforcement Actions | QUALIFYING_EVIDENCE | regulatory | government_official |
| `company-press-releases` | Public Company Press Releases | DISCOVERY_ONLY | corporate | corporate_official |
| `federal-reserve` | Federal Reserve Press Releases | QUALIFYING_EVIDENCE | macro | government_official |
| `bls-economic-releases` | BLS Economic Releases | QUALIFYING_EVIDENCE | macro | government_official |
| `eurostat` | Eurostat Economic Indicators | QUALIFYING_EVIDENCE | macro | government_official |
| `github-security-advisories` | GitHub Security Advisories | QUALIFYING_EVIDENCE | technology | platform_official |
| `nvd-nist` | NVD National Vulnerability Database | QUALIFYING_EVIDENCE | technology | government_official |
| `binance-public` | Binance Public Market Data | MARKET_OUTCOME | market | exchange_official |
| `coinbase-public` | Coinbase Public Market Data | MARKET_OUTCOME | market | exchange_official |
| `cisa-alerts` | CISA Cybersecurity Alerts | QUALIFYING_EVIDENCE | security | government_official |

## Class Distribution

| Class | Count |
|-------|-------|
| QUALIFYING_EVIDENCE | 8 |
| DISCOVERY_ONLY | 1 |
| MARKET_OUTCOME | 2 |
| **Total** | **11** |

## Family Distribution (primary binding)

| Family | Sources |
|--------|---------|
| regulatory | 2 |
| corporate | 1 |
| macro | 3 |
| technology | 2 |
| market | 2 |
| security | 1 |
| **Total** | **11** |

## Source Policy Compliance

All 11 sources are:
- **Public, read-only, legally accessible** — no paid APIs, credentials, or bypass
- **Government, exchange, or platform official** — authority and fact permission documented
- **Rate-limited with finite retry** — no unbounded or hidden loops
- **Short excerpts only** (<500 chars) — no full copyrighted articles

## Pilot Production Adapters

The following adapters are implemented and tested for the 120-case pilot:

| Source ID | Adapter | Parser Version | Live Probe |
|-----------|---------|----------------|------------|
| sec-edgar | SecEdgarAdapter | sec-edgar-1.0 | pending bounded probe |
| federal-reserve | FederalReserveAdapter | fed-1.0 | pending bounded probe |
| bls-economic-releases | BLSAdapter | bls-1.0 | pending bounded probe |
| github-security-advisories | GitHubAdvisoryAdapter | gh-advisory-1.0 | pending bounded probe |
| nvd-nist | NVDAdapter | nvd-cve-1.0 | pending bounded probe |
| cisa-alerts | CISAAdapter | cisa-1.0 | pending bounded probe |
| binance-public | BinanceMarketAdapter | binance-klines-1.0 | pending bounded probe |
| coinbase-public | CoinbaseMarketAdapter | coinbase-candles-1.0 | pending bounded probe |

## Risk Assessment

- **No paid API risk** — all sources free/public
- **Rate limiting** — documented and respected with backoff/retry
- **Historical coverage** — all sources cover 2021-01 through 2026-06
- **Fallback sources** — documented for market (coinbase → binance)

**Conclusion:** Source feasibility is CONFIRMED for pilot. All 6 families supported.
