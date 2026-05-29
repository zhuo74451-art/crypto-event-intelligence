# v13 Rule Tightening Report

- generated_at_china: 2026-05-28 20:01:05 UTC+8
- input_candidates: 5000
- archive_count: 2055
- keep_count: 2507
- review_count: 438

| metric | before | after | delta | note |
|---|---:|---:|---:|---|
| total_candidates | 5000 | 2945 | -2055 | strict archive removes low-quality unknown candidates |
| archive_count | 0 | 2055 | 2055 | rows marked archive by v13 strict gate |
| other_uncategorized_count | 1968 | 193 | -1775 | unknown bucket after strict gate |
| protected_valid_event_count | 707 | 646 | 0 | protected types should not be harmed by garbage gate |
