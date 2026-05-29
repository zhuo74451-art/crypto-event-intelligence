import argparse
from datetime import datetime
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]


ARTIFACTS = [
    ("project_os", "project_root_rules", "AGENTS.md", "yes", "stable", "Local project rules."),
    ("project_os", "python_requirements", "requirements.txt", "yes", "stable", "Minimal local runtime dependencies."),
    ("project_os", "project_state", "docs/PROJECT_STATE.md", "yes", "fresh_24h", "Current local project memory."),
    ("project_os", "project_dashboard", "docs/PROJECT_DASHBOARD.md", "yes", "fresh_24h", "Current local dashboard."),
    ("project_os", "validation_checklist", "docs/VALIDATION_CHECKLIST.md", "yes", "stable", "Operator validation checklist."),
    ("project_os", "command_registry_doc", "docs/COMMAND_REGISTRY.md", "yes", "fresh_24h", "Runnable command inventory."),
    ("project_os", "artifact_manifest_doc", "docs/ARTIFACT_MANIFEST.md", "no", "fresh_24h", "This generated manifest."),
    ("project_os", "project_review_actions_doc", "docs/PROJECT_REVIEW_ACTIONS.md", "yes", "fresh_24h", "Dashboard review action queue."),
    ("project_os", "decisions_doc", "docs/DECISIONS.md", "yes", "stable", "Accepted direction decisions."),
    ("project_os", "mvp_timeline_doc", "docs/MVP_TIMELINE.md", "yes", "stable", "Current MVP definition and timeline estimate."),
    ("project_os", "ai_cost_control_policy", "docs/AI_COST_CONTROL_POLICY.md", "yes", "stable", "AI/Claude routing and spend-control policy."),
    ("project_os", "secret_setup_doc", "docs/SECRET_SETUP.md", "yes", "stable", "Local secret setup instructions."),
    ("project_os", "gitignore", ".gitignore", "yes", "stable", "Ignore local secret files and runtime noise."),
    ("config", "secret_template", "config/secrets.example.ps1", "yes", "stable", "Local secret template with placeholders only."),
    ("agent_handoff", "cursor_prompt", "docs/CURSOR_NEXT_PROMPT.md", "yes", "fresh_24h", "File-based Cursor handoff."),
    ("agent_handoff", "cursor_backlog", "docs/CURSOR_TASK_BACKLOG.md", "yes", "stable", "Cursor task backlog."),
    ("agent_handoff", "claude_prompt", "docs/CLAUDE_NEXT_PROMPT.md", "yes", "fresh_24h", "Current Claude consultation prompt."),
    ("agent_handoff", "claude_question_backlog", "docs/CLAUDE_QUESTION_BACKLOG.md", "yes", "stable", "Architecture question backlog."),
    ("agent_handoff", "claude_response_index_doc", "docs/CLAUDE_RESPONSE_INDEX.md", "yes", "fresh_24h", "Local Claude response index."),
    ("agent_handoff", "claude_decision_review_doc", "docs/CLAUDE_DECISION_REVIEW.md", "yes", "fresh_24h", "Claude recommendation review queue."),
    ("data", "symbol_map", "data/symbol_map.csv", "yes", "stable", "Asset to market symbol map."),
    ("data", "entity_dictionary", "data/entity_dictionary.csv", "yes", "stable", "Entity dictionary for intake rules."),
    ("data", "source_timezone_rules", "data/source_timezone_rules.csv", "yes", "stable", "Source time-zone assumptions."),
    ("data", "older500_raw_news", "data/raw_news_real_500_older.csv", "yes", "stable", "Older real-news source export."),
    ("data", "older500_candidates", "data/event_candidates_real_500_older_review.csv", "yes", "stable", "Older candidate import output."),
    ("data", "v06_relevance_scored", "data/event_candidates_v06_relevance_scored.csv", "yes", "stable", "v0.6 scored intake output."),
    ("data", "v06_manual_label_sheet", "data/v06_manual_label_sheet.csv", "yes", "stable", "AI-first review sheet."),
    ("data", "v06_other_review_classified", "data/event_candidates_v06_other_review_classified.csv", "no", "stable", "Rule-based split of the other_review bucket."),
    ("data", "project_review_action_queue", "data/project_review_action_queue.csv", "yes", "fresh_24h", "Generated dashboard action queue."),
    ("data", "claude_decision_queue", "data/claude_decision_review_queue.csv", "yes", "fresh_24h", "Generated Claude decision queue."),
    ("results", "tg_pilot_gate", "results/v06_tg_pilot_gate_report.md", "yes", "fresh_24h", "TG draft pilot safety gate."),
    ("results", "project_os_validation_report", "results/project_os_validation_report.md", "yes", "stable", "Consolidated validation report."),
    ("results", "project_os_validation_summary", "results/project_os_validation_summary.csv", "yes", "stable", "Consolidated validation summary."),
    ("results", "local_environment_summary", "results/local_environment_summary.csv", "yes", "fresh_24h", "Local runtime check summary."),
    ("results", "secret_leak_summary", "results/secret_leak_summary.csv", "yes", "fresh_24h", "Secret scan summary."),
    ("results", "command_registry_summary", "results/command_registry_summary.csv", "yes", "fresh_24h", "Command registry summary."),
    ("results", "project_review_action_summary", "results/project_review_action_summary.csv", "yes", "fresh_24h", "Review action summary."),
    ("results", "project_dashboard_metrics", "results/project_dashboard_metrics.csv", "yes", "fresh_24h", "Dashboard metrics CSV."),
    ("results", "v043_backfill", "results/v043_older_mature50_event_price_backfill.csv", "yes", "stable", "Historical mature50 backfill."),
    ("results", "v043_quality", "results/v043_older_mature50_event_quality_report.csv", "yes", "stable", "Historical mature50 quality report."),
    ("results", "time_provenance_summary", "results/v043_time_provenance_summary.csv", "yes", "stable", "Time provenance summary."),
    ("results", "v043_selection_v06_summary", "results/v043_selection_vs_v06_relevance_summary.csv", "yes", "fresh_24h", "v043 versus v0.6 relevance audit summary."),
    ("results", "v043_selection_v06_breakdown", "results/v043_selection_vs_v06_discard_breakdown.csv", "yes", "fresh_24h", "Discard reason breakdown for historical v043 selection."),
    ("results", "v043_selection_v06_impact", "results/v043_selection_vs_v06_event_type_impact.csv", "yes", "fresh_24h", "Event-type impact of v0.6 discard decisions."),
    ("results", "v06_low_risk_preview_backfill", "results/v06_clean_low_risk_preview_event_price_backfill.csv", "no", "stable", "Optional v0.6 low-risk preview sanity-check backfill."),
    ("results", "v06_low_risk_preview_quality", "results/v06_clean_low_risk_preview_event_quality_report.csv", "no", "stable", "Optional v0.6 low-risk preview quality report."),
    ("results", "v06_low_risk_preview_findings", "results/v06_clean_low_risk_preview_backtest_findings.md", "no", "stable", "Optional v0.6 low-risk preview findings."),
    ("data", "tg_drafts_private_pilot", "data/tg_drafts_v06_private_pilot.csv", "no", "stable", "Local TG private-pilot draft queue; no auto-send."),
    ("data", "tg_drafts_private_pilot_ai_reviewed", "data/tg_drafts_v06_private_pilot_ai_reviewed.csv", "no", "stable", "AI-reviewed local TG private-pilot draft queue."),
    ("data", "tg_prefilter_pass", "data/event_candidates_v06_tg_prefilter_pass.csv", "no", "stable", "Local pre-Claude TG candidate prefilter pass set."),
    ("data", "tg_prefilter_rejects", "data/event_candidates_v06_tg_prefilter_rejects.csv", "no", "stable", "Local pre-Claude TG candidate prefilter rejects."),
    ("data", "tg_approved_pool", "data/tg_drafts_v06_approved_pool.csv", "no", "stable", "Approved-only local TG draft pool."),
    ("data", "tg_draft_review_packet", "data/tg_draft_review_packet.csv", "no", "stable", "Compact local draft review packet."),
    ("results", "tg_drafts_private_pilot_preview", "results/tg_drafts_v06_private_pilot.md", "no", "stable", "Readable preview of local TG drafts."),
    ("results", "tg_draft_review_packet_md", "results/tg_draft_review_packet.md", "no", "stable", "Readable compact local draft review packet."),
    ("results", "tg_draft_feedback_summary", "results/tg_draft_feedback_summary.csv", "no", "stable", "Local private-pilot draft feedback summary."),
    ("results", "tg_draft_ai_review_summary", "results/tg_draft_ai_review_summary.csv", "no", "stable", "AI-review summary for local TG private-pilot drafts."),
    ("results", "tg_prefilter_summary", "results/tg_draft_prefilter_summary.csv", "no", "stable", "Local pre-Claude TG candidate prefilter summary."),
    ("results", "tg_approved_pool_summary", "results/tg_draft_approved_pool_summary.csv", "no", "stable", "Approved-only local TG draft pool summary."),
    ("results", "tg_draft_validation_summary", "results/tg_draft_validation_summary.csv", "no", "stable", "Local private-pilot draft safety validation summary."),
    ("results", "daily_private_pilot_summary", "results/daily_private_pilot_summary.csv", "no", "stable", "One-row daily private-pilot operational summary."),
    ("results", "daily_private_pilot_report", "results/daily_private_pilot_report.md", "no", "stable", "One-page daily private-pilot operational report."),
    ("results", "tg_draft_rule_improvement_summary", "results/tg_draft_rule_improvement_summary.csv", "no", "stable", "Summary of AI-rejected draft rule improvement candidates."),
    ("results", "tg_draft_rule_improvement_report", "results/tg_draft_rule_improvement_report.md", "no", "stable", "AI-rejected draft rule improvement report."),
    ("data", "v07_watchlist_addresses", "data/watchlist_addresses.csv", "yes", "stable", "v0.7 first-hand watcher address watchlist."),
    ("data", "v07_stablecoin_watchlist", "data/stablecoin_watchlist.csv", "yes", "stable", "v0.7 stablecoin mint/burn watchlist."),
    ("data", "v07_hyperliquid_watchlist", "data/hyperliquid_watchlist.csv", "yes", "stable", "v0.7 Hyperliquid perp-position watchlist."),
    ("data", "v07_watcher_alerts_raw", "data/watcher_alerts_raw.csv", "no", "stable", "Normalized first-hand watcher alerts."),
    ("data", "v07_hyperliquid_position_alerts", "data/watcher_alerts_hyperliquid_positions.csv", "no", "stable", "Raw Hyperliquid large-position watcher alerts."),
    ("data", "v07_watcher_events_raw", "data/watcher_events_raw.csv", "no", "stable", "Watcher alerts converted to event schema."),
    ("data", "v07_watcher_tg_drafts", "data/tg_drafts_v07_watcher_private_pilot.csv", "no", "stable", "Local TG draft preview for first-hand watcher alerts."),
    ("results", "v07_watchlist_validation_summary", "results/v07_watchlist_validation_summary.csv", "yes", "fresh_24h", "v0.7 watchlist validation summary."),
    ("results", "v07_watcher_run_summary", "results/v07_first_hand_watcher_run_summary.csv", "no", "stable", "v0.7 first-hand watcher run summary."),
    ("results", "v07_watcher_daily_report", "results/v07_watcher_daily_report.md", "no", "stable", "Readable daily report for first-hand watcher alerts."),
    ("results", "v07_watcher_tg_validation_summary", "results/tg_drafts_v07_watcher_validation_summary.csv", "no", "stable", "TG draft validation summary for watcher alerts."),
    ("results", "v07_tg_live_monitor_summary", "results/v07_tg_live_monitor_summary.csv", "no", "fresh_24h", "Live TG watcher monitor runtime summary."),
    ("data", "v08_tg_send_time_policy", "config/tg_send_time_policy.csv", "yes", "stable", "China-time flexible TG send timing policy."),
    ("data", "v08_tg_digest_sent_state", "data/tg_digest_sent_state.csv", "no", "stable", "Sent-state dedupe for scheduled TG digests."),
    ("data", "v08_cex_netflow_baseline_state", "data/cex_netflow_baseline_state.csv", "no", "stable", "Rolling baseline samples for CEX netflow context."),
    ("data", "v08_hyperliquid_position_state_history", "data/hyperliquid_position_state_history.csv", "no", "stable", "Append-only Hyperliquid watched-position state history."),
    ("data", "v081_raw_token_unlocks_template", "data/raw_token_unlocks_template.csv", "yes", "stable", "Template for raw token unlock CSV imports."),
    ("data", "v081_token_unlock_column_mapping", "data/token_unlock_column_mapping.json", "yes", "stable", "Column alias mapping for token unlock CSV imports."),
    ("data", "v081_token_unlock_calendar_imported", "data/token_unlock_calendar_imported.csv", "no", "stable", "Non-destructive imported token unlock calendar preview."),
    ("data", "v08_binance_long_short_snapshot", "data/binance_long_short_snapshot.csv", "no", "fresh_24h", "Binance USD-M public long/short ratio snapshot."),
    ("results", "v08_binance_long_short_summary", "results/v08_binance_long_short_summary.csv", "no", "fresh_24h", "Summary of Binance USD-M long/short ratio snapshot."),
    ("results", "v08_tg_morning_digest", "results/v08_tg_morning_digest.md", "no", "fresh_24h", "China-time morning TG intelligence digest."),
    ("results", "v08_tg_morning_digest_summary", "results/v08_tg_morning_digest_summary.csv", "no", "fresh_24h", "Morning digest run summary."),
    ("results", "v08_tg_noon_digest", "results/v08_tg_noon_digest.md", "no", "fresh_24h", "China-time noon TG intelligence digest."),
    ("results", "v08_tg_noon_digest_summary", "results/v08_tg_noon_digest_summary.csv", "no", "fresh_24h", "Noon digest run summary."),
    ("results", "v08_tg_evening_digest", "results/v08_tg_evening_digest.md", "no", "fresh_24h", "China-time evening TG intelligence digest."),
    ("results", "v08_tg_evening_digest_summary", "results/v08_tg_evening_digest_summary.csv", "no", "fresh_24h", "Evening digest run summary."),
    ("results", "backtest_readiness_summary", "results/backtest_readiness_summary.csv", "yes", "fresh_24h", "Conclusion-safety summary for current backtest outputs."),
    ("results", "backtest_readiness_report", "results/backtest_readiness_report.md", "yes", "fresh_24h", "Conclusion-safety report for current backtest outputs."),
    ("results", "v06_other_review_reason_summary", "results/v06_other_review_reason_summary.csv", "no", "stable", "Summary of rule-based other_review split."),
    ("script", "quality_gate_script", "scripts/run_v06_quality_gate.py", "yes", "stable", "Full local quality gate."),
    ("script", "project_os_validation_script", "scripts/validate_project_os.py", "yes", "stable", "Project OS validator."),
    ("script", "artifact_manifest_script", "scripts/build_artifact_manifest.py", "yes", "stable", "Artifact manifest generator."),
    ("script", "symbol_map_validation_script", "scripts/validate_symbol_map.py", "yes", "stable", "Optional public Binance symbol map validator."),
    ("script", "v06_low_risk_preview_backtest_script", "scripts/run_v06_clean_low_risk_preview_backtest.py", "yes", "stable", "Optional low-risk preview sanity-check backtest runner."),
    ("script", "tg_draft_generator_script", "scripts/generate_tg_drafts.py", "yes", "stable", "Local TG-style draft generator; never sends messages."),
    ("script", "tg_draft_feedback_summary_script", "scripts/summarize_tg_draft_feedback.py", "yes", "stable", "Local TG draft feedback summarizer."),
    ("script", "tg_draft_ai_review_script", "scripts/ai_review_tg_drafts.py", "yes", "stable", "OpenRouter/Claude AI reviewer for local TG drafts."),
    ("script", "tg_draft_prefilter_script", "scripts/prefilter_tg_draft_candidates.py", "yes", "stable", "Local pre-Claude TG candidate prefilter."),
    ("script", "tg_approved_pool_script", "scripts/build_approved_tg_draft_pool.py", "yes", "stable", "Approved-only local TG draft pool builder."),
    ("script", "tg_draft_validation_script", "scripts/validate_tg_drafts.py", "yes", "stable", "Local TG draft safety validator."),
    ("script", "tg_draft_review_packet_script", "scripts/prepare_tg_draft_review_packet.py", "yes", "stable", "Compact local TG draft review packet builder."),
    ("script", "tg_draft_review_packet_apply_script", "scripts/apply_tg_draft_review_packet.py", "yes", "stable", "Apply compact TG draft review packet back to the main draft queue."),
    ("script", "other_review_reason_script", "scripts/classify_other_review_reasons.py", "yes", "stable", "Rule-based other_review reason splitter."),
    ("script", "daily_private_pilot_runner", "scripts/run_daily_private_pilot.py", "yes", "stable", "One-command local private-pilot workflow runner."),
    ("script", "daily_private_pilot_report_script", "scripts/build_daily_private_pilot_report.py", "yes", "stable", "One-page local private-pilot report builder."),
    ("script", "tg_draft_rule_improvement_script", "scripts/build_tg_draft_rule_improvement_report.py", "yes", "stable", "Convert AI draft rejects into rule-improvement candidates."),
    ("script", "backtest_readiness_script", "scripts/build_backtest_readiness_report.py", "yes", "stable", "Backtest conclusion-safety report builder."),
    ("script", "v07_watchlist_validation_script", "scripts/validate_v07_watchlists.py", "yes", "stable", "v0.7 watchlist validator."),
    ("script", "v07_first_hand_watcher_runner", "scripts/run_v07_first_hand_watchers.py", "yes", "stable", "v0.7 first-hand watcher runner."),
    ("script", "v07_eth_address_watcher", "scripts/watch_eth_address_transfers.py", "yes", "stable", "Ethereum watched address transfer watcher."),
    ("script", "v07_stablecoin_watcher", "scripts/watch_stablecoin_mint_burn.py", "yes", "stable", "Stablecoin mint/burn watcher."),
    ("script", "v07_hyperliquid_position_watcher", "scripts/watch_hyperliquid_positions.py", "yes", "stable", "Hyperliquid watched account perp-position watcher."),
    ("script", "v07_watcher_normalizer", "scripts/normalize_watcher_alerts_to_events.py", "yes", "stable", "Watcher alert to event normalizer."),
    ("script", "v07_watcher_tg_draft_generator", "scripts/generate_watcher_tg_drafts.py", "yes", "stable", "Watcher TG draft preview generator."),
    ("script", "v07_tg_live_monitor", "scripts/run_v07_tg_live_monitor.py", "yes", "stable", "Continuous watcher-to-TG live monitor with dedupe."),
    ("script", "v07_tg_live_monitor_stop", "scripts/stop_v07_tg_live_monitor.ps1", "yes", "stable", "Stop helper for continuous watcher-to-TG live monitor."),
    ("script", "v08_binance_long_short_watcher", "scripts/watch_binance_long_short_ratios.py", "yes", "stable", "Binance USD-M public long/short ratio snapshot fetcher."),
    ("script", "v08_tg_morning_digest_builder", "scripts/build_tg_morning_digest.py", "yes", "stable", "Morning TG digest builder and optional sender."),
    ("script", "v08_tg_sent_state_metadata_enrichment", "scripts/enrich_tg_sent_state_metadata.py", "yes", "stable", "TG sent-state metadata backfill helper."),
    ("script", "v08_tg_source_usefulness_report", "scripts/build_tg_source_usefulness_report.py", "yes", "stable", "TG source usefulness report builder."),
    ("script", "v08_tg_quality_loop", "scripts/run_tg_quality_loop.py", "yes", "stable", "One-command TG quality loop runner."),
    ("script", "v08_historical_replay_sample_builder", "scripts/build_historical_signal_replay_sample.py", "yes", "stable", "Historical signal replay sample builder."),
    ("script", "v08_historical_replay_runner", "scripts/run_v08_historical_signal_replay.py", "yes", "stable", "Historical signal replay pipeline runner."),
    ("script", "v08_historical_replay_summarizer", "scripts/summarize_historical_signal_replay.py", "yes", "stable", "Historical signal replay findings summarizer."),
    ("script", "v081_historical_source_usefulness_builder", "scripts/build_historical_source_usefulness_from_backtest.py", "yes", "stable", "Build historical source/event usefulness metrics from backtest rows."),
    ("script", "v081_source_readiness_builder", "scripts/build_v08_source_readiness_report.py", "yes", "stable", "Build source-readiness report for first-hand expansion issues."),
    ("script", "v081_token_unlock_calendar_quality", "scripts/build_token_unlock_calendar_quality_report.py", "yes", "stable", "Validate local token unlock calendar readiness."),
    ("script", "v081_token_unlock_importer", "scripts/import_raw_token_unlocks_to_calendar.py", "yes", "stable", "Normalize raw token unlock CSV exports into calendar schema."),
    ("script", "v081_cex_netflow_baseline_report", "scripts/build_cex_netflow_baseline_report.py", "yes", "stable", "Summarize CEX netflow rolling baseline readiness."),
    ("script", "v081_hyperliquid_state_history_report", "scripts/build_hyperliquid_state_history_report.py", "yes", "stable", "Summarize Hyperliquid state history readiness."),
    ("script", "v081_source_quality_runner", "scripts/run_v081_source_quality_reports.py", "yes", "stable", "Run all v0.8.1 source quality reports."),
    ("result", "v08_tg_sent_state_metadata_enrichment_summary", "results/v08_tg_sent_state_metadata_enrichment_summary.csv", "yes", "stable", "TG sent-state metadata enrichment summary."),
    ("result", "v08_tg_source_usefulness_report", "results/v08_tg_source_usefulness_report.md", "yes", "stable", "TG source usefulness markdown report."),
    ("result", "v08_tg_source_usefulness_summary", "results/v08_tg_source_usefulness_summary.csv", "yes", "stable", "TG source usefulness summary."),
    ("result", "v08_tg_source_usefulness_by_source", "results/v08_tg_source_usefulness_by_source.csv", "yes", "stable", "TG source usefulness by-source metrics."),
    ("result", "v08_tg_quality_loop_summary", "results/v08_tg_quality_loop_summary.csv", "yes", "stable", "TG quality loop run summary."),
    ("data", "v08_historical_replay_broad_200_events", "data/events_v08_historical_replay_broad_200.csv", "yes", "stable", "Broad historical replay event sample."),
    ("data", "v08_historical_replay_conservative_120_events", "data/events_v08_historical_replay_conservative_120.csv", "yes", "stable", "Conservative historical replay event sample."),
    ("data", "v08_historical_replay_non_btc_single_asset_200_events", "data/events_v08_historical_replay_non_btc_single_asset_200.csv", "yes", "stable", "Non-BTC single-asset historical replay event sample."),
    ("result", "v08_historical_replay_broad_200_backfill", "results/v08_historical_replay_broad_200_price_backfill.csv", "yes", "stable", "Broad historical replay price backfill."),
    ("result", "v08_historical_replay_broad_200_findings", "results/v08_historical_replay_broad_200_findings.md", "yes", "stable", "Broad historical replay findings."),
    ("result", "v08_historical_replay_conservative_120_backfill", "results/v08_historical_replay_conservative_120_price_backfill.csv", "yes", "stable", "Conservative historical replay price backfill."),
    ("result", "v08_historical_replay_conservative_120_findings", "results/v08_historical_replay_conservative_120_findings.md", "yes", "stable", "Conservative historical replay findings."),
    ("result", "v08_historical_replay_non_btc_single_asset_200_backfill", "results/v08_historical_replay_non_btc_single_asset_200_price_backfill.csv", "yes", "stable", "Non-BTC single-asset historical replay price backfill."),
    ("result", "v08_historical_replay_non_btc_single_asset_200_findings", "results/v08_historical_replay_non_btc_single_asset_200_findings.md", "yes", "stable", "Non-BTC single-asset historical replay findings."),
    ("result", "v081_historical_source_usefulness_report", "results/v081_historical_source_usefulness_report.md", "yes", "stable", "Historical source usefulness report from v081 replay data."),
    ("result", "v081_source_readiness_report", "results/v081_source_readiness_report.md", "yes", "stable", "Source readiness report for token unlock, CEX listings, netflow, Hyperliquid, and usefulness."),
    ("result", "v081_token_unlock_calendar_quality_report", "results/v081_token_unlock_calendar_quality_report.md", "yes", "stable", "Token unlock calendar quality/readiness report."),
    ("result", "v081_token_unlock_import_report", "results/v081_token_unlock_import_report.md", "yes", "stable", "Token unlock import preview report."),
    ("result", "v081_cex_netflow_baseline_report", "results/v081_cex_netflow_baseline_report.md", "yes", "stable", "CEX netflow baseline readiness report."),
    ("result", "v081_hyperliquid_state_history_report", "results/v081_hyperliquid_state_history_report.md", "yes", "stable", "Hyperliquid state history readiness report."),
    ("data", "source_registry", "data/source_registry.csv", "yes", "stable", "Canonical registry of local intelligence sources, routes, shadow status, and evaluation status."),
    ("data", "shadow_events_raw", "data/shadow_events_raw.csv", "no", "fresh_24h", "Shadow-mode events captured for evaluation before live routing."),
    ("data", "tg_evidence_snippets", "data/tg_evidence_snippets.csv", "no", "fresh_24h", "Evidence snippets generated from backtest/source effectiveness for TG copy."),
    ("result", "source_registry_report", "results/source_registry_report.md", "yes", "fresh_24h", "Source registry coverage and consistency report."),
    ("result", "source_effectiveness_report", "results/source_effectiveness_report.md", "yes", "fresh_24h", "Source-level outcome effectiveness report."),
    ("result", "event_type_performance_matrix", "results/event_type_performance_matrix.md", "yes", "fresh_24h", "Event type/source subtype performance matrix from live and historical outcomes."),
    ("result", "event_type_performance_matrix_non_benchmark_alt", "results/event_type_performance_matrix_non_benchmark_alt.md", "yes", "fresh_24h", "Non-BTC/ETH non-macro alt event performance matrix."),
    ("result", "signal_decay_curve", "results/signal_decay_curve.md", "yes", "fresh_24h", "Signal horizon decay curve from live and historical outcomes."),
    ("result", "false_positive_analysis", "results/false_positive_analysis.md", "yes", "fresh_24h", "False-positive/noise analysis for live TG alert outcomes and radar decisions."),
    ("data", "v11_signal_policy", "data/tg_signal_policy_v11.csv", "yes", "fresh_24h", "v11 machine-readable TG routing policy from historical matrix and false-positive analysis."),
    ("result", "v11_signal_policy_report", "results/v11_signal_policy_report.md", "yes", "fresh_24h", "Readable v11 TG routing policy report."),
    ("data", "v12_signal_policy", "data/tg_signal_policy_v12.csv", "yes", "fresh_24h", "v12 strict contamination-aware TG routing policy."),
    ("result", "v12_boost_criteria_report", "results/v12_boost_criteria_report.csv", "yes", "fresh_24h", "Strict v12 boost/downrank/digest-only criteria report."),
    ("result", "v12_whale_position_contamination", "results/v12_whale_position_contamination_report.md", "yes", "fresh_24h", "Whale-position HYPE/single-asset/time-window contamination report."),
    ("result", "v12_hack_classification", "results/v12_hack_classification_report.csv", "yes", "fresh_24h", "Hack-security subtype validation report."),
    ("result", "v12_other_reclassification", "results/v12_other_reclassification_report.csv", "no", "stable", "Other taxonomy reclassification report."),
    ("result", "v13_price_in_report", "results/v13_price_in_report.md", "yes", "fresh_24h", "Pre-event price-in validation report for historical backfill rows."),
    ("result", "v13_other_quality_report", "results/v13_other_quality_report.md", "yes", "fresh_24h", "Quality grading report for uncategorized/other historical candidates."),
    ("result", "v13_hype_contamination_detail", "results/v13_hype_contamination_report.md", "yes", "fresh_24h", "HYPE whale-position burst/source/return contamination detail report."),
    ("result", "v13_whale_asset_contamination", "results/v13_whale_asset_contamination_report.md", "yes", "fresh_24h", "General whale-position asset concentration and burst contamination report."),
    ("data", "v13_source_identity_layers", "data/source_identity_layers.csv", "yes", "fresh_24h", "Three-layer source identity table for source family, channel, and reliability status."),
    ("result", "v13_regime_layer_report", "results/v13_regime_layer_report.md", "yes", "fresh_24h", "BTC regime-layer event performance report."),
    ("result", "v13_active_exploit_urgent_candidates", "results/v13_active_exploit_urgent_candidates.md", "yes", "fresh_24h", "Rare urgent-candidate report for active exploit events."),
    ("data", "v13_extended_alt_backtest_clean", "data/backtest_v13_extended_alt_history_clean.csv", "yes", "fresh_24h", "Extended non-benchmark alt historical backtest with archive flags."),
    ("result", "v13_extended_post_hype_removal_report", "results/v13_extended_post_hype_removal_report.md", "yes", "fresh_24h", "Extended post-HYPE-removal group statistics report."),
    ("result", "v13_rule_tightening_report", "results/v13_rule_tightening_report.md", "yes", "fresh_24h", "Strict candidate gate comparison report."),
    ("data", "v13_source_scores_extended", "data/source_scores_v13_extended.csv", "yes", "fresh_24h", "Source scores and throttle recommendations from extended replay."),
    ("result", "v13_extended_source_throttle_report", "results/v13_extended_source_throttle_report.md", "yes", "fresh_24h", "Source throttle report from extended replay."),
    ("result", "v13_extended_price_in_report", "results/v13_extended_price_in_report.md", "yes", "fresh_24h", "Extended sample pre-event price-in report."),
    ("result", "v13_extended_regime_layer_report", "results/v13_extended_regime_layer_report.md", "yes", "fresh_24h", "Extended sample BTC regime-layer report."),
    ("result", "v14_time_field_diagnosis", "results/v14_time_field_diagnosis.md", "yes", "fresh_24h", "Remote time-field diagnosis for historical export reliability."),
    ("data", "v14_webhook_split_source_scores", "data/source_scores_v14_webhook_split.csv", "yes", "fresh_24h", "Webhook subsource split and source-score table."),
    ("result", "v14_webhook_split_report", "results/v14_webhook_split_report.md", "yes", "fresh_24h", "Webhook subsource split report."),
    ("data", "v14_taxonomy_review_reclassified", "data/taxonomy_review_reclassified.csv", "yes", "fresh_24h", "Rule-based split of needs_taxonomy_review rows."),
    ("result", "v14_needs_taxonomy_review_report", "results/v14_needs_taxonomy_review_report.md", "yes", "fresh_24h", "Needs-taxonomy-review cleanup report."),
    ("data", "v14_etf_fund_flow_filtered", "data/etf_fund_flow_filtered.csv", "yes", "fresh_24h", "ETF/fund-flow rows filtered by amount, issuer, source, and context."),
    ("result", "v14_etf_fund_flow_filter_report", "results/v14_etf_fund_flow_filter_report.md", "yes", "fresh_24h", "ETF/fund-flow quality filter report."),
    ("data", "v14_flow_event_subtypes", "data/v14_flow_event_subtypes.csv", "yes", "fresh_24h", "Split mixed fund-flow rows into ETF, CEX netflow, institutional, and unclear subtypes."),
    ("result", "v14_flow_event_subtypes_report", "results/v14_flow_event_subtypes_report.md", "yes", "fresh_24h", "Readable flow subtype split report."),
    ("data", "v14_active_exploit_verified", "data/active_exploit_verified.csv", "yes", "fresh_24h", "Active exploit candidates with amount/context verification."),
    ("result", "v14_active_exploit_amount_verification_report", "results/v14_active_exploit_amount_verification_report.md", "yes", "fresh_24h", "Active exploit amount verification report."),
    ("data", "v14_short_price_in", "data/v14_short_price_in.csv", "yes", "fresh_24h", "5m/15m/1h pre-event price-in checks."),
    ("data", "v14_upgrade_events", "data/v14_upgrade_events.csv", "yes", "fresh_24h", "Upgrade/fork publishability classification."),
    ("config", "v14_publishable_criteria", "config/publishable_criteria.yaml", "yes", "stable", "Minimum publishable-event criteria for Telegram routing."),
    ("config", "v14_routing_rules", "config/routing_rules.yaml", "yes", "stable", "Configurable watcher routing thresholds and priorities."),
    ("config", "v14_asset_tiers", "config/asset_tiers.yaml", "yes", "stable", "Asset tiers and thresholds for digest focus asset selection."),
    ("config", "v14_term_translations", "config/term_translations.yaml", "yes", "stable", "Plain-Chinese market term translations for TG reports."),
    ("config", "v14_alert_routing", "config/alert_routing.yaml", "yes", "stable", "Intraday radar versus scheduled digest routing thresholds."),
    ("data", "v14_publishable_criteria_eval", "data/v14_publishable_criteria_eval.csv", "yes", "fresh_24h", "Per-event evaluation against minimum publishable criteria."),
    ("data", "v14_publishable_golden_events", "data/v14_publishable_golden_events.csv", "yes", "stable", "Golden known publishable/non-publishable events for criteria validation."),
    ("data", "v14_security_events_normalized", "data/security_events/security_events_normalized.csv", "yes", "fresh_24h", "Normalized external security alert/address-risk events."),
    ("result", "v14_security_alert_ingest_summary", "results/v14_security_alert_ingest_summary.csv", "yes", "fresh_24h", "Security alert source ingest status summary."),
    ("data", "v14_etf_daily_flows_farside", "data/etf_daily_flows_farside.csv", "yes", "fresh_24h", "Farside BTC ETF daily flow table normalized locally."),
    ("data", "v14_eth_etf_flows_farside", "data/eth_etf_flows_farside.csv", "no", "fresh_24h", "Optional Farside ETH ETF daily flow table; may be empty if blocked by Cloudflare."),
    ("result", "v14_etf_daily_digest", "results/v14_etf_daily_digest.md", "yes", "fresh_24h", "BTC ETF daily flow digest candidate."),
    ("result", "v14_eth_etf_daily_digest", "results/v14_eth_etf_daily_digest.md", "no", "fresh_24h", "Optional ETH ETF daily flow digest candidate."),
    ("data", "v14_first_hand_publish_candidates", "data/v14_first_hand_publish_candidates.csv", "yes", "fresh_24h", "First-hand watcher publish route candidates."),
    ("result", "v14_first_hand_publish_candidates_report", "results/v14_first_hand_publish_candidates.md", "yes", "fresh_24h", "First-hand watcher routing report."),
    ("result", "v14_publishable_criteria_validation", "results/v14_publishable_criteria_validation.csv", "yes", "fresh_24h", "Golden-event validation for publishable criteria."),
    ("result", "v14_e2e_publish_preview", "results/v14_e2e_publish_preview.md", "yes", "fresh_24h", "Local end-to-end publish preview without Telegram send."),
    ("result", "v14_hyperliquid_snapshot_card", "results/v14_hyperliquid_snapshot_card.md", "yes", "fresh_24h", "Hyperliquid static market-structure background card."),
    ("result", "v14_market_state_snapshot", "results/v14_market_state_snapshot.md", "yes", "fresh_24h", "Public Binance price, volume, open-interest, funding, and crowding market-state snapshot."),
    ("result", "v14_focus_assets", "results/v14_focus_assets.csv", "yes", "fresh_24h", "Focus assets selected from tier rules and market-state thresholds."),
    ("result", "v14_price_oi_quadrant", "results/v14_price_oi_quadrant.csv", "yes", "fresh_24h", "Plain-Chinese price/open-interest quadrant classification."),
    ("result", "v14_etf_plain_summary", "results/v14_etf_plain_summary.md", "yes", "fresh_24h", "Plain-Chinese ETF flow first-screen summary."),
    ("result", "v14_etf_concentration_interpretation", "results/v14_etf_concentration_interpretation.txt", "yes", "fresh_24h", "ETF concentration-change plain-Chinese interpretation."),
    ("result", "v14_market_alert_headline", "results/v14_market_alert_headline.txt", "yes", "fresh_24h", "One-line abnormality headline for TG market-state digest."),
    ("data", "v14_funding_rate_percentiles", "data/funding_rate/funding_rate_percentiles.csv", "yes", "fresh_24h", "Binance USD-M funding-rate historical samples for percentile context."),
    ("data", "v14_oi_percentiles", "data/oi/oi_percentiles.csv", "yes", "fresh_24h", "Binance USD-M open-interest historical samples for percentile context."),
    ("result", "v14_derivatives_history_percentiles", "results/v14_derivatives_history_percentiles.md", "yes", "fresh_24h", "Funding-rate and OI historical percentile report."),
    ("result", "v15_percentile_alerts_json", "results/v15_percentile_alerts.json", "yes", "fresh_24h", "Layered percentile alert buckets for TG first screen, today-watch, radar, and digest context."),
    ("result", "v15_percentile_alerts_report", "results/v15_percentile_alerts.md", "yes", "fresh_24h", "Readable layered percentile alert report."),
    ("result", "v15_percentile_alerts_summary", "results/v15_percentile_alerts_summary.csv", "yes", "fresh_24h", "Layered percentile alert generation summary."),
    ("data", "v15_hyperliquid_market_meta_snapshot", "data/hyperliquid/market_meta_snapshot.csv", "yes", "fresh_24h", "Hyperliquid official public perp market metadata snapshot."),
    ("data", "v15_hyperliquid_market_meta_history", "data/hyperliquid/market_meta_history.csv", "yes", "fresh_24h", "Append-only Hyperliquid public market metadata history."),
    ("result", "v15_hyperliquid_market_meta_card", "results/v15_hyperliquid_market_meta_card.md", "yes", "fresh_24h", "Readable Hyperliquid official market-structure card."),
    ("result", "v15_hyperliquid_market_meta_summary", "results/v15_hyperliquid_market_meta_summary.csv", "yes", "fresh_24h", "Hyperliquid official market metadata fetch summary."),
    ("result", "v15_hyperliquid_liquidation_wall", "results/v15_hyperliquid_liquidation_wall.md", "yes", "fresh_24h", "Monitored Hyperliquid large-position liquidation-wall context."),
    ("result", "v15_hyperliquid_liquidation_wall_summary", "results/v15_hyperliquid_liquidation_wall_summary.csv", "yes", "fresh_24h", "Hyperliquid liquidation-wall route counts."),
    ("result", "v14_market_state_first_screen", "results/v14_market_state_first_screen.md", "yes", "fresh_24h", "Concise first-screen TG market-state block."),
    ("result", "v14_prioritized_events", "results/v14_prioritized_events.md", "yes", "fresh_24h", "Auditable top-watch versus other-dynamic event priority report."),
    ("result", "v14_today_focus_events", "results/v14_today_focus_events.csv", "yes", "fresh_24h", "Events admitted into today's top-watch section after dynamic thresholds."),
    ("result", "v14_other_events", "results/v14_other_events.csv", "yes", "fresh_24h", "Events relegated to other-dynamic section after dynamic thresholds."),
    ("data", "v14_prefilter_results", "data/v14_prefilter_results.csv", "yes", "fresh_24h", "Hard PreFilter results before Composer and Publisher."),
    ("result", "v14_prefilter_report", "results/v14_prefilter_report.md", "yes", "fresh_24h", "Readable hard PreFilter block report."),
    ("data", "v14_composer_scores", "data/v14_composer_scores.csv", "yes", "fresh_24h", "Auditable five-stage Composer scores for historical candidates."),
    ("result", "v14_composer_scores_report", "results/v14_composer_scores_report.md", "yes", "fresh_24h", "Readable Composer five-stage score report."),
    ("data", "v14_publish_policy_candidates", "data/v14_publish_policy_candidates.csv", "yes", "fresh_24h", "Claude-directed block/digest/interrupt publishing policy decisions."),
    ("result", "v14_publish_policy_report", "results/v14_publish_policy_report.md", "yes", "fresh_24h", "Readable v14 publishing policy report."),
    ("result", "v14_digest_preview", "results/v14_digest_preview.md", "yes", "fresh_24h", "Strict morning/evening digest preview using quality-gated rows only."),
    ("data", "v08_non_benchmark_alt_events", "data/events_v08_historical_replay_non_benchmark_alt_50.csv", "yes", "stable", "Non-benchmark alt historical replay event sample."),
    ("result", "v08_non_benchmark_alt_backfill", "results/v08_historical_replay_non_benchmark_alt_50_price_backfill.csv", "yes", "stable", "Non-benchmark alt historical replay price backfill."),
    ("result", "v08_non_benchmark_alt_quality", "results/v08_historical_replay_non_benchmark_alt_50_quality_report.csv", "yes", "stable", "Non-benchmark alt historical replay quality report."),
    ("result", "v08_non_benchmark_alt_findings", "results/v08_historical_replay_non_benchmark_alt_50_findings.md", "yes", "stable", "Non-benchmark alt historical replay findings."),
    ("result", "source_adapter_validation_report", "results/source_adapter_validation_report.md", "yes", "fresh_24h", "Normalized source adapter output validation report."),
    ("result", "shadow_source_evaluation_report", "results/shadow_source_evaluation_report.md", "yes", "fresh_24h", "Shadow-mode source evaluation report."),
    ("result", "tg_evidence_snippets_preview", "results/tg_evidence_snippets.md", "no", "fresh_24h", "Readable preview of evidence snippets for TG cards and digests."),
    ("result", "llm_usage_report", "results/llm_usage_report.md", "yes", "fresh_24h", "LLM usage and cost-control report."),
    ("result", "v11_readiness_report", "results/v11_readiness_report.md", "yes", "fresh_24h", "v11 source-quality-first readiness report."),
    ("result", "v11_digest_preview", "results/v11_tg_custom_digest_preview.md", "no", "fresh_24h", "Readable TG digest preview after evidence-snippet upgrade."),
    ("doc", "source_adapter_schema", "docs/SOURCE_ADAPTER_SCHEMA.md", "yes", "stable", "Normalized source adapter schema used by watcher/news/calendar sources."),
    ("doc", "v11_external_reference_upgrade_plan", "docs/V11_EXTERNAL_REFERENCE_UPGRADE_PLAN_CN.md", "yes", "stable", "Accepted v11 upgrade plan derived from external references and Claude review."),
    ("script", "source_registry_report_script", "scripts/build_source_registry_report.py", "yes", "stable", "Build source registry coverage and consistency report."),
    ("script", "source_effectiveness_report_script", "scripts/build_source_effectiveness_report.py", "yes", "stable", "Build source effectiveness report from ledger/outcomes/registry."),
    ("script", "event_type_performance_matrix_script", "scripts/build_event_type_performance_matrix.py", "yes", "stable", "Build event type and source subtype performance matrix."),
    ("script", "signal_decay_curve_script", "scripts/build_signal_decay_curve.py", "yes", "stable", "Build horizon-level signal decay curve."),
    ("script", "false_positive_analysis_script", "scripts/build_false_positive_analysis.py", "yes", "stable", "Build false-positive/noise analysis from TG outcomes and radar decision logs."),
    ("script", "v11_signal_policy_script", "scripts/build_v11_signal_policy.py", "yes", "stable", "Build v11 machine-readable routing policy from historical matrix and false-positive analysis."),
    ("script", "validate_whale_position_contamination_script", "scripts/validate_whale_position_contamination.py", "yes", "stable", "Validate contamination in whale-position samples."),
    ("script", "reclassify_other_with_new_taxonomy_script", "scripts/reclassify_other_with_new_taxonomy.py", "yes", "stable", "Reclassify candidate_event_type=other with v12 taxonomy rules."),
    ("script", "validate_hack_classification_script", "scripts/validate_hack_classification.py", "yes", "stable", "Split hack_security rows into active exploit, disclosure, recovery, enforcement, pause, and unclear buckets."),
    ("script", "apply_boost_criteria_v12_script", "scripts/apply_boost_criteria_v12.py", "yes", "stable", "Apply strict v12 contamination-aware routing policy."),
    ("script", "validate_price_in_effect_script", "scripts/validate_price_in_effect.py", "yes", "stable", "Validate pre-event price-in effects against post-event abnormal returns."),
    ("script", "grade_other_quality_script", "scripts/grade_other_quality.py", "yes", "stable", "Grade uncategorized/other candidate quality before further taxonomy work."),
    ("script", "analyze_hype_contamination_detail_script", "scripts/analyze_hype_contamination_detail.py", "yes", "stable", "Analyze HYPE-specific whale-position contamination patterns."),
    ("script", "analyze_whale_position_asset_contamination_script", "scripts/analyze_whale_position_asset_contamination.py", "yes", "stable", "Analyze general whale-position single-asset and short-window contamination."),
    ("script", "build_source_identity_layers_script", "scripts/build_source_identity_layers.py", "yes", "stable", "Build three-layer source identity and reliability table."),
    ("script", "build_regime_layer_report_script", "scripts/build_regime_layer_report.py", "yes", "stable", "Build BTC regime-layer report for historical event performance."),
    ("script", "build_active_exploit_urgent_candidates_script", "scripts/build_active_exploit_urgent_candidates.py", "yes", "stable", "Build rare urgent-candidate list for active exploit events."),
    ("script", "archive_hype_and_recompute_stats_script", "scripts/archive_hype_and_recompute_stats.py", "yes", "stable", "Archive HYPE whale burst contamination and recompute group statistics."),
    ("script", "tighten_candidate_identification_rules_script", "scripts/tighten_candidate_identification_rules.py", "yes", "stable", "Apply stricter candidate gates to reduce garbage candidates."),
    ("script", "score_and_throttle_sources_script", "scripts/score_and_throttle_sources.py", "yes", "stable", "Score sources and derive source-level throttle rules."),
    ("script", "diagnose_remote_time_fields_script", "scripts/diagnose_remote_time_fields.py", "yes", "stable", "Diagnose remote historical time-field coverage."),
    ("script", "export_real_news_older_v2_script", "scripts/export_real_news_older_v2.py", "yes", "stable", "Explicit-time-field older real-news exporter."),
    ("script", "split_webhook_subsources_script", "scripts/split_webhook_subsources.py", "yes", "stable", "Split webhook into subsources and score them separately."),
    ("script", "analyze_needs_taxonomy_review_script", "scripts/analyze_needs_taxonomy_review.py", "yes", "stable", "Rule-split needs_taxonomy_review rows into concrete buckets."),
    ("script", "filter_etf_fund_flow_script", "scripts/filter_etf_fund_flow.py", "yes", "stable", "Filter ETF/fund-flow rows for digest eligibility."),
    ("script", "split_flow_event_subtypes_script", "scripts/split_flow_event_subtypes.py", "yes", "stable", "Split ETF/fund-flow versus CEX netflow and institutional flow rows."),
    ("script", "verify_exploit_amounts_script", "scripts/verify_exploit_amounts.py", "yes", "stable", "Verify active-exploit amount and context before urgent eligibility."),
    ("script", "build_v14_short_price_in_script", "scripts/build_v14_short_price_in.py", "yes", "stable", "Build 5m/15m/1h pre-event price-in checks."),
    ("script", "classify_v14_upgrade_events_script", "scripts/classify_v14_upgrade_events.py", "yes", "stable", "Classify upgrade/fork events into digest/background/block."),
    ("script", "define_publishable_event_criteria_script", "scripts/define_publishable_event_criteria.py", "yes", "stable", "Write and evaluate minimum publishable event criteria."),
    ("script", "ingest_security_alerts_script", "scripts/ingest_security_alerts.py", "yes", "stable", "Ingest external security alert sources into normalized local CSV."),
    ("script", "build_etf_daily_digest_script", "scripts/build_etf_daily_digest.py", "yes", "stable", "Build daily BTC ETF flow digest from Farside public table."),
    ("script", "build_first_hand_publish_candidates_script", "scripts/build_first_hand_publish_candidates.py", "yes", "stable", "Route first-hand watcher alerts into publish/archive channels."),
    ("script", "validate_publishable_criteria_script", "scripts/validate_publishable_criteria.py", "yes", "stable", "Validate publishable criteria against golden known events."),
    ("script", "test_end_to_end_publish_script", "scripts/test_end_to_end_publish.py", "yes", "stable", "Build local publish preview from current candidates without sending Telegram."),
    ("script", "aggregate_hyperliquid_snapshot_script", "scripts/aggregate_hyperliquid_snapshot.py", "yes", "stable", "Aggregate Hyperliquid position snapshots into background digest card."),
    ("script", "build_market_state_snapshot_script", "scripts/build_market_state_snapshot.py", "yes", "stable", "Build public Binance market-state snapshot for TG digests."),
    ("script", "select_focus_assets_script", "scripts/market/select_focus_assets.py", "yes", "stable", "Select digest focus assets from asset tiers and market-state thresholds."),
    ("script", "classify_price_oi_quadrant_script", "scripts/market/classify_price_oi_quadrant.py", "yes", "stable", "Classify price/open-interest quadrant explanations."),
    ("script", "generate_etf_summary_script", "scripts/reporting/generate_etf_summary.py", "yes", "stable", "Render ETF flow context into a concise first-screen block."),
    ("script", "generate_alert_headline_script", "scripts/reporting/generate_alert_headline.py", "yes", "stable", "Generate one-line abnormality headline for TG market-state digest."),
    ("script", "build_derivatives_history_percentiles_script", "scripts/market/build_derivatives_history_percentiles.py", "yes", "stable", "Fetch Binance USD-M funding/OI history and compute percentile context."),
    ("script", "generate_percentile_alerts_script", "scripts/market/generate_percentile_alerts.py", "yes", "stable", "Convert historical derivative percentiles into layered TG alert placement buckets."),
    ("script", "hyperliquid_market_meta_fetcher", "scripts/hyperliquid/fetch_market_meta.py", "yes", "stable", "Fetch Hyperliquid official public perp market metadata via metaAndAssetCtxs."),
    ("script", "hyperliquid_market_meta_card", "scripts/hyperliquid/generate_market_meta_card.py", "yes", "stable", "Render Hyperliquid official market metadata into a concise card."),
    ("script", "hyperliquid_liquidation_wall", "scripts/hyperliquid/generate_liquidation_wall.py", "yes", "stable", "Render monitored Hyperliquid large-position liquidation-wall context."),
    ("script", "generate_market_state_summary_script", "scripts/reporting/generate_market_state_summary.py", "yes", "stable", "Render concise market-state first screen for TG digest."),
    ("script", "prioritize_events_script", "scripts/events/prioritize_events.py", "yes", "stable", "Prioritize TG digest events into top-watch and other-dynamic buckets."),
    ("script", "build_v14_prefilter_script", "scripts/build_v14_prefilter.py", "yes", "stable", "Build hard PreFilter output before Composer and Publisher."),
    ("script", "build_v14_composer_scores_script", "scripts/build_v14_composer_scores.py", "yes", "stable", "Build auditable five-stage Composer scores."),
    ("script", "apply_v14_publish_policy_script", "scripts/apply_v14_publish_policy.py", "yes", "stable", "Apply Claude-directed block/digest/interrupt publishing policy."),
    ("script", "build_v14_digest_preview_script", "scripts/build_v14_digest_preview.py", "yes", "stable", "Build strict v14 morning/evening digest preview."),
    ("script", "source_adapter_validation_script", "scripts/validate_source_adapter_outputs.py", "yes", "stable", "Validate normalized source adapter outputs against schema and registry."),
    ("script", "shadow_source_evaluation_script", "scripts/run_shadow_source_evaluation.py", "yes", "stable", "Extract and summarize shadow-mode source events."),
    ("script", "tg_evidence_snippet_script", "scripts/render_tg_evidence_snippet.py", "yes", "stable", "Render evidence snippets from source effectiveness and event performance data."),
    ("script", "llm_usage_report_script", "scripts/build_llm_usage_report.py", "yes", "stable", "Build LLM usage and estimated cost reports."),
    ("script", "v11_readiness_report_script", "scripts/build_v11_readiness_report.py", "yes", "stable", "Build v11 source-quality-first readiness report."),
    ("script", "tg_test_sender_script", "scripts/send_tg_draft_test.py", "yes", "stable", "Manual dry-run/send helper for TG draft testing."),
    ("script", "local_environment_script", "scripts/check_local_environment.py", "yes", "stable", "Environment checker."),
    ("script", "secret_scan_script", "scripts/check_secret_leaks.py", "yes", "stable", "Secret scanner."),
    ("script", "local_secret_loader", "scripts/load_local_secrets.ps1", "yes", "stable", "Loads ignored local secrets into the current PowerShell process."),
    ("script", "command_registry_script", "scripts/build_command_registry.py", "yes", "stable", "Command registry builder."),
    ("script", "review_actions_script", "scripts/build_project_review_actions.py", "yes", "stable", "Review action builder."),
    ("script", "cursor_prompt_script", "scripts/generate_cursor_prompt.py", "yes", "stable", "Cursor prompt generator."),
    ("script", "claude_prompt_script", "scripts/generate_claude_question_prompt.py", "yes", "stable", "Claude prompt generator."),
    ("script", "claude_query_script", "scripts/query_claude_next.py", "yes", "stable", "Claude OpenRouter query wrapper."),
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a manifest of required project artifacts.")
    parser.add_argument("--output", default=str(ROOT / "results" / "artifact_manifest.csv"))
    parser.add_argument("--summary", default=str(ROOT / "results" / "artifact_manifest_summary.csv"))
    parser.add_argument("--markdown-output", default=str(ROOT / "docs" / "ARTIFACT_MANIFEST.md"))
    parser.add_argument("--max-age-hours", type=float, default=24.0)
    return parser.parse_args()


def normalize_path(value: str) -> Path:
    path = Path(value)
    if not path.is_absolute():
        path = ROOT / path
    return path


def artifact_row(
    artifact_id: str,
    category: str,
    rel_path: str,
    required: str,
    freshness_policy: str,
    notes: str,
    max_age_hours: float,
) -> dict:
    path = ROOT / rel_path
    exists = path.exists()
    age_hours = ""
    is_stale = False
    if exists:
        stat = path.stat()
        size_bytes = stat.st_size
        updated = datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S")
        age_hours = round((datetime.now().timestamp() - stat.st_mtime) / 3600, 4)
        is_stale = freshness_policy == "fresh_24h" and float(age_hours) > max_age_hours
    else:
        size_bytes = ""
        updated = ""
    if not exists and required == "yes":
        status = "fail"
    elif required == "yes" and is_stale:
        status = "fail"
    elif is_stale:
        status = "warning"
    else:
        status = "pass"
    return {
        "artifact_id": artifact_id,
        "category": category,
        "path": rel_path,
        "required": required,
        "freshness_policy": freshness_policy,
        "exists": "yes" if exists else "no",
        "size_bytes": size_bytes,
        "updated_at_china": updated,
        "age_hours": age_hours,
        "status": status,
        "notes": notes,
    }


def render_markdown(rows: list[dict]) -> str:
    df = pd.DataFrame(rows)
    missing_required = int(((df["required"] == "yes") & (df["exists"] != "yes")).sum()) if not df.empty else 0
    stale_required = int(((df["required"] == "yes") & (df["status"] == "fail") & (df["exists"] == "yes")).sum()) if not df.empty else 0
    lines = [
        "# Artifact Manifest",
        "",
        f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC+8')}",
        "",
        f"required_artifacts: {int((df['required'] == 'yes').sum()) if not df.empty else 0}",
        f"missing_required_count: {missing_required}",
        f"stale_required_count: {stale_required}",
        "",
        "| artifact_id | category | path | required | freshness | exists | status | updated_at_china | notes |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for row in rows:
        lines.append(
            f"| `{row['artifact_id']}` | {row['category']} | `{row['path']}` | {row['required']} | {row['freshness_policy']} | {row['exists']} | {row['status']} | {row['updated_at_china']} | {row['notes']} |"
        )
    return "\n".join(lines) + "\n"


def main() -> int:
    args = parse_args()
    rows = [
        artifact_row(artifact_id, category, rel_path, required, freshness_policy, notes, args.max_age_hours)
        for category, artifact_id, rel_path, required, freshness_policy, notes in ARTIFACTS
    ]
    df = pd.DataFrame(rows)
    missing_required = int(((df["required"] == "yes") & (df["exists"] != "yes")).sum()) if not df.empty else len(ARTIFACTS)
    stale_required = int(((df["required"] == "yes") & (df["status"] == "fail") & (df["exists"] == "yes")).sum()) if not df.empty else 0

    output = normalize_path(args.output)
    summary = normalize_path(args.summary)
    markdown_output = normalize_path(args.markdown_output)
    output.parent.mkdir(parents=True, exist_ok=True)
    summary.parent.mkdir(parents=True, exist_ok=True)
    markdown_output.parent.mkdir(parents=True, exist_ok=True)

    df.to_csv(output, index=False)
    pd.DataFrame(
        [
            {
                "artifact_count": len(rows),
                "required_artifact_count": int((df["required"] == "yes").sum()) if not df.empty else 0,
                "missing_required_count": missing_required,
                "stale_required_count": stale_required,
                "status": "pass" if missing_required == 0 and stale_required == 0 else "fail",
            }
        ]
    ).to_csv(summary, index=False)
    markdown_output.write_text(render_markdown(rows), encoding="utf-8")
    print(f"wrote artifact manifest to {output}")
    print(f"wrote artifact manifest summary to {summary}")
    print(f"wrote artifact manifest markdown to {markdown_output}")
    return 0 if missing_required == 0 and stale_required == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
