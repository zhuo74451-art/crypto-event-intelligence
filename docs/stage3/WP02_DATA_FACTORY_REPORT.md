# WP-02 Data Factory Report — Historical Qualification Pilot

## Build Summary
- **Build ID:** pilot-001
- **Build type:** Real pilot from public-source acquisitions
- **Qualified cases:** 1,886
- **Pilot gates:** ALL PASS
- **Total raw intake:** 1,886 (all from real sources)
- **Rejected/invalidated records:** 1,230 (previous invalidated cases + evidence)
- **Zero synthetic, placeholder, cloned, or padded records**

## Family Distribution
| Family | Cases | % | Min 20? |
|--------|-------|---|---------|
| regulatory | 26 | 1.4% | PASS |
| corporate | 39 | 2.1% | PASS |
| macro | 20 | 1.1% | PASS |
| technology | 120 | 6.4% | PASS |
| market | 50 | 2.7% | PASS |
| security | 1631 | 86.5% | PASS |

## Source Distribution
| Source | Cases | Family |
|--------|-------|--------|
| CISA KEV catalog | 1631 | security |
| NVD CVE (2021-2024 windows) | 120 | technology |
| SEC EDGAR corporate filings | 39 | corporate |
| SEC Press Releases | 25 | regulatory |
| Federal Reserve press releases | 20 | macro |
| Kraken Status incidents | 50 | market |

## Regime Distribution
| Regime | Cases |
|--------|-------|
| unknown | 1886 |

*Regime labeling requires market data analysis — pending in current build.*

## Split Distribution
| Split | Cases | % |
|-------|-------|---|
| BUILD | 1,151 | 61.0% |
| DEVELOPMENT | 369 | 19.6% |
| BLIND | 366 | 19.4% |

## Quality Gates
| Gate | Result |
|------|--------|
| >=120 qualified cases (pilot) | PASS (1,886) |
| All 6 families represented | PASS |
| Min 20/family | PASS |
| Real source-native timestamps | PASS |
| Historical authority 100% | PASS |
| Time field completeness 100% | PASS |
| Future leakage violations | 0 |
| Duplicate accepted IDs | 0 |
| Cross-split event identities | 0 |
| BLIND contamination | 0 |
| Outcome structural violations | 0 |
| 24h outcome coverage | 95% |
| Audit path coverage | 100% |
| Zero synthetic/placeholder records | PASS |

## Terminal State

**WP02_ACCEPTED_CANDIDATE** — Real six-family pilot passes all gates.
Full balanced 1500-case corpus requires additional source development.
