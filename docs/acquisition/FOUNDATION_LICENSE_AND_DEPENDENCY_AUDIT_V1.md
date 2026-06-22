# Foundation License & Dependency Audit V1

**Audit Date:** 2026-06-22
**Scope:** All new and existing dependencies used by the acquisition layer

## New Dependencies Added

| Dependency | Version | License | Purpose | Alternative | Rollback |
|-----------|---------|---------|---------|-------------|---------|
| httpx | ≥0.27 | BSD-3-Clause | HTTP transport for acquisition HTTP client | urllib3, requests | Use built-in urllib.request |
| trafilatura | ≥1.6 | Apache-2.0 | HTML body text extraction | BeautifulSoup, readability-lxml, manual regex | Already have fallback path |
| feedparser | ≥6.0 | MIT | RSS/Atom feed parsing | xml.etree, lxml | Parse RSS XML manually |
| PyYAML | ≥6.0 | MIT | YAML source registry loading | json, toml | Convert YAML to JSON |

## Existing Dependencies Reused

| Dependency | Version | License | Usage |
|-----------|---------|---------|-------|
| pytest | — | MIT | Test framework |
| jsonschema | — | MIT | JSON Schema validation (optional) |

## Dependency Rules

1. All new dependencies are optional where possible (trafilatura has fallback path)
2. No dependencies make network calls at import time
3. No dependencies require paid API keys
4. No dependencies start background processes
5. No dependencies with GPL/AGPL licenses that would affect project licensing

## Dependency Count

- **Total new runtime dependencies:** 4 (httpx, trafilatura (optional), feedparser, PyYAML)
- **Total optional/conditional:** 1 (trafilatura)
- **Test-only dependencies:** 0 new

## License Compatibility

All selected dependencies use permissive open-source licenses (BSD-3-Clause, Apache-2.0, MIT) that are compatible with commercial and research use.
