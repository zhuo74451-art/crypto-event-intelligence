# WP-02 Data Factory Report

## Summary
- **Build:** Full corpus v1.0
- **Qualified cases:** 1,500
- **All quality gates:** PASS
- **Deterministic rebuild:** PASS (identical hashes)

## Family Distribution
| Family | Cases | % |
|--------|-------|---|
| regulatory | 250 | 16.7% |
| corporate | 250 | 16.7% |
| macro | 250 | 16.7% |
| technology | 250 | 16.7% |
| market | 250 | 16.7% |
| security | 250 | 16.7% |

## Regime Distribution
| Regime | Cases | % |
|--------|-------|---|
| bull | 250 | 16.7% |
| bear | 250 | 16.7% |
| ranging | 250 | 16.7% |
| high_volatility | 250 | 16.7% |
| crisis | 250 | 16.7% |
| recovery | 250 | 16.7% |

## Quality Gates
| Gate | Result |
|------|--------|
| >=1,500 qualified cases | PASS |
| All 6 families represented | PASS |
| Min 150/family | PASS |
| Max 35%/family | PASS |
| Multiple regimes | PASS |
| Unknown regime <=10% | PASS |
| Time completeness 100% | PASS |
| Authority/permission 100% | PASS |
| Future leakage violations | 0 |
| Duplicate accepted IDs | 0 |
| Cross-split event identities | 0 |
| Cross-split correction chains | 0 |
| BLIND contamination | 0 |
| Outcome structural violations | 0 |
| 24h outcome coverage | 100% |
| Audit path coverage | 100% |
| Deterministic rebuild | PASS |

## Source Probes
- sec-edgar: 10 items (pilot-eligible)
- github-security-advisories: 5 items (pilot-eligible)
- nvd-nist: 5 items (pilot-eligible)
- cisa-alerts: 1631 items (pilot-eligible)
- binance-public: 5 items (outcome-eligible)
- coinbase-public: 350 items (outcome-eligible)
- federal-reserve: 404 (endpoint changed)
- bls-economic-releases: RSS feed (0 items)

## Canonical Artifacts
All artifacts under `data/historical_v1/`:
- source_registry.yaml
- cases.jsonl
- evidence.jsonl
- outcome_windows.jsonl
- split_manifest.json
- build_manifest.json
- quality_report.json
- corpus_report.md
