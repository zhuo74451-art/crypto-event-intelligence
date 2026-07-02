# WP-02 Source Feasibility Report

*Generated from machine registry and live probe results.*

## Registry Summary

**5 qualifying sources** executed for the pilot, covering all 6 event families:

| Source ID | Family | Status | Records | Authority |
|-----------|--------|--------|---------|-----------|
| `cisa-alerts` | security | OK | 1631 | government_official / OFFICIAL_IMMUTABLE_ARCHIVE |
| `nvd-nist` | technology | OK (partial windows) | 120 | government_official / OFFICIAL_VERSIONED_FEED |
| `federal-reserve` | macro | OK (fixed URL) | 20 | government_official / OFFICIAL_VERSIONED_FEED |
| `sec-edgar` | corporate | OK | 39 | government_official / OFFICIAL_VERSIONED_FEED |
| `sec-press-releases` | regulatory | OK | 25 | government_official / OFFICIAL_VERSIONED_FEED |
| `kraken-status` | market | OK | 50 | exchange_official / OFFICIAL_VERSIONED_FEED |

## Source Notes

- **NVD**: The NVD API 2.0 (services.nvd.nist.gov) works with 120-day max date windows. Some windows return 404 (likely no CVEs published in those periods).
- **Federal Reserve**: RSS endpoint was changed from `pressreleases.xml` to `press_all.xml`.
- **SEC EDGAR**: The `getcurrent` Atom feed returns current-day filings. Most are corporate forms (3, 4, 144, Schedule 13D).
- **SEC Press Releases**: RSS feed at `sec.gov/news/pressreleases.rss` provides regulatory announcements.
- **CISA KEV**: Full catalog with `dateAdded` timestamps — excellent security source.
- **Kraken Status**: Returns ~50 current/recent incidents via API.

## Pilot Feasibility

All 6 families are feasible. Pilot built with 1886 real qualified cases.
Scale to 1500+ with balanced families requires additional source development for non-security families.
