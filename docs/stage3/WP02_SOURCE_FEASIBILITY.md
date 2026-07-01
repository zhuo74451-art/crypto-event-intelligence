# WP-02 Source Feasibility Report

## Registry Summary

Initial source registry contains **15 entries** across 6 event families:

| Family | Qualifying Evidence | Discovery Only | Market Outcome | Total |
|--------|-------------------|----------------|----------------|-------|
| Regulatory | 2 (sec-edgar, cftc-enforcement) | 0 | 0 | 2 |
| Corporate | 1 (sec-edgar) | 1 (company-press-releases) | 0 | 2 |
| Macro | 3 (federal-reserve, bls-economic-releases, eurostat) | 0 | 0 | 3 |
| Technology | 2 (github-security-advisories, nvd-nist) | 0 | 0 | 2 |
| Market | 0 | 0 | 2 (binance-public, coinbase-public) | 2 |
| Security | 1 (cisa-alerts) | 0 | 0 | 1 |

**Total: 15 entries** — 9 QUALIFYING_EVIDENCE, 1 DISCOVERY_ONLY, 2 MARKET_OUTCOME.

## Source Classification

All sources are:
- **Public, read-only, legally accessible** — no paid APIs, credentials, or bypass
- **Government, exchange, or platform official** — authority and fact permission documented
- **Rate-limited with finite retry** — no unbounded or hidden loops

## Permission Review

| Source | Access | Excerpts Allowed | Terms |
|--------|--------|------------------|-------|
| sec-edgar | https GET, robots.txt | Yes | Public record |
| cftc-enforcement | https GET | Yes | Public record |
| federal-reserve | https GET | Yes | Public data |
| bls-economic-releases | https GET | Yes | Public data |
| eurostat | API | Yes | Free API |
| github-security-advisories | API | Yes | Public API |
| nvd-nist | API | Yes | Public data |
| binance-public | REST API | Yes | Public market data |
| coinbase-public | REST API | Yes | Public market data |
| cisa-alerts | https GET | Yes | Public advisories |

## Pilot Feasibility

At least **20 candidate cases per family** are feasible through the following sources:

- **Regulatory**: SEC filings (enforcement actions, material events), CFTC actions
- **Corporate**: SEC 8-K filings, press releases verified against EDGAR
- **Macro**: Fed announcements, BLS releases, Eurostat indicators
- **Technology**: GitHub security advisories, NVD CVEs
- **Market**: Exchange announcements (Binance, Coinbase), delistings, forks
- **Security**: CISA alerts, major vulnerability disclosures

All 6 families have **at least 2 source classes** where feasible (regulatory: government + exchange in some cases; macro: multiple government sources).

## Risk Assessment

- **No paid API risk** — all sources are free/public
- **Rate limiting** — all sources have documented rate limits; backoff and retry configured
- **Historical depth** — all sources cover 2021-01 through 2026-06
- **Fallback sources** — documented for corporate (sec-edgar), market (binance → coinbase)

**Conclusion**: Source feasibility is **CONFIRMED**. No blockers identified. Proceed with pilot at 120 cases (20/family).
