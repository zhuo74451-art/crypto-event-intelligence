# v0.8 Source Readiness Report

This report turns the current open issues into historical-data checks. It is for source QA and product operations only.

| area | historical_evidence | status | next_action |
| --- | --- | --- | --- |
| token_unlock_calendar | candidate_token_unlock=0; backtest_samples=0; false_positive_like_rows=0; calendar_rows=500; real_calendar_rows=500 | usable | Add real unlock rows from a token-unlock calendar source and keep stricter keyword rules; do not treat generic 'release/unlock' text as token unlock. |
| cex_listing_sources | candidate_exchange_listing=3; backtest_samples=0; enabled_sources=1; okx_bybit_enabled=0 | binance_only | Keep Binance parser strict on publish time; add OKX/Bybit only after each source has parse-time validation and historical replay counts. |
| cex_netflow_baseline | baseline_rows=37; historical_cex_mentions=36; source_rows=9 | needs_more_baseline | Continue collecting rolling baseline; use baseline_multiple gate before increasing TG volume. Historical news can identify CEX-transfer narratives, but baseline must come from watcher snapshots. |
| hyperliquid_state_changes | state_rows=9; history_rows=9; historical_hyperliquid_mentions=43; whale_backtest_samples=2 | state_tracking_ready | Keep state and state-history files as source of truth for position-change alerts; historical news replay can test message relevance, but true change detection needs watcher state snapshots. |
| source_usefulness_from_history | historical_event_rows=7; historical_source_rows=9; live_sent_count=8; live_followup_4h=7; macro_samples=94 | usable_for_triage | Use historical usefulness report to decide expand/digest/holdout; do not wait 7 days for obvious low-quality historical buckets. |

## Practical Decision

- Do not expand random news volume. Expand only sources with source-specific validation.
- Token unlock needs real calendar rows plus stricter event typing.
- CEX listing can expand to OKX/Bybit after parser-level time validation, not before.
- CEX netflow and Hyperliquid require watcher state/baseline history; historical news backtest is only a relevance proxy.
- Historical usefulness reports can replace part of the 7-day waiting period for obvious bad buckets, but live follow-up is still needed for first-hand watcher-only signals.
