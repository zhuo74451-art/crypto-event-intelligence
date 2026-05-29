# Shadow Source Evaluation

- generated_at_china: 2026-05-28 19:24:40 UTC+8
- watcher_event_rows: 9
- shadow_event_rows: 1
- shadow_source_count: 1

## Shadow Sources With Current Rows

| source_id | source_type | shadow_events | tg_default_route | evaluation_status |
| --- | --- | --- | --- | --- |
| cex_listing_announcement | exchange_listing | 1 | archive | shadow_collect |

## Route Distribution

- review: 1

## Decision

- Shadow rows are collected for evaluation only and should not be treated as production TG signals.
- Promotion from shadow requires enough outcomes and a non-noisy source effectiveness report.
