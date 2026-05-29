# v0.8.1 Token Unlock Calendar Quality Report

- status: needs_data
- calendar_rows: 2
- real_rows: 0
- sample_rows: 2
- upcoming_30d_rows: 2
- large_unlock_rows: 1

## Blocking Issues

- real_rows below target: 0 / 20
- invalid_time_rows: 0
- unsupported_symbol_rows: 0
- missing_amount_rows: 0
- missing_source_rows: 0

## Preview

| unlock_id | asset | time | amount_usd | source | flags |
|---|---|---|---:|---|---|
| sample_xrp_unlock | XRP | 2026-05-30T00:00:00Z | 50000000 | manual_calendar | sample_row |
| sample_avax_unlock | AVAX | 2026-06-15T00:00:00Z | 25000000 | manual_calendar | sample_row |

## Rule

Only real, sourced unlock rows should drive Telegram or backtest candidates. Sample rows are allowed for pipeline tests only.
