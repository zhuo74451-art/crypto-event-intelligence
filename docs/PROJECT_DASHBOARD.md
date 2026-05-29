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
| source_rule:tg: | 28 |
| source_rule:news:cryptonews | 18 |
| source_rule:news:cointelegraph | 11 |

## Next Actions

1. Keep review failure modes and rollback workflow current; they are now part of the TG draft gate.
2. Keep `auto_publish` disabled; TG work can only be draft-only after direction approval.
3. Use synthetic edge cases and holdout audit rows as regression tests for labeling changes.
4. Add Claude questions only when a direction/framework issue is genuinely unclear.
