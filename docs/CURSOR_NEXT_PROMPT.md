# Cursor Next Prompt

You are taking over one review cycle for Crypto Event Intelligence.

Workspace:

```text
C:\Users\PC\Desktop\Projects\事件情报系统
```

Hard rules:

- No Notion
- No trading integration
- No web app work
- No buy/sell/long/short advice
- Do not overwrite historical outputs
- Human review uses China-time fields (`*_china`)
- API/math uses UTC fields (`*_utc`)
- `auto_publish` must stay disabled

Read the project memory below, then execute the task checklist.

## AGENTS.md

```text
# Crypto Event Intelligence Agent Rules

## Project Direction

This project is a local crypto event intelligence and research pipeline.

It converts historical or real-time news into structured event candidates, audits time and price quality, filters low-value events, and prepares reviewed intelligence items.

## Hard Boundaries

- Do not connect Notion.
- Do not place trades.
- Do not generate buy/sell/long/short signals.
- Do not connect exchange order APIs.
- Do not build a web app unless explicitly requested.
- Keep the core workflow local: CSV, SQLite, Python scripts, and Markdown docs.
- Human-facing time is China time: `Asia/Shanghai`, `UTC+8`.
- Machine/API time is UTC: `*_utc` and Unix milliseconds.

## Working Style

- Keep project momentum high.
- If key information is missing and guessing would damage the architecture, stop and ask.
- If a better technical path is obvious, state it and take it.
- Prefer scripts and repeatable checks over manual one-off operations.
- Preserve outputs with versioned prefixes when changing major pipeline behavior.
- Use `docs/PROJECT_DASHBOARD.md` as the first human-readable status view before inspecting detailed code or CSVs.

## Required Validation

Before treating a result as usable:

- Time provenance audit must pass or warnings must be understood.
- Price source validation should have no mismatches in sampled rows.
- Backfill quality report should not contain unexplained `fail`.
- Review queues should be manually sampled before any publishing workflow.
- `auto_publish` remains disabled until manually labeled ground truth exists.

## Collaboration

- Codex implements and verifies.
- Cursor is optional and not required for project progress.
- Claude is consulted only for direction-level questions once enough unresolved questions accumulate.
- All cross-agent handoffs must be written to files under `docs/`.
- Project state should be refreshed with `python scripts/refresh_project_state.py`.
- Project dashboard should be rendered with `python scripts/render_project_dashboard.py`.
```
## docs/PROJECT_STATE.md

```text
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
interpretation: only morning/evening digest-style 

...(truncated)
```
## docs/PROJECT_DASHBOARD.md

```text
# Project Dashboard

Last updated: 2026-05-29 12:52:29 UTC+8

## Gates

- Blocking/failing items: 0
- Review items: 12

| area | metric | value | target | status |
|---|---|---:|---|---|
| backtest | backtest_readiness_review_count | 5 | 0 before conclusion use | review |
| backtest | ready_for_statistical_conclusions | no | yes before product claims | review |
| backtest | stratified_selected_count | 37 | 50 desired | review |
| backtest | v043_safe_as_current_evidence | no | yes for current conclusions | review |
| backtest | v043_selected_v06_discard_rate | 0.3784 | historical baseline only | review |
| backtest | v043_selected_v06_discard_rows | 14 | 0 for clean current sample | review |
| backtest | v06_entity_protocol_exploit_policy_rows | 5 | ask Claude/policy | review |
| backtest | v06_preview_asset_high_risk | 11 | 0 before clean backtest | review |
| claude | pending_claude_decision_items | 778 | review before implementation | review |
| project_os | project_os_validation_review_count | 2 | tracked | review |
| relevance | other_review_keep_review_count | 5 | small manual queue | review |
| tg_draft | private_pilot_draft_count | 9 | 10-20 | review |
| claude | claude_open_questions | 0 | 20 | wait |
| backtest | backtest_readiness_claude_review_count | 1 | direction queue | info |
| backtest | backtest_readiness_local_review_count | 3 | local cleanup queue | info |
| backtest | backtest_readiness_mixed_review_count | 1 | local then Claude | info |
| backtest | mature_72h_count | 500 |  | info |
| backtest | stratified_capped_event_types | 3 | review caps with Claude | info |
| backtest | stratified_diagnostic_selected | 37 | explain underfill | info |
| backtest | stratified_unused_eligible_after_cap | 142 | do not relax automatically | info |
| backtest | v06_clean_low_risk_preview_rows | 22 | sanity-check only | info |
| backtest | v06_entity_unsupported_primary_rows | missing | rule candidate | info |
| backtest | v06_filtered_preview_eligible | 60 | preview only | info |
| backtest | v06_filtered_preview_selected | 50 | preview only | info |
| backtest | v06_fix_plan_entity_review_rows | 8 | rule improvement | info |
| backtest | v06_fix_plan_exclude_rows | 9 | do not backtest | info |
| backtest | v06_fix_plan_unsupported_rows | missing | no fake BTC/ETH | info |
| backtest | v06_low_risk_backfill_ok_rows | 22 | preview only | info |
| backtest | v06_low_risk_quality_pass_rows | 22 | preview only | info |
| backtest | v06_preview_asset_low_risk | 22 | safe subset | info |
| claude | claude_response_files | 46 | indexed | info |
| data | older500_candidates | 500 |  | info |
| data | v06_discard_audit_rows | 80 |  | info |
| data | v06_other_review_rows | 210 |  | info |
| data | v06_publish_review_rows | 69 |  | info |
| labels | auto_closed_rows_in_run | 0 | >=0 | info |
| labels | auto_filled_rows_in_run | 9 | >=0 | info |
| labels | auto_label_suggest_ready_rows | 73 |  | info |
| labels | auto_prefilled_rows | 73 | increase | info |
| labels | auto_verified_rows_in_run | 0 | >=0 | info |
| labels | manual_review_required_rows | 13 | decrease by batch review | info |
| labels | next_batch_review_required | 30 |  | info |
| labels | next_label_batch_size | 30 | 30 | info |
| labels | provisional_remaining | 50 | decrease | info |
| project_os | open_review_actions | 12 | tracked | info |
| relevance | discard_count | 431 |  | info |
| relevance | human_review_count | 69 |  | info |
| relevance | other_review_auto_discard_candidate_count | 205 | taxonomy cleanup candidate | info |
| suggestions | suggest_include_count | 234 |  | info |
| tg_draft | private_pilot_reviewed_count | 9 | review before any posting | info |
| tg_draft | private_pilot_validation_warning_count | 0 | 0 preferred | info |
| environment | local_environment_fail_count | 0 | 0 | pass |
| labels | manual_label_rows | 201 | >=200 | pass |
| labels | manual_labeled_rows | 201 | >=200 before TG | pass |
| labels | manual_review_required_rate | 0.0647 | <=0.085 before TG drafts | pass |
| project_os | artifact_missing_required_count | 0 | 0 | pass |
| project_os | artifact_stale_required_count | 0 | 0 | pass |
| project_os | command_registry_missing_scripts | 0 | 0 | pass |
| project_os | project_os_validation_fail_count | 0 | 0 | pass |
| project_os | review_action_unknown_rules | 0 | 0 | pass |
| relevance | auto_publish_count | 0 | 0 | pass |
| security | secret_leak_count | 0 | 0 | pass |
| tg_draft | daily_private_pilot_status | pilot_signal_ready | ready_for_review or better | pass |
| tg_draft | private_pilot_auto_send_enabled_count | 0 | 0 | pass |
| tg_draft | private_pilot_validation_fail_count | 0 | 0 | pass |
| tg_gate | review_failure_modes_doc | present | required sections | pass |
| tg_gate | rollback_workflow_doc | present | required sections | pass |
| time | price_kline_lag_out_of_range_count | 0 | 0 | pass |
| time | time_audit_fail_count | 0 | 0 | pass |

## Backfill Status

| value | count |
|---|---:|
| 

...(truncated)
```
## docs/ACTIVE_GOALS.md

```text
# Active Goals

## Goal 1: Project OS

Status: active

Objective:

Create a local file-based working memory and handoff system so Codex can continue the project without losing context, and Claude can be consulted when question backlog reaches threshold.

Acceptance:

- `AGENTS.md` exists.
- `docs/PROJECT_STATE.md` exists.
- `docs/ACTIVE_GOALS.md` exists.
- `docs/DECISIONS.md` exists.
- `docs/VALIDATION_CHECKLIST.md` exists.
- `docs/DAILY_WORKFLOW.md` exists.
- `scripts/render_project_dashboard.py` generates a readable status dashboard.

## Goal 2: Event Intake Ground Truth

Status: active

Objective:

Create and maintain an AI-first labeled dataset for v0.6 review quality with audit gates instead of heavy manual labeling.

Acceptance:

- `data/v06_manual_label_sheet.csv` exists.
- Labeled rows reach at least 200.
- AI-owned labels have audit samples and rollback gates.
- `scripts/check_v06_tg_pilot_gate.py` can decide whether TG draft pilot is allowed.

## Goal 3: TG Draft System

Status: active

Boundary:

Draft-only local files are allowed. Telegram API calls and auto-send remain disabled.

Objective:

Generate TG message drafts for approved intelligence events, but do not auto-send.

Acceptance:

- Only reviewed or low-risk pilot events can generate drafts.
- Drafts include factual summary, affected asset, route, confidence, time, source, and risk note.
- No buy/sell/long/short language.
- Drafts are written to local CSV/Markdown and default to `pending_review`.
```
## docs/DECISIONS.md

```text
# Decisions

## D001: Human-Facing Time Is China Time

Decision:

Human review fields use China time: `Asia/Shanghai`, `UTC+8`.

Implementation:

- Keep `*_china` for review.
- Keep `*_utc` for API/math.
- Binance Kline requests use UTC milliseconds.

Reason:

The operator reviews news and Telegram output in China time, while APIs use UTC.

## D002: Backtest Time Uses Published Time

Decision:

Backtests use `published_at` as the default `backtest_time`, not the earlier source event time.

Reason:

This models what was known after the news reached the system and avoids look-ahead bias.

## D003: Unsupported Asset Does Not Mean Irrelevant

Decision:

Assets without Binance symbols can enter `unsupported_research`, but cannot enter Binance price backtest.

Reason:

HYPE/ONDO/WLD-like events can be valuable intelligence even when Binance spot/futures data is unavailable.

## D004: Auto Publish Is Disabled

Decision:

All would-be `auto_publish` items are downgraded to `human_review`.

Reason:

No publishing automation should run before 200+ manually labeled rows prove event intake quality.

## D005: Cursor Handoff Is File-Based

Decision:

Cursor receives generated prompt files instead of direct UI automation.

Reason:

Cursor chat automation is brittle without an official local API. File-based handoff is auditable and repeatable.

## D006: AI-First Labeling With Audit Gates

Decision:

AI owns the main event-intake labeling workflow. Human work is limited to low-confidence review, audit samples, rollback investigation, and taxonomy/policy changes.

Implementation:

- Use `docs/V06_AI_LABELING_POLICY.md` as the labeling policy.
- Use `scripts/check_v06_tg_pilot_gate.py` before any TG draft pilot.
- Keep `auto_publish` disabled.

Reason:

The product needs Web3-aware AI judgment at scale. Large manual labeling queues are slow, inconsistent, and do not match the intended operating model.

## D007: Delay TG Drafts Until Labeling Fragility Is Reduced

Decision:

Do not build the TG draft generator yet, even though an earlier pilot gate passed.

Implementation:

- Treat `results/v06_claude_next_engineering_direction.md` as the latest direction-level guidance.
- Continue v0.6 quality work until `manual_review_required` is at or below 10% or explicitly accepted.
- Require a larger audit sample before draft pilot.

Reason:

Claude identified TG drafts as a downstream visibility step that would amplify upstream labeling errors. A 59-row review queue on 201 labels is still too high for a production-like draft workflow.

## D008: Gate Pass Is Not Enough For TG Drafts

Decision:

Even after the stricter pilot gate passed, TG draft generation remains delayed.

Implementation:

- Treat `results/v06_claude_after_gate_next_step.md` as current direction-level guidance.
- Expand audit sample to 200+ rows.
- Add synthetic edge cases for timezone, missing assets, macro scope, conflicting signals, and unsupported assets.
- New target: `manual_review_required_rate <= 0.085`.

Reason:

The previous pass was too close to the 10% ceiling. A single noisy macro batch could break the gate again.

## D009: High-Confidence Macro Discards Leave The Main Review Queue

Decision:

High-confidence rows with `manual_decision=discard`, `manual_channel_route=macro_policy`, and `event_scope=multi_asset` or `market_wide` do not remain in the main `manual_review_required` queue.

Implementation:

- Use `scripts/release_v06_macro_discard_rows.py`.
- Move released rows to `macro_discard_audit`.
- Preserve released rows in `data/v06_macro_discard_released_rows.csv`.
- Do not release `approve_publish` or `keep_review` rows with this rule.

Reason:

These rows are already excluded from publishing and trading-facing flows. Keeping them in the main review queue inflates the blocker rate without improving TG draft safety. They still remain auditable and reversible.

## D010: TG Draft Pilot Is A Product Smoke Test, Not A Statistical Claim

Decision:

Start a local TG draft pilot queue before waiting for statistically significant event-type backtest conclusions.

Implementation:

- Generate local draft files only.
- Do not call Telegram API.
- Do not auto-send.
- Keep every draft in `pending_review` until a human approves, rejects, or edits it.
- Use backtests as smoke tests for time, symbol, and price sanity; do not present event-type performance as a product conclusion.
- Keep `auto_publish` disabled.

Reason:

Claude's latest direction review argued that the product is an intelligence feed, not a quantitative trading strategy. The backtest is useful for catching broken data, but the next product risk is whether reviewed event drafts are useful to real readers.

## D011: Multi-Asset Exploit Events Should Not Be Blocked By Primary-Asset Perfection

Decision:

Protocol exploit and security events may carry multiple relevant asset tags during draft/review workflows.

Implementation:

- Do not force uncertain exploit events into BTC or ETH just to make the price

...(truncated)
```
## docs/CLAUDE_RESPONSE_INDEX.md

```text
# Claude Response Index

Last updated: 2026-05-29 12:52:19 UTC+8

This index tracks local Claude responses stored under `results/`. It does not mark advice as accepted; accepted project decisions still belong in `docs/DECISIONS.md`.

## Counts

| response_type | count |
|---|---:|
| next_consultation | 30 |
| other | 9 |
| manual_reduction | 2 |
| macro_holdout | 1 |
| release_rules | 1 |
| engineering_direction | 1 |
| question_backlog | 1 |
| tg_pilot | 1 |

## Latest Responses

| file | type | modified_at_china | title |
|---|---|---|---|
| `results\v15_claude_liquidation_whale_onchain_review.md` | next_consultation | 2026-05-29 12:52:15 | Claude Response |
| `results\v15_claude_hyperliquid_after_impl_review.md` | next_consultation | 2026-05-29 12:20:52 | Claude Response |
| `results\v15_claude_tg_digest_hyperliquid_review.md` | next_consultation | 2026-05-29 12:09:56 | Claude Response |
| `results\v14_claude_derivatives_percentile_review.md` | next_consultation | 2026-05-28 23:01:02 | Claude Response |
| `results\v14_claude_after_p0_p1_review.md` | next_consultation | 2026-05-28 22:45:55 | Claude Response |
| `results\v14_claude_market_state_next_review.md` | next_consultation | 2026-05-28 22:35:17 | Claude Response |
| `results\v14_claude_next_public_data_tasks.md` | other | 2026-05-28 22:23:07 | v14 系统上线评估：综合审查意见 |
| `results\v14_claude_next_data_layer_review.md` | other | 2026-05-28 22:18:58 | 综合审查意见：v14 系统上线评估 |
| `results\v14_claude_next_user_value_review.md` | other | 2026-05-28 22:15:28 | 综合审查意见：v14 系统上线评估 |
| `results\v14_claude_digest_integration_review.md` | other | 2026-05-28 22:11:10 | 验证报告综合审查意见 |
| `results\v14_claude_gate_next_review.md` | other | 2026-05-28 22:02:21 | 验证报告审查意见 |
| `results\v14_claude_three_task_followup_review.md` | other | 2026-05-28 21:59:12 | 验证报告总结 |

## Operating Rule

- Store raw Claude responses in `results/`.
- Run `python scripts/index_claude_responses.py` after adding a response.
- Convert accepted recommendations into `docs/DECISIONS.md` before changing product direction.
- Do not treat unreviewed Claude text as implementation authority.
```
## docs/CLAUDE_DECISION_REVIEW.md

```text
# Claude Decision Review

Last updated: 2026-05-29 12:52:20 UTC+8

This queue extracts possible decision/action items from Claude responses. It is a review aid only.

Rules:

- `pending` means not accepted.
- `accepted` requires a matching entry in `docs/DECISIONS.md`.
- `implementation_status=done` requires code/docs/tests to prove the change.
- Do not implement direction-level recommendations directly from this queue.

## Status Counts

| decision_status | count |
|---|---:|
| pending | 778 |

## Scope Counts

| suggested_scope | count |
|---|---:|
| unknown | 391 |
| tg | 111 |
| asset_attribution | 81 |
| qa | 61 |
| data | 57 |
| product | 30 |
| macro_policy | 17 |
| taxonomy | 15 |
| backtest | 15 |

## Pending Preview

| item_id | scope | source | recommendation |
|---|---|---|---|
| `claude_543ac47df43a43a2` | unknown | `results\claude_cost_control_response.md` | **Recommendation: Only uncertain cases after multi-stage filtering** |
| `claude_8270357b7b993ab4` | unknown | `results\claude_cost_control_response.md` | **Must implement before any AI call:** |
| `claude_eb8b4a4727559d57` | macro_policy | `results\claude_cost_control_response.md` | Non-English without translation (if English-only policy) |
| `claude_80c57432ef4b80b7` | unknown | `results\claude_cost_control_response.md` | **Simple binary decisions**: "Does this mention a specific exploit?" "Is this about a token listing?" |
| `claude_13d077fb61555791` | unknown | `results\claude_cost_control_response.md` | **Critical insight:** Small models are 90% as good for structured tasks, 60% as good for judgment calls. Route accordingly. |
| `claude_05babe6363176b24` | unknown | `results\claude_cost_control_response.md` | **Do NOT batch time-sensitive events** (large exploits, major transfers) |
| `claude_e1c146e0117882c3` | unknown | `results\claude_cost_control_response.md` | Separate fast-track queue for high-value events (>$1M, known hacker wallets) |
| `claude_f476a21fabb428c8` | unknown | `results\claude_cost_control_response.md` | Don't batch >200 events - quality degrades, timeouts increase |
| `claude_55cef8ccf8607922` | unknown | `results\claude_cost_control_response.md` | Don't batch mixed languages - context confusion |
| `claude_e177322f836e2d4b` | unknown | `results\claude_cost_control_response.md` | Don't delay critical events for batch efficiency |
| `claude_305f22481a51a8cb` | unknown | `results\claude_cost_control_response.md` | Queue 1 (real-time): High-priority events → immediate small model → Claude if needed |
| `claude_7e5bb4d312104575` | unknown | `results\claude_cost_control_response.md` | └─> Claude Decision |
| `claude_fa195a41d602688f` | tg | `results\claude_cost_control_response.md` | **Volume explosion**: 100x more events than Telegram (every block has transactions) |
| `claude_dcb87e841ec89911` | unknown | `results\claude_cost_control_response.md` | **Structured data**: On-chain events are machine-readable (no NLP needed for extraction) |
| `claude_3e84b940aef26350` | unknown | `results\claude_cost_control_response.md` | **Real-time expectations**: Exploit detection must be <1 min latency |
| `claude_a01fa78835f7f75f` | unknown | `results\claude_cost_control_response.md` | **High signal variance**: 99.9% of transactions are routine, 0.1% are critical |
| `claude_fd4790d0ad68770e` | unknown | `results\claude_cost_control_response.md` | └─> Anomaly Detection: Statistical outliers → PRIORITY_REVIEW |
| `claude_a50016486efbd203` | unknown | `results\claude_cost_control_response.md` | Ambiguous multi-step transactions requiring reasoning |
| `claude_d71519fd121aa6ac` | unknown | `results\claude_cost_control_response.md` | **Critical change:** On-chain watchers should generate **structured alerts**, not raw events. LLMs review alerts, not transactions. |
| `claude_1cd1a8ec3f260947` | tg | `results\claude_cost_control_response.md` | **Cost impact:** With proper filtering, on-chain events should cost LESS per published alert than Telegram scraping (more structured, less noise). |
| `claude_5bb1c9458e70ddb2` | unknown | `results\claude_cost_control_response.md` | Should decrease over time as rules improve |
| `claude_6f8d4dceb9dcabb4` | unknown | `results\claude_cost_control_response.md` | **Human override rate**: % of AI decisions reversed by humans |
| `claude_09385dca5f8eb3e7` | unknown | `results\claude_cost_control_response.md` | **Don't overthink it. Start here:** |
| `claude_b9614cecb40803bc` | unknown | `results\claude_cost_control_response.md` | **Route remainder to Claude** with confidence scoring prompt - 1 day |
| `claude_d58dee70a18d2a86` | qa | `results\claude_next_response_20260527_163346.md` | **Product direction**: Fundamentally sound, but you're over-engineering the quality gates before proving the core value hypothesis. |
```
## docs/COMMAND_REGISTRY.md

```text
# Command Registry

Last updated: 2026-05-29 12:52:20 UTC+8

This is the short operational command list. It does not replace the detailed Runbook.

Rules:

- Prefer `python scripts/run_v06_quality_gate.py` for a full local refresh.
- Do not run commands requiring secrets unless the secret is set only in the current terminal environment.
- Commands here do not permit Notion, trading, web app work, auto-send, or trading advice.

| id | category | command | network | secret | script_exists |
|---|---|---|---|---|---|
| `quality_gate` | project_os | `python scripts/run_v06_quality_gate.py` | no | no | yes |
| `daily_private_pilot` | publishing_draft | `python scripts/run_daily_private_pilot.py` | no | no | yes |
| `daily_private_pilot_ai_review` | publishing_draft | `python scripts/run_daily_private_pilot.py --ai-review` | yes | yes | yes |
| `daily_private_pilot_report` | publishing_draft | `python scripts/build_daily_private_pilot_report.py` | no | no | yes |
| `tg_draft_rule_improvement` | publishing_draft | `python scripts/build_tg_draft_rule_improvement_report.py` | no | no | yes |
| `project_os_validation` | project_os | `python scripts/validate_project_os.py` | no | no | yes |
| `secret_scan` | security | `python scripts/check_secret_leaks.py` | no | no | yes |
| `local_environment` | project_os | `python scripts/check_local_environment.py` | no | no | yes |
| `cursor_prompt` | agent_handoff | `python scripts/generate_cursor_prompt.py` | no | no | yes |
| `claude_prompt` | agent_handoff | `python scripts/generate_claude_question_prompt.py --force` | no | no | yes |
| `claude_query` | agent_handoff | `python scripts/query_claude_next.py` | yes | yes | yes |
| `claude_index` | agent_handoff | `python scripts/index_claude_responses.py` | no | no | yes |
| `claude_decision_review` | agent_handoff | `python scripts/build_claude_decision_review_queue.py` | no | no | yes |
| `project_review_actions` | project_os | `python scripts/build_project_review_actions.py` | no | no | yes |
| `artifact_manifest` | project_os | `python scripts/build_artifact_manifest.py` | no | no | yes |
| `v07_first_hand_watchers` | first_hand_intel | `python scripts/run_v07_first_hand_watchers.py --hours 24 --limit-alerts 100` | conditional | conditional | yes |
| `v07_watchlist_validation` | first_hand_intel | `python scripts/validate_v07_watchlists.py` | no | no | yes |
| `v07_first_hand_watchers_backfill` | first_hand_intel | `python scripts/run_v07_first_hand_watchers.py --hours 24 --limit-alerts 100 --backfill` | yes | conditional | yes |
| `tg_draft_test_send_dry_run` | publishing_draft | `python scripts/send_tg_draft_test.py --input data/tg_drafts_v07_watcher_private_pilot.csv --limit 1` | no | no | yes |
| `tg_draft_test_send` | publishing_draft | `python scripts/send_tg_draft_test.py --input data/tg_drafts_v07_watcher_private_pilot.csv --limit 1 --send` | yes | yes | yes |
| `v07_tg_live_monitor` | publishing_live | `python scripts/run_v07_tg_live_monitor.py --send --interval-seconds 300 --max-send-per-cycle 3 --limit-alerts 100` | yes | yes | yes |
| `v07_tg_live_monitor_stop` | publishing_live | `powershell -ExecutionPolicy Bypass -File scripts/stop_v07_tg_live_monitor.ps1` | no | no | yes |
| `binance_long_short_snapshot` | market_structure | `python scripts/watch_binance_long_short_ratios.py --output data/binance_long_short_snapshot.csv --summary results/v08_binance_long_short_summary.csv --period 1h --limit 2` | yes | no | yes |
| `tg_morning_digest` | publishing_digest | `python scripts/build_tg_morning_digest.py --output results/v08_tg_morning_digest.md --summary results/v08_tg_morning_digest_summary.csv` | yes | no | yes |
| `tg_noon_digest` | publishing_digest | `python scripts/build_tg_morning_digest.py --digest-label noon --window-end-hour 12 --window-hours 4 --output results/v08_tg_noon_digest.md --summary results/v08_tg_noon_digest_summary.csv` | yes | no | yes |
| `tg_evening_digest` | publishing_digest | `python scripts/build_tg_morning_digest.py --digest-label evening --window-end-hour 20 --window-hours 8 --output results/v08_tg_evening_digest.md --summary results/v08_tg_evening_digest_summary.csv` | yes | no | yes |
| `tg_sent_state_metadata_enrichment` | publishing_quality | `python scripts/enrich_tg_sent_state_metadata.py` | no | no | yes |
| `tg_source_usefulness_report` | publishing_quality | `python scripts/build_tg_source_usefulness_report.py --lookback-days 7` | no | no | yes |
| `tg_quality_loop` | publishing_quality | `python scripts/run_tg_quality_loop.py --lookback-days 7 --followup-min-age-hours 4` | yes | no | yes |
| `historical_signal_replay_broad_200` | backtest | `python scripts/run_v08_historical_signal_replay.py --limit 200 --mode broad` | yes | no | yes |
| `historical_signal_replay_conservative_120` | backtest | `python scripts/run_v08_historical_signal_replay.py --limit 120 --mode conservative` | yes | no | yes |
| `historical_source_usefulness_v081` | source_quality | `python scripts/buil

...(truncated)
```
## docs/ARTIFACT_MANIFEST.md

```text
# Artifact Manifest

Last updated: 2026-05-29 12:52:25 UTC+8

required_artifacts: 274
missing_required_count: 0
stale_required_count: 0

| artifact_id | category | path | required | freshness | exists | status | updated_at_china | notes |
|---|---|---|---|---|---|---|---|---|
| `project_root_rules` | project_os | `AGENTS.md` | yes | stable | yes | pass | 2026-05-27 14:29:24 | Local project rules. |
| `python_requirements` | project_os | `requirements.txt` | yes | stable | yes | pass | 2026-05-27 16:08:36 | Minimal local runtime dependencies. |
| `project_state` | project_os | `docs/PROJECT_STATE.md` | yes | fresh_24h | yes | pass | 2026-05-29 12:52:22 | Current local project memory. |
| `project_dashboard` | project_os | `docs/PROJECT_DASHBOARD.md` | yes | fresh_24h | yes | pass | 2026-05-29 12:52:23 | Current local dashboard. |
| `validation_checklist` | project_os | `docs/VALIDATION_CHECKLIST.md` | yes | stable | yes | pass | 2026-05-27 16:12:44 | Operator validation checklist. |
| `command_registry_doc` | project_os | `docs/COMMAND_REGISTRY.md` | yes | fresh_24h | yes | pass | 2026-05-29 12:52:20 | Runnable command inventory. |
| `artifact_manifest_doc` | project_os | `docs/ARTIFACT_MANIFEST.md` | no | fresh_24h | yes | pass | 2026-05-29 12:33:00 | This generated manifest. |
| `project_review_actions_doc` | project_os | `docs/PROJECT_REVIEW_ACTIONS.md` | yes | fresh_24h | yes | pass | 2026-05-29 12:52:24 | Dashboard review action queue. |
| `decisions_doc` | project_os | `docs/DECISIONS.md` | yes | stable | yes | pass | 2026-05-28 21:21:51 | Accepted direction decisions. |
| `mvp_timeline_doc` | project_os | `docs/MVP_TIMELINE.md` | yes | stable | yes | pass | 2026-05-27 16:52:39 | Current MVP definition and timeline estimate. |
| `ai_cost_control_policy` | project_os | `docs/AI_COST_CONTROL_POLICY.md` | yes | stable | yes | pass | 2026-05-27 17:07:32 | AI/Claude routing and spend-control policy. |
| `secret_setup_doc` | project_os | `docs/SECRET_SETUP.md` | yes | stable | yes | pass | 2026-05-27 17:55:40 | Local secret setup instructions. |
| `gitignore` | project_os | `.gitignore` | yes | stable | yes | pass | 2026-05-27 17:55:23 | Ignore local secret files and runtime noise. |
| `secret_template` | config | `config/secrets.example.ps1` | yes | stable | yes | pass | 2026-05-27 17:55:27 | Local secret template with placeholders only. |
| `cursor_prompt` | agent_handoff | `docs/CURSOR_NEXT_PROMPT.md` | yes | fresh_24h | yes | pass | 2026-05-28 14:22:47 | File-based Cursor handoff. |
| `cursor_backlog` | agent_handoff | `docs/CURSOR_TASK_BACKLOG.md` | yes | stable | yes | pass | 2026-05-27 15:51:15 | Cursor task backlog. |
| `claude_prompt` | agent_handoff | `docs/CLAUDE_NEXT_PROMPT.md` | yes | fresh_24h | yes | pass | 2026-05-29 12:47:18 | Current Claude consultation prompt. |
| `claude_question_backlog` | agent_handoff | `docs/CLAUDE_QUESTION_BACKLOG.md` | yes | stable | yes | pass | 2026-05-29 12:52:15 | Architecture question backlog. |
| `claude_response_index_doc` | agent_handoff | `docs/CLAUDE_RESPONSE_INDEX.md` | yes | fresh_24h | yes | pass | 2026-05-29 12:52:19 | Local Claude response index. |
| `claude_decision_review_doc` | agent_handoff | `docs/CLAUDE_DECISION_REVIEW.md` | yes | fresh_24h | yes | pass | 2026-05-29 12:52:20 | Claude recommendation review queue. |
| `symbol_map` | data | `data/symbol_map.csv` | yes | stable | yes | pass | 2026-05-27 17:36:15 | Asset to market symbol map. |
| `entity_dictionary` | data | `data/entity_dictionary.csv` | yes | stable | yes | pass | 2026-05-27 12:21:19 | Entity dictionary for intake rules. |
| `source_timezone_rules` | data | `data/source_timezone_rules.csv` | yes | stable | yes | pass | 2026-05-27 14:04:51 | Source time-zone assumptions. |
| `older500_raw_news` | data | `data/raw_news_real_500_older.csv` | yes | stable | yes | pass | 2026-05-26 10:43:18 | Older real-news source export. |
| `older500_candidates` | data | `data/event_candidates_real_500_older_review.csv` | yes | stable | yes | pass | 2026-05-27 14:06:50 | Older candidate import output. |
| `v06_relevance_scored` | data | `data/event_candidates_v06_relevance_scored.csv` | yes | stable | yes | pass | 2026-05-27 16:21:12 | v0.6 scored intake output. |
| `v06_manual_label_sheet` | data | `data/v06_manual_label_sheet.csv` | yes | stable | yes | pass | 2026-05-27 15:23:40 | AI-first review sheet. |
| `v06_other_review_classified` | data | `data/event_candidates_v06_other_review_classified.csv` | no | stable | yes | pass | 2026-05-27 18:38:15 | Rule-based split of the other_review bucket. |
| `project_review_action_queue` | data | `data/project_review_action_queue.csv` | yes | fresh_24h | yes | pass | 2026-05-29 12:52:24 | Generated dashboard action queue. |
| `claude_decision_queue` | data | `data/claude_decision_review_queue.csv` | yes | fresh_24h | yes | pass | 2026-05-29 12:52:20 | Generated Claude decision queue. |
| `tg_pilot_gate` | results | `results/v06_tg_pilot_gate_report.md` | ye

...(truncated)
```
## docs/PROJECT_REVIEW_ACTIONS.md

```text
# Project Review Actions

Last updated: 2026-05-29 12:52:24 UTC+8

This queue turns dashboard `review` metrics into explicit next actions. It does not approve product-direction changes.

## Counts

| field | value |
|---|---:|
| open_actions | 12 |
| requires_claude_yes | 3 |
| can_do_locally_yes | 6 |

## Actions

| action_id | owner | value | next_step | evidence |
|---|---|---:|---|---|
| `review_project_os_validation_review_count` | project_os | 2 | Keep review items visible; do not treat Project OS validation review rows as blocking failures. | `results/project_os_validation_report.md` |
| `review_other_review_keep_review_count` | local_rules | 5 | Inspect the remaining keep_review rows from the other_review split and convert recurring patterns into explicit taxonomy/entity rules. | `results/v06_other_review_reason_summary.md` |
| `review_private_pilot_draft_count` | local_rules | 9 | Keep the first private-pilot queue intentionally small after prefilter tightening; expand only by adding higher-quality sources or eligible event types, not by relaxing noise filters. | `results/daily_private_pilot_report.md` |
| `review_stratified_selected_count` | claude_product | 37 | Decide whether to relax event_type caps or improve scarce event-type classification first. Do not change caps locally without direction approval. | `results/v043_stratified_selection_diagnostics.md` |
| `review_v043_selected_v06_discard_rows` | local_research | 14 | Treat v043 backtest as historical baseline and inspect discarded selected rows before using it as current evidence. | `results/v043_selection_vs_v06_relevance_audit.md` |
| `review_v043_selected_v06_discard_rate` | local_research | 0.3784 | Use v0.6-filtered preview rather than old v043 selection for any future clean backtest branch. | `results/v043_selection_vs_v06_relevance_audit.md` |
| `review_v043_safe_as_current_evidence` | local_research | no | Keep v043 labeled as historical_baseline_only until a v0.6-filtered clean sample is approved and backtested. | `results/v043_selection_vs_v06_relevance_audit.md` |
| `review_v06_preview_asset_high_risk` | local_rules_then_claude | 11 | Apply only obvious dictionary/rule fixes; route protocol exploit and multi-chain policy questions to Claude/product direction. | `results/v06_filtered_preview_asset_attribution_audit.md` |
| `review_ready_for_statistical_conclusions` | local_research_then_claude | no | Do not cite event-type performance as a product conclusion; use the readiness report to decide what local cleanup remains and what needs Claude/product approval. | `results/backtest_readiness_report.md` |
| `review_backtest_readiness_review_count` | local_research_then_claude | 5 | Reduce local data-quality review items where possible; route policy-level blockers to Claude/product direction. | `results/backtest_readiness_report.md` |
| `review_v06_entity_protocol_exploit_policy_rows` | claude_product | 5 | Define primary-asset policy for exploit rows that mix protocol, chain, minted asset, stolen asset, and returned asset. | `results/v06_entity_rule_review_packet.md` |
| `review_pending_claude_decision_items` | project_direction | 778 | Send docs/CLAUDE_NEXT_PROMPT.md, then convert accepted recommendations into docs/DECISIONS.md before implementation. | `docs/CLAUDE_DECISION_REVIEW.md` |
```
## docs/VALIDATION_CHECKLIST.md

```text
# Validation Checklist

Run these before trusting results.

## Time

```powershell
python scripts/audit_event_time_provenance.py --candidates data/event_candidates_real_500_older_review.csv --backfill results/v043_older_mature50_event_price_backfill.csv --output results/v043_time_provenance_report.csv --summary results/v043_time_provenance_summary.csv
```

Required:

- `fail_count = 0`
- `price_kline_lag_out_of_range_count = 0`
- Any `source_lag_over_30m_count` must be reviewed.

## Price

```powershell
python scripts/validate_price_sources.py --sample-size 30 --output results/price_source_validation_report.csv --recent-output results/recent_price_point_sample.csv
```

Required:

- No `mismatch`.
- Request failures can be retried, but cannot be treated as validated prices.

## Backfill Quality

```powershell
python scripts/validate_backfill_results.py --input results/v043_older_mature50_event_price_backfill.csv --output results/v043_older_mature50_event_quality_report.csv
```

Required:

- `quality_status=fail` rows must be understood.
- `suspicious_extreme_return` rows must be manually reviewed.

## Review Quality

Required before TG:

- At least 200 labeled rows (AI prefill allowed, plus manual sampling).
- Clear false-positive categories.
- Clear false-negative categories.
- Clear wrong-asset examples.
- Clear wrong-time examples.

Evaluate manual labels:

```powershell
python scripts/auto_label_v06_sheet.py --input data/v06_manual_label_sheet.csv --output data/v06_manual_label_sheet.csv --summary results/v06_auto_label_summary.csv --apply-high-confidence --min-confidence 0.90 --apply-provisional --provisional-min-confidence 0.75
python scripts/auto_verify_v06_provisional_labels.py --input data/v06_manual_label_sheet.csv --output data/v06_manual_label_sheet.csv --summary results/v06_auto_verify_summary.csv --audit-output data/v06_auto_verify_audit_sample.csv --audit-size 20
python scripts/auto_close_low_risk_unlabeled.py --input data/v06_manual_label_sheet.csv --output data/v06_manual_label_sheet.csv --summary results/v06_auto_close_summary.csv --audit-output data/v06_auto_close_audit_sample.csv --audit-size 20
python scripts/auto_fill_unlabeled_review_required.py --input data/v06_manual_label_sheet.csv --output data/v06_manual_label_sheet.csv --summary results/v06_auto_fill_unlabeled_summary.csv --audit-output data/v06_auto_fill_unlabeled_audit_sample.csv --audit-size 20
python scripts/evaluate_manual_labels.py --input data/v06_manual_label_sheet.csv --summary results/v06_manual_label_eval_summary.csv --errors results/v06_manual_label_eval_errors.csv
python scripts/prepare_labeling_batch.py --input data/v06_manual_label_sheet.csv --output data/v06_manual_label_batch.csv --summary results/v06_labeling_batch_summary.csv --batch-size 30
python scripts/export_v06_review_packet.py --input data/v06_manual_label_batch.csv --output data/v06_manual_label_batch_review.csv
python scripts/apply_v06_review_packet.py --sheet data/v06_manual_label_sheet.csv --packet data/v06_manual_label_batch_review.csv --output data/v06_manual_label_sheet.csv
```

Required before TG:

- `labeled_rows >= 200`
- `false_positive_review_count` is understood and reduced.
- `false_negative_discard_count` is understood and reduced.
- Wrong asset/type/route patterns are converted into explicit rule or dictionary tasks.

## Publishing Safety

Required:

- `auto_publish` disabled.
- Draft generation only after manual approval.
- No buy/sell/long/short language.

TG draft pilot gate:

```powershell
python scripts/check_v06_tg_pilot_gate.py
```

Required:

- All rows in `results/v06_tg_pilot_gate_report.csv` have `status=pass`.
- Passing this gate allows draft generation only, not auto-send.

## Project OS

Check local environment:

```powershell
python scripts/check_local_environment.py
```

Run the consolidated project validation:

```powershell
python scripts/validate_project_os.py
```

Preferred full refresh:

```powershell
python scripts/run_v06_quality_gate.py
```

Required:

- `fail_count = 0` in `results/local_environment_summary.csv`.
- `requirements.txt` must exist and declare required packages.
- `blocking_or_fail_count = 0` in `results/project_os_validation_report.md`.
- `missing_script_count = 0` in `results/command_registry_summary.csv`.
- `unknown_rule_count = 0` in `results/project_review_action_summary.csv`.
- `missing_required_count = 0` in `results/artifact_manifest_summary.csv`.
- `stale_required_count = 0` in `results/artifact_manifest_summary.csv`.
- `review` items must remain visible and tracked; they are not completion proof.
- Hard boundary static scan must have zero findings.
- Key inputs checked by `validate_project_os.py` must be fresh within 24 hours by default.
- Accepted Claude decision review items must reference an existing `Dxxx` entry in `docs/DECISIONS.md`.
- `implementation_status=done` in the Claude decision review queue requires `decision_status=accepted`.
- `docs/PROJECT_DASHBOARD.md` must be rendered aft

...(truncated)
```
## docs/V06_REVIEW_FAILURE_MODES.md

```text
# v0.6 Review Failure Modes

Last updated: 2026-05-27

This file records why rows still require review after AI-first labeling. It is used to improve rules without turning the project back into a manual labeling workflow.

## Current Summary

Source files:

- `data/v06_manual_review_required_audit.csv`
- `results/v06_manual_review_required_report.md`
- `data/v06_synthetic_edge_cases.csv`

Current strict gate:

```text
manual_review_required_rows: 13
manual_review_required_rate: 0.0647
target_rate: <= 0.085
```

## Failure Modes

| mode | current meaning | handling |
|---|---|---|
| asset_missing | The event may matter, but no reliable primary asset was found. | Keep in review or route to macro/research holdout. Do not force a fake asset. |
| scope_ambiguous | The event may affect several assets or the full market. | Avoid single-asset TG drafts unless a clear primary asset exists. |
| low_ai_confidence | Confidence is below the publish-review floor. | Keep in review, improve rules, or discard if clearly non-actionable. |
| route_research_only | Useful context, but not a direct fast-alert item. | Keep as research material; do not push into TG draft flow by default. |
| route_macro_policy | Macro/regulatory event that needs separate treatment. | Route through macro policy; do not attribute to one coin unless explicit. |
| auto_provisional_needs_audit | AI found a likely label but not enough certainty for final routing. | Use audit sample and synthetic cases to improve rules. |
| medium_confidence_review | Model/rule confidence is medium and needs a second pass. | Keep in review or improve entity/taxonomy dictionary. |

## Examples Still Requiring Caution

- Market-wide liquidation headlines with no primary asset.
- ZachXBT or security items where the target asset/protocol is not clear.
- RWA/stablecoin growth metrics without a tradable primary asset.
- Tokenized stock/regulatory headlines where crypto asset attribution is weak.
- Payment adoption/product-card announcements that may be long-term relevant but not alert-worthy.

## Rules Not To Add Yet

- Do not map all macro or regulatory news to BTC by default.
- Do not convert every RWA or stablecoin metric into an alpha candidate.
- Do not publish market-wide liquidation or broad TVL metrics as single-asset alerts.
- Do not treat unsupported assets as irrelevant; route them to `unsupported_research`.
- Do not release `approve_publish` rows from review just to improve a gate metric.

## Regression Cases

Synthetic edge cases live in:

```text
data/v06_synthetic_edge_cases.csv
```

They cover:

- macro without asset
- explicit ETH regulatory event
- unsupported but relevant HYPE event
- soft hack/security language
- generic price recap
- product announcement noise
- legal enforcement macro
- network upgrade
- stablecoin mint/flow
- scraped footer noise
- token unlock
- non-crypto noise
- institutional BTC flow
- multi-asset macro
- hack with unknown asset

Any future labeling rule change should be checked against these cases before TG draft work resumes.
```
## docs/V06_ROLLBACK_WORKFLOW.md

```text
# v0.6 Rollback Workflow

Last updated: 2026-05-27

This workflow keeps AI-first labeling reversible. It is required before building any TG draft workflow.

## What Can Be Rolled Back

| artifact | rollback source |
|---|---|
| low-risk released rows | `data/v06_manual_review_released_rows.csv` |
| macro holdout rows | `data/v06_macro_holdout_queue.csv` |
| macro discard released rows | `data/v06_macro_discard_released_rows.csv` |
| holdout sample | `data/v06_holdout_audit_sample.csv` |
| synthetic edge cases | `data/v06_synthetic_edge_cases.csv` |

## Rollback Triggers

Rollback or pause the related rule if any of these occur:

- UTC conversion error is found.
- More than 2 false asset attributions per 100 audited rows.
- Low-risk discard produces more than 1 false negative in a week.
- Event taxonomy disagreement exceeds 5% in audit.
- `manual_review_required_rate` rises above 0.085 after a new batch.
- `secret_leak_count` is greater than 0 in `results/secret_leak_summary.csv`.
- A released row would have been an `approve_publish` item after review.
- A macro/multi-asset row was incorrectly converted into a single-asset alert.

## Rollback Steps

1. Stop applying the suspected release or auto-label rule.
2. Find the released rows in the relevant audit CSV.
3. Restore these fields in `data/v06_manual_label_sheet.csv`:

```text
manual_review_required=true
review_queue=
label_origin=rollback_required
manual_notes=<previous notes> | rollback:<reason>
```

4. Re-run:

```powershell
python scripts/check_secret_leaks.py
python scripts/audit_v06_manual_review_required.py
python scripts/build_v06_holdout_audit_sample.py --size 201
python scripts/check_v06_tg_pilot_gate.py
python scripts/refresh_project_state.py
python scripts/render_project_dashboard.py
```

5. Record the reason in `docs/DECISIONS.md` if the rollback changes policy.

## Current Non-Negotiables

- `auto_publish` remains disabled.
- No auto-send to Telegram.
- No trading advice.
- No order execution.
- TG work, when allowed, is draft-only formatting and routing.

## Preferred Fix Order

1. Fix time/source parsing first.
2. Fix asset/entity attribution second.
3. Fix taxonomy third.
4. Adjust channel routing last.

Routing changes are last because they directly affect what a user would see.
```
## docs/CURSOR_TASK_BACKLOG.md

```text
# Cursor Task Backlog

Cursor handoff is file-based. Generate the current handoff prompt with:

```powershell
python scripts/generate_cursor_prompt.py
```

Current handoff file:

```text
docs/CURSOR_NEXT_PROMPT.md
```

## Pending Tasks

1. Review whether `project_business/payment_adoption` rows such as Revolut crypto card should stay in review or be discarded.
2. Check whether BTC macro/policy rows should be a separate queue from single-asset market-moving events.
3. Inspect `primary_asset_symbol` blank rows in `data/event_candidates_v06_publish_review_queue.csv` and decide whether they should be discarded or treated as market-wide.
4. Review unsupported assets such as HYPE, ONDO, WLD and decide which ones deserve `unsupported_research` review even though they cannot enter Binance backtest.
5. Identify recurring Web3 project aliases still missing from `data/entity_dictionary.csv`.
6. Find rows where long scraped webpage footer text caused false entity/event matches.
7. Flag opinion/analysis articles that should be research-only rather than publish candidates.
8. Decide whether BTC miner equity / AI data-center stories should be in the main crypto event stream.
9. Decide whether crypto enforcement/fraud stories should be `hack_security` or a separate `legal_enforcement` L1 type.
10. Inspect protocol incident rows such as Curvance/Echo/eBTC and decide whether `protocol_incident` should stay under `hack_security` or become its own L1 bucket later.
11. Review all time fields using China time as the human-facing standard: `*_china` for review, `*_utc` for API/math. Flag any row where the title/source implies US local time but the CSV time is timezone-naive.
12. Review `source_timezone_assumption=default_china` rows and decide whether source-specific timezone rules should be added to `data/source_timezone_rules.csv`.
13. Check whether `macro` should have a separate TG stream from asset-specific event intelligence.
14. Review whether `other` event_type rows in the backtest are explainable or should be split into new L1/L2 event types.
15. Read `results/v043_stratified_selection_diagnostics.md` and identify whether scarce event types can be improved without relaxing macro/other caps.
16. Read `results/v043_selection_vs_v06_relevance_audit.md` and identify which old v043 selected rows should not be trusted under v0.6 relevance scoring.
17. Read `results/v06_filtered_mature_sample_preview.md` and evaluate whether it is a safer candidate set for a future v0.6-filtered backtest branch.
18. Read `results/v06_filtered_preview_asset_attribution_audit.md` and propose concrete fixes for high-risk asset attribution rows.
19. Read `results/v06_clean_low_risk_preview.md` and use it only as a sanity-check subset, not as statistical evidence.
20. Read `results/v06_asset_attribution_fix_plan.md` and convert obvious fixes into rule/dictionary changes only when they do not change product direction.
21. Read `results/v06_entity_rule_review_packet.md` and propose concrete dictionary/rule changes for Hyperliquid/HYPE, multi-chain regulatory flow, and protocol exploit primary-asset policy. Do not auto-fix Echo/Monad/eBTC rows before direction approval.
22. Read `docs/CLAUDE_DECISION_REVIEW.md`; do not implement pending Claude recommendations until they are accepted into `docs/DECISIONS.md`.

## Completed From Cursor Review

- Added Curvance, RUNE, Polymarket, Tornado Cash, Base, Kevin Warsh, ZachXBT, and Citi to `data/entity_dictionary.csv`.
- Added `tornado cash` to hack/exploit detection.
- Added common Chinese long/short wording to whale-position detection.
- Confirmed `cand_00419` is now `regulation_macro/bitcoin_reserve_policy`, not `hack_security`.
- Confirmed Bitwise HYPE rows now route to `human_review` + `unsupported_research` without fake Binance symbols.
- Added protocol incident soft-signal handling for abnormal/paused protocol market notices.
- Kept `auto_publish` disabled by downgrading high-score rows to `human_review`.
- Standardized human-facing time fields to China time and added time provenance auditing.

## Current Non-Blocking Focus

- Explain why v043 stratified selection only produced 37/50 rows.
- Treat v043 mature50 backtest as a historical baseline until v0.6-filtered sampling is approved.
- Use `data/event_candidates_v06_filtered_mature_review_auto50_preview.csv` only as a preview; do not overwrite v043 backtest outputs.
- Do not run a clean v0.6-filtered backtest until high-risk asset attribution rows are fixed or excluded.
- The current clean low-risk subset has only 18 rows and is too small for event-type conclusions.
- Use `results/v06_asset_attribution_fix_plan.md` as the current asset attribution repair queue.
- Protocol exploit primary-asset policy is unresolved; do not auto-fix Echo/Monad/eBTC rows before Claude/product direction approval.
- Use `results/v06_entity_rule_review_packet.md` as the current entity-policy review queue.
- Use `docs/CLAUDE_DECISION_REVIEW.md` to track Claude advice; only `doc

...(truncated)
```

## Data Snapshot

```text
- data\event_candidates_v06_publish_review_queue.csv: 69 rows
  - channel_route=macro_policy: 27
  - channel_route=research_only: 19
  - channel_route=alpha_candidate: 18
  - channel_route=unsupported_research: 5
- data\event_candidates_v06_other_review_queue.csv: 210 rows
  - discard_reason=missing_entity,duplicate_non_primary,other_review,low_crypto_relevance: 148
  - discard_reason=duplicate_non_primary,other_review,low_crypto_relevance: 14
  - discard_reason=missing_entity,duplicate_non_primary,opinion_or_analysis,other_review,low_crypto_relevance: 9
  - discard_reason=other_review: 8
  - discard_reason=other_review,low_crypto_relevance: 7
  - discard_reason=missing_entity,duplicate_non_primary,other_review: 6
  - discard_reason=missing_entity,other_review,low_crypto_relevance: 5
  - discard_reason=missing_entity,duplicate_non_primary,ai_only_non_crypto,other_review,low_crypto_relevance: 3
  - discard_reason=duplicate_non_primary,other_review: 3
  - discard_reason=unsupported_asset,other_review: 3
- data\event_candidates_v06_discard_audit_sample.csv: 80 rows
  - discard_reason=duplicate_non_primary: 41
  - discard_reason=duplicate_non_primary,low_crypto_relevance: 11
  - discard_reason=low_crypto_relevance: 6
  - discard_reason=duplicate_non_primary,scraped_footer_noise: 4
  - discard_reason=duplicate_non_primary,ai_only_non_crypto,low_crypto_relevance: 3
  - discard_reason=duplicate_non_primary,opinion_or_analysis: 2
  - discard_reason=ai_only_non_crypto: 2
  - discard_reason=scraped_footer_noise: 2
  - discard_reason=opinion_or_analysis,low_crypto_relevance: 2
  - discard_reason=generic_price_recap: 2
- data\event_candidates_real_500_older_review.csv: 500 rows
  - source_timezone_assumption=source_rule:news:jin10: 204
  - source_timezone_assumption=source_rule:webhook: 196
  - source_timezone_assumption=default_china: 43
  - source_timezone_assumption=source_rule:tg:: 28
  - source_timezone_assumption=source_rule:news:cryptonews: 18
  - source_timezone_assumption=source_rule:news:cointelegraph: 11
- results\v043_time_provenance_summary.csv: 1 rows
- results\v06_manual_label_eval_summary.csv: 1 rows
- results\v043_stratified_selection_diagnostics.csv: 10 rows
  - cap_binding=false: 7
  - cap_binding=true: 3
- results\v043_stratified_selection_blocked_examples.csv: 48 rows
  - candidate_event_type=hack_security: 12
  - candidate_event_type=institutional_flow: 12
  - candidate_event_type=network_upgrade: 9
  - candidate_event_type=staking_governance: 6
  - candidate_event_type=token_unlock: 4
  - candidate_event_type=exchange_listing: 2
  - candidate_event_type=whale_position: 2
  - candidate_event_type=halving: 1
- results\v043_selection_vs_v06_relevance_summary.csv: 1 rows
- results\v043_selection_vs_v06_discard_breakdown.csv: 6 rows
  - primary_discard_reason=duplicate_non_primary: 1
  - primary_discard_reason=low_crypto_relevance: 1
  - primary_discard_reason=generic_price_recap: 1
  - primary_discard_reason=opinion_or_analysis: 1
  - primary_discard_reason=generic_market_commentary: 1
  - primary_discard_reason=scraped_footer_noise: 1
- results\v043_selection_vs_v06_event_type_impact.csv: 8 rows
  - candidate_event_type=macro: 1
  - candidate_event_type=other: 1
  - candidate_event_type=halving: 1
  - candidate_event_type=token_unlock: 1
  - candidate_event_type=hack_security: 1
  - candidate_event_type=institutional_flow: 1
  - candidate_event_type=network_upgrade: 1
  - candidate_event_type=staking_governance: 1
- results\v06_filtered_mature_sample_preview_summary.csv: 15 rows
- results\v06_filtered_preview_asset_attribution_summary.csv: 1 rows
- results\v06_clean_low_risk_preview_summary.csv: 1 rows
- results\backtest_readiness_summary.csv: 1 rows
- results\v06_asset_attribution_fix_plan_summary.csv: 5 rows
  - recommended_action=keep_for_clean_preview: 1
  - recommended_action=route_macro_or_research_holdout: 1
  - recommended_action=exclude_from_clean_backtest: 1
  - recommended_action=needs_entity_rule_review: 1
  - recommended_action=keep_for_manual_review: 1
- results\v06_entity_rule_review_packet_summary.csv: 4 rows
  - entity_review_type=protocol_exploit_primary_asset_policy: 1
  - entity_review_type=generic_entity_mismatch: 1
  - entity_review_type=hyperliquid_primary_asset_supported: 1
  - entity_review_type=multi_chain_regulatory_flow: 1
```

## Your Task

Run one v0.6 intake-quality review pass. Prefer concrete rule or dictionary improvements over open-ended manual labeling:

1. Find rows in `data/event_candidates_v06_publish_review_queue.csv` that still should not be publish candidates (opinion/analysis, generic price recap, footer noise, weak trading relevance).
2. Review rows with blank `primary_asset_symbol`: decide between `market_wide + human_review` vs `discard`.
3. Review `unsupported_research` rows (especially HYPE/ONDO/WLD): not backtestable on Binance but potentially research-worthy.
4. Check Curvance/Echo/eBTC-like `hack_security/protocol_incident` classification quality and whether a dedicated L1 type is needed.
5. Review `source_timezone_assumption=default_china` rows and decide whether to add entries in `data/source_timezone_rules.csv`.
6. Decide whether miner equities, AI data-center stories, enforcement/fraud news, and Polymarket stories belong in the main publish stream.
7. Read `results/v043_stratified_selection_diagnostics.md`; do not relax macro/other caps unless you can justify it as a product decision.
8. Inspect `results/v043_stratified_selection_blocked_examples.csv` for scarce event-type false positives and missing-symbol cases.
9. Read `results/v043_selection_vs_v06_relevance_audit.md`; treat v043 backtest as historical baseline if selected rows are now discarded by v0.6 relevance scoring.
10. Read `results/v043_selection_vs_v06_discard_breakdown.csv` and `results/v043_selection_vs_v06_event_type_impact.csv`; do not cite v043 event-type performance without this caveat.
11. Read `results/v06_filtered_mature_sample_preview.md`; evaluate whether this preview is a safer basis for a future v0.6-filtered backtest branch.
12. Read `results/v06_filtered_preview_asset_attribution_audit.md`; identify asset attribution fixes needed before a clean backtest branch.
13. Read `results/v06_clean_low_risk_preview.md`; treat it as a sanity-check subset only, not a statistical backtest sample.
14. Read `results/backtest_readiness_report.md`; do not cite event-type performance as a product conclusion while readiness is `not_ready`.
15. Read `results/v06_asset_attribution_fix_plan.md`; focus on rule/dictionary changes that reduce false BTC/ETH attribution without forcing unsupported assets into Binance backtests.
16. Read `results/v06_entity_rule_review_packet.md`; focus on protocol exploit primary-asset policy, unsupported HYPE/Hyperliquid attribution, and multi-chain regulatory flow without forcing Binance symbols.

Output requirements:

- Include `candidate_id`
- Explain issue cause
- Propose rule/dictionary/script changes
- If editing files, keep changes minimal and list verification commands
- Do not touch TG automation
- Do not provide trading advice
- Do not overwrite historical results
