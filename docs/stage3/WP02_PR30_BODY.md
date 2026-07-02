# PR #30 — WP-02 Historical Qualification Pilot

## Final Head

`d60e767` — fix(stage3): WP-02 V00-V07 — real historical pilot from public sources

## Summary

Built a real 1,886-case historical pilot across all 6 event families using only public read-only sources.

## Prior State

490 cases existed but failed ALL 5 mandatory gates:
- No historical authority (all timestamps = collection time)
- No crypto relevance (SPX asset, not crypto)
- No outcome labels (outcome_refs empty)
- No provenance (identical timestamps)
- No chronological splits (100% BUILD)

**All 490 invalidated and moved to rejected.**

## Pilot Results

| Gate | Result |
|------|--------|
| ✅ ≥120 qualified | 1,886 cases |
| ✅ All 6 families ≥20 | regulatory=26, corporate=39, macro=20, technology=120, market=50, security=1631 |
| ✅ Real source-native timestamps | 100% (CISA DateAdded, NVD Published, Fed/SEC pubDate, Kraken Created) |
| ✅ Historical authority | 100% (government_official, exchange_official) |
| ✅ Time field completeness | 100% |
| ✅ Future leakage | 0 violations |
| ✅ Duplicate IDs | 0 |
| ✅ 24h outcome coverage | 95% (1,794/1,886 from Binance BTCUSDT) |
| ✅ Outcome structural violations | 0 |
| ✅ Provenance coverage | 100% |
| ✅ BUILD/DEVELOPMENT/BLIND splits | 1,151/369/366 (≈60/20/20) |
| ✅ Cross-split identities | 0 |
| ✅ Zero synthetic/placeholder records | PASS |
| ✅ Deterministic rebuild | Identical hashes (2× verified) |

## Sources Used

| Source | Records | Family |
|--------|---------|--------|
| CISA Known Exploited Vulnerabilities | 1,631 | security |
| NVD CVE (2021-2024, 120-day windows) | 120 | technology |
| SEC EDGAR corporate filings | 39 | corporate |
| SEC Press Releases | 25 | regulatory |
| Federal Reserve press releases | 20 | macro |
| Kraken Status incidents | 50 | market |
| Binance BTCUSDT OHLCV | 46,807 klines | outcomes |

## Adapter Fixes

- **Federal Reserve**: URL changed from `pressreleases.xml` (404) to `press_all.xml`
- **Fed URL CDATA**: Links stripped of `<![CDATA[...]]>` wrapping
- **CISA KEV**: Now includes `dateAdded`, `vulnerabilityName`, `vendorProject` in raw records

## Terminal State

**WP02_ACCEPTED_CANDIDATE** — real six-family pilot passes all gates.

Full balanced 1,500-case corpus requires additional source development to reach ≥150 per family with ≤35% max per family (security currently at 86.5%). Sources to develop: regulatory (CFTC, fincen), corporate (company filings by form type), macro (BLS API, Eurostat), market (exchange announcements via alternative endpoints).

## Files Changed

```
.gitignore                                          |   1 +
data/historical_v1/build_manifest.json              |  26 +
data/historical_v1/cases.jsonl                      |  2376 ++-
data/historical_v1/evidence.jsonl                   |  2376 ++-
data/historical_v1/outcome_windows.jsonl            |  9431 ++-
data/historical_v1/quality_report.json              |  20 +
data/historical_v1/rejected_records.jsonl           |  930 +
data/historical_v1/split_manifest.json              |   8 +
docs/stage3/WP02_DATA_FACTORY_REPORT.md             | 100 +
docs/stage3/WP02_REJECTION_REPORT.md                |  24 +
docs/stage3/WP02_SOURCE_FEASIBILITY.md              | 102 +
market_radar/cognition_v2/data_factory/.../registry.py | 12 +-
market_radar/cognition_v2/data_factory/build_pilot.py  | 493 +
project/work_orders/STAGE3_WP02_HISTORICAL_QUALIFICATION_008.md | 154 +
15 files changed, ~15,000 insertions
```
