# Secret Leak Report

Last updated: 2026-06-04 12:51:42 UTC+8

leak_count: 3

| file | line | type | redacted_match |
|---|---:|---|---|
| `scripts\test_market_radar_history_v19c.py` | 411 | telegram_bot_token | `8848...wxyz` |
| `scripts\test_market_radar_sender_v19a.py` | 2171 | telegram_bot_token | `1234...MnOp` |
| `scripts\_r2_real_tg_send.py` | 29 | telegram_bot_token | `8848...Pits` |
