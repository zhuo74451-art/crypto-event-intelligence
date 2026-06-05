# Artifact Manifest

Last updated: 2026-06-01 10:07:26 UTC+8

required_artifacts: 274
missing_required_count: 0
stale_required_count: 103

| artifact_id | category | path | required | freshness | exists | status | updated_at_china | notes |
|---|---|---|---|---|---|---|---|---|
| `project_root_rules` | project_os | `AGENTS.md` | yes | stable | yes | pass | 2026-05-27 14:29:24 | Local project rules. |
| `python_requirements` | project_os | `requirements.txt` | yes | stable | yes | pass | 2026-05-27 16:08:36 | Minimal local runtime dependencies. |
| `project_state` | project_os | `docs/PROJECT_STATE.md` | yes | fresh_24h | yes | fail | 2026-05-29 12:52:28 | Current local project memory. |
| `project_dashboard` | project_os | `docs/PROJECT_DASHBOARD.md` | yes | fresh_24h | yes | fail | 2026-05-29 12:52:29 | Current local dashboard. |
| `validation_checklist` | project_os | `docs/VALIDATION_CHECKLIST.md` | yes | stable | yes | pass | 2026-05-27 16:12:44 | Operator validation checklist. |
| `command_registry_doc` | project_os | `docs/COMMAND_REGISTRY.md` | yes | fresh_24h | yes | fail | 2026-05-29 14:29:06 | Runnable command inventory. |
| `artifact_manifest_doc` | project_os | `docs/ARTIFACT_MANIFEST.md` | no | fresh_24h | yes | warning | 2026-05-29 14:29:07 | This generated manifest. |
| `project_review_actions_doc` | project_os | `docs/PROJECT_REVIEW_ACTIONS.md` | yes | fresh_24h | yes | fail | 2026-05-29 12:52:24 | Dashboard review action queue. |
| `decisions_doc` | project_os | `docs/DECISIONS.md` | yes | stable | yes | pass | 2026-05-28 21:21:51 | Accepted direction decisions. |
| `mvp_timeline_doc` | project_os | `docs/MVP_TIMELINE.md` | yes | stable | yes | pass | 2026-05-27 16:52:39 | Current MVP definition and timeline estimate. |
| `ai_cost_control_policy` | project_os | `docs/AI_COST_CONTROL_POLICY.md` | yes | stable | yes | pass | 2026-05-27 17:07:32 | AI/Claude routing and spend-control policy. |
| `secret_setup_doc` | project_os | `docs/SECRET_SETUP.md` | yes | stable | yes | pass | 2026-05-27 17:55:40 | Local secret setup instructions. |
| `gitignore` | project_os | `.gitignore` | yes | stable | yes | pass | 2026-05-29 14:28:02 | Ignore local secret files and runtime noise. |
| `secret_template` | config | `config/secrets.example.ps1` | yes | stable | yes | pass | 2026-05-27 17:55:27 | Local secret template with placeholders only. |
| `cursor_prompt` | agent_handoff | `docs/CURSOR_NEXT_PROMPT.md` | yes | fresh_24h | yes | fail | 2026-05-29 12:52:30 | File-based Cursor handoff. |
| `cursor_backlog` | agent_handoff | `docs/CURSOR_TASK_BACKLOG.md` | yes | stable | yes | pass | 2026-05-27 15:51:15 | Cursor task backlog. |
| `claude_prompt` | agent_handoff | `docs/CLAUDE_NEXT_PROMPT.md` | yes | fresh_24h | yes | fail | 2026-05-29 12:52:30 | Current Claude consultation prompt. |
| `claude_question_backlog` | agent_handoff | `docs/CLAUDE_QUESTION_BACKLOG.md` | yes | stable | yes | pass | 2026-05-29 12:52:15 | Architecture question backlog. |
| `claude_response_index_doc` | agent_handoff | `docs/CLAUDE_RESPONSE_INDEX.md` | yes | fresh_24h | yes | fail | 2026-05-29 12:52:19 | Local Claude response index. |
| `claude_decision_review_doc` | agent_handoff | `docs/CLAUDE_DECISION_REVIEW.md` | yes | fresh_24h | yes | fail | 2026-05-29 12:52:20 | Claude recommendation review queue. |
| `symbol_map` | data | `data/symbol_map.csv` | yes | stable | yes | pass | 2026-05-27 17:36:15 | Asset to market symbol map. |
| `entity_dictionary` | data | `data/entity_dictionary.csv` | yes | stable | yes | pass | 2026-05-27 12:21:19 | Entity dictionary for intake rules. |
| `source_timezone_rules` | data | `data/source_timezone_rules.csv` | yes | stable | yes | pass | 2026-05-27 14:04:51 | Source time-zone assumptions. |
| `older500_raw_news` | data | `data/raw_news_real_500_older.csv` | yes | stable | yes | pass | 2026-05-26 10:43:18 | Older real-news source export. |
| `older500_candidates` | data | `data/event_candidates_real_500_older_review.csv` | yes | stable | yes | pass | 2026-05-27 14:06:50 | Older candidate import output. |
| `v06_relevance_scored` | data | `data/event_candidates_v06_relevance_scored.csv` | yes | stable | yes | pass | 2026-05-27 16:21:12 | v0.6 scored intake output. |
| `v06_manual_label_sheet` | data | `data/v06_manual_label_sheet.csv` | yes | stable | yes | pass | 2026-05-27 15:23:40 | AI-first review sheet. |
| `v06_other_review_classified` | data | `data/event_candidates_v06_other_review_classified.csv` | no | stable | yes | pass | 2026-05-27 18:38:15 | Rule-based split of the other_review bucket. |
| `project_review_action_queue` | data | `data/project_review_action_queue.csv` | yes | fresh_24h | yes | fail | 2026-05-29 12:52:24 | Generated dashboard action queue. |
| `claude_decision_queue` | data | `data/claude_decision_review_queue.csv` | yes | fresh_24h | yes | fail | 2026-05-29 12:52:20 | Generated Claude decision queue. |
| `tg_pilot_gate` | results | `results/v06_tg_pilot_gate_report.md` | yes | fresh_24h | yes | fail | 2026-05-29 12:14:13 | TG draft pilot safety gate. |
| `project_os_validation_report` | results | `results/project_os_validation_report.md` | yes | stable | yes | pass | 2026-06-01 10:07:07 | Consolidated validation report. |
| `project_os_validation_summary` | results | `results/project_os_validation_summary.csv` | yes | stable | yes | pass | 2026-06-01 10:07:07 | Consolidated validation summary. |
| `local_environment_summary` | results | `results/local_environment_summary.csv` | yes | fresh_24h | yes | fail | 2026-05-29 12:52:17 | Local runtime check summary. |
| `secret_leak_summary` | results | `results/secret_leak_summary.csv` | yes | fresh_24h | yes | pass | 2026-06-01 10:07:04 | Secret scan summary. |
| `command_registry_summary` | results | `results/command_registry_summary.csv` | yes | fresh_24h | yes | fail | 2026-05-29 14:29:06 | Command registry summary. |
| `project_review_action_summary` | results | `results/project_review_action_summary.csv` | yes | fresh_24h | yes | fail | 2026-05-29 12:52:24 | Review action summary. |
| `project_dashboard_metrics` | results | `results/project_dashboard_metrics.csv` | yes | fresh_24h | yes | fail | 2026-05-29 12:52:29 | Dashboard metrics CSV. |
| `v043_backfill` | results | `results/v043_older_mature50_event_price_backfill.csv` | yes | stable | yes | pass | 2026-05-27 14:06:55 | Historical mature50 backfill. |
| `v043_quality` | results | `results/v043_older_mature50_event_quality_report.csv` | yes | stable | yes | pass | 2026-05-27 14:06:56 | Historical mature50 quality report. |
| `time_provenance_summary` | results | `results/v043_time_provenance_summary.csv` | yes | stable | yes | pass | 2026-05-27 14:06:59 | Time provenance summary. |
| `v043_selection_v06_summary` | results | `results/v043_selection_vs_v06_relevance_summary.csv` | yes | fresh_24h | yes | fail | 2026-05-29 12:52:18 | v043 versus v0.6 relevance audit summary. |
| `v043_selection_v06_breakdown` | results | `results/v043_selection_vs_v06_discard_breakdown.csv` | yes | fresh_24h | yes | fail | 2026-05-29 12:52:18 | Discard reason breakdown for historical v043 selection. |
| `v043_selection_v06_impact` | results | `results/v043_selection_vs_v06_event_type_impact.csv` | yes | fresh_24h | yes | fail | 2026-05-29 12:52:18 | Event-type impact of v0.6 discard decisions. |
| `v06_low_risk_preview_backfill` | results | `results/v06_clean_low_risk_preview_event_price_backfill.csv` | no | stable | yes | pass | 2026-05-27 16:27:45 | Optional v0.6 low-risk preview sanity-check backfill. |
| `v06_low_risk_preview_quality` | results | `results/v06_clean_low_risk_preview_event_quality_report.csv` | no | stable | yes | pass | 2026-05-27 16:27:46 | Optional v0.6 low-risk preview quality report. |
| `v06_low_risk_preview_findings` | results | `results/v06_clean_low_risk_preview_backtest_findings.md` | no | stable | yes | pass | 2026-05-27 16:27:47 | Optional v0.6 low-risk preview findings. |
| `tg_drafts_private_pilot` | data | `data/tg_drafts_v06_private_pilot.csv` | no | stable | yes | pass | 2026-05-27 18:43:18 | Local TG private-pilot draft queue; no auto-send. |
| `tg_drafts_private_pilot_ai_reviewed` | data | `data/tg_drafts_v06_private_pilot_ai_reviewed.csv` | no | stable | yes | pass | 2026-05-27 17:13:43 | AI-reviewed local TG private-pilot draft queue. |
| `tg_prefilter_pass` | data | `data/event_candidates_v06_tg_prefilter_pass.csv` | no | stable | yes | pass | 2026-05-27 18:38:15 | Local pre-Claude TG candidate prefilter pass set. |
| `tg_prefilter_rejects` | data | `data/event_candidates_v06_tg_prefilter_rejects.csv` | no | stable | yes | pass | 2026-05-27 18:38:15 | Local pre-Claude TG candidate prefilter rejects. |
| `tg_approved_pool` | data | `data/tg_drafts_v06_approved_pool.csv` | no | stable | yes | pass | 2026-05-27 18:38:15 | Approved-only local TG draft pool. |
| `tg_draft_review_packet` | data | `data/tg_draft_review_packet.csv` | no | stable | yes | pass | 2026-05-27 18:38:15 | Compact local draft review packet. |
| `tg_drafts_private_pilot_preview` | results | `results/tg_drafts_v06_private_pilot.md` | no | stable | yes | pass | 2026-05-27 18:43:18 | Readable preview of local TG drafts. |
| `tg_draft_review_packet_md` | results | `results/tg_draft_review_packet.md` | no | stable | yes | pass | 2026-05-27 18:38:15 | Readable compact local draft review packet. |
| `tg_draft_feedback_summary` | results | `results/tg_draft_feedback_summary.csv` | no | stable | yes | pass | 2026-05-27 18:38:15 | Local private-pilot draft feedback summary. |
| `tg_draft_ai_review_summary` | results | `results/tg_draft_ai_review_summary.csv` | no | stable | yes | pass | 2026-05-27 17:13:43 | AI-review summary for local TG private-pilot drafts. |
| `tg_prefilter_summary` | results | `results/tg_draft_prefilter_summary.csv` | no | stable | yes | pass | 2026-05-27 18:38:15 | Local pre-Claude TG candidate prefilter summary. |
| `tg_approved_pool_summary` | results | `results/tg_draft_approved_pool_summary.csv` | no | stable | yes | pass | 2026-05-27 18:38:15 | Approved-only local TG draft pool summary. |
| `tg_draft_validation_summary` | results | `results/tg_draft_validation_summary.csv` | no | stable | yes | pass | 2026-05-27 18:43:25 | Local private-pilot draft safety validation summary. |
| `daily_private_pilot_summary` | results | `results/daily_private_pilot_summary.csv` | no | stable | yes | pass | 2026-05-27 18:38:15 | One-row daily private-pilot operational summary. |
| `daily_private_pilot_report` | results | `results/daily_private_pilot_report.md` | no | stable | yes | pass | 2026-05-27 18:38:15 | One-page daily private-pilot operational report. |
| `tg_draft_rule_improvement_summary` | results | `results/tg_draft_rule_improvement_summary.csv` | no | stable | yes | pass | 2026-05-27 18:38:15 | Summary of AI-rejected draft rule improvement candidates. |
| `tg_draft_rule_improvement_report` | results | `results/tg_draft_rule_improvement_report.md` | no | stable | yes | pass | 2026-05-27 18:38:15 | AI-rejected draft rule improvement report. |
| `v07_watchlist_addresses` | data | `data/watchlist_addresses.csv` | yes | stable | yes | pass | 2026-05-28 09:48:08 | v0.7 first-hand watcher address watchlist. |
| `v07_stablecoin_watchlist` | data | `data/stablecoin_watchlist.csv` | yes | stable | yes | pass | 2026-05-27 17:33:09 | v0.7 stablecoin mint/burn watchlist. |
| `v07_hyperliquid_watchlist` | data | `data/hyperliquid_watchlist.csv` | yes | stable | yes | pass | 2026-05-27 18:47:04 | v0.7 Hyperliquid perp-position watchlist. |
| `v07_watcher_alerts_raw` | data | `data/watcher_alerts_raw.csv` | no | stable | yes | pass | 2026-05-28 19:23:36 | Normalized first-hand watcher alerts. |
| `v07_hyperliquid_position_alerts` | data | `data/watcher_alerts_hyperliquid_positions.csv` | no | stable | yes | pass | 2026-05-29 12:18:12 | Raw Hyperliquid large-position watcher alerts. |
| `v07_watcher_events_raw` | data | `data/watcher_events_raw.csv` | no | stable | yes | pass | 2026-05-28 19:23:36 | Watcher alerts converted to event schema. |
| `v07_watcher_tg_drafts` | data | `data/tg_drafts_v07_watcher_private_pilot.csv` | no | stable | yes | pass | 2026-05-28 19:23:36 | Local TG draft preview for first-hand watcher alerts. |
| `v07_watchlist_validation_summary` | results | `results/v07_watchlist_validation_summary.csv` | yes | fresh_24h | yes | fail | 2026-05-28 19:23:27 | v0.7 watchlist validation summary. |
| `v07_watcher_run_summary` | results | `results/v07_first_hand_watcher_run_summary.csv` | no | stable | yes | pass | 2026-05-28 19:23:36 | v0.7 first-hand watcher run summary. |
| `v07_watcher_daily_report` | results | `results/v07_watcher_daily_report.md` | no | stable | yes | pass | 2026-05-28 19:23:36 | Readable daily report for first-hand watcher alerts. |
| `v07_watcher_tg_validation_summary` | results | `results/tg_drafts_v07_watcher_validation_summary.csv` | no | stable | yes | pass | 2026-05-28 19:23:36 | TG draft validation summary for watcher alerts. |
| `v07_tg_live_monitor_summary` | results | `results/v07_tg_live_monitor_summary.csv` | no | fresh_24h | yes | warning | 2026-05-28 12:39:56 | Live TG watcher monitor runtime summary. |
| `v08_tg_send_time_policy` | data | `config/tg_send_time_policy.csv` | yes | stable | yes | pass | 2026-05-28 11:20:06 | China-time flexible TG send timing policy. |
| `v08_tg_digest_sent_state` | data | `data/tg_digest_sent_state.csv` | no | stable | yes | pass | 2026-05-29 12:32:48 | Sent-state dedupe for scheduled TG digests. |
| `v08_cex_netflow_baseline_state` | data | `data/cex_netflow_baseline_state.csv` | no | stable | yes | pass | 2026-05-28 12:48:56 | Rolling baseline samples for CEX netflow context. |
| `v08_hyperliquid_position_state_history` | data | `data/hyperliquid_position_state_history.csv` | no | stable | yes | pass | 2026-05-29 12:18:12 | Append-only Hyperliquid watched-position state history. |
| `v081_raw_token_unlocks_template` | data | `data/raw_token_unlocks_template.csv` | yes | stable | yes | pass | 2026-05-28 14:18:05 | Template for raw token unlock CSV imports. |
| `v081_token_unlock_column_mapping` | data | `data/token_unlock_column_mapping.json` | yes | stable | yes | pass | 2026-05-28 14:18:14 | Column alias mapping for token unlock CSV imports. |
| `v081_token_unlock_calendar_imported` | data | `data/token_unlock_calendar_imported.csv` | no | stable | yes | pass | 2026-05-28 14:18:50 | Non-destructive imported token unlock calendar preview. |
| `v08_binance_long_short_snapshot` | data | `data/binance_long_short_snapshot.csv` | no | fresh_24h | yes | warning | 2026-05-29 12:32:37 | Binance USD-M public long/short ratio snapshot. |
| `v08_binance_long_short_summary` | results | `results/v08_binance_long_short_summary.csv` | no | fresh_24h | yes | warning | 2026-05-29 12:32:37 | Summary of Binance USD-M long/short ratio snapshot. |
| `v08_tg_morning_digest` | results | `results/v08_tg_morning_digest.md` | no | fresh_24h | yes | warning | 2026-05-28 12:55:25 | China-time morning TG intelligence digest. |
| `v08_tg_morning_digest_summary` | results | `results/v08_tg_morning_digest_summary.csv` | no | fresh_24h | yes | warning | 2026-05-28 12:55:25 | Morning digest run summary. |
| `v08_tg_noon_digest` | results | `results/v08_tg_noon_digest.md` | no | fresh_24h | yes | warning | 2026-05-28 12:55:44 | China-time noon TG intelligence digest. |
| `v08_tg_noon_digest_summary` | results | `results/v08_tg_noon_digest_summary.csv` | no | fresh_24h | yes | warning | 2026-05-28 12:55:44 | Noon digest run summary. |
| `v08_tg_evening_digest` | results | `results/v08_tg_evening_digest.md` | no | fresh_24h | yes | warning | 2026-05-28 17:51:34 | China-time evening TG intelligence digest. |
| `v08_tg_evening_digest_summary` | results | `results/v08_tg_evening_digest_summary.csv` | no | fresh_24h | yes | warning | 2026-05-28 17:51:34 | Evening digest run summary. |
| `backtest_readiness_summary` | results | `results/backtest_readiness_summary.csv` | yes | fresh_24h | yes | fail | 2026-05-29 12:52:21 | Conclusion-safety summary for current backtest outputs. |
| `backtest_readiness_report` | results | `results/backtest_readiness_report.md` | yes | fresh_24h | yes | fail | 2026-05-29 12:52:21 | Conclusion-safety report for current backtest outputs. |
| `v06_other_review_reason_summary` | results | `results/v06_other_review_reason_summary.csv` | no | stable | yes | pass | 2026-05-27 18:38:15 | Summary of rule-based other_review split. |
| `quality_gate_script` | script | `scripts/run_v06_quality_gate.py` | yes | stable | yes | pass | 2026-05-27 16:29:44 | Full local quality gate. |
| `project_os_validation_script` | script | `scripts/validate_project_os.py` | yes | stable | yes | pass | 2026-05-27 16:14:01 | Project OS validator. |
| `artifact_manifest_script` | script | `scripts/build_artifact_manifest.py` | yes | stable | yes | pass | 2026-05-29 12:24:57 | Artifact manifest generator. |
| `symbol_map_validation_script` | script | `scripts/validate_symbol_map.py` | yes | stable | yes | pass | 2026-05-27 16:22:14 | Optional public Binance symbol map validator. |
| `v06_low_risk_preview_backtest_script` | script | `scripts/run_v06_clean_low_risk_preview_backtest.py` | yes | stable | yes | pass | 2026-05-27 16:26:56 | Optional low-risk preview sanity-check backtest runner. |
| `tg_draft_generator_script` | script | `scripts/generate_tg_drafts.py` | yes | stable | yes | pass | 2026-05-27 18:42:47 | Local TG-style draft generator; never sends messages. |
| `tg_draft_feedback_summary_script` | script | `scripts/summarize_tg_draft_feedback.py` | yes | stable | yes | pass | 2026-05-27 16:42:14 | Local TG draft feedback summarizer. |
| `tg_draft_ai_review_script` | script | `scripts/ai_review_tg_drafts.py` | yes | stable | yes | pass | 2026-05-27 16:58:31 | OpenRouter/Claude AI reviewer for local TG drafts. |
| `tg_draft_prefilter_script` | script | `scripts/prefilter_tg_draft_candidates.py` | yes | stable | yes | pass | 2026-05-27 17:16:35 | Local pre-Claude TG candidate prefilter. |
| `tg_approved_pool_script` | script | `scripts/build_approved_tg_draft_pool.py` | yes | stable | yes | pass | 2026-05-27 17:10:14 | Approved-only local TG draft pool builder. |
| `tg_draft_validation_script` | script | `scripts/validate_tg_drafts.py` | yes | stable | yes | pass | 2026-05-28 12:35:06 | Local TG draft safety validator. |
| `tg_draft_review_packet_script` | script | `scripts/prepare_tg_draft_review_packet.py` | yes | stable | yes | pass | 2026-05-27 16:54:22 | Compact local TG draft review packet builder. |
| `tg_draft_review_packet_apply_script` | script | `scripts/apply_tg_draft_review_packet.py` | yes | stable | yes | pass | 2026-05-27 16:55:51 | Apply compact TG draft review packet back to the main draft queue. |
| `other_review_reason_script` | script | `scripts/classify_other_review_reasons.py` | yes | stable | yes | pass | 2026-05-27 16:53:51 | Rule-based other_review reason splitter. |
| `daily_private_pilot_runner` | script | `scripts/run_daily_private_pilot.py` | yes | stable | yes | pass | 2026-05-27 17:13:17 | One-command local private-pilot workflow runner. |
| `daily_private_pilot_report_script` | script | `scripts/build_daily_private_pilot_report.py` | yes | stable | yes | pass | 2026-05-27 17:10:49 | One-page local private-pilot report builder. |
| `tg_draft_rule_improvement_script` | script | `scripts/build_tg_draft_rule_improvement_report.py` | yes | stable | yes | pass | 2026-05-27 17:02:44 | Convert AI draft rejects into rule-improvement candidates. |
| `backtest_readiness_script` | script | `scripts/build_backtest_readiness_report.py` | yes | stable | yes | pass | 2026-05-27 16:32:32 | Backtest conclusion-safety report builder. |
| `v07_watchlist_validation_script` | script | `scripts/validate_v07_watchlists.py` | yes | stable | yes | pass | 2026-05-27 18:48:09 | v0.7 watchlist validator. |
| `v07_first_hand_watcher_runner` | script | `scripts/run_v07_first_hand_watchers.py` | yes | stable | yes | pass | 2026-05-28 14:45:16 | v0.7 first-hand watcher runner. |
| `v07_eth_address_watcher` | script | `scripts/watch_eth_address_transfers.py` | yes | stable | yes | pass | 2026-05-27 17:53:35 | Ethereum watched address transfer watcher. |
| `v07_stablecoin_watcher` | script | `scripts/watch_stablecoin_mint_burn.py` | yes | stable | yes | pass | 2026-05-27 17:53:07 | Stablecoin mint/burn watcher. |
| `v07_hyperliquid_position_watcher` | script | `scripts/watch_hyperliquid_positions.py` | yes | stable | yes | pass | 2026-05-28 14:44:33 | Hyperliquid watched account perp-position watcher. |
| `v07_watcher_normalizer` | script | `scripts/normalize_watcher_alerts_to_events.py` | yes | stable | yes | pass | 2026-05-28 12:29:17 | Watcher alert to event normalizer. |
| `v07_watcher_tg_draft_generator` | script | `scripts/generate_watcher_tg_drafts.py` | yes | stable | yes | pass | 2026-05-28 15:44:35 | Watcher TG draft preview generator. |
| `v07_tg_live_monitor` | script | `scripts/run_v07_tg_live_monitor.py` | yes | stable | yes | pass | 2026-05-28 14:49:08 | Continuous watcher-to-TG live monitor with dedupe. |
| `v07_tg_live_monitor_stop` | script | `scripts/stop_v07_tg_live_monitor.ps1` | yes | stable | yes | pass | 2026-05-27 19:02:20 | Stop helper for continuous watcher-to-TG live monitor. |
| `v08_binance_long_short_watcher` | script | `scripts/watch_binance_long_short_ratios.py` | yes | stable | yes | pass | 2026-05-28 11:28:21 | Binance USD-M public long/short ratio snapshot fetcher. |
| `v08_tg_morning_digest_builder` | script | `scripts/build_tg_morning_digest.py` | yes | stable | yes | pass | 2026-05-29 12:31:43 | Morning TG digest builder and optional sender. |
| `v08_tg_sent_state_metadata_enrichment` | script | `scripts/enrich_tg_sent_state_metadata.py` | yes | stable | yes | pass | 2026-05-28 11:51:18 | TG sent-state metadata backfill helper. |
| `v08_tg_source_usefulness_report` | script | `scripts/build_tg_source_usefulness_report.py` | yes | stable | yes | pass | 2026-05-28 12:13:08 | TG source usefulness report builder. |
| `v08_tg_quality_loop` | script | `scripts/run_tg_quality_loop.py` | yes | stable | yes | pass | 2026-05-28 12:13:18 | One-command TG quality loop runner. |
| `v08_historical_replay_sample_builder` | script | `scripts/build_historical_signal_replay_sample.py` | yes | stable | yes | pass | 2026-05-28 19:55:56 | Historical signal replay sample builder. |
| `v08_historical_replay_runner` | script | `scripts/run_v08_historical_signal_replay.py` | yes | stable | yes | pass | 2026-05-28 18:50:17 | Historical signal replay pipeline runner. |
| `v08_historical_replay_summarizer` | script | `scripts/summarize_historical_signal_replay.py` | yes | stable | yes | pass | 2026-05-28 12:18:46 | Historical signal replay findings summarizer. |
| `v081_historical_source_usefulness_builder` | script | `scripts/build_historical_source_usefulness_from_backtest.py` | yes | stable | yes | pass | 2026-05-28 14:06:02 | Build historical source/event usefulness metrics from backtest rows. |
| `v081_source_readiness_builder` | script | `scripts/build_v08_source_readiness_report.py` | yes | stable | yes | pass | 2026-05-28 14:09:20 | Build source-readiness report for first-hand expansion issues. |
| `v081_token_unlock_calendar_quality` | script | `scripts/build_token_unlock_calendar_quality_report.py` | yes | stable | yes | pass | 2026-05-28 14:32:27 | Validate local token unlock calendar readiness. |
| `v081_token_unlock_importer` | script | `scripts/import_raw_token_unlocks_to_calendar.py` | yes | stable | yes | pass | 2026-05-28 14:18:43 | Normalize raw token unlock CSV exports into calendar schema. |
| `v081_cex_netflow_baseline_report` | script | `scripts/build_cex_netflow_baseline_report.py` | yes | stable | yes | pass | 2026-05-28 14:14:04 | Summarize CEX netflow rolling baseline readiness. |
| `v081_hyperliquid_state_history_report` | script | `scripts/build_hyperliquid_state_history_report.py` | yes | stable | yes | pass | 2026-05-28 14:14:25 | Summarize Hyperliquid state history readiness. |
| `v081_source_quality_runner` | script | `scripts/run_v081_source_quality_reports.py` | yes | stable | yes | pass | 2026-05-28 14:33:43 | Run all v0.8.1 source quality reports. |
| `v08_tg_sent_state_metadata_enrichment_summary` | result | `results/v08_tg_sent_state_metadata_enrichment_summary.csv` | yes | stable | yes | pass | 2026-05-28 13:27:53 | TG sent-state metadata enrichment summary. |
| `v08_tg_source_usefulness_report` | result | `results/v08_tg_source_usefulness_report.md` | yes | stable | yes | pass | 2026-05-28 13:28:41 | TG source usefulness markdown report. |
| `v08_tg_source_usefulness_summary` | result | `results/v08_tg_source_usefulness_summary.csv` | yes | stable | yes | pass | 2026-05-28 13:28:41 | TG source usefulness summary. |
| `v08_tg_source_usefulness_by_source` | result | `results/v08_tg_source_usefulness_by_source.csv` | yes | stable | yes | pass | 2026-05-28 13:28:41 | TG source usefulness by-source metrics. |
| `v08_tg_quality_loop_summary` | result | `results/v08_tg_quality_loop_summary.csv` | yes | stable | yes | pass | 2026-05-28 13:28:41 | TG quality loop run summary. |
| `v08_historical_replay_broad_200_events` | data | `data/events_v08_historical_replay_broad_200.csv` | yes | stable | yes | pass | 2026-05-28 12:00:47 | Broad historical replay event sample. |
| `v08_historical_replay_conservative_120_events` | data | `data/events_v08_historical_replay_conservative_120.csv` | yes | stable | yes | pass | 2026-05-28 14:07:43 | Conservative historical replay event sample. |
| `v08_historical_replay_non_btc_single_asset_200_events` | data | `data/events_v08_historical_replay_non_btc_single_asset_200.csv` | yes | stable | yes | pass | 2026-05-28 12:15:29 | Non-BTC single-asset historical replay event sample. |
| `v08_historical_replay_broad_200_backfill` | result | `results/v08_historical_replay_broad_200_price_backfill.csv` | yes | stable | yes | pass | 2026-05-28 12:03:46 | Broad historical replay price backfill. |
| `v08_historical_replay_broad_200_findings` | result | `results/v08_historical_replay_broad_200_findings.md` | yes | stable | yes | pass | 2026-05-28 12:18:53 | Broad historical replay findings. |
| `v08_historical_replay_conservative_120_backfill` | result | `results/v08_historical_replay_conservative_120_price_backfill.csv` | yes | stable | yes | pass | 2026-05-28 14:08:09 | Conservative historical replay price backfill. |
| `v08_historical_replay_conservative_120_findings` | result | `results/v08_historical_replay_conservative_120_findings.md` | yes | stable | yes | pass | 2026-05-28 14:08:11 | Conservative historical replay findings. |
| `v08_historical_replay_non_btc_single_asset_200_backfill` | result | `results/v08_historical_replay_non_btc_single_asset_200_price_backfill.csv` | yes | stable | yes | pass | 2026-05-28 12:15:30 | Non-BTC single-asset historical replay price backfill. |
| `v08_historical_replay_non_btc_single_asset_200_findings` | result | `results/v08_historical_replay_non_btc_single_asset_200_findings.md` | yes | stable | yes | pass | 2026-05-28 12:18:56 | Non-BTC single-asset historical replay findings. |
| `v081_historical_source_usefulness_report` | result | `results/v081_historical_source_usefulness_report.md` | yes | stable | yes | pass | 2026-05-28 14:33:57 | Historical source usefulness report from v081 replay data. |
| `v081_source_readiness_report` | result | `results/v081_source_readiness_report.md` | yes | stable | yes | pass | 2026-05-28 14:33:57 | Source readiness report for token unlock, CEX listings, netflow, Hyperliquid, and usefulness. |
| `v081_token_unlock_calendar_quality_report` | result | `results/v081_token_unlock_calendar_quality_report.md` | yes | stable | yes | pass | 2026-05-28 14:15:00 | Token unlock calendar quality/readiness report. |
| `v081_token_unlock_import_report` | result | `results/v081_token_unlock_import_report.md` | yes | stable | yes | pass | 2026-05-28 14:18:50 | Token unlock import preview report. |
| `v081_cex_netflow_baseline_report` | result | `results/v081_cex_netflow_baseline_report.md` | yes | stable | yes | pass | 2026-05-28 22:24:32 | CEX netflow baseline readiness report. |
| `v081_hyperliquid_state_history_report` | result | `results/v081_hyperliquid_state_history_report.md` | yes | stable | yes | pass | 2026-05-28 14:33:57 | Hyperliquid state history readiness report. |
| `source_registry` | data | `data/source_registry.csv` | yes | stable | yes | pass | 2026-05-28 18:19:24 | Canonical registry of local intelligence sources, routes, shadow status, and evaluation status. |
| `shadow_events_raw` | data | `data/shadow_events_raw.csv` | no | fresh_24h | yes | warning | 2026-05-28 19:24:40 | Shadow-mode events captured for evaluation before live routing. |
| `tg_evidence_snippets` | data | `data/tg_evidence_snippets.csv` | no | fresh_24h | yes | warning | 2026-05-28 22:19:49 | Evidence snippets generated from backtest/source effectiveness for TG copy. |
| `source_registry_report` | result | `results/source_registry_report.md` | yes | fresh_24h | yes | fail | 2026-05-28 19:24:39 | Source registry coverage and consistency report. |
| `source_effectiveness_report` | result | `results/source_effectiveness_report.md` | yes | fresh_24h | yes | fail | 2026-05-28 19:24:39 | Source-level outcome effectiveness report. |
| `event_type_performance_matrix` | result | `results/event_type_performance_matrix.md` | yes | fresh_24h | yes | fail | 2026-05-28 19:24:39 | Event type/source subtype performance matrix from live and historical outcomes. |
| `event_type_performance_matrix_non_benchmark_alt` | result | `results/event_type_performance_matrix_non_benchmark_alt.md` | yes | fresh_24h | yes | fail | 2026-05-28 19:24:39 | Non-BTC/ETH non-macro alt event performance matrix. |
| `signal_decay_curve` | result | `results/signal_decay_curve.md` | yes | fresh_24h | yes | fail | 2026-05-28 19:24:39 | Signal horizon decay curve from live and historical outcomes. |
| `false_positive_analysis` | result | `results/false_positive_analysis.md` | yes | fresh_24h | yes | fail | 2026-05-28 19:24:39 | False-positive/noise analysis for live TG alert outcomes and radar decisions. |
| `v11_signal_policy` | data | `data/tg_signal_policy_v11.csv` | yes | fresh_24h | yes | fail | 2026-05-28 19:24:40 | v11 machine-readable TG routing policy from historical matrix and false-positive analysis. |
| `v11_signal_policy_report` | result | `results/v11_signal_policy_report.md` | yes | fresh_24h | yes | fail | 2026-05-28 19:24:40 | Readable v11 TG routing policy report. |
| `v12_signal_policy` | data | `data/tg_signal_policy_v12.csv` | yes | fresh_24h | yes | fail | 2026-05-28 19:50:07 | v12 strict contamination-aware TG routing policy. |
| `v12_boost_criteria_report` | result | `results/v12_boost_criteria_report.csv` | yes | fresh_24h | yes | fail | 2026-05-28 19:50:07 | Strict v12 boost/downrank/digest-only criteria report. |
| `v12_whale_position_contamination` | result | `results/v12_whale_position_contamination_report.md` | yes | fresh_24h | yes | fail | 2026-05-28 19:24:39 | Whale-position HYPE/single-asset/time-window contamination report. |
| `v12_hack_classification` | result | `results/v12_hack_classification_report.csv` | yes | fresh_24h | yes | fail | 2026-05-28 19:48:50 | Hack-security subtype validation report. |
| `v12_other_reclassification` | result | `results/v12_other_reclassification_report.csv` | no | stable | yes | pass | 2026-05-28 19:16:58 | Other taxonomy reclassification report. |
| `v13_price_in_report` | result | `results/v13_price_in_report.md` | yes | fresh_24h | yes | fail | 2026-05-28 19:38:38 | Pre-event price-in validation report for historical backfill rows. |
| `v13_other_quality_report` | result | `results/v13_other_quality_report.md` | yes | fresh_24h | yes | fail | 2026-05-28 19:40:27 | Quality grading report for uncategorized/other historical candidates. |
| `v13_hype_contamination_detail` | result | `results/v13_hype_contamination_report.md` | yes | fresh_24h | yes | fail | 2026-05-28 19:41:06 | HYPE whale-position burst/source/return contamination detail report. |
| `v13_whale_asset_contamination` | result | `results/v13_whale_asset_contamination_report.md` | yes | fresh_24h | yes | fail | 2026-05-28 19:45:49 | General whale-position asset concentration and burst contamination report. |
| `v13_source_identity_layers` | data | `data/source_identity_layers.csv` | yes | fresh_24h | yes | fail | 2026-05-28 19:45:49 | Three-layer source identity table for source family, channel, and reliability status. |
| `v13_regime_layer_report` | result | `results/v13_regime_layer_report.md` | yes | fresh_24h | yes | fail | 2026-05-28 19:47:10 | BTC regime-layer event performance report. |
| `v13_active_exploit_urgent_candidates` | result | `results/v13_active_exploit_urgent_candidates.md` | yes | fresh_24h | yes | fail | 2026-05-28 19:50:00 | Rare urgent-candidate report for active exploit events. |
| `v13_extended_alt_backtest_clean` | data | `data/backtest_v13_extended_alt_history_clean.csv` | yes | fresh_24h | yes | fail | 2026-05-28 20:05:55 | Extended non-benchmark alt historical backtest with archive flags. |
| `v13_extended_post_hype_removal_report` | result | `results/v13_extended_post_hype_removal_report.md` | yes | fresh_24h | yes | fail | 2026-05-28 20:05:55 | Extended post-HYPE-removal group statistics report. |
| `v13_rule_tightening_report` | result | `results/v13_rule_tightening_report.md` | yes | fresh_24h | yes | fail | 2026-05-28 19:55:16 | Strict candidate gate comparison report. |
| `v13_source_scores_extended` | data | `data/source_scores_v13_extended.csv` | yes | fresh_24h | yes | fail | 2026-05-28 20:06:10 | Source scores and throttle recommendations from extended replay. |
| `v13_extended_source_throttle_report` | result | `results/v13_extended_source_throttle_report.md` | yes | fresh_24h | yes | fail | 2026-05-28 20:06:10 | Source throttle report from extended replay. |
| `v13_extended_price_in_report` | result | `results/v13_extended_price_in_report.md` | yes | fresh_24h | yes | fail | 2026-05-28 20:11:00 | Extended sample pre-event price-in report. |
| `v13_extended_regime_layer_report` | result | `results/v13_extended_regime_layer_report.md` | yes | fresh_24h | yes | fail | 2026-05-28 20:08:53 | Extended sample BTC regime-layer report. |
| `v14_time_field_diagnosis` | result | `results/v14_time_field_diagnosis.md` | yes | fresh_24h | yes | fail | 2026-05-28 20:15:52 | Remote time-field diagnosis for historical export reliability. |
| `v14_webhook_split_source_scores` | data | `data/source_scores_v14_webhook_split.csv` | yes | fresh_24h | yes | fail | 2026-05-28 20:30:13 | Webhook subsource split and source-score table. |
| `v14_webhook_split_report` | result | `results/v14_webhook_split_report.md` | yes | fresh_24h | yes | fail | 2026-05-28 20:30:13 | Webhook subsource split report. |
| `v14_taxonomy_review_reclassified` | data | `data/taxonomy_review_reclassified.csv` | yes | fresh_24h | yes | fail | 2026-05-28 20:30:40 | Rule-based split of needs_taxonomy_review rows. |
| `v14_needs_taxonomy_review_report` | result | `results/v14_needs_taxonomy_review_report.md` | yes | fresh_24h | yes | fail | 2026-05-28 20:30:40 | Needs-taxonomy-review cleanup report. |
| `v14_etf_fund_flow_filtered` | data | `data/etf_fund_flow_filtered.csv` | yes | fresh_24h | yes | fail | 2026-05-28 21:04:42 | ETF/fund-flow rows filtered by amount, issuer, source, and context. |
| `v14_etf_fund_flow_filter_report` | result | `results/v14_etf_fund_flow_filter_report.md` | yes | fresh_24h | yes | fail | 2026-05-28 21:04:42 | ETF/fund-flow quality filter report. |
| `v14_flow_event_subtypes` | data | `data/v14_flow_event_subtypes.csv` | yes | fresh_24h | yes | fail | 2026-05-28 21:04:42 | Split mixed fund-flow rows into ETF, CEX netflow, institutional, and unclear subtypes. |
| `v14_flow_event_subtypes_report` | result | `results/v14_flow_event_subtypes_report.md` | yes | fresh_24h | yes | fail | 2026-05-28 21:04:42 | Readable flow subtype split report. |
| `v14_active_exploit_verified` | data | `data/active_exploit_verified.csv` | yes | fresh_24h | yes | fail | 2026-05-28 21:04:43 | Active exploit candidates with amount/context verification. |
| `v14_active_exploit_amount_verification_report` | result | `results/v14_active_exploit_amount_verification_report.md` | yes | fresh_24h | yes | fail | 2026-05-28 21:04:43 | Active exploit amount verification report. |
| `v14_short_price_in` | data | `data/v14_short_price_in.csv` | yes | fresh_24h | yes | fail | 2026-05-28 21:19:39 | 5m/15m/1h pre-event price-in checks. |
| `v14_upgrade_events` | data | `data/v14_upgrade_events.csv` | yes | fresh_24h | yes | fail | 2026-05-28 21:20:49 | Upgrade/fork publishability classification. |
| `v14_publishable_criteria` | config | `config/publishable_criteria.yaml` | yes | stable | yes | pass | 2026-05-28 21:59:49 | Minimum publishable-event criteria for Telegram routing. |
| `v14_routing_rules` | config | `config/routing_rules.yaml` | yes | stable | yes | pass | 2026-05-28 21:43:41 | Configurable watcher routing thresholds and priorities. |
| `v14_asset_tiers` | config | `config/asset_tiers.yaml` | yes | stable | yes | pass | 2026-05-28 22:36:35 | Asset tiers and thresholds for digest focus asset selection. |
| `v14_term_translations` | config | `config/term_translations.yaml` | yes | stable | yes | pass | 2026-05-28 22:36:35 | Plain-Chinese market term translations for TG reports. |
| `v14_alert_routing` | config | `config/alert_routing.yaml` | yes | stable | yes | pass | 2026-05-28 22:53:14 | Intraday radar versus scheduled digest routing thresholds. |
| `v14_publishable_criteria_eval` | data | `data/v14_publishable_criteria_eval.csv` | yes | fresh_24h | yes | fail | 2026-05-28 21:59:49 | Per-event evaluation against minimum publishable criteria. |
| `v14_publishable_golden_events` | data | `data/v14_publishable_golden_events.csv` | yes | stable | yes | pass | 2026-05-28 21:42:36 | Golden known publishable/non-publishable events for criteria validation. |
| `v14_security_events_normalized` | data | `data/security_events/security_events_normalized.csv` | yes | fresh_24h | yes | fail | 2026-05-28 21:28:01 | Normalized external security alert/address-risk events. |
| `v14_security_alert_ingest_summary` | result | `results/v14_security_alert_ingest_summary.csv` | yes | fresh_24h | yes | fail | 2026-05-28 21:28:01 | Security alert source ingest status summary. |
| `v14_etf_daily_flows_farside` | data | `data/etf_daily_flows_farside.csv` | yes | fresh_24h | yes | fail | 2026-05-28 21:44:43 | Farside BTC ETF daily flow table normalized locally. |
| `v14_eth_etf_flows_farside` | data | `data/eth_etf_flows_farside.csv` | no | fresh_24h | yes | warning | 2026-05-28 22:52:39 | Optional Farside ETH ETF daily flow table; may be empty if blocked by Cloudflare. |
| `v14_etf_daily_digest` | result | `results/v14_etf_daily_digest.md` | yes | fresh_24h | yes | fail | 2026-05-28 21:44:43 | BTC ETF daily flow digest candidate. |
| `v14_eth_etf_daily_digest` | result | `results/v14_eth_etf_daily_digest.md` | no | fresh_24h | yes | warning | 2026-05-28 22:52:39 | Optional ETH ETF daily flow digest candidate. |
| `v14_first_hand_publish_candidates` | data | `data/v14_first_hand_publish_candidates.csv` | yes | fresh_24h | yes | fail | 2026-05-28 21:44:44 | First-hand watcher publish route candidates. |
| `v14_first_hand_publish_candidates_report` | result | `results/v14_first_hand_publish_candidates.md` | yes | fresh_24h | yes | fail | 2026-05-28 21:44:44 | First-hand watcher routing report. |
| `v14_publishable_criteria_validation` | result | `results/v14_publishable_criteria_validation.csv` | yes | fresh_24h | yes | fail | 2026-05-28 21:59:49 | Golden-event validation for publishable criteria. |
| `v14_e2e_publish_preview` | result | `results/v14_e2e_publish_preview.md` | yes | fresh_24h | yes | fail | 2026-05-28 21:44:44 | Local end-to-end publish preview without Telegram send. |
| `v14_hyperliquid_snapshot_card` | result | `results/v14_hyperliquid_snapshot_card.md` | yes | fresh_24h | yes | fail | 2026-05-28 21:44:44 | Hyperliquid static market-structure background card. |
| `v14_market_state_snapshot` | result | `results/v14_market_state_snapshot.md` | yes | fresh_24h | yes | fail | 2026-05-29 12:32:41 | Public Binance price, volume, open-interest, funding, and crowding market-state snapshot. |
| `v14_focus_assets` | result | `results/v14_focus_assets.csv` | yes | fresh_24h | yes | fail | 2026-05-29 12:32:44 | Focus assets selected from tier rules and market-state thresholds. |
| `v14_price_oi_quadrant` | result | `results/v14_price_oi_quadrant.csv` | yes | fresh_24h | yes | fail | 2026-05-29 12:32:44 | Plain-Chinese price/open-interest quadrant classification. |
| `v14_etf_plain_summary` | result | `results/v14_etf_plain_summary.md` | yes | fresh_24h | yes | fail | 2026-05-29 12:32:46 | Plain-Chinese ETF flow first-screen summary. |
| `v14_etf_concentration_interpretation` | result | `results/v14_etf_concentration_interpretation.txt` | yes | fresh_24h | yes | fail | 2026-05-29 12:32:46 | ETF concentration-change plain-Chinese interpretation. |
| `v14_market_alert_headline` | result | `results/v14_market_alert_headline.txt` | yes | fresh_24h | yes | fail | 2026-05-29 12:32:44 | One-line abnormality headline for TG market-state digest. |
| `v14_funding_rate_percentiles` | data | `data/funding_rate/funding_rate_percentiles.csv` | yes | fresh_24h | yes | fail | 2026-05-29 12:32:46 | Binance USD-M funding-rate historical samples for percentile context. |
| `v14_oi_percentiles` | data | `data/oi/oi_percentiles.csv` | yes | fresh_24h | yes | fail | 2026-05-29 12:32:46 | Binance USD-M open-interest historical samples for percentile context. |
| `v14_derivatives_history_percentiles` | result | `results/v14_derivatives_history_percentiles.md` | yes | fresh_24h | yes | fail | 2026-05-29 12:32:46 | Funding-rate and OI historical percentile report. |
| `v15_percentile_alerts_json` | result | `results/v15_percentile_alerts.json` | yes | fresh_24h | yes | fail | 2026-05-29 12:32:46 | Layered percentile alert buckets for TG first screen, today-watch, radar, and digest context. |
| `v15_percentile_alerts_report` | result | `results/v15_percentile_alerts.md` | yes | fresh_24h | yes | fail | 2026-05-29 12:32:46 | Readable layered percentile alert report. |
| `v15_percentile_alerts_summary` | result | `results/v15_percentile_alerts_summary.csv` | yes | fresh_24h | yes | fail | 2026-05-29 12:32:46 | Layered percentile alert generation summary. |
| `v15_hyperliquid_market_meta_snapshot` | data | `data/hyperliquid/market_meta_snapshot.csv` | yes | fresh_24h | yes | fail | 2026-05-29 12:25:14 | Hyperliquid official public perp market metadata snapshot. |
| `v15_hyperliquid_market_meta_history` | data | `data/hyperliquid/market_meta_history.csv` | yes | fresh_24h | yes | fail | 2026-05-29 12:25:14 | Append-only Hyperliquid public market metadata history. |
| `v15_hyperliquid_market_meta_card` | result | `results/v15_hyperliquid_market_meta_card.md` | yes | fresh_24h | yes | fail | 2026-05-29 12:25:19 | Readable Hyperliquid official market-structure card. |
| `v15_hyperliquid_market_meta_summary` | result | `results/v15_hyperliquid_market_meta_summary.csv` | yes | fresh_24h | yes | fail | 2026-05-29 12:25:14 | Hyperliquid official market metadata fetch summary. |
| `v15_hyperliquid_liquidation_wall` | result | `results/v15_hyperliquid_liquidation_wall.md` | yes | fresh_24h | yes | fail | 2026-05-29 14:16:05 | Monitored Hyperliquid large-position liquidation-wall context. |
| `v15_hyperliquid_liquidation_wall_summary` | result | `results/v15_hyperliquid_liquidation_wall_summary.csv` | yes | fresh_24h | yes | fail | 2026-05-29 14:16:05 | Hyperliquid liquidation-wall route counts. |
| `v14_market_state_first_screen` | result | `results/v14_market_state_first_screen.md` | yes | fresh_24h | yes | fail | 2026-05-29 12:32:46 | Concise first-screen TG market-state block. |
| `v14_prioritized_events` | result | `results/v14_prioritized_events.md` | yes | fresh_24h | yes | fail | 2026-05-29 12:32:42 | Auditable top-watch versus other-dynamic event priority report. |
| `v14_today_focus_events` | result | `results/v14_today_focus_events.csv` | yes | fresh_24h | yes | fail | 2026-05-29 12:32:42 | Events admitted into today's top-watch section after dynamic thresholds. |
| `v14_other_events` | result | `results/v14_other_events.csv` | yes | fresh_24h | yes | fail | 2026-05-29 12:32:42 | Events relegated to other-dynamic section after dynamic thresholds. |
| `v14_prefilter_results` | data | `data/v14_prefilter_results.csv` | yes | fresh_24h | yes | fail | 2026-05-28 21:19:49 | Hard PreFilter results before Composer and Publisher. |
| `v14_prefilter_report` | result | `results/v14_prefilter_report.md` | yes | fresh_24h | yes | fail | 2026-05-28 21:19:49 | Readable hard PreFilter block report. |
| `v14_composer_scores` | data | `data/v14_composer_scores.csv` | yes | fresh_24h | yes | fail | 2026-05-28 21:19:49 | Auditable five-stage Composer scores for historical candidates. |
| `v14_composer_scores_report` | result | `results/v14_composer_scores_report.md` | yes | fresh_24h | yes | fail | 2026-05-28 21:19:49 | Readable Composer five-stage score report. |
| `v14_publish_policy_candidates` | data | `data/v14_publish_policy_candidates.csv` | yes | fresh_24h | yes | fail | 2026-05-28 22:00:31 | Claude-directed block/digest/interrupt publishing policy decisions. |
| `v14_publish_policy_report` | result | `results/v14_publish_policy_report.md` | yes | fresh_24h | yes | fail | 2026-05-28 22:00:31 | Readable v14 publishing policy report. |
| `v14_digest_preview` | result | `results/v14_digest_preview.md` | yes | fresh_24h | yes | fail | 2026-05-28 22:00:31 | Strict morning/evening digest preview using quality-gated rows only. |
| `v08_non_benchmark_alt_events` | data | `data/events_v08_historical_replay_non_benchmark_alt_50.csv` | yes | stable | yes | pass | 2026-05-28 18:50:26 | Non-benchmark alt historical replay event sample. |
| `v08_non_benchmark_alt_backfill` | result | `results/v08_historical_replay_non_benchmark_alt_50_price_backfill.csv` | yes | stable | yes | pass | 2026-05-28 18:50:38 | Non-benchmark alt historical replay price backfill. |
| `v08_non_benchmark_alt_quality` | result | `results/v08_historical_replay_non_benchmark_alt_50_quality_report.csv` | yes | stable | yes | pass | 2026-05-28 18:50:39 | Non-benchmark alt historical replay quality report. |
| `v08_non_benchmark_alt_findings` | result | `results/v08_historical_replay_non_benchmark_alt_50_findings.md` | yes | stable | yes | pass | 2026-05-28 18:50:40 | Non-benchmark alt historical replay findings. |
| `source_adapter_validation_report` | result | `results/source_adapter_validation_report.md` | yes | fresh_24h | yes | fail | 2026-05-28 19:24:40 | Normalized source adapter output validation report. |
| `shadow_source_evaluation_report` | result | `results/shadow_source_evaluation_report.md` | yes | fresh_24h | yes | fail | 2026-05-28 19:24:40 | Shadow-mode source evaluation report. |
| `tg_evidence_snippets_preview` | result | `results/tg_evidence_snippets.md` | no | fresh_24h | yes | warning | 2026-05-28 22:19:49 | Readable preview of evidence snippets for TG cards and digests. |
| `llm_usage_report` | result | `results/llm_usage_report.md` | yes | fresh_24h | yes | fail | 2026-05-28 19:24:40 | LLM usage and cost-control report. |
| `v11_readiness_report` | result | `results/v11_readiness_report.md` | yes | fresh_24h | yes | fail | 2026-05-28 19:24:41 | v11 source-quality-first readiness report. |
| `v11_digest_preview` | result | `results/v11_tg_custom_digest_preview.md` | no | fresh_24h | yes | warning | 2026-05-28 18:27:33 | Readable TG digest preview after evidence-snippet upgrade. |
| `source_adapter_schema` | doc | `docs/SOURCE_ADAPTER_SCHEMA.md` | yes | stable | yes | pass | 2026-05-28 18:18:24 | Normalized source adapter schema used by watcher/news/calendar sources. |
| `v11_external_reference_upgrade_plan` | doc | `docs/V11_EXTERNAL_REFERENCE_UPGRADE_PLAN_CN.md` | yes | stable | yes | pass | 2026-05-28 18:09:03 | Accepted v11 upgrade plan derived from external references and Claude review. |
| `source_registry_report_script` | script | `scripts/build_source_registry_report.py` | yes | stable | yes | pass | 2026-05-28 18:14:49 | Build source registry coverage and consistency report. |
| `source_effectiveness_report_script` | script | `scripts/build_source_effectiveness_report.py` | yes | stable | yes | pass | 2026-05-28 18:15:29 | Build source effectiveness report from ledger/outcomes/registry. |
| `event_type_performance_matrix_script` | script | `scripts/build_event_type_performance_matrix.py` | yes | stable | yes | pass | 2026-05-28 18:17:29 | Build event type and source subtype performance matrix. |
| `signal_decay_curve_script` | script | `scripts/build_signal_decay_curve.py` | yes | stable | yes | pass | 2026-05-28 18:17:41 | Build horizon-level signal decay curve. |
| `false_positive_analysis_script` | script | `scripts/build_false_positive_analysis.py` | yes | stable | yes | pass | 2026-05-28 18:33:11 | Build false-positive/noise analysis from TG outcomes and radar decision logs. |
| `v11_signal_policy_script` | script | `scripts/build_v11_signal_policy.py` | yes | stable | yes | pass | 2026-05-28 18:51:02 | Build v11 machine-readable routing policy from historical matrix and false-positive analysis. |
| `validate_whale_position_contamination_script` | script | `scripts/validate_whale_position_contamination.py` | yes | stable | yes | pass | 2026-05-28 19:15:28 | Validate contamination in whale-position samples. |
| `reclassify_other_with_new_taxonomy_script` | script | `scripts/reclassify_other_with_new_taxonomy.py` | yes | stable | yes | pass | 2026-05-28 19:15:51 | Reclassify candidate_event_type=other with v12 taxonomy rules. |
| `validate_hack_classification_script` | script | `scripts/validate_hack_classification.py` | yes | stable | yes | pass | 2026-05-28 19:48:33 | Split hack_security rows into active exploit, disclosure, recovery, enforcement, pause, and unclear buckets. |
| `apply_boost_criteria_v12_script` | script | `scripts/apply_boost_criteria_v12.py` | yes | stable | yes | pass | 2026-05-28 19:18:49 | Apply strict v12 contamination-aware routing policy. |
| `validate_price_in_effect_script` | script | `scripts/validate_price_in_effect.py` | yes | stable | yes | pass | 2026-05-28 19:35:46 | Validate pre-event price-in effects against post-event abnormal returns. |
| `grade_other_quality_script` | script | `scripts/grade_other_quality.py` | yes | stable | yes | pass | 2026-05-28 19:40:22 | Grade uncategorized/other candidate quality before further taxonomy work. |
| `analyze_hype_contamination_detail_script` | script | `scripts/analyze_hype_contamination_detail.py` | yes | stable | yes | pass | 2026-05-28 19:41:00 | Analyze HYPE-specific whale-position contamination patterns. |
| `analyze_whale_position_asset_contamination_script` | script | `scripts/analyze_whale_position_asset_contamination.py` | yes | stable | yes | pass | 2026-05-28 19:45:41 | Analyze general whale-position single-asset and short-window contamination. |
| `build_source_identity_layers_script` | script | `scripts/build_source_identity_layers.py` | yes | stable | yes | pass | 2026-05-28 19:45:41 | Build three-layer source identity and reliability table. |
| `build_regime_layer_report_script` | script | `scripts/build_regime_layer_report.py` | yes | stable | yes | pass | 2026-05-28 19:45:41 | Build BTC regime-layer report for historical event performance. |
| `build_active_exploit_urgent_candidates_script` | script | `scripts/build_active_exploit_urgent_candidates.py` | yes | stable | yes | pass | 2026-05-28 19:49:54 | Build rare urgent-candidate list for active exploit events. |
| `archive_hype_and_recompute_stats_script` | script | `scripts/archive_hype_and_recompute_stats.py` | yes | stable | yes | pass | 2026-05-28 19:55:10 | Archive HYPE whale burst contamination and recompute group statistics. |
| `tighten_candidate_identification_rules_script` | script | `scripts/tighten_candidate_identification_rules.py` | yes | stable | yes | pass | 2026-05-28 19:55:10 | Apply stricter candidate gates to reduce garbage candidates. |
| `score_and_throttle_sources_script` | script | `scripts/score_and_throttle_sources.py` | yes | stable | yes | pass | 2026-05-28 19:55:10 | Score sources and derive source-level throttle rules. |
| `diagnose_remote_time_fields_script` | script | `scripts/diagnose_remote_time_fields.py` | yes | stable | yes | pass | 2026-05-28 20:15:37 | Diagnose remote historical time-field coverage. |
| `export_real_news_older_v2_script` | script | `scripts/export_real_news_older_v2.py` | yes | stable | yes | pass | 2026-05-28 20:21:22 | Explicit-time-field older real-news exporter. |
| `split_webhook_subsources_script` | script | `scripts/split_webhook_subsources.py` | yes | stable | yes | pass | 2026-05-28 20:30:00 | Split webhook into subsources and score them separately. |
| `analyze_needs_taxonomy_review_script` | script | `scripts/analyze_needs_taxonomy_review.py` | yes | stable | yes | pass | 2026-05-28 20:30:34 | Rule-split needs_taxonomy_review rows into concrete buckets. |
| `filter_etf_fund_flow_script` | script | `scripts/filter_etf_fund_flow.py` | yes | stable | yes | pass | 2026-05-28 21:04:04 | Filter ETF/fund-flow rows for digest eligibility. |
| `split_flow_event_subtypes_script` | script | `scripts/split_flow_event_subtypes.py` | yes | stable | yes | pass | 2026-05-28 21:02:37 | Split ETF/fund-flow versus CEX netflow and institutional flow rows. |
| `verify_exploit_amounts_script` | script | `scripts/verify_exploit_amounts.py` | yes | stable | yes | pass | 2026-05-28 21:04:34 | Verify active-exploit amount and context before urgent eligibility. |
| `build_v14_short_price_in_script` | script | `scripts/build_v14_short_price_in.py` | yes | stable | yes | pass | 2026-05-28 21:17:19 | Build 5m/15m/1h pre-event price-in checks. |
| `classify_v14_upgrade_events_script` | script | `scripts/classify_v14_upgrade_events.py` | yes | stable | yes | pass | 2026-05-28 21:20:39 | Classify upgrade/fork events into digest/background/block. |
| `define_publishable_event_criteria_script` | script | `scripts/define_publishable_event_criteria.py` | yes | stable | yes | pass | 2026-05-28 21:59:43 | Write and evaluate minimum publishable event criteria. |
| `ingest_security_alerts_script` | script | `scripts/ingest_security_alerts.py` | yes | stable | yes | pass | 2026-05-28 21:27:52 | Ingest external security alert sources into normalized local CSV. |
| `build_etf_daily_digest_script` | script | `scripts/build_etf_daily_digest.py` | yes | stable | yes | pass | 2026-05-28 22:52:47 | Build daily BTC ETF flow digest from Farside public table. |
| `build_first_hand_publish_candidates_script` | script | `scripts/build_first_hand_publish_candidates.py` | yes | stable | yes | pass | 2026-05-28 21:43:59 | Route first-hand watcher alerts into publish/archive channels. |
| `validate_publishable_criteria_script` | script | `scripts/validate_publishable_criteria.py` | yes | stable | yes | pass | 2026-05-28 21:42:56 | Validate publishable criteria against golden known events. |
| `test_end_to_end_publish_script` | script | `scripts/test_end_to_end_publish.py` | yes | stable | yes | pass | 2026-05-28 21:44:34 | Build local publish preview from current candidates without sending Telegram. |
| `aggregate_hyperliquid_snapshot_script` | script | `scripts/aggregate_hyperliquid_snapshot.py` | yes | stable | yes | pass | 2026-05-28 21:44:20 | Aggregate Hyperliquid position snapshots into background digest card. |
| `build_market_state_snapshot_script` | script | `scripts/build_market_state_snapshot.py` | yes | stable | yes | pass | 2026-05-29 12:10:45 | Build public Binance market-state snapshot for TG digests. |
| `select_focus_assets_script` | script | `scripts/market/select_focus_assets.py` | yes | stable | yes | pass | 2026-05-28 22:36:35 | Select digest focus assets from asset tiers and market-state thresholds. |
| `classify_price_oi_quadrant_script` | script | `scripts/market/classify_price_oi_quadrant.py` | yes | stable | yes | pass | 2026-05-28 22:36:35 | Classify price/open-interest quadrant explanations. |
| `generate_etf_summary_script` | script | `scripts/reporting/generate_etf_summary.py` | yes | stable | yes | pass | 2026-05-28 22:51:12 | Render ETF flow context into a concise first-screen block. |
| `generate_alert_headline_script` | script | `scripts/reporting/generate_alert_headline.py` | yes | stable | yes | pass | 2026-05-28 22:46:30 | Generate one-line abnormality headline for TG market-state digest. |
| `build_derivatives_history_percentiles_script` | script | `scripts/market/build_derivatives_history_percentiles.py` | yes | stable | yes | pass | 2026-05-28 22:55:40 | Fetch Binance USD-M funding/OI history and compute percentile context. |
| `generate_percentile_alerts_script` | script | `scripts/market/generate_percentile_alerts.py` | yes | stable | yes | pass | 2026-05-29 12:21:11 | Convert historical derivative percentiles into layered TG alert placement buckets. |
| `hyperliquid_market_meta_fetcher` | script | `scripts/hyperliquid/fetch_market_meta.py` | yes | stable | yes | pass | 2026-05-29 12:16:08 | Fetch Hyperliquid official public perp market metadata via metaAndAssetCtxs. |
| `hyperliquid_market_meta_card` | script | `scripts/hyperliquid/generate_market_meta_card.py` | yes | stable | yes | pass | 2026-05-29 12:21:56 | Render Hyperliquid official market metadata into a concise card. |
| `hyperliquid_liquidation_wall` | script | `scripts/hyperliquid/generate_liquidation_wall.py` | yes | stable | yes | pass | 2026-05-29 14:16:05 | Render monitored Hyperliquid large-position liquidation-wall context. |
| `generate_market_state_summary_script` | script | `scripts/reporting/generate_market_state_summary.py` | yes | stable | yes | pass | 2026-05-29 12:26:20 | Render concise market-state first screen for TG digest. |
| `prioritize_events_script` | script | `scripts/events/prioritize_events.py` | yes | stable | yes | pass | 2026-05-28 22:46:55 | Prioritize TG digest events into top-watch and other-dynamic buckets. |
| `build_v14_prefilter_script` | script | `scripts/build_v14_prefilter.py` | yes | stable | yes | pass | 2026-05-28 21:10:54 | Build hard PreFilter output before Composer and Publisher. |
| `build_v14_composer_scores_script` | script | `scripts/build_v14_composer_scores.py` | yes | stable | yes | pass | 2026-05-28 21:05:24 | Build auditable five-stage Composer scores. |
| `apply_v14_publish_policy_script` | script | `scripts/apply_v14_publish_policy.py` | yes | stable | yes | pass | 2026-05-28 21:25:12 | Apply Claude-directed block/digest/interrupt publishing policy. |
| `build_v14_digest_preview_script` | script | `scripts/build_v14_digest_preview.py` | yes | stable | yes | pass | 2026-05-28 21:20:59 | Build strict v14 morning/evening digest preview. |
| `source_adapter_validation_script` | script | `scripts/validate_source_adapter_outputs.py` | yes | stable | yes | pass | 2026-05-28 18:18:50 | Validate normalized source adapter outputs against schema and registry. |
| `shadow_source_evaluation_script` | script | `scripts/run_shadow_source_evaluation.py` | yes | stable | yes | pass | 2026-05-28 18:20:09 | Extract and summarize shadow-mode source events. |
| `tg_evidence_snippet_script` | script | `scripts/render_tg_evidence_snippet.py` | yes | stable | yes | pass | 2026-05-28 22:19:36 | Render evidence snippets from source effectiveness and event performance data. |
| `llm_usage_report_script` | script | `scripts/build_llm_usage_report.py` | yes | stable | yes | pass | 2026-05-28 18:21:33 | Build LLM usage and estimated cost reports. |
| `v11_readiness_report_script` | script | `scripts/build_v11_readiness_report.py` | yes | stable | yes | pass | 2026-05-28 18:51:19 | Build v11 source-quality-first readiness report. |
| `tg_test_sender_script` | script | `scripts/send_tg_draft_test.py` | yes | stable | yes | pass | 2026-05-27 18:43:10 | Manual dry-run/send helper for TG draft testing. |
| `local_environment_script` | script | `scripts/check_local_environment.py` | yes | stable | yes | pass | 2026-05-27 16:08:43 | Environment checker. |
| `secret_scan_script` | script | `scripts/check_secret_leaks.py` | yes | stable | yes | pass | 2026-05-27 17:55:45 | Secret scanner. |
| `local_secret_loader` | script | `scripts/load_local_secrets.ps1` | yes | stable | yes | pass | 2026-05-27 17:55:33 | Loads ignored local secrets into the current PowerShell process. |
| `command_registry_script` | script | `scripts/build_command_registry.py` | yes | stable | yes | pass | 2026-05-29 12:24:49 | Command registry builder. |
| `review_actions_script` | script | `scripts/build_project_review_actions.py` | yes | stable | yes | pass | 2026-05-27 17:19:04 | Review action builder. |
| `cursor_prompt_script` | script | `scripts/generate_cursor_prompt.py` | yes | stable | yes | pass | 2026-05-27 16:30:29 | Cursor prompt generator. |
| `claude_prompt_script` | script | `scripts/generate_claude_question_prompt.py` | yes | stable | yes | pass | 2026-05-27 15:45:16 | Claude prompt generator. |
| `claude_query_script` | script | `scripts/query_claude_next.py` | yes | stable | yes | pass | 2026-05-28 18:21:13 | Claude OpenRouter query wrapper. |
