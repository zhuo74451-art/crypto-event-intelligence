# Pilot Source Report V1

**Pilot Date:** 2026-06-22 (dry-run)
**Pilot Mode:** One-shot, dry-run with fixture data

## Sources Attempted

| Source ID | Source Name | Status | Observations |
|-----------|-------------|--------|-------------|
| sec-edgar | SEC EDGAR (fixture) | ✅ Success | 2 |
| federal-register | Federal Register (fixture) | ✅ Success | 2 |
| federal-reserve-press | Fed Press (fixture) | ✅ Success | 2 |
| github-releases | GitHub Releases (fixture) | ✅ Success | 2 |

## Results Summary

- **Sources attempted:** 4 (SEC, Federal Register, Fed RSS, GitHub)
- **Sources successful:** 4
- **Total raw documents:** 8
- **Total observations:** 8
- **Errors:** 0
- **Paid APIs used:** None
- **Background processes:** None
- **Notifications sent:** None

## Timestamp Quality

All 8 observations have:
- published_at: explicit_source ✓
- first_seen_at: retrieval_only ✓
- retrieved_at: retrieval_only ✓

## Limitations

1. Live network pilot not yet executed — requires real API endpoints
2. BLS and BEA adapters require free API keys for live operation
3. GitHub API rate limited to 60 req/hr unauthenticated
4. PDF extraction not implemented (OCR deferred)
5. changedetection.io, ArchiveBox, Apprise are stub contracts only
6. No persistent storage beyond file-based evidence store

## No Paid API Verification

- ✅ All sources use free public APIs or fixtures
- ✅ No API keys required for fixture tests
- ✅ No paid subscriptions used
- ✅ No credentials stored in code
