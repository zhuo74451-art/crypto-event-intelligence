# v13 Rule Tightening Report

- generated_at_china: 2026-05-28 19:55:46 UTC+8
- input_candidates: 2000
- archive_count: 622
- keep_count: 1179
- review_count: 199

| metric | before | after | delta | note |
|---|---:|---:|---:|---|
| total_candidates | 2000 | 1378 | -622 | strict archive removes low-quality unknown candidates |
| archive_count | 0 | 622 | 622 | rows marked archive by v13 strict gate |
| other_uncategorized_count | 705 | 83 | -622 | unknown bucket after strict gate |
| protected_valid_event_count | 289 | 289 | 0 | protected types should not be harmed by garbage gate |
