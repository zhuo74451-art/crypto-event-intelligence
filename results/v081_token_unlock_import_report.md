# v0.8.1 Token Unlock Import Report

- input: `C:\Users\PC\Desktop\Projects\事件情报系统\data\raw_token_unlocks_template.csv`
- output: `C:\Users\PC\Desktop\Projects\事件情报系统\data\token_unlock_calendar_imported.csv`
- raw_rows: 3
- output_rows: 3
- real_rows: 0
- sample_rows: 3
- invalid_time_rows: 0
- unsupported_symbol_rows: 0

## Preview

| unlock_id | asset_symbol | unlock_time_utc | unlock_amount_usd | unlock_pct_circulating | source |
| --- | --- | --- | --- | --- | --- |
| sample_001 | XRP | 2026-05-30T00:00:00Z | 50000000 | 2.5 | manual_template |
| sample_002 | AVAX | 2026-06-15T00:00:00Z | 25000000 | 1.8 | manual_template |
| sample_003 | SOL | 2026-06-20T12:00:00Z | 75000000 | 3.2 | manual_template |

## Usage

Default output is non-destructive. After reviewing quality, rerun with `--output data/token_unlock_calendar.csv` to replace the live calendar.
