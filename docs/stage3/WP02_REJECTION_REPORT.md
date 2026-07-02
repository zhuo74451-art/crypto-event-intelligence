# WP-02 Rejection Report

## Invalidated Records

**Previous 490 cases** — invalidated for failing all 5 mandatory gates:

| Gate | Result for previous 490 cases |
|------|-------------------------------|
| Historical authority | FAIL — all event_times = 2026-07-02 (collection time) |
| Crypto relevance | FAIL — regulatory/corporate mapped to SPX, not crypto |
| Real outcome labels | FAIL — outcome_refs empty, outcome_windows empty |
| Complete provenance | FAIL — all timestamps identical, no source-native data |
| Chronological splits | FAIL — 100% BUILD, no DEVELOPMENT or BLIND |

**Total invalidated:** 490 cases + 490 evidence records = 980 records moved to rejected/quarantined

## Current Rejected Records

Total rejected records in rejected_records.jsonl: 1,230

Includes:
- 490 previously invalidated cases
- 490 previously invalidated evidence records
- 250 records from pre-existing rejects
