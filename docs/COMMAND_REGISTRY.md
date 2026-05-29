# Command Registry

Last updated: 2026-05-29 14:29:06 UTC+8

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
| `historical_source_usefulness_v081` | source_quality | `python scripts/build_historical_source_usefulness_from_backtest.py --backfill results/v08_historical_replay_conservative_120_price_backfill.csv --quality results/v08_historical_replay_conservative_120_quality_report.csv --by-event-type results/v081_historical_source_usefulness_by_event_type.csv --by-source results/v081_historical_source_usefulness_by_source.csv --summary results/v081_historical_source_usefulness_summary.csv --output results/v081_historical_source_usefulness_report.md` | no | no | yes |
| `source_readiness_v081` | source_quality | `python scripts/build_v08_source_readiness_report.py --candidates data/event_candidates_real_500_older_v081_review_suggested.csv --historical-event-type results/v081_historical_source_usefulness_by_event_type.csv --historical-source results/v081_historical_source_usefulness_by_source.csv --output results/v081_source_readiness_report.md --summary results/v081_source_readiness_summary.csv` | no | no | yes |
| `source_quality_reports_v081` | source_quality | `python scripts/run_v081_source_quality_reports.py` | no | no | yes |
| `source_registry_report_v11` | source_quality | `python scripts/build_source_registry_report.py --registry data/source_registry.csv --summary results/source_registry_report.csv --output results/source_registry_report.md` | no | no | yes |
| `source_effectiveness_report_v11` | source_quality | `python scripts/build_source_effectiveness_report.py --registry data/source_registry.csv --output results/source_effectiveness_report.csv --markdown-output results/source_effectiveness_report.md --summary results/source_effectiveness_summary.csv` | no | no | yes |
| `event_type_performance_matrix_v11` | source_quality | `python scripts/build_event_type_performance_matrix.py --outcomes data/tg_alert_outcomes.csv --historical-backfill results/v08_historical_replay_broad_200_price_backfill.csv --historical-quality results/v08_historical_replay_broad_200_quality_report.csv --output results/event_type_performance_matrix.csv --summary results/event_type_performance_matrix_summary.csv --markdown-output results/event_type_performance_matrix.md` | no | no | yes |
| `historical_signal_replay_non_benchmark_alt_50` | backtest | `python scripts/run_v08_historical_signal_replay.py --limit 50 --mode non_benchmark_alt` | yes | no | yes |
| `event_type_performance_matrix_non_benchmark_alt_v11` | source_quality | `python scripts/build_event_type_performance_matrix.py --outcomes data/tg_alert_outcomes.csv --historical-backfill results/v08_historical_replay_non_benchmark_alt_200_price_backfill.csv --historical-quality results/v08_historical_replay_non_benchmark_alt_200_quality_report.csv --output results/event_type_performance_matrix_non_benchmark_alt.csv --summary results/event_type_performance_matrix_non_benchmark_alt_summary.csv --markdown-output results/event_type_performance_matrix_non_benchmark_alt.md` | no | no | yes |
| `signal_policy_v12_strict` | source_quality | `python scripts/validate_whale_position_contamination.py && python scripts/validate_hack_classification.py && python scripts/apply_boost_criteria_v12.py` | no | no | yes |
| `v13_historical_quality_audit` | source_quality | `python scripts/validate_price_in_effect.py && python scripts/grade_other_quality.py && python scripts/analyze_hype_contamination_detail.py && python scripts/analyze_whale_position_asset_contamination.py && python scripts/build_source_identity_layers.py && python scripts/build_regime_layer_report.py && python scripts/validate_hack_classification.py && python scripts/build_active_exploit_urgent_candidates.py && python scripts/apply_boost_criteria_v12.py` | yes | no | yes |
| `v13_extended_history_replay_500` | backtest | `python scripts/run_v08_historical_signal_replay.py --input data/event_candidates_real_5000_older_7_365d_mature_tightened.csv --limit 500 --mode non_benchmark_alt` | yes | no | yes |
| `v13_post_hype_source_regime_refresh` | source_quality | `python scripts/archive_hype_and_recompute_stats.py --backfill results/v08_historical_replay_non_benchmark_alt_500_price_backfill.csv --output data/backtest_v13_extended_alt_history_clean.csv --summary results/v13_extended_post_hype_removal_summary.csv --group-stats results/v13_extended_post_hype_removal_group_stats.csv --markdown-output results/v13_extended_post_hype_removal_report.md && python scripts/analyze_whale_position_asset_contamination.py --backfill results/v08_historical_replay_non_benchmark_alt_500_price_backfill.csv --output results/v13_extended_whale_asset_contamination_report.csv --summary results/v13_extended_whale_asset_contamination_summary.csv --markdown-output results/v13_extended_whale_asset_contamination_report.md && python scripts/build_source_identity_layers.py --candidates data/event_candidates_real_5000_older_7_365d_mature_tightened.csv --backfill results/v08_historical_replay_non_benchmark_alt_500_price_backfill.csv --output data/source_identity_layers_v13_extended.csv --summary results/v13_extended_source_identity_summary.csv --markdown-output results/v13_extended_source_identity_layers.md && python scripts/score_and_throttle_sources.py --source-layers data/source_identity_layers_v13_extended.csv --clean-backfill data/backtest_v13_extended_alt_history_clean.csv --output data/source_scores_v13_extended.csv --rules results/v13_extended_source_throttle_rules.csv --markdown-output results/v13_extended_source_throttle_report.md` | no | no | yes |
| `v14_time_and_source_audit` | source_quality | `python scripts/diagnose_remote_time_fields.py && python scripts/split_webhook_subsources.py && python scripts/analyze_needs_taxonomy_review.py` | yes | conditional | yes |
| `v14_digest_quality_filters` | publishing_quality | `python scripts/split_flow_event_subtypes.py; python scripts/filter_etf_fund_flow.py; python scripts/verify_exploit_amounts.py; python scripts/build_v14_short_price_in.py --limit 281; python scripts/classify_v14_upgrade_events.py; python scripts/build_v14_prefilter.py; python scripts/build_v14_composer_scores.py; python scripts/apply_v14_publish_policy.py; python scripts/define_publishable_event_criteria.py; python scripts/apply_v14_publish_policy.py; python scripts/build_v14_digest_preview.py` | no | no | yes |
| `v14_security_alert_ingest` | source_ingest | `python scripts/ingest_security_alerts.py --source etherscan-labels --label phish-hack --limit 200` | yes | yes | yes |
| `v14_etf_daily_digest` | daily_digest | `python scripts/build_etf_daily_digest.py` | yes | no | yes |
| `v14_first_hand_publish_candidates` | publishing_quality | `python scripts/build_first_hand_publish_candidates.py` | no | no | yes |
| `v14_publishable_criteria_validation` | publishing_quality | `python scripts/validate_publishable_criteria.py` | no | no | yes |
| `v14_adversarial_golden_validation` | publishing_quality | `python scripts/generate_adversarial_golden_samples.py` | no | no | yes |
| `v14_etf_daily_digest_with_baseline` | daily_digest | `python scripts/build_etf_daily_digest_with_baseline.py` | no | no | yes |
| `v14_hyperliquid_snapshot_card_v2` | daily_digest | `python scripts/aggregate_hyperliquid_snapshot_with_baseline.py` | yes | no | yes |
| `v14_project_os_warning_review` | project_os | `python scripts/review_project_os_warnings.py` | no | no | yes |
| `v14_false_positive_monitor` | publishing_quality | `python scripts/build_false_positive_monitor.py` | no | no | yes |
| `v14_false_negative_case_review` | publishing_quality | `python scripts/review_false_negative_cases.py` | no | no | yes |
| `v14_hyperliquid_baseline_readiness` | daily_digest | `python scripts/validate_hyperliquid_baseline_readiness.py` | no | no | yes |
| `v14_weekly_fp_analysis` | publishing_quality | `python scripts/build_weekly_fp_analysis.py` | no | no | yes |
| `v14_market_state_snapshot` | daily_digest | `python scripts/build_market_state_snapshot.py` | yes | no | yes |
| `v14_focus_assets` | daily_digest | `python scripts/market/select_focus_assets.py` | no | no | yes |
| `v14_price_oi_quadrant` | daily_digest | `python scripts/market/classify_price_oi_quadrant.py` | no | no | yes |
| `v14_etf_plain_summary` | daily_digest | `python scripts/reporting/generate_etf_summary.py` | no | no | yes |
| `v14_eth_etf_fetch` | daily_digest | `python scripts/build_etf_daily_digest.py --asset ETH --url https://farside.co.uk/eth/ --output data/eth_etf_flows_farside.csv --digest-output results/v14_eth_etf_daily_digest.md --summary results/v14_eth_etf_daily_digest_summary.csv` | yes | no | yes |
| `v14_market_state_first_screen` | daily_digest | `python scripts/reporting/generate_market_state_summary.py` | no | no | yes |
| `v14_market_alert_headline` | daily_digest | `python scripts/reporting/generate_alert_headline.py` | no | no | yes |
| `v14_derivatives_history_percentiles` | daily_digest | `python scripts/market/build_derivatives_history_percentiles.py` | yes | no | yes |
| `v15_percentile_alerts` | daily_digest | `python scripts/market/generate_percentile_alerts.py` | no | no | yes |
| `v15_hyperliquid_market_meta` | first_hand_intel | `python scripts/hyperliquid/fetch_market_meta.py && python scripts/hyperliquid/generate_market_meta_card.py` | yes | no | yes |
| `v15_hyperliquid_liquidation_wall` | first_hand_intel | `python scripts/hyperliquid/generate_liquidation_wall.py` | no | no | yes |
| `v14_prioritized_events` | daily_digest | `python scripts/events/prioritize_events.py` | no | no | yes |
| `v14_e2e_publish_preview` | publishing_quality | `python scripts/test_end_to_end_publish.py` | no | no | yes |
| `v14_hyperliquid_snapshot_card` | daily_digest | `python scripts/aggregate_hyperliquid_snapshot.py` | no | no | yes |
| `signal_decay_curve_v11` | source_quality | `python scripts/build_signal_decay_curve.py --outcomes data/tg_alert_outcomes.csv --historical-backfill results/v08_historical_replay_broad_200_price_backfill.csv --historical-quality results/v08_historical_replay_broad_200_quality_report.csv --output results/signal_decay_curve.csv --summary results/signal_decay_curve_summary.csv --markdown-output results/signal_decay_curve.md` | no | no | yes |
| `false_positive_analysis_v11` | source_quality | `python scripts/build_false_positive_analysis.py --outcomes data/tg_alert_outcomes.csv --decision-log data/tg_radar_decision_log.csv --output results/false_positive_analysis.csv --summary results/false_positive_analysis_summary.csv --markdown-output results/false_positive_analysis.md` | no | no | yes |
| `signal_policy_v11` | source_quality | `python scripts/build_v11_signal_policy.py --event-matrix results/event_type_performance_matrix.csv --non-benchmark-event-matrix results/event_type_performance_matrix_non_benchmark_alt.csv --source-effectiveness results/source_effectiveness_report.csv --false-positive results/false_positive_analysis.csv --output data/tg_signal_policy_v11.csv --summary results/v11_signal_policy_summary.csv --report results/v11_signal_policy_report.md` | no | no | yes |
| `source_adapter_validation_v11` | source_quality | `python scripts/validate_source_adapter_outputs.py --input data/watcher_events_raw.csv --registry data/source_registry.csv --output results/source_adapter_validation_report.csv --summary results/source_adapter_validation_summary.csv --markdown-output results/source_adapter_validation_report.md` | no | no | yes |
| `shadow_source_evaluation_v11` | source_quality | `python scripts/run_shadow_source_evaluation.py --registry data/source_registry.csv --watcher-events data/watcher_events_raw.csv --shadow-output data/shadow_events_raw.csv --summary results/shadow_source_evaluation_summary.csv --report results/shadow_source_evaluation_report.md` | no | no | yes |
| `tg_evidence_snippets_v11` | publishing_quality | `python scripts/render_tg_evidence_snippet.py --alerts data/tg_alert_ledger.csv --event-matrix results/event_type_performance_matrix.csv --source-effectiveness results/source_effectiveness_report.csv --output data/tg_evidence_snippets.csv --markdown-output results/tg_evidence_snippets.md` | no | no | yes |
| `llm_usage_report_v11` | cost_control | `python scripts/build_llm_usage_report.py --input data/llm_usage_ledger.csv --output results/llm_usage_report.csv --summary results/llm_usage_summary.csv --markdown-output results/llm_usage_report.md` | no | no | yes |
| `readiness_report_v11` | source_quality | `python scripts/build_v11_readiness_report.py --output results/v11_readiness_report.md --summary results/v11_readiness_summary.csv` | no | no | yes |
| `import_token_unlock_calendar_v081` | source_quality | `python scripts/import_raw_token_unlocks_to_calendar.py --input data/raw_token_unlocks_template.csv --output data/token_unlock_calendar_imported.csv` | no | no | yes |
| `v06_intake_quality` | event_intake | `python scripts/run_v06_event_intake_quality.py --input data/event_candidates_real_500_older_review_suggested.csv` | no | no | yes |
| `time_audit` | quality | `python scripts/audit_event_time_provenance.py --candidates data/event_candidates_real_500_older_review.csv --backfill results/v043_older_mature50_event_price_backfill.csv --output results/v043_time_provenance_report.csv --summary results/v043_time_provenance_summary.csv` | no | no | yes |
| `v043_relevance_audit` | quality | `python scripts/audit_v043_selection_against_v06.py` | no | no | yes |
| `price_source_validation` | quality | `python scripts/validate_price_sources.py --sample-size 30 --output results/price_source_validation_report.csv --recent-output results/recent_price_point_sample.csv` | yes | no | yes |
| `symbol_map_validation` | quality | `python scripts/validate_symbol_map.py` | yes | no | yes |
| `v05_research_validation` | backtest | `python scripts/run_v05_research_validation.py` | no | no | yes |
| `v06_clean_low_risk_preview_backtest` | backtest | `python scripts/run_v06_clean_low_risk_preview_backtest.py --limit 50` | yes | no | yes |
| `tg_draft_private_pilot` | publishing_draft | `python scripts/generate_tg_drafts.py --input data/event_candidates_v06_clean_low_risk_preview.csv --output data/tg_drafts_v06_private_pilot.csv --markdown-output results/tg_drafts_v06_private_pilot.md --limit 20` | no | no | yes |
| `tg_draft_prefilter` | publishing_draft | `python scripts/prefilter_tg_draft_candidates.py --input data/event_candidates_v06_clean_low_risk_preview.csv --output data/event_candidates_v06_tg_prefilter_pass.csv --rejects-output data/event_candidates_v06_tg_prefilter_rejects.csv --summary results/tg_draft_prefilter_summary.csv` | no | no | yes |
| `tg_draft_feedback_summary` | publishing_draft | `python scripts/summarize_tg_draft_feedback.py --input data/tg_drafts_v06_private_pilot.csv --summary results/tg_draft_feedback_summary.csv --markdown-output results/tg_draft_feedback_summary.md` | no | no | yes |
| `tg_draft_ai_review` | publishing_draft | `python scripts/ai_review_tg_drafts.py --input data/tg_drafts_v06_private_pilot.csv --output data/tg_drafts_v06_private_pilot_ai_reviewed.csv --summary results/tg_draft_ai_review_summary.csv --limit 20 --apply` | yes | yes | yes |
| `tg_approved_pool` | publishing_draft | `python scripts/build_approved_tg_draft_pool.py --input data/tg_drafts_v06_private_pilot.csv --output data/tg_drafts_v06_approved_pool.csv --summary results/tg_draft_approved_pool_summary.csv --markdown-output results/tg_draft_approved_pool.md` | no | no | yes |
| `tg_draft_review_packet` | publishing_draft | `python scripts/prepare_tg_draft_review_packet.py --input data/tg_drafts_v06_private_pilot.csv --output data/tg_draft_review_packet.csv --markdown-output results/tg_draft_review_packet.md --limit 20 --only-pending` | no | no | yes |
| `tg_draft_apply_review_packet` | publishing_draft | `python scripts/apply_tg_draft_review_packet.py --drafts data/tg_drafts_v06_private_pilot.csv --packet data/tg_draft_review_packet.csv --output data/tg_drafts_v06_private_pilot.csv` | no | no | yes |
| `tg_draft_validation` | publishing_draft | `python scripts/validate_tg_drafts.py --input data/tg_drafts_v06_private_pilot.csv --output results/tg_draft_validation_report.csv --summary results/tg_draft_validation_summary.csv --markdown-output results/tg_draft_validation_report.md` | no | no | yes |
| `other_review_reason_split` | event_intake | `python scripts/classify_other_review_reasons.py --input data/event_candidates_v06_other_review_queue.csv --output data/event_candidates_v06_other_review_classified.csv --summary results/v06_other_review_reason_summary.csv --markdown-output results/v06_other_review_reason_summary.md` | no | no | yes |
| `backtest_readiness` | backtest | `python scripts/build_backtest_readiness_report.py` | no | no | yes |

## Details

### quality_gate

Purpose: Run the full v0.6 gate, refresh Project State, Dashboard, Claude indexes, and Project OS validation.

```powershell
python scripts/run_v06_quality_gate.py
```

Outputs: `docs/PROJECT_DASHBOARD.md; results/project_os_validation_report.md`

Notes: Preferred full refresh command.

### daily_private_pilot

Purpose: Run the local private-pilot MVP workflow: prefilter candidates, generate drafts, validate draft safety, summarize feedback, classify other_review reasons, build approved pool, and refresh the dashboard.

```powershell
python scripts/run_daily_private_pilot.py
```

Outputs: `data/event_candidates_v06_tg_prefilter_pass.csv; data/tg_drafts_v06_private_pilot.csv; data/tg_drafts_v06_approved_pool.csv; results/daily_private_pilot_report.md`

Notes: Does not call Telegram, does not auto-send, and does not use market-data network calls.

### daily_private_pilot_ai_review

Purpose: Run the local private-pilot workflow and fill draft review fields with Claude/OpenRouter suggestions.

```powershell
python scripts/run_daily_private_pilot.py --ai-review
```

Outputs: `data/tg_drafts_v06_private_pilot.csv; data/tg_drafts_v06_private_pilot_ai_reviewed.csv; results/tg_draft_ai_review_summary.csv; results/daily_private_pilot_report.md`

Notes: Requires OPENROUTER_API_KEY only in the current terminal environment. Does not call Telegram or auto-send.

### daily_private_pilot_report

Purpose: Build the one-page daily private-pilot report from draft, validation, feedback, other_review, dashboard, and Claude backlog state.

```powershell
python scripts/build_daily_private_pilot_report.py
```

Outputs: `results/daily_private_pilot_summary.csv; results/daily_private_pilot_report.md`

Notes: Read-only report generator.

### tg_draft_rule_improvement

Purpose: Convert AI-rejected/noisy TG drafts into concrete local rule-improvement candidates.

```powershell
python scripts/build_tg_draft_rule_improvement_report.py
```

Outputs: `results/tg_draft_rule_improvement_report.csv; results/tg_draft_rule_improvement_report.md`

Notes: Local analysis only; does not change classification rules by itself.

### project_os_validation

Purpose: Validate Project OS freshness, gates, boundary checks, secret scan state, and Claude decision consistency.

```powershell
python scripts/validate_project_os.py
```

Outputs: `results/project_os_validation_report.md; results/project_os_validation_summary.csv`

Notes: Use after generating prerequisite reports, or run quality_gate instead.

### secret_scan

Purpose: Scan local project text files for likely leaked API keys, tokens, passwords, and private keys.

```powershell
python scripts/check_secret_leaks.py
```

Outputs: `results/secret_leak_report.md; results/secret_leak_summary.csv`

Notes: Report uses redacted matches only.

### local_environment

Purpose: Check Python version, required packages, required directories, and optional Claude API key environment state.

```powershell
python scripts/check_local_environment.py
```

Outputs: `results/local_environment_report.md; results/local_environment_summary.csv`

Notes: OPENROUTER_API_KEY is informational; missing is acceptable unless querying Claude.

### cursor_prompt

Purpose: Generate file-based Cursor handoff prompt from local Project OS state.

```powershell
python scripts/generate_cursor_prompt.py
```

Outputs: `docs/CURSOR_NEXT_PROMPT.md`

Notes: Does not automate Cursor UI.

### claude_prompt

Purpose: Generate the current Claude consultation prompt from backlog, state, decisions, and review packets.

```powershell
python scripts/generate_claude_question_prompt.py --force
```

Outputs: `docs/CLAUDE_NEXT_PROMPT.md`

Notes: Does not send the prompt.

### claude_query

Purpose: Send docs/CLAUDE_NEXT_PROMPT.md to Claude via OpenRouter and refresh Project OS after response.

```powershell
python scripts/query_claude_next.py
```

Outputs: `results/claude_next_response_*.md; docs/CLAUDE_RESPONSE_INDEX.md; docs/CLAUDE_DECISION_REVIEW.md`

Notes: Requires OPENROUTER_API_KEY in the current terminal environment. Do not write the key to files.

### claude_index

Purpose: Index local Claude response files stored in results/.

```powershell
python scripts/index_claude_responses.py
```

Outputs: `docs/CLAUDE_RESPONSE_INDEX.md; results/claude_response_index.csv`

Notes: Does not mark recommendations as accepted.

### claude_decision_review

Purpose: Extract reviewable decision/action items from Claude responses without auto-applying them.

```powershell
python scripts/build_claude_decision_review_queue.py
```

Outputs: `docs/CLAUDE_DECISION_REVIEW.md; data/claude_decision_review_queue.csv`

Notes: Accepted direction still requires docs/DECISIONS.md entry.

### project_review_actions

Purpose: Turn dashboard review metrics into explicit action items with owner, next step, and evidence.

```powershell
python scripts/build_project_review_actions.py
```

Outputs: `docs/PROJECT_REVIEW_ACTIONS.md; data/project_review_action_queue.csv`

Notes: Does not approve direction-level changes.

### artifact_manifest

Purpose: Build a required artifact manifest so core local files are visible and protected from accidental deletion.

```powershell
python scripts/build_artifact_manifest.py
```

Outputs: `docs/ARTIFACT_MANIFEST.md; results/artifact_manifest.csv; results/artifact_manifest_summary.csv`

Notes: Checks existence and freshness policy for core project outputs.

### v07_first_hand_watchers

Purpose: Run the local v0.7 first-hand watcher MVP: watched address alerts, stablecoin mint/burn alerts, Hyperliquid large-position alerts, event normalization, and TG draft preview.

```powershell
python scripts/run_v07_first_hand_watchers.py --hours 24 --limit-alerts 100
```

Outputs: `data/watcher_alerts_raw.csv; data/watcher_alerts_hyperliquid_positions.csv; data/watcher_events_raw.csv; data/tg_drafts_v07_watcher_private_pilot.csv; results/v07_watcher_daily_report.md`

Notes: Uses ETHERSCAN_API_KEY from the current terminal if set for Ethereum sources. Hyperliquid uses its public info endpoint. Does not call Telegram or auto-send.

### v07_watchlist_validation

Purpose: Validate v0.7 watcher address, stablecoin, and Hyperliquid watchlists before live API/TG testing.

```powershell
python scripts/validate_v07_watchlists.py
```

Outputs: `results/v07_watchlist_validation_report.csv; results/v07_watchlist_validation_summary.csv; results/v07_watchlist_validation_report.md`

Notes: Checks address format, duplicates, required labels/entities/categories, and positive thresholds.

### v07_first_hand_watchers_backfill

Purpose: Run v0.7 watcher MVP and verify normalized watcher events against the existing Binance price backfill/quality pipeline.

```powershell
python scripts/run_v07_first_hand_watchers.py --hours 24 --limit-alerts 100 --backfill
```

Outputs: `results/v07_watcher_event_price_backfill.csv; results/v07_watcher_event_quality_report.csv; results/tg_drafts_v07_watcher_validation_summary.csv`

Notes: Backfill uses public Binance market data. Live watcher mode requires ETHERSCAN_API_KEY in the current terminal; no Telegram send.

### tg_draft_test_send_dry_run

Purpose: Dry-run one local TG draft test message without calling Telegram.

```powershell
python scripts/send_tg_draft_test.py --input data/tg_drafts_v07_watcher_private_pilot.csv --limit 1
```

Outputs: `results/tg_draft_test_send_summary.csv`

Notes: Prints message preview only. No Telegram API call.

### tg_draft_test_send

Purpose: Manually send one local TG draft test message after TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID are set in the current terminal.

```powershell
python scripts/send_tg_draft_test.py --input data/tg_drafts_v07_watcher_private_pilot.csv --limit 1 --send
```

Outputs: `results/tg_draft_test_send_summary.csv`

Notes: Manual test only. Refuses auto_send_enabled=true rows. Does not store token or chat id.

### v07_tg_live_monitor

Purpose: Continuously run first-hand watchers, validate TG drafts, dedupe by candidate_id, and send new watcher alerts to Telegram.

```powershell
python scripts/run_v07_tg_live_monitor.py --send --interval-seconds 300 --max-send-per-cycle 3 --limit-alerts 100
```

Outputs: `results/v07_tg_live_monitor_summary.csv; data/tg_live_sent_state.csv; results/v07_tg_live_monitor.log`

Notes: Loads ignored local secrets if present. Use scripts/stop_v07_tg_live_monitor.ps1 to stop the background monitor. No trading integration.

### v07_tg_live_monitor_stop

Purpose: Stop the background v0.7 watcher-to-TG live monitor using the recorded pid file.

```powershell
powershell -ExecutionPolicy Bypass -File scripts/stop_v07_tg_live_monitor.ps1
```

Outputs: `results/v07_tg_live_monitor.pid`

Notes: Does not delete sent-state. Existing dedupe history remains intact.

### binance_long_short_snapshot

Purpose: Fetch public Binance USD-M top-trader/global long-short and taker buy-sell ratios for morning digest context.

```powershell
python scripts/watch_binance_long_short_ratios.py --output data/binance_long_short_snapshot.csv --summary results/v08_binance_long_short_summary.csv --period 1h --limit 2
```

Outputs: `data/binance_long_short_snapshot.csv; results/v08_binance_long_short_summary.csv`

Notes: Public market-data only. Context for crowding/structure, not a direction instruction.

### tg_morning_digest

Purpose: Build the China-time morning digest for the previous evening/night window without sending to Telegram.

```powershell
python scripts/build_tg_morning_digest.py --output results/v08_tg_morning_digest.md --summary results/v08_tg_morning_digest_summary.csv
```

Outputs: `results/v08_tg_morning_digest.md; results/v08_tg_morning_digest_summary.csv; data/binance_long_short_snapshot.csv`

Notes: Dry-run/report mode. Server timer uses --send with Telegram env loaded at runtime.

### tg_noon_digest

Purpose: Build the China-time noon digest for the morning window without sending to Telegram.

```powershell
python scripts/build_tg_morning_digest.py --digest-label noon --window-end-hour 12 --window-hours 4 --output results/v08_tg_noon_digest.md --summary results/v08_tg_noon_digest_summary.csv
```

Outputs: `results/v08_tg_noon_digest.md; results/v08_tg_noon_digest_summary.csv; data/binance_long_short_snapshot.csv`

Notes: Dry-run/report mode. Server timer uses --send with Telegram env loaded at runtime.

### tg_evening_digest

Purpose: Build the China-time evening digest for the daytime window without sending to Telegram.

```powershell
python scripts/build_tg_morning_digest.py --digest-label evening --window-end-hour 20 --window-hours 8 --output results/v08_tg_evening_digest.md --summary results/v08_tg_evening_digest_summary.csv
```

Outputs: `results/v08_tg_evening_digest.md; results/v08_tg_evening_digest_summary.csv; data/binance_long_short_snapshot.csv`

Notes: Dry-run/report mode. Server timer uses --send with Telegram env loaded at runtime.

### tg_sent_state_metadata_enrichment

Purpose: Backfill missing event_type/asset/severity metadata in local TG sent-state rows from local TG draft CSV files.

```powershell
python scripts/enrich_tg_sent_state_metadata.py
```

Outputs: `data/tg_live_sent_state.csv; results/v08_tg_sent_state_metadata_enrichment_summary.csv`

Notes: Creates a .bak backup before overwriting sent-state. Does not send Telegram messages.

### tg_source_usefulness_report

Purpose: Summarize live TG source usefulness from sent alerts and 4h/24h follow-up coverage.

```powershell
python scripts/build_tg_source_usefulness_report.py --lookback-days 7
```

Outputs: `results/v08_tg_source_usefulness_report.md; results/v08_tg_source_usefulness_summary.csv; results/v08_tg_source_usefulness_by_source.csv`

Notes: Local quality/operations report only. Uses sent alerts and 4h/24h follow-up data; does not use Telegram replies or reactions. Does not provide trading advice.

### tg_quality_loop

Purpose: Run the full TG quality loop: sent-state metadata enrichment, follow-up report, and source usefulness report.

```powershell
python scripts/run_tg_quality_loop.py --lookback-days 7 --followup-min-age-hours 4
```

Outputs: `results/v08_tg_quality_loop_summary.csv; results/v08_tg_alert_followup_report.md; results/v08_tg_source_usefulness_report.md`

Notes: Uses public Binance market data through follow-up backfill. Does not collect Telegram replies/reactions, send messages, or trade.

### historical_signal_replay_broad_200

Purpose: Replay up to 200 older mature historical candidates through event price backfill to increase signal sample size.

```powershell
python scripts/run_v08_historical_signal_replay.py --limit 200 --mode broad
```

Outputs: `data/events_v08_historical_replay_broad_200.csv; results/v08_historical_replay_broad_200_price_backfill.csv; results/v08_historical_replay_broad_200_findings.md`

Notes: Uses public Binance data and local cache. Research/quality analysis only; not a live publishing rule.

### historical_signal_replay_conservative_120

Purpose: Replay a cleaner high-score subset of older mature historical candidates for comparison against broad replay.

```powershell
python scripts/run_v08_historical_signal_replay.py --limit 120 --mode conservative
```

Outputs: `data/events_v08_historical_replay_conservative_120.csv; results/v08_historical_replay_conservative_120_price_backfill.csv; results/v08_historical_replay_conservative_120_findings.md`

Notes: Still dominated by BTC/macro in the current dataset; interpret abnormal-vs-BTC carefully.

### historical_source_usefulness_v081

Purpose: Summarize event/source usefulness from historical backtest rows after v081 token-unlock cleanup.

```powershell
python scripts/build_historical_source_usefulness_from_backtest.py --backfill results/v08_historical_replay_conservative_120_price_backfill.csv --quality results/v08_historical_replay_conservative_120_quality_report.csv --by-event-type results/v081_historical_source_usefulness_by_event_type.csv --by-source results/v081_historical_source_usefulness_by_source.csv --summary results/v081_historical_source_usefulness_summary.csv --output results/v081_historical_source_usefulness_report.md
```

Outputs: `results/v081_historical_source_usefulness_report.md; results/v081_historical_source_usefulness_by_event_type.csv; results/v081_historical_source_usefulness_by_source.csv`

Notes: Research/source QA only. Does not send Telegram messages or produce trade instructions.

### source_readiness_v081

Purpose: Build readiness checklist for token unlock, CEX listings, CEX netflow baseline, Hyperliquid state history, and source usefulness.

```powershell
python scripts/build_v08_source_readiness_report.py --candidates data/event_candidates_real_500_older_v081_review_suggested.csv --historical-event-type results/v081_historical_source_usefulness_by_event_type.csv --historical-source results/v081_historical_source_usefulness_by_source.csv --output results/v081_source_readiness_report.md --summary results/v081_source_readiness_summary.csv
```

Outputs: `results/v081_source_readiness_report.md; results/v081_source_readiness_summary.csv`

Notes: Uses local historical replay outputs and watcher state files. Source QA only.

### source_quality_reports_v081

Purpose: Run token unlock calendar quality, CEX netflow baseline, Hyperliquid state history, historical usefulness, and source readiness reports.

```powershell
python scripts/run_v081_source_quality_reports.py
```

Outputs: `results/v081_token_unlock_calendar_quality_report.md; results/v081_cex_netflow_baseline_report.md; results/v081_hyperliquid_state_history_report.md; results/v081_source_readiness_report.md`

Notes: Local report refresh only. Does not send Telegram messages, call Notion, or trade.

### source_registry_report_v11

Purpose: Validate source registry coverage against watcher events, alert ledger, and decision logs.

```powershell
python scripts/build_source_registry_report.py --registry data/source_registry.csv --summary results/source_registry_report.csv --output results/source_registry_report.md
```

Outputs: `results/source_registry_report.md; results/source_registry_report.csv`

Notes: Source governance report. Does not send Telegram messages or call external APIs.

### source_effectiveness_report_v11

Purpose: Estimate source-level usefulness from sent alert ledger, outcome rows, and routing decisions.

```powershell
python scripts/build_source_effectiveness_report.py --registry data/source_registry.csv --output results/source_effectiveness_report.csv --markdown-output results/source_effectiveness_report.md --summary results/source_effectiveness_summary.csv
```

Outputs: `results/source_effectiveness_report.md; results/source_effectiveness_report.csv; results/source_effectiveness_summary.csv`

Notes: Insufficient samples are reported explicitly. Research/source QA only.

### event_type_performance_matrix_v11

Purpose: Build event-type/source-subtype performance matrix across live and historical outcomes.

```powershell
python scripts/build_event_type_performance_matrix.py --outcomes data/tg_alert_outcomes.csv --historical-backfill results/v08_historical_replay_broad_200_price_backfill.csv --historical-quality results/v08_historical_replay_broad_200_quality_report.csv --output results/event_type_performance_matrix.csv --summary results/event_type_performance_matrix_summary.csv --markdown-output results/event_type_performance_matrix.md
```

Outputs: `results/event_type_performance_matrix.md; results/event_type_performance_matrix.csv; results/event_type_performance_matrix_summary.csv`

Notes: Separates insufficient samples and weak/context-only buckets. No trade instructions.

### historical_signal_replay_non_benchmark_alt_50

Purpose: Replay mature historical non-BTC/ETH, non-macro altcoin candidates to reduce benchmark/macro pollution.

```powershell
python scripts/run_v08_historical_signal_replay.py --limit 50 --mode non_benchmark_alt
```

Outputs: `data/events_v08_historical_replay_non_benchmark_alt_50.csv; results/v08_historical_replay_non_benchmark_alt_50_price_backfill.csv; results/v08_historical_replay_non_benchmark_alt_50_findings.md`

Notes: Uses public Binance data and local cache. Research/source QA only; not a publishing or trade rule.

### event_type_performance_matrix_non_benchmark_alt_v11

Purpose: Build event performance matrix from the non-benchmark altcoin historical replay sample.

```powershell
python scripts/build_event_type_performance_matrix.py --outcomes data/tg_alert_outcomes.csv --historical-backfill results/v08_historical_replay_non_benchmark_alt_200_price_backfill.csv --historical-quality results/v08_historical_replay_non_benchmark_alt_200_quality_report.csv --output results/event_type_performance_matrix_non_benchmark_alt.csv --summary results/event_type_performance_matrix_non_benchmark_alt_summary.csv --markdown-output results/event_type_performance_matrix_non_benchmark_alt.md
```

Outputs: `results/event_type_performance_matrix_non_benchmark_alt.md; results/event_type_performance_matrix_non_benchmark_alt.csv; results/event_type_performance_matrix_non_benchmark_alt_summary.csv`

Notes: Used by v11 signal policy to reduce BTC/macro benchmark pollution.

### signal_policy_v12_strict

Purpose: Build strict contamination-aware TG routing policy after whale and hack subtype validation.

```powershell
python scripts/validate_whale_position_contamination.py && python scripts/validate_hack_classification.py && python scripts/apply_boost_criteria_v12.py
```

Outputs: `data/tg_signal_policy_v12.csv; results/v12_boost_criteria_report.csv; results/v12_whale_position_contamination_report.md; results/v12_hack_classification_report.csv`

Notes: Prevents apparent historical alpha from becoming a boost when HYPE, single-asset, short-window, or hack-subtype contamination is detected.

### v13_historical_quality_audit

Purpose: Run the Claude-directed v13 historical quality audit: price-in, other grading, HYPE/whale contamination, source identity, regime layer, and active-exploit urgent candidates.

```powershell
python scripts/validate_price_in_effect.py && python scripts/grade_other_quality.py && python scripts/analyze_hype_contamination_detail.py && python scripts/analyze_whale_position_asset_contamination.py && python scripts/build_source_identity_layers.py && python scripts/build_regime_layer_report.py && python scripts/validate_hack_classification.py && python scripts/build_active_exploit_urgent_candidates.py && python scripts/apply_boost_criteria_v12.py
```

Outputs: `results/v13_price_in_report.md; results/v13_other_quality_report.md; results/v13_hype_contamination_report.md; results/v13_whale_asset_contamination_report.md; data/source_identity_layers.csv; results/v13_regime_layer_report.md; results/v13_active_exploit_urgent_candidates.md; data/tg_signal_policy_v12.csv`

Notes: Uses public Binance for price-in/regime checks. Research/source QA only; no trade advice and no TG sending.

### v13_extended_history_replay_500

Purpose: Run extended strict non-benchmark alt historical replay after candidate tightening and HYPE whale exclusion.

```powershell
python scripts/run_v08_historical_signal_replay.py --input data/event_candidates_real_5000_older_7_365d_mature_tightened.csv --limit 500 --mode non_benchmark_alt
```

Outputs: `results/v08_historical_replay_non_benchmark_alt_500_price_backfill.csv; results/v08_historical_replay_non_benchmark_alt_500_quality_report.csv; results/v08_historical_replay_non_benchmark_alt_500_findings.md`

Notes: Uses public Binance data. Current strict eligible count is below 500 when source quality is enforced.

### v13_post_hype_source_regime_refresh

Purpose: Refresh post-HYPE group stats, whale contamination, source identity, and source throttling from the extended replay.

```powershell
python scripts/archive_hype_and_recompute_stats.py --backfill results/v08_historical_replay_non_benchmark_alt_500_price_backfill.csv --output data/backtest_v13_extended_alt_history_clean.csv --summary results/v13_extended_post_hype_removal_summary.csv --group-stats results/v13_extended_post_hype_removal_group_stats.csv --markdown-output results/v13_extended_post_hype_removal_report.md && python scripts/analyze_whale_position_asset_contamination.py --backfill results/v08_historical_replay_non_benchmark_alt_500_price_backfill.csv --output results/v13_extended_whale_asset_contamination_report.csv --summary results/v13_extended_whale_asset_contamination_summary.csv --markdown-output results/v13_extended_whale_asset_contamination_report.md && python scripts/build_source_identity_layers.py --candidates data/event_candidates_real_5000_older_7_365d_mature_tightened.csv --backfill results/v08_historical_replay_non_benchmark_alt_500_price_backfill.csv --output data/source_identity_layers_v13_extended.csv --summary results/v13_extended_source_identity_summary.csv --markdown-output results/v13_extended_source_identity_layers.md && python scripts/score_and_throttle_sources.py --source-layers data/source_identity_layers_v13_extended.csv --clean-backfill data/backtest_v13_extended_alt_history_clean.csv --output data/source_scores_v13_extended.csv --rules results/v13_extended_source_throttle_rules.csv --markdown-output results/v13_extended_source_throttle_report.md
```

Outputs: `results/v13_extended_post_hype_removal_report.md; results/v13_extended_whale_asset_contamination_report.md; data/source_scores_v13_extended.csv; results/v13_extended_source_throttle_report.md`

Notes: No Telegram sending. Used to keep product routing aligned with historical quality results.

### v14_time_and_source_audit

Purpose: Run Claude-directed v14 fixes for remote time-field diagnosis, webhook subsource scoring, and needs_taxonomy_review cleanup.

```powershell
python scripts/diagnose_remote_time_fields.py && python scripts/split_webhook_subsources.py && python scripts/analyze_needs_taxonomy_review.py
```

Outputs: `results/v14_time_field_diagnosis.md; data/source_scores_v14_webhook_split.csv; data/taxonomy_review_reclassified.csv`

Notes: Time diagnosis may use remote read-only export credentials if configured locally. Does not modify remote data or send Telegram messages.

### v14_digest_quality_filters

Purpose: Split flow subtypes, apply v14 quality filters, build short price-in checks, classify upgrade events, run hard PreFilter, build gate-based Composer output, evaluate minimum publishable criteria, enforce block/digest/interrupt policy, then build a strict digest preview.

```powershell
python scripts/split_flow_event_subtypes.py; python scripts/filter_etf_fund_flow.py; python scripts/verify_exploit_amounts.py; python scripts/build_v14_short_price_in.py --limit 281; python scripts/classify_v14_upgrade_events.py; python scripts/build_v14_prefilter.py; python scripts/build_v14_composer_scores.py; python scripts/apply_v14_publish_policy.py; python scripts/define_publishable_event_criteria.py; python scripts/apply_v14_publish_policy.py; python scripts/build_v14_digest_preview.py
```

Outputs: `data/v14_flow_event_subtypes.csv; data/etf_fund_flow_filtered.csv; data/active_exploit_verified.csv; data/v14_short_price_in.csv; data/v14_upgrade_events.csv; data/v14_prefilter_results.csv; data/v14_composer_scores.csv; data/v14_publishable_criteria_eval.csv; data/v14_publish_policy_candidates.csv; results/v14_digest_preview.md`

Notes: Preview only. Does not send Telegram messages and excludes rows failing source, amount, context, or asset-consistency gates.

### v14_security_alert_ingest

Purpose: Try ingesting external security address-risk labels into local normalized CSV.

```powershell
python scripts/ingest_security_alerts.py --source etherscan-labels --label phish-hack --limit 200
```

Outputs: `data/security_events/security_events_normalized.csv; results/v14_security_alert_ingest_summary.csv`

Notes: Requires ETHERSCAN_API_KEY in environment. Current Etherscan metadata export may require higher access level; failure is recorded as warning without leaking the key.

### v14_etf_daily_digest

Purpose: Fetch Farside public BTC ETF flow table and build daily ETF flow digest candidate.

```powershell
python scripts/build_etf_daily_digest.py
```

Outputs: `data/etf_daily_flows_farside.csv; results/v14_etf_daily_digest.md; results/v14_etf_daily_digest_summary.csv`

Notes: Daily ETF flow belongs in evening digest, not intraday alerting. Uses public web data and marks low-flow days as archive-only.

### v14_first_hand_publish_candidates

Purpose: Route first-hand watcher alerts into intraday, digest, daily digest, or archive candidates.

```powershell
python scripts/build_first_hand_publish_candidates.py
```

Outputs: `data/v14_first_hand_publish_candidates.csv; results/v14_first_hand_publish_candidates_summary.csv; results/v14_first_hand_publish_candidates.md`

Notes: Static Hyperliquid snapshots are archived unless there is a real state change; token unlocks are digest-only; CEX listings are digest candidates.

### v14_publishable_criteria_validation

Purpose: Validate minimum publishable criteria against known historical golden events.

```powershell
python scripts/validate_publishable_criteria.py
```

Outputs: `results/v14_publishable_criteria_validation.csv; results/v14_publishable_criteria_validation_summary.csv`

Notes: Golden sample contains expected publishable and non-publishable events; script fails if criteria rejects expected publishable events or admits expected rejects.

### v14_adversarial_golden_validation

Purpose: Generate adversarial publishable/non-publishable samples and validate criteria against boundary cases.

```powershell
python scripts/generate_adversarial_golden_samples.py
```

Outputs: `data/v14_adversarial_golden_events.csv; results/v14_adversarial_golden_validation.csv; results/v14_adversarial_golden_validation_summary.csv`

Notes: Expected to expose some false positives/false negatives; a perfect score is suspicious rather than desirable.

### v14_etf_daily_digest_with_baseline

Purpose: Build ETF daily digest with rolling 90d percentile, same-period comparison, top ETF share, and calendar-effect threshold adjustment.

```powershell
python scripts/build_etf_daily_digest_with_baseline.py
```

Outputs: `results/v14_etf_daily_digest_with_context.md; results/v14_etf_daily_digest_with_context_summary.csv`

Notes: Uses already exported Farside data. Belongs in morning/evening digest, not high-frequency intraday alerts.

### v14_hyperliquid_snapshot_card_v2

Purpose: Aggregate Hyperliquid monitored positions with available baseline, market share, HYPE/non-HYPE long-short split, and liquidation-risk wording.

```powershell
python scripts/aggregate_hyperliquid_snapshot_with_baseline.py
```

Outputs: `results/v14_hyperliquid_snapshot_card_v2.md; results/v14_hyperliquid_snapshot_v2_summary.csv`

Notes: Uses Hyperliquid public API for total open interest. If 24h baseline is missing, the card must explicitly say so.

### v14_project_os_warning_review

Purpose: Classify non-blocking Project OS review items so they do not hide real launch blockers.

```powershell
python scripts/review_project_os_warnings.py
```

Outputs: `results/v14_project_os_warning_review.csv; results/v14_project_os_warning_review.md`

Notes: Review report only; does not suppress validation warnings.

### v14_false_positive_monitor

Purpose: Build offline false-positive and false-negative monitoring from adversarial validation without relying on user feedback.

```powershell
python scripts/build_false_positive_monitor.py
```

Outputs: `results/v14_false_positive_monitor.csv; results/v14_false_positive_monitor_summary.csv; results/v14_false_positive_monitor.md`

Notes: Uses historical/adversarial validation only. Does not require TG user feedback or manual review.

### v14_false_negative_case_review

Purpose: Review false-negative cases and identify required cross-validation evidence before loosening source gates.

```powershell
python scripts/review_false_negative_cases.py
```

Outputs: `results/v14_false_negative_case_review.csv; results/v14_false_negative_case_review_summary.csv; results/v14_false_negative_case_review.md`

Notes: Does not auto-loosen source_basis rules; produces evidence requirements for later rule changes.

### v14_hyperliquid_baseline_readiness

Purpose: Validate whether Hyperliquid snapshot baseline is mature enough to remove Beta wording from daily digests.

```powershell
python scripts/validate_hyperliquid_baseline_readiness.py
```

Outputs: `results/v14_hyperliquid_baseline_readiness.csv; results/v14_hyperliquid_baseline_readiness.md`

Notes: Uses existing Hyperliquid summary; does not wait or fetch live data.

### v14_weekly_fp_analysis

Purpose: Build weekly offline FP/FN analysis from validation monitors, including reason distribution and rule-improvement next actions.

```powershell
python scripts/build_weekly_fp_analysis.py
```

Outputs: `results/v14_weekly_fp_analysis.md; results/v14_weekly_fp_analysis_summary.csv`

Notes: Historical/offline validation only; no user feedback dependency.

### v14_market_state_snapshot

Purpose: Fetch public Binance USD-M price, volume, open-interest, funding, and crowding context for the first screen of TG digests.

```powershell
python scripts/build_market_state_snapshot.py
```

Outputs: `results/v14_market_state_snapshot.csv; results/v14_market_state_snapshot_summary.csv; results/v14_market_state_snapshot.md`

Notes: Observation-only market-structure context. Does not generate trade directions or orders.

### v14_focus_assets

Purpose: Select BTC/ETH-first focus assets and prevent small-cap assets from polluting TG digest first screen unless extreme thresholds are met.

```powershell
python scripts/market/select_focus_assets.py
```

Outputs: `results/v14_focus_assets.csv; results/v14_focus_assets_summary.csv`

Notes: Uses config/asset_tiers.yaml and market-state snapshot rows.

### v14_price_oi_quadrant

Purpose: Classify price/open-interest combinations into plain-Chinese market-structure explanations.

```powershell
python scripts/market/classify_price_oi_quadrant.py
```

Outputs: `results/v14_price_oi_quadrant.csv; results/v14_price_oi_quadrant_summary.csv`

Notes: Observation-only explanation layer; does not output trading instructions.

### v14_etf_plain_summary

Purpose: Convert ETF daily flow percentile context into a short Chinese first-screen digest block.

```powershell
python scripts/reporting/generate_etf_summary.py
```

Outputs: `results/v14_etf_plain_summary.md; results/v14_etf_plain_summary.csv; results/v14_etf_concentration_interpretation.txt`

Notes: Uses existing BTC ETF context summary and optional data/eth_etf_flows_farside.csv. ETH missing data is not faked.

### v14_eth_etf_fetch

Purpose: Attempt to fetch public Farside ETH ETF flow table into local CSV for ETF first-screen summary.

```powershell
python scripts/build_etf_daily_digest.py --asset ETH --url https://farside.co.uk/eth/ --output data/eth_etf_flows_farside.csv --digest-output results/v14_eth_etf_daily_digest.md --summary results/v14_eth_etf_daily_digest_summary.csv
```

Outputs: `data/eth_etf_flows_farside.csv; results/v14_eth_etf_daily_digest.md; results/v14_eth_etf_daily_digest_summary.csv`

Notes: Currently may return warning/no_rows_parsed if Farside Cloudflare blocks local scraping. Do not fabricate ETH ETF data.

### v14_market_state_first_screen

Purpose: Generate a concise first-screen market-state block for TG morning/noon/evening digest.

```powershell
python scripts/reporting/generate_market_state_summary.py
```

Outputs: `results/v14_market_state_first_screen.md; results/v14_market_state_first_screen_summary.csv`

Notes: Runs focus asset, quadrant, and ETF summary dependencies before rendering.

### v14_market_alert_headline

Purpose: Generate one plain-Chinese abnormality headline for the top of TG market-state digest.

```powershell
python scripts/reporting/generate_alert_headline.py
```

Outputs: `results/v14_market_alert_headline.txt; results/v14_market_alert_headline_summary.csv`

Notes: Triggers on major BTC/ETH moves, ETF extremes, funding extremes, and high-priority event density.

### v14_derivatives_history_percentiles

Purpose: Fetch public Binance USD-M funding-rate and open-interest history and compute historical percentiles for TG market-state context.

```powershell
python scripts/market/build_derivatives_history_percentiles.py
```

Outputs: `data/funding_rate/funding_rate_percentiles.csv; data/oi/oi_percentiles.csv; results/v14_derivatives_history_percentiles_summary.csv; results/v14_derivatives_history_percentiles.md`

Notes: Uses 90d funding history and 4h OI history to avoid waiting for local accumulation. Observation-only context.

### v15_percentile_alerts

Purpose: Convert derivative historical percentiles into layered TG placement buckets: first-screen alerts, today-watch candidates, radar triggers, and digest-only context.

```powershell
python scripts/market/generate_percentile_alerts.py
```

Outputs: `results/v15_percentile_alerts.json; results/v15_percentile_alerts.csv; results/v15_percentile_alerts.md; results/v15_percentile_alerts_summary.csv`

Notes: Uses existing market-state and derivative-percentile files. Observation-only wording; no trading instructions.

### v15_hyperliquid_market_meta

Purpose: Fetch Hyperliquid official public perp market metadata and render a concise market-structure card.

```powershell
python scripts/hyperliquid/fetch_market_meta.py && python scripts/hyperliquid/generate_market_meta_card.py
```

Outputs: `data/hyperliquid/market_meta_snapshot.csv; data/hyperliquid/market_meta_history.csv; results/v15_hyperliquid_market_meta_card.md; results/v15_hyperliquid_market_meta_summary.csv`

Notes: Uses official public info API metaAndAssetCtxs. Does not use third-party liquidation heatmap estimates.

### v15_hyperliquid_liquidation_wall

Purpose: Group monitored Hyperliquid large positions into nearest liquidation-wall context for radar or digest routing.

```powershell
python scripts/hyperliquid/generate_liquidation_wall.py
```

Outputs: `results/v15_hyperliquid_liquidation_wall.md; results/v15_hyperliquid_liquidation_wall.csv; results/v15_hyperliquid_liquidation_wall_summary.csv`

Notes: Uses only local monitored position state. Distance under 5% is radar; under 10% is digest; otherwise hidden.

### v14_prioritized_events

Purpose: Audit which TG digest events become top-watch versus other-dynamic items, with explicit scoring reasons.

```powershell
python scripts/events/prioritize_events.py
```

Outputs: `results/v14_prioritized_events.csv; results/v14_today_focus_events.csv; results/v14_other_events.csv; results/v14_prioritized_events.md; results/v14_prioritized_events_summary.csv`

Notes: Static large positions are downweighted; top-watch is capped at three items.

### v14_e2e_publish_preview

Purpose: Build local end-to-end publish preview from ETF and first-hand watcher candidates without sending Telegram.

```powershell
python scripts/test_end_to_end_publish.py
```

Outputs: `results/v14_e2e_publish_preview.md; results/v14_e2e_publish_preview_summary.csv`

Notes: Local preview only. Does not send messages.

### v14_hyperliquid_snapshot_card

Purpose: Aggregate Hyperliquid static position snapshots into morning/evening background card.

```powershell
python scripts/aggregate_hyperliquid_snapshot.py
```

Outputs: `results/v14_hyperliquid_snapshot_card.md; results/v14_hyperliquid_snapshot_summary.csv`

Notes: Static position snapshots are background context only. Real-time alerting requires state changes.

### signal_decay_curve_v11

Purpose: Build horizon-level signal decay curves for event type/source subtype groups.

```powershell
python scripts/build_signal_decay_curve.py --outcomes data/tg_alert_outcomes.csv --historical-backfill results/v08_historical_replay_broad_200_price_backfill.csv --historical-quality results/v08_historical_replay_broad_200_quality_report.csv --output results/signal_decay_curve.csv --summary results/signal_decay_curve_summary.csv --markdown-output results/signal_decay_curve.md
```

Outputs: `results/signal_decay_curve.md; results/signal_decay_curve.csv; results/signal_decay_curve_summary.csv`

Notes: Used to avoid overstating short-lived or immature signals.

### false_positive_analysis_v11

Purpose: Analyze likely false-positive/noisy TG alert groups from outcome rows and radar decision logs.

```powershell
python scripts/build_false_positive_analysis.py --outcomes data/tg_alert_outcomes.csv --decision-log data/tg_radar_decision_log.csv --output results/false_positive_analysis.csv --summary results/false_positive_analysis_summary.csv --markdown-output results/false_positive_analysis.md
```

Outputs: `results/false_positive_analysis.md; results/false_positive_analysis.csv; results/false_positive_analysis_summary.csv`

Notes: Uses statistical/passive feedback only. Does not rely on user reactions and does not produce trade instructions.

### signal_policy_v11

Purpose: Build machine-readable TG routing policy from historical matrix, source effectiveness, and passive false-positive analysis.

```powershell
python scripts/build_v11_signal_policy.py --event-matrix results/event_type_performance_matrix.csv --non-benchmark-event-matrix results/event_type_performance_matrix_non_benchmark_alt.csv --source-effectiveness results/source_effectiveness_report.csv --false-positive results/false_positive_analysis.csv --output data/tg_signal_policy_v11.csv --summary results/v11_signal_policy_summary.csv --report results/v11_signal_policy_report.md
```

Outputs: `data/tg_signal_policy_v11.csv; results/v11_signal_policy_report.md; results/v11_signal_policy_summary.csv`

Notes: Controls priority and cooldown only. It does not create trade direction or buy/sell advice.

### source_adapter_validation_v11

Purpose: Validate normalized watcher/news/calendar source outputs against the v11 adapter schema and registry.

```powershell
python scripts/validate_source_adapter_outputs.py --input data/watcher_events_raw.csv --registry data/source_registry.csv --output results/source_adapter_validation_report.csv --summary results/source_adapter_validation_summary.csv --markdown-output results/source_adapter_validation_report.md
```

Outputs: `results/source_adapter_validation_report.md; results/source_adapter_validation_report.csv; results/source_adapter_validation_summary.csv`

Notes: Adapter QA only. Prevents unregistered or malformed sources from quietly entering downstream reports.

### shadow_source_evaluation_v11

Purpose: Extract shadow-mode source events and summarize whether they are ready for live routing.

```powershell
python scripts/run_shadow_source_evaluation.py --registry data/source_registry.csv --watcher-events data/watcher_events_raw.csv --shadow-output data/shadow_events_raw.csv --summary results/shadow_source_evaluation_summary.csv --report results/shadow_source_evaluation_report.md
```

Outputs: `data/shadow_events_raw.csv; results/shadow_source_evaluation_report.md; results/shadow_source_evaluation_summary.csv`

Notes: Keeps unproven sources in shadow until enough evidence exists.

### tg_evidence_snippets_v11

Purpose: Render evidence-based snippets for TG cards and digests using source effectiveness and event performance data.

```powershell
python scripts/render_tg_evidence_snippet.py --alerts data/tg_alert_ledger.csv --event-matrix results/event_type_performance_matrix.csv --source-effectiveness results/source_effectiveness_report.csv --output data/tg_evidence_snippets.csv --markdown-output results/tg_evidence_snippets.md
```

Outputs: `data/tg_evidence_snippets.csv; results/tg_evidence_snippets.md`

Notes: Replaces black-box wording with sample-count and quality caveats.

### llm_usage_report_v11

Purpose: Summarize Claude/OpenRouter call count, token usage, estimated spend, and failure rate.

```powershell
python scripts/build_llm_usage_report.py --input data/llm_usage_ledger.csv --output results/llm_usage_report.csv --summary results/llm_usage_summary.csv --markdown-output results/llm_usage_report.md
```

Outputs: `results/llm_usage_report.md; results/llm_usage_report.csv; results/llm_usage_summary.csv`

Notes: No secrets are logged. Historical calls before the ledger patch are not backfilled.

### readiness_report_v11

Purpose: Build one readiness report across source registry, adapter validation, source effectiveness, event matrix, signal decay, shadow mode, evidence snippets, digest preview, and LLM cost.

```powershell
python scripts/build_v11_readiness_report.py --output results/v11_readiness_report.md --summary results/v11_readiness_summary.csv
```

Outputs: `results/v11_readiness_report.md; results/v11_readiness_summary.csv`

Notes: This is the current v11 progress dashboard and explicitly reports weak evidence instead of overstating conclusions.

### import_token_unlock_calendar_v081

Purpose: Normalize a raw token-unlock CSV export into the local token_unlock_calendar schema without overwriting the live calendar.

```powershell
python scripts/import_raw_token_unlocks_to_calendar.py --input data/raw_token_unlocks_template.csv --output data/token_unlock_calendar_imported.csv
```

Outputs: `data/token_unlock_calendar_imported.csv; results/v081_token_unlock_import_report.md; results/v081_token_unlock_import_summary.csv`

Notes: Default output is a preview file. Use --output data/token_unlock_calendar.csv only after reviewing quality.

### v06_intake_quality

Purpose: Run v0.6 entity/taxonomy/dedup/relevance pipeline on older500 candidates.

```powershell
python scripts/run_v06_event_intake_quality.py --input data/event_candidates_real_500_older_review_suggested.csv
```

Outputs: `data/event_candidates_v06_enriched.csv; data/event_candidates_v06_relevance_scored.csv; results/v06_relevance_filter_summary.csv`

Notes: Local CSV only.

### time_audit

Purpose: Audit event time provenance and price kline lag.

```powershell
python scripts/audit_event_time_provenance.py --candidates data/event_candidates_real_500_older_review.csv --backfill results/v043_older_mature50_event_price_backfill.csv --output results/v043_time_provenance_report.csv --summary results/v043_time_provenance_summary.csv
```

Outputs: `results/v043_time_provenance_report.csv; results/v043_time_provenance_summary.csv`

Notes: Checks China-time/UTC consistency.

### v043_relevance_audit

Purpose: Audit the historical v043 selected backtest sample against current v0.6 relevance decisions.

```powershell
python scripts/audit_v043_selection_against_v06.py
```

Outputs: `results/v043_selection_vs_v06_relevance_audit.md; results/v043_selection_vs_v06_discard_breakdown.csv; results/v043_selection_vs_v06_event_type_impact.csv`

Notes: Keeps v043 labeled as a historical baseline when current v0.6 would discard selected rows.

### price_source_validation

Purpose: Sample Binance price source validation and produce a recent price point for manual checking.

```powershell
python scripts/validate_price_sources.py --sample-size 30 --output results/price_source_validation_report.csv --recent-output results/recent_price_point_sample.csv
```

Outputs: `results/price_source_validation_report.csv; results/recent_price_point_sample.csv`

Notes: Uses public market data only.

### symbol_map_validation

Purpose: Validate data/symbol_map.csv symbols against public Binance spot and USD-M futures exchangeInfo.

```powershell
python scripts/validate_symbol_map.py
```

Outputs: `results/symbol_map_market_validation.md; results/symbol_map_market_validation_summary.csv`

Notes: Public market metadata only; not part of the default quality gate because it depends on network availability.

### v05_research_validation

Purpose: Run statistical validation on event returns.

```powershell
python scripts/run_v05_research_validation.py
```

Outputs: `results/v05_event_return_statistical_validation.md`

Notes: Research validation only, not trading advice.

### v06_clean_low_risk_preview_backtest

Purpose: Run a non-destructive sanity-check backtest on the current v0.6 clean low-risk preview subset.

```powershell
python scripts/run_v06_clean_low_risk_preview_backtest.py --limit 50
```

Outputs: `results/v06_clean_low_risk_preview_event_price_backfill.csv; results/v06_clean_low_risk_preview_backtest_findings.md`

Notes: Preview only; too small for statistical conclusions and does not replace v043 historical outputs.

### tg_draft_private_pilot

Purpose: Generate local Telegram-style private pilot drafts without calling Telegram or sending messages.

```powershell
python scripts/generate_tg_drafts.py --input data/event_candidates_v06_clean_low_risk_preview.csv --output data/tg_drafts_v06_private_pilot.csv --markdown-output results/tg_drafts_v06_private_pilot.md --limit 20
```

Outputs: `data/tg_drafts_v06_private_pilot.csv; results/tg_drafts_v06_private_pilot.md`

Notes: Draft-only queue; every row remains pending_review and auto_send_enabled=false.

### tg_draft_prefilter

Purpose: Apply local pre-Claude filters for duplicates, weak generic content, weak marketing/adoption stories, and incomplete titles.

```powershell
python scripts/prefilter_tg_draft_candidates.py --input data/event_candidates_v06_clean_low_risk_preview.csv --output data/event_candidates_v06_tg_prefilter_pass.csv --rejects-output data/event_candidates_v06_tg_prefilter_rejects.csv --summary results/tg_draft_prefilter_summary.csv
```

Outputs: `data/event_candidates_v06_tg_prefilter_pass.csv; data/event_candidates_v06_tg_prefilter_rejects.csv; results/tg_draft_prefilter_summary.csv`

Notes: Reduces Claude calls by filtering obvious rejects locally.

### tg_draft_feedback_summary

Purpose: Summarize local TG draft private-pilot feedback after reviewer fields are filled.

```powershell
python scripts/summarize_tg_draft_feedback.py --input data/tg_drafts_v06_private_pilot.csv --summary results/tg_draft_feedback_summary.csv --markdown-output results/tg_draft_feedback_summary.md
```

Outputs: `results/tg_draft_feedback_summary.csv; results/tg_draft_feedback_summary.md`

Notes: Local review metrics only; does not approve auto-send.

### tg_draft_ai_review

Purpose: Use Claude/OpenRouter to review local TG drafts and fill reviewer fields.

```powershell
python scripts/ai_review_tg_drafts.py --input data/tg_drafts_v06_private_pilot.csv --output data/tg_drafts_v06_private_pilot_ai_reviewed.csv --summary results/tg_draft_ai_review_summary.csv --limit 20 --apply
```

Outputs: `data/tg_drafts_v06_private_pilot_ai_reviewed.csv; results/tg_draft_ai_review_summary.csv`

Notes: Requires OPENROUTER_API_KEY only in the current terminal environment. Review suggestions only; no Telegram send.

### tg_approved_pool

Purpose: Build approved-only local TG draft pool from AI-reviewed draft queue.

```powershell
python scripts/build_approved_tg_draft_pool.py --input data/tg_drafts_v06_private_pilot.csv --output data/tg_drafts_v06_approved_pool.csv --summary results/tg_draft_approved_pool_summary.csv --markdown-output results/tg_draft_approved_pool.md
```

Outputs: `data/tg_drafts_v06_approved_pool.csv; results/tg_draft_approved_pool.md`

Notes: Does not send messages; approved pool is still local.

### tg_draft_review_packet

Purpose: Prepare a compact packet for reviewing local TG drafts without editing the wide draft CSV directly.

```powershell
python scripts/prepare_tg_draft_review_packet.py --input data/tg_drafts_v06_private_pilot.csv --output data/tg_draft_review_packet.csv --markdown-output results/tg_draft_review_packet.md --limit 20 --only-pending
```

Outputs: `data/tg_draft_review_packet.csv; results/tg_draft_review_packet.md`

Notes: Review helper only; does not send or approve messages.

### tg_draft_apply_review_packet

Purpose: Apply compact review packet fields back to the main local TG draft queue.

```powershell
python scripts/apply_tg_draft_review_packet.py --drafts data/tg_drafts_v06_private_pilot.csv --packet data/tg_draft_review_packet.csv --output data/tg_drafts_v06_private_pilot.csv
```

Outputs: `data/tg_drafts_v06_private_pilot.csv; results/tg_draft_review_packet_apply_summary.csv`

Notes: Local CSV merge only; does not send or approve externally.

### tg_draft_validation

Purpose: Validate local TG draft safety: no auto-send, required fields present, no recommendation language.

```powershell
python scripts/validate_tg_drafts.py --input data/tg_drafts_v06_private_pilot.csv --output results/tg_draft_validation_report.csv --summary results/tg_draft_validation_summary.csv --markdown-output results/tg_draft_validation_report.md
```

Outputs: `results/tg_draft_validation_report.csv; results/tg_draft_validation_summary.csv`

Notes: Hard safety check for draft-only pilot.

### other_review_reason_split

Purpose: Split the broad other_review bucket into explicit rule-based review/reject reasons without mutating the source queue.

```powershell
python scripts/classify_other_review_reasons.py --input data/event_candidates_v06_other_review_queue.csv --output data/event_candidates_v06_other_review_classified.csv --summary results/v06_other_review_reason_summary.csv --markdown-output results/v06_other_review_reason_summary.md
```

Outputs: `data/event_candidates_v06_other_review_classified.csv; results/v06_other_review_reason_summary.csv`

Notes: Supports taxonomy cleanup and discard audit; does not publish or backtest rows.

### backtest_readiness

Purpose: Summarize whether existing backtest outputs are safe to use as statistical conclusions.

```powershell
python scripts/build_backtest_readiness_report.py
```

Outputs: `results/backtest_readiness_report.md; results/backtest_readiness_summary.csv`

Notes: Conclusion-safety report only; does not run prices or alter samples.
