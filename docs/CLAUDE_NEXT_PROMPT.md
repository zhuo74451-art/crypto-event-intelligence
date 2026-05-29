# Claude Consultation Prompt

You are an external project manager and architecture reviewer for this project.
Give direct, critical, and practical feedback.

Project: Crypto Event Intelligence

Goal:
Convert Web3/crypto news into structured event intelligence, filter low-value items,
audit time/price quality, and produce human-reviewable high-value candidates.
No trading advice and no auto-order execution.

Please focus on:
- Whether the product direction is correct
- Which event types should be in the main workflow
- Which categories should be split into separate channels/rules
- Which rules create systemic misclassification
- What should be solved now vs later
- Any major architecture gaps

## Project State

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
under
...(truncated)
```

## Dashboard

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
| ok | 37 |

## Quality Status

| value | count |
|---|---:|
| pass | 37 |

## Publish Review Routes

| value | count |
|---|---:|
| macro_policy | 27 |
| research_only | 19 |
| alpha_candidate | 18 |
| unsupported_research | 5 |

## Other Review Reasons

| value | count |
|---|---:|
| reject_missing_entity_low_crypto_relevance | 155 |
| reject_social_noise_or_contextless | 22 |
| reject_geopolitics_no_crypto_angle | 10 |
| reject_equity_company_no_crypto_angle | 6 |
| reject_generic_price_recap | 6 |
| review_btc_treasury_company | 3 |
| reject_non_crypto_health_weather_local | 2 |
| reject_opinion_or_kol_thesis | 2 |
| reject_tradfi_marketing_or_ad | 1 |
| review_crypto_entity_missing | 1 |
| reject_industry_meta_or_career_content | 1 |
| review_onchain_transfer | 1 |

## TG Draft Status

| value | count |
|---|---:|
| approved | 9 |

## Source Timezone Assumptions

| value | count |
|---|---:|
| source_rule:news:jin10 | 204 |
| source_rule:webhook | 196 |
| default_china | 43 |
| sour
...(truncated)
```

## Decisions

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

- Do not force uncertain exploit events into BTC or ETH just to make the price backtest easier.
- Use protocol token, chain, stolen asset, and affected ecosystem as review context when available.
- If a single primary asset is not defensible, keep the item in review/research routing instead of publishing as a clean single-asset backtest row.

Reason:

Exploit events can be high-value intelligence even when the primary trading asset is ambiguous. The taxonomy should improve from review feedback rather than blocking all such items.

## D012: Claude Is A Scarce Review Tier, Not The First Filter

Decision:

Claude-level models must not review every raw news item or every future on-chain event.

Implementation:

- Run deterministic local rules before any model call.
- Use local dedup, source quality, length/truncation checks, entity extraction, and obvious discard rules first.
- Use cheaper/smaller review tiers for simple classification and confidence scoring when available.
- Use Claude for borderline cases, complex editorial judgment, exploit/multi-asset ambiguity,
...(truncated)
```

## Current Attribution Review Packet

```text
# v0.6 Entity Rule Review Packet

This packet isolates rows where entity detection or primary-asset selection is ambiguous.
It is non-destructive and does not edit candidate files.

## Summary

| review_type | count |
|---|---:|
| protocol_exploit_primary_asset_policy | 5 |
| generic_entity_mismatch | 1 |
| hyperliquid_primary_asset_supported | 1 |
| multi_chain_regulatory_flow | 1 |

## Rows

| candidate_id | review_type | current_asset | suggested_asset | suggested_route | note | title |
|---|---|---|---|---|---|---|
| cand_00117 | protocol_exploit_primary_asset_policy | ETH | ETH | alpha_candidate | Exploit rows mix protocol, chain, minted asset, and returned asset; define whether primary asset is affected token, stol | Exploit Alert 🚨  According to @dcfgod, @EchoProtocol_ on @monad has been exploited.  The attacker reportedly m |
| cand_00047 | protocol_exploit_primary_asset_policy | ETH | ETH | alpha_candidate | Exploit rows mix protocol, chain, minted asset, and returned asset; define whether primary asset is affected token, stol | Lookonchain：过去4天内发生3起重大黑客攻击事件 |
| cand_00011 | protocol_exploit_primary_asset_policy | ETH | ETH | alpha_candidate | Exploit rows mix protocol, chain, minted asset, and returned asset; define whether primary asset is affected token, stol | 黑客攻击Monad Echo协议，损失约7600万美元 |
| cand_00124 | protocol_exploit_primary_asset_policy | BTC | BTC | alpha_candidate | Exploit rows mix protocol, chain, minted asset, and returned asset; define whether primary asset is affected token, stol | #PeckShieldAlert @dcfgod reports that @EchoProtocol_ was hacked on @monad   The hacker minted 1k $eBTC ($76.7M |
| cand_00105 | protocol_exploit_primary_asset_policy | BTC | BTC | alpha_candidate | Exploit rows mix protocol, chain, minted asset, and returned asset; define whether primary asset is affected token, stol | 链上监测：黑客在Monad平台上铸造1000枚EBTC并洗钱 |
| cand_00213 | generic_entity_mismatch | SHIB | SHIB | research_only | Entity mismatch requires dictionary or rule review. | Shiba Inu sees 3b SHIB hit exchanges |
| cand_00029 | hyperliquid_primary_asset_supported | HYPE | HYPE | alpha_candidate | Hyperliquid/HYPE appears to be primary and now has a validated Binance market symbol; review route, not symbol support. | Defillama：Hyperliquid仍维持链上永续合约市场领先地位 |
| cand_00026 | multi_chain_regulatory_flow | TRX |  | macro_policy | Regulatory/sanctions flow across Tron and BNB Chain; avoid single-asset attribution. | 据 Reuters 调查报道，数据分析显示，自 2023 年以来，受制裁影响的伊朗最大加密交易所 Nobitex 已通过 Tron 和 BNB Chain 网络处理了至少 23 亿美元。报道指出，这两个区块链的创始人孙宇 |

## Recommended Next Step

- Do not apply these as automatic fixes yet.
- First decide primary-asset policy for protocol exploits and multi-chain regulatory events.
- Add dictionary/rule changes only when the same pattern repeats.
```

## Current Asset Attribution Fix Plan

```text
# v0.6 Asset Attribution Fix Plan

This is a non-destructive plan. It does not edit candidates or run backtests.

## Summary

| action | count |
|---|---:|
| keep_for_clean_preview | 22 |
| route_macro_or_research_holdout | 10 |
| exclude_from_clean_backtest | 9 |
| needs_entity_rule_review | 8 |
| keep_for_manual_review | 1 |

## High/Medium Risk Actions

| candidate_id | risk | action | asset | route | reason | title |
|---|---|---|---|---|---|---|
| cand_00493 | high | exclude_from_clean_backtest |  | research_only | non-token/equity/infrastructure reference: MSTR | JUST IN: Strategy $MSTR has generated an 84,987 #Bitcoin gain ($6.6 billion) so far this year, which |
| cand_00178 | high | exclude_from_clean_backtest |  | research_only | BTC default without explicit BTC reference | 美国司法部：俄亥俄州居民因加密庞氏骗局被判9年监禁 |
| cand_00253 | high | exclude_from_clean_backtest |  | research_only | non-token/equity/infrastructure reference: HIVE | HIVE soars over 35% on plans for $2.55b Toronto AI 'super factory' |
| cand_00025 | medium | route_macro_or_research_holdout | BTC | research_only | market-wide row should not be alpha_candidate without explicit primary asset | 燕子回来了！💪  「先定 10 个大目标」老哥晒图展示其 $BTC 空单已浮盈 1222.5 万美元，但具体仓位和开仓点位并未露出  05.06 时他止损 BTC 空单最大亏损约 286.7 万美元， |
| cand_00117 | medium | needs_entity_rule_review | ETH | alpha_candidate | protocol exploit proxy assets require primary-asset policy review | Exploit Alert 🚨  According to @dcfgod, @EchoProtocol_ on @monad has been exploited.  The attacker re |
| cand_00047 | medium | needs_entity_rule_review | ETH | alpha_candidate | protocol exploit proxy assets require primary-asset policy review | Lookonchain：过去4天内发生3起重大黑客攻击事件 |
| cand_00011 | medium | needs_entity_rule_review | ETH | alpha_candidate | protocol exploit proxy assets require primary-asset policy review | 黑客攻击Monad Echo协议，损失约7600万美元 |
| cand_00324 | high | exclude_from_clean_backtest |  | research_only | non-token/equity/infrastructure reference: HIVE | Leopold Aschenbrenner bets $13.6b on miners |
| cand_00124 | medium | needs_entity_rule_review | BTC | alpha_candidate | protocol exploit proxy assets require primary-asset policy review | #PeckShieldAlert @dcfgod reports that @EchoProtocol_ was hacked on @monad   The hacker minted 1k $eB |
| cand_00105 | medium | needs_entity_rule_review | BTC | alpha_candidate | protocol exploit proxy assets require primary-asset policy review | 链上监测：黑客在Monad平台上铸造1000枚EBTC并洗钱 |
| cand_00041 | high | route_macro_or_research_holdout | ETH | research_only | market-wide row should not be alpha_candidate without explicit primary asset | 近三天囤积的 ETH 数量增长至 6627.79 枚，价值 1427.6 万美元😆  「曾在 2016 年以均价 $3.45 建仓 11004 枚 $ETH 并获利 3038 万美金的聪明钱」10 小 |
| cand_00098 | medium | route_macro_or_research_holdout | WLD | research_only | market-wide row should not be alpha_candidate without explicit primary asset | WorldCoin团队将1318枚WLD存入Coinbase |
| cand_00079 | medium | route_macro_or_research_holdout | ONDO | research_only | market-wide row should not be alpha_candidate without explicit primary asset | Ondo项目方多签钱包过去2个月向Coinbase等交易所累计转移超3.28亿枚ONDO |
| cand_00023 | medium | keep_for_manual_review | BTC | macro_policy | medium risk; review before clean backtest | 比特币ETF总净流出达6.49亿美元，创2026年第三大流出 |
| cand_00213 | medium | needs_entity_rule_review | SHIB | research_only | multiple assets or entity mismatch requires dictionary/rule review | Shiba Inu sees 3b SHIB hit exchanges |
| cand_00029 | medium | needs_entity_rule_review | HYPE | alpha_candidate | multiple assets or entity mismatch requires dictionary/rule review | Defillama：Hyperliquid仍维持链上永续合约市场领先地位 |
| cand_00183 | high | exclude_from_clean_backtest |  | research_only | BTC default without explicit BTC reference | 明尼苏达州银行可提供比特币保管服务 |
| cand_00329 | medium | route_macro_or_research_holdout | SOL | research_only | market-wide row should not be alpha_candidate without explicit primary asset | Messari报告：2026年Q1 Solana链上应用总收入达3.422亿美元 |
| cand_00357 | medium | route_macro_or_research_holdout | BTC | research_only | market-wide row should not be alpha_candidate without explicit primary asset | ZachXBT offers $10,000 bounty for evidence against Hong Kong market maker HSBG |
| cand_00142 | medium | route_macro_or_research_holdout | BTC | research_only | market-wide row should not be alpha_candidate without explicit primary asset | 加密市场24小时清算金额达8.55亿美元 |
| cand_00095 | high | exclude_from_clean_backtest |  | research_only | unresolved high risk attribution | 美SEC或最快本周推出代币化股票监管框架，华尔街加速布局链上证券 |
| cand_00232 | high | exclude_from_clean_backtest |  | research_only | BTC default without explicit BTC reference | 亚洲主导稳定币支付，近三分之二交易量来自亚洲 |
| cand_00230 | medium | route_macro_or_research_holdout | HYPE | research_only | market-wide row should not be alpha_candidate without explicit primary asset | 【知名交易员Loracle「 HYPE 空仓 TOP 1」】HYPE 空单 摊平 啦! |
| cand_00009 | medium | route_macro_or_research_holdout | HYPE | research_only | market-wide row should not be alpha_candidate without explicit primary asset | 交易员Loracle加仓HYPE空单20万枚，总规模升至6810万美元 |
| cand_00026 | medium | needs_entity_rule_review | TRX | macro_policy | multiple assets or entity mismatch requires dictionary/rule review | 据 Reuters 调查报道，数据分析显示，自 2023 年以来，受制裁影响的伊朗最大加密交易所 Nobitex 已通过 Tron 和 BNB Chain 网络处理了至少 23 亿美元。报道指出，这两 |
| cand_00479 | high | exclude_from_clean_backtest |  | research_only | BTC default without explicit BTC reference | Tempo集成Morpho借贷协议，扩展稳定币支付功能 |
| cand_00137 | high | exclude_from_clean_backtest |  | research_only | unresolved high risk attribution | Ostium与纳斯达克达成合作，推出股票永续合约 |
| cand_00081 | high | route_macro_or_research_holdout | BTC | research_only | market-wide row should not be alpha_candidate without explicit primary asset | CryptoSlate 文章表示，RWA 代币化市场链上规模已接近 300 亿美元，但真正进入 DeFi 协议的活跃 TVL 仅约 24.7 亿美元，不到 10%。文章援引 DefiLlama 数据称 |

## Use

- Apply this plan only after reviewing the recommended action categories.
- Do not force unsupported assets into BTC/ETH just to mak
...(truncated)
```

## Questions



Please output:
1. The 3 assumptions you disagree with most.
2. The 5 highest-priority actions now.
3. Concrete recommendation per question.
4. Which questions are not worth solving now.
5. Which data/manual-label assets are most critical.
