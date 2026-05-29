# v0.8 Realtime Intelligence Next Plan

Sources:

- `results/v08_claude_remaining_plan_review.md`
- `results/v08_claude_user_view_project_review.md`

## Current Diagnosis

The project has a working Telegram live surface and several first-hand watcher seeds. The main risk is no longer local infrastructure. The main risk is that the current alert stream is still too thin and too dependent on broad BTC/macro/news-like inputs.

The next phase should ship more first-hand sources, keep the user-facing Telegram experience readable, and measure alert usefulness through follow-up and source-level evidence. Do not expand random historical news exports; they have already shown BTC/macro domination.

## Claude User-View Review: Accepted Direction

Decision:

- Stop treating random second-hand news replay as the main path.
- Expand first-hand sources: CEX listing announcements, token unlock calendar, CEX wallet/netflow, stablecoin supply changes, Hyperliquid position changes, and large liquidations.
- Keep Telegram as the product surface. The user experience matters: China-time scheduling, short Chinese-first messages, strong context, and no spam.
- Keep realtime Telegram reactions/replies out of the core quality loop.
- Use source-level follow-up, timeliness, source diversity, and user retention/forwarding proxies instead.

Today-compressed 7-day implementation checklist:

1. Add or wire CEX listing watcher.
2. Add or wire token unlock watcher.
3. Keep CEX netflow, stablecoin mint/burn, Hyperliquid, funding, and liquidation watchers running.
4. Run watcher history/sample pipeline into normalized events and TG drafts.
5. Run source quality loop and product metrics.
6. Generate user-experience audit for recent drafts.
7. Refresh Project OS and keep the next Claude questions batched.

## Priority Order

1. Use automated follow-up as the primary quality loop.
   - Track 4h/24h/72h post-alert movement.
   - Compare each source and event type across historical replay.
   - Do not use Telegram replies/reactions as a realtime quality metric.

2. Add alert severity tiers.
   - `critical`: rare, high-confidence, should interrupt.
   - `watch`: useful real-time monitoring.
   - `fyi`: lower urgency, digest-eligible.

3. Add per-source and per-token rate limits.
   - Cap total live alerts per day.
   - Cap noisy sources like Hyperliquid if they dominate.
   - Add token cooldown unless severity increases.
   - Shape routine delivery around China-time user attention windows instead of rigid fixed-time rules.

4. Add cross-source correlation.
   - Hyperliquid position + CEX netflow + funding anomaly should rank higher than isolated single-source signals.
   - Correlation should be deterministic first; model review can come later for borderline cases.

5. Add "Why this matters" context.
   - Last time this wallet/entity moved.
   - Recent related alerts.
   - Whether this is unusual relative to recent baseline.
   - What to monitor next, without trade direction.

6. Add daily usefulness metrics.
   - Alert count by source.
   - Quality gate pass/fail.
   - Source concentration.
   - 4h/24h follow-up move after alerts.

## Source Policy

Double down:

- CEX listing announcements.
- Token unlock calendar.
- Hyperliquid large positions.
- CEX netflow.

Keep but strict:

- Stablecoin treasury flows.
- Aave V3 lending liquidations.
- Funding-rate anomalies.
- Watched Ethereum addresses.

Do not add yet:

- Broad DEX swap monitoring.
- Broad social sentiment.
- Mempool monitoring.
- More generic second-hand news scraping.
- Mobile app / UI / paid tiers.

Potential later source:

- DEX liquidity removal, not raw swaps, after current feed quality is measurable.

## TG Product Rule

Every alert should answer:

```text
Why now?
Why this?
Why care?
What should be watched next?
```

It must not answer:

```text
Should I take a specific trade?
```

## Time Policy

The live watcher stays continuous, but routine sends should respect China-time attention windows:

- 00:00-07:00: quiet; only critical alerts pass by default.
- 07:00-10:00: morning check window.
- 10:00-15:00: daytime active window.
- 15:00-18:00: afternoon trading window.
- 18:00-24:00: evening trading window.

This is implemented as editable configuration, not a hard product rule:

```text
config/tg_send_time_policy.csv
```

Critical alerts may still pass outside active windows. Lower-priority routine alerts should concentrate into periods when users are more likely to read Telegram or watch markets.

## Scheduled Digests

Add separate scheduled summary surfaces:

- Morning digest: around 08:30 China time, previous 20:00-08:00 window.
- Noon digest: around 12:30 China time, 08:00-12:00 window.
- Evening digest: around 20:30 China time, 12:00-20:00 window.
- Summarizes sent TG alerts, source/event-type concentration, and follow-up availability.
- Adds Binance USD-M public long/short ratio snapshots for major markets.
- Uses this as a convenience layer, not a trading instruction layer.

Current files:

```text
scripts/watch_binance_long_short_ratios.py
scripts/build_tg_morning_digest.py
data/binance_long_short_snapshot.csv
data/tg_digest_sent_state.csv
results/v08_binance_long_short_summary.csv
results/v08_tg_morning_digest.md
results/v08_tg_morning_digest_summary.csv
results/v08_tg_noon_digest.md
results/v08_tg_noon_digest_summary.csv
results/v08_tg_evening_digest.md
results/v08_tg_evening_digest_summary.csv
```

## Initial User-Ready Bar

Before showing 10 real users:

- Average under 5 high-priority alerts per day.
- No repeated low-context spam.
- Each alert has Chinese rich formatting and clear interpretation.
- Each alert is tracked for follow-up movement.
- There is a daily report showing what was useful and what was noise.

## Next Engineering Tasks

1. Expand first-hand source coverage, especially CEX listings and token unlocks.
2. Keep automated follow-up running for sent alerts.
3. Keep severity, source caps, token cooldown, and China-time send windows active.
4. Improve sent-state metadata completeness so follow-up reports can attribute every alert to a source and asset.
5. Build product metrics around source diversity, timeliness, follow-up movement, and digest consistency.
6. Improve Hyperliquid context with previous position state.
7. Improve CEX netflow context with rolling baseline.
8. Keep random news replay, DEX swaps, social sentiment, and UI work parked.

## First-Hand Source Expansion Files

Current new source files:

```text
data/cex_listing_sources.csv
data/token_unlock_calendar.csv
scripts/watch_cex_listing_announcements.py
scripts/watch_token_unlock_calendar.py
scripts/build_tg_product_metrics_report.py
scripts/build_tg_user_experience_audit.py
```

Run locally:

```powershell
python scripts/watch_cex_listing_announcements.py
python scripts/watch_token_unlock_calendar.py
python scripts/run_v07_first_hand_watchers.py --hours 24 --limit-alerts 100
python scripts/run_tg_quality_loop.py --lookback-days 7 --followup-min-age-hours 4
python scripts/build_tg_product_metrics_report.py --lookback-days 7
python scripts/build_tg_user_experience_audit.py --limit 10
```

## Source Usefulness Reporting

Current local files:

```text
scripts/enrich_tg_sent_state_metadata.py
scripts/build_tg_source_usefulness_report.py
scripts/run_tg_quality_loop.py
results/v08_tg_quality_loop_summary.csv
results/v08_tg_sent_state_metadata_enrichment_summary.csv
results/v08_tg_source_usefulness_report.md
results/v08_tg_source_usefulness_summary.csv
results/v08_tg_source_usefulness_by_source.csv
```

Run locally:

```powershell
python scripts/enrich_tg_sent_state_metadata.py
python scripts/build_tg_source_usefulness_report.py --lookback-days 7
python scripts/run_tg_quality_loop.py --lookback-days 7 --followup-min-age-hours 4
```

Use the report to classify each source as:

- promising
- review_noise
- needs_instrumentation
- insufficient_data

Do not add new broad sources until CEX netflow and Hyperliquid have measurable historical replay and follow-up behavior.

## 2026-05-28 Execution Snapshot

Claude's 7-day recommendation has been compressed into today's build where practical. Current status:

- Planning accepted: first-hand source expansion is now higher priority than more random historical news replay.
- Implemented CEX listing announcement watcher.
- Implemented local token unlock calendar watcher.
- Wired both sources into the first-hand watcher pipeline and TG draft generator.
- Rebuilt TG drafts as Chinese rich-format messages with China-time timestamps, bold first line, interpretation, follow-up watch item, and no trade instruction.
- Initial local watcher run generated 21 first-hand drafts:
  - 17 CEX listing announcement candidates.
  - 1 token unlock candidate.
  - 2 Tether treasury transfer candidates.
  - 1 CEX netflow candidate.
- CEX listing watcher was then corrected because Binance announcement rows without parsed time were being treated as current.
- Corrected local 24h watcher run with real Etherscan key generated 4 first-hand drafts:
  - 0 CEX listing candidates.
  - 1 token unlock candidate.
  - 2 Tether treasury transfer candidates.
  - 1 CEX netflow candidate.
- Corrected local TG draft validation: 4 checked, 0 fail, 0 warning.
- Local TG user experience audit: 10 checked, 10 pass, 0 review.
- Local 7-day product metrics:
  - sent_count: 8.
  - first_hand_share: 100%.
  - followup_4h_rows: 5.
  - followup_24h_rows: 0 because the newest live samples are still too young.
  - top_source_share: 50%, which still needs monitoring to avoid source concentration.
- Server watcher service was updated and restarted.
- Server live watcher first post-fix cycle:
  - 4 normalized event rows.
  - 2 quality-gate checked rows.
  - 1 row sent.
  - 0 send failures.
- Scheduled digest timers are enabled:
  - morning around 08:30 China time.
  - noon around 12:30 China time.
  - evening around 20:30 China time.

Remaining from the 7-day recommendation:

1. Fill `data/token_unlock_calendar.csv` with real near-term unlock rows instead of the current small seed list.
2. Improve CEX listing parser so announcement titles that contain project names are not over-trusted without exchange pair context.
3. Add OKX/Bybit announcement sources after Binance parser quality is stable.
4. Add rolling baseline context for CEX netflow.
5. Add previous-state tracking for Hyperliquid positions.
6. Keep source usefulness reports running for at least 7 days before expanding noisy sources.

## 2026-05-28 Historical QA Pass

User request: resolve the remaining source-quality issues with historical backtest data where possible.

Implemented:

- Tightened token unlock classification:
  - Generic `释放` / `解锁` no longer maps to token unlock.
  - Requires token-specific language such as `token unlock`, `vesting unlock`, `代币解锁`, `解锁代币`, `代币释放`, or `归属解锁`.
  - Rebuilt older500 candidates with v081 prefix.
  - Result: older500 v081 candidate token_unlock count is 0; previous false positives are removed.
- Added historical source usefulness report:
  - `scripts/build_historical_source_usefulness_from_backtest.py`
  - `results/v081_historical_source_usefulness_report.md`
  - `results/v081_historical_source_usefulness_by_event_type.csv`
  - `results/v081_historical_source_usefulness_by_source.csv`
- Added source readiness report:
  - `scripts/build_v08_source_readiness_report.py`
  - `results/v081_source_readiness_report.md`
  - `results/v081_source_readiness_summary.csv`
- Rebuilt conservative historical replay using v081 rules:
  - selected rows: 120.
  - event types: macro 94, hack_security 10, institutional_flow 6, staking_governance 3, halving 3, network_upgrade 2, whale_position 2.
  - token_unlock: 0.
  - exchange_listing: 0 in backtest sample.
- Added Hyperliquid position state history:
  - `data/hyperliquid_position_state_history.csv`
  - local history rows after first run: 9.
  - server watcher updated and restarted so future cycles append history.

Historical QA conclusions:

- Token unlock is not ready as a real-time source until a real calendar source is loaded. Historical news did not provide clean token unlock samples after stricter rules.
- CEX listing remains Binance-only. Historical older500 contains too few clean listing rows to justify OKX/Bybit expansion yet.
- CEX netflow has a live rolling baseline file with 37 rows. It needs more watcher snapshots; historical news mentions can validate relevance but cannot replace wallet-flow baseline data.
- Hyperliquid has historical mentions and now has persistent state history. Actual change detection should rely on state snapshots, not historical news prose.
- Historical source usefulness is now usable for triage. Macro and hack_security are benchmark-polluted; institutional_flow is promising-looking but still under-sampled.

## 2026-05-28 Source Quality Report Automation

Added one-command source-quality refresh:

```powershell
python scripts/run_v081_source_quality_reports.py
```

It refreshes:

- `results/v081_token_unlock_calendar_quality_report.md`
- `results/v081_cex_netflow_baseline_report.md`
- `results/v081_hyperliquid_state_history_report.md`
- `results/v081_historical_source_usefulness_report.md`
- `results/v081_source_readiness_report.md`

Latest local results:

- Token unlock calendar:
  - status: `needs_data`
  - real_rows: 0
  - sample_rows: 2
  - target real rows before use: 20+
- CEX netflow baseline:
  - status: `needs_more_history`
  - baseline_rows: 37
  - ready_pairs: 0
  - max pair samples: 4 / 72
- Hyperliquid state history:
  - status: `needs_more_history`
  - history_rows: 9
  - ready_positions: 0
  - max snapshots per position: 1 / 12

Interpretation:

- The system should keep running live collection, but not increase source volume yet.
- Token unlock is blocked on real calendar data, not code.
- CEX netflow and Hyperliquid are correctly instrumented; they need accumulated state history before stronger claims.

## 2026-05-28 Token Unlock Import Layer

Added a non-destructive token unlock import workflow:

```powershell
python scripts/import_raw_token_unlocks_to_calendar.py --input data/raw_token_unlocks_template.csv --output data/token_unlock_calendar_imported.csv
python scripts/build_token_unlock_calendar_quality_report.py --input data/token_unlock_calendar_imported.csv --output results/v081_token_unlock_imported_quality_report.md --summary results/v081_token_unlock_imported_quality_summary.csv
```

New files:

- `data/raw_token_unlocks_template.csv`
- `data/token_unlock_column_mapping.json`
- `scripts/import_raw_token_unlocks_to_calendar.py`
- `data/token_unlock_calendar_imported.csv`
- `results/v081_token_unlock_import_report.md`

Safety fix:

- `scripts/watch_token_unlock_calendar.py` now skips sample/template rows by default.
- `--include-samples true` is required to emit sample unlock alerts for local tests.
- Server watcher was updated and restarted.
- Latest server result:
  - token calendar rows: 2
  - sample_skipped_rows: 2
  - token_unlock alert_rows: 0

Rule:

Never publish sample unlock rows to Telegram. Real unlock rows must include asset, UTC unlock time, source, amount or percentage, and should pass `build_token_unlock_calendar_quality_report.py`.

## 2026-05-28 CoinMarketCap Token Unlock API Integration

The token unlock source is no longer blocked on manual CSV data.

Implemented:

- `scripts/probe_token_unlock_sources.py`
  - Scans public pages and JS chunks for usable token-unlock APIs.
- `scripts/fetch_coinmarketcap_token_unlocks.py`
  - Calls CoinMarketCap public page API.
  - Writes `data/token_unlock_calendar_cmc.csv`.
  - Writes raw JSON to `data/token_unlock_calendar_cmc_raw.json`.
- `scripts/run_v07_first_hand_watchers.py`
  - Refreshes CMC token unlock calendar before the watcher runs.
  - Falls back to the previous local CMC file if refresh fails.
- `scripts/generate_watcher_tg_drafts.py`
  - Token unlock messages now show `预计解锁` in UTC+8.
  - `发现时间` remains separate, also UTC+8.
- `scripts/build_token_unlock_calendar_quality_report.py`
  - Adds configurable `--require-symbol-map` and `--require-amount-usd`.
  - Default behavior no longer blocks calendar readiness just because an asset is not in Binance-oriented `symbol_map.csv`.

Current local/server evidence:

- API endpoint: `https://api.coinmarketcap.com/data-api/v3/token-unlock/listing`
- API total count: 1264.
- fetched rows: 500.
- future rows: 495.
- next 72h rows: 234.
- current watcher threshold output: 5 token unlock alerts.
- source quality: `ready`.
- server service: restarted and active.

Operational rule:

- Do not publish every unlock. The watcher can see hundreds of near-term unlocks, but TG should only surface large enough events.
- Current watcher emits if `unlock_pct_circulating >= 2` or `unlock_amount_usd >= 10,000,000`.
- Quality gate blocks low-dollar unlocks even when percent is high; this prevents tiny microcap unlocks from flooding the group.
- For product value, prefer large USD unlocks, large circulating-supply percentage, and assets users are likely to recognize.

## 2026-05-28 Live TG Source Visibility Update

The newly built sources are now visible in the Telegram group, not just in local files.

Server changes:

- `run_v07_tg_live_monitor_server.sh`
  - `--max-send-per-cycle 5`
  - `--daily-send-limit 45`
- `run_v07_first_hand_watchers.py`
  - Hyperliquid uses `--alert-first-seen true`.
  - Hyperliquid uses `--alert-snapshot true`.
  - CEX baseline seeding runs before the live CEX netflow watcher.
- `seed_cex_netflow_baseline_from_transfers.py`
  - Seeds 4h CEX baseline buckets from recent historical Etherscan transfers.

Latest server evidence:

- CEX historical seed:
  - raw transfers checked: 6000.
  - used transfers: 1097.
  - new 4h buckets: 24.
  - baseline rows: 384.
- Hyperliquid watcher:
  - alert rows: 5.
  - state rows: 9.
- Live sends after update:
  - ETH Hyperliquid large-position snapshot.
  - HYPE Hyperliquid large-position snapshot.
  - HOME token unlock.
  - BTC Hyperliquid large-position snapshot.

Current product rule:

- Let users see the source classes now.
- Keep low-quality microcap unlocks blocked.
- Keep token cooldown active so repeated HYPE/BTC snapshots do not flood the group.
- Use historical Etherscan transfer buckets for CEX baseline immediately instead of waiting days for baseline accumulation.

## 2026-05-28 Claude TG Product/Card Review

New planning file:

```text
docs/V09_TG_MARKET_RADAR_PLAN.md
```

Claude's direct critique:

- The project is technically working but still too backend-first.
- The TG product should not be a continuous stream of full explanatory cards.
- Users need a scannable market radar: ranked board snapshots, rare interrupt alerts, and scheduled digests.
- Full cards should become detail surfaces, not the default output for every event.

Accepted direction:

1. Main TG surface:
   - ranked board snapshots during China-time active windows
   - rare interrupt alerts only for high-magnitude first-hand events
   - morning/noon/evening digests
2. Detail cards:
   - security incidents
   - major Hyperliquid positions
   - major stablecoin/CEX flows
   - large token unlocks
3. Archive/history:
   - lower-priority qualified events stay in CSV/SQLite and follow-up reports
   - not every qualified event deserves a main-channel push

Next implementation priority:

1. Build a board generator from existing watcher outputs.
2. Route events by severity bucket: interrupt / board / archive / discard.
3. Replace most main-channel full cards with compact ranked rows.
4. Keep full detail cards only for interrupt-grade events or linked detail items.
5. Add source/token concentration metrics to the quality loop.

This changes the v0.9 focus from "more sources" to "better product shape".
