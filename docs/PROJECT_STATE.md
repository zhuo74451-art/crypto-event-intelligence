# Project State

Last updated: 2026-05-29 12:52:28 UTC+8

## Current Version

Current active layer: v0.8 Telegram live intelligence pilot plus v0.6/v0.7 data-quality foundations.

The project has working local pipelines for:

- Raw news normalization.
- Event candidate import.
- Symbol/entity/taxonomy enrichment.
- Candidate relevance scoring.
- Mature candidate filtering.
- Stratified auto-review sampling.
- Binance price backfill.
- BTC/ETH abnormal return calculation.
- Backfill quality validation.
- Price source validation.
- Time provenance auditing.
- Claude consultation prompt generation.
- Manual label evaluation.
- First-hand watcher alerts for curated Ethereum addresses and stablecoin mint/burn.
- Watcher alert normalization into the existing event/backtest and TG draft preview schemas.
- Telegram live monitor with quality gates, rate limits, and China-time send windows.
- Scheduled China-time morning/noon/evening digests.
- CEX netflow rolling baseline context.
- Hyperliquid large-position state-change tracking.
- Binance USD-M long/short ratio snapshots for digest context.
- Binance USD-M market-state snapshots for price, volume, open-interest, funding, and crowding context.

## v0.8 Telegram Intelligence Pilot

```text
live_monitor: deployed on server systemd service
time_policy_file: config/tg_send_time_policy.csv
latest_time_window: daytime_active
time_policy_enabled: true
morning_digest_status: pass
noon_digest_status: pass
evening_digest_status: pass
long_short_status: pass
long_short_top_crowded_asset: DOGE
long_short_top_crowded_bias: 多头拥挤
market_state_status: pass
market_state_coverage: 7/7
market_state_btc_24h: 0.4400%
market_state_eth_24h: 1.1440%
market_state_top_price_move: HYPE 7.5370%
market_state_top_oi_change: BTC 3.1240%
market_state_focus_assets: ETH;BTC
market_state_first_screen_status: pass
market_state_first_screen_lines: 4
derivatives_history_percentile_rows: 7
quality_loop_first_step_status: pass
followup_4h_rows: 7
followup_24h_rows: 0
source_usefulness_sent_count: 8
source_usefulness_source_count: 4
source_usefulness_basis: sent alerts plus 4h/24h follow-up only
historical_replay_broad_selected_rows: 200
historical_replay_conservative_selected_rows: 120
historical_replay_non_btc_single_asset_selected_rows: 1
historical_replay_broad_summary: results/v08_historical_replay_broad_200_findings.md
historical_replay_conservative_summary: results/v08_historical_replay_conservative_120_findings.md
historical_replay_non_btc_single_asset_summary: results/v08_historical_replay_non_btc_single_asset_200_findings.md
server_schedule: morning around 08:30, noon around 12:30, evening around 20:30 China time
interpretation: the live TG surface is running; next work is proving signal usefulness, separating BTC/macro pollution, and reducing noisy sources, not expanding every possible feed.
```

## v14 Claude-Directed Quality Fixes

```text
status: intraday radar remains paused until data-quality gates pass
time_field_diagnosis: results/v14_time_field_diagnosis.md
webhook_subsource_count: 37
webhook_source_score_gt_50_count: 7
needs_taxonomy_review_remaining: 5
etf_fund_flow_kept_rows: 3
etf_fund_flow_archived_rows: 54
flow_split_etf_specific_rows: 45
flow_split_etf_creation_redemption_rows: 9
flow_split_etf_macro_news_rows: 32
flow_split_institutional_disclosure_rows: 4
flow_split_cex_netflow_rows: 2
flow_split_unclear_rows: 10
active_exploit_rows: 28
active_exploit_urgent_eligible_count: 0
short_price_in_pass_rows: 276
short_price_in_block_rows: 5
upgrade_digest_rows: 3
upgrade_background_rows: 1
upgrade_block_rows: 26
publishable_criteria_passed_rows: 0
publishable_criteria_blocked_rows: 281
security_alert_ingest_status: warning
security_alert_normalized_rows: 0
etf_daily_rows: 612
etf_daily_latest_date: 27 May 2026
etf_daily_latest_total_net_flow_usd: -733400000.0
etf_daily_publishable: true
first_hand_input_rows: 9
first_hand_intraday_candidate_rows: 0
first_hand_digest_candidate_rows: 1
first_hand_daily_digest_candidate_rows: 1
first_hand_archived_rows: 7
publishable_criteria_golden_rows: 30
publishable_criteria_validation_failed_rows: 0
e2e_preview_etf_publishable: true
e2e_preview_first_hand_publishable_rows: 2
e2e_latency_sla_pass: false
hyperliquid_snapshot_position_count: 5
hyperliquid_snapshot_total_position_value_usd: 329883053.54
hyperliquid_snapshot_near_liquidation_value_usd: 0
prefilter_passed_rows: 172
prefilter_blocked_rows: 109
composer_gate_passed_count: 20
composer_digest_candidate_count: 20
composer_interrupt_candidate_count: 15
composer_review_count: 5
composer_block_count: 256
publish_policy_digest_rows: 0
publish_policy_interrupt_rows: 0
publish_policy_block_rows: 281
strict_digest_security_rows: 0
strict_digest_fund_flow_rows: 0
strict_digest_upgrade_rows: 0
publish_policy_report: results/v14_publish_policy_report.md
composer_report: results/v14_composer_scores_report.md
digest_preview: results/v14_digest_preview.md
interpretation: only morning/evening digest-style output is allowed from this branch; rows failing source score, amount context, taxonomy, or asset-consistency checks stay out of Telegram.
```

## v0.7 First-Hand Watcher MVP

```text
plan: docs/V07_FIRST_HAND_INTEL_PLAN.md
watchlist_validation_status: pass
watchlist_fail_count: 0
address_alert_rows: 0
stablecoin_alert_rows: 0
deduped_alert_rows: 9
event_rows: 9
tg_draft_rows: 9
tg_draft_validation_status: pass
tg_draft_validation_fail_count: 0
normalization_status: pass
report: results/v07_watcher_daily_report.md
interpretation: local first-hand watcher MVP is dry-run/live-ready; it does not call Telegram unless the explicit TG test sender is run with --send.
```

## Latest Stable Real Run

Dataset:

```text
data/raw_news_real_500_older.csv
```

Latest v043 result:

```text
candidates: 500
stratified selected: 37
backfill rows: 37
quality rows: 37
```

Stratified selection diagnostics:

```text
diagnostic_report: results/v043_stratified_selection_diagnostics.md
selected_rows: 37
underfill_reason: capped macro/other/hack_security plus scarce eligible non-macro event types
policy_note: do not relax event_type caps without Claude/product approval
```

v043 selection vs v0.6 relevance audit:

```text
audit_report: results/v043_selection_vs_v06_relevance_audit.md
v06_human_review_rows: 23
v06_discard_rows: 14
v06_discard_rate: 0.3784
safe_to_use_as_current_evidence: no
recommended_use: historical_baseline_only
clean_sample_next_step: use_v06_filtered_preview_after_asset_attribution_cleanup
interpretation: existing v043 backtest is a historical baseline, not the cleanest current sample
```

v0.6-filtered mature sample preview:

```text
preview_report: results/v06_filtered_mature_sample_preview.md
preview_file: data/event_candidates_v06_filtered_mature_review_auto50_preview.csv
eligible_count: 60
selected_count: 50
status: preview only; does not overwrite v043 outputs and does not run backtest
```

v0.6 preview asset attribution audit:

```text
audit_report: results/v06_filtered_preview_asset_attribution_audit.md
high_risk_rows: 11
medium_risk_rows: 17
low_risk_rows: 22
interpretation: preview still needs asset attribution cleanup before a clean backtest branch
```

v0.6 clean low-risk preview:

```text
preview_report: results/v06_clean_low_risk_preview.md
preview_file: data/event_candidates_v06_clean_low_risk_preview.csv
selected_low_risk_rows: 22
excluded_medium_risk_rows: 17
excluded_high_risk_rows: 11
interpretation: safe sanity-check subset only; too small for statistical conclusions
```

v0.6 clean low-risk preview backtest:

```text
runner: scripts/run_v06_clean_low_risk_preview_backtest.py
events_file: data/events_v06_clean_low_risk_preview.csv
backfill_rows: 22
quality_rows: 22
findings: results/v06_clean_low_risk_preview_backtest_findings.md
interpretation: sanity-check only; does not replace v043 historical outputs
```

Backtest readiness:

```text
report: results/backtest_readiness_report.md
overall_conclusion_status: not_ready
ready_for_statistical_conclusions: no
review_count: 5
local_review_count: 3
claude_review_count: 1
mixed_local_claude_review_count: 1
interpretation: if not ready, do not cite event-type performance as a product conclusion
```

v0.6 asset attribution fix plan:

```text
fix_plan_report: results/v06_asset_attribution_fix_plan.md
top_action: keep_for_clean_preview
top_action_count: 22
interpretation: non-destructive plan for fixing or excluding high/medium attribution-risk rows
```

v0.6 entity rule review packet:

```text
entity_review_report: results/v06_entity_rule_review_packet.md
top_review_type: protocol_exploit_primary_asset_policy
top_review_count: 5
interpretation: protocol exploit primary-asset policy needs direction before automatic fixes
```

Backfill status:

```text
- ok: 37
```

Quality status:

```text
- pass: 37
```

Latest time audit:

```text
total_rows: 1055
pass: 1055
warning: 0
fail: 0
price_kline_lag_out_of_range_count: 0
```

Manual label status:

```text
total_rows: 201
labeled_rows: 201
label_coverage_pct: 100.0
auto_prefilled_rows: 73
error_rows: 0
```

Auto-label assist status:

```text
suggest_ready_rows: 73
avg_auto_label_confidence: 0.8299
auto_prefilled_rows_in_run: 0
auto_provisional_rows_in_run: 0
manual_review_required_rows_after_run: 50
manual_unlabeled_rows_after_run: 9
```

Auto-verify status:

```text
auto_verified_rows_in_run: 0
provisional_remaining_after_run: 50
audit_sample_rows: 20
```

Auto-close status:

```text
auto_closed_rows_in_run: 0
selected_low_risk_rows: 0
audit_sample_rows: 0
```

Auto-fill unlabeled status:

```text
auto_filled_rows_in_run: 9
unlabeled_rows_after_run: 0
audit_sample_rows: 9
manual_review_required_rows_current: 13
```

Manual review audit:

```text
manual_review_required_rows: 13
manual_review_required_rate: 0.0647
status: pass
```

TG pilot gate:

```text
gate_report: results/v06_tg_pilot_gate_report.md
current_status: pass
```

Secret leak scan:

```text
secret_leak_count: 0
status: pass
report: results/secret_leak_report.md
```

Project OS validation:

```text
overall_status: pass
blocking_or_fail_count: 0
review_count: 2
report: results/project_os_validation_report.md
```

Local environment:

```text
overall_status: pass
fail_count: 0
python_version: 3.11.9
report: results/local_environment_report.md
```

Command registry:

```text
command_count: 97
missing_script_count: 0
status: pass
doc: docs/COMMAND_REGISTRY.md
```

Review action queue:

```text
open_action_count: 12
requires_claude_yes_count: 3
can_do_locally_yes_count: 6
unknown_rule_count: 0
doc: docs/PROJECT_REVIEW_ACTIONS.md
```

Artifact manifest:

```text
artifact_count: 324
required_artifact_count: 274
missing_required_count: 0
stale_required_count: 0
status: pass
doc: docs/ARTIFACT_MANIFEST.md
```

Claude consultation archive:

```text
indexed_response_files: 46
index_doc: docs/CLAUDE_RESPONSE_INDEX.md
decision_review_items: 778
decision_review_doc: docs/CLAUDE_DECISION_REVIEW.md
rule: accepted direction changes must be copied into docs/DECISIONS.md before implementation
```

## Key Output Files

```text
data/event_candidates_real_500_older_review.csv
data/event_candidates_real_500_older_review_suggested.csv
data/event_candidates_real_500_older_mature_review_auto50.csv
data/events_real_500_older_mature_50.csv
data/v06_manual_label_sheet.csv
results/v043_older_mature50_event_price_backfill.csv
results/v043_older_mature50_event_quality_report.csv
results/v043_time_provenance_report.csv
results/v043_time_provenance_summary.csv
results/v06_auto_label_summary.csv
results/v06_auto_verify_summary.csv
results/v06_auto_close_summary.csv
results/v06_auto_fill_unlabeled_summary.csv
results/v06_manual_review_required_summary.csv
results/v06_tg_pilot_gate_report.md
results/v06_manual_label_eval_summary.csv
results/v06_manual_label_eval_errors.csv
results/claude_response_index.csv
results/secret_leak_report.md
results/project_os_validation_report.md
results/project_os_validation_summary.csv
results/local_environment_report.md
results/command_registry.csv
docs/COMMAND_REGISTRY.md
docs/ARTIFACT_MANIFEST.md
data/events_v06_clean_low_risk_preview.csv
results/v06_clean_low_risk_preview_event_price_backfill.csv
results/v06_clean_low_risk_preview_event_quality_report.csv
results/v06_clean_low_risk_preview_backtest_findings.md
results/backtest_readiness_report.md
data/project_review_action_queue.csv
docs/PROJECT_REVIEW_ACTIONS.md
data/claude_decision_review_queue.csv
```

## Current Bottleneck

The system can process historical news, generate first-hand alerts, send Telegram messages, and produce scheduled digests. The current bottleneck is no longer infrastructure. The bottleneck is data quality: source trust, taxonomy clarity, amount/context verification, asset attribution, and enough historical coverage across regimes.

Before scaling alert volume:

- Keep `secret_leak_count = 0`.
- Keep intraday radar paused until Claude-defined quality gates pass.
- Keep live alerts focused on rare, quality-gated first-hand events, not dense observation boards.
- Keep stablecoin, ETF/fund flow, long/short, and security items primarily as digest/context signals unless they pass explicit amount, source, and context gates.
- Measure post-alert follow-up movement and historical replay behavior before adding more sources.
- Avoid turning broad market/news items into high-frequency real-time noise.
- Keep all wording as intelligence/research context, not trading advice.

## Current Engineering Focus

1. Keep applying Claude v14 quality fixes one by one: source split, taxonomy cleanup, ETF/fund-flow context, exploit amount verification, and digest-only routing.
2. Build a cleaner morning/evening digest from strict quality-gated rows before restarting any intraday board.
3. Solve historical coverage/regime limits by finding a better older event source or proving the current database is too sparse.
4. Keep historical backtest/data-quality tools available, but do not treat small-sample event_type performance as a product conclusion.
5. Consult Claude before direction-level changes such as new source tiers, publishing policy, source expansion, or taxonomy changes.
